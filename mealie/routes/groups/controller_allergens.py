from functools import cached_property

from fastapi import APIRouter, Depends
from pydantic import UUID4

from mealie.routes._base.base_controllers import BaseCrudController
from mealie.routes._base.controller import controller
from mealie.routes._base.mixins import HttpRepo
from mealie.routes._base.permissions import Perm, require
from mealie.routes._base.routers import MealieCrudRoute
from mealie.schema.allergens.allergen import (
    AllergenCreate,
    AllergenOut,
    AllergenPagination,
    AllergenSave,
    AllergenUpdate,
)
from mealie.schema.response.pagination import PaginationQuery

router = APIRouter(prefix="/groups/allergens", tags=["Groups: Allergens"], route_class=MealieCrudRoute)


@controller(router)
class AllergensController(BaseCrudController):
    @cached_property
    def repo(self):
        return self.repos.group_allergens

    @property
    def mixins(self) -> HttpRepo:
        return HttpRepo(self.repo, self.logger, self.registered_exceptions, self.t("generic.server-error"))

    @router.get("", response_model=AllergenPagination)
    def get_all(self, q: PaginationQuery = Depends(PaginationQuery), search: str | None = None):
        response = self.repo.page_all(pagination=q, override=AllergenOut, search=search)
        response.set_pagination_guides(router.url_path_for("get_all"), q.model_dump())
        return response

    @router.post("", response_model=AllergenOut, status_code=201, dependencies=[require(Perm.GROUP_ORGANIZE)])
    def create_one(self, data: AllergenCreate):
        save = AllergenSave(**data.model_dump(), group_id=self.group_id)
        return self.mixins.create_one(save)

    @router.get("/{item_id}", response_model=AllergenOut)
    def get_one(self, item_id: UUID4):
        return self.mixins.get_one(item_id)

    @router.put("/{item_id}", response_model=AllergenOut, dependencies=[require(Perm.GROUP_ORGANIZE)])
    def update_one(self, item_id: UUID4, data: AllergenUpdate):
        return self.mixins.update_one(data, item_id)

    @router.delete("/{item_id}", response_model=AllergenOut, dependencies=[require(Perm.GROUP_ORGANIZE)])
    def delete_one(self, item_id: UUID4):
        return self.mixins.delete_one(item_id)
