import asyncio
from collections.abc import Callable, Generator

import httpx
import pytest

from mealie.services.recipe import usda_service
from mealie.services.recipe.usda_service import (
    UsdaConfig,
    UsdaError,
    UsdaInvalidKey,
    UsdaRateLimited,
    UsdaService,
    search_usda,
)


def _nutrient(nutrient_id: int, value: float, unit: str) -> dict:
    return {"nutrientId": nutrient_id, "value": value, "unitName": unit}


BUTTER = {
    "fdcId": 173410,
    "description": "Butter, salted",
    "dataType": "SR Legacy",
    "foodNutrients": [
        _nutrient(1008, 717, "KCAL"),
        _nutrient(1005, 0.06, "G"),
        _nutrient(1004, 81.11, "G"),
        _nutrient(1258, 51.368, "G"),
        _nutrient(1292, 21.021, "G"),
        _nutrient(1293, 3.043, "G"),
        _nutrient(1003, 0.85, "G"),
        _nutrient(1253, 215, "MG"),
        _nutrient(1093, 643, "MG"),
        _nutrient(1106, 684, "UG"),
        _nutrient(1114, 0.0006, "MG"),
    ],
}

APPLE = {
    "fdcId": 1750340,
    "description": "Apples, fuji, with skin, raw",
    "dataType": "Foundation",
    "foodNutrients": [
        _nutrient(2047, 64.7, "KCAL"),
        _nutrient(2048, 58.2, "KCAL"),
        _nutrient(1005, 15.7, "G"),
        _nutrient(1079, 2.08, "G"),
        _nutrient(1063, 13.3, "G"),
        _nutrient(1004, 0.162, "G"),
        _nutrient(1003, 0.148, "G"),
        _nutrient(1092, 104, "MG"),
    ],
}


@pytest.fixture(autouse=True)
def reset() -> Generator[None]:
    usda_service.reset_state()
    yield
    usda_service.reset_state()


def _service(
    handler: Callable[[httpx.Request], httpx.Response], config: UsdaConfig | None = None
) -> tuple[UsdaService, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    return UsdaService(httpx.MockTransport(record), config=config), requests


def test_converts_the_nutrients_to_mealie_units():
    result = UsdaService.to_result(BUTTER)

    assert result is not None
    assert (result.source, result.code, result.name, result.name_en) == (
        "usda",
        "173410",
        "Butter, salted",
        "Butter, salted",
    )
    assert result.url == "https://fdc.nal.usda.gov/food-details/173410/nutrients"
    assert result.nutrients["calories"] == 717
    assert result.nutrients["fat_content"] == pytest.approx(81.11)
    assert result.nutrients["unsaturated_fat_content"] == pytest.approx(24.064)
    assert result.nutrients["cholesterol_content"] == 215  # mg
    assert result.nutrients["vitamin_a_content"] == 684  # µg
    assert result.nutrients["vitamin_d_content"] == pytest.approx(0.6)  # µg, converted from mg
    assert result.nutrients["fiber_content"] is None


def test_foundation_foods_use_their_fallback_nutrients_and_exclude_fibre_from_carbohydrates():
    result = UsdaService.to_result(APPLE)

    assert result is not None
    assert result.nutrients["calories"] == pytest.approx(64.7)
    assert result.nutrients["sugar_content"] == pytest.approx(13.3)
    assert result.nutrients["carbohydrate_content"] == pytest.approx(15.7 - 2.08)


@pytest.mark.parametrize(
    "food",
    [
        {**BUTTER, "foodNutrients": [_nutrient(1008, 717, "KCAL"), _nutrient(1004, 81, "G")]},
        {**BUTTER, "description": ""},
        {**BUTTER, "fdcId": None},
    ],
)
def test_incomplete_foods_are_skipped(food: dict):
    assert UsdaService.to_result(food) is None


def test_search_sends_the_demo_key_by_default_and_is_cached():
    service, requests = _service(lambda request: httpx.Response(200, json={"foods": [BUTTER, {"fdcId": 1}]}))

    first = asyncio.run(service.search("butter  salted"))
    second = asyncio.run(service.search("Butter salted"))

    assert [r.code for r in first] == [r.code for r in second] == ["173410"]
    assert len(requests) == 1
    url = requests[0].url
    assert (url.host, url.path) == ("api.nal.usda.gov", "/fdc/v1/foods/search")
    assert url.params["query"] == "butter salted"
    assert url.params["pageSize"] == "25"
    assert url.params["dataType"] == "Foundation,SR Legacy"
    assert url.params["api_key"] == "DEMO_KEY"
    assert requests[0].headers["User-Agent"].startswith("Mealie/")


def test_search_uses_the_group_key():
    service, requests = _service(lambda request: httpx.Response(200, json={"foods": []}), UsdaConfig(api_key=" k3y "))

    asyncio.run(service.search("butter"))

    assert requests[0].url.params["api_key"] == "k3y"


def test_disabled_api_is_not_called():
    service, requests = _service(
        lambda request: httpx.Response(200, json={"foods": [BUTTER]}), UsdaConfig(enabled=False)
    )

    assert asyncio.run(service.search("butter")) == []
    assert requests == []


def test_demo_key_is_rate_limited_without_waiting():
    service, requests = _service(lambda request: httpx.Response(200, json={"foods": []}))

    for i in range(30):
        asyncio.run(service.search(f"food {i}"))
    with pytest.raises(UsdaRateLimited):
        asyncio.run(service.search("one too many"))

    assert len(requests) == 30
    # another key has its own quota
    other, _ = _service(lambda request: httpx.Response(200, json={"foods": []}), UsdaConfig(api_key="mine"))
    assert asyncio.run(other.search("one too many")) == []


@pytest.mark.parametrize(
    ("response", "error"),
    [
        (httpx.Response(429), UsdaRateLimited),
        (httpx.Response(403, json={"error": {"code": "API_KEY_INVALID"}}), UsdaInvalidKey),
        (httpx.Response(500), UsdaError),
        (httpx.Response(200, text="not json"), UsdaError),
    ],
)
def test_search_errors(response: httpx.Response, error: type[Exception]):
    service, _ = _service(lambda request: response)

    with pytest.raises(error):
        asyncio.run(service.search("butter"))


def test_unreachable():
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no network")

    service, _ = _service(fail)
    with pytest.raises(UsdaError):
        asyncio.run(service.search("butter"))


def test_search_usda_reads_the_group_preferences():
    class Preferences:
        usda_api_enabled = True
        usda_api_key = "group-key"

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"foods": [APPLE, BUTTER]})

    results = asyncio.run(search_usda("butter", Preferences(), limit=1, transport=httpx.MockTransport(handler)))

    assert [r.code for r in results] == ["1750340"]
    assert requests[0].url.params["api_key"] == "group-key"
    assert UsdaConfig.from_preferences(None).effective_api_key == "DEMO_KEY"
