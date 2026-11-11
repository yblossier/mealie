"""
Online search in USDA FoodData Central (public domain), through its API with the key chosen by the group, or the
shared demonstration key. The API limits the requests per key (30 an hour for the demonstration key, 1,000 for a
personal one), so every request goes through a process-wide limiter and its answers are cached.
"""

from dataclasses import dataclass
from typing import Any

import httpx

from mealie.core.settings.static import APP_VERSION
from mealie.services.recipe.food_reference_types import FoodReferenceResult
from mealie.services.recipe.open_food_facts_service import _RateLimiter, _TTLCache

BASE_URL = "https://api.nal.usda.gov/fdc/v1"
SEARCH_PATH = "/foods/search"
FOOD_URL = "https://fdc.nal.usda.gov/food-details/{fdc_id}/nutrients"
DEMO_KEY = "DEMO_KEY"
DATA_TYPES = "Foundation,SR Legacy"
PAGE_SIZE = 25
USER_AGENT = f"Mealie/{APP_VERSION} (https://github.com/mealie-recipes/mealie)"

UNIT_FACTORS: dict[str, float] = {"g": 1, "mg": 1e-3, "ug": 1e-6, "µg": 1e-6}
"""Grams per unit of the API"""

# Mealie field -> its unit, and the FoodData Central nutrient ids giving it, the preferred one first
NUTRIENTS: dict[str, tuple[str, tuple[int, ...]]] = {
    "carbohydrate_content": ("g", (1005, 1050)),
    "sugar_content": ("g", (2000, 1063)),
    "fiber_content": ("g", (1079,)),
    "fat_content": ("g", (1004,)),
    "saturated_fat_content": ("g", (1258,)),
    "trans_fat_content": ("g", (1257,)),
    "protein_content": ("g", (1003,)),
    "cholesterol_content": ("mg", (1253,)),
    "sodium_content": ("mg", (1093,)),
    "calcium_content": ("mg", (1087,)),
    "iron_content": ("mg", (1089,)),
    "magnesium_content": ("mg", (1090,)),
    "potassium_content": ("mg", (1092,)),
    "vitamin_a_content": ("ug", (1106,)),
    "vitamin_c_content": ("mg", (1162,)),
    "vitamin_d_content": ("ug", (1114,)),
}
ENERGY_KCAL_IDS = (1008, 2047, 2048)
"""Energy in kcal: the general one, then the Atwater ones used by the Foundation foods"""
ENERGY_KJ_ID = 1062
FIBER_ID = 1079
MONO_FAT_ID, POLY_FAT_ID = 1292, 1293
CORE_FIELDS = ("calories", "carbohydrate_content", "fat_content", "protein_content")


class UsdaError(Exception):
    """FoodData Central could not be reached or gave an unusable answer"""


class UsdaRateLimited(UsdaError):
    """The requests allowed for the API key are used up"""


class UsdaInvalidKey(UsdaError):
    """FoodData Central refused the API key"""


_cache = _TTLCache()
_limiters: dict[str, _RateLimiter] = {}


def _limiter(api_key: str) -> _RateLimiter:
    if api_key not in _limiters:
        _limiters[api_key] = _RateLimiter(30 if api_key == DEMO_KEY else 1_000, period=3600)
    return _limiters[api_key]


def reset_state() -> None:
    """Forgets the cached answers and the requests made, for the tests"""
    _limiters.clear()
    _cache.clear()


@dataclass(frozen=True)
class UsdaConfig:
    """How a group reaches the API, from its preferences"""

    api_key: str | None = None
    enabled: bool = True

    @property
    def effective_api_key(self) -> str:
        return (self.api_key or "").strip() or DEMO_KEY

    @classmethod
    def from_preferences(cls, preferences: Any) -> UsdaConfig:
        if preferences is None:
            return cls()
        enabled = getattr(preferences, "usda_api_enabled", True)
        return cls(api_key=getattr(preferences, "usda_api_key", None), enabled=True if enabled is None else enabled)


class UsdaService:
    TIMEOUT = 10

    transport: httpx.AsyncBaseTransport | None = None
    """The default transport, replaced by the tests"""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None, config: UsdaConfig | None = None) -> None:
        if transport:
            self.transport = transport
        self.config = config or UsdaConfig()

    @staticmethod
    def _amount(nutrient: dict, unit: str) -> float | None:
        """The nutrient's value in the given unit, or None when it's missing or in another kind of unit"""
        try:
            value = float(nutrient["value"])
        except KeyError, TypeError, ValueError:
            return None
        if value < 0:
            return None
        source_unit = str(nutrient.get("unitName") or unit).lower()
        if source_unit not in UNIT_FACTORS:
            return None
        return value * UNIT_FACTORS[source_unit] / UNIT_FACTORS[unit]

    @classmethod
    def nutrients(cls, food_nutrients: list) -> dict[str, float | None]:
        """The nutrients of a food of the API, per 100 g, with the keys and units of the composition tables"""
        by_id: dict[int, dict] = {}
        for nutrient in food_nutrients:
            if not isinstance(nutrient, dict):
                continue
            try:
                nutrient_id = int(nutrient["nutrientId"])
            except KeyError, TypeError, ValueError:
                continue
            by_id.setdefault(nutrient_id, nutrient)

        def first(unit: str, ids: tuple[int, ...]) -> float | None:
            for nutrient_id in ids:
                if nutrient_id in by_id and (value := cls._amount(by_id[nutrient_id], unit)) is not None:
                    return round(value, 4)
            return None

        def number(nutrient_id: int) -> float | None:
            try:
                value = float(by_id[nutrient_id]["value"])
            except KeyError, TypeError, ValueError:
                return None
            return value if value >= 0 else None

        values: dict[str, float | None] = {}
        calories = next((v for i in ENERGY_KCAL_IDS if (v := number(i)) is not None), None)
        if calories is None and (kj := number(ENERGY_KJ_ID)) is not None:
            calories = round(kj / 4.184, 4)
        values["calories"] = calories
        for field, (unit, ids) in NUTRIENTS.items():
            values[field] = first(unit, ids)

        carbs, fiber = values["carbohydrate_content"], values["fiber_content"]
        if carbs is not None and fiber is not None:
            # USDA counts fibre in carbohydrates; the EU (and Ciqual) does not
            values["carbohydrate_content"] = round(max(carbs - fiber, 0.0), 4)
        mono, poly = first("g", (MONO_FAT_ID,)), first("g", (POLY_FAT_ID,))
        values["unsaturated_fat_content"] = (
            round((mono or 0) + (poly or 0), 4) if mono is not None or poly is not None else None
        )
        return values

    @classmethod
    def to_result(cls, food: dict) -> FoodReferenceResult | None:
        """The food as a normalized reference food, or None when its main nutrition facts are missing"""
        code = str(food.get("fdcId") or "").strip()
        name = str(food.get("description") or "").strip()
        if not code or not name:
            return None
        nutrients = cls.nutrients(food.get("foodNutrients") or [])
        if any(nutrients.get(field) is None for field in CORE_FIELDS):
            return None
        brand = str(food.get("brandOwner") or food.get("brandName") or "").strip() or None
        return FoodReferenceResult(
            source="usda",
            code=code,
            name=name,
            name_en=name,
            nutrients=nutrients,
            brand=brand,
            url=FOOD_URL.format(fdc_id=code),
        )

    async def _get(self, path: str, params: dict[str, Any]) -> dict:
        api_key = self.config.effective_api_key
        if not _limiter(api_key).acquire():
            raise UsdaRateLimited("Too many requests to FoodData Central, try again later")
        try:
            async with httpx.AsyncClient(
                transport=self.transport, timeout=self.TIMEOUT, headers={"User-Agent": USER_AGENT}
            ) as client:
                response = await client.get(BASE_URL + path, params={**params, "api_key": api_key})
        except httpx.HTTPError as e:
            raise UsdaError(f"Could not reach FoodData Central: {e}") from e

        if response.status_code == 429:
            raise UsdaRateLimited("FoodData Central limits the requests of this API key, try again later")
        if response.status_code in (401, 403):
            raise UsdaInvalidKey("FoodData Central refused the API key")
        if response.status_code != 200:
            raise UsdaError(f"FoodData Central answered with the status {response.status_code}")
        try:
            data = response.json()
        except ValueError as e:
            raise UsdaError("FoodData Central gave an invalid answer") from e
        return data if isinstance(data, dict) else {}

    async def search(self, query: str, limit: int = PAGE_SIZE) -> list[FoodReferenceResult]:
        """The foods named like the query that have their main nutrition facts, in the API's order"""
        query = " ".join(query.split())
        if not query or not self.config.enabled:
            return []
        key = f"search:{query.lower()}"
        found, cached = _cache.get(key)
        if not found:
            data = await self._get(SEARCH_PATH, {"query": query, "pageSize": PAGE_SIZE, "dataType": DATA_TYPES})
            foods = data.get("foods") or []
            cached = [result for food in foods if isinstance(food, dict) and (result := self.to_result(food))]
            _cache.set(key, cached)
        return list(cached[:limit])


async def search_usda(
    query: str,
    config: UsdaConfig | Any = None,
    limit: int = PAGE_SIZE,
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[FoodReferenceResult]:
    """
    Searches FoodData Central with the group's settings (a `UsdaConfig` or the group preferences) and returns the
    foods having their main nutrition facts, normalized. Returns nothing when the group turned the API off. Nothing is
    written to the database. Raises `UsdaError` (or one of its subclasses) when the API can't answer.
    """
    if not isinstance(config, UsdaConfig):
        config = UsdaConfig.from_preferences(config)
    return await UsdaService(transport=transport, config=config).search(query, limit)
