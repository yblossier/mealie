from fastapi.testclient import TestClient

from tests.utils import api_routes
from tests.utils.factories import random_string
from tests.utils.fixture_schemas import TestUser


def test_create_recipe_for_thermomix(api_client: TestClient, unique_user: TestUser):
    r = api_client.post(
        api_routes.recipes, json={"name": random_string(), "thermomix": True}, headers=unique_user.token
    )
    assert r.status_code == 201
    recipe = api_client.get(api_routes.recipes_slug(r.json()), headers=unique_user.token).json()
    assert recipe["settings"]["thermomix"] is True

    # the setting can be turned off later, like the other recipe settings
    recipe["settings"]["thermomix"] = False
    r = api_client.put(api_routes.recipes_slug(recipe["slug"]), json=recipe, headers=unique_user.token)
    assert r.status_code == 200
    recipe = api_client.get(api_routes.recipes_slug(recipe["slug"]), headers=unique_user.token).json()
    assert recipe["settings"]["thermomix"] is False


def test_create_recipe_not_for_thermomix_by_default(api_client: TestClient, unique_user: TestUser):
    r = api_client.post(api_routes.recipes, json={"name": random_string()}, headers=unique_user.token)
    assert r.status_code == 201
    recipe = api_client.get(api_routes.recipes_slug(r.json()), headers=unique_user.token).json()
    assert recipe["settings"]["thermomix"] is False

    recipe["settings"]["thermomix"] = True
    api_client.put(api_routes.recipes_slug(recipe["slug"]), json=recipe, headers=unique_user.token)
    recipe = api_client.get(api_routes.recipes_slug(recipe["slug"]), headers=unique_user.token).json()
    assert recipe["settings"]["thermomix"] is True
