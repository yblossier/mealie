from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from mealie.db.models.group.report import ReportEntryModel, ReportModel
from mealie.db.models.recipe.ingredient import IngredientFoodNutritionLogModel
from mealie.schema.recipe.recipe_ingredient import IngredientFoodSave
from mealie.services.maintenance import database_maintenance
from tests.utils import api_routes
from tests.utils.factories import random_string
from tests.utils.fixture_schemas import TestUser


def _seed(session: Session, user: TestUser) -> dict[str, list]:
    food = user.repos.ingredient_foods.create(IngredientFoodSave(name=random_string(), group_id=user.group_id))
    old = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=45)
    recent = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=2)

    ids: dict[str, list] = {"old_logs": [], "recent_logs": [], "old_reports": [], "recent_reports": []}
    for created_at, key in ((old, "old_logs"), (recent, "recent_logs")):
        log = IngredientFoodNutritionLogModel(group_id=user.group_id, food_id=food.id, origin="ai", session=session)
        log.created_at = created_at
        session.add(log)
        session.flush()
        ids[key].append(log.id)

    for timestamp, key in ((old, "old_reports"), (recent, "recent_reports")):
        report = ReportModel(name="r", status="success", category="migration", group_id=user.group_id, session=session)
        report.timestamp = timestamp
        report.entries = [
            ReportEntryModel(success=True, message="m", exception="", timestamp=timestamp, session=session)
        ]
        session.add(report)
        session.flush()
        ids[key].append(report.id)

    session.commit()
    return ids


def test_clean_database_removes_only_entries_older_than_a_month(session: Session, unique_user: TestUser):
    ids = _seed(session, unique_user)

    assert database_maintenance.count_cleanable_rows(session) >= 2
    result = database_maintenance.clean_database(session, vacuum=False)

    assert result.ai_logs_deleted >= 1
    assert result.reports_deleted >= 1
    assert result.report_entries_deleted >= 1

    remaining_logs = set(session.scalars(select(IngredientFoodNutritionLogModel.id)).all())
    remaining_reports = set(session.scalars(select(ReportModel.id)).all())
    assert not remaining_logs & set(ids["old_logs"])
    assert set(ids["recent_logs"]) <= remaining_logs
    assert not remaining_reports & set(ids["old_reports"])
    assert set(ids["recent_reports"]) <= remaining_reports


def test_get_database_size(session: Session):
    size = database_maintenance.get_database_size(session)
    assert size is not None and size > 0


def test_maintenance_summary_and_clean_database_route(api_client: TestClient, admin_user: TestUser):
    response = api_client.get(api_routes.admin_maintenance, headers=admin_user.token)
    assert response.status_code == 200
    data = response.json()
    assert data["databaseSize"]
    assert "cleanableDatabaseRows" in data

    response = api_client.post(f"{api_routes.admin_maintenance}/clean/database", headers=admin_user.token)
    assert response.status_code == 200


def test_clean_database_route_requires_admin(api_client: TestClient, unique_user: TestUser):
    response = api_client.post(f"{api_routes.admin_maintenance}/clean/database", headers=unique_user.token)
    assert response.status_code == 403
