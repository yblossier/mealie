import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from mealie.schema.openai.food_allergens import OpenAIFoodAllergens, OpenAIFoodsAllergens
from mealie.services.openai import OpenAIService
from tests.utils import api_routes
from tests.utils.fixture_schemas import TestUser

FOODS_ALLERGENS_SUGGEST = "/api/foods/allergens/suggest"
FOODS_ALLERGENS_FILL = "/api/foods/allergens/fill"


def _create_allergen(api_client: TestClient, user: TestUser, keywords: str = "", exclusions: str = "") -> dict:
    response = api_client.post(
        api_routes.groups_allergens,
        json={
            "name": f"Allergen {uuid4()}",
            "code": f"code-{uuid4().hex[:8]}",
            "keywords": keywords,
            "exclusions": exclusions,
        },
        headers=user.token,
    )
    assert response.status_code == 201
    return response.json()


def _create_food(api_client: TestClient, user: TestUser, name: str, allergens: list[dict] | None = None) -> dict:
    response = api_client.post(
        api_routes.foods,
        json={"name": name, "allergens": [{"id": a["id"], "name": a["name"]} for a in allergens or []]},
        headers=user.token,
    )
    assert response.status_code == 201
    return response.json()


def _mock_ai(monkeypatch: pytest.MonkeyPatch, answers: dict[str, list[str]]) -> list[list[str]]:
    """Answers with the allergen codes given per food name, recording the names sent to the AI"""
    requests: list[list[str]] = []

    async def mock_get_response(self, prompt: str, message: str, *args, **kwargs) -> OpenAIFoodsAllergens:
        names = [item["name"] for item in json.loads(message)]
        requests.append(names)
        return OpenAIFoodsAllergens(
            foods=[OpenAIFoodAllergens(name=name, allergens=answers.get(name, [])) for name in names]
        )

    monkeypatch.setattr(OpenAIService, "get_response", mock_get_response)
    return requests


def test_seed_and_crud(api_client: TestClient, unique_user: TestUser):
    headers = unique_user.token
    assert (
        api_client.post(api_routes.groups_seeders_allergens, json={"locale": "fr-FR"}, headers=headers).status_code
        == 200
    )
    # Seeding twice keeps a single entry per allergen
    assert (
        api_client.post(api_routes.groups_seeders_allergens, json={"locale": "fr-FR"}, headers=headers).status_code
        == 200
    )

    items = api_client.get(api_routes.groups_allergens, params={"perPage": -1}, headers=headers).json()["items"]
    assert len(items) == 14
    milk = next(item for item in items if item["code"] == "milk")
    assert "beurre" in milk["keywords"]

    custom = api_client.post(
        api_routes.groups_allergens, json={"name": f"Custom {uuid4()}", "keywords": "safran"}, headers=headers
    )
    assert custom.status_code == 201
    custom_id = custom.json()["id"]
    updated = api_client.put(
        api_routes.groups_allergens_item_id(custom_id),
        json={**custom.json(), "keywords": "safran, curcuma"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["keywords"] == "safran, curcuma"
    assert api_client.delete(api_routes.groups_allergens_item_id(custom_id), headers=headers).status_code == 200


def test_recipe_allergens_come_only_from_linked_foods(api_client: TestClient, unique_user: TestUser):
    headers = unique_user.token
    allergen = _create_allergen(api_client, unique_user, keywords="beurre, curcuma")
    linked = _create_food(api_client, unique_user, f"Linked {uuid4()}", [allergen])
    unlinked = _create_food(api_client, unique_user, f"Beurre {uuid4()}")

    slug = api_client.post(api_routes.recipes, json={"name": f"Allergens {uuid4()}"}, headers=headers).json()
    recipe = api_client.get(api_routes.recipes_slug(slug), headers=headers).json()
    recipe["recipeIngredient"] = [
        {"note": "200 g de beurre", "originalText": "200 g de beurre"},
        {"note": "", "food": unlinked, "quantity": 1},
        {"note": "", "food": linked, "quantity": 2},
    ]
    assert api_client.put(api_routes.recipes_slug(slug), json=recipe, headers=headers).status_code == 200

    # the recipe page reads the allergens of each ingredient food for its info bubble
    recipe = api_client.get(api_routes.recipes_slug(slug), headers=headers).json()
    foods = [ingredient["food"] for ingredient in recipe["recipeIngredient"]]
    assert foods[0] is None
    assert foods[1]["allergens"] == []
    assert [a["id"] for a in foods[2]["allergens"]] == [allergen["id"]]

    response = api_client.get(api_routes.recipes_slug_allergens(slug), headers=headers)
    assert response.status_code == 200
    assert response.json() == [
        {
            "allergenId": allergen["id"],
            "code": allergen["code"],
            "name": allergen["name"],
            "ingredients": [linked["name"]],
        }
    ]


def test_recipe_without_linked_food_has_no_allergen(api_client: TestClient, unique_user: TestUser):
    headers = unique_user.token
    _create_allergen(api_client, unique_user, keywords="beurre")
    slug = api_client.post(api_routes.recipes, json={"name": f"Allergens {uuid4()}"}, headers=headers).json()
    recipe = api_client.get(api_routes.recipes_slug(slug), headers=headers).json()
    recipe["recipeIngredient"] = [{"note": "200 g de beurre", "originalText": "200 g de beurre"}]
    assert api_client.put(api_routes.recipes_slug(slug), json=recipe, headers=headers).status_code == 200

    assert api_client.get(api_routes.recipes_slug_allergens(slug), headers=headers).json() == []


def test_suggest_uses_keywords_before_the_ai(
    api_client: TestClient, unique_user: TestUser, monkeypatch: pytest.MonkeyPatch
):
    allergen = _create_allergen(api_client, unique_user, keywords="zesamix")
    requests = _mock_ai(monkeypatch, {"Tahinoq": [allergen["code"]]})

    response = api_client.post(FOODS_ALLERGENS_SUGGEST, json={"name": "Graines de zesamix"}, headers=unique_user.token)
    assert response.status_code == 200
    assert [a["id"] for a in response.json()] == [allergen["id"]]
    assert requests == []

    response = api_client.post(FOODS_ALLERGENS_SUGGEST, json={"name": "Tahinoq"}, headers=unique_user.token)
    assert [a["id"] for a in response.json()] == [allergen["id"]]
    assert requests == [["Tahinoq"]]

    # the AI match enriched the keywords, so the food is now matched offline
    saved = api_client.get(api_routes.groups_allergens_item_id(allergen["id"]), headers=unique_user.token).json()
    assert saved["keywords"] == "zesamix, tahinoq"
    response = api_client.post(FOODS_ALLERGENS_SUGGEST, json={"name": "Tahinoqs"}, headers=unique_user.token)
    assert [a["id"] for a in response.json()] == [allergen["id"]]
    assert requests == [["Tahinoq"]]


def test_fill_sends_only_unmatched_foods_to_the_ai(
    api_client: TestClient, unique_user: TestUser, monkeypatch: pytest.MonkeyPatch
):
    gluten = _create_allergen(api_client, unique_user, keywords="zorblé, zorbflour")
    milk = _create_allergen(api_client, unique_user, keywords="zorbmilk")
    suffix = uuid4().hex[:6]
    flour = _create_food(api_client, unique_user, f"Zorbflour {suffix}")
    brioche = _create_food(api_client, unique_user, f"Quixbun {suffix}")
    salt = _create_food(api_client, unique_user, f"Plimsal {suffix}")
    requests = _mock_ai(monkeypatch, {brioche["name"]: [gluten["code"], milk["code"]]})

    response = api_client.post(
        FOODS_ALLERGENS_FILL,
        json={"foodIds": [flour["id"], brioche["id"], salt["id"]]},
        headers=unique_user.token,
    )
    assert response.status_code == 200
    updated = {food["id"]: {a["id"] for a in food["allergens"]} for food in response.json()}
    assert updated == {flour["id"]: {gluten["id"]}, brioche["id"]: {gluten["id"], milk["id"]}}
    assert requests == [[brioche["name"], salt["name"]]]

    for allergen, keywords in ((gluten, "zorblé, zorbflour"), (milk, "zorbmilk")):
        saved = api_client.get(api_routes.groups_allergens_item_id(allergen["id"]), headers=unique_user.token).json()
        assert saved["keywords"] == f"{keywords}, {brioche['name'].lower()}"

    # enriching twice doesn't repeat the keyword
    response = api_client.post(
        FOODS_ALLERGENS_FILL, json={"foodIds": [brioche["id"]], "overwrite": True}, headers=unique_user.token
    )
    assert response.status_code == 200
    assert requests == [[brioche["name"], salt["name"]]]
    saved = api_client.get(api_routes.groups_allergens_item_id(milk["id"]), headers=unique_user.token).json()
    assert saved["keywords"] == f"zorbmilk, {brioche['name'].lower()}"


def test_allergens_are_scoped_to_the_group(
    api_client: TestClient, unique_user: TestUser, unique_user_fn_scoped: TestUser
):
    other_group = unique_user_fn_scoped
    allergen = _create_allergen(api_client, unique_user, keywords="zorbsel")
    item_route = api_routes.groups_allergens_item_id(allergen["id"])

    # another group neither lists, reads, edits nor deletes it
    items = api_client.get(api_routes.groups_allergens, params={"perPage": -1}, headers=other_group.token).json()[
        "items"
    ]
    assert allergen["id"] not in {item["id"] for item in items}
    assert api_client.get(item_route, headers=other_group.token).status_code == 404
    assert (
        api_client.put(item_route, json={**allergen, "keywords": "hacked"}, headers=other_group.token).status_code
        == 404
    )
    assert api_client.delete(item_route, headers=other_group.token).status_code == 404
    assert api_client.get(item_route, headers=unique_user.token).json()["keywords"] == "zorbsel"

    # a food can't be linked with the allergen of another group
    foreign_food = _create_food(api_client, other_group, f"Foreign {uuid4()}", [allergen])
    assert foreign_food["allergens"] == []
    own_allergen = _create_allergen(api_client, other_group)
    response = api_client.put(
        api_routes.foods_item_id(foreign_food["id"]),
        json={**foreign_food, "allergens": [{"id": a["id"], "name": a["name"]} for a in (allergen, own_allergen)]},
        headers=other_group.token,
    )
    assert response.status_code == 200
    assert [a["id"] for a in response.json()["allergens"]] == [own_allergen["id"]]


def test_food_allergen_routes_require_organize_permission(api_client: TestClient, unprivileged_user: TestUser):
    response = api_client.post(FOODS_ALLERGENS_SUGGEST, json={"name": "Beurre"}, headers=unprivileged_user.token)
    assert response.status_code == 403
    response = api_client.post(FOODS_ALLERGENS_FILL, json={"foodIds": []}, headers=unprivileged_user.token)
    assert response.status_code == 403
    response = api_client.post(
        api_routes.groups_allergens, json={"name": f"Allergen {uuid4()}"}, headers=unprivileged_user.token
    )
    assert response.status_code == 403


def test_recipe_allergens_of_another_group_are_not_found(
    api_client: TestClient, unique_user: TestUser, g2_user: TestUser
):
    slug = api_client.post(api_routes.recipes, json={"name": f"Allergens {uuid4()}"}, headers=unique_user.token).json()
    assert api_client.get(api_routes.recipes_slug_allergens(slug), headers=g2_user.token).status_code == 404
