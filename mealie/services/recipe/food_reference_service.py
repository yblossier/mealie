"""
The nutrition referential of the database, shared by all the groups, and the way the nutrition sources are looked up:

1. the referential of the source is searched first;
2. when it has no relevant food, the source's API (Open Food Facts, USDA FoodData Central) is called;
3. when the API has no relevant food either, the foods of both are returned, without duplicates.

The foods found through an API that the referential doesn't know yet are added to it, so it keeps getting richer.

A food is relevant when its name's main part is the query or starts with it (tier 0 or 1 of the composition tables'
ranking). Ciqual has no API: its referential is imported from the open data of Anses (see `CiqualRefreshService`).
Until a source is imported into the database, the table bundled with Mealie stands for its imported foods.
"""

import threading
from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from mealie.core.root_logger import get_logger
from mealie.db.models.server.food_composition import FoodCompositionFoodModel
from mealie.repos.repository_food_composition import ORIGIN_API, ORIGIN_IMPORT, RepositoryFoodComposition
from mealie.services.recipe.food_composition_service import (
    SOURCES,
    CompositionFood,
    CompositionMatch,
    CompositionSource,
    CompositionTable,
    get_table,
    normalize,
)
from mealie.services.recipe.food_reference_types import NUTRIENT_KEYS, FoodReferenceResult

logger = get_logger()

RELEVANT_TIER = 1
"""The worst tier of a relevant food: its name's main part starts with the query"""

ApiFood = CompositionFood | FoodReferenceResult
ApiSearch = Callable[[str], Awaitable[Sequence[ApiFood]]]

_lock = threading.Lock()
_base_tables: dict[str, tuple[tuple, CompositionTable]] = {}
"""The imported foods of each source, by the stamp of the imported rows"""
_tables: dict[str, tuple[tuple, CompositionTable]] = {}
"""The whole referential of each source, by the stamp of all its rows"""


def invalidate_tables(source: str | None = None) -> None:
    """Forgets the cached referential tables, for a source or all of them"""
    with _lock:
        for cache in (_base_tables, _tables):
            if source:
                cache.pop(source, None)
            else:
                cache.clear()


def to_composition_food(food: ApiFood) -> CompositionFood:
    if isinstance(food, CompositionFood):
        return food
    name = food.name
    if food.brand and food.source == "off":
        # like the bundled tables, a parenthesis is left out of the name's main part when matching it
        name = f"{name} ({food.brand})"
    return CompositionFood(
        source=food.source,
        code=str(food.code),
        name=name,
        name_en=food.name_en or "",
        nutrients={key: food.nutrients.get(key) for key in NUTRIENT_KEYS},
        average_weight=food.average_weight,
    )


def model_to_food(row: FoodCompositionFoodModel) -> CompositionFood:
    nutrients = row.nutrients or {}
    name = row.name
    if row.brand and row.source == "off" and not name.endswith(f"({row.brand})"):
        name = f"{name} ({row.brand})"
    return CompositionFood(
        source=row.source,  # type: ignore[arg-type]
        code=row.code,
        name=name,
        name_en=row.name_en or "",
        nutrients={key: nutrients.get(key) for key in NUTRIENT_KEYS},
        average_weight=row.average_weight,
    )


def to_row(food: ApiFood) -> dict[str, Any]:
    """The columns of the referential for a food found through an API"""
    brand = getattr(food, "brand", None)
    name = food.name
    if isinstance(food, CompositionFood) and food.source == "off" and name.endswith(")") and " (" in name:
        # Open Food Facts products carry their brand in a parenthesis
        name, _, rest = name.rpartition(" (")
        brand = rest[:-1] or None
    return {
        "code": str(food.code),
        "name": name[:512],
        "name_en": (food.name_en or None) and food.name_en[:512],
        "nutrients": {key: food.nutrients.get(key) for key in NUTRIENT_KEYS},
        "average_weight": food.average_weight,
        "brand": brand[:255] if brand else None,
        "url": getattr(food, "url", None),
    }


def is_relevant(matches: Iterable[CompositionMatch]) -> bool:
    return any(match.tier <= RELEVANT_TIER for match in matches)


def merge(*groups: Iterable[CompositionMatch]) -> list[CompositionMatch]:
    """The matches in the given order, without duplicates: the same food of a source, or the same name"""
    seen_codes: set[tuple[str, str]] = set()
    seen_names: set[str] = set()
    merged: list[CompositionMatch] = []
    for group in groups:
        for match in group:
            key = (match.food.source, match.food.code)
            name = normalize(match.food.name)
            if key in seen_codes or (name and name in seen_names):
                continue
            seen_codes.add(key)
            if name:
                seen_names.add(name)
            merged.append(match)
    return merged


@dataclass
class ReferenceLookup:
    matches: list[CompositionMatch] = field(default_factory=list)
    """The foods to use, best first: the referential's when relevant, else the API's when relevant, else both"""
    db_matches: list[CompositionMatch] = field(default_factory=list)
    api_matches: list[CompositionMatch] = field(default_factory=list)
    api_foods: list[CompositionFood] = field(default_factory=list)
    """The whole API answer, including the foods it found by something else than their name (e.g. their brand)"""
    api_called: bool = False
    error: Exception | None = None
    added: int = 0
    """The number of foods of the API answer added to the referential"""


class FoodReferenceService:
    def __init__(self, repo: RepositoryFoodComposition) -> None:
        self.repo = repo

    # ==================================================================================================================
    # Tables

    def _base_table(self, source: CompositionSource, stamp: tuple) -> CompositionTable:
        cached = _base_tables.get(source)
        if cached and cached[0] == stamp:
            return cached[1]
        if stamp:
            rows = self.repo.get_all(source, ORIGIN_IMPORT)
            table = CompositionTable.from_foods(source, (model_to_food(row) for row in rows))
        elif source in SOURCES:
            # not imported into the database yet: the table bundled with Mealie
            table = get_table(source)
        else:
            table = CompositionTable.from_foods(source, [])
        _base_tables[source] = (stamp, table)
        return table

    def table(self, source: CompositionSource) -> CompositionTable:
        """The referential of the source: its imported foods (or the bundled table) and the ones kept from its API"""
        stamp = self.repo.stamp(source)
        cached = _tables.get(source)
        if cached and cached[0] == stamp:
            return cached[1]
        with _lock:
            cached = _tables.get(source)
            if cached and cached[0] == stamp:
                return cached[1]
            imported = tuple(item for item in stamp if item[0] == ORIGIN_IMPORT)
            table = self._base_table(source, imported)
            if any(item[0] == ORIGIN_API for item in stamp):
                table = table.extended(model_to_food(row) for row in self.repo.get_all(source, ORIGIN_API))
            _tables[source] = (stamp, table)
            return table

    # ==================================================================================================================
    # Lookup

    def enrich(self, source: CompositionSource, foods: Iterable[ApiFood]) -> int:
        """Adds the foods found through the API of the source that the referential doesn't know yet"""
        table = self.table(source)
        rows = [to_row(food) for food in foods if food.source == source and table.get(str(food.code)) is None]
        if not rows:
            return 0
        try:
            return self.repo.add_api_foods(source, rows)
        except Exception as e:
            # the referential is only enriched on the way, the lookup has its answer anyway
            self.repo.session.rollback()
            logger.warning(f"Could not add {len(rows)} foods to the {source} referential: {e}")
            return 0

    @staticmethod
    def rank(query: str, source: CompositionSource, foods: Sequence[ApiFood], limit: int) -> list[CompositionMatch]:
        """The foods of an API answer named like the query, ranked like the foods of the composition tables"""
        table = CompositionTable.from_foods(source, (to_composition_food(food) for food in foods))
        return table.search(query, limit)

    async def lookup(
        self, source: CompositionSource, query: str, api: ApiSearch | None = None, limit: int = 10
    ) -> ReferenceLookup:
        """
        Searches the referential of the source, then its API when the referential has no relevant food, keeping the
        new foods of the API answer in the referential. An API failure leaves the referential's foods as the answer.
        """
        result = ReferenceLookup()
        result.db_matches = self.table(source).search(query, limit)
        result.matches = result.db_matches
        if api is None or is_relevant(result.db_matches) or not query.strip():
            return result

        result.api_called = True
        try:
            foods = [food for food in await api(query) if food.source == source]
        except Exception as e:
            logger.info(f"The {source} API could not be searched for '{query}': {e}")
            result.error = e
            return result

        result.api_foods = [to_composition_food(food) for food in foods]
        result.api_matches = self.rank(query, source, foods, limit)
        result.added = self.enrich(source, foods)
        if is_relevant(result.api_matches):
            result.matches = merge(result.api_matches)
        else:
            result.matches = merge(result.db_matches, result.api_matches)[:limit]
        return result
