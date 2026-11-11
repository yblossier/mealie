"""
Refresh of the Ciqual referential from the open data of Anses, run in the background: the latest table published at
the configured URL replaces the imported Ciqual foods of the database, in one transaction.
"""

from datetime import timedelta

from mealie.core.root_logger import get_logger
from mealie.db.db_setup import session_context
from mealie.db.models._model_utils.datetime import get_utc_now
from mealie.repos.repository_food_composition import ORIGIN_API, ORIGIN_IMPORT, RepositoryFoodComposition
from mealie.schema.group.group_food_composition import FoodCompositionSourceCount, FoodCompositionStatus
from mealie.services.recipe.ciqual_import import DEFAULT_CIQUAL_URL, CiqualDataverseClient, CiqualImportError
from mealie.services.recipe.food_composition_service import SOURCES, get_table
from mealie.services.recipe.food_reference_service import invalidate_tables

logger = get_logger()

CIQUAL = "ciqual"
STATUS_IDLE, STATUS_RUNNING, STATUS_SUCCESS, STATUS_ERROR = "idle", "running", "success", "error"
STALE_AFTER = timedelta(hours=1)
"""A refresh still running after this long was interrupted (e.g. by a restart), and can be started again"""


class CiqualRefreshRunning(Exception):
    """A refresh of the Ciqual referential is already running"""


class CiqualRefreshService:
    def __init__(self, repo: RepositoryFoodComposition, client: CiqualDataverseClient | None = None) -> None:
        self.repo = repo
        self.client = client or CiqualDataverseClient()

    def url(self) -> str:
        item = self.repo.get_source(CIQUAL)
        return (item.url if item else None) or DEFAULT_CIQUAL_URL

    def set_url(self, url: str) -> None:
        self.repo.update_source(CIQUAL, url=url.strip())

    def is_running(self) -> bool:
        item = self.repo.get_source(CIQUAL)
        if not item or item.status != STATUS_RUNNING or not item.started_at:
            return False
        started_at = item.started_at.replace(tzinfo=None)
        return get_utc_now().replace(tzinfo=None) - started_at < STALE_AFTER

    def start(self) -> str:
        """Marks the refresh as running and returns the URL to import, unless one is already running"""
        if self.is_running():
            raise CiqualRefreshRunning("The Ciqual referential is already being refreshed")
        url = self.url()
        self.repo.update_source(CIQUAL, url=url, status=STATUS_RUNNING, started_at=get_utc_now(), last_error=None)
        return url

    def run(self, url: str) -> int:
        """Downloads the table and replaces the imported Ciqual foods with it; returns the number of foods"""
        try:
            download = self.client.fetch(url)
            rows = [
                {
                    "code": food.code,
                    "name": food.name[:512],
                    "name_en": food.name_en[:512] or None,
                    "group_code": food.group_code or None,
                    "nutrients": food.nutrients,
                }
                for food in download.foods
            ]
            count = self.repo.replace_imported(CIQUAL, rows)
        except Exception as e:
            message = str(e) if isinstance(e, CiqualImportError) else f"{type(e).__name__}: {e}"
            logger.error(f"Could not refresh the Ciqual referential from {url}: {message}")
            self.repo.session.rollback()
            self.repo.update_source(CIQUAL, status=STATUS_ERROR, last_error=message[:2000])
            return 0
        finally:
            invalidate_tables(CIQUAL)

        version = " - ".join(v for v in (download.version and f"v{download.version}", download.table_version) if v)
        self.repo.update_source(
            CIQUAL,
            status=STATUS_SUCCESS,
            version=version or None,
            release_time=download.release_time,
            imported_at=get_utc_now(),
            food_count=count,
            last_error=None,
        )
        logger.info(f"Imported {count} foods into the Ciqual referential from {url}")
        return count

    def status(self) -> FoodCompositionStatus:
        item = self.repo.get_source(CIQUAL)
        counts = self.repo.counts()
        sources: list[FoodCompositionSourceCount] = []
        for source in (*SOURCES, "off"):
            imported = counts.get((source, ORIGIN_IMPORT), 0)
            bundled = not imported and source in SOURCES
            sources.append(
                FoodCompositionSourceCount(
                    source=source,
                    imported_count=len(get_table(source)) if bundled else imported,  # type: ignore[arg-type]
                    api_count=counts.get((source, ORIGIN_API), 0),
                    bundled=bundled,
                )
            )
        status = item.status if item else STATUS_IDLE
        if status == STATUS_RUNNING and not self.is_running():
            status = STATUS_ERROR
        return FoodCompositionStatus(
            ciqual_url=(item.url if item else None) or DEFAULT_CIQUAL_URL,
            ciqual_default_url=DEFAULT_CIQUAL_URL,
            ciqual_status=status,
            ciqual_version=item.version if item else None,
            ciqual_release_time=item.release_time if item else None,
            ciqual_imported_at=item.imported_at if item else None,
            ciqual_started_at=item.started_at if item else None,
            ciqual_error=item.last_error if item else None,
            sources=sources,
        )


def run_ciqual_refresh(url: str) -> None:
    """The background task of the refresh, with its own database session"""
    with session_context() as session:
        CiqualRefreshService(RepositoryFoodComposition(session)).run(url)
