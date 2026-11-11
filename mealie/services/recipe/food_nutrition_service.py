import json
from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import field as dataclass_field

from pydantic import UUID4
from rapidfuzz import fuzz
from text_unidecode import unidecode

from mealie.core import exceptions
from mealie.repos.repository_factory import AllRepositories
from mealie.schema import mapper
from mealie.schema.openai.food_nutrition import (
    OpenAIFoodNutrition,
    OpenAIFoodNutritionMatches,
    OpenAIFoodsNutrition,
)
from mealie.schema.recipe.recipe_ingredient import (
    IngredientFoodNutritionEstimate,
    IngredientFoodNutritionEstimateItem,
    IngredientFoodNutritionIssue,
    IngredientFoodNutritionLogCorrection,
    IngredientFoodNutritionLogOrigin,
    IngredientFoodNutritionLogSave,
    IngredientFoodNutritionLogStep,
    IngredientFoodNutritionLogStepKind,
    IngredientFoodNutritionReference,
    IngredientFoodNutritionSource,
    IngredientFoodOut,
    IngredientFoodSave,
)
from mealie.schema.recipe.recipe_nutrition import Nutrition
from mealie.services._base_service import BaseService
from mealie.services.openai import OpenAIService
from mealie.services.recipe.food_composition_service import (
    CompositionFood,
    CompositionMatch,
    CompositionSource,
    FoodCompositionService,
)
from mealie.services.recipe.food_reference_service import ApiSearch, FoodReferenceService, is_relevant, merge
from mealie.services.recipe.open_food_facts_service import (
    OpenFoodFactsConfig,
    OpenFoodFactsRateLimited,
    OpenFoodFactsService,
)
from mealie.services.recipe.usda_service import UsdaConfig, UsdaRateLimited, UsdaService

ESTIMATE_FOOD_NUTRITION_PROMPT = "recipes.estimate-food-nutrition"
MATCH_FOOD_NUTRITION_PROMPT = "recipes.match-food-nutrition"


@dataclass
class _Trace:
    """What happened while estimating a food, kept in its history"""

    item: IngredientFoodNutritionEstimateItem
    steps: list[IngredientFoodNutritionLogStep] = dataclass_field(default_factory=list)
    corrections: list[IngredientFoodNutritionLogCorrection] = dataclass_field(default_factory=list)
    result: IngredientFoodNutritionEstimate | None = None
    error: str | None = None
    candidates: list[CompositionMatch] = dataclass_field(default_factory=list)
    """Foods of the composition tables named like this one, best first"""
    match: CompositionMatch | None = None
    """The candidate confident enough to be used without the AI choosing"""


@dataclass
class _Answer:
    raw: OpenAIFoodNutrition
    """The answer of the model"""
    food: OpenAIFoodNutrition
    """The answer without its out of range values"""
    step: IngredientFoodNutritionLogStep


class FoodNutritionService(BaseService):
    """
    Finds the nutrition facts of foods, per 100 g: in the Ciqual table first, then in the USDA one, then online in
    Open Food Facts, with the group's AI provider choosing among their candidates when it's set up, and estimating
    them as a last resort.
    """

    CHUNK_SIZE = 10
    """Number of foods sent per request, so long lists don't overflow the model's output"""

    CORE_FIELDS = ("calories", "carbohydrate_content", "fat_content", "protein_content")
    """Values any food has; an estimate missing one of them is asked again"""

    MAX_VALUES: dict[str, float] = {
        "calories": 900,
        "carbohydrate_content": 100,
        "fat_content": 100,
        "fiber_content": 100,
        "protein_content": 100,
        "saturated_fat_content": 100,
        "sugar_content": 100,
        "trans_fat_content": 100,
        "unsaturated_fat_content": 100,
        "cholesterol_content": 3_000,
        "sodium_content": 40_000,
        "calcium_content": 3_000,
        "iron_content": 150,
        "magnesium_content": 1_000,
        "potassium_content": 6_000,
        "vitamin_a_content": 30_000,
        "vitamin_c_content": 3_000,
        "vitamin_d_content": 300,
        "average_weight": 10_000,
    }
    """Highest plausible value per 100 g (in each field's unit), from the richest foods of food composition tables"""

    MACROS_TOLERANCE = 1.05
    """Carbohydrates, fat, protein and fiber can't weigh more than the 100 g they're part of, give or take rounding"""

    ENERGY_TOLERANCE = 0.25
    """Accepted gap between the calories and the energy computed from the macronutrients"""

    ENERGY_MIN_GAP = 15
    """Accepted gap in kcal, so the relative tolerance doesn't reject low calorie foods over rounding"""

    LOGS_PER_FOOD = 10
    """Number of estimates kept in the history of each food"""

    NAME_MATCH_THRESHOLD = 50
    """Below this similarity, the name echoed by the model doesn't match the food it was asked about"""

    CANDIDATES_PER_SOURCE = 5
    """Number of foods of each composition table the AI chooses from"""

    def __init__(self, repos: AllRepositories, group_id: UUID4) -> None:
        self.repos = repos
        self.group_id = group_id
        self.references = FoodReferenceService(repos.food_composition)
        self.composition = FoodCompositionService(tables=self.references.table)
        preferences = repos.group_preferences.get_one(group_id)
        self.open_food_facts = OpenFoodFactsService(config=OpenFoodFactsConfig.from_preferences(preferences))
        self.usda = UsdaService(config=UsdaConfig.from_preferences(preferences))
        super().__init__()

    @staticmethod
    def _format_value(value: float | None) -> str | None:
        if value is None or value < 0:
            return None

        return f"{round(value, 2):.2f}".rstrip("0").rstrip(".")

    @classmethod
    def _to_nutrition(cls, data: OpenAIFoodNutrition) -> Nutrition:
        values = data.model_dump(exclude={"name", "average_weight"})
        return Nutrition(**{field: cls._format_value(value) for field, value in values.items()})

    @staticmethod
    def has_values(nutrition: Nutrition | None) -> bool:
        return nutrition is not None and any(value for value in nutrition.model_dump().values())

    # ==================================================================================================================
    # Coherence checks

    @staticmethod
    def _sum(*values: float | None) -> float:
        return sum(value or 0 for value in values)

    @classmethod
    def _computed_energy(cls, data: OpenAIFoodNutrition) -> float | None:
        """Energy from the Atwater factors, or None when the main macronutrients are unknown"""
        if data.carbohydrate_content is None or data.fat_content is None or data.protein_content is None:
            return None

        return (
            4 * data.carbohydrate_content
            + 4 * data.protein_content
            + 9 * data.fat_content
            + 2 * (data.fiber_content or 0)
        )

    @classmethod
    def _drop_out_of_range(cls, data: OpenAIFoodNutrition) -> OpenAIFoodNutrition:
        """Removes the values that can't be right: negative, or above what any food has"""
        updates: dict[str, float | None] = {}
        for field, maximum in cls.MAX_VALUES.items():
            value = getattr(data, field)
            if value is not None and not (0 <= value <= maximum):
                updates[field] = None
        if data.average_weight is not None and data.average_weight <= 0:
            updates["average_weight"] = None

        return data.model_copy(update=updates) if updates else data

    @classmethod
    def _issues(
        cls, data: OpenAIFoodNutrition, item: IngredientFoodNutritionEstimateItem | None = None
    ) -> list[IngredientFoodNutritionIssue]:
        """Lists the inconsistencies of an estimate, after the out of range values were dropped"""
        issues: list[IngredientFoodNutritionIssue] = []

        if item and data.name and cls._name_similarity(data.name, item) < cls.NAME_MATCH_THRESHOLD:
            issues.append(IngredientFoodNutritionIssue(code="name-mismatch", params={"name": data.name}))

        missing = [field for field in cls.CORE_FIELDS if getattr(data, field) is None]
        if missing:
            issues.append(IngredientFoodNutritionIssue(code="missing-values", params={"fields": ",".join(missing)}))

        macros = cls._sum(data.carbohydrate_content, data.fat_content, data.protein_content, data.fiber_content)
        if macros > 100 * cls.MACROS_TOLERANCE:
            issues.append(
                IngredientFoodNutritionIssue(code="macronutrients-overflow", params={"grams": round(macros, 1)})
            )

        if data.sugar_content is not None and data.carbohydrate_content is not None:
            if data.sugar_content > data.carbohydrate_content * cls.MACROS_TOLERANCE:
                issues.append(IngredientFoodNutritionIssue(code="sugar-over-carbohydrates"))

        if data.fat_content is not None:
            fats = cls._sum(data.saturated_fat_content, data.unsaturated_fat_content, data.trans_fat_content)
            if fats > data.fat_content * cls.MACROS_TOLERANCE + 0.1:
                issues.append(IngredientFoodNutritionIssue(code="fat-details-over-fat"))

        energy = cls._computed_energy(data)
        if energy is not None and data.calories is not None:
            gap = abs(data.calories - energy)
            if gap > max(cls.ENERGY_MIN_GAP, cls.ENERGY_TOLERANCE * max(data.calories, energy)):
                issues.append(
                    IngredientFoodNutritionIssue(
                        code="energy-mismatch", params={"calories": data.calories, "energy": round(energy)}
                    )
                )

        return issues

    @staticmethod
    def _normalize_name(name: str) -> str:
        return unidecode(name).lower().strip()

    @classmethod
    def _name_similarity(cls, name: str, item: IngredientFoodNutritionEstimateItem) -> float:
        answer = cls._normalize_name(name)
        names = [item.name, item.plural_name] if item.plural_name else [item.name]
        return max(fuzz.partial_ratio(answer, cls._normalize_name(candidate)) for candidate in names)

    @classmethod
    def _correct(cls, data: OpenAIFoodNutrition) -> OpenAIFoodNutrition:
        """
        Fixes what can be fixed in an estimate that is still inconsistent after a retry, and drops what can't.
        """
        updates: dict[str, float | None] = {}

        macros = cls._sum(data.carbohydrate_content, data.fat_content, data.protein_content, data.fiber_content)
        if macros > 100 * cls.MACROS_TOLERANCE:
            # nothing tells which value is wrong, so none of the macronutrients can be trusted
            for field in OpenAIFoodNutrition.model_fields:
                if field not in ("name", "average_weight"):
                    updates[field] = None
            return data.model_copy(update=updates)

        carbohydrates = data.carbohydrate_content
        if data.sugar_content is not None and carbohydrates is not None and data.sugar_content > carbohydrates:
            updates["sugar_content"] = carbohydrates

        fat = data.fat_content
        if fat is not None:
            saturated = min(data.saturated_fat_content, fat) if data.saturated_fat_content is not None else None
            trans = min(data.trans_fat_content, fat) if data.trans_fat_content is not None else None
            updates["saturated_fat_content"] = saturated
            updates["trans_fat_content"] = trans
            if data.unsaturated_fat_content is not None:
                updates["unsaturated_fat_content"] = max(
                    0, min(data.unsaturated_fat_content, fat - cls._sum(saturated, trans))
                )

        energy = cls._computed_energy(data)
        if energy is not None:
            # more calories than the macronutrients give can come from alcohol, which has no field, so only
            # missing or impossibly low calories are replaced
            if data.calories is None or energy - data.calories > max(cls.ENERGY_MIN_GAP, cls.ENERGY_TOLERANCE * energy):
                updates["calories"] = round(energy)

        return data.model_copy(update=updates)

    # ==================================================================================================================
    # Estimation

    async def _request(
        self, service: OpenAIService, prompt: str, items: Sequence[IngredientFoodNutritionEstimateItem]
    ) -> list[OpenAIFoodNutrition]:
        """Asks the model, returning its raw answers"""
        message = json.dumps(
            [item.model_dump(exclude_none=True, exclude={"id"}) for item in items],
            ensure_ascii=False,
            separators=(",", ":"),
        )

        response = await service.get_response(prompt, message, response_schema=OpenAIFoodsNutrition)
        if not response:
            raise Exception("No response from OpenAI")

        self.logger.debug(f"AI nutrition estimate for {message}: {response.model_dump_json(exclude_none=True)}")
        if len(response.foods) != len(items):
            raise ValueError(
                f"OpenAI returned an unexpected number of foods. Expected {len(items)}, got {len(response.foods)}"
            )

        return response.foods

    async def _ask(
        self, service: OpenAIService, prompt: str, traces: Sequence[_Trace], kind: IngredientFoodNutritionLogStepKind
    ) -> list[_Answer]:
        """Asks the model about the foods of the traces, recording the answer or the failure in each trace"""
        items = [trace.item for trace in traces]
        try:
            raws = await self._request(service, prompt, items)
        except Exception as e:
            for trace in traces:
                trace.steps.append(IngredientFoodNutritionLogStep(kind=kind, foods_count=len(items), error=str(e)))
            raise

        answers: list[_Answer] = []
        for trace, raw in zip(traces, raws, strict=True):
            food = self._drop_out_of_range(raw)
            step = IngredientFoodNutritionLogStep(
                kind=kind,
                foods_count=len(items),
                response=raw.model_dump(exclude_none=True),
                issues=self._issues(food, trace.item if len(items) > 1 else None),
            )
            trace.steps.append(step)
            answers.append(_Answer(raw, food, step))

        return answers

    async def _estimate_chunk(self, service: OpenAIService, prompt: str, traces: Sequence[_Trace]) -> None:
        kind = (
            IngredientFoodNutritionLogStepKind.batch if len(traces) > 1 else IngredientFoodNutritionLogStepKind.single
        )
        try:
            answers = await self._ask(service, prompt, traces, kind)
        except exceptions.RateLimitError:
            raise
        except Exception as e:
            if len(traces) == 1:
                raise
            # small models often drop, add or garble foods in long lists, which they get right one at a time
            self.logger.info(f"Asking the nutrition facts of {len(traces)} foods one at a time: {e}")
            for trace in traces:
                answer = (await self._ask(service, prompt, [trace], IngredientFoodNutritionLogStepKind.single))[0]
                self._finalize(trace, answer)
            return

        for trace, answer in zip(traces, answers, strict=True):
            issues = answer.step.issues
            if issues:
                # a food asked on its own gets the model's full attention, and can't be mixed up with another one
                self.logger.info(f"Asking again the nutrition facts of '{trace.item.name}': {self._describe(issues)}")
                try:
                    retry = (await self._ask(service, prompt, [trace], IngredientFoodNutritionLogStepKind.retry))[0]
                except exceptions.RateLimitError:
                    raise
                except Exception as e:
                    self.logger.warning(f"Could not ask again the nutrition facts of '{trace.item.name}': {e}")
                else:
                    if len(retry.step.issues) <= len(issues):
                        answer = retry

            self._finalize(trace, answer)

    @staticmethod
    def _describe(issues: Sequence[IngredientFoodNutritionIssue]) -> str:
        return "; ".join(str(issue) for issue in issues)

    def _finalize(self, trace: _Trace, answer: _Answer) -> None:
        answer.step.kept = True
        food = answer.food
        if answer.step.issues:
            self.logger.warning(
                f"Inconsistent nutrition facts for '{trace.item.name}': {self._describe(answer.step.issues)}"
            )
            food = self._correct(food)

        for field in OpenAIFoodNutrition.model_fields:
            before, after = getattr(answer.raw, field), getattr(food, field)
            if field != "name" and before != after:
                trace.corrections.append(IngredientFoodNutritionLogCorrection(field=field, before=before, after=after))

        trace.result = IngredientFoodNutritionEstimate(
            nutrition=self._to_nutrition(food),
            average_weight=round(food.average_weight, 1) if food.average_weight else None,
            source=IngredientFoodNutritionSource.ai,
        )

    @staticmethod
    def ai_enabled(service: OpenAIService) -> bool:
        """Whether the group has an AI provider to choose among the candidates and estimate the foods found nowhere"""
        return service.default_provider is not None

    # ==================================================================================================================
    # Composition tables

    @classmethod
    def _reference_id(cls, food: CompositionFood) -> str:
        return f"{food.source}:{food.code}"

    @classmethod
    def to_reference(
        cls, food: CompositionFood, average_weight: float | None = None
    ) -> IngredientFoodNutritionReference:
        return IngredientFoodNutritionReference(
            source=IngredientFoodNutritionSource(food.source),
            code=food.code,
            name=food.name,
            nutrition=Nutrition(**{field: cls._format_value(value) for field, value in food.nutrients.items()}),
            average_weight=average_weight,
        )

    def online_enabled(self, source: CompositionSource) -> bool:
        """Whether the API of the source may be called, once its referential has no relevant food"""
        if not self.open_food_facts.enabled():
            return False
        return source == "off" or (source == "usda" and self.usda.config.enabled)

    def api(self, source: CompositionSource, limit: int) -> ApiSearch | None:
        if not self.online_enabled(source):
            return None
        if source == "off":
            return lambda query: self.open_food_facts.search(query, limit)
        if source == "usda":
            return lambda query: self.usda.search(query, limit)
        return None

    async def search_references(self, query: str, limit: int = 20) -> list[IngredientFoodNutritionReference]:
        """
        Foods of the composition tables named like the query, Ciqual first. When none is named like it, USDA
        FoodData Central is searched online, and its foods are kept in the referential.
        """
        matches = self.composition.search(query, limit)
        if not is_relevant(matches) and (api := self.api("usda", limit)):
            lookup = await self.references.lookup("usda", query, api, limit)
            if is_relevant(lookup.api_matches):
                matches = merge(lookup.api_matches)
            else:
                matches = merge(matches, lookup.api_matches)[:limit]
        return [self.to_reference(match.food, self.composition.average_weight(match.food)) for match in matches]

    async def search_open_food_facts(self, query: str, limit: int = 20) -> list[IngredientFoodNutritionReference]:
        """
        Products of Open Food Facts named like the query, or the one with this barcode: the ones kept in the
        referential first, then the ones found online when the referential has none named like the query.
        """
        if self.open_food_facts.is_barcode(query):
            known = self.references.table("off").get(query)
            if known:
                return [self.to_reference(known)]
            product = await self.open_food_facts.product(query)
            if product:
                self.references.enrich("off", [product])
            return [self.to_reference(product)] if product else []

        lookup = await self.references.lookup("off", query, self.api("off", limit), limit)
        if lookup.error and not lookup.db_matches:
            raise lookup.error
        foods = [match.food for match in lookup.matches]
        # the products Open Food Facts finds by their brand or category stay after the ones named like the query
        codes = {food.code for food in foods}
        foods += [food for food in lookup.api_foods if food.code not in codes]
        return [self.to_reference(food) for food in foods[:limit]]

    def _from_table(self, trace: _Trace, food: CompositionFood, average_weight: float | None = None) -> None:
        weight = average_weight or self.composition.average_weight(food)
        reference = self.to_reference(food, round(weight, 1) if weight else None)
        trace.result = IngredientFoodNutritionEstimate(
            nutrition=reference.nutrition,
            average_weight=reference.average_weight,
            source=reference.source,
            reference_code=reference.code,
            reference_name=reference.name,
        )

    @staticmethod
    def _names(item: IngredientFoodNutritionEstimateItem) -> list[str]:
        return list(dict.fromkeys(name for name in (item.name, item.plural_name) if name))

    def _lookup(self, trace: _Trace) -> None:
        """Looks the food up in the composition tables, keeping its candidates and its confident match"""
        names = self._names(trace.item)
        trace.match = self.composition.best(*names)

        candidates: dict[str, CompositionMatch] = {}
        if trace.match:
            candidates[self._reference_id(trace.match.food)] = trace.match
        for name in names:
            for matches in self.composition.search_by_source(name, self.CANDIDATES_PER_SOURCE).values():
                for match in matches:
                    candidates.setdefault(self._reference_id(match.food), match)
        trace.candidates = list(candidates.values())

        trace.steps.append(
            IngredientFoodNutritionLogStep(
                kind=IngredientFoodNutritionLogStepKind.lookup,
                response={
                    "match": self._reference_id(trace.match.food) if trace.match else None,
                    "candidates": [
                        {"id": self._reference_id(c.food), "name": c.food.name} for c in trace.candidates[:10]
                    ],
                },
                kept=trace.match is not None,
            )
        )

    async def _search_api(self, source: CompositionSource, traces: Sequence[_Trace], use_best: bool) -> None:
        """
        Searches the referential of the source, then its API, for the foods the tables have no confident match for,
        adding the foods found to their candidates. With `use_best`, a food named like the item is used right away, as
        no AI will choose. Once the API is rate limited or unreachable, only the referential is searched.
        """
        kind = (
            IngredientFoodNutritionLogStepKind.open_food_facts
            if source == "off"
            else IngredientFoodNutritionLogStepKind.usda
        )
        api = self.api(source, self.CANDIDATES_PER_SOURCE * 2)
        if api is None and source != "off":
            # the composition tables, searched first, already hold the referential of the source
            return
        error: str | None = None
        for trace in traces:
            query = trace.item.name
            lookup = await self.references.lookup(source, query, None if error else api, self.CANDIDATES_PER_SOURCE * 2)
            if lookup.error:
                if isinstance(lookup.error, OpenFoodFactsRateLimited | UsdaRateLimited):
                    self.logger.info(f"{source} API skipped: {lookup.error}")
                else:
                    self.logger.warning(f"{source} API skipped: {lookup.error}")
                error = str(lookup.error)
            elif error and api:
                lookup.error = Exception(error)
            if not lookup.matches and not lookup.api_called and not lookup.error:
                continue

            matches = lookup.matches[: self.CANDIDATES_PER_SOURCE]
            best = matches[0] if use_best and is_relevant(matches[:1]) else None
            known = {self._reference_id(c.food) for c in trace.candidates}
            trace.candidates += [m for m in matches if self._reference_id(m.food) not in known]
            trace.steps.append(
                IngredientFoodNutritionLogStep(
                    kind=kind,
                    response={
                        "source": source,
                        "query": query,
                        "api_called": lookup.api_called,
                        "match": self._reference_id(best.food) if best else None,
                        "candidates": [{"id": self._reference_id(m.food), "name": m.food.name} for m in matches],
                    },
                    error=str(lookup.error) if lookup.error else None,
                    kept=best is not None,
                )
            )
            if best:
                self._from_table(trace, best.food)

    async def _match(self, service: OpenAIService, traces: Sequence[_Trace]) -> None:
        """Lets the AI choose the candidate of each food, and give its average weight"""
        prompt = service.get_prompt(MATCH_FOOD_NUTRITION_PROMPT)
        message = json.dumps(
            [
                trace.item.model_dump(exclude_none=True, exclude={"id"})
                | {
                    "candidates": [
                        {"id": self._reference_id(c.food), "name": c.food.name}
                        for c in ([trace.match] if trace.match else trace.candidates)
                    ]
                }
                for trace in traces
            ],
            ensure_ascii=False,
            separators=(",", ":"),
        )

        try:
            response = await service.get_response(prompt, message, response_schema=OpenAIFoodNutritionMatches)
            if not response:
                raise Exception("No response from OpenAI")
            if len(response.foods) != len(traces):
                raise ValueError(
                    f"OpenAI returned an unexpected number of foods. Expected {len(traces)}, got {len(response.foods)}"
                )
        except exceptions.RateLimitError:
            raise
        except Exception as e:
            # the tables' own match, or else the AI estimate, still gives an answer
            self.logger.warning(f"Could not match {len(traces)} foods with the composition tables: {e}")
            for trace in traces:
                trace.steps.append(
                    IngredientFoodNutritionLogStep(
                        kind=IngredientFoodNutritionLogStepKind.match, foods_count=len(traces), error=str(e)
                    )
                )
            return

        for trace, answer in zip(traces, response.foods, strict=True):
            candidates = {self._reference_id(c.food): c.food for c in trace.candidates}
            chosen = candidates.get(answer.reference or "")
            weight = answer.average_weight if answer.average_weight and 0 < answer.average_weight <= 10_000 else None
            issues = []
            if answer.reference and not chosen:
                issues.append(IngredientFoodNutritionIssue(code="unknown-reference", params={"id": answer.reference}))

            food = chosen or (trace.match.food if trace.match else None)
            trace.steps.append(
                IngredientFoodNutritionLogStep(
                    kind=IngredientFoodNutritionLogStepKind.match,
                    foods_count=len(traces),
                    response=answer.model_dump(exclude_none=True),
                    issues=issues,
                    kept=food is not None,
                )
            )
            if food:
                self._from_table(trace, food, weight)

    def _save_logs(
        self,
        traces: Sequence[_Trace],
        origin: IngredientFoodNutritionLogOrigin,
        ai_model: str | None,
        error: str | None,
    ) -> None:
        """Keeps the history of the estimates of existing foods, including the failed ones"""
        repo = self.repos.ingredient_food_nutrition_logs
        food_ids = {trace.item.id for trace in traces if trace.item.id}
        if not food_ids:
            return

        # the ids come from the request, so only the foods of the group are kept
        known_ids = {food_id for food_id in food_ids if self.repos.ingredient_foods.get_one(food_id)}
        for trace in traces:
            if trace.item.id not in known_ids or not (trace.steps or error or trace.error):
                continue
            try:
                repo.add(
                    IngredientFoodNutritionLogSave(
                        group_id=self.group_id,
                        food_id=trace.item.id,
                        origin=origin,
                        ai_model=ai_model,
                        steps=trace.steps,
                        corrections=trace.corrections,
                        result=trace.result,
                        error=None if trace.result else (error or trace.error),
                    ),
                    keep=self.LOGS_PER_FOOD,
                )
            except Exception as e:
                # the history is a diagnostic aid, which must not fail the estimate
                self.logger.exception(f"Could not save the nutrition estimate log of '{trace.item.name}': {e}")

    async def estimate(
        self,
        items: Sequence[IngredientFoodNutritionEstimateItem],
        origin: IngredientFoodNutritionLogOrigin = IngredientFoodNutritionLogOrigin.estimate,
    ) -> list[IngredientFoodNutritionEstimate]:
        """
        Finds the nutrition facts of the items, in the same order, keeping the history of the items with an id.
        An item found nowhere gets empty nutrition facts and no source.

        1. the composition tables, Ciqual first, then USDA, give their candidates and their confident match;
        1b. for the foods without a confident match, the referential of USDA, then of Open Food Facts, is searched, then
            its API when enabled and the referential has no food named like it (the foods found online are kept in the
            referential); the food named like it is used right away when there's no AI provider;
        2. with an AI provider, it chooses among the candidates and gives the average weight;
        3. with an AI provider, it estimates the foods matching no candidate.
        """
        service = OpenAIService(self.repos)
        ai_enabled = self.ai_enabled(service)
        ai_model = service.default_provider.model if service.default_provider else None

        traces = [_Trace(item) for item in items]
        error: str | None = None
        try:
            for trace in traces:
                self._lookup(trace)
                # without a weight, the AI gives it while confirming the match
                if trace.match and (not ai_enabled or self.composition.average_weight(trace.match.food)):
                    self._from_table(trace, trace.match.food)

            for source in ("usda", "off"):
                await self._search_api(
                    source, [trace for trace in traces if not trace.result and not trace.match], use_best=not ai_enabled
                )

            if ai_enabled:
                to_match = [trace for trace in traces if not trace.result and trace.candidates]
                for i in range(0, len(to_match), self.CHUNK_SIZE):
                    await self._match(service, to_match[i : i + self.CHUNK_SIZE])

                to_estimate = [trace for trace in traces if not trace.result]
                if to_estimate:
                    prompt = service.get_prompt(ESTIMATE_FOOD_NUTRITION_PROMPT)
                    for i in range(0, len(to_estimate), self.CHUNK_SIZE):
                        await self._estimate_chunk(service, prompt, to_estimate[i : i + self.CHUNK_SIZE])
            else:
                for trace in traces:
                    if not trace.result:
                        trace.error = "Not found in the food composition tables"
        except Exception as e:
            error = str(e)
            raise
        finally:
            self._save_logs(traces, origin, ai_model, error)

        return [trace.result or IngredientFoodNutritionEstimate(nutrition=Nutrition(), source=None) for trace in traces]

    async def fill(self, food_ids: Sequence[UUID4], overwrite: bool = False) -> list[IngredientFoodOut]:
        """
        Estimates and saves the nutrition facts and average weight of the given foods, returning the foods that
        were updated. Unless `overwrite` is set, only the missing nutrition facts or average weight are filled.
        """

        repo = self.repos.ingredient_foods
        foods: list[IngredientFoodOut] = []
        for food_id in dict.fromkeys(food_ids):
            food = repo.get_one(food_id)
            if not food:
                continue
            if not overwrite and self.has_values(food.nutrition) and food.average_weight:
                continue

            foods.append(food)

        if not foods:
            return []

        estimates = await self.estimate(
            [
                IngredientFoodNutritionEstimateItem(
                    id=food.id, name=food.name, plural_name=food.plural_name, description=food.description or None
                )
                for food in foods
            ],
            origin=IngredientFoodNutritionLogOrigin.fill,
        )

        updated: list[IngredientFoodOut] = []
        for food, estimate in zip(foods, estimates, strict=True):
            updates: dict = {}
            if self.has_values(estimate.nutrition) and (overwrite or not self.has_values(food.nutrition)):
                updates["nutrition"] = estimate.nutrition
                updates["nutrition_source"] = estimate.source
                updates["nutrition_reference_code"] = estimate.reference_code
                updates["nutrition_reference_name"] = estimate.reference_name
            if estimate.average_weight and (overwrite or not food.average_weight):
                updates["average_weight"] = estimate.average_weight
            if not updates:
                continue

            save_data = mapper.cast(food, IngredientFoodSave, group_id=self.group_id, **updates)
            updated.append(repo.update(food.id, save_data))

        return updated
