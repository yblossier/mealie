import json
from datetime import datetime
from uuid import uuid4

from mealie.core.config import get_app_settings
from mealie.db.models._model_base import SqlAlchemyBase
from mealie.db.models._model_utils.datetime import NaiveDateTime
from mealie.services.backups_v2.alchemy_exporter import AlchemyExporter
from tests.utils.alembic_reader import alembic_versions


def test_alchemy_exporter():
    settings = get_app_settings()
    exporter = AlchemyExporter(settings.DB_URL)
    data = exporter.dump()

    assert data["alembic_version"] == alembic_versions()
    assert json.dumps(data, indent=4)  # Make sure data is json-serializable

    exporter.engine.dispose()


def test_every_datetime_column_survives_a_backup():
    """Restores rebuild datetimes by column name, so an unregistered one comes back as a string.

    The failure is silent at backup time and only shows up on restore, so this asserts the two stay
    in step rather than waiting for someone to notice a broken restore.
    """
    datetime_columns = {
        column.name
        for table in SqlAlchemyBase.metadata.tables.values()
        for column in table.columns
        if isinstance(column.type, NaiveDateTime)
    }

    unregistered = datetime_columns - AlchemyExporter.look_for_datetime
    assert not unregistered, (
        f"datetime columns missing from AlchemyExporter.look_for_datetime: {sorted(unregistered)}. "
        "Add them, or they will restore as strings."
    )


def test_json_columns_are_restored_as_dumped():
    """A JSON column holding an object is restored untouched, next to the other columns of its row"""
    exporter = AlchemyExporter(get_app_settings().DB_URL)
    row_id = str(uuid4())
    payload = {"id": str(uuid4()), "created_at": "2024-01-02T03:04:05", "nested": {"date": "2024-01-02"}}
    suppliers = [{"name": "Shop", "url": "https://shop.test/?q={query}"}]

    row = exporter.convert_types(
        {"id": row_id, "payload": payload, "tool_suppliers": suppliers, "created_at": "2024-01-02T03:04:05"}
    )

    assert set(row) == {"id", "payload", "tool_suppliers", "created_at"}
    assert row["payload"] == payload
    assert row["tool_suppliers"] == suppliers
    assert isinstance(row["created_at"], datetime)

    exporter.engine.dispose()
