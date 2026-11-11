import json
import re

from rapidfuzz import fuzz

from mealie.db.models.recipe.ingredient import IngredientFoodModel
from mealie.schema.openai.recipe_ingredient import OpenAIIngredient, OpenAIIngredients
from mealie.schema.recipe.recipe_ingredient import (
    IngredientConfidence,
    IngredientFoodCreate,
    IngredientUnitCreate,
    ParsedIngredient,
    RecipeIngredient,
    RecipeIngredientSubstitution,
)
from mealie.services.openai import OpenAIDataInjection, OpenAIService

from .._base import ABCIngredientParser
from ..parser_utils import extract_quantity_from_string


class OpenAIParser(ABCIngredientParser):
    MAX_FOOD_REFERENCES = 150

    def _calculate_qty_conf(self, original_text: str, parsed_qty: float | None) -> float:
        """Compares the extracted quantity to a brute-force parsed quantity."""

        expected_qty, _ = extract_quantity_from_string(original_text)
        parsed_qty = parsed_qty or 0
        if parsed_qty == expected_qty:
            return 1
        else:
            return 0

    def _calculate_note_conf(self, original_text: str, note: str | None) -> float:
        """
        Calculate confidence based on how many words in the note are found in the original text.
        Uses alphanumeric filtering and lowercasing to improve matching.
        """

        if not note:
            return 1

        note_words: list[str] = []
        for word in note.strip().lower().split():
            clean_word = "".join(filter(str.isalnum, word))
            if clean_word:
                note_words.append(clean_word)

        if not note_words:
            return 1

        original_words: list[str] = []
        for word in original_text.strip().lower().split():
            clean_word = "".join(filter(str.isalnum, word))
            if clean_word:
                original_words.append(clean_word)

        note_conf_sum = sum(1 for word in note_words if word in original_words)
        return note_conf_sum / len(note_words)

    def _calculate_overall_confidence(self, original_text: str, ing_text: str) -> float:
        """
        Calculate overall confidence based on fuzzy matching between the original text and the ingredient text.
        Uses token sort ratio to account for word order variations.
        """

        ratio = fuzz.token_sort_ratio(original_text, ing_text)
        return ratio / 100.0

    def _calculate_confidence(self, original_text: str, ing: RecipeIngredient) -> IngredientConfidence:
        qty_conf = self._calculate_qty_conf(original_text, ing.quantity)
        note_conf = self._calculate_note_conf(original_text, ing.note)

        # Not all ingredients will have a food and/or unit,
        # so if either is missing we fall back to overall confidence.
        overall_confidence = self._calculate_overall_confidence(original_text, ing.display)
        if ing.food:
            food_conf = 1.0
        else:
            food_conf = overall_confidence

        if ing.unit:
            unit_conf = 1.0
        else:
            unit_conf = overall_confidence

        return IngredientConfidence(
            average=(qty_conf + unit_conf + food_conf + note_conf) / 4,
            quantity=qty_conf,
            unit=unit_conf,
            food=food_conf,
            comment=note_conf,
        )

    def _convert_substitutes(
        self, substitutes: list[str], food: IngredientFoodCreate | None
    ) -> list[RecipeIngredientSubstitution]:
        """
        Resolves each alternative the model extracted to an existing food, keeping the raw text
        as a note when nothing matches.

        Unlike the ingredient's own food, a substitute cannot be invented here: the column holds
        a food id, and an id for a food that does not exist yet is dropped on save. The note
        fallback is what keeps the alternative from being lost either way.
        """

        ingredient_food = self.data_matcher.find_food_match(food) if food else None

        substitutions: list[RecipeIngredientSubstitution] = []
        for substitute in substitutes:
            substitute = substitute.strip()
            if not substitute:
                continue

            food_match = self.data_matcher.find_food_match(substitute)
            if not food_match:
                substitutions.append(RecipeIngredientSubstitution(note=substitute))
            elif not ingredient_food or food_match.id != ingredient_food.id:
                # an alternative that resolves back to the ingredient's own food says nothing
                substitutions.append(RecipeIngredientSubstitution(substitute_food_id=food_match.id))

        return substitutions

    def _convert_ingredient(self, original_text: str, openai_ing: OpenAIIngredient) -> ParsedIngredient:
        food = IngredientFoodCreate(name=openai_ing.food) if openai_ing.food else None
        ingredient = RecipeIngredient(
            original_text=original_text,
            quantity=openai_ing.quantity,
            unit=IngredientUnitCreate(name=openai_ing.unit) if openai_ing.unit else None,
            food=food,
            note=openai_ing.note,
            substitutions=self._convert_substitutes(openai_ing.substitutes, food),
        )

        parsed_ingredient = ParsedIngredient(
            input=original_text,
            confidence=self._calculate_confidence(original_text, ingredient),
            ingredient=ingredient,
        )

        return self.find_ingredient_match(parsed_ingredient)

    @staticmethod
    def _reference_line(name: str, alternatives: list[str | None]) -> str:
        """Formats one reference entry as `name: alias, alias`, keeping each alternative once."""

        seen = {name.casefold()}
        aliases: list[str] = []
        for alternative in alternatives:
            if alternative and alternative.strip() and alternative.strip().casefold() not in seen:
                seen.add(alternative.strip().casefold())
                aliases.append(alternative.strip())

        return f"{name}: {', '.join(aliases)}" if aliases else name

    @staticmethod
    def _tokens(text: str) -> list[str]:
        """Normalized words with a trailing plural `s` or `x` removed, so singular and plural forms compare equal."""

        words = re.findall(r"[a-z0-9]+", IngredientFoodModel.normalize(text))
        return [word[:-1] if len(word) > 3 and word[-1] in "sx" else word for word in words]

    def _unit_references(self) -> list[str]:
        return sorted(
            self._reference_line(
                unit.name,
                [
                    unit.plural_name,
                    unit.abbreviation,
                    unit.plural_abbreviation,
                    *(alias.name for alias in unit.aliases or []),
                ],
            )
            for unit in self.data_matcher.units_by_id.values()
            if unit.name
        )

    def _food_references(self, ingredients: list[str]) -> list[str]:
        """
        Foods whose name, plural or alias appears in the ingredients. Sending only these candidates keeps the
        prompt small, whatever the size of the foods database.
        """

        input_text = f" {' '.join(' '.join(self._tokens(ingredient)) for ingredient in ingredients)} "
        candidates: list[tuple[int, str]] = []
        for food in self.data_matcher.foods_by_id.values():
            if not food.name:
                continue

            terms = [food.name, food.plural_name, *(alias.name for alias in food.aliases or [])]
            match_lengths = [
                len(phrase)
                for term in terms
                if term and (phrase := " ".join(self._tokens(term))) and f" {phrase} " in input_text
            ]
            if match_lengths:
                candidates.append((max(match_lengths), self._reference_line(food.name, [food.plural_name, *terms[2:]])))

        # the most specific matches first, e.g. "pomme de terre" before "pomme"
        candidates.sort(key=lambda candidate: -candidate[0])
        return [line for _, line in candidates[: self.MAX_FOOD_REFERENCES]]

    def _get_prompt(self, service: OpenAIService, ingredients: list[str] | None = None) -> str:
        data_injections: list[OpenAIDataInjection] = []
        if units := self._unit_references():
            data_injections.append(
                OpenAIDataInjection(
                    description=(
                        "Below are the units of the units database, one per line, as `name: aliases`, where the "
                        "aliases are the plural, abbreviations and other names of the unit. Use the names and "
                        "aliases to determine which part of the input is the unit. When it matches a name or an "
                        "alias, return the unit name exactly as written before the colon. You may find a unit in "
                        "the input that does not exist in this list. This should not prevent you from parsing "
                        "that text as a unit."
                    ),
                    value="\n".join(units),
                )
            )

        if ingredients and (foods := self._food_references(ingredients)):
            data_injections.append(
                OpenAIDataInjection(
                    description=(
                        "Below are the foods of the foods database that may appear in the input, one per line, "
                        "as `name: aliases`, where the aliases are the plural and other names of the food. Use "
                        "the names and aliases to determine which part of the input is the food. When it matches "
                        "a name or an alias, return the food name exactly as written before the colon, choosing "
                        "the entry that matches the most words of the input. You may find a food in the input "
                        "that does not exist in this list. This should not prevent you from parsing that text "
                        "as a food."
                    ),
                    value="\n".join(foods),
                )
            )

        return service.get_prompt("recipes.parse-recipe-ingredients", data_injections=data_injections or None)

    async def _parse(self, ingredients: list[str]) -> OpenAIIngredients:
        service = OpenAIService(self.repos)
        prompt = self._get_prompt(service, ingredients)

        response = await service.get_response(
            prompt, json.dumps(ingredients, separators=(",", ":")), response_schema=OpenAIIngredients
        )

        if not response:
            raise Exception("No response from OpenAI")

        return OpenAIIngredients(ingredients=response.ingredients)

    async def parse_one(self, ingredient_string: str) -> ParsedIngredient:
        items = await self.parse([ingredient_string])
        return items[0]

    async def parse(self, ingredients: list[str]) -> list[ParsedIngredient]:
        response = await self._parse(ingredients)
        if len(response.ingredients) != len(ingredients):
            raise ValueError(
                "OpenAI returned an unexpected number of ingredients. "
                f"Expected {len(ingredients)}, got {len(response.ingredients)}"
            )

        return [
            self._convert_ingredient(original_text, ing)
            for original_text, ing in zip(ingredients, response.ingredients, strict=True)
        ]
