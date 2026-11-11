from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from mealie.db.models._model_utils.datetime import get_utc_now
from mealie.db.models.server.food_composition import FoodCompositionFoodModel, FoodCompositionSourceModel

ORIGIN_IMPORT = "import"
ORIGIN_API = "api"

INSERT_BATCH_SIZE = 500


class RepositoryFoodComposition:
    """
    The nutrition referential shared by all the groups (reference data, not scoped to a group or a household): the
    foods of each source and the settings and status of their imports.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    # Foods

    def stamp(self, source: str) -> tuple:
        """Changes whenever the foods of the source change, to know when a cached table is stale"""
        model = FoodCompositionFoodModel
        stmt = (
            select(model.origin, func.count(model.id), func.max(model.id), func.max(model.update_at))
            .where(model.source == source)
            .group_by(model.origin)
            .order_by(model.origin)
        )
        return tuple(tuple(row) for row in self.session.execute(stmt).all())

    def count(self, source: str, origin: str | None = None) -> int:
        model = FoodCompositionFoodModel
        stmt = select(func.count(model.id)).where(model.source == source)
        if origin:
            stmt = stmt.where(model.origin == origin)
        return self.session.execute(stmt).scalar_one()

    def counts(self) -> dict[tuple[str, str], int]:
        """The number of foods of each source and origin"""
        model = FoodCompositionFoodModel
        stmt = select(model.source, model.origin, func.count(model.id)).group_by(model.source, model.origin)
        return {(source, origin): count for source, origin, count in self.session.execute(stmt).all()}

    def get_all(self, source: str, origin: str | None = None) -> Sequence[FoodCompositionFoodModel]:
        model = FoodCompositionFoodModel
        stmt = select(model).where(model.source == source).order_by(model.id)
        if origin:
            stmt = stmt.where(model.origin == origin)
        return self.session.execute(stmt).scalars().all()

    def codes(self, source: str) -> set[str]:
        model = FoodCompositionFoodModel
        return set(self.session.execute(select(model.code).where(model.source == source)).scalars().all())

    def _insert(self, rows: list[dict[str, Any]]) -> None:
        now = get_utc_now()
        for i in range(0, len(rows), INSERT_BATCH_SIZE):
            batch = [{**row, "created_at": now, "update_at": now} for row in rows[i : i + INSERT_BATCH_SIZE]]
            self.session.execute(insert(FoodCompositionFoodModel), batch)

    def add_api_foods(self, source: str, rows: Iterable[dict[str, Any]]) -> int:
        """
        Keeps the foods found through an API that the referential doesn't have yet, never touching the existing ones
        (an imported food is the reference, an API one was already kept). Returns the number of foods added.
        """
        known = self.codes(source)
        new: dict[str, dict[str, Any]] = {}
        for row in rows:
            code = str(row["code"])
            if code and code not in known and code not in new:
                new[code] = {**row, "source": source, "code": code, "origin": ORIGIN_API}
        if not new:
            return 0
        self._insert(list(new.values()))
        self.session.commit()
        return len(new)

    def replace_imported(self, source: str, rows: list[dict[str, Any]]) -> int:
        """
        Replaces the imported foods of the source, in one transaction. The foods kept from an API answer stay, unless
        the import now has a food with their code.
        """
        model = FoodCompositionFoodModel
        codes = [str(row["code"]) for row in rows]
        try:
            self.session.execute(delete(model).where(model.source == source, model.origin == ORIGIN_IMPORT))
            for i in range(0, len(codes), INSERT_BATCH_SIZE):
                self.session.execute(
                    delete(model).where(model.source == source, model.code.in_(codes[i : i + INSERT_BATCH_SIZE]))
                )
            self._insert([{**row, "source": source, "origin": ORIGIN_IMPORT} for row in rows])
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return len(rows)

    # Sources

    def get_source(self, source: str) -> FoodCompositionSourceModel | None:
        model = FoodCompositionSourceModel
        return self.session.execute(select(model).where(model.source == source)).scalars().one_or_none()

    def update_source(self, source: str, **values: Any) -> FoodCompositionSourceModel:
        """Creates or updates the settings and status of the source"""
        item = self.get_source(source)
        if item is None:
            item = FoodCompositionSourceModel(session=self.session, source=source, food_count=0, status="idle")
            self.session.add(item)
        for key, value in values.items():
            setattr(item, key, value)
        self.session.commit()
        self.session.refresh(item)
        return item
