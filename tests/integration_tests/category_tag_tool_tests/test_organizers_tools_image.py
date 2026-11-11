"""Integration tests for the tool category and photo."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from mealie.schema.recipe.recipe_organizers import ToolOut
from tests import data as test_data
from tests.utils import api_routes
from tests.utils.factories import random_string
from tests.utils.fixture_schemas import TestUser


def _create_tool(api_client: TestClient, user: TestUser, **extra) -> dict:
    response = api_client.post(
        api_routes.organizers_tools, json={"name": random_string(10), **extra}, headers=user.token
    )
    assert response.status_code == 201
    return response.json()


def _upload_image(api_client: TestClient, user: TestUser, tool_id: str):
    return api_client.put(
        api_routes.organizers_tools_item_id_image(tool_id),
        files={"image": test_data.images_test_image_1.read_bytes()},
        headers=user.token,
    )


def test_tool_defaults_to_utensils(api_client: TestClient, unique_user: TestUser):
    tool = _create_tool(api_client, unique_user)

    assert tool["category"] == "utensils"
    assert tool["image"] is None


def test_tool_is_created_with_category(api_client: TestClient, unique_user: TestUser):
    tool = _create_tool(api_client, unique_user, category="appliance")

    assert tool["category"] == "appliance"


@pytest.mark.parametrize("category", ["rocket", "mdi-pot-steam", ""])
def test_tool_rejects_unknown_category(api_client: TestClient, unique_user: TestUser, category: str):
    response = api_client.post(
        api_routes.organizers_tools, json={"name": random_string(10), "category": category}, headers=unique_user.token
    )

    assert response.status_code == 422


def test_tool_update_changes_category_and_keeps_image(api_client: TestClient, unique_user: TestUser):
    tool = _create_tool(api_client, unique_user, category="dishes")
    image_key = _upload_image(api_client, unique_user, tool["id"]).json()["image"]

    response = api_client.put(
        api_routes.organizers_tools_item_id(tool["id"]),
        json={"name": tool["name"], "category": "cutlery"},
        headers=unique_user.token,
    )

    assert response.status_code == 200
    assert response.json()["category"] == "cutlery"
    assert response.json()["image"] == image_key


def test_tool_image_upload_is_served(api_client: TestClient, unique_user: TestUser):
    tool = _create_tool(api_client, unique_user)

    response = _upload_image(api_client, unique_user, tool["id"])

    assert response.status_code == 200
    assert response.json()["image"]
    assert (ToolOut.get_directory(tool["id"]) / "original.webp").is_file()

    response = api_client.get(api_routes.media_tools_tool_id_file_name(tool["id"], "original.webp"))
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/webp"


def test_tool_image_upload_rejects_invalid_file(api_client: TestClient, unique_user: TestUser):
    tool = _create_tool(api_client, unique_user)

    response = api_client.put(
        api_routes.organizers_tools_item_id_image(tool["id"]),
        files={"image": b"not an image"},
        headers=unique_user.token,
    )

    assert response.status_code == 400
    assert (
        api_client.get(api_routes.organizers_tools_item_id(tool["id"]), headers=unique_user.token).json()["image"]
        is None
    )


def test_tool_image_upload_unknown_tool(api_client: TestClient, unique_user: TestUser):
    response = _upload_image(api_client, unique_user, str(uuid4()))

    assert response.status_code == 404


def test_tool_image_of_another_group_is_not_found(
    api_client: TestClient, unique_user: TestUser, unique_user_fn_scoped: TestUser
):
    other_group = unique_user_fn_scoped
    tool = _create_tool(api_client, unique_user)
    assert _upload_image(api_client, unique_user, tool["id"]).status_code == 200

    assert _upload_image(api_client, other_group, tool["id"]).status_code == 404
    response = api_client.delete(api_routes.organizers_tools_item_id_image(tool["id"]), headers=other_group.token)
    assert response.status_code == 404
    assert ToolOut.get_directory(tool["id"]).joinpath("original.webp").exists()


def test_tool_image_requires_organize_permission(
    api_client: TestClient, unique_user: TestUser, unprivileged_user: TestUser
):
    tool = _create_tool(api_client, unique_user)

    assert _upload_image(api_client, unprivileged_user, tool["id"]).status_code == 403
    response = api_client.delete(api_routes.organizers_tools_item_id_image(tool["id"]), headers=unprivileged_user.token)
    assert response.status_code == 403


def test_tool_image_delete(api_client: TestClient, unique_user: TestUser):
    tool = _create_tool(api_client, unique_user)
    _upload_image(api_client, unique_user, tool["id"])

    response = api_client.delete(api_routes.organizers_tools_item_id_image(tool["id"]), headers=unique_user.token)

    assert response.status_code == 200
    assert response.json()["image"] is None
    assert not (ToolOut.get_directory(tool["id"]) / "original.webp").exists()
    response = api_client.get(api_routes.media_tools_tool_id_file_name(tool["id"], "original.webp"))
    assert response.status_code == 404


def test_tool_delete_removes_image(api_client: TestClient, unique_user: TestUser):
    tool = _create_tool(api_client, unique_user)
    _upload_image(api_client, unique_user, tool["id"])

    response = api_client.delete(api_routes.organizers_tools_item_id(tool["id"]), headers=unique_user.token)

    assert response.status_code == 200
    assert not ToolOut.get_directory(tool["id"]).exists()


def test_tool_media_rejects_path_traversal(api_client: TestClient, unique_user: TestUser):
    tool = _create_tool(api_client, unique_user)

    response = api_client.get(api_routes.media_tools_tool_id_file_name(tool["id"], "..%2F..%2Fmealie.db"))

    assert response.status_code in (400, 404)


def test_recipe_update_keeps_tool_category_and_image(api_client: TestClient, unique_user: TestUser):
    tool = _create_tool(api_client, unique_user, category="linen")
    image_key = _upload_image(api_client, unique_user, tool["id"]).json()["image"]
    slug = api_client.post(api_routes.recipes, json={"name": random_string(10)}, headers=unique_user.token).json()

    recipe = api_client.get(api_routes.recipes_slug(slug), headers=unique_user.token).json()
    recipe["tools"] = [{"id": tool["id"], "groupId": unique_user.group_id, "name": tool["name"], "slug": tool["slug"]}]
    response = api_client.put(api_routes.recipes_slug(slug), json=recipe, headers=unique_user.token)
    assert response.status_code == 200

    recipe = api_client.get(api_routes.recipes_slug(slug), headers=unique_user.token).json()
    assert recipe["tools"][0]["category"] == "linen"
    assert recipe["tools"][0]["image"] == image_key
