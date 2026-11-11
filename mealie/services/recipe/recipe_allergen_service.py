import re
from collections.abc import Callable

from pydantic import UUID4
from text_unidecode import unidecode

from mealie.repos.repository_factory import AllRepositories
from mealie.schema.allergens.allergen import AllergenSummary, RecipeAllergen
from mealie.schema.recipe.recipe import RecipeOut
from mealie.schema.recipe.recipe_ingredient import RecipeIngredient
from mealie.services._base_service import BaseService


def _singular(word: str) -> str:
    if len(word) <= 3:
        return word
    if word[-1] in "sx" and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def normalize(text: str | None) -> str:
    """Lowercase, unaccented, singular words separated by single spaces"""
    words = re.sub(r"[^a-z0-9]+", " ", unidecode(text or "").lower()).split()
    return " ".join(_singular(word) for word in words)


def split_terms(terms: str | None) -> list[str]:
    return [normalized for term in re.split(r"[,\n;]", terms or "") if (normalized := normalize(term))]


class RecipeAllergenService(BaseService):
    """
    Lists the allergens of a recipe: an allergen is present only when it is linked to the food of one of
    the recipe's ingredients. Ingredients without a food, or whose food is linked to no allergen, bring none.
    """

    def __init__(self, repos: AllRepositories):
        self.repos = repos
        super().__init__()

    @staticmethod
    def linked_allergens(ingredient: RecipeIngredient) -> list[AllergenSummary]:
        """The allergens set by hand (or by the matching) on the food of the ingredient"""
        if not ingredient.food:
            return []
        return list(getattr(ingredient.food, "allergens", None) or [])

    @staticmethod
    def ingredient_label(ingredient: RecipeIngredient) -> str:
        if ingredient.food:
            return ingredient.food.name
        return (ingredient.note or ingredient.display or ingredient.original_text or "").strip()

    def detect(self, recipe: RecipeOut) -> list[RecipeAllergen]:
        found: dict[UUID4, RecipeAllergen] = {}
        for ingredient in recipe.recipe_ingredient:
            label = self.ingredient_label(ingredient)
            for allergen in self.linked_allergens(ingredient):
                entry = found.setdefault(
                    allergen.id,
                    RecipeAllergen(allergen_id=allergen.id, code=allergen.code, name=allergen.name, ingredients=[]),
                )
                if label and label not in entry.ingredients:
                    entry.ingredients.append(label)

        return sorted(found.values(), key=lambda allergen: allergen.name.lower())

    def name_finder(self) -> Callable[[RecipeOut], list[str]]:
        """Names of the allergens linked to the foods of a recipe"""

        def find(recipe: RecipeOut) -> list[str]:
            return [allergen.name for allergen in self.detect(recipe)]

        return find
