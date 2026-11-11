import json
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from mealie.core import exceptions
from mealie.routes.unit_and_foods.foods import IngredientFoodsController
from mealie.schema.openai.food_nutrition import (
    OpenAIFoodNutrition,
    OpenAIFoodNutritionMatch,
    OpenAIFoodNutritionMatches,
    OpenAIFoodsNutrition,
)
from mealie.schema.recipe.recipe_ingredient import IngredientFoodCreate
from mealie.services.openai import OpenAIService
from mealie.services.recipe.food_composition_service import FoodCompositionService
from mealie.services.recipe.food_nutrition_service import FoodNutritionService
from tests import utils
from tests.utils import api_routes
from tests.utils.factories import random_string
from tests.utils.fixture_schemas import TestUser


@pytest.fixture(scope="function")
def food(api_client: TestClient, unique_user: TestUser) -> Generator[dict]:
    data = IngredientFoodCreate(
        name=random_string(10),
        description=random_string(10),
    ).model_dump(by_alias=True)

    response = api_client.post(api_routes.foods, json=data, headers=unique_user.token)

    assert response.status_code == 201

    yield response.json()

    response = api_client.delete(api_routes.foods_item_id(response.json()["id"]), headers=unique_user.token)


def test_create_food(api_client: TestClient, unique_user: TestUser):
    data = IngredientFoodCreate(
        name=random_string(10),
        description=random_string(10),
    ).model_dump(by_alias=True)

    response = api_client.post(api_routes.foods, json=data, headers=unique_user.token)
    assert response.status_code == 201


def test_read_food(api_client: TestClient, food: dict, unique_user: TestUser):
    response = api_client.get(api_routes.foods_item_id(food["id"]), headers=unique_user.token)
    assert response.status_code == 200

    as_json = response.json()

    assert as_json["id"] == food["id"]
    assert as_json["name"] == food["name"]
    assert as_json["description"] == food["description"]


def test_update_food(api_client: TestClient, food: dict, unique_user: TestUser):
    update_data = {
        "id": food["id"],
        "name": random_string(10),
        "description": random_string(10),
    }
    response = api_client.put(
        api_routes.foods_item_id(food["id"]),
        json=update_data,
        headers=unique_user.token,
    )
    assert response.status_code == 200
    as_json = response.json()

    assert as_json["id"] == food["id"]
    assert as_json["name"] == update_data["name"]
    assert as_json["description"] == update_data["description"]


def test_delete_food(api_client: TestClient, food: dict, unique_user: TestUser):
    id = food["id"]

    response = api_client.delete(api_routes.foods_item_id(id), headers=unique_user.token)

    assert response.status_code == 200

    response = api_client.get(api_routes.foods_item_id(id), headers=unique_user.token)
    assert response.status_code == 404


def test_food_extras(
    api_client: TestClient,
    unique_user: TestUser,
):
    key_str_1 = random_string()
    val_str_1 = random_string()

    key_str_2 = random_string()
    val_str_2 = random_string()

    # create a food with extras
    new_food_data: dict = {"name": random_string()}
    new_food_data["extras"] = {key_str_1: val_str_1}

    response = api_client.post(api_routes.foods, json=new_food_data, headers=unique_user.token)
    food_as_json = utils.assert_deserialize(response, 201)

    # make sure the extra persists
    extras = food_as_json["extras"]
    assert key_str_1 in extras
    assert extras[key_str_1] == val_str_1

    # add more extras to the food
    food_as_json["extras"][key_str_2] = val_str_2

    response = api_client.put(
        api_routes.foods_item_id(food_as_json["id"]),
        json=food_as_json,
        headers=unique_user.token,
    )
    food_as_json = utils.assert_deserialize(response, 200)

    # make sure both the new extra and original extra persist
    extras = food_as_json["extras"]
    assert key_str_1 in extras
    assert key_str_2 in extras
    assert extras[key_str_1] == val_str_1
    assert extras[key_str_2] == val_str_2


def test_food_nutrition_crud(api_client: TestClient, food: dict, unique_user: TestUser):
    assert food["nutrition"] is None

    food["nutrition"] = {
        "calories": "52",
        "proteinContent": "0.3",
        "sugarContent": "",
        "calciumContent": "6",
        "vitaminCContent": "4.6",
    }
    response = api_client.put(api_routes.foods_item_id(food["id"]), json=food, headers=unique_user.token)
    food_as_json = utils.assert_deserialize(response, 200)
    assert food_as_json["nutrition"]["calories"] == "52"
    assert food_as_json["nutrition"]["proteinContent"] == "0.3"
    assert food_as_json["nutrition"]["sugarContent"] is None
    assert food_as_json["nutrition"]["calciumContent"] == "6"
    assert food_as_json["nutrition"]["vitaminCContent"] == "4.6"

    # updating the existing values must not insert a second row for the food
    food_as_json["nutrition"]["calories"] = "60"
    response = api_client.put(api_routes.foods_item_id(food["id"]), json=food_as_json, headers=unique_user.token)
    food_as_json = utils.assert_deserialize(response, 200)
    assert food_as_json["nutrition"]["calories"] == "60"
    assert food_as_json["nutrition"]["proteinContent"] == "0.3"

    response = api_client.get(api_routes.foods_item_id(food["id"]), headers=unique_user.token)
    assert utils.assert_deserialize(response, 200)["nutrition"]["calories"] == "60"

    food_as_json["averageWeight"] = 110.5
    response = api_client.put(api_routes.foods_item_id(food["id"]), json=food_as_json, headers=unique_user.token)
    food_as_json = utils.assert_deserialize(response, 200)
    assert food_as_json["averageWeight"] == 110.5

    food_as_json["averageWeight"] = 0
    response = api_client.put(api_routes.foods_item_id(food["id"]), json=food_as_json, headers=unique_user.token)
    assert response.status_code == 422
    food_as_json["averageWeight"] = None

    # clearing every value removes the nutrition facts
    food_as_json["nutrition"] = {"calories": "", "proteinContent": None}
    response = api_client.put(api_routes.foods_item_id(food["id"]), json=food_as_json, headers=unique_user.token)
    assert utils.assert_deserialize(response, 200)["nutrition"] is None


def _mock_nutrition_ai(monkeypatch: pytest.MonkeyPatch) -> list[list[dict]]:
    requests: list[list[dict]] = []

    async def mock_get_response(self, prompt: str, message: str, *args, **kwargs) -> OpenAIFoodsNutrition:
        inputs = json.loads(message)
        requests.append(inputs)
        return OpenAIFoodsNutrition(
            foods=[
                OpenAIFoodNutrition(
                    calories=100 + i,
                    carbohydrate_content=20,
                    protein_content=1.256,
                    fat_content=0.5,
                    sodium_content=None,
                    average_weight=110.04,
                )
                for i in range(len(inputs))
            ]
        )

    monkeypatch.setattr(OpenAIService, "get_response", mock_get_response)
    monkeypatch.setattr(FoodNutritionService, "ai_enabled", staticmethod(lambda service: True))
    return requests


def test_estimate_food_nutrition(api_client: TestClient, unique_user: TestUser, monkeypatch: pytest.MonkeyPatch):
    requests = _mock_nutrition_ai(monkeypatch)

    names = [random_string() for _ in range(FoodNutritionService.CHUNK_SIZE + 2)]
    response = api_client.post(
        api_routes.foods_nutrition_estimate,
        json={"foods": [{"name": name} for name in names]},
        headers=unique_user.token,
    )
    data = utils.assert_deserialize(response, 200)

    assert len(data) == len(names)
    assert [len(request) for request in requests] == [FoodNutritionService.CHUNK_SIZE, 2]
    assert [request["name"] for chunk in requests for request in chunk] == names
    assert data[0]["nutrition"]["calories"] == "100"
    assert data[0]["nutrition"]["proteinContent"] == "1.26"
    assert data[0]["nutrition"]["sodiumContent"] is None
    assert data[0]["averageWeight"] == 110.0


def test_fill_food_nutrition(api_client: TestClient, unique_user: TestUser, monkeypatch: pytest.MonkeyPatch):
    requests = _mock_nutrition_ai(monkeypatch)

    foods: list[dict] = []
    for _ in range(3):
        response = api_client.post(api_routes.foods, json={"name": random_string()}, headers=unique_user.token)
        foods.append(utils.assert_deserialize(response, 201))

    # a food that already has nutrition facts and an average weight is skipped unless overwriting
    foods[0]["nutrition"] = {"calories": "1"}
    foods[0]["averageWeight"] = 80
    response = api_client.put(api_routes.foods_item_id(foods[0]["id"]), json=foods[0], headers=unique_user.token)
    utils.assert_deserialize(response, 200)

    food_ids = [food["id"] for food in foods]
    response = api_client.post(api_routes.foods_nutrition_fill, json={"foodIds": food_ids}, headers=unique_user.token)
    updated = utils.assert_deserialize(response, 200)

    assert {food["id"] for food in updated} == set(food_ids[1:])
    assert [request["name"] for request in requests[0]] == [food["name"] for food in foods[1:]]

    response = api_client.get(api_routes.foods_item_id(foods[0]["id"]), headers=unique_user.token)
    assert utils.assert_deserialize(response, 200)["nutrition"]["calories"] == "1"
    response = api_client.get(api_routes.foods_item_id(foods[1]["id"]), headers=unique_user.token)
    filled = utils.assert_deserialize(response, 200)
    assert filled["nutrition"]["calories"] == "100"
    assert filled["averageWeight"] == 110.0

    response = api_client.post(
        api_routes.foods_nutrition_fill, json={"foodIds": food_ids, "overwrite": True}, headers=unique_user.token
    )
    assert len(utils.assert_deserialize(response, 200)) == 3
    response = api_client.get(api_routes.foods_item_id(foods[0]["id"]), headers=unique_user.token)
    overwritten = utils.assert_deserialize(response, 200)
    assert overwritten["nutrition"]["calories"] == "100"
    assert overwritten["averageWeight"] == 110.0


def test_fill_food_average_weight_only(
    api_client: TestClient, unique_user: TestUser, food: dict, monkeypatch: pytest.MonkeyPatch
):
    _mock_nutrition_ai(monkeypatch)

    # the nutrition facts entered by the user are kept, only the missing average weight is filled
    food["nutrition"] = {"calories": "1"}
    response = api_client.put(api_routes.foods_item_id(food["id"]), json=food, headers=unique_user.token)
    utils.assert_deserialize(response, 200)

    response = api_client.post(
        api_routes.foods_nutrition_fill, json={"foodIds": [food["id"]]}, headers=unique_user.token
    )
    updated = utils.assert_deserialize(response, 200)

    assert len(updated) == 1
    assert updated[0]["nutrition"]["calories"] == "1"
    assert updated[0]["averageWeight"] == 110.0


def _mock_ai_responses(
    monkeypatch: pytest.MonkeyPatch, responses: list[list[OpenAIFoodNutrition] | Exception]
) -> list[list[dict]]:
    """
    Answers each request with the next of the given responses, raising the exceptions.
    The composition tables find nothing, so every food is estimated by the AI.
    """
    requests: list[list[dict]] = []

    async def mock_get_response(self, prompt: str, message: str, *args, **kwargs) -> OpenAIFoodsNutrition:
        requests.append(json.loads(message))
        response = responses[len(requests) - 1]
        if isinstance(response, Exception):
            raise response
        return OpenAIFoodsNutrition(foods=response)

    monkeypatch.setattr(OpenAIService, "get_response", mock_get_response)
    monkeypatch.setattr(FoodNutritionService, "ai_enabled", staticmethod(lambda service: True))
    monkeypatch.setattr(FoodCompositionService, "best", lambda self, *names: None)
    monkeypatch.setattr(FoodCompositionService, "search_by_source", lambda self, query, limit=5: {})
    return requests


LEMON = OpenAIFoodNutrition(
    name="citron",
    calories=37,
    carbohydrate_content=3.1,
    fat_content=0.7,
    protein_content=0.8,
    fiber_content=4.7,
    sugar_content=2.5,
    average_weight=110,
)
FLOUR = OpenAIFoodNutrition(
    name="farine", calories=343, carbohydrate_content=71.6, fat_content=1.2, protein_content=10.2
)


def test_estimate_food_nutrition_retries_empty_answers(
    api_client: TestClient, unique_user: TestUser, monkeypatch: pytest.MonkeyPatch
):
    requests = _mock_ai_responses(monkeypatch, [[OpenAIFoodNutrition(name="citron"), FLOUR], [LEMON]])

    response = api_client.post(
        api_routes.foods_nutrition_estimate,
        json={"foods": [{"name": "citron"}, {"name": "farine"}]},
        headers=unique_user.token,
    )
    data = utils.assert_deserialize(response, 200)

    # only the food that came back empty is asked again, on its own
    assert [[item["name"] for item in request] for request in requests] == [["citron", "farine"], ["citron"]]
    assert data[0]["nutrition"]["calories"] == "37"
    assert data[0]["averageWeight"] == 110
    assert data[1]["nutrition"]["calories"] == "343"
    assert data[1]["averageWeight"] is None


def test_estimate_food_nutrition_asks_one_at_a_time_when_the_list_is_garbled(
    api_client: TestClient, unique_user: TestUser, monkeypatch: pytest.MonkeyPatch
):
    requests = _mock_ai_responses(monkeypatch, [[FLOUR], [LEMON], [FLOUR]])

    response = api_client.post(
        api_routes.foods_nutrition_estimate,
        json={"foods": [{"name": "citron"}, {"name": "farine"}]},
        headers=unique_user.token,
    )
    data = utils.assert_deserialize(response, 200)

    assert [[item["name"] for item in request] for request in requests] == [
        ["citron", "farine"],
        ["citron"],
        ["farine"],
    ]
    assert data[0]["nutrition"]["calories"] == "37"
    assert data[1]["nutrition"]["calories"] == "343"


def test_estimate_food_nutrition_keeps_the_first_answer_when_the_retry_fails(
    api_client: TestClient, unique_user: TestUser, monkeypatch: pytest.MonkeyPatch
):
    no_fat = LEMON.model_copy(update={"fat_content": None})
    _mock_ai_responses(monkeypatch, [[no_fat, FLOUR], Exception("Timeout")])

    response = api_client.post(
        api_routes.foods_nutrition_estimate,
        json={"foods": [{"name": "citron"}, {"name": "farine"}]},
        headers=unique_user.token,
    )
    data = utils.assert_deserialize(response, 200)

    assert data[0]["nutrition"]["calories"] == "37"
    assert data[0]["nutrition"]["fatContent"] is None
    assert data[1]["nutrition"]["calories"] == "343"


def test_estimate_food_nutrition_corrects_inconsistent_answers(
    api_client: TestClient, unique_user: TestUser, monkeypatch: pytest.MonkeyPatch
):
    inconsistent = OpenAIFoodNutrition(
        name="citron",
        calories=5,
        carbohydrate_content=3.1,
        fat_content=0.7,
        protein_content=0.8,
        sugar_content=9,
        saturated_fat_content=2,
        sodium_content=-1,
        vitamin_c_content=99_999,
        average_weight=110,
    )
    requests = _mock_ai_responses(monkeypatch, [[inconsistent], [inconsistent]])

    response = api_client.post(
        api_routes.foods_nutrition_estimate, json={"foods": [{"name": "citron"}]}, headers=unique_user.token
    )
    nutrition = utils.assert_deserialize(response, 200)[0]["nutrition"]

    assert len(requests) == 2
    assert nutrition["calories"] == "22"  # 4 x 3.1 + 4 x 0.8 + 9 x 0.7
    assert nutrition["sugarContent"] == "3.1"
    assert nutrition["saturatedFatContent"] == "0.7"
    assert nutrition["sodiumContent"] is None
    assert nutrition["vitaminCContent"] is None


def test_estimate_food_nutrition_retries_mixed_up_answers(
    api_client: TestClient, unique_user: TestUser, monkeypatch: pytest.MonkeyPatch
):
    # the first answer is about another food, so the order of the list can't be trusted for it
    butter = OpenAIFoodNutrition(
        name="beurre", calories=717, carbohydrate_content=0.1, fat_content=81, protein_content=0.9
    )
    requests = _mock_ai_responses(monkeypatch, [[butter, FLOUR], [LEMON]])

    response = api_client.post(
        api_routes.foods_nutrition_estimate,
        json={"foods": [{"name": "citron"}, {"name": "farine"}]},
        headers=unique_user.token,
    )
    data = utils.assert_deserialize(response, 200)

    assert len(requests) == 2
    assert data[0]["nutrition"]["calories"] == "37"
    assert data[1]["nutrition"]["calories"] == "343"


def test_estimate_food_nutrition_rejects_impossible_macros(
    api_client: TestClient, unique_user: TestUser, monkeypatch: pytest.MonkeyPatch
):
    impossible = OpenAIFoodNutrition(
        name="citron", calories=500, carbohydrate_content=80, fat_content=30, protein_content=20, average_weight=110
    )
    _mock_ai_responses(monkeypatch, [[impossible], [impossible]])

    response = api_client.post(
        api_routes.foods_nutrition_estimate, json={"foods": [{"name": "citron"}]}, headers=unique_user.token
    )
    data = utils.assert_deserialize(response, 200)[0]

    assert not any(data["nutrition"].values())
    assert data["averageWeight"] == 110


def test_food_nutrition_ai_not_enabled(api_client: TestClient, unique_user: TestUser):
    # without AI, the composition tables still give the foods they know, and nothing for the others
    response = api_client.post(
        api_routes.foods_nutrition_estimate,
        json={"foods": [{"name": "citron"}, {"name": random_string()}]},
        headers=unique_user.token,
    )
    lemon, unknown = utils.assert_deserialize(response, 200)

    assert lemon["source"] == "ciqual"
    assert lemon["referenceCode"] == "13009"
    assert lemon["nutrition"]["calories"]
    assert unknown["source"] is None
    assert not any(unknown["nutrition"].values())


def test_food_nutrition_ai_technical_error(
    api_client: TestClient, unique_user: TestUser, monkeypatch: pytest.MonkeyPatch
):
    async def mock_get_response(self, *args, **kwargs):
        try:
            raise TimeoutError("Request timed out")
        except TimeoutError as e:
            raise Exception(f"OpenAI Request Failed. {e.__class__.__name__}: {e}") from e

    monkeypatch.setattr(OpenAIService, "get_response", mock_get_response)
    monkeypatch.setattr(FoodNutritionService, "ai_enabled", staticmethod(lambda service: True))

    response = api_client.post(
        api_routes.foods_nutrition_estimate,
        json={"foods": [{"name": random_string()}]},
        headers=unique_user.token,
    )
    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "TimeoutError: Request timed out" in detail["message"]
    assert detail["exception"] == "TimeoutError: Request timed out"


def _mock_failing_ai(monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    async def mock_get_response(self, *args, **kwargs):
        try:
            raise error
        except Exception as e:
            raise Exception(f"OpenAI Request Failed. {e.__class__.__name__}: {e}") from e

    monkeypatch.setattr(OpenAIService, "get_response", mock_get_response)
    monkeypatch.setattr(FoodNutritionService, "ai_enabled", staticmethod(lambda service: True))


def test_food_nutrition_ai_rate_limit(api_client: TestClient, unique_user: TestUser, monkeypatch: pytest.MonkeyPatch):
    _mock_failing_ai(monkeypatch, exceptions.RateLimitError("Too many requests"))

    response = api_client.post(
        api_routes.foods_nutrition_estimate,
        json={"foods": [{"name": random_string()}]},
        headers=unique_user.token,
    )
    assert response.status_code == 429
    assert response.json()["detail"]["message"]


def test_food_nutrition_ai_technical_error_is_truncated(
    api_client: TestClient, unique_user: TestUser, monkeypatch: pytest.MonkeyPatch
):
    _mock_failing_ai(monkeypatch, ValueError("x" * 1000))

    response = api_client.post(
        api_routes.foods_nutrition_estimate,
        json={"foods": [{"name": random_string()}]},
        headers=unique_user.token,
    )
    assert response.status_code == 502
    detail = response.json()["detail"]
    assert detail["exception"].startswith("ValueError: xxx")
    assert len(detail["exception"]) == IngredientFoodsController.AI_ERROR_MAX_LENGTH + 1
    assert detail["exception"].endswith("…")
    assert detail["exception"] in detail["message"]


def test_fill_food_nutrition_technical_error(
    api_client: TestClient, unique_user: TestUser, food: dict, monkeypatch: pytest.MonkeyPatch
):
    _mock_failing_ai(monkeypatch, ConnectionError("Connection refused"))

    response = api_client.post(
        api_routes.foods_nutrition_fill, json={"foodIds": [food["id"]]}, headers=unique_user.token
    )
    assert response.status_code == 502
    assert "ConnectionError: Connection refused" in response.json()["detail"]["message"]

    # nothing is saved when the AI fails
    response = api_client.get(api_routes.foods_item_id(food["id"]), headers=unique_user.token)
    assert utils.assert_deserialize(response, 200)["nutrition"] is None


def _create_food(api_client: TestClient, user: TestUser, name: str | None = None) -> str:
    name = name or random_string(10)
    response = api_client.post(api_routes.foods, json={"name": name}, headers=user.token)
    return utils.assert_deserialize(response, 201)["id"]


def _nutrition_logs(api_client: TestClient, user: TestUser, food_id: str) -> list[dict]:
    response = api_client.get(f"{api_routes.foods_item_id(food_id)}/nutrition/logs", headers=user.token)
    return utils.assert_deserialize(response, 200)


def test_fill_food_nutrition_keeps_the_history_of_the_estimate(
    api_client: TestClient, unique_user: TestUser, monkeypatch: pytest.MonkeyPatch
):
    lemon_id = _create_food(api_client, unique_user, "citron")
    flour_id = _create_food(api_client, unique_user, "farine")
    _mock_ai_responses(monkeypatch, [[OpenAIFoodNutrition(name="citron"), FLOUR], [LEMON]])

    response = api_client.post(
        api_routes.foods_nutrition_fill, json={"foodIds": [lemon_id, flour_id]}, headers=unique_user.token
    )
    utils.assert_deserialize(response, 200)

    [log] = _nutrition_logs(api_client, unique_user, lemon_id)
    assert log["origin"] == "fill"
    assert log["error"] is None
    assert log["result"]["nutrition"]["calories"] == "37"
    assert log["result"]["averageWeight"] == 110

    lookup, first, retry = log["steps"]
    assert lookup["kind"] == "lookup"
    assert lookup["response"] == {"match": None, "candidates": []}
    assert not lookup["kept"]
    assert first["kind"] == "batch"
    assert first["foodsCount"] == 2
    assert first["response"] == {"name": "citron"}
    assert [issue["code"] for issue in first["issues"]] == ["missing-values"]
    assert first["issues"][0]["params"]["fields"] == "calories,carbohydrate_content,fat_content,protein_content"
    assert not first["kept"]
    assert retry["kind"] == "retry"
    assert retry["foodsCount"] == 1
    assert retry["response"]["calories"] == 37
    assert retry["issues"] == []
    assert retry["kept"]
    assert log["corrections"] == []

    [log] = _nutrition_logs(api_client, unique_user, flour_id)
    assert [step["kind"] for step in log["steps"]] == ["lookup", "batch"]
    assert log["steps"][-1]["kept"]

    for food_id in (lemon_id, flour_id):
        api_client.delete(api_routes.foods_item_id(food_id), headers=unique_user.token)


def test_estimate_food_nutrition_keeps_the_corrections_in_the_history(
    api_client: TestClient, unique_user: TestUser, monkeypatch: pytest.MonkeyPatch
):
    food_id = _create_food(api_client, unique_user)
    inconsistent = LEMON.model_copy(update={"sugar_content": 9, "sodium_content": -1})
    _mock_ai_responses(monkeypatch, [[inconsistent], [inconsistent]])

    response = api_client.post(
        api_routes.foods_nutrition_estimate,
        json={"foods": [{"id": food_id, "name": "citron"}]},
        headers=unique_user.token,
    )
    utils.assert_deserialize(response, 200)

    [log] = _nutrition_logs(api_client, unique_user, food_id)
    assert log["origin"] == "estimate"
    assert [step["kind"] for step in log["steps"]] == ["lookup", "single", "retry"]
    assert [step["kept"] for step in log["steps"]] == [False, False, True]
    assert [issue["code"] for issue in log["steps"][2]["issues"]] == ["sugar-over-carbohydrates"]
    assert {correction["field"]: (correction["before"], correction["after"]) for correction in log["corrections"]} == {
        "sugar_content": (9, 3.1),
        "sodium_content": (-1, None),
    }
    assert log["result"]["nutrition"]["sugarContent"] == "3.1"

    # the food itself is only changed when the user saves it
    response = api_client.get(api_routes.foods_item_id(food_id), headers=unique_user.token)
    assert utils.assert_deserialize(response, 200)["nutrition"] is None


def test_estimate_food_nutrition_without_id_has_no_history(
    api_client: TestClient, unique_user: TestUser, monkeypatch: pytest.MonkeyPatch
):
    food_id = _create_food(api_client, unique_user)
    _mock_ai_responses(monkeypatch, [[LEMON]])

    response = api_client.post(
        api_routes.foods_nutrition_estimate, json={"foods": [{"name": "citron"}]}, headers=unique_user.token
    )
    utils.assert_deserialize(response, 200)

    assert _nutrition_logs(api_client, unique_user, food_id) == []


def test_failed_food_nutrition_estimate_is_kept_in_the_history(
    api_client: TestClient, unique_user: TestUser, monkeypatch: pytest.MonkeyPatch
):
    food_id = _create_food(api_client, unique_user)
    _mock_ai_responses(monkeypatch, [Exception("Connection refused")])

    response = api_client.post(api_routes.foods_nutrition_fill, json={"foodIds": [food_id]}, headers=unique_user.token)
    assert response.status_code == 502

    [log] = _nutrition_logs(api_client, unique_user, food_id)
    assert log["error"] == "Connection refused"
    assert log["result"] is None
    assert [(step["kind"], step["error"]) for step in log["steps"]] == [
        ("lookup", None),
        ("single", "Connection refused"),
    ]


def test_food_nutrition_history_keeps_the_latest_estimates(
    api_client: TestClient, unique_user: TestUser, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(FoodNutritionService, "LOGS_PER_FOOD", 2)
    food_id = _create_food(api_client, unique_user)
    _mock_ai_responses(monkeypatch, [[LEMON.model_copy(update={"calories": calories})] for calories in (35, 36, 37)])

    for _ in range(3):
        response = api_client.post(
            api_routes.foods_nutrition_estimate,
            json={"foods": [{"id": food_id, "name": "citron"}]},
            headers=unique_user.token,
        )
        utils.assert_deserialize(response, 200)

    logs = _nutrition_logs(api_client, unique_user, food_id)
    assert [log["result"]["nutrition"]["calories"] for log in logs] == ["37", "36"]


def test_food_nutrition_history_is_scoped_to_the_group(
    api_client: TestClient, unique_user: TestUser, g2_user: TestUser, monkeypatch: pytest.MonkeyPatch
):
    food_id = _create_food(api_client, unique_user)
    _mock_ai_responses(monkeypatch, [[LEMON]])
    api_client.post(api_routes.foods_nutrition_fill, json={"foodIds": [food_id]}, headers=unique_user.token)
    assert len(_nutrition_logs(api_client, unique_user, food_id)) == 1

    response = api_client.get(f"{api_routes.foods_item_id(food_id)}/nutrition/logs", headers=g2_user.token)
    assert response.status_code == 404


def test_food_nutrition_history_is_deleted_with_the_food(
    api_client: TestClient, unique_user: TestUser, monkeypatch: pytest.MonkeyPatch
):
    food_id = _create_food(api_client, unique_user, "citron")
    _mock_ai_responses(monkeypatch, [[LEMON]])
    api_client.post(api_routes.foods_nutrition_fill, json={"foodIds": [food_id]}, headers=unique_user.token)
    assert len(_nutrition_logs(api_client, unique_user, food_id)) == 1

    response = api_client.delete(api_routes.foods_item_id(food_id), headers=unique_user.token)
    assert response.status_code == 200

    unique_user.repos.session.expire_all()
    assert unique_user.repos.ingredient_food_nutrition_logs.get_for_food(food_id) == []


def _mock_tables_ai(
    monkeypatch: pytest.MonkeyPatch,
    matches: list[OpenAIFoodNutritionMatch] | Exception,
    estimates: list[OpenAIFoodNutrition] | None = None,
) -> dict[str, list[list[dict]]]:
    """
    The composition tables give their candidates but no confident match, so the AI chooses among them,
    answering with the given matches, then estimates the foods it matched with none.
    """
    requests: dict[str, list[list[dict]]] = {"match": [], "estimate": []}

    async def mock_get_response(self, prompt: str, message: str, *args, response_schema=None, **kwargs):
        if response_schema is OpenAIFoodNutritionMatches:
            requests["match"].append(json.loads(message))
            if isinstance(matches, Exception):
                raise matches
            return OpenAIFoodNutritionMatches(foods=matches)
        requests["estimate"].append(json.loads(message))
        return OpenAIFoodsNutrition(foods=estimates or [])

    monkeypatch.setattr(OpenAIService, "get_response", mock_get_response)
    monkeypatch.setattr(FoodNutritionService, "ai_enabled", staticmethod(lambda service: True))
    monkeypatch.setattr(FoodCompositionService, "best", lambda self, *names: None)
    return requests


def test_estimate_food_nutrition_from_the_ciqual_table_without_ai(api_client: TestClient, unique_user: TestUser):
    food_id = _create_food(api_client, unique_user)
    response = api_client.post(
        api_routes.foods_nutrition_estimate,
        json={"foods": [{"id": food_id, "name": "citrons"}]},
        headers=unique_user.token,
    )
    [data] = utils.assert_deserialize(response, 200)

    assert data["source"] == "ciqual"
    assert data["referenceCode"] == "13009"
    assert data["referenceName"].lower().startswith("citron")
    assert float(data["nutrition"]["calories"]) > 0
    assert data["averageWeight"] == pytest.approx(58, abs=1)

    [log] = _nutrition_logs(api_client, unique_user, food_id)
    assert log["aiModel"] is None
    assert [step["kind"] for step in log["steps"]] == ["lookup"]
    assert log["steps"][0]["kept"]
    assert log["steps"][0]["response"]["match"] == "ciqual:13009"
    assert log["result"]["source"] == "ciqual"


def test_unknown_food_without_ai_is_kept_in_the_history(api_client: TestClient, unique_user: TestUser):
    food_id = _create_food(api_client, unique_user)
    response = api_client.post(api_routes.foods_nutrition_fill, json={"foodIds": [food_id]}, headers=unique_user.token)
    assert utils.assert_deserialize(response, 200) == []

    [log] = _nutrition_logs(api_client, unique_user, food_id)
    assert log["result"] is None
    assert log["error"]


def test_ai_chooses_among_the_candidates_of_the_tables(
    api_client: TestClient, unique_user: TestUser, monkeypatch: pytest.MonkeyPatch
):
    food_id = _create_food(api_client, unique_user)
    requests = _mock_tables_ai(
        monkeypatch, [OpenAIFoodNutritionMatch(name="citron", reference="ciqual:13009", average_weight=110)]
    )

    response = api_client.post(
        api_routes.foods_nutrition_estimate,
        json={"foods": [{"id": food_id, "name": "citron"}]},
        headers=unique_user.token,
    )
    [data] = utils.assert_deserialize(response, 200)

    [[item]] = requests["match"]
    assert item["name"] == "citron"
    candidates = [candidate["id"] for candidate in item["candidates"]]
    assert "ciqual:13009" in candidates
    assert requests["estimate"] == []

    assert (data["source"], data["referenceCode"]) == ("ciqual", "13009")
    assert data["averageWeight"] == 110

    [log] = _nutrition_logs(api_client, unique_user, food_id)
    assert [step["kind"] for step in log["steps"]] == ["lookup", "match"]
    assert log["steps"][1]["kept"]
    assert log["steps"][1]["response"]["reference"] == "ciqual:13009"


def test_ai_estimates_the_foods_matching_no_candidate(
    api_client: TestClient, unique_user: TestUser, monkeypatch: pytest.MonkeyPatch
):
    requests = _mock_tables_ai(
        monkeypatch,
        [
            OpenAIFoodNutritionMatch(name="citron", reference=None),
            OpenAIFoodNutritionMatch(name="farine", reference="ciqual:does-not-exist"),
        ],
        [LEMON, FLOUR],
    )

    response = api_client.post(
        api_routes.foods_nutrition_estimate,
        json={"foods": [{"name": "citron"}, {"name": "farine"}]},
        headers=unique_user.token,
    )
    lemon, flour = utils.assert_deserialize(response, 200)

    assert len(requests["match"]) == 1
    assert [[item["name"] for item in request] for request in requests["estimate"]] == [["citron", "farine"]]
    assert (lemon["source"], lemon["referenceCode"], lemon["nutrition"]["calories"]) == ("ai", None, "37")
    assert (flour["source"], flour["nutrition"]["calories"]) == ("ai", "343")


def test_failed_ai_match_falls_back_to_the_estimate(
    api_client: TestClient, unique_user: TestUser, monkeypatch: pytest.MonkeyPatch
):
    food_id = _create_food(api_client, unique_user)
    requests = _mock_tables_ai(monkeypatch, Exception("Timeout"), [LEMON])

    response = api_client.post(
        api_routes.foods_nutrition_estimate,
        json={"foods": [{"id": food_id, "name": "citron"}]},
        headers=unique_user.token,
    )
    [data] = utils.assert_deserialize(response, 200)

    assert len(requests["estimate"]) == 1
    assert data["source"] == "ai"

    [log] = _nutrition_logs(api_client, unique_user, food_id)
    assert [(step["kind"], step["error"]) for step in log["steps"]] == [
        ("lookup", None),
        ("match", "Timeout"),
        ("single", None),
    ]


def test_fill_food_nutrition_saves_the_source(api_client: TestClient, unique_user: TestUser):
    food_id = _create_food(api_client, unique_user, "citron")

    response = api_client.post(api_routes.foods_nutrition_fill, json={"foodIds": [food_id]}, headers=unique_user.token)
    [food] = utils.assert_deserialize(response, 200)

    assert food["nutritionSource"] == "ciqual"
    assert food["nutritionReferenceCode"] == "13009"
    assert food["nutritionReferenceName"]
    assert food["nutrition"]["calories"]
    assert food["averageWeight"]

    response = api_client.get(api_routes.foods_item_id(food_id), headers=unique_user.token)
    assert utils.assert_deserialize(response, 200)["nutritionSource"] == "ciqual"

    # editing the values by hand is up to the client, which then clears the source
    food["nutritionSource"] = None
    food["nutritionReferenceCode"] = None
    food["nutritionReferenceName"] = None
    response = api_client.put(api_routes.foods_item_id(food_id), json=food, headers=unique_user.token)
    assert utils.assert_deserialize(response, 200)["nutritionSource"] is None

    api_client.delete(api_routes.foods_item_id(food_id), headers=unique_user.token)


def test_search_nutrition_references(api_client: TestClient, unique_user: TestUser):
    response = api_client.get(
        api_routes.foods_nutrition_references, params={"search": "citron", "limit": 5}, headers=unique_user.token
    )
    references = utils.assert_deserialize(response, 200)

    assert 0 < len(references) <= 5
    assert references[0]["source"] == "ciqual"
    assert any(reference["code"] == "13009" for reference in references)
    lemon = next(reference for reference in references if reference["code"] == "13009")
    assert lemon["nutrition"]["calories"]
    assert lemon["averageWeight"] == pytest.approx(58, abs=1)

    response = api_client.get(
        api_routes.foods_nutrition_references, params={"search": "lemon"}, headers=unique_user.token
    )
    assert any(reference["source"] == "usda" for reference in utils.assert_deserialize(response, 200))

    response = api_client.get(api_routes.foods_nutrition_references, params={"search": ""}, headers=unique_user.token)
    assert response.status_code == 422
