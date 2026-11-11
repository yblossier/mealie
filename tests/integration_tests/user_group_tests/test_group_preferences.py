import pytest
from fastapi.testclient import TestClient

from mealie.schema.group.group_preferences import GroupPreferencesUpdate
from tests import utils
from tests.utils import api_routes
from tests.utils.assertion_helpers import assert_ignore_keys
from tests.utils.factories import random_bool
from tests.utils.fixture_schemas import TestUser


def test_get_preferences(api_client: TestClient, unique_user: TestUser) -> None:
    response = api_client.get(api_routes.groups_preferences, headers=unique_user.token)
    assert response.status_code == 200

    preferences = response.json()

    assert preferences["privateGroup"] in {True, False}


def test_preferences_in_group(api_client: TestClient, unique_user: TestUser) -> None:
    response = api_client.get(api_routes.groups_self, headers=unique_user.token)

    assert response.status_code == 200

    group = response.json()

    assert group["preferences"] is not None

    # Spot Check
    assert group["preferences"]["privateGroup"] in {True, False}


def test_update_preferences(api_client: TestClient, unique_user: TestUser) -> None:
    new_data = GroupPreferencesUpdate(private_group=random_bool())

    response = api_client.put(api_routes.groups_preferences, json=new_data.model_dump(), headers=unique_user.token)

    assert response.status_code == 200

    preferences = response.json()

    assert preferences is not None
    assert preferences["privateGroup"] == new_data.private_group

    assert_ignore_keys(new_data.model_dump(by_alias=True), preferences, ["id", "groupId", "usdaApiKey"])


def test_update_settings_preferences(api_client: TestClient, unique_user: TestUser) -> None:
    payload = {
        "defaultTablePageSize": 50,
        "toolSuppliers": [
            {"name": "Shop", "url": "https://shop.example/search?q={query}", "enabled": True},
            {"name": "Other", "url": "https://other.example/s/", "enabled": False},
        ],
        "showToolSupplierLinks": False,
        "offMode": "dev",
        "offAppName": "MyMealie",
        "offAppVersion": "2.0",
        "offAppUuid": "",
        "usdaApiEnabled": False,
        "usdaApiKey": "secret-key",
    }
    response = api_client.put(api_routes.groups_preferences, json=payload, headers=unique_user.token)
    preferences = utils.assert_deserialize(response, 200)

    assert preferences["defaultTablePageSize"] == 50
    assert preferences["toolSuppliers"] == payload["toolSuppliers"]
    assert preferences["showToolSupplierLinks"] is False
    assert (preferences["offMode"], preferences["offAppName"], preferences["offAppVersion"]) == (
        "dev",
        "MyMealie",
        "2.0",
    )
    assert preferences["offAppUuid"] is None
    assert preferences["usdaApiEnabled"] is False
    # the key is never sent back
    assert "usdaApiKey" not in preferences
    assert preferences["usdaApiKeySet"] is True

    # without a key, the saved one is kept
    payload.pop("usdaApiKey")
    response = api_client.put(api_routes.groups_preferences, json=payload, headers=unique_user.token)
    assert utils.assert_deserialize(response, 200)["usdaApiKeySet"] is True
    group = utils.assert_deserialize(api_client.get(api_routes.groups_self, headers=unique_user.token), 200)
    assert group["preferences"]["defaultTablePageSize"] == 50
    assert "usdaApiKey" not in group["preferences"]

    # an empty key removes it
    response = api_client.put(
        api_routes.groups_preferences, json={**payload, "usdaApiKey": ""}, headers=unique_user.token
    )
    assert utils.assert_deserialize(response, 200)["usdaApiKeySet"] is False


@pytest.mark.parametrize(
    "invalid",
    [
        {"defaultTablePageSize": 1},
        {"defaultTablePageSize": 10_000},
        {"offMode": "staging"},
        {"toolSuppliers": [{"name": "Shop", "url": "ftp://shop.example", "enabled": True}]},
        {"toolSuppliers": [{"name": " ", "url": "https://shop.example", "enabled": True}]},
    ],
)
def test_update_settings_preferences_validation(api_client: TestClient, unique_user: TestUser, invalid: dict) -> None:
    response = api_client.put(api_routes.groups_preferences, json=invalid, headers=unique_user.token)
    assert response.status_code == 422


def test_user_table_page_size(api_client: TestClient, unique_user: TestUser) -> None:
    user = utils.assert_deserialize(api_client.get(api_routes.users_self, headers=unique_user.token), 200)
    assert user["tablePageSize"] is None

    for value in (100, None):
        response = api_client.put(
            api_routes.users_item_id(unique_user.user_id),
            json={**user, "tablePageSize": value},
            headers=unique_user.token,
        )
        assert response.status_code == 200
        user = utils.assert_deserialize(api_client.get(api_routes.users_self, headers=unique_user.token), 200)
        assert user["tablePageSize"] == value

    response = api_client.put(
        api_routes.users_item_id(unique_user.user_id), json={**user, "tablePageSize": 2}, headers=unique_user.token
    )
    assert response.status_code == 422
