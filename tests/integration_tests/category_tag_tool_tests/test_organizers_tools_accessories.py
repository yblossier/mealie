"""Integration tests for dish sizes and usages, and accessories linked to their appliance."""

from fastapi.testclient import TestClient

from mealie.schema.recipe.recipe_organizers import ToolCategory, ToolSave
from tests.utils import api_routes
from tests.utils.factories import random_string
from tests.utils.fixture_schemas import TestUser


def _create_tool(api_client: TestClient, user: TestUser, **extra) -> dict:
    response = api_client.post(
        api_routes.organizers_tools, json={"name": random_string(10), **extra}, headers=user.token
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_recipe(api_client: TestClient, user: TestUser) -> str:
    return api_client.post(api_routes.recipes, json={"name": random_string(10)}, headers=user.token).json()


def _set_recipe_tools(api_client: TestClient, user: TestUser, slug: str, tools: list[dict]) -> list[str]:
    recipe = api_client.get(api_routes.recipes_slug(slug), headers=user.token).json()
    recipe["tools"] = [
        {"id": tool["id"], "groupId": user.group_id, "name": tool["name"], "slug": tool["slug"]} for tool in tools
    ]
    response = api_client.put(api_routes.recipes_slug(slug), json=recipe, headers=user.token)
    assert response.status_code == 200, response.text

    recipe = api_client.get(api_routes.recipes_slug(slug), headers=user.token).json()
    return sorted(tool["id"] for tool in recipe["tools"])


def test_dish_keeps_size_and_usages(api_client: TestClient, unique_user: TestUser):
    tool = _create_tool(
        api_client,
        unique_user,
        category="dishes",
        dishShape="rectangular",
        length=30,
        width=20,
        height=6.5,
        diameter=24,
        usages=["oven", "induction", "oven"],
    )

    assert tool["dishShape"] == "rectangular"
    assert (tool["length"], tool["width"], tool["height"]) == (30, 20, 6.5)
    assert tool["diameter"] is None
    assert tool["usages"] == ["induction", "oven"]

    fetched = api_client.get(api_routes.organizers_tools_item_id(tool["id"]), headers=unique_user.token).json()
    assert fetched["usages"] == ["induction", "oven"]


def test_round_dish_keeps_only_diameter(api_client: TestClient, unique_user: TestUser):
    tool = _create_tool(
        api_client, unique_user, category="dishes", dishShape="round", length=30, width=20, diameter=24, height=5
    )

    assert (tool["length"], tool["width"], tool["diameter"], tool["height"]) == (None, None, 24, 5)


def test_dish_fields_are_dropped_for_other_categories(api_client: TestClient, unique_user: TestUser):
    tool = _create_tool(api_client, unique_user, category="linen", length=30, usages=["gas"])

    assert tool["length"] is None
    assert tool["usages"] == []


def test_dish_rejects_unknown_usage(api_client: TestClient, unique_user: TestUser):
    response = api_client.post(
        api_routes.organizers_tools,
        json={"name": random_string(10), "category": "dishes", "usages": ["campfire"]},
        headers=unique_user.token,
    )

    assert response.status_code == 422


def test_accessory_links_to_appliance(api_client: TestClient, unique_user: TestUser):
    appliance = _create_tool(api_client, unique_user, category="appliance")
    accessory = _create_tool(api_client, unique_user, category="appliance", parentId=appliance["id"])

    assert accessory["parentId"] == appliance["id"]


def test_parent_is_dropped_outside_appliances(api_client: TestClient, unique_user: TestUser):
    appliance = _create_tool(api_client, unique_user, category="appliance")
    tool = _create_tool(api_client, unique_user, category="utensils", parentId=appliance["id"])

    assert tool["parentId"] is None


def test_accessory_parent_must_be_a_top_level_appliance(api_client: TestClient, unique_user: TestUser):
    dish = _create_tool(api_client, unique_user, category="dishes")
    appliance = _create_tool(api_client, unique_user, category="appliance")
    accessory = _create_tool(api_client, unique_user, category="appliance", parentId=appliance["id"])

    for parent_id in (dish["id"], accessory["id"]):
        response = api_client.post(
            api_routes.organizers_tools,
            json={"name": random_string(10), "category": "appliance", "parentId": parent_id},
            headers=unique_user.token,
        )
        assert response.status_code == 400

    # an appliance with accessories can't become an accessory itself
    other = _create_tool(api_client, unique_user, category="appliance")
    response = api_client.put(
        api_routes.organizers_tools_item_id(appliance["id"]),
        json={"name": appliance["name"], "category": "appliance", "parentId": other["id"]},
        headers=unique_user.token,
    )
    assert response.status_code == 400

    response = api_client.put(
        api_routes.organizers_tools_item_id(appliance["id"]),
        json={"name": appliance["name"], "category": "appliance", "parentId": appliance["id"]},
        headers=unique_user.token,
    )
    assert response.status_code == 400


def test_accessory_parent_from_other_group_is_rejected(
    api_client: TestClient, unique_user: TestUser, g2_user: TestUser
):
    # created through the repo: g2_user is created by an admin without the organize permission
    foreign = g2_user.repos.tools.create(
        ToolSave(name=random_string(10), group_id=g2_user.group_id, category=ToolCategory.appliance)
    )

    response = api_client.post(
        api_routes.organizers_tools,
        json={"name": random_string(10), "category": "appliance", "parentId": str(foreign.id)},
        headers=unique_user.token,
    )

    assert response.status_code == 400
    g2_user.repos.tools.delete(foreign.id)


def test_deleting_or_recategorizing_appliance_releases_accessories(api_client: TestClient, unique_user: TestUser):
    appliance = _create_tool(api_client, unique_user, category="appliance")
    accessory = _create_tool(api_client, unique_user, category="appliance", parentId=appliance["id"])

    response = api_client.put(
        api_routes.organizers_tools_item_id(appliance["id"]),
        json={"name": appliance["name"], "category": "utensils"},
        headers=unique_user.token,
    )
    assert response.status_code == 200
    fetched = api_client.get(api_routes.organizers_tools_item_id(accessory["id"]), headers=unique_user.token).json()
    assert fetched["parentId"] is None

    appliance = _create_tool(api_client, unique_user, category="appliance")
    accessory = _create_tool(api_client, unique_user, category="appliance", parentId=appliance["id"])
    response = api_client.delete(api_routes.organizers_tools_item_id(appliance["id"]), headers=unique_user.token)
    assert response.status_code == 200
    fetched = api_client.get(api_routes.organizers_tools_item_id(accessory["id"]), headers=unique_user.token).json()
    assert fetched["parentId"] is None


def test_merge_moves_accessories_to_the_merged_appliance(api_client: TestClient, unique_user: TestUser):
    old = _create_tool(api_client, unique_user, category="appliance")
    new = _create_tool(api_client, unique_user, category="appliance")
    accessory = _create_tool(api_client, unique_user, category="appliance", parentId=old["id"])

    response = api_client.post(
        api_routes.organizers_tools_merge, json={"fromId": old["id"], "toId": new["id"]}, headers=unique_user.token
    )
    assert response.status_code == 200

    fetched = api_client.get(api_routes.organizers_tools_item_id(accessory["id"]), headers=unique_user.token).json()
    assert fetched["parentId"] == new["id"]


def test_recipe_accessory_brings_its_appliance(api_client: TestClient, unique_user: TestUser):
    appliance = _create_tool(api_client, unique_user, category="appliance")
    accessory = _create_tool(api_client, unique_user, category="appliance", parentId=appliance["id"])
    slug = _create_recipe(api_client, unique_user)

    tool_ids = _set_recipe_tools(api_client, unique_user, slug, [accessory])

    assert tool_ids == sorted([appliance["id"], accessory["id"]])


def test_recipe_removing_appliance_removes_its_accessories(api_client: TestClient, unique_user: TestUser):
    appliance = _create_tool(api_client, unique_user, category="appliance")
    accessory = _create_tool(api_client, unique_user, category="appliance", parentId=appliance["id"])
    other = _create_tool(api_client, unique_user)
    slug = _create_recipe(api_client, unique_user)
    _set_recipe_tools(api_client, unique_user, slug, [appliance, accessory, other])

    tool_ids = _set_recipe_tools(api_client, unique_user, slug, [accessory, other])

    assert tool_ids == [other["id"]]


def test_recipe_removing_accessory_keeps_its_appliance(api_client: TestClient, unique_user: TestUser):
    appliance = _create_tool(api_client, unique_user, category="appliance")
    accessory = _create_tool(api_client, unique_user, category="appliance", parentId=appliance["id"])
    slug = _create_recipe(api_client, unique_user)
    _set_recipe_tools(api_client, unique_user, slug, [appliance, accessory])

    tool_ids = _set_recipe_tools(api_client, unique_user, slug, [appliance])

    assert tool_ids == [appliance["id"]]


def test_recipe_patch_applies_accessory_rules(api_client: TestClient, unique_user: TestUser):
    appliance = _create_tool(api_client, unique_user, category="appliance")
    accessory = _create_tool(api_client, unique_user, category="appliance", parentId=appliance["id"])
    slug = _create_recipe(api_client, unique_user)

    response = api_client.patch(
        api_routes.recipes_slug(slug),
        json={"tools": [{"id": accessory["id"], "name": accessory["name"], "slug": accessory["slug"]}]},
        headers=unique_user.token,
    )
    assert response.status_code == 200, response.text

    recipe = api_client.get(api_routes.recipes_slug(slug), headers=unique_user.token).json()
    assert sorted(tool["id"] for tool in recipe["tools"]) == sorted([appliance["id"], accessory["id"]])
