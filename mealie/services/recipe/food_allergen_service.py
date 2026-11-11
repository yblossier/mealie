import json
from collections.abc import Sequence

from pydantic import UUID4

from mealie.repos.repository_factory import AllRepositories
from mealie.schema import mapper
from mealie.schema.allergens.allergen import AllergenOut, AllergenSummary, AllergenUpdate
from mealie.schema.openai.food_allergens import OpenAIFoodsAllergens
from mealie.schema.recipe.recipe_ingredient import IngredientFoodOut, IngredientFoodSave
from mealie.services._base_service import BaseService
from mealie.services.openai import OpenAIDataInjection, OpenAIService
from mealie.services.recipe.recipe_allergen_service import normalize, split_terms

MATCH_FOOD_ALLERGENS_PROMPT = "recipes.match-food-allergens"


class FoodAllergenItem:
    def __init__(
        self, name: str, plural_name: str | None = None, aliases: Sequence[str] = (), description: str | None = None
    ) -> None:
        self.name = name
        self.plural_name = plural_name
        self.aliases = list(aliases)
        self.description = description

    def to_dict(self) -> dict:
        data: dict = {"name": self.name}
        if self.plural_name:
            data["plural_name"] = self.plural_name
        if self.aliases:
            data["aliases"] = self.aliases
        if self.description:
            data["description"] = self.description
        return data

    def texts(self) -> list[str]:
        """The normalized names of the food, searched for the allergen keywords"""
        names = [self.name, self.plural_name or "", *self.aliases]
        return list(dict.fromkeys(normalized for name in names if (normalized := normalize(name))))


def _contains(text: str, term: str) -> bool:
    return f" {term} " in f" {text} "


def _remove(text: str, term: str) -> str:
    return f" {text} ".replace(f" {term} ", " ").strip()


class FoodAllergenService(BaseService):
    """
    Links the foods of a group with the allergens they contain. The allergen keywords are tried first, offline;
    only the foods they don't match are sent to the AI provider, and each food it links with an allergen is added
    to the keywords of that allergen, so the same food is matched offline the next time.
    """

    CHUNK_SIZE = 40

    def __init__(self, repos: AllRepositories, group_id: UUID4) -> None:
        self.repos = repos
        self.group_id = group_id
        super().__init__()

    @staticmethod
    def allergen_code(allergen: AllergenOut) -> str:
        return allergen.code or allergen.name

    def _allergens(self) -> list[AllergenOut]:
        return self.repos.group_allergens.get_all()

    def _prompt(self, service: OpenAIService, allergens: Sequence[AllergenOut]) -> str:
        lines = [
            f"{self.allergen_code(allergen)}: {allergen.name}"
            + (f" ({allergen.keywords})" if allergen.keywords else "")
            for allergen in allergens
        ]
        return service.get_prompt(
            MATCH_FOOD_ALLERGENS_PROMPT,
            data_injections=[OpenAIDataInjection(description="The allergens to look for", value="\n".join(lines))],
        )

    async def _ask(
        self, service: OpenAIService, prompt: str, items: Sequence[FoodAllergenItem], allergens: Sequence[AllergenOut]
    ) -> list[list[AllergenSummary]]:
        message = json.dumps([item.to_dict() for item in items], ensure_ascii=False, separators=(",", ":"))
        response = await service.get_response(prompt, message, response_schema=OpenAIFoodsAllergens)
        if not response:
            raise Exception("No response from OpenAI")
        if len(response.foods) != len(items):
            raise ValueError(
                f"OpenAI returned an unexpected number of foods. Expected {len(items)}, got {len(response.foods)}"
            )

        by_code = {self.allergen_code(allergen).lower(): allergen for allergen in allergens}
        results: list[list[AllergenSummary]] = []
        for food in response.foods:
            found: dict[UUID4, AllergenSummary] = {}
            for code in food.allergens:
                allergen = by_code.get(code.strip().lower())
                if allergen and allergen.id not in found:
                    found[allergen.id] = AllergenSummary(id=allergen.id, name=allergen.name, code=allergen.code)
            results.append(sorted(found.values(), key=lambda a: a.name.lower()))
        return results

    @staticmethod
    def keyword_match(item: FoodAllergenItem, allergens: Sequence[AllergenOut]) -> list[AllergenSummary]:
        """The allergens whose keywords appear, as whole words, in the name, plural name or aliases of the food"""
        texts = item.texts()
        found: list[AllergenSummary] = []
        for allergen in allergens:
            keywords = split_terms(allergen.keywords)
            if not keywords:
                continue
            exclusions = split_terms(allergen.exclusions)
            for text in texts:
                for exclusion in exclusions:
                    text = _remove(text, exclusion)
                if any(_contains(text, keyword) for keyword in keywords):
                    found.append(AllergenSummary(id=allergen.id, name=allergen.name, code=allergen.code))
                    break
        return sorted(found, key=lambda a: a.name.lower())

    def _enrich_keywords(
        self, allergens: list[AllergenOut], matches: Sequence[tuple[FoodAllergenItem, list[AllergenSummary]]]
    ) -> list[AllergenOut]:
        """Adds the foods the AI linked with an allergen to its keywords, saving the allergens that changed"""
        additions: dict[UUID4, list[str]] = {}
        for item, found in matches:
            term = " ".join(item.name.split()).lower()
            if not normalize(term):
                continue
            for summary in found:
                additions.setdefault(summary.id, []).append(term)

        enriched: list[AllergenOut] = []
        for allergen in allergens:
            known = set(split_terms(allergen.keywords)) | set(split_terms(allergen.exclusions))
            new_terms: list[str] = []
            for term in additions.get(allergen.id, []):
                if (normalized := normalize(term)) not in known:
                    known.add(normalized)
                    new_terms.append(term)

            if not new_terms:
                enriched.append(allergen)
                continue

            keywords = ", ".join([k for k in [allergen.keywords.strip().rstrip(",")] if k] + new_terms)
            enriched.append(
                self.repos.group_allergens.update(allergen.id, mapper.cast(allergen, AllergenUpdate, keywords=keywords))
            )
        return enriched

    async def suggest(self, items: Sequence[FoodAllergenItem]) -> list[list[AllergenSummary]]:
        """
        The allergens of each food: found with the allergen keywords when possible, otherwise by the AI provider,
        whose matches then enrich the keywords of the allergens.
        """
        allergens = self._allergens()
        if not items or not allergens:
            return [[] for _ in items]

        results: list[list[AllergenSummary]] = [self.keyword_match(item, allergens) for item in items]
        pending = [i for i, found in enumerate(results) if not found]

        service: OpenAIService | None = None
        prompt = ""
        while pending:
            chunk, pending = pending[: self.CHUNK_SIZE], pending[self.CHUNK_SIZE :]
            if service is None:
                service = OpenAIService(self.repos)
                prompt = self._prompt(service, allergens)

            answers = await self._ask(service, prompt, [items[i] for i in chunk], allergens)
            for i, found in zip(chunk, answers, strict=True):
                results[i] = found
            allergens = self._enrich_keywords(allergens, [(items[i], results[i]) for i in chunk if results[i]])

            # the enriched keywords may now match foods still waiting, sparing them the AI
            still_pending: list[int] = []
            for i in pending:
                if found := self.keyword_match(items[i], allergens):
                    results[i] = found
                else:
                    still_pending.append(i)
            pending = still_pending

        return results

    async def match(self, food_ids: Sequence[UUID4] | None = None, overwrite: bool = False) -> list[IngredientFoodOut]:
        """
        Links the given foods (every food of the group when none is given) with their allergens, returning the
        foods that were updated. Unless `overwrite` is set, foods already linked with an allergen are left as is.
        """

        repo = self.repos.ingredient_foods
        if food_ids is None:
            candidates = repo.get_all()
        else:
            candidates = [food for food_id in dict.fromkeys(food_ids) if (food := repo.get_one(food_id))]

        foods = [food for food in candidates if overwrite or not food.allergens]
        if not foods:
            return []

        suggestions = await self.suggest(
            [
                FoodAllergenItem(
                    name=food.name,
                    plural_name=food.plural_name,
                    aliases=[alias.name for alias in food.aliases],
                    description=food.description or None,
                )
                for food in foods
            ]
        )

        updated: list[IngredientFoodOut] = []
        for food, allergens in zip(foods, suggestions, strict=True):
            if {a.id for a in allergens} == {a.id for a in food.allergens}:
                continue

            save_data = mapper.cast(food, IngredientFoodSave, group_id=self.group_id, allergens=allergens)
            updated.append(repo.update(food.id, save_data))

        return updated
