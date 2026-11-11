from __future__ import annotations

import datetime
import enum
from enum import StrEnum
from fractions import Fraction
from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import UUID4, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.interfaces import LoaderOption

from mealie.db.models.recipe import IngredientFoodModel, IngredientFoodSubstitutionModel, IngredientUnitModel
from mealie.lang.locale_config import LocalePluralFoodHandling
from mealie.lang.providers import get_locale_context
from mealie.schema._mealie import MealieModel
from mealie.schema._mealie.mealie_model import MealieOutModel, UpdatedAtField
from mealie.schema._mealie.types import NoneFloat
from mealie.schema.allergens.allergen import AllergenSummary
from mealie.schema.recipe.recipe import RecipeDraft
from mealie.schema.recipe.recipe_nutrition import Nutrition
from mealie.schema.response.pagination import PaginationBase

INGREDIENT_QTY_PRECISION = 3
MAX_INGREDIENT_DENOMINATOR = 32

SUPERSCRIPT = dict(zip("1234567890", "¹²³⁴⁵⁶⁷⁸⁹⁰", strict=False))
SUBSCRIPT = dict(zip("1234567890", "₁₂₃₄₅₆₇₈₉₀", strict=False))


def display_fraction(fraction: Fraction):
    return (
        "".join([SUPERSCRIPT[c] for c in str(fraction.numerator)])
        + "/"
        + "".join([SUBSCRIPT[c] for c in str(fraction.denominator)])
    )


class StandardizedUnitType(StrEnum):
    """
    An arbitrary list of standardized units supported by unit conversions.
    The backend doesn't really care what standardized unit you use, as long as it's recognized,
    but defining them here keeps it consistant with the frontend.
    """

    # Imperial
    FLUID_OUNCE = "fluid_ounce"
    CUP = "cup"

    OUNCE = "ounce"
    POUND = "pound"

    # Metric
    MILLILITER = "milliliter"
    LITER = "liter"

    GRAM = "gram"
    KILOGRAM = "kilogram"


class UnitFoodBase(MealieModel):
    id: UUID4 | None = None
    name: str
    plural_name: str | None = None
    description: str = ""
    extras: dict | None = {}

    @field_validator("id", mode="before")
    def convert_empty_id_to_none(cls, v):
        # sometimes the frontend will give us an empty string instead of null, so we convert it to None,
        # otherwise Pydantic will try to convert it to a UUID and fail
        if not v:
            v = None

        return v

    @field_validator("description", mode="before")
    def convert_none_description_to_empty(cls, v):
        return "" if v is None else v

    @field_validator("extras", mode="before")
    def convert_extras_to_dict(cls, v):
        if isinstance(v, dict):
            return v

        return {x.key_name: x.value for x in v} if v else {}


class IngredientFoodAliasCreate(MealieModel):
    name: str


class IngredientFoodAlias(IngredientFoodAliasCreate):
    model_config = ConfigDict(from_attributes=True)


class IngredientFoodSummary(MealieOutModel):
    """
    A trimmed projection of a food, with nothing on it that can recurse.

    Substitutions reference this rather than the full IngredientFoodOut, which would make
    Pydantic walk food -> substitutions -> food forever and generate an equally circular
    TypeScript type.
    """

    id: UUID4
    name: str
    plural_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SubstitutionBase(MealieModel):
    """
    One "may be replaced by" substitution. The substitute food and the note are independently
    optional, but at least one must be present, so a substitution may be another food
    ("chicken broth"), free text ("water and a bouillon cube"), or a food with a caveat.

    A combination of foods ("butter + flour") keeps its first food in substitute_food_id and
    the others in additional_food_ids, the note then telling how to combine them.
    """

    substitute_food_id: UUID4 | None = None
    additional_food_ids: list[UUID4] = []
    note: str | None = None

    @field_validator("additional_food_ids", mode="before")
    def remove_empty_additional_food_ids(cls, v):
        return [food_id for food_id in v if food_id] if isinstance(v, list) else v or []

    @field_validator("substitute_food_id", mode="before")
    def convert_empty_id_to_none(cls, v):
        # the frontend sometimes sends an empty string rather than null
        return v or None

    @field_validator("note", mode="before")
    def convert_blank_note_to_none(cls, v):
        return (v.strip() or None) if isinstance(v, str) else v

    @model_validator(mode="after")
    def validate_not_empty(self):
        if not self.substitute_food_id and not self.note:
            raise ValueError("a substitution must have a substitute food, a note, or both")

        return self

    @staticmethod
    def prune(value: Any) -> Any:
        """
        Drops empty substitutions and de-dupes them by their whole set of foods, keeping the first:
        "butter + flour" and "butter + oil" are two substitutions, "butter" alone a third one.

        Parents call this before their substitutions validate, because an empty row is a UI
        artifact rather than a client bug, and validate_not_empty rejects it outright.
        """

        if not isinstance(value, list):
            return value

        pruned = []
        seen_combinations: set[frozenset[str]] = set()
        for substitution in value:
            if isinstance(substitution, dict):
                food_id = substitution.get("substituteFoodId", substitution.get("substitute_food_id"))
                additional_food_ids = substitution.get("additionalFoodIds", substitution.get("additional_food_ids"))
                note = substitution.get("note")
            else:
                food_id = getattr(substitution, "substitute_food_id", None)
                additional_food_ids = getattr(substitution, "additional_food_ids", None)
                note = getattr(substitution, "note", None)

            if isinstance(note, str):
                note = note.strip()

            if not food_id and not note:
                continue

            if food_id:
                # note-only substitutions have no id to de-dupe on, and repeated notes are legitimate,
                # so they must not be collapsed together here
                extra_ids = additional_food_ids if isinstance(additional_food_ids, list) else []
                combination = frozenset([str(food_id), *(str(extra) for extra in extra_ids if extra)])
                if combination in seen_combinations:
                    continue

                seen_combinations.add(combination)

            pruned.append(substitution)

        return pruned


class IngredientFoodSubstitutionCreate(SubstitutionBase): ...


class IngredientFoodSubstitution(IngredientFoodSubstitutionCreate):
    substitute_food: IngredientFoodSummary | None = None
    additional_foods: list[IngredientFoodSummary] = []

    model_config = ConfigDict(from_attributes=True)


class RecipeIngredientSubstitutionCreate(SubstitutionBase): ...


class RecipeIngredientSubstitution(RecipeIngredientSubstitutionCreate):
    substitute_food: IngredientFoodSummary | None = None
    additional_foods: list[IngredientFoodSummary] = []

    model_config = ConfigDict(from_attributes=True)


class IngredientFoodNutritionSource(StrEnum):
    ciqual = "ciqual"
    """Anses Ciqual food composition table"""
    usda = "usda"
    """USDA FoodData Central"""
    off = "off"
    """Open Food Facts, the database of packaged products"""
    ai = "ai"
    """Estimated by the AI provider"""


class IngredientFoodCreate(UnitFoodBase):
    label_id: UUID4 | None = None
    aliases: list[IngredientFoodAliasCreate] = []
    substitutions: list[IngredientFoodSubstitutionCreate] = []
    households_with_ingredient_food: list[str] = []
    allergens: list[AllergenSummary] = []
    """Allergens the food contains"""
    nutrition: Nutrition | None = None
    """Nutrition facts per 100 g (or 100 ml)"""
    average_weight: float | None = Field(None, gt=0)
    """Weight in grams of one piece of the food, used for recipe quantities given without a unit"""
    nutrition_source: IngredientFoodNutritionSource | None = None
    """Where the nutrition facts come from; None when they were typed in by hand"""
    nutrition_reference_code: str | None = None
    """Code of the food in the composition table the nutrition facts come from"""
    nutrition_reference_name: str | None = None
    """Name of the food in the composition table the nutrition facts come from"""

    @field_validator("substitutions", mode="before")
    def remove_empty_substitutions(cls, v):
        return SubstitutionBase.prune(v)

    @model_validator(mode="after")
    def validate_no_self_substitution(self):
        if self.id and any(sub.substitute_food_id == self.id for sub in self.substitutions):
            raise ValueError("a food cannot be substituted with itself")

        return self


class IngredientFoodSave(IngredientFoodCreate):
    group_id: UUID4


class IngredientFoodOut(IngredientFoodCreate, MealieOutModel):
    id: UUID4
    label: MultiPurposeLabelSummary | None = None
    aliases: list[IngredientFoodAlias] = []  # type: ignore[assignment]  # narrows the create type's items; list is invariant
    recipe_count: int = 0
    substitutions: list[IngredientFoodSubstitution] = []  # type: ignore[assignment]  # narrows the create type's items; list is invariant

    created_at: datetime.datetime | None = None
    updated_at: datetime.datetime | None = UpdatedAtField(None)

    _searchable_properties: ClassVar[list[str]] = [
        "name_normalized",
        "plural_name_normalized",
    ]
    _normalize_search: ClassVar[bool] = True
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def loader_options(cls) -> list[LoaderOption]:
        return [
            selectinload(IngredientFoodModel.households_with_ingredient_food),
            selectinload(IngredientFoodModel.aliases),
            joinedload(IngredientFoodModel.extras),
            joinedload(IngredientFoodModel.label),
            selectinload(IngredientFoodModel.substitutions).joinedload(IngredientFoodSubstitutionModel.substitute_food),
            selectinload(IngredientFoodModel.substitutions).selectinload(
                IngredientFoodSubstitutionModel.additional_foods
            ),
            selectinload(IngredientFoodModel.allergens),
            selectinload(IngredientFoodModel.nutrition),
        ]

    @field_validator("households_with_ingredient_food", mode="before")
    def convert_households_to_slugs(cls, v):
        if not v:
            return []

        try:
            return [household.slug for household in v]
        except AttributeError:
            return v


class IngredientFoodPagination(PaginationBase):
    items: list[IngredientFoodOut]


class IngredientUnitAliasCreate(MealieModel):
    name: str


class IngredientUnitAlias(IngredientUnitAliasCreate):
    model_config = ConfigDict(from_attributes=True)


class IngredientUnitCreate(UnitFoodBase):
    fraction: bool = True
    abbreviation: str = ""
    plural_abbreviation: str | None = ""
    use_abbreviation: bool = False

    aliases: list[IngredientUnitAliasCreate] = []
    standard_quantity: float | None = None
    standard_unit: str | None = None

    @model_validator(mode="after")
    def validate_standardization_fields(self):
        # If one is set, the other must be set.
        # If quantity is <= 0, it's considered not set.
        if not self.standard_unit:
            self.standard_quantity = self.standard_unit = None
        elif not ((self.standard_quantity or 0) > 0):
            self.standard_quantity = self.standard_unit = None

        return self


class IngredientUnitSave(IngredientUnitCreate):
    group_id: UUID4


class IngredientUnitOut(IngredientUnitCreate, MealieOutModel):
    id: UUID4
    aliases: list[IngredientUnitAlias] = []  # type: ignore[assignment]  # narrows the create type's items; list is invariant

    @classmethod
    def loader_options(cls) -> list[LoaderOption]:
        return [selectinload(IngredientUnitModel.aliases)]

    created_at: datetime.datetime | None = None
    updated_at: datetime.datetime | None = UpdatedAtField(None)

    _searchable_properties: ClassVar[list[str]] = [
        "name_normalized",
        "plural_name_normalized",
        "abbreviation_normalized",
        "plural_abbreviation_normalized",
    ]
    _normalize_search: ClassVar[bool] = True
    model_config = ConfigDict(from_attributes=True)


class RecipeIngredientBase(MealieModel):
    quantity: NoneFloat = 0
    unit: IngredientUnitOut | IngredientUnitCreate | None = None
    food: IngredientFoodOut | IngredientFoodCreate | None = None
    referenced_recipe: RecipeDraft | None = None

    note: str | None = ""
    display: str = ""
    """
    How the ingredient should be displayed

    Automatically calculated after the object is created, unless overwritten
    """

    @model_validator(mode="after")
    def format_display(self):
        if not self.display:
            self.display = self._format_display()

        return self

    @field_validator("unit", mode="before")
    @classmethod
    def validate_unit(cls, v):
        if isinstance(v, str):
            return IngredientUnitCreate(name=v)
        else:
            return v

    @field_validator("food", mode="before")
    @classmethod
    def validate_food(cls, v):
        if isinstance(v, str):
            return IngredientFoodCreate(name=v)
        else:
            return v

    def _format_quantity_for_display(self) -> str:
        """How the quantity should be displayed"""

        qty: float | Fraction

        # decimal
        if self.unit and not self.unit.fraction:
            qty = round(self.quantity or 0, INGREDIENT_QTY_PRECISION)
            if qty.is_integer():
                return str(int(qty))

            else:
                return str(qty)

        # fraction
        qty = Fraction(self.quantity or 0).limit_denominator(MAX_INGREDIENT_DENOMINATOR)
        if qty.denominator == 1:
            return str(qty.numerator)

        if qty.numerator <= qty.denominator:
            return display_fraction(qty)

        # convert an improper fraction into a mixed fraction (e.g. 11/4 --> 2 3/4)
        whole_number = 0
        while qty.numerator > qty.denominator:
            whole_number += 1
            qty -= 1

        return f"{whole_number} {display_fraction(qty)}"

    def _format_unit_for_display(self) -> str:
        if not self.unit:
            return ""

        use_plural = self.quantity and self.quantity > 1
        unit_val = ""
        if self.unit.use_abbreviation:
            if use_plural:
                unit_val = self.unit.plural_abbreviation or self.unit.abbreviation
            else:
                unit_val = self.unit.abbreviation

        if not unit_val:
            if use_plural:
                unit_val = self.unit.plural_name or self.unit.name
            else:
                unit_val = self.unit.name

        return unit_val

    def _format_food_for_display(self, plural_handling: LocalePluralFoodHandling) -> str:
        if not self.food:
            return ""

        if self.quantity and self.quantity <= 1:
            use_plural = False
        else:
            match plural_handling:
                case LocalePluralFoodHandling.NEVER:
                    use_plural = False
                case LocalePluralFoodHandling.WITHOUT_UNIT:
                    # if quantity is zero then unit is not shown even if it's set
                    use_plural = not (self.quantity and self.unit)
                case LocalePluralFoodHandling.ALWAYS:
                    use_plural = True
                case _:
                    use_plural = False

        if use_plural:
            return self.food.plural_name or self.food.name
        else:
            return self.food.name

    def _format_display(self) -> str:
        locale_context = get_locale_context()
        if locale_context:
            _, locale_cfg = locale_context
            plural_food_handling = locale_cfg.plural_food_handling
        else:
            plural_food_handling = LocalePluralFoodHandling.WITHOUT_UNIT

        components: list[str] = []

        if self.quantity:
            components.append(self._format_quantity_for_display())

        if self.quantity and self.unit:
            components.append(self._format_unit_for_display())

        if self.food:
            components.append(self._format_food_for_display(plural_food_handling))

        if self.note:
            components.append(self.note)

        return " ".join(components).strip()


class IngredientUnitPagination(PaginationBase):
    items: list[IngredientUnitOut]


class RecipeIngredient(RecipeIngredientBase):
    title: str | None = None
    original_text: str | None = None

    # kept off RecipeIngredientBase: its only other subclass is ShoppingListItemBase, which has
    # nowhere to store these, so inheriting them would advertise a field that is always empty
    substitutions: list[RecipeIngredientSubstitution] = []

    # Ref is used as a way to distinguish between an individual ingredient on the frontend
    # It is required for the reorder and section titles to function properly because of how
    # Vue handles reactivity. ref may serve another purpose in the future.
    reference_id: UUID = Field(default_factory=uuid4)
    model_config = ConfigDict(from_attributes=True)

    @field_validator("substitutions", mode="before")
    @classmethod
    def remove_empty_substitutions(cls, v):
        return SubstitutionBase.prune(v)

    @field_validator("reference_id", mode="before")
    @classmethod
    def ensure_reference_id(cls, value) -> UUID:
        return value or uuid4()

    @field_validator("quantity", mode="before")
    @classmethod
    def validate_quantity(cls, value) -> NoneFloat:
        """
        Sometimes the frontend UI will provide an empty string as a "null" value because of the default
        bindings in Vue. This validator will ensure that the quantity is set to None if the value is an
        empty string.
        """
        if isinstance(value, float):
            return round(value, INGREDIENT_QTY_PRECISION)
        if value is None or value == "":
            return None
        return value


class IngredientConfidence(MealieModel):
    average: NoneFloat = None
    comment: NoneFloat = None
    name: NoneFloat = None
    unit: NoneFloat = None
    quantity: NoneFloat = None
    food: NoneFloat = None

    @field_validator("quantity", mode="before")
    @classmethod
    def validate_quantity(cls, value, values) -> NoneFloat:
        if isinstance(value, float):
            return round(value, INGREDIENT_QTY_PRECISION)
        if value is None or value == "":
            return None
        return value


class ParsedIngredient(MealieModel):
    input: str | None = None
    confidence: IngredientConfidence = IngredientConfidence()
    ingredient: RecipeIngredient


class RegisteredParser(enum.StrEnum):
    nlp = "nlp"
    brute = "brute"
    openai = "openai"


class IngredientsRequest(MealieModel):
    parser: RegisteredParser = RegisteredParser.nlp
    ingredients: list[str]


class IngredientRequest(MealieModel):
    parser: RegisteredParser = RegisteredParser.nlp
    ingredient: str


class IngredientFoodMerge(MealieModel):
    from_food: UUID4
    to_food: UUID4


class IngredientFoodNutritionEstimateItem(MealieModel):
    id: UUID4 | None = None
    """The food being estimated, if it exists, so the estimate is kept in its history"""
    name: str
    plural_name: str | None = None
    description: str | None = None


class IngredientFoodNutritionEstimateRequest(MealieModel):
    foods: list[IngredientFoodNutritionEstimateItem] = Field(..., min_length=1, max_length=50)


class IngredientFoodNutritionEstimate(MealieOutModel):
    nutrition: Nutrition
    """Nutrition facts per 100 g (or 100 ml)"""
    average_weight: float | None = None
    """Weight in grams of one piece of the food, or None when the food isn't counted by the piece"""
    source: IngredientFoodNutritionSource | None = None
    """Where the nutrition facts come from, or null when the food was found nowhere"""
    reference_code: str | None = None
    """Code of the food in the composition table, when the facts come from one"""
    reference_name: str | None = None


class IngredientFoodNutritionReference(MealieOutModel):
    """A food of a composition table (Ciqual or USDA), with its nutrition facts per 100 g"""

    source: IngredientFoodNutritionSource
    code: str
    name: str
    nutrition: Nutrition
    average_weight: float | None = None


class IngredientFoodNutritionIssue(MealieModel):
    code: str
    """
    One of `name-mismatch`, `missing-values`, `macronutrients-overflow`, `sugar-over-carbohydrates`,
    `fat-details-over-fat` and `energy-mismatch`
    """
    params: dict[str, str | float] = {}

    def __str__(self) -> str:
        params = ", ".join(f"{key}={value}" for key, value in self.params.items())
        return f"{self.code} ({params})" if params else self.code


class IngredientFoodNutritionLogStepKind(StrEnum):
    batch = "batch"
    """The food was asked with others"""
    single = "single"
    """The food was asked on its own, after the answer for the whole list was unusable"""
    retry = "retry"
    """The food was asked again on its own, after an inconsistent answer"""
    lookup = "lookup"
    """The food was looked up in the composition tables (Ciqual, then USDA)"""
    open_food_facts = "open_food_facts"
    """The food was searched in Open Food Facts, after the composition tables"""
    usda = "usda"
    """The food was searched in USDA FoodData Central online, after the composition tables"""
    match = "match"
    """The AI chose the food among the composition tables' candidates"""


class IngredientFoodNutritionLogStep(MealieModel):
    kind: IngredientFoodNutritionLogStepKind
    foods_count: int = 1
    """Number of foods in the request"""
    response: dict[str, Any] | None = None
    """Raw answer of the model for this food"""
    issues: list[IngredientFoodNutritionIssue] = []
    error: str | None = None
    kept: bool = False
    """Whether this answer is the one the result was made from"""


class IngredientFoodNutritionLogCorrection(MealieModel):
    field: str
    before: float | None = None
    after: float | None = None


class IngredientFoodNutritionLogOrigin(StrEnum):
    estimate = "estimate"
    """Estimated from the food form, saved only if the user saves the food"""
    fill = "fill"
    """Estimated and saved at once"""


class IngredientFoodNutritionLogSave(MealieModel):
    group_id: UUID4
    food_id: UUID4
    origin: IngredientFoodNutritionLogOrigin
    ai_model: str | None = None
    """Model of the AI provider that answered"""
    steps: list[IngredientFoodNutritionLogStep] = []
    corrections: list[IngredientFoodNutritionLogCorrection] = []
    result: IngredientFoodNutritionEstimate | None = None
    error: str | None = None


class IngredientFoodNutritionLogOut(IngredientFoodNutritionLogSave, MealieOutModel):
    id: UUID4
    created_at: datetime.datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class IngredientFoodNutritionFillRequest(MealieModel):
    food_ids: list[UUID4] = Field(..., min_length=1, max_length=200)
    overwrite: bool = False
    """When false, foods that already have nutrition facts and an average weight are skipped"""


class IngredientFoodAllergenSuggestRequest(MealieModel):
    name: str
    plural_name: str | None = None
    aliases: list[str] = []
    description: str | None = None


class IngredientFoodAllergenFillRequest(MealieModel):
    food_ids: list[UUID4] | None = None
    """The foods to link with their allergens; every food of the group when not given"""
    overwrite: bool = False
    """Whether to replace the allergens of the foods that already have some"""


class IngredientUnitMerge(MealieModel):
    from_unit: UUID4
    to_unit: UUID4


from mealie.schema.labels.multi_purpose_label import MultiPurposeLabelSummary  # noqa: E402

IngredientFoodOut.model_rebuild()
