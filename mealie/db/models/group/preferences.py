from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Mapped, mapped_column

from .._model_base import BaseMixins, SqlAlchemyBase
from .._model_utils.auto_init import auto_init
from .._model_utils.guid import GUID

if TYPE_CHECKING:
    from .group import Group


class GroupPreferencesModel(SqlAlchemyBase, BaseMixins):
    __tablename__ = "group_preferences"
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)

    group_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("groups.id"), nullable=False, index=True)
    group: Mapped[Group | None] = orm.relationship("Group", back_populates="preferences")

    private_group: Mapped[bool | None] = mapped_column(sa.Boolean, default=True)
    show_announcements: Mapped[bool] = mapped_column(sa.Boolean, default=True)

    # Configuration tables and tool suppliers
    default_table_page_size: Mapped[int] = mapped_column(sa.Integer, default=15, server_default="15")
    tool_suppliers: Mapped[list | None] = mapped_column(sa.JSON, default=None)
    show_tool_supplier_links: Mapped[bool] = mapped_column(sa.Boolean, default=True, server_default=sa.true())

    # Nutrition APIs
    off_mode: Mapped[str] = mapped_column(sa.String, default="prod", server_default="prod")
    off_app_name: Mapped[str | None] = mapped_column(sa.String, default=None)
    off_app_version: Mapped[str | None] = mapped_column(sa.String, default=None)
    off_app_uuid: Mapped[str | None] = mapped_column(sa.String, default=None)
    usda_api_enabled: Mapped[bool] = mapped_column(sa.Boolean, default=True, server_default=sa.true())
    usda_api_key: Mapped[str | None] = mapped_column(sa.String, default=None)

    # Deprecated (see household preferences)
    first_day_of_week: Mapped[int | None] = mapped_column(sa.Integer, default=0)
    recipe_public: Mapped[bool | None] = mapped_column(sa.Boolean, default=True)
    recipe_show_nutrition: Mapped[bool | None] = mapped_column(sa.Boolean, default=False)
    recipe_show_assets: Mapped[bool | None] = mapped_column(sa.Boolean, default=False)
    recipe_landscape_view: Mapped[bool | None] = mapped_column(sa.Boolean, default=False)
    recipe_disable_comments: Mapped[bool | None] = mapped_column(sa.Boolean, default=False)
    recipe_disable_amount: Mapped[bool | None] = mapped_column(sa.Boolean, default=True)

    @auto_init()
    def __init__(self, **_) -> None:
        pass
