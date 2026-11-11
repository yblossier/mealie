import pathlib
from collections.abc import Generator
from functools import cached_property

from mealie.lang.locale_config import resolve_food_plural, resolve_plural
from mealie.schema.allergens.allergen import AllergenSave, AllergenUpdate
from mealie.schema.labels import MultiPurposeLabelOut, MultiPurposeLabelSave
from mealie.schema.recipe.recipe_ingredient import (
    IngredientFoodOut,
    IngredientFoodSave,
    IngredientUnitOut,
    IngredientUnitSave,
)
from mealie.services.group_services.labels_service import MultiPurposeLabelService

from ._abstract_seeder import AbstractSeeder
from .resources import allergens, foods, units


class IngredientUnitsSeeder(AbstractSeeder):
    @classmethod
    def get_file(cls, locale: str | None = None) -> pathlib.Path:
        locale_path = cls.resources / "units" / "locales" / f"{locale}.json"
        return locale_path if locale_path.exists() else units.en_US

    def get_all_units(self) -> list[IngredientUnitOut]:
        return self.repos.ingredient_units.get_all()

    def load_data(self, locale: str | None = None) -> Generator[IngredientUnitSave]:
        file = self.get_file(locale)

        seen_unit_names = {unit.name for unit in self.get_all_units()}
        for key, unit in self.load_file(file).items():
            if unit["name"] in seen_unit_names:
                continue

            seen_unit_names.add(unit["name"])

            # an unrecognized key has nothing to compare against, so treat it as untranslated
            source = self.source_data.get(key, unit)
            yield IngredientUnitSave(
                group_id=self.repos.group_id,
                name=unit["name"],
                plural_name=resolve_plural(
                    source_singular=source["name"],
                    source_plural=source.get("plural_name"),
                    singular=unit["name"],
                    plural=unit.get("plural_name"),
                ),
                description=unit["description"],
                abbreviation=unit["abbreviation"],
                plural_abbreviation=resolve_plural(
                    source_singular=source["abbreviation"],
                    source_plural=source.get("plural_abbreviation"),
                    singular=unit["abbreviation"],
                    plural=unit.get("plural_abbreviation"),
                ),
            )

    def seed(self, locale: str | None = None) -> None:
        self.logger.info("Seeding Ingredient Units")
        for unit in self.load_data(locale):
            try:
                self.repos.ingredient_units.create(unit)
            except Exception as e:
                self.logger.error(e)


class IngredientFoodsSeeder(AbstractSeeder):
    """Seeds both the foods and the labels that group them, from a single locale file."""

    @cached_property
    def label_service(self) -> MultiPurposeLabelService:
        return MultiPurposeLabelService(self.repos)

    @classmethod
    def get_file(cls, locale: str | None = None) -> pathlib.Path:
        locale_path = cls.resources / "foods" / "locales" / f"{locale}.json"
        return locale_path if locale_path.exists() else foods.en_US

    def get_label(self, value: str) -> MultiPurposeLabelOut | None:
        return self.repos.group_multi_purpose_labels.get_one(value, "name")

    def get_all_foods(self) -> list[IngredientFoodOut]:
        return self.repos.ingredient_foods.get_all()

    def seed_labels(self, locale: str | None = None) -> None:
        """Create any labels from the seed file that don't already exist in the group."""
        seen_label_names = {label.name for label in self.repos.group_multi_purpose_labels.get_all()}
        for label in self.load_file(self.get_file(locale)).values():
            name = label["name"]
            if not name or name in seen_label_names:
                continue

            seen_label_names.add(name)
            try:
                self.label_service.create_one(MultiPurposeLabelSave(name=name, group_id=self.repos.group_id))
            except Exception as e:
                self.logger.error(e)

    def load_data(self, locale: str | None = None) -> Generator[IngredientFoodSave]:
        file = self.get_file(locale)

        # de-duplicate on the localized name rather than the English seed key, otherwise seeding
        # a second locale skips every food whose English key already exists in the group
        seen_foods_names = {food.name for food in self.get_all_foods()}
        for label_key, values in self.load_file(file).items():
            label_out = self.get_label(values["name"])
            source_foods = self.source_data.get(label_key, {}).get("foods", {})

            for food_key, attributes in values["foods"].items():
                name = attributes["name"]
                if name in seen_foods_names:
                    continue

                seen_foods_names.add(name)

                # an unrecognized key has nothing to compare against, so treat it as untranslated
                source = source_foods.get(food_key, attributes)
                yield IngredientFoodSave(
                    group_id=self.repos.group_id,
                    name=name,
                    plural_name=resolve_food_plural(
                        source_singular=source["name"],
                        source_plural=source.get("plural_name"),
                        singular=name,
                        plural=attributes.get("plural_name"),
                        locale=locale,
                    ),
                    description="",  # description expected to be empty string by UnitFoodBase class
                    label_id=label_out.id if label_out and label_out.id else None,
                )

    def seed(self, locale: str | None = None) -> None:
        self.logger.info("Seeding Ingredient Foods")
        # labels must exist before foods so each food can be linked to its label
        self.seed_labels(locale)

        to_seed = list(self.load_data(locale))
        if not to_seed:
            return

        try:
            self.repos.ingredient_foods.create_many(to_seed)
        except Exception:
            self.logger.exception("Failed to seed ingredient foods in bulk, falling back to one at a time")
            for food in to_seed:
                try:
                    self.repos.ingredient_foods.create(food)
                except Exception as e:
                    self.logger.error(e)


def _merge_terms(existing: str, new: list[str]) -> str:
    terms = [term.strip() for term in existing.split(",") if term.strip()]
    known = {term.lower() for term in terms}
    terms += [term for term in new if term.lower() not in known]
    return ", ".join(terms)


class AllergensSeeder(AbstractSeeder):
    """
    Seeds the 14 major allergens of Regulation (EU) No 1169/2011, Annex II. Allergens already in the
    group (recognized by their code, or by their name) keep their edits and only gain the missing keywords.
    """

    @classmethod
    def get_file(cls, locale: str | None = None) -> pathlib.Path:
        return allergens.allergens

    @staticmethod
    def pick_locale(locales: dict[str, dict], locale: str | None) -> dict | None:
        lang = (locale or "en").split("-")[0].lower()
        return locales.get(lang) or locales.get("en")

    def seed(self, locale: str | None = None) -> None:
        self.logger.info("Seeding Allergens")
        repo = self.repos.group_allergens
        existing = repo.get_all()
        by_code = {allergen.code: allergen for allergen in existing if allergen.code}
        by_name = {allergen.name.lower(): allergen for allergen in existing}

        for code, data in self.load_file(self.get_file(locale))["allergens"].items():
            values = self.pick_locale(data["locales"], locale)
            if not values:
                continue

            current = by_code.get(code) or by_name.get(values["name"].lower())
            try:
                if current:
                    repo.update(
                        current.id,
                        AllergenUpdate(
                            id=current.id,
                            group_id=self.repos.group_id,
                            name=current.name,
                            code=current.code or code,
                            keywords=_merge_terms(current.keywords, values["keywords"]),
                            exclusions=_merge_terms(current.exclusions, values["exclusions"]),
                        ),
                    )
                else:
                    repo.create(
                        AllergenSave(
                            group_id=self.repos.group_id,
                            code=code,
                            name=values["name"],
                            keywords=", ".join(values["keywords"]),
                            exclusions=", ".join(values["exclusions"]),
                        )
                    )
            except Exception as e:
                self.logger.error(e)
