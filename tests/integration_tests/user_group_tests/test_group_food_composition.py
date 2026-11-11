import asyncio
from collections.abc import Generator, Sequence

import httpx
import pytest
from fastapi.testclient import TestClient

from mealie.repos.repository_food_composition import ORIGIN_API, ORIGIN_IMPORT, RepositoryFoodComposition
from mealie.services.recipe.ciqual_import import DEFAULT_CIQUAL_URL, CiqualDataverseClient
from mealie.services.recipe.ciqual_refresh_service import CiqualRefreshService
from mealie.services.recipe.food_composition_service import CompositionFood, get_table
from mealie.services.recipe.food_reference_service import FoodReferenceService
from mealie.services.recipe.food_reference_types import NUTRIENT_KEYS, FoodReferenceResult
from tests import utils
from tests.unit_tests.services_tests.test_ciqual_import import ALIM_XML, COMPO_XML, _dataset
from tests.utils import api_routes
from tests.utils.fixture_schemas import TestUser
from tests.utils.food_references import clear_food_references

DATASET_URL = "https://data.example.org/dataset.xhtml?persistentId=doi:10.57745/TEST"


@pytest.fixture(autouse=True)
def empty_referential() -> Generator[None]:
    clear_food_references()
    yield
    clear_food_references()


@pytest.fixture()
def dataverse(monkeypatch: pytest.MonkeyPatch) -> list[httpx.Request]:
    """The Ciqual dataset, published by a mocked Dataverse"""
    requests: list[httpx.Request] = []
    files = {10: ALIM_XML.encode("cp1252"), 11: COMPO_XML.encode("cp1252")}

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/datasets/:persistentId/":
            return httpx.Response(200, json=_dataset([(10, "alim_2025_11_03.xml"), (11, "compo_2025_11_03.xml")]))
        return httpx.Response(200, content=files[int(request.url.path.rsplit("/", 1)[-1])])

    monkeypatch.setattr(CiqualDataverseClient, "transport", httpx.MockTransport(respond))
    return requests


def _food(source: str, code: str, name: str, calories: float = 100) -> FoodReferenceResult:
    return FoodReferenceResult(
        source=source,  # type: ignore[arg-type]
        code=code,
        name=name,
        nutrients={key: (calories if key == "calories" else None) for key in NUTRIENT_KEYS},
    )


class FakeApi:
    def __init__(self, foods: Sequence[FoodReferenceResult] = (), error: Exception | None = None) -> None:
        self.foods = list(foods)
        self.error = error
        self.queries: list[str] = []

    async def __call__(self, query: str) -> list[FoodReferenceResult]:
        self.queries.append(query)
        if self.error:
            raise self.error
        return self.foods


def _lookup(service: FoodReferenceService, source: str, query: str, api: FakeApi):
    return asyncio.run(service.lookup(source, query, api))  # type: ignore[arg-type]


# ======================================================================================================================
# Referential and lookup rule


def test_bundled_tables_stand_for_the_sources_never_imported(unique_user: TestUser):
    service = FoodReferenceService(RepositoryFoodComposition(unique_user.repos.session))

    assert service.table("ciqual") is get_table("ciqual")
    assert service.table("usda") is get_table("usda")
    assert len(service.table("off")) == 0


def test_lookup_uses_the_referential_first(unique_user: TestUser):
    repo = RepositoryFoodComposition(unique_user.repos.session)
    repo.add_api_foods("off", [{"code": "1", "name": "Zorglub feuilleté", "nutrients": {"calories": 378}}])
    api = FakeApi([_food("off", "2", "Zorglub feuilleté au beurre")])

    result = _lookup(FoodReferenceService(repo), "off", "zorglub feuilleté", api)

    assert api.queries == []
    assert not result.api_called
    assert [match.food.code for match in result.matches] == ["1"]


def test_lookup_calls_the_api_and_enriches_the_referential(unique_user: TestUser):
    repo = RepositoryFoodComposition(unique_user.repos.session)
    service = FoodReferenceService(repo)
    api = FakeApi([_food("off", "2", "Zorglub feuilleté"), _food("off", "3", "Biscuit au zorglub")])

    result = _lookup(service, "off", "zorglub feuilleté", api)

    assert api.queries == ["zorglub feuilleté"]
    assert result.matches[0].food.code == "2"
    assert result.added == 2
    assert repo.counts() == {("off", ORIGIN_API): 2}

    # the next lookup finds the food in the referential, without calling the API
    again = _lookup(service, "off", "zorglub feuilleté", api)
    assert len(api.queries) == 1
    assert again.matches[0].food.code == "2"


def test_lookup_merges_both_without_duplicates_when_none_is_relevant(unique_user: TestUser):
    repo = RepositoryFoodComposition(unique_user.repos.session)
    repo.add_api_foods("off", [{"code": "1", "name": "Gâteau zorglub", "nutrients": {"calories": 400}}])
    api = FakeApi(
        [
            _food("off", "1", "Gâteau zorglub"),  # the same food
            _food("off", "9", "Gâteau zorglub"),  # the same name
            _food("off", "2", "Tarte zorglub"),
        ]
    )

    result = _lookup(FoodReferenceService(repo), "off", "zorglub", api)

    assert result.api_called
    assert [match.food.code for match in result.matches] == ["1", "2"]
    # the referential never gets the same food twice
    assert sorted(row.code for row in repo.get_all("off")) == ["1", "2", "9"]


def test_lookup_answers_from_the_referential_when_the_api_fails(unique_user: TestUser):
    repo = RepositoryFoodComposition(unique_user.repos.session)
    repo.add_api_foods("off", [{"code": "1", "name": "Gâteau zorglub", "nutrients": {"calories": 400}}])
    api = FakeApi(error=RuntimeError("down"))

    result = _lookup(FoodReferenceService(repo), "off", "zorglub", api)

    assert result.api_called
    assert isinstance(result.error, RuntimeError)
    assert [match.food.code for match in result.matches] == ["1"]


def test_api_foods_never_duplicate_the_bundled_ones(unique_user: TestUser):
    repo = RepositoryFoodComposition(unique_user.repos.session)
    service = FoodReferenceService(repo)
    bundled = get_table("usda").entries[0].food
    assert isinstance(bundled, CompositionFood)

    added = service.enrich("usda", [_food("usda", bundled.code, bundled.name), _food("usda", "x-new", "Zorglub")])

    assert added == 1
    assert [row.code for row in repo.get_all("usda")] == ["x-new"]


# ======================================================================================================================
# Ciqual refresh


def test_refresh_replaces_the_imported_foods_and_keeps_the_api_ones(unique_user: TestUser, dataverse):
    repo = RepositoryFoodComposition(unique_user.repos.session)
    repo.add_api_foods(
        "ciqual",
        [
            {"code": "999", "name": "Kept", "nutrients": {"calories": 1}},
            {"code": "2000", "name": "Replaced by the import", "nutrients": {"calories": 1}},
        ],
    )
    repo.replace_imported("ciqual", [{"code": "1", "name": "Old import", "nutrients": {"calories": 1}}])

    count = CiqualRefreshService(repo).run(DATASET_URL)

    assert count == 2
    rows = {row.code: row for row in repo.get_all("ciqual")}
    assert set(rows) == {"999", "2000", "13028"}
    assert rows["2000"].origin == ORIGIN_IMPORT and rows["2000"].name == "Citron, pulpe, cru"
    assert rows["999"].origin == ORIGIN_API

    source = repo.get_source("ciqual")
    assert source is not None
    assert (source.status, source.food_count, source.release_time) == ("success", 2, "2025-11-14T10:00:00Z")
    assert source.version == "v3.1 - 2025-11-03"

    # the lookups now use the imported table instead of the bundled one
    table = FoodReferenceService(repo).table("ciqual")
    assert table is not get_table("ciqual")
    assert len(table) == 3


def test_refresh_failure_keeps_the_referential(unique_user: TestUser, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(CiqualDataverseClient, "transport", httpx.MockTransport(lambda request: httpx.Response(503)))
    repo = RepositoryFoodComposition(unique_user.repos.session)

    assert CiqualRefreshService(repo).run(DATASET_URL) == 0

    source = repo.get_source("ciqual")
    assert source is not None
    assert source.status == "error"
    assert "503" in (source.last_error or "")
    assert FoodReferenceService(repo).table("ciqual") is get_table("ciqual")


# ======================================================================================================================
# Routes


def test_get_status(api_client: TestClient, unique_user: TestUser):
    response = api_client.get(api_routes.groups_food_composition, headers=unique_user.token)
    data = utils.assert_deserialize(response, 200)

    assert data["ciqualUrl"] == DEFAULT_CIQUAL_URL
    assert data["ciqualDefaultUrl"] == DEFAULT_CIQUAL_URL
    assert data["ciqualStatus"] == "idle"
    sources = {item["source"]: item for item in data["sources"]}
    assert sources["ciqual"]["bundled"] and sources["ciqual"]["importedCount"] > 1000
    assert sources["off"] == {"source": "off", "importedCount": 0, "apiCount": 0, "bundled": False}


@pytest.mark.parametrize(
    "url",
    ["http://data.example.org/dataset.xhtml?persistentId=doi:1", "https://data.example.org/dataset.xhtml", ""],
)
def test_update_url_is_validated(api_client: TestClient, unique_user: TestUser, url: str):
    response = api_client.put(api_routes.groups_food_composition_ciqual, json={"url": url}, headers=unique_user.token)
    assert response.status_code == 422


def test_update_url_requires_manage_permission(api_client: TestClient, unprivileged_user: TestUser):
    response = api_client.put(
        api_routes.groups_food_composition_ciqual, json={"url": DATASET_URL}, headers=unprivileged_user.token
    )
    assert response.status_code == 403
    response = api_client.post(api_routes.groups_food_composition_ciqual_refresh, headers=unprivileged_user.token)
    assert response.status_code == 403


def test_refresh_route_imports_from_the_configured_url(
    api_client: TestClient, unique_user: TestUser, dataverse: list[httpx.Request]
):
    response = api_client.put(
        api_routes.groups_food_composition_ciqual, json={"url": DATASET_URL}, headers=unique_user.token
    )
    assert utils.assert_deserialize(response, 200)["ciqualUrl"] == DATASET_URL

    response = api_client.post(api_routes.groups_food_composition_ciqual_refresh, headers=unique_user.token)
    assert response.status_code == 202
    assert response.json()["ciqualStatus"] == "running"

    # the test client runs the background task before answering
    assert dataverse[0].url.host == "data.example.org"
    data = utils.assert_deserialize(api_client.get(api_routes.groups_food_composition, headers=unique_user.token), 200)
    assert data["ciqualStatus"] == "success"
    assert data["ciqualVersion"] == "v3.1 - 2025-11-03"
    assert data["ciqualImportedAt"]
    sources = {item["source"]: item for item in data["sources"]}
    assert sources["ciqual"] == {"source": "ciqual", "importedCount": 2, "apiCount": 0, "bundled": False}

    # the nutrition references come from the imported table
    response = api_client.get(
        api_routes.foods_nutrition_references, params={"search": "pomme"}, headers=unique_user.token
    )
    references = utils.assert_deserialize(response, 200)
    ciqual = [reference for reference in references if reference["source"] == "ciqual"]
    assert [reference["code"] for reference in ciqual] == ["13028"]


def test_refresh_route_refuses_a_second_refresh(api_client: TestClient, unique_user: TestUser):
    CiqualRefreshService(RepositoryFoodComposition(unique_user.repos.session)).start()
    response = api_client.post(api_routes.groups_food_composition_ciqual_refresh, headers=unique_user.token)
    assert response.status_code == 409
