import json
from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from mealie.schema.group.ai_providers import AIProviderCreate, AIProviderSettingsUpdate
from mealie.schema.openai.thermomix import OpenAIThermomixStep, OpenAIThermomixView
from mealie.schema.recipe.recipe import RecipeOut
from mealie.services.openai import OpenAIService
from tests.utils import api_routes
from tests.utils.factories import random_string
from tests.utils.fixture_schemas import TestUser


def thermomix_route(slug: str) -> str:
    return f"{api_routes.recipes_slug(slug)}/thermomix"


def create_recipe(api_client: TestClient, user: TestUser) -> dict:
    r = api_client.post(api_routes.recipes, json={"name": random_string()}, headers=user.token)
    assert r.status_code == 201
    return api_client.get(api_routes.recipes_slug(r.json()), headers=user.token).json()


def create_tool(api_client: TestClient, user: TestUser) -> dict:
    r = api_client.post(api_routes.organizers_tools, json={"name": random_string()}, headers=user.token)
    assert r.status_code == 201
    return r.json()


@pytest.fixture()
def ai_provider(unique_user: TestUser) -> Generator[None]:
    provider = unique_user.repos.group_ai_providers.create(
        AIProviderCreate(name=random_string(), model="gpt-4o", api_key="test-key")
    )
    unique_user.repos.group_ai_provider_settings.update(
        unique_user.repos.group_id,
        AIProviderSettingsUpdate(default_provider_id=provider.id, audio_provider_id=None, image_provider_id=None),
    )
    yield
    unique_user.repos.group_ai_provider_settings.update(
        unique_user.repos.group_id,
        AIProviderSettingsUpdate(default_provider_id=None, audio_provider_id=None, image_provider_id=None),
    )


def test_step_tool_references(api_client: TestClient, unique_user: TestUser):
    recipe = create_recipe(api_client, unique_user)
    pan, whisk = create_tool(api_client, unique_user), create_tool(api_client, unique_user)

    recipe["tools"] = [pan, whisk]
    recipe["recipeInstructions"] = [
        {"text": "Whisk the eggs.", "toolReferences": [{"referenceId": whisk["id"]}]},
        {"text": "Cook them.", "toolReferences": [{"referenceId": pan["id"]}, {"referenceId": whisk["id"]}]},
    ]
    r = api_client.put(api_routes.recipes_slug(recipe["slug"]), json=recipe, headers=unique_user.token)
    assert r.status_code == 200

    saved = api_client.get(api_routes.recipes_slug(recipe["slug"]), headers=unique_user.token).json()
    refs = [[ref["referenceId"] for ref in step["toolReferences"]] for step in saved["recipeInstructions"]]
    assert refs == [[whisk["id"]], [pan["id"], whisk["id"]]]

    # removing a tool from the recipe unlinks it from the steps
    saved["tools"] = [pan]
    r = api_client.put(api_routes.recipes_slug(recipe["slug"]), json=saved, headers=unique_user.token)
    assert r.status_code == 200
    refs = [[ref["referenceId"] for ref in step["toolReferences"]] for step in r.json()["recipeInstructions"]]
    assert refs == [[], [pan["id"]]]

    # a patch can't link a tool the recipe doesn't use
    instructions = r.json()["recipeInstructions"]
    instructions[0]["toolReferences"] = [{"referenceId": whisk["id"]}, {"referenceId": pan["id"]}]
    r = api_client.patch(
        api_routes.recipes_slug(recipe["slug"]),
        json={"recipeInstructions": instructions},
        headers=unique_user.token,
    )
    assert r.status_code == 200
    assert [ref["referenceId"] for ref in r.json()["recipeInstructions"][0]["toolReferences"]] == [pan["id"]]


def test_step_references(api_client: TestClient, unique_user: TestUser):
    recipe = create_recipe(api_client, unique_user)
    ids = [str(uuid4()) for _ in range(3)]
    recipe["recipeInstructions"] = [
        {"id": ids[0], "text": "Make the dough."},
        {"id": ids[1], "text": "Make the cream.", "stepReferences": [{"referenceId": ids[1]}]},
        {
            "id": ids[2],
            "text": "Fill the dough with the cream.",
            "stepReferences": [
                {"referenceId": ids[0]},
                {"referenceId": ids[1]},
                {"referenceId": ids[0]},
                {"referenceId": str(uuid4())},
            ],
        },
    ]
    r = api_client.put(api_routes.recipes_slug(recipe["slug"]), json=recipe, headers=unique_user.token)
    assert r.status_code == 200

    # steps get new ids on save, the references follow them; self, duplicate and unknown references are dropped
    saved = api_client.get(api_routes.recipes_slug(recipe["slug"]), headers=unique_user.token).json()
    ids = [step["id"] for step in saved["recipeInstructions"]]
    refs = [[ref["referenceId"] for ref in step["stepReferences"]] for step in saved["recipeInstructions"]]
    assert refs == [[], [], [ids[0], ids[1]]]

    # removing a step unlinks it from the steps using it
    instructions = [step for step in saved["recipeInstructions"] if step["id"] != ids[1]]
    r = api_client.patch(
        api_routes.recipes_slug(recipe["slug"]),
        json={"recipeInstructions": instructions},
        headers=unique_user.token,
    )
    assert r.status_code == 200
    patched = r.json()["recipeInstructions"]
    assert [ref["referenceId"] for ref in patched[1]["stepReferences"]] == [patched[0]["id"]]

    # a duplicated recipe points to its own steps
    r = api_client.post(
        api_routes.recipes_slug_duplicate(recipe["slug"]), json={"name": random_string()}, headers=unique_user.token
    )
    assert r.status_code == 201
    copy = r.json()["recipeInstructions"]
    assert copy[0]["id"] != patched[0]["id"]
    assert [ref["referenceId"] for ref in copy[1]["stepReferences"]] == [copy[0]["id"]]


def test_thermomix_view_without_ai(api_client: TestClient, unique_user: TestUser):
    recipe = create_recipe(api_client, unique_user)
    recipe["recipeInstructions"] = [{"text": "Chop the onion."}]
    api_client.put(api_routes.recipes_slug(recipe["slug"]), json=recipe, headers=unique_user.token)

    r = api_client.get(thermomix_route(recipe["slug"]), headers=unique_user.token)
    assert r.status_code == 200
    assert r.json() is None

    r = api_client.post(thermomix_route(recipe["slug"]), headers=unique_user.token)
    assert r.status_code == 400


def test_thermomix_view(
    api_client: TestClient, unique_user: TestUser, ai_provider: None, monkeypatch: pytest.MonkeyPatch
):
    recipe = create_recipe(api_client, unique_user)
    knife, pan = create_tool(api_client, unique_user), create_tool(api_client, unique_user)
    recipe["tools"] = [knife, pan]
    recipe["recipeInstructions"] = [
        {
            "title": "Base",
            "summary": "Onion",
            "text": "Chop the onion.",
            "toolReferences": [{"referenceId": knife["id"]}],
        },
        {
            "text": "Cook the risotto for 18 minutes.",
            "restSeconds": 120,
            "coolingSeconds": 0,
            "toolReferences": [{"referenceId": pan["id"]}],
        },
    ]
    r = api_client.put(api_routes.recipes_slug(recipe["slug"]), json=recipe, headers=unique_user.token)
    steps = r.json()["recipeInstructions"]

    messages: list[str] = []

    async def mock_get_response(self, prompt, message, *args, response_schema=None, **kwargs):
        messages.append(message)
        assert response_schema is OpenAIThermomixView
        return OpenAIThermomixView(
            steps=[
                OpenAIThermomixStep(
                    text="Chop 5 sec/speed 5.",
                    time_seconds=5,
                    speed="5",
                    source_steps=[1],
                    tools=[f" {knife['name'].upper()} ", "unknown tool", knife["name"]],
                ),
                OpenAIThermomixStep(
                    text="Cook 18 min/100°C/reverse/speed 1.",
                    time_seconds=1080,
                    temperature="100°C",
                    speed="1",
                    reverse=True,
                    source_steps=[2, 9],
                    cautions=["  Le bol est brûlant.  ", " "],
                ),
                OpenAIThermomixStep(
                    text="Serve.",
                    title="Serving",
                    rest_seconds=120,
                    cooling_seconds=0,
                    cooking_seconds=-5,
                    accessory=pan["name"],
                ),
                OpenAIThermomixStep(text="  "),
            ],
            notes=["Do not exceed 2.2 L."],
        )

    monkeypatch.setattr(OpenAIService, "get_response", mock_get_response)

    r = api_client.post(thermomix_route(recipe["slug"]), headers=unique_user.token)
    assert r.status_code == 200
    view = r.json()
    assert "Chop the onion." in messages[0]
    assert '"section": "Base"' in messages[0]
    # only the step times that are set are sent
    assert '"rest_seconds": 120' in messages[0]
    assert "cooling_seconds" not in messages[0]
    # the tools linked to the steps are sent, and the generated steps keep the recipe tools still used
    assert f'"tools": ["{knife["name"]}"]' in messages[0]
    assert [step["toolIds"] for step in view["steps"]] == [[knife["id"]], [], [pan["id"]]]
    assert [step["text"] for step in view["steps"]] == [
        "Chop 5 sec/speed 5.",
        "Cook 18 min/100°C/reverse/speed 1.",
        "Serve.",
    ]
    # the section starts on its first step only, and the step titles come from the recipe or the AI
    assert [step["title"] for step in view["steps"]] == ["Base", None, None]
    assert [step["summary"] for step in view["steps"]] == ["Onion", None, "Serving"]
    assert view["steps"][1]["reverse"] is True
    # the cautions stay on the step they concern
    assert [step["cautions"] for step in view["steps"]] == [[], ["Le bol est brûlant."], []]
    # the other step times come from the generated recipe, and only positive ones are kept
    assert [(s["restSeconds"], s["coolingSeconds"], s["cookingSeconds"]) for s in view["steps"]] == [
        (None, None, None),
        (None, None, None),
        (120, None, None),
    ]
    assert view["steps"][1]["sourceStepIds"] == [steps[1]["id"]]
    assert view["notes"] == ["Do not exceed 2.2 L."]
    assert view["model"] == "gpt-4o"

    # the view is kept apart from the recipe, which is left untouched
    assert api_client.get(thermomix_route(recipe["slug"]), headers=unique_user.token).json() == view
    saved = api_client.get(api_routes.recipes_slug(recipe["slug"]), headers=unique_user.token).json()
    assert [step["text"] for step in saved["recipeInstructions"]] == [
        "Chop the onion.",
        "Cook the risotto for 18 minutes.",
    ]

    # a view stored before the step titles and cautions existed takes the titles from its original steps
    path = RecipeOut.directory_from_id(recipe["id"]) / "thermomix.json"
    stored = json.loads(path.read_text(encoding="utf-8"))
    for step in stored["steps"]:
        step.pop("summary", None)
        step.pop("cautions", None)
    path.write_text(json.dumps(stored), encoding="utf-8")
    old_view = api_client.get(thermomix_route(recipe["slug"]), headers=unique_user.token).json()
    assert [step["summary"] for step in old_view["steps"]] == ["Onion", None, None]
    assert [step["cautions"] for step in old_view["steps"]] == [[], [], []]

    r = api_client.delete(thermomix_route(recipe["slug"]), headers=unique_user.token)
    assert r.status_code == 200
    assert api_client.get(thermomix_route(recipe["slug"]), headers=unique_user.token).json() is None


def test_thermomix_logs(
    api_client: TestClient, unique_user: TestUser, ai_provider: None, monkeypatch: pytest.MonkeyPatch
):
    recipe = create_recipe(api_client, unique_user)
    recipe["recipeInstructions"] = [{"text": "Chop the onion."}]
    api_client.put(api_routes.recipes_slug(recipe["slug"]), json=recipe, headers=unique_user.token)
    logs_route = f"{thermomix_route(recipe['slug'])}/logs"

    assert api_client.get(logs_route, headers=unique_user.token).json() == []

    async def failing_get_response(self, *args, **kwargs):
        raise Exception("OpenAI Request Failed. APITimeoutError: Request timed out.")

    monkeypatch.setattr(OpenAIService, "get_response", failing_get_response)
    assert api_client.post(thermomix_route(recipe["slug"]), headers=unique_user.token).status_code == 502

    async def get_response(self, *args, **kwargs):
        return OpenAIThermomixView(steps=[OpenAIThermomixStep(text="Chop 5 sec/speed 5.")])

    monkeypatch.setattr(OpenAIService, "get_response", get_response)
    assert api_client.post(thermomix_route(recipe["slug"]), headers=unique_user.token).status_code == 200

    logs = api_client.get(logs_route, headers=unique_user.token).json()
    assert [log["status"] for log in logs] == ["success", "error"]
    success, error = logs
    assert success["model"] == "gpt-4o"
    assert success["stepsCount"] == 1
    assert success["response"]["steps"][0]["text"] == "Chop 5 sec/speed 5."
    assert "Chop the onion." in success["request"]
    assert success["estimatedTokens"] > 0
    assert success["user"]
    assert "APITimeoutError" in error["error"]
    assert error["response"] is None

    # deleting the view keeps its history
    api_client.delete(thermomix_route(recipe["slug"]), headers=unique_user.token)
    assert len(api_client.get(logs_route, headers=unique_user.token).json()) == 2


def test_thermomix_view_is_protected(
    api_client: TestClient, unique_user: TestUser, h2_user: TestUser, g2_user: TestUser, ai_provider: None
):
    recipe = create_recipe(api_client, unique_user)
    route = thermomix_route(recipe["slug"])

    # another group doesn't even find the recipe
    for method in ("get", "post", "delete"):
        assert getattr(api_client, method)(route, headers=g2_user.token).status_code == 404
    assert api_client.get(f"{route}/logs", headers=g2_user.token).status_code == 404

    # another household of the group reads it like the recipe itself, but can't generate or delete it
    # while edits from other households are locked (the default)
    assert api_client.get(route, headers=h2_user.token).status_code == 200
    assert api_client.get(f"{route}/logs", headers=h2_user.token).status_code == 200
    assert api_client.get(api_routes.recipes_slug_allergens(recipe["slug"]), headers=h2_user.token).status_code == 200
    assert api_client.post(route, headers=h2_user.token).status_code == 403
    assert api_client.delete(route, headers=h2_user.token).status_code == 403
