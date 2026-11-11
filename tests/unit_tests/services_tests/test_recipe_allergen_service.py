from uuid import uuid4

from mealie.schema.allergens.allergen import AllergenOut, AllergenSummary
from mealie.schema.recipe.recipe import RecipeOut
from mealie.schema.recipe.recipe_ingredient import IngredientFoodCreate, RecipeIngredient
from mealie.services.recipe.food_allergen_service import FoodAllergenItem, FoodAllergenService
from mealie.services.recipe.recipe_allergen_service import RecipeAllergenService, normalize, split_terms


def _allergen(name: str, keywords: str = "", exclusions: str = "") -> AllergenOut:
    return AllergenOut(
        id=uuid4(), group_id=uuid4(), name=name, code=name.lower(), keywords=keywords, exclusions=exclusions
    )


def _summary(allergen: AllergenOut) -> AllergenSummary:
    return AllergenSummary(id=allergen.id, name=allergen.name, code=allergen.code)


def _recipe(*ingredients: RecipeIngredient) -> RecipeOut:
    return RecipeOut(
        id=uuid4(),
        name="Test",
        slug="test",
        user_id=uuid4(),
        household_id=uuid4(),
        group_id=uuid4(),
        recipe_ingredient=list(ingredients),
    )


def _service() -> RecipeAllergenService:
    return RecipeAllergenService.__new__(RecipeAllergenService)


def test_normalize_removes_accents_and_plurals():
    assert normalize("Œufs frais, Crème!") == "oeuf frais creme"
    assert split_terms("Lait, beurre\nCrème ; ") == ["lait", "beurre", "creme"]


def test_detects_only_the_allergens_linked_to_the_foods():
    milk = _allergen("Lait", "lait, beurre")
    nuts = _allergen("Fruits à coque", "noix, amande")
    butter = IngredientFoodCreate(name="Beurre", allergens=[_summary(milk)])
    almond = IngredientFoodCreate(name="Amande", allergens=[_summary(nuts), _summary(milk)])
    recipe = _recipe(
        RecipeIngredient(food=butter, note="doux"),
        RecipeIngredient(food=almond),
        RecipeIngredient(food=butter),
        # keywords alone never bring an allergen anymore
        RecipeIngredient(note="200 g de beurre", original_text="200 g de beurre"),
        RecipeIngredient(food=IngredientFoodCreate(name="Lait de vache")),
    )

    found = _service().detect(recipe)

    assert [(a.name, a.ingredients) for a in found] == [
        ("Fruits à coque", ["Amande"]),
        ("Lait", ["Beurre", "Amande"]),
    ]
    assert _service().name_finder()(recipe) == ["Fruits à coque", "Lait"]


def test_no_allergen_when_no_food_is_linked():
    recipe = _recipe(RecipeIngredient(note="lait"), RecipeIngredient(food=IngredientFoodCreate(name="Beurre")))
    assert _service().detect(recipe) == []


def test_food_keyword_match_applies_exclusions():
    milk = _allergen("Lait", "lait, beurre, crème", "lait de coco, noix de beurre")
    nuts = _allergen("Fruits à coque", "noix, amande", "noix de coco, noix de beurre")
    allergens = [milk, nuts]

    def names(item: FoodAllergenItem) -> list[str]:
        return [a.name for a in FoodAllergenService.keyword_match(item, allergens)]

    assert names(FoodAllergenItem("Beurre doux")) == ["Lait"]
    assert names(FoodAllergenItem("Noix de coco râpée")) == []
    assert names(FoodAllergenItem("Lait de coco")) == []
    assert names(FoodAllergenItem("Poudre", aliases=["amandes en poudre"])) == ["Fruits à coque"]
    assert names(FoodAllergenItem("Laitue")) == []
