import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from tests.utils.alembic_reader import ALEMBIC_MIGRATIONS, import_file


def _migration():
    path = next(ALEMBIC_MIGRATIONS.glob("*f3a7c1e9b2d4*.py"))
    return import_file("tool_category_dish_size_and_accessories", path)


def _columns(connection: sa.Connection) -> set[str]:
    return {column["name"] for column in sa.inspect(connection).get_columns("tools")}


def test_tool_icon_becomes_category() -> None:
    migration = _migration()
    engine = sa.create_engine("sqlite://")

    try:
        with engine.connect() as connection:
            connection.execute(sa.text("CREATE TABLE tools (id CHAR(32) PRIMARY KEY, name VARCHAR, icon VARCHAR)"))
            connection.execute(
                sa.text(
                    "INSERT INTO tools (id, name, icon) VALUES "
                    "('1', 'pan', 'dishes'), ('2', 'robot', 'mdi-robot'), ('3', 'spoon', NULL)"
                )
            )

            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()

            columns = _columns(connection)
            assert "icon" not in columns
            assert {"category", "dish_shape", "length", "width", "height", "diameter", "usages", "parent_id"} <= columns
            categories = connection.execute(sa.text("SELECT category FROM tools ORDER BY id")).scalars().all()
            assert categories == ["dishes", "utensils", "utensils"]

            with Operations.context(MigrationContext.configure(connection)):
                migration.downgrade()

            assert "category" not in _columns(connection)
            icons = connection.execute(sa.text("SELECT icon FROM tools ORDER BY id")).scalars().all()
            assert icons == ["dishes", "utensils", "utensils"]
    finally:
        engine.dispose()
