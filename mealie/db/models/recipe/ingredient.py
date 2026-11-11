from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, event, literal, orm
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import Mapped, mapped_column, query_expression
from sqlalchemy.orm.session import Session

from mealie.db.models._model_base import BaseMixins, FilterableColumn, SqlAlchemyBase
from mealie.db.models.recipe.api_extras import IngredientFoodExtras, api_extras
from mealie.db.models.recipe.labels import MultiPurposeLabel

from .._model_utils.auto_init import AutoInitOptions, auto_init
from .._model_utils.guid import GUID

if TYPE_CHECKING:
    from ..group import Group
    from ..household import Household
    from .allergen import Allergen
    from .recipe import RecipeModel

households_to_ingredient_foods = sa.Table(
    "households_to_ingredient_foods",
    SqlAlchemyBase.metadata,
    sa.Column("household_id", GUID, sa.ForeignKey("households.id"), index=True),
    sa.Column("food_id", GUID, sa.ForeignKey("ingredient_foods.id"), index=True),
    sa.UniqueConstraint("household_id", "food_id", name="household_id_food_id_key"),
)

ingredient_foods_to_allergens = sa.Table(
    "ingredient_foods_to_allergens",
    SqlAlchemyBase.metadata,
    sa.Column("food_id", GUID, sa.ForeignKey("ingredient_foods.id", ondelete="CASCADE"), index=True),
    sa.Column("allergen_id", GUID, sa.ForeignKey("allergens.id", ondelete="CASCADE"), index=True),
    sa.UniqueConstraint("food_id", "allergen_id", name="ingredient_foods_to_allergens_key"),
)

# the other foods of a combination substitution ("butter + flour"), the first one being substitute_food
ingredient_foods_substitutions_additional_foods = sa.Table(
    "ingredient_foods_substitutions_additional_foods",
    SqlAlchemyBase.metadata,
    sa.Column(
        "substitution_id", GUID, sa.ForeignKey("ingredient_foods_substitutions.id", ondelete="CASCADE"), index=True
    ),
    sa.Column("food_id", GUID, sa.ForeignKey("ingredient_foods.id", ondelete="CASCADE"), index=True),
    sa.UniqueConstraint("substitution_id", "food_id", name="ingredient_foods_substitutions_additional_foods_key"),
)

recipes_ingredients_substitutions_additional_foods = sa.Table(
    "recipes_ingredients_substitutions_additional_foods",
    SqlAlchemyBase.metadata,
    sa.Column(
        "substitution_id",
        GUID,
        sa.ForeignKey("recipes_ingredients_substitutions.id", ondelete="CASCADE"),
        index=True,
    ),
    sa.Column("food_id", GUID, sa.ForeignKey("ingredient_foods.id", ondelete="CASCADE"), index=True),
    sa.UniqueConstraint("substitution_id", "food_id", name="recipes_ingredients_substitutions_additional_foods_key"),
)

ResolvedSubstitution = tuple[GUID | None, str | None, list[GUID]]


def resolve_substitutions(
    session: Session,
    group_id: GUID | None,
    substitutions: list[dict] | None,
    exclude_food_id: GUID | None = None,
) -> list[ResolvedSubstitution]:
    """
    Normalizes a substitution payload into (substitute_food_id, note) pairs safe to persist.

    Substitute ids arrive straight from the payload, so the repository's group scoping does
    not cover them. They are resolved against `group_id`, and an id resolving to nothing --
    deleted, or belonging to another group -- invalidates the whole substitution, since the note
    qualifies the food it travels with. `exclude_food_id` rejects self-substitution the same
    way. Both tiers share this; only the row they build from it differs.

    The additional foods of a combination are resolved the same way, but an unresolvable one is
    simply dropped, along with any repeat of the substitute food or of the excluded food.
    """

    if not substitutions or not group_id:
        return []

    requested_food_ids = {sub.get("substitute_food_id") for sub in substitutions}
    for sub in substitutions:
        requested_food_ids.update(sub.get("additional_food_ids") or [])
    requested_food_ids.discard(None)

    resolvable_food_ids: set = set()
    if requested_food_ids:
        resolvable_food_ids = set(
            session.execute(
                sa.select(IngredientFoodModel.id).filter(
                    IngredientFoodModel.group_id == group_id,
                    IngredientFoodModel.id.in_(requested_food_ids),
                )
            )
            .scalars()
            .all()
        )

    resolved: list[ResolvedSubstitution] = []
    seen_combinations: set[frozenset] = set()
    for sub in substitutions:
        substitute_food_id = sub.get("substitute_food_id")
        note = (sub.get("note") or "").strip() or None

        if substitute_food_id is None:
            # note-only rows are deliberately not de-duped: two textual workarounds are
            # two legitimate rows, and there is no id to collapse them on
            if not note:
                continue
        elif substitute_food_id not in resolvable_food_ids or substitute_food_id == exclude_food_id:
            continue

        additional_food_ids: list[GUID] = []
        if substitute_food_id is not None:
            for food_id in sub.get("additional_food_ids") or []:
                if (
                    food_id in resolvable_food_ids
                    and food_id not in (substitute_food_id, exclude_food_id)
                    and food_id not in additional_food_ids
                ):
                    additional_food_ids.append(food_id)

            # a substitution is identified by its whole set of foods: "butter + flour" and
            # "butter + oil" both stay, "butter + flour" and "flour + butter" are the same one
            combination = frozenset([substitute_food_id, *additional_food_ids])
            if combination in seen_combinations:
                continue
            seen_combinations.add(combination)

        resolved.append((substitute_food_id, note, additional_food_ids))

    return resolved


class IngredientUnitModel(SqlAlchemyBase, BaseMixins):
    __tablename__ = "ingredient_units"
    id: FilterableColumn[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)

    # ID Relationships
    group_id: FilterableColumn[GUID] = mapped_column(GUID, ForeignKey("groups.id"), nullable=False, index=True)
    group: Mapped[Group] = orm.relationship("Group", back_populates="ingredient_units", foreign_keys=[group_id])

    name: FilterableColumn[str | None] = mapped_column(String)
    plural_name: FilterableColumn[str | None] = mapped_column(String)
    description: FilterableColumn[str | None] = mapped_column(String)
    abbreviation: FilterableColumn[str | None] = mapped_column(String)
    plural_abbreviation: FilterableColumn[str | None] = mapped_column(String)
    use_abbreviation: FilterableColumn[bool | None] = mapped_column(Boolean, default=False)
    fraction: FilterableColumn[bool | None] = mapped_column(Boolean, default=True)

    ingredients: Mapped[list[RecipeIngredientModel]] = orm.relationship("RecipeIngredientModel", back_populates="unit")
    aliases: Mapped[list[IngredientUnitAliasModel]] = orm.relationship(
        "IngredientUnitAliasModel",
        back_populates="unit",
        cascade="all, delete, delete-orphan",
    )

    # Standardization
    standard_quantity: FilterableColumn[float | None] = mapped_column(Float)
    standard_unit: FilterableColumn[str | None] = mapped_column(String)

    # Automatically updated by sqlalchemy event, do not write to this manually
    name_normalized: FilterableColumn[str | None] = mapped_column(sa.String, index=True)
    plural_name_normalized: FilterableColumn[str | None] = mapped_column(sa.String, index=True)
    abbreviation_normalized: FilterableColumn[str | None] = mapped_column(String, index=True)
    plural_abbreviation_normalized: FilterableColumn[str | None] = mapped_column(String, index=True)

    @auto_init()
    def __init__(
        self,
        session: Session,
        name: str | None = None,
        plural_name: str | None = None,
        abbreviation: str | None = None,
        plural_abbreviation: str | None = None,
        **_,
    ) -> None:
        if name is not None:
            self.name_normalized = self.normalize(name)
        if plural_name is not None:
            self.plural_name_normalized = self.normalize(plural_name)
        if abbreviation is not None:
            self.abbreviation_normalized = self.normalize(abbreviation)
        if plural_abbreviation is not None:
            self.plural_abbreviation_normalized = self.normalize(plural_abbreviation)

        tableargs = [
            sa.UniqueConstraint("name", "group_id", name="ingredient_units_name_group_id_key"),
            sa.Index(
                "ix_ingredient_units_name_normalized",
                "name_normalized",
                unique=False,
            ),
            sa.Index(
                "ix_ingredient_units_plural_name_normalized",
                "plural_name_normalized",
                unique=False,
            ),
            sa.Index(
                "ix_ingredient_units_abbreviation_normalized",
                "abbreviation_normalized",
                unique=False,
            ),
            sa.Index(
                "ix_ingredient_units_plural_abbreviation_normalized",
                "plural_abbreviation_normalized",
                unique=False,
            ),
        ]

        if session.get_bind().name == "postgresql":
            tableargs.extend(
                [
                    sa.Index(
                        "ix_ingredient_units_name_normalized_gin",
                        "name_normalized",
                        unique=False,
                        postgresql_using="gin",
                        postgresql_ops={
                            "name_normalized": "gin_trgm_ops",
                        },
                    ),
                    sa.Index(
                        "ix_ingredient_units_plural_name_normalized_gin",
                        "name_normalized",
                        unique=False,
                        postgresql_using="gin",
                        postgresql_ops={
                            "plural_name_normalized": "gin_trgm_ops",
                        },
                    ),
                    sa.Index(
                        "ix_ingredient_units_abbreviation_normalized_gin",
                        "abbreviation_normalized",
                        unique=False,
                        postgresql_using="gin",
                        postgresql_ops={
                            "abbreviation_normalized": "gin_trgm_ops",
                        },
                    ),
                    sa.Index(
                        "ix_ingredient_units_plural_abbreviation_normalized_gin",
                        "plural_abbreviation_normalized",
                        unique=False,
                        postgresql_using="gin",
                        postgresql_ops={
                            "plural_abbreviation_normalized": "gin_trgm_ops",
                        },
                    ),
                ]
            )

        self.__table_args__ = tuple(tableargs)


class IngredientFoodModel(SqlAlchemyBase, BaseMixins):
    __tablename__ = "ingredient_foods"
    id: FilterableColumn[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)

    # ID Relationships
    group_id: FilterableColumn[GUID] = mapped_column(GUID, ForeignKey("groups.id"), nullable=False, index=True)
    group: Mapped[Group] = orm.relationship("Group", back_populates="ingredient_foods", foreign_keys=[group_id])
    households_with_ingredient_food: Mapped[list[Household]] = orm.relationship(
        "Household", secondary=households_to_ingredient_foods, back_populates="ingredient_foods_on_hand"
    )

    name: FilterableColumn[str | None] = mapped_column(String)
    plural_name: FilterableColumn[str | None] = mapped_column(String)
    description: FilterableColumn[str | None] = mapped_column(String)
    recipe_count: Mapped[int] = query_expression(default_expr=literal(0))

    ingredients: Mapped[list[RecipeIngredientModel]] = orm.relationship("RecipeIngredientModel", back_populates="food")
    aliases: Mapped[list[IngredientFoodAliasModel]] = orm.relationship(
        "IngredientFoodAliasModel",
        back_populates="food",
        cascade="all, delete, delete-orphan",
    )
    # substitutions this food offers, e.g. chicken stock -> chicken broth
    substitutions: Mapped[list[IngredientFoodSubstitutionModel]] = orm.relationship(
        "IngredientFoodSubstitutionModel",
        back_populates="food",
        foreign_keys="IngredientFoodSubstitutionModel.food_id",
        cascade="all, delete, delete-orphan",
        order_by="IngredientFoodSubstitutionModel.position",
        collection_class=ordering_list("position"),
    )
    # substitutions pointing at this food; exists so deleting a food cleans up the ones aimed at it
    substitution_references: Mapped[list[IngredientFoodSubstitutionModel]] = orm.relationship(
        "IngredientFoodSubstitutionModel",
        back_populates="substitute_food",
        foreign_keys="IngredientFoodSubstitutionModel.substitute_food_id",
        cascade="all, delete, delete-orphan",
    )
    # the same, for the recipe tier: without it a deleted food leaves ingredient substitutions
    # pointing at a row that is gone, which renders as an empty popover on SQLite and fails the
    # foreign key outright on Postgres
    recipe_substitution_references: Mapped[list[RecipeIngredientSubstitutionModel]] = orm.relationship(
        "RecipeIngredientSubstitutionModel",
        back_populates="substitute_food",
        cascade="all, delete, delete-orphan",
    )
    # the combinations this food is part of; exists so deleting a food removes it from them
    substitution_combinations: Mapped[list[IngredientFoodSubstitutionModel]] = orm.relationship(
        "IngredientFoodSubstitutionModel",
        secondary=ingredient_foods_substitutions_additional_foods,
        back_populates="additional_foods",
    )
    recipe_substitution_combinations: Mapped[list[RecipeIngredientSubstitutionModel]] = orm.relationship(
        "RecipeIngredientSubstitutionModel",
        secondary=recipes_ingredients_substitutions_additional_foods,
        back_populates="additional_foods",
    )
    allergens: Mapped[list[Allergen]] = orm.relationship(
        "Allergen", secondary=ingredient_foods_to_allergens, back_populates="foods", order_by="Allergen.name"
    )
    extras: Mapped[list[IngredientFoodExtras]] = orm.relationship("IngredientFoodExtras", cascade="all, delete-orphan")
    nutrition: Mapped[IngredientFoodNutritionModel | None] = orm.relationship(
        "IngredientFoodNutritionModel",
        back_populates="food",
        uselist=False,
        cascade="all, delete-orphan",
    )
    nutrition_logs: Mapped[list[IngredientFoodNutritionLogModel]] = orm.relationship(
        "IngredientFoodNutritionLogModel",
        back_populates="food",
        cascade="all, delete-orphan",
    )

    label_id: FilterableColumn[GUID | None] = mapped_column(GUID, ForeignKey("multi_purpose_labels.id"), index=True)
    label: Mapped[MultiPurposeLabel | None] = orm.relationship(MultiPurposeLabel, uselist=False, back_populates="foods")

    # Automatically updated by sqlalchemy event, do not write to this manually
    name_normalized: FilterableColumn[str | None] = mapped_column(sa.String, index=True)
    plural_name_normalized: FilterableColumn[str | None] = mapped_column(sa.String, index=True)

    model_config = AutoInitOptions(
        exclude={
            "households_with_ingredient_food",
            # substitutions are resolved explicitly, since auto_init creates rows it can't find
            "substitutions",
            # resolved explicitly too, against the allergens of the group
            "allergens",
            # the existing row is updated in place, see _set_nutrition
            "nutrition",
            # written by the nutrition estimates only
            "nutrition_logs",
        }
    )

    average_weight: Mapped[float | None] = mapped_column(Float)
    """Weight in grams of one piece of the food, for quantities given without a unit"""
    nutrition_source: Mapped[str | None] = mapped_column(sa.String)
    """Where the nutrition facts come from: ciqual, usda or ai; None when typed in by hand"""
    nutrition_reference_code: Mapped[str | None] = mapped_column(sa.String)
    """Code of the food in the composition table the nutrition facts come from"""
    nutrition_reference_name: Mapped[str | None] = mapped_column(sa.String)

    # Deprecated
    on_hand: Mapped[bool] = mapped_column(Boolean, default=False)

    def _set_substitutions(self, session: Session, group_id: GUID, substitutions: list[dict] | None) -> None:
        """
        Builds the substitution rows by hand, since auto_init creates any related row it
        fails to look up and would manufacture a food out of an unrecognized id.
        """

        resolved = resolve_substitutions(session, group_id, substitutions, exclude_food_id=self.id)
        if not resolved:
            self.substitutions = []
            return

        # Existing rows are reused rather than rebuilt, keeping their ids stable: the same
        # combination first, then any row starting with the same food.
        def combination_of(row: IngredientFoodSubstitutionModel) -> frozenset:
            return frozenset([row.substitute_food_id, *row.additional_food_ids])

        reusable_food_rows = [row for row in self.substitutions if row.substitute_food_id]
        reusable_note_only = [row for row in self.substitutions if not row.substitute_food_id]

        def take_row(
            substitute_food_id: GUID, additional_food_ids: list[GUID]
        ) -> IngredientFoodSubstitutionModel | None:
            combination = frozenset([substitute_food_id, *additional_food_ids])
            candidates = [row for row in reusable_food_rows if combination_of(row) == combination] or [
                row for row in reusable_food_rows if row.substitute_food_id == substitute_food_id
            ]
            if not candidates:
                return None
            reusable_food_rows.remove(candidates[0])
            return candidates[0]

        rows: list[IngredientFoodSubstitutionModel] = []
        additional_foods = _load_foods(session, resolved)
        for substitute_food_id, note, additional_food_ids in resolved:
            if substitute_food_id is not None:
                row = take_row(substitute_food_id, additional_food_ids)
            else:
                row = reusable_note_only.pop(0) if reusable_note_only else None

            if row is None:
                row = IngredientFoodSubstitutionModel(substitute_food_id=substitute_food_id, note=note)
            else:
                row.substitute_food_id = substitute_food_id
                row.note = note

            row.additional_foods = [additional_foods[food_id] for food_id in additional_food_ids]
            rows.append(row)

        # rows left over are orphaned by the assignment and cascade-deleted
        self.substitutions = rows

    def _set_allergens(self, session: Session, group_id: GUID, allergens: list[dict] | None) -> None:
        from .allergen import Allergen

        allergen_ids = {allergen.get("id") for allergen in allergens or [] if isinstance(allergen, dict)}
        allergen_ids.discard(None)
        if not allergen_ids:
            self.allergens = []
            return

        self.allergens = (
            session.query(Allergen).filter(Allergen.group_id == group_id, Allergen.id.in_(allergen_ids)).all()
        )

    def _set_nutrition(self, nutrition: dict | None) -> None:
        """
        Updates the existing nutrition row rather than replacing it, since the unique food_id
        would otherwise be inserted again before the old row is deleted within the same flush.
        A payload without any value removes the row.
        """

        nutrition = nutrition or {}
        values: dict[str, str | None] = {}
        for field in IngredientFoodNutritionModel.NUTRITION_FIELDS:
            value = nutrition.get(field)
            values[field] = str(value).strip() or None if value is not None else None

        if not any(values.values()):
            self.nutrition = None
            return

        if self.nutrition is None:
            self.nutrition = IngredientFoodNutritionModel(**values)
            return

        for field, value in values.items():
            setattr(self.nutrition, field, value)

    @api_extras
    @auto_init()
    def __init__(
        self,
        session: Session,
        group_id: GUID,
        name: str | None = None,
        plural_name: str | None = None,
        households_with_ingredient_food: list[str] | None = None,
        substitutions: list[dict] | None = None,
        nutrition: dict | None = None,
        allergens: list[dict] | None = None,
        **_,
    ) -> None:
        from ..household import Household

        if name is not None:
            self.name_normalized = self.normalize(name)
        if plural_name is not None:
            self.plural_name_normalized = self.normalize(plural_name)

        if not households_with_ingredient_food:
            self.households_with_ingredient_food = []
        else:
            self.households_with_ingredient_food = (
                session.query(Household)
                .filter(Household.group_id == group_id, Household.slug.in_(households_with_ingredient_food))
                .all()
            )

        self._set_substitutions(session, group_id, substitutions)
        self._set_allergens(session, group_id, allergens)
        self._set_nutrition(nutrition)

        tableargs = [
            sa.UniqueConstraint("name", "group_id", name="ingredient_foods_name_group_id_key"),
            sa.Index(
                "ix_ingredient_foods_name_normalized",
                "name_normalized",
                unique=False,
            ),
            sa.Index(
                "ix_ingredient_foods_plural_name_normalized",
                "plural_name_normalized",
                unique=False,
            ),
        ]

        if session.get_bind().name == "postgresql":
            tableargs.extend(
                [
                    sa.Index(
                        "ix_ingredient_foods_name_normalized_gin",
                        "name_normalized",
                        unique=False,
                        postgresql_using="gin",
                        postgresql_ops={
                            "name_normalized": "gin_trgm_ops",
                        },
                    ),
                    sa.Index(
                        "ix_ingredient_foods_plural_name_normalized_gin",
                        "plural_name_normalized",
                        unique=False,
                        postgresql_using="gin",
                        postgresql_ops={
                            "plural_name_normalized": "gin_trgm_ops",
                        },
                    ),
                ]
            )

        self.__table_args__ = tuple(tableargs)


class IngredientUnitAliasModel(SqlAlchemyBase, BaseMixins):
    __tablename__ = "ingredient_units_aliases"
    id: FilterableColumn[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)

    unit_id: FilterableColumn[GUID] = mapped_column(
        GUID, ForeignKey("ingredient_units.id"), primary_key=True, index=True
    )
    unit: Mapped[IngredientUnitModel] = orm.relationship("IngredientUnitModel", back_populates="aliases")

    name: FilterableColumn[str] = mapped_column(String)

    # Automatically updated by sqlalchemy event, do not write to this manually
    name_normalized: FilterableColumn[str | None] = mapped_column(sa.String, index=True)

    @auto_init()
    def __init__(self, session: Session, name: str, **_) -> None:
        self.name_normalized = self.normalize(name)
        tableargs = [
            sa.Index(
                "ix_ingredient_units_aliases_name_normalized",
                "name_normalized",
                unique=False,
            ),
        ]

        if session.get_bind().name == "postgresql":
            tableargs.extend(
                [
                    sa.Index(
                        "ix_ingredient_units_aliases_name_normalized_gin",
                        "name_normalized",
                        unique=False,
                        postgresql_using="gin",
                        postgresql_ops={
                            "name_normalized": "gin_trgm_ops",
                        },
                    ),
                ]
            )

        self.__table_args__ = tableargs


class IngredientFoodAliasModel(SqlAlchemyBase, BaseMixins):
    __tablename__ = "ingredient_foods_aliases"
    id: FilterableColumn[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)

    food_id: FilterableColumn[GUID] = mapped_column(
        GUID, ForeignKey("ingredient_foods.id"), primary_key=True, index=True
    )
    food: Mapped[IngredientFoodModel] = orm.relationship("IngredientFoodModel", back_populates="aliases")

    name: FilterableColumn[str] = mapped_column(String)

    # Automatically updated by sqlalchemy event, do not write to this manually
    name_normalized: FilterableColumn[str | None] = mapped_column(sa.String, index=True)

    @auto_init()
    def __init__(self, session: Session, name: str, **_) -> None:
        self.name_normalized = self.normalize(name)
        tableargs = [
            sa.Index(
                "ix_ingredient_foods_aliases_name_normalized",
                "name_normalized",
                unique=False,
            ),
        ]

        if session.get_bind().name == "postgresql":
            tableargs.extend(
                [
                    sa.Index(
                        "ix_ingredient_foods_aliases_name_normalized_gin",
                        "name_normalized",
                        unique=False,
                        postgresql_using="gin",
                        postgresql_ops={
                            "name_normalized": "gin_trgm_ops",
                        },
                    ),
                ]
            )

        self.__table_args__ = tableargs


class IngredientFoodSubstitutionModel(SqlAlchemyBase, BaseMixins):
    """
    A directed "this food may be replaced by that one" substitution.

    Both the substitute food and the note are optional, but at least one must be
    present: a substitution can be another food ("chicken broth"), a free-text
    workaround ("water and a bouillon cube"), or a food with a caveat attached.
    """

    __tablename__ = "ingredient_foods_substitutions"
    # No uniqueness on (food_id, substitute_food_id): combinations sharing their first food
    # ("butter + flour", "butter + oil") coexist; resolve_substitutions dedupes on the full set of foods.
    __table_args__ = (
        sa.CheckConstraint("food_id != substitute_food_id", name="ingredient_foods_substitutions_no_self_substitution"),
        sa.CheckConstraint(
            "substitute_food_id IS NOT NULL OR note IS NOT NULL",
            name="ingredient_foods_substitutions_food_or_note",
        ),
    )

    id: FilterableColumn[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)

    food_id: FilterableColumn[GUID] = mapped_column(GUID, ForeignKey("ingredient_foods.id"), index=True, nullable=False)
    food: Mapped[IngredientFoodModel] = orm.relationship(
        "IngredientFoodModel", back_populates="substitutions", foreign_keys=[food_id]
    )

    substitute_food_id: FilterableColumn[GUID | None] = mapped_column(
        GUID, ForeignKey("ingredient_foods.id"), index=True
    )
    substitute_food: Mapped[IngredientFoodModel | None] = orm.relationship(
        "IngredientFoodModel", back_populates="substitution_references", foreign_keys=[substitute_food_id]
    )

    note: FilterableColumn[str | None] = mapped_column(String)

    additional_foods: Mapped[list[IngredientFoodModel]] = orm.relationship(
        "IngredientFoodModel",
        secondary=ingredient_foods_substitutions_additional_foods,
        back_populates="substitution_combinations",
    )

    # note-only substitutions have no name to sort by, so display order is stored
    position: FilterableColumn[int | None] = mapped_column(Integer, index=True)

    @property
    def additional_food_ids(self) -> list[GUID]:
        return [food.id for food in self.additional_foods]


class IngredientFoodNutritionModel(SqlAlchemyBase, BaseMixins):
    """
    Nutrition facts of a food, per 100 g (or 100 ml for liquids).
    Values are stored as strings, like recipe nutrition.
    """

    __tablename__ = "ingredient_foods_nutrition"

    NUTRITION_FIELDS = (
        "calories",
        "carbohydrate_content",
        "cholesterol_content",
        "fat_content",
        "fiber_content",
        "protein_content",
        "saturated_fat_content",
        "sodium_content",
        "sugar_content",
        "trans_fat_content",
        "unsaturated_fat_content",
        "calcium_content",
        "iron_content",
        "magnesium_content",
        "potassium_content",
        "vitamin_a_content",
        "vitamin_c_content",
        "vitamin_d_content",
    )

    id: FilterableColumn[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)

    food_id: FilterableColumn[GUID] = mapped_column(
        GUID, ForeignKey("ingredient_foods.id"), index=True, unique=True, nullable=False
    )
    food: Mapped[IngredientFoodModel] = orm.relationship("IngredientFoodModel", back_populates="nutrition")

    calories: FilterableColumn[str | None] = mapped_column(String)
    carbohydrate_content: FilterableColumn[str | None] = mapped_column(String)
    cholesterol_content: FilterableColumn[str | None] = mapped_column(String)
    fat_content: FilterableColumn[str | None] = mapped_column(String)
    fiber_content: FilterableColumn[str | None] = mapped_column(String)
    protein_content: FilterableColumn[str | None] = mapped_column(String)
    saturated_fat_content: FilterableColumn[str | None] = mapped_column(String)
    sodium_content: FilterableColumn[str | None] = mapped_column(String)
    sugar_content: FilterableColumn[str | None] = mapped_column(String)
    trans_fat_content: FilterableColumn[str | None] = mapped_column(String)
    unsaturated_fat_content: FilterableColumn[str | None] = mapped_column(String)
    calcium_content: FilterableColumn[str | None] = mapped_column(String)
    iron_content: FilterableColumn[str | None] = mapped_column(String)
    magnesium_content: FilterableColumn[str | None] = mapped_column(String)
    potassium_content: FilterableColumn[str | None] = mapped_column(String)
    vitamin_a_content: FilterableColumn[str | None] = mapped_column(String)
    vitamin_c_content: FilterableColumn[str | None] = mapped_column(String)
    vitamin_d_content: FilterableColumn[str | None] = mapped_column(String)


class IngredientFoodNutritionLogModel(SqlAlchemyBase, BaseMixins):
    """History of the AI nutrition estimates of a food: the raw answers, the retries and the corrections"""

    __tablename__ = "ingredient_foods_nutrition_logs"

    id: FilterableColumn[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    group_id: FilterableColumn[GUID] = mapped_column(GUID, ForeignKey("groups.id"), nullable=False, index=True)
    food_id: FilterableColumn[GUID] = mapped_column(
        GUID, ForeignKey("ingredient_foods.id", ondelete="CASCADE"), nullable=False, index=True
    )
    food: Mapped[IngredientFoodModel] = orm.relationship("IngredientFoodModel", back_populates="nutrition_logs")

    origin: Mapped[str] = mapped_column(String, nullable=False)
    ai_model: Mapped[str | None] = mapped_column(String)
    steps: Mapped[list | None] = mapped_column(sa.JSON)
    corrections: Mapped[list | None] = mapped_column(sa.JSON)
    result: Mapped[dict | None] = mapped_column(sa.JSON)
    error: Mapped[str | None] = mapped_column(String)

    @auto_init()
    def __init__(self, **_) -> None:
        pass


class RecipeIngredientModel(SqlAlchemyBase, BaseMixins):
    __tablename__ = "recipes_ingredients"
    id: FilterableColumn[int] = mapped_column(Integer, primary_key=True)
    position: FilterableColumn[int | None] = mapped_column(Integer, index=True)
    recipe_id: FilterableColumn[GUID | None] = mapped_column(GUID, ForeignKey("recipes.id"), index=True)

    title: FilterableColumn[str | None] = mapped_column(String)  # Section Header - Shows if Present
    note: FilterableColumn[str | None] = mapped_column(String)  # Force Show Text - Overrides Concat

    # Scaling Items
    unit_id: FilterableColumn[GUID | None] = mapped_column(GUID, ForeignKey("ingredient_units.id"), index=True)
    unit: Mapped[IngredientUnitModel | None] = orm.relationship(IngredientUnitModel, uselist=False)

    food_id: FilterableColumn[GUID | None] = mapped_column(GUID, ForeignKey("ingredient_foods.id"), index=True)
    food: Mapped[IngredientFoodModel | None] = orm.relationship(IngredientFoodModel, uselist=False)
    quantity: FilterableColumn[float | None] = mapped_column(Float)

    original_text: FilterableColumn[str | None] = mapped_column(String)

    reference_id: FilterableColumn[GUID | None] = mapped_column(GUID)  # Reference Links

    # Recipe Reference
    referenced_recipe_id: FilterableColumn[GUID | None] = mapped_column(GUID, ForeignKey("recipes.id"), index=True)
    referenced_recipe: Mapped[RecipeModel] = orm.relationship(
        "RecipeModel", back_populates="referenced_ingredients", foreign_keys=[referenced_recipe_id]
    )

    substitutions: Mapped[list[RecipeIngredientSubstitutionModel]] = orm.relationship(
        "RecipeIngredientSubstitutionModel",
        back_populates="ingredient",
        cascade="all, delete, delete-orphan",
        order_by="RecipeIngredientSubstitutionModel.position",
        collection_class=ordering_list("position"),
    )

    # Automatically updated by sqlalchemy event, do not write to this manually
    note_normalized: FilterableColumn[str | None] = mapped_column(String, index=True)
    original_text_normalized: FilterableColumn[str | None] = mapped_column(String, index=True)

    model_config = AutoInitOptions(
        exclude={
            "id",
            # substitutions are resolved explicitly, since auto_init creates rows it can't find
            "substitutions",
        }
    )

    def _set_substitutions(self, session: Session, group_id: GUID | None, substitutions: list[dict] | None) -> None:
        """
        Builds the substitution rows by hand, since auto_init creates any related row it
        fails to look up and would manufacture a food out of an unrecognized id.

        Rows are always built fresh rather than reused, unlike the food tier: ingredient rows
        are destroyed and recreated on every recipe save, so there is never an existing set to
        reconcile with, and no unique constraint for a re-insert to collide with.
        """

        resolved = resolve_substitutions(session, group_id, substitutions)
        additional_foods = _load_foods(session, resolved)
        self.substitutions = [
            RecipeIngredientSubstitutionModel(
                substitute_food_id=substitute_food_id,
                note=note,
                additional_foods=[additional_foods[food_id] for food_id in additional_food_ids],
            )
            for substitute_food_id, note, additional_food_ids in resolved
        ]

    @auto_init()
    def __init__(
        self,
        session: Session,
        note: str | None = None,
        orginal_text: str | None = None,
        group_id: GUID | None = None,
        substitutions: list[dict] | None = None,
        **_,
    ) -> None:
        # SQLAlchemy events do not seem to register things that are set during auto_init
        if note is not None:
            self.note_normalized = self.normalize(note)

        if orginal_text is not None:
            self.orginal_text = self.normalize(orginal_text)

        self._set_substitutions(session, group_id, substitutions)

        tableargs = [  # base set of indices
            sa.Index(
                "ix_recipes_ingredients_note_normalized",
                "note_normalized",
                unique=False,
            ),
            sa.Index(
                "ix_recipes_ingredients_original_text_normalized",
                "original_text_normalized",
                unique=False,
            ),
        ]
        if session.get_bind().name == "postgresql":
            tableargs.extend(
                [
                    sa.Index(
                        "ix_recipes_ingredients_note_normalized_gin",
                        "note_normalized",
                        unique=False,
                        postgresql_using="gin",
                        postgresql_ops={
                            "note_normalized": "gin_trgm_ops",
                        },
                    ),
                    sa.Index(
                        "ix_recipes_ingredients_original_text_normalized_gin",
                        "original_text",
                        unique=False,
                        postgresql_using="gin",
                        postgresql_ops={
                            "original_text_normalized": "gin_trgm_ops",
                        },
                    ),
                ]
            )
        # add indices
        self.__table_args__ = tuple(tableargs)


class RecipeIngredientSubstitutionModel(SqlAlchemyBase, BaseMixins):
    """
    A substitution scoped to one ingredient line on one recipe.

    Structurally identical to IngredientFoodSubstitutionModel, but the left side is an
    ingredient row rather than a food. There is no unique constraint: ingredient rows are
    rebuilt from scratch on every recipe save, so the write path always starts from an
    empty set and deduping happens in the schema.
    """

    __tablename__ = "recipes_ingredients_substitutions"
    __table_args__ = (
        sa.CheckConstraint(
            "substitute_food_id IS NOT NULL OR note IS NOT NULL",
            name="recipes_ingredients_substitutions_food_or_note",
        ),
    )

    id: FilterableColumn[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)

    # Integer, because recipes_ingredients.id is an autoincrement integer PK
    ingredient_id: FilterableColumn[int] = mapped_column(
        Integer, ForeignKey("recipes_ingredients.id"), index=True, nullable=False
    )
    ingredient: Mapped[RecipeIngredientModel] = orm.relationship(
        "RecipeIngredientModel", back_populates="substitutions"
    )

    substitute_food_id: FilterableColumn[GUID | None] = mapped_column(
        GUID, ForeignKey("ingredient_foods.id"), index=True
    )
    substitute_food: Mapped[IngredientFoodModel | None] = orm.relationship(
        "IngredientFoodModel", back_populates="recipe_substitution_references"
    )

    note: FilterableColumn[str | None] = mapped_column(String)

    additional_foods: Mapped[list[IngredientFoodModel]] = orm.relationship(
        "IngredientFoodModel",
        secondary=recipes_ingredients_substitutions_additional_foods,
        back_populates="recipe_substitution_combinations",
    )

    # note-only substitutions have no name to sort by, so display order is stored
    position: FilterableColumn[int | None] = mapped_column(Integer, index=True)

    @property
    def additional_food_ids(self) -> list[GUID]:
        return [food.id for food in self.additional_foods]


def _load_foods(session: Session, resolved: list[ResolvedSubstitution]) -> dict[GUID, IngredientFoodModel]:
    food_ids = {food_id for _, _, additional_food_ids in resolved for food_id in additional_food_ids}
    if not food_ids:
        return {}

    foods = session.query(IngredientFoodModel).filter(IngredientFoodModel.id.in_(food_ids)).all()
    return {food.id: food for food in foods}


@event.listens_for(IngredientUnitModel.name, "set")
def receive_unit_name(target: IngredientUnitModel, value: str | None, oldvalue, initiator):
    if value is not None:
        target.name_normalized = IngredientUnitModel.normalize(value)
    else:
        target.name_normalized = None


@event.listens_for(IngredientUnitModel.plural_name, "set")
def receive_plural_unit_name(target: IngredientUnitModel, value: str | None, oldvalue, initiator):
    if value is not None:
        target.plural_name_normalized = IngredientUnitModel.normalize(value)
    else:
        target.plural_name_normalized = None


@event.listens_for(IngredientUnitModel.abbreviation, "set")
def receive_unit_abbreviation(target: IngredientUnitModel, value: str | None, oldvalue, initiator):
    if value is not None:
        target.abbreviation_normalized = IngredientUnitModel.normalize(value)
    else:
        target.abbreviation_normalized = None


@event.listens_for(IngredientUnitModel.plural_abbreviation, "set")
def receive_unit_plural_abbreviation(target: IngredientUnitModel, value: str | None, oldvalue, initiator):
    if value is not None:
        target.plural_abbreviation_normalized = IngredientUnitModel.normalize(value)
    else:
        target.plural_abbreviation_normalized = None


@event.listens_for(IngredientFoodModel.name, "set")
def receive_food_name(target: IngredientFoodModel, value: str | None, oldvalue, initiator):
    if value is not None:
        target.name_normalized = IngredientFoodModel.normalize(value)
    else:
        target.name_normalized = None


@event.listens_for(IngredientFoodModel.plural_name, "set")
def receive_food_plural_name(target: IngredientFoodModel, value: str | None, oldvalue, initiator):
    if value is not None:
        target.plural_name_normalized = IngredientFoodModel.normalize(value)
    else:
        target.plural_name_normalized = None


@event.listens_for(IngredientUnitAliasModel.name, "set")
def receive_unit_alias_name(target: IngredientUnitAliasModel, value: str, oldvalue, initiator):
    target.name_normalized = IngredientUnitAliasModel.normalize(value)


@event.listens_for(IngredientFoodAliasModel.name, "set")
def receive_food_alias_name(target: IngredientFoodAliasModel, value: str, oldvalue, initiator):
    target.name_normalized = IngredientFoodAliasModel.normalize(value)


@event.listens_for(RecipeIngredientModel.note, "set")
def receive_ingredient_note(target: RecipeIngredientModel, value: str | None, oldvalue, initiator):
    if value is not None:
        target.note_normalized = RecipeIngredientModel.normalize(value)
    else:
        target.note_normalized = None


@event.listens_for(RecipeIngredientModel.original_text, "set")
def receive_ingredient_original_text(target: RecipeIngredientModel, value: str | None, oldvalue, initiator):
    if value is not None:
        target.original_text_normalized = RecipeIngredientModel.normalize(value)
    else:
        target.original_text_normalized = None
