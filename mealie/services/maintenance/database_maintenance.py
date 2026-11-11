from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from mealie.core.root_logger import get_logger
from mealie.db.models.group.report import ReportEntryModel, ReportModel
from mealie.db.models.recipe.ingredient import IngredientFoodNutritionLogModel

DEFAULT_RETENTION = timedelta(days=30)

logger = get_logger()


@dataclass
class DatabaseCleanupResult:
    ai_logs_deleted: int
    reports_deleted: int
    report_entries_deleted: int
    size_before: int | None
    size_after: int | None


def _cutoff(retention: timedelta) -> datetime:
    return datetime.now(UTC).replace(tzinfo=None) - retention


def get_database_size(session: Session) -> int | None:
    """Size of the database in bytes, or None when the engine doesn't expose it"""
    dialect = session.get_bind().dialect.name

    try:
        if dialect == "sqlite":
            page_count = session.execute(text("PRAGMA page_count")).scalar_one()
            page_size = session.execute(text("PRAGMA page_size")).scalar_one()
            return int(page_count) * int(page_size)
        if dialect == "postgresql":
            return int(session.execute(text("SELECT pg_database_size(current_database())")).scalar_one())
    except Exception as e:
        logger.warning(f"Unable to read the database size: {e}")

    return None


def count_cleanable_rows(session: Session, retention: timedelta = DEFAULT_RETENTION) -> int:
    cutoff = _cutoff(retention)
    ai_logs = session.execute(
        select(func.count())
        .select_from(IngredientFoodNutritionLogModel)
        .where(IngredientFoodNutritionLogModel.created_at < cutoff)
    ).scalar_one()
    reports = session.execute(
        select(func.count()).select_from(ReportModel).where(ReportModel.timestamp < cutoff)
    ).scalar_one()
    return int(ai_logs) + int(reports)


def _vacuum(session: Session) -> None:
    """Gives the space of the deleted rows back to the file system (best effort)"""
    engine = session.get_bind()
    statement = "VACUUM" if engine.dialect.name == "sqlite" else "VACUUM ANALYZE"

    try:
        with engine.connect() as connection:
            connection.execution_options(isolation_level="AUTOCOMMIT").execute(text(statement))
    except Exception as e:
        logger.warning(f"Database vacuum skipped: {e}")


def clean_database(
    session: Session, retention: timedelta = DEFAULT_RETENTION, vacuum: bool = True
) -> DatabaseCleanupResult:
    """Deletes the AI logs and the reports older than the retention period, then compacts the database"""
    size_before = get_database_size(session)
    cutoff = _cutoff(retention)

    ai_logs = session.execute(
        delete(IngredientFoodNutritionLogModel).where(IngredientFoodNutritionLogModel.created_at < cutoff)
    ).rowcount  # type: ignore[attr-defined]

    old_report_ids = select(ReportModel.id).where(ReportModel.timestamp < cutoff)
    report_entries = session.execute(
        delete(ReportEntryModel).where(ReportEntryModel.report_id.in_(old_report_ids))
    ).rowcount  # type: ignore[attr-defined]
    reports = session.execute(delete(ReportModel).where(ReportModel.timestamp < cutoff)).rowcount  # type: ignore[attr-defined]

    session.commit()

    if vacuum:
        _vacuum(session)

    return DatabaseCleanupResult(
        ai_logs_deleted=ai_logs or 0,
        reports_deleted=reports or 0,
        report_entries_deleted=report_entries or 0,
        size_before=size_before,
        size_after=get_database_size(session),
    )
