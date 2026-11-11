from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from mealie.db.models._model_base import BaseMixins, SqlAlchemyBase
from mealie.db.models._model_utils.datetime import NaiveDateTime

from .._model_utils.auto_init import auto_init


class FoodCompositionFoodModel(SqlAlchemyBase, BaseMixins):
    """
    A food of the nutrition referential shared by all the groups: imported from a food composition table (Ciqual),
    or found online through an API (Open Food Facts, USDA) and kept to enrich the referential.
    """

    __tablename__ = "food_composition_foods"
    __table_args__ = (
        UniqueConstraint("source", "code", name="food_composition_foods_source_code_key"),
        Index("ix_food_composition_foods_source_name", "source", "name"),
    )

    source: Mapped[str] = mapped_column(String(16), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(512), nullable=True)
    group_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    nutrients: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    average_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "import" for the rows of a composition table, "api" for the ones kept from an API answer
    origin: Mapped[str] = mapped_column(String(16), nullable=False, default="import")

    @auto_init()
    def __init__(self, **_) -> None:
        pass


class FoodCompositionSourceModel(SqlAlchemyBase, BaseMixins):
    """The settings and the last import of a source of the nutrition referential."""

    __tablename__ = "food_composition_sources"

    source: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    release_time: Mapped[str | None] = mapped_column(String(64), nullable=True)
    imported_at: Mapped[datetime | None] = mapped_column(NaiveDateTime, nullable=True)
    food_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # idle, running, success or error
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="idle")
    started_at: Mapped[datetime | None] = mapped_column(NaiveDateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    @auto_init()
    def __init__(self, **_) -> None:
        pass
