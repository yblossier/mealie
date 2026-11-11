import asyncio
from collections.abc import Callable, Generator

import httpx
import pytest

from mealie.services.recipe import open_food_facts_service
from mealie.services.recipe.food_reference_types import FoodReferenceResult
from mealie.services.recipe.open_food_facts_service import (
    OpenFoodFactsConfig,
    OpenFoodFactsError,
    OpenFoodFactsRateLimited,
    OpenFoodFactsService,
    search_open_food_facts,
)

PUFF_PASTRY = {
    "code": "3392590205130",
    "product_name": "Pâte feuilletée",
    "brands": ["Croustipate"],
    "nutriments": {
        "energy-kcal_100g": 378,
        "carbohydrates_100g": 41,
        "sugars_100g": 2.3,
        "fat_100g": 19,
        "saturated-fat_100g": 13,
        "monounsaturated-fat_100g": 4,
        "polyunsaturated-fat_100g": 1.5,
        "proteins_100g": 6.1,
        "fiber_100g": 1.4,
        "sodium_100g": 0.44,
        "calcium_100g": 0.12,
        "vitamin-a_100g": 0.0002,
    },
}


@pytest.fixture(autouse=True)
def reset() -> Generator[None]:
    open_food_facts_service.reset_state()
    yield
    open_food_facts_service.reset_state()


def _service(
    handler: Callable[[httpx.Request], httpx.Response], config: OpenFoodFactsConfig | None = None
) -> tuple[OpenFoodFactsService, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    return OpenFoodFactsService(httpx.MockTransport(record), config=config), requests


def test_converts_the_nutrients_to_mealie_units():
    food = OpenFoodFactsService.to_food(PUFF_PASTRY)

    assert food is not None
    assert (food.source, food.code, food.name) == ("off", "3392590205130", "Pâte feuilletée (Croustipate)")
    assert food.nutrients["calories"] == 378
    assert food.nutrients["fat_content"] == 19
    assert food.nutrients["unsaturated_fat_content"] == pytest.approx(5.5)
    assert food.nutrients["sodium_content"] == pytest.approx(440)  # mg
    assert food.nutrients["calcium_content"] == pytest.approx(120)  # mg
    assert food.nutrients["vitamin_a_content"] == pytest.approx(200)  # µg
    assert food.nutrients["cholesterol_content"] is None


def test_energy_falls_back_on_kilojoules():
    product = {**PUFF_PASTRY, "nutriments": {**PUFF_PASTRY["nutriments"], "energy-kcal_100g": None}}
    product["nutriments"]["energy-kj_100g"] = 1578

    food = OpenFoodFactsService.to_food(product)

    assert food is not None
    assert food.nutrients["calories"] == pytest.approx(377, abs=1)


@pytest.mark.parametrize(
    "product",
    [
        {**PUFF_PASTRY, "nutriments": {"energy-kcal_100g": 378, "fat_100g": 19}},
        {**PUFF_PASTRY, "product_name": ""},
        {**PUFF_PASTRY, "code": ""},
        {**PUFF_PASTRY, "nutriments": {**PUFF_PASTRY["nutriments"], "proteins_100g": "n/a"}},
    ],
)
def test_incomplete_products_are_skipped(product: dict):
    assert OpenFoodFactsService.to_food(product) is None


def test_rank_puts_the_products_named_like_the_food_first():
    foods = [
        OpenFoodFactsService.to_food({**PUFF_PASTRY, "code": "1", "product_name": "Feuilletés apéritif"}),
        OpenFoodFactsService.to_food({**PUFF_PASTRY, "code": "2", "product_name": "Pâte feuilletée pur beurre"}),
        OpenFoodFactsService.to_food({**PUFF_PASTRY, "code": "3", "product_name": "Pâte feuilletée"}),
    ]

    matches = OpenFoodFactsService.rank("pâte feuilletée", [food for food in foods if food])

    assert [(match.food.code, match.tier) for match in matches][:2] == [("3", 0), ("2", 1)]
    assert OpenFoodFactsService.best(matches) == matches[0]
    assert OpenFoodFactsService.best([match for match in matches if match.tier > 1]) is None


def test_search_is_cached():
    service, requests = _service(
        lambda request: httpx.Response(200, json={"count": 2, "products": [PUFF_PASTRY, {"code": "x"}]})
    )

    first = asyncio.run(service.search("pâte  feuilletée"))
    second = asyncio.run(service.search("Pâte feuilletée"))

    assert [food.code for food in first] == [food.code for food in second] == ["3392590205130"]
    assert len(requests) == 1
    assert requests[0].url.host == "world.openfoodfacts.org"
    assert requests[0].url.path == "/cgi/search.pl"
    assert requests[0].url.params["search_terms"] == "pâte feuilletée"
    assert requests[0].url.params["json"] == "1"
    assert "app_name" not in requests[0].url.params
    assert "Authorization" not in requests[0].headers
    assert requests[0].headers["User-Agent"].startswith("Mealie/")


def test_search_is_rate_limited_without_waiting():
    service, requests = _service(lambda request: httpx.Response(200, json={"count": 0, "products": []}))

    for i in range(10):
        asyncio.run(service.search(f"food {i}"))
    with pytest.raises(OpenFoodFactsRateLimited):
        asyncio.run(service.search("one too many"))

    assert len(requests) == 10


@pytest.mark.parametrize(
    ("response", "error"),
    [
        (httpx.Response(503, text="<html>"), OpenFoodFactsRateLimited),
        (httpx.Response(429), OpenFoodFactsRateLimited),
        (httpx.Response(500), OpenFoodFactsError),
        (httpx.Response(200, text="not json"), OpenFoodFactsError),
    ],
)
def test_search_errors(response: httpx.Response, error: type[Exception]):
    service, _ = _service(lambda request: response)

    with pytest.raises(error):
        asyncio.run(service.search("pâte feuilletée"))


def test_unreachable():
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no network")

    service, _ = _service(fail)
    with pytest.raises(OpenFoodFactsError):
        asyncio.run(service.search("pâte feuilletée"))


def test_product_by_barcode():
    service, requests = _service(
        lambda request: (
            httpx.Response(200, json={"status": 1, "product": PUFF_PASTRY})
            if request.url.path.endswith("/3392590205130")
            else httpx.Response(404, json={"status": 0})
        )
    )

    food = asyncio.run(service.product(" 3392590205130 "))
    assert food is not None and food.code == "3392590205130"
    assert asyncio.run(service.product("3392590205130")) == food
    assert asyncio.run(service.product("00000000")) is None
    assert asyncio.run(service.product("not-a-barcode")) is None

    assert len(requests) == 2
    assert requests[0].url.host == "world.openfoodfacts.org"


def test_dev_mode_uses_the_staging_server_with_its_credentials_and_the_app_parameters():
    config = OpenFoodFactsConfig(mode="dev", app_name="MyMealie", app_version="1.2", app_uuid=" abc-123 ")
    service, requests = _service(lambda request: httpx.Response(200, json={"products": [PUFF_PASTRY]}), config)

    asyncio.run(service.search("pâte feuilletée"))
    asyncio.run(service.product("3392590205130"))

    for request in requests:
        assert request.url.host == "world.openfoodfacts.net"
        assert request.headers["Authorization"] == httpx.BasicAuth("off", "off")._auth_header
        assert request.url.params["app_name"] == "MyMealie"
        assert request.url.params["app_version"] == "1.2"
        assert request.url.params["app_uuid"] == "abc-123"
        assert request.headers["User-Agent"].startswith("MyMealie/1.2 (Mealie/")


def test_cache_is_per_mode():
    prod, prod_requests = _service(lambda request: httpx.Response(200, json={"products": [PUFF_PASTRY]}))
    dev, dev_requests = _service(
        lambda request: httpx.Response(200, json={"products": []}), OpenFoodFactsConfig(mode="dev")
    )

    assert len(asyncio.run(prod.search("pâte feuilletée"))) == 1
    assert asyncio.run(dev.search("pâte feuilletée")) == []
    assert len(prod_requests) == len(dev_requests) == 1


def test_config_from_preferences():
    class Preferences:
        off_mode = "dev"
        off_app_name = "App"
        off_app_version = None
        off_app_uuid = ""

    config = OpenFoodFactsConfig.from_preferences(Preferences())

    assert config.base_url == "https://world.openfoodfacts.net"
    assert config.params == {"app_name": "App"}
    assert OpenFoodFactsConfig.from_preferences(None).base_url == "https://world.openfoodfacts.org"
    assert OpenFoodFactsConfig(mode="unknown").base_url == "https://world.openfoodfacts.org"


def test_search_open_food_facts_returns_normalized_results():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"products": [{**PUFF_PASTRY, "product_name_en": "Puff pastry"}, {"code": "x"}]}
        )

    results = asyncio.run(
        search_open_food_facts("pâte feuilletée", OpenFoodFactsConfig(), transport=httpx.MockTransport(handler))
    )

    assert results == [
        FoodReferenceResult(
            source="off",
            code="3392590205130",
            name="Pâte feuilletée",
            name_en="Puff pastry",
            nutrients=OpenFoodFactsService.to_food(PUFF_PASTRY).nutrients,  # type: ignore[union-attr]
            brand="Croustipate",
            url="https://world.openfoodfacts.org/product/3392590205130",
        )
    ]
