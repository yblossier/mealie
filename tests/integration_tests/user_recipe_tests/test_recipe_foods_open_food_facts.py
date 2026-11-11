import json
from collections.abc import Callable, Generator
from dataclasses import dataclass, field

import httpx
import pytest
from fastapi.testclient import TestClient

from mealie.schema.openai.food_nutrition import OpenAIFoodNutritionMatch, OpenAIFoodNutritionMatches
from mealie.services.openai import OpenAIService
from mealie.services.recipe import open_food_facts_service
from mealie.services.recipe.food_nutrition_service import FoodNutritionService
from mealie.services.recipe.open_food_facts_service import OpenFoodFactsService
from mealie.services.recipe.usda_service import UsdaService
from tests import utils
from tests.utils import api_routes
from tests.utils.fixture_schemas import TestUser
from tests.utils.food_references import clear_food_references

OFF_SEARCH = "/api/foods/nutrition/references/open-food-facts"
FOOD_NAME = "zorglub feuilleté"
"""A food missing from the Ciqual and USDA tables"""


def _product(code: str, name: str) -> dict:
    return {
        "code": code,
        "product_name": name,
        "brands": ["Marque"],
        "nutriments": {
            "energy-kcal_100g": 378,
            "carbohydrates_100g": 41,
            "fat_100g": 19,
            "proteins_100g": 6.1,
            "sodium_100g": 0.44,
        },
    }


PRODUCTS = [_product("1111111111111", "Zorglub feuilleté pur beurre"), _product("2222222222222", "Zorglub feuilleté")]


@dataclass
class OffMock:
    requests: list[httpx.Request] = field(default_factory=list)
    handler: Callable[[httpx.Request], httpx.Response] | None = None
    """Replaces the default answers, made of PRODUCTS"""


@pytest.fixture()
def off(monkeypatch: pytest.MonkeyPatch) -> Generator[OffMock]:
    """Open Food Facts is enabled and its requests are mocked"""
    mock = OffMock()

    def respond(request: httpx.Request) -> httpx.Response:
        mock.requests.append(request)
        if mock.handler:
            return mock.handler(request)
        if request.url.path == "/cgi/search.pl":
            return httpx.Response(200, json={"count": len(PRODUCTS), "products": PRODUCTS})
        code = request.url.path.rsplit("/", 1)[-1]
        product = next((p for p in PRODUCTS if p["code"] == code), None)
        return httpx.Response(200, json={"status": 1, "product": product} if product else {"status": 0})

    open_food_facts_service.reset_state()
    clear_food_references()
    monkeypatch.setattr(OpenFoodFactsService, "enabled", staticmethod(lambda: True))
    monkeypatch.setattr(OpenFoodFactsService, "transport", httpx.MockTransport(respond))
    # USDA FoodData Central is searched online too, and knows none of these foods
    monkeypatch.setattr(
        UsdaService, "transport", httpx.MockTransport(lambda request: httpx.Response(200, json={"foods": []}))
    )
    yield mock
    open_food_facts_service.reset_state()
    clear_food_references()


def _create_food(api_client: TestClient, user: TestUser, name: str) -> str:
    response = api_client.post(api_routes.foods, json={"name": name}, headers=user.token)
    return utils.assert_deserialize(response, 201)["id"]


def _logs(api_client: TestClient, user: TestUser, food_id: str) -> list[dict]:
    response = api_client.get(f"{api_routes.foods_item_id(food_id)}/nutrition/logs", headers=user.token)
    return utils.assert_deserialize(response, 200)


def test_search_open_food_facts(api_client: TestClient, unique_user: TestUser, off: OffMock):
    response = api_client.get(OFF_SEARCH, params={"search": FOOD_NAME}, headers=unique_user.token)
    references = utils.assert_deserialize(response, 200)

    # the product named like the query first
    assert [reference["code"] for reference in references] == ["2222222222222", "1111111111111"]
    assert references[0]["source"] == "off"
    assert references[0]["name"] == "Zorglub feuilleté (Marque)"
    assert references[0]["nutrition"]["calories"] == "378"
    assert references[0]["nutrition"]["sodiumContent"] == "440"


def test_search_open_food_facts_by_barcode(api_client: TestClient, unique_user: TestUser, off: OffMock):
    response = api_client.get(OFF_SEARCH, params={"search": "1111111111111"}, headers=unique_user.token)
    [reference] = utils.assert_deserialize(response, 200)

    assert reference["code"] == "1111111111111"
    assert off.requests[0].url.host == "world.openfoodfacts.org"


def test_search_open_food_facts_uses_the_group_settings(api_client: TestClient, unique_user: TestUser, off: OffMock):
    response = api_client.put(
        api_routes.groups_preferences,
        json={"offMode": "dev", "offAppName": "MyMealie", "offAppVersion": "3.1", "offAppUuid": "uuid-1"},
        headers=unique_user.token,
    )
    assert response.status_code == 200

    response = api_client.get(OFF_SEARCH, params={"search": FOOD_NAME}, headers=unique_user.token)
    assert len(utils.assert_deserialize(response, 200)) == 2

    [request] = off.requests
    assert request.url.host == "world.openfoodfacts.net"
    assert request.url.params["search_terms"] == FOOD_NAME
    assert request.url.params["app_name"] == "MyMealie"
    assert request.url.params["app_version"] == "3.1"
    assert request.url.params["app_uuid"] == "uuid-1"
    assert request.headers["Authorization"].startswith("Basic ")


@pytest.mark.parametrize(("upstream", "expected"), [(503, 429), (500, 502)])
def test_search_open_food_facts_errors(
    api_client: TestClient, unique_user: TestUser, off: OffMock, upstream: int, expected: int
):
    off.handler = lambda request: httpx.Response(upstream)

    response = api_client.get(OFF_SEARCH, params={"search": FOOD_NAME}, headers=unique_user.token)
    assert response.status_code == expected


def test_search_open_food_facts_disabled(api_client: TestClient, unique_user: TestUser):
    response = api_client.get(OFF_SEARCH, params={"search": FOOD_NAME}, headers=unique_user.token)
    assert response.status_code == 503


def test_estimate_falls_back_on_open_food_facts_without_ai(api_client: TestClient, unique_user: TestUser, off: OffMock):
    food_id = _create_food(api_client, unique_user, FOOD_NAME)
    response = api_client.post(
        api_routes.foods_nutrition_estimate,
        json={"foods": [{"id": food_id, "name": FOOD_NAME}, {"name": "citron"}]},
        headers=unique_user.token,
    )
    product, lemon = utils.assert_deserialize(response, 200)

    assert (product["source"], product["referenceCode"]) == ("off", "2222222222222")
    assert product["referenceName"] == "Zorglub feuilleté (Marque)"
    assert product["nutrition"]["calories"] == "378"
    # the food found in Ciqual is not searched online
    assert lemon["source"] == "ciqual"
    assert len(off.requests) == 1

    [log] = _logs(api_client, unique_user, food_id)
    assert [step["kind"] for step in log["steps"]] == ["lookup", "usda", "open_food_facts"]
    step = log["steps"][2]
    assert step["kept"]
    assert step["response"]["match"] == "off:2222222222222"
    assert log["result"]["source"] == "off"


def test_estimate_skips_open_food_facts_when_rate_limited(api_client: TestClient, unique_user: TestUser, off: OffMock):
    off.handler = lambda request: httpx.Response(503)
    food_id = _create_food(api_client, unique_user, "zorglub ter")

    response = api_client.post(
        api_routes.foods_nutrition_estimate,
        json={"foods": [{"id": food_id, "name": "zorglub ter"}, {"name": "zorglub bis"}]},
        headers=unique_user.token,
    )
    first, second = utils.assert_deserialize(response, 200)

    assert first["source"] is None and second["source"] is None
    # the second food isn't searched once Open Food Facts refused the first
    assert len(off.requests) == 1

    [log] = _logs(api_client, unique_user, food_id)
    assert log["steps"][-1]["kind"] == "open_food_facts"
    assert log["steps"][-1]["error"]
    assert log["error"]


def test_ai_chooses_among_the_open_food_facts_products(
    api_client: TestClient, unique_user: TestUser, off: OffMock, monkeypatch: pytest.MonkeyPatch
):
    requests: list[list[dict]] = []

    async def mock_get_response(self, prompt: str, message: str, *args, response_schema=None, **kwargs):
        assert response_schema is OpenAIFoodNutritionMatches
        requests.append(json.loads(message))
        return OpenAIFoodNutritionMatches(
            foods=[OpenAIFoodNutritionMatch(name=FOOD_NAME, reference="off:1111111111111", average_weight=None)]
        )

    monkeypatch.setattr(OpenAIService, "get_response", mock_get_response)
    monkeypatch.setattr(FoodNutritionService, "ai_enabled", staticmethod(lambda service: True))

    response = api_client.post(
        api_routes.foods_nutrition_estimate, json={"foods": [{"name": FOOD_NAME}]}, headers=unique_user.token
    )
    [data] = utils.assert_deserialize(response, 200)

    [[item]] = requests
    candidates = [candidate["id"] for candidate in item["candidates"]]
    assert {"off:1111111111111", "off:2222222222222"} <= set(candidates)
    assert (data["source"], data["referenceCode"]) == ("off", "1111111111111")
