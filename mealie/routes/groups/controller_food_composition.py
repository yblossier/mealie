from functools import cached_property

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from mealie.routes._base.base_controllers import BaseUserController
from mealie.routes._base.controller import controller
from mealie.routes._base.permissions import Perm, require
from mealie.schema.group.group_food_composition import FoodCompositionCiqualUpdate, FoodCompositionStatus
from mealie.services.recipe.ciqual_refresh_service import (
    CiqualRefreshRunning,
    CiqualRefreshService,
    run_ciqual_refresh,
)

router = APIRouter(prefix="/groups/food-composition", tags=["Groups: Food Composition"])


@controller(router)
class FoodCompositionController(BaseUserController):
    """The nutrition referential shared by all the groups, and the import of the Ciqual table"""

    @cached_property
    def service(self) -> CiqualRefreshService:
        return CiqualRefreshService(self.repos.food_composition)

    @router.get("", response_model=FoodCompositionStatus)
    def get_status(self):
        return self.service.status()

    @router.put("/ciqual", response_model=FoodCompositionStatus, dependencies=[require(Perm.GROUP_MANAGE)])
    def update_ciqual(self, data: FoodCompositionCiqualUpdate):
        self.service.set_url(data.url)
        return self.service.status()

    @router.post(
        "/ciqual/refresh",
        response_model=FoodCompositionStatus,
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=[require(Perm.GROUP_MANAGE)],
    )
    def refresh_ciqual(self, background_tasks: BackgroundTasks):
        """Starts importing the latest Ciqual table published at the configured URL into the referential"""
        try:
            url = self.service.start()
        except CiqualRefreshRunning as e:
            raise HTTPException(status.HTTP_409_CONFLICT, detail=str(e)) from e
        background_tasks.add_task(run_ciqual_refresh, url)
        return self.service.status()
