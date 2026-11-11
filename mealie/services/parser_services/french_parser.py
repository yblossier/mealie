"""French path of the NLP and brute force parsers: rule-based parsing plus database matching."""

from mealie.db.models.recipe.ingredient import IngredientFoodModel, IngredientUnitModel
from mealie.lang.providers import get_locale_context
from mealie.schema.recipe import RecipeIngredient
from mealie.schema.recipe.recipe_ingredient import (
    IngredientConfidence,
    IngredientFoodCreate,
    IngredientFoodOut,
    IngredientUnitCreate,
    IngredientUnitOut,
    ParsedIngredient,
    RecipeIngredientSubstitution,
)

from ._base import ABCIngredientParser, DataMatcher
from .parser_utils.french import (
    FrenchParsedIngredient,
    is_french_ingredient,
    parse_french_ingredient,
    singular_candidates,
)

QUANTITY_CONFIDENCE = 1.0
UNIT_CONFIDENCE = 0.9
"""A unit from the French unit table that is not in the database"""
FOOD_CONFIDENCE = 0.75
"""A food that is not in the database"""
NOTE_CONFIDENCE = 0.9
FUZZY_UNIT_THRESHOLD = 85


def get_request_locale() -> str | None:
    if context := get_locale_context():
        return context[1].key
    return None


def should_parse_as_french(ingredient_string: str, locale: str | None = None) -> bool:
    return is_french_ingredient(ingredient_string, locale or get_request_locale())


def _find_exact_food(matcher: DataMatcher, name: str) -> IngredientFoodOut | None:
    for candidate in [name, *singular_candidates(name)]:
        if food := matcher.foods_by_alias.get(IngredientFoodModel.normalize(candidate)):
            return food
    return None


def _find_unit(matcher: DataMatcher, parsed: FrenchParsedIngredient) -> IngredientUnitOut | None:
    if not parsed.unit:
        return None

    for candidate in [parsed.unit_text, *parsed.unit.match_candidates]:
        if unit := matcher.units_by_alias.get(IngredientUnitModel.normalize(candidate)):
            return unit

    # stricter than the default unit threshold: short French unit names are close to each other ("boîte"/"botte")
    return matcher.find_match(
        IngredientUnitModel.normalize(parsed.unit.name),
        store_map=matcher.units_by_alias,
        fuzzy_match_threshold=FUZZY_UNIT_THRESHOLD,
    )


def _find_food(matcher: DataMatcher, name: str) -> IngredientFoodOut | None:
    return _find_exact_food(matcher, name) or matcher.find_food_match(name)


def _convert_alternatives(matcher: DataMatcher, alternatives: list[str]) -> list[RecipeIngredientSubstitution]:
    substitutions: list[RecipeIngredientSubstitution] = []
    for alternative in alternatives:
        if food := _find_food(matcher, alternative):
            substitutions.append(RecipeIngredientSubstitution(substitute_food_id=food.id))
        else:
            substitutions.append(RecipeIngredientSubstitution(note=alternative))
    return substitutions


def parse_french(parser: ABCIngredientParser, ingredient_string: str) -> ParsedIngredient:
    matcher = parser.data_matcher
    parsed = parse_french_ingredient(ingredient_string)

    unit: IngredientUnitOut | IngredientUnitCreate | None = None
    if parsed.unit:
        unit = _find_unit(matcher, parsed) or IngredientUnitCreate(name=parsed.unit.name)

    food: IngredientFoodOut | IngredientFoodCreate | None = None
    if parsed.food:
        # a food stored with its preparation ("tomates concassées") wins over the split
        if parsed.preparation and (food := _find_exact_food(matcher, f"{parsed.food} {parsed.preparation}")):
            parsed.preparation = ""
        else:
            food = _find_food(matcher, parsed.food) or IngredientFoodCreate(name=parsed.food)

    ingredient = RecipeIngredient(
        original_text=ingredient_string,
        quantity=parsed.quantity,
        unit=unit,
        food=food,
        note=parsed.note,
    )
    if parsed.alternatives:
        ingredient.substitutions = _convert_alternatives(matcher, parsed.alternatives)

    result = ParsedIngredient(input=ingredient_string, ingredient=ingredient)

    qty_conf = QUANTITY_CONFIDENCE if parsed.has_quantity else 0
    unit_conf = (1.0 if isinstance(unit, IngredientUnitOut) else UNIT_CONFIDENCE) if unit else 0
    food_conf = (1.0 if isinstance(food, IngredientFoodOut) else FOOD_CONFIDENCE) if food else 0
    note_conf = NOTE_CONFIDENCE if parsed.note else 0

    confidences = [
        conf
        for conf, present in [
            (qty_conf, parsed.has_quantity),
            (unit_conf, bool(unit)),
            (food_conf, bool(food)),
            (note_conf, bool(parsed.note)),
        ]
        if present
    ]
    result.confidence = IngredientConfidence(
        average=sum(confidences) / len(confidences) if confidences else 0,
        quantity=qty_conf,
        unit=unit_conf,
        food=food_conf,
        comment=note_conf,
    )
    return result
