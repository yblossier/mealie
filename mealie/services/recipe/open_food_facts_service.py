"""
Online lookup in Open Food Facts, the collaborative database of packaged products (ODbL license), for the foods
missing from the bundled Ciqual and USDA tables, through its API on the production or the staging server chosen by
the group. Open Food Facts bans the IPs exceeding its rate limits, so every request goes through a process-wide
limiter and its answers are cached.
"""

import re
import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass
from typing import Any

import httpx
from rapidfuzz import fuzz

from mealie.core.config import get_app_settings
from mealie.core.settings.static import APP_VERSION
from mealie.services.recipe.food_composition_service import (
    CompositionFood,
    CompositionMatch,
    CompositionTable,
    head_tokens,
    normalize_tokens,
)
from mealie.services.recipe.food_reference_types import FoodReferenceResult

BASE_URLS = {"prod": "https://world.openfoodfacts.org", "dev": "https://world.openfoodfacts.net"}
"""The servers of the API, not editable: the production one, and the staging one meant for development"""
DEV_AUTH = ("off", "off")
"""The staging server asks for these public credentials"""
SEARCH_PATH = "/cgi/search.pl"
PRODUCT_PATH = "/api/v2/product/{barcode}"
USER_AGENT = f"Mealie/{APP_VERSION} (https://github.com/mealie-recipes/mealie)"
FIELDS = "code,product_name,product_name_fr,product_name_en,brands,nutriments"
BARCODE_PATTERN = re.compile(r"^\d{8,14}$")

# Open Food Facts field (per 100 g, in grams for the nutrients) -> Mealie field, and the factor to its unit
NUTRIENTS: dict[str, tuple[str, float]] = {
    "carbohydrates_100g": ("carbohydrate_content", 1),
    "sugars_100g": ("sugar_content", 1),
    "fiber_100g": ("fiber_content", 1),
    "fat_100g": ("fat_content", 1),
    "saturated-fat_100g": ("saturated_fat_content", 1),
    "trans-fat_100g": ("trans_fat_content", 1),
    "proteins_100g": ("protein_content", 1),
    "cholesterol_100g": ("cholesterol_content", 1_000),
    "sodium_100g": ("sodium_content", 1_000),
    "calcium_100g": ("calcium_content", 1_000),
    "iron_100g": ("iron_content", 1_000),
    "magnesium_100g": ("magnesium_content", 1_000),
    "potassium_100g": ("potassium_content", 1_000),
    "vitamin-c_100g": ("vitamin_c_content", 1_000),
    "vitamin-a_100g": ("vitamin_a_content", 1_000_000),
    "vitamin-d_100g": ("vitamin_d_content", 1_000_000),
}
CORE_FIELDS = ("calories", "carbohydrate_content", "fat_content", "protein_content")


class OpenFoodFactsError(Exception):
    """Open Food Facts could not be reached or gave an unusable answer"""


class OpenFoodFactsRateLimited(OpenFoodFactsError):
    """The requests allowed per minute are used up, by Mealie or by Open Food Facts itself"""


class _RateLimiter:
    """Sliding window limiter that never waits: a request beyond the limit is refused"""

    def __init__(self, limit: int, period: float = 60) -> None:
        self.limit = limit
        self.period = period
        self._calls: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> bool:
        now = time.monotonic()
        with self._lock:
            while self._calls and now - self._calls[0] >= self.period:
                self._calls.popleft()
            if len(self._calls) >= self.limit:
                return False
            self._calls.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._calls.clear()


class _TTLCache:
    def __init__(self, max_size: int = 1_000, ttl: float = 24 * 3600) -> None:
        self.max_size = max_size
        self.ttl = ttl
        self._items: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> tuple[bool, Any]:
        with self._lock:
            item = self._items.get(key)
            if item is None or time.monotonic() - item[0] >= self.ttl:
                self._items.pop(key, None)
                return False, None
            self._items.move_to_end(key)
            return True, item[1]

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._items[key] = (time.monotonic(), value)
            self._items.move_to_end(key)
            while len(self._items) > self.max_size:
                self._items.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


# Shared by the whole process, as the limits of Open Food Facts are per IP: 10 searches and 15 products a minute
_search_limiter = _RateLimiter(10)
_product_limiter = _RateLimiter(15)
_cache = _TTLCache()


def reset_state() -> None:
    """Forgets the cached answers and the requests made, for the tests"""
    _search_limiter.reset()
    _product_limiter.reset()
    _cache.clear()


@dataclass(frozen=True)
class OpenFoodFactsConfig:
    """How a group reaches the API, from its preferences"""

    mode: str = "prod"
    app_name: str | None = None
    app_version: str | None = None
    app_uuid: str | None = None

    @property
    def base_url(self) -> str:
        return BASE_URLS.get(self.mode, BASE_URLS["prod"])

    @property
    def is_dev(self) -> bool:
        return self.base_url == BASE_URLS["dev"]

    @property
    def params(self) -> dict[str, str]:
        """The parameters identifying the application, sent with every request"""
        values = {"app_name": self.app_name, "app_version": self.app_version, "app_uuid": self.app_uuid}
        return {key: value.strip() for key, value in values.items() if value and value.strip()}

    @property
    def user_agent(self) -> str:
        name = (self.app_name or "").strip()
        if not name:
            return USER_AGENT
        version = (self.app_version or "").strip() or APP_VERSION
        return f"{name}/{version} (Mealie/{APP_VERSION}; https://github.com/mealie-recipes/mealie)"

    @classmethod
    def from_preferences(cls, preferences: Any) -> OpenFoodFactsConfig:
        if preferences is None:
            return cls()
        mode = getattr(preferences, "off_mode", None) or "prod"
        return cls(
            mode=str(getattr(mode, "value", mode)),
            app_name=getattr(preferences, "off_app_name", None),
            app_version=getattr(preferences, "off_app_version", None),
            app_uuid=getattr(preferences, "off_app_uuid", None),
        )


class OpenFoodFactsService:
    TIMEOUT = 10

    transport: httpx.AsyncBaseTransport | None = None
    """The default transport, replaced by the tests"""

    def __init__(
        self, transport: httpx.AsyncBaseTransport | None = None, config: OpenFoodFactsConfig | None = None
    ) -> None:
        if transport:
            self.transport = transport
        self.config = config or OpenFoodFactsConfig()

    @staticmethod
    def enabled() -> bool:
        return get_app_settings().NUTRITION_OPEN_FOOD_FACTS

    @staticmethod
    def is_barcode(value: str) -> bool:
        return bool(BARCODE_PATTERN.match(value.strip()))

    @staticmethod
    def _number(value: Any) -> float | None:
        try:
            number = float(value)
        except TypeError, ValueError:
            return None
        return number if number >= 0 else None

    @classmethod
    def to_food(cls, product: dict) -> CompositionFood | None:
        """The product as a food of the composition tables, or None when its main nutrition facts are missing"""
        code = str(product.get("code") or "").strip()
        name = next(
            (
                str(product[key]).strip()
                for key in ("product_name_fr", "product_name", "product_name_en")
                if str(product.get(key) or "").strip()
            ),
            "",
        )
        nutriments = product.get("nutriments") or {}
        if not code or not name or not isinstance(nutriments, dict):
            return None

        nutrients: dict[str, float | None] = {}
        calories = cls._number(nutriments.get("energy-kcal_100g"))
        if calories is None and (kj := cls._number(nutriments.get("energy-kj_100g"))) is not None:
            calories = kj / 4.184
        nutrients["calories"] = calories
        for key, (field, factor) in NUTRIENTS.items():
            value = cls._number(nutriments.get(key))
            nutrients[field] = round(value * factor, 4) if value is not None else None
        mono = cls._number(nutriments.get("monounsaturated-fat_100g"))
        poly = cls._number(nutriments.get("polyunsaturated-fat_100g"))
        nutrients["unsaturated_fat_content"] = (
            (mono or 0) + (poly or 0) if mono is not None or poly is not None else None
        )

        if any(nutrients.get(field) is None for field in CORE_FIELDS):
            return None

        brand = cls._brand(product)
        if brand:
            # a parenthesis is left out of the name's main part when matching it with a food
            name = f"{name} ({brand})"
        return CompositionFood(source="off", code=code, name=name, name_en="", nutrients=nutrients)

    @staticmethod
    def _brand(product: dict) -> str:
        brands = product.get("brands")
        return (brands[0] if isinstance(brands, list) and brands else str(brands or "").split(",")[0]).strip()

    def to_result(self, product: dict) -> FoodReferenceResult | None:
        """The product as a normalized reference food, or None when its main nutrition facts are missing"""
        food = self.to_food(product)
        if food is None:
            return None
        brand = self._brand(product)
        name = food.name[: -len(f" ({brand})")] if brand else food.name
        name_en = str(product.get("product_name_en") or "").strip() or None
        return FoodReferenceResult(
            source="off",
            code=food.code,
            name=name,
            name_en=name_en,
            nutrients=dict(food.nutrients),
            brand=brand or None,
            url=f"{self.config.base_url}/product/{food.code}",
        )

    @staticmethod
    def rank(query: str, foods: list[CompositionFood]) -> list[CompositionMatch]:
        """The products named like the query, ranked like the foods of the composition tables"""
        q = normalize_tokens(query)
        if not q:
            return []
        query_text = " ".join(q)
        ranked: list[tuple[tuple[int, float, int], CompositionMatch]] = []
        for index, food in enumerate(foods):
            tokens = normalize_tokens(food.name.split("(")[0])
            if not tokens:
                continue
            score = fuzz.token_set_ratio(query_text, " ".join(tokens))
            tier = CompositionTable.tier(q, tokens, head_tokens(food.name))
            if score >= 50:
                ranked.append(((tier, -round(score), index), CompositionMatch(food, float(score), tier)))
        ranked.sort(key=lambda item: item[0])
        return [match for _, match in ranked]

    @staticmethod
    def best(matches: list[CompositionMatch]) -> CompositionMatch | None:
        """The product confident enough to be used without anyone choosing: named like the food itself"""
        return matches[0] if matches and matches[0].tier <= 1 else None

    async def _get(self, path: str, params: dict[str, Any] | None, limiter: _RateLimiter) -> dict:
        if not limiter.acquire():
            raise OpenFoodFactsRateLimited("Too many requests to Open Food Facts, try again in a minute")
        try:
            async with httpx.AsyncClient(
                transport=self.transport,
                timeout=self.TIMEOUT,
                headers={"User-Agent": self.config.user_agent},
                auth=httpx.BasicAuth(*DEV_AUTH) if self.config.is_dev else None,
            ) as client:
                response = await client.get(
                    self.config.base_url + path, params={**(params or {}), **self.config.params}
                )
        except httpx.HTTPError as e:
            raise OpenFoodFactsError(f"Could not reach Open Food Facts: {e}") from e

        if response.status_code in (429, 503):
            raise OpenFoodFactsRateLimited("Open Food Facts is overloaded or limits the requests, try again later")
        if response.status_code == 404:
            return {}
        if response.status_code != 200:
            raise OpenFoodFactsError(f"Open Food Facts answered with the status {response.status_code}")
        try:
            data = response.json()
        except ValueError as e:
            raise OpenFoodFactsError("Open Food Facts gave an invalid answer") from e
        return data if isinstance(data, dict) else {}

    async def _search_products(self, query: str) -> list[dict]:
        """The raw products found for the query, cached"""
        key = f"{self.config.mode}:search:{query.lower()}"
        found, cached = _cache.get(key)
        if not found:
            data = await self._get(
                SEARCH_PATH,
                {
                    "search_terms": query,
                    "search_simple": 1,
                    "action": "process",
                    "json": 1,
                    "fields": FIELDS,
                    "page_size": 25,
                    "lc": "fr",
                },
                _search_limiter,
            )
            cached = [product for product in data.get("products") or [] if isinstance(product, dict)]
            _cache.set(key, cached)
        return cached

    async def search(self, query: str, limit: int = 10) -> list[CompositionFood]:
        """The products named like the query that have their main nutrition facts, most relevant first"""
        query = " ".join(query.split())
        if not query:
            return []
        # extra products are asked for, as some lack nutrition facts
        products = await self._search_products(query)
        return [food for product in products if (food := self.to_food(product))][:limit]

    async def search_references(self, query: str, limit: int = 25) -> list[FoodReferenceResult]:
        """Like `search`, as normalized reference foods, without writing anything"""
        query = " ".join(query.split())
        if not query:
            return []
        products = await self._search_products(query)
        return [result for product in products if (result := self.to_result(product))][:limit]

    async def product(self, barcode: str) -> CompositionFood | None:
        barcode = barcode.strip()
        if not self.is_barcode(barcode):
            return None
        key = f"{self.config.mode}:product:{barcode}"
        found, cached = _cache.get(key)
        if not found:
            data = await self._get(PRODUCT_PATH.format(barcode=barcode), {"fields": FIELDS}, _product_limiter)
            product = data.get("product") if data.get("status") in (1, "1", "success") else None
            cached = self.to_food(product) if isinstance(product, dict) else None
            _cache.set(key, cached)
        return cached


async def search_open_food_facts(
    query: str,
    config: OpenFoodFactsConfig | Any = None,
    limit: int = 25,
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[FoodReferenceResult]:
    """
    Searches Open Food Facts with the group's settings (an `OpenFoodFactsConfig` or the group preferences) and returns
    the products having their main nutrition facts, normalized. Nothing is written to the database. Raises
    `OpenFoodFactsError` (or `OpenFoodFactsRateLimited`) when the API can't answer.
    """
    if not isinstance(config, OpenFoodFactsConfig):
        config = OpenFoodFactsConfig.from_preferences(config)
    return await OpenFoodFactsService(transport=transport, config=config).search_references(query, limit)
