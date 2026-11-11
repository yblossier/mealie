import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from mealie.services.recipe.ciqual_import import ciqual_nutrients, parse_ciqual_value
from mealie.services.recipe.food_composition_service import (
    CIQUAL_DEFAULTS,
    FoodCompositionService,
    get_table,
    normalize,
)

BUILD_SCRIPT = Path(__file__).parents[3] / "dev" / "scripts" / "build_food_composition_tables.py"


@pytest.fixture(scope="module")
def build() -> ModuleType:
    spec = importlib.util.spec_from_file_location("build_food_composition_tables", BUILD_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def composition() -> FoodCompositionService:
    return FoodCompositionService()


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("12,5", 12.5),
        (" 3 ", 3.0),
        ("traces", 0.0),
        ("< 0,5", 0.25),
        ("-", None),
        ("", None),
        (None, None),
        ("n/a", None),
    ],
)
def test_parse_ciqual_value(raw: str | None, expected: float | None):
    assert parse_ciqual_value(raw) == expected


def test_usda_carbohydrates_exclude_fiber(build: ModuleType):
    nutrients = build.usda_nutrients({"1005": 10.0, "1079": 2.5, "1292": 1.0, "1293": 0.5})
    assert nutrients["carbohydrate_content"] == 7.5
    assert nutrients["unsaturated_fat_content"] == 1.5
    assert nutrients["calories"] is None


def test_ciqual_vitamin_a_counts_beta_carotene():
    nutrients = ciqual_nutrients({"51200": 10.0, "51330": 120.0, "333": 50.0})
    assert nutrients["vitamin_a_content"] == 20.0
    assert nutrients["calories"] == 50.0


@pytest.mark.parametrize(
    "portions, expected",
    [
        ([(1, "large", 70.0), (1, 'medium (2-1/8" dia)', 58.0)], 58.0),
        ([(1, "cup, sections", 212.0), (1, "fruit without seeds", 84.0)], 84.0),
        ([(2, "medium", 100.0)], None),
        ([(1, "package (10 oz)", 284.0)], None),
        ([(1, "cup", 150.0)], None),
    ],
)
def test_piece_weight(build: ModuleType, portions: list, expected: float | None):
    assert build.piece_weight(portions) == expected


def test_tables_are_shipped():
    ciqual, usda = get_table("ciqual"), get_table("usda")
    assert ciqual.version and ciqual.attribution and ciqual.license
    assert usda.version and usda.attribution and usda.license
    assert ciqual.get("13009") is not None
    assert usda.get("167746") is not None or usda.has_candidates("lemon")


def test_ciqual_defaults_exist():
    table = get_table("ciqual")
    missing = {name: code for name, code in CIQUAL_DEFAULTS.items() if table.get(code) is None}
    assert missing == {}


def test_normalize():
    assert normalize("Œufs  frais") == normalize("oeuf frais")
    assert normalize("Citrons") == "citron"


def test_lemon_is_found_in_ciqual(composition: FoodCompositionService):
    match = composition.best("citron")
    assert match is not None
    assert (match.food.source, match.food.code) == ("ciqual", "13009")
    assert match.food.nutrients["calories"]
    assert composition.average_weight(match.food) == pytest.approx(58, abs=1)


def test_plural_and_english_names(composition: FoodCompositionService):
    match = composition.best("citrons")
    assert match is not None and match.food.code == "13009"

    match = composition.best("lemon")
    assert match is not None
    assert match.food.source in ("ciqual", "usda")
    assert "lemon" in match.food.name.lower() or "citron" in match.food.name.lower()


def test_staples_use_their_default(composition: FoodCompositionService):
    for name in ("farine", "sucre", "beurre", "lait"):
        match = composition.best(name)
        assert match is not None, name
        assert match.food.code == CIQUAL_DEFAULTS[normalize(name)], name


def test_unknown_food_is_not_found(composition: FoodCompositionService):
    assert composition.best("zqxwv plorbt") is None
    assert composition.search("zqxwv plorbt") == []


def test_search_lists_ciqual_first(composition: FoodCompositionService):
    results = composition.search("citron", 10)
    assert results
    assert results[0].food.source == "ciqual"
    by_source = composition.search_by_source("lemon", 5)
    assert all(len(matches) <= 5 for matches in by_source.values())
