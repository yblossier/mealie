import shutil
from functools import cached_property
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import UUID4

from mealie.core.dependencies import get_temporary_path
from mealie.pkgs import cache, img
from mealie.routes._base.base_controllers import BaseUserController
from mealie.routes._base.controller import controller
from mealie.routes._base.mixins import HttpRepo
from mealie.routes._base.permissions import Perm, require
from mealie.schema import mapper
from mealie.schema.recipe.recipe_organizers import OrganizerMerge, ToolCreate, ToolOut, ToolPagination, ToolSave
from mealie.schema.recipe.recipe_tool import ToolWithRecipes
from mealie.schema.response.pagination import PaginationQuery
from mealie.services.recipe.tool_service import InvalidToolParent, ToolService

router = APIRouter(prefix="/tools", tags=["Organizer: Tools"])

TOOL_IMAGE_FILE = "original.webp"


def _remove_tool_directory(tool_id: UUID4) -> None:
    shutil.rmtree(ToolOut.get_directory(tool_id), ignore_errors=True)


@controller(router)
class RecipeToolController(BaseUserController):
    @cached_property
    def repo(self):
        return self.repos.tools

    @property
    def mixins(self) -> HttpRepo:
        return HttpRepo[ToolCreate, ToolOut, ToolCreate](self.repo, self.logger)

    @cached_property
    def service(self) -> ToolService:
        return ToolService(self.repo)

    def _validate_parent(self, data: ToolSave, item_id: UUID4 | None = None) -> None:
        try:
            self.service.validate_parent(data, item_id)
        except InvalidToolParent as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

    @router.get("", response_model=ToolPagination)
    def get_all(self, q: PaginationQuery = Depends(PaginationQuery), search: str | None = None):
        response = self.repo.page_all(
            pagination=q,
            override=ToolOut,
            search=search,
        )

        response.set_pagination_guides(router.url_path_for("get_all"), q.model_dump())
        return response

    @router.post("", response_model=ToolOut, status_code=201, dependencies=[require(Perm.GROUP_ORGANIZE)])
    def create_one(self, data: ToolCreate):
        save_data = mapper.cast(data, ToolSave, group_id=self.group_id)
        self._validate_parent(save_data)
        return self.mixins.create_one(save_data)

    @router.get("/empty", response_model=list[ToolOut])
    def get_all_empty(self):
        """Returns a list of tools that are not used by any recipe"""
        return self.repo.get_empty()

    @router.post("/merge", response_model=ToolOut, dependencies=[require(Perm.GROUP_ORGANIZE)])
    def merge_tools(self, body: OrganizerMerge):
        """Merges the from_id tool into the to_id tool, then deletes from_id."""
        if body.from_id == body.to_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "from_id and to_id must be different")

        if not self.repo.get_one(body.from_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "from_id tool not found")
        if not self.repo.get_one(body.to_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "to_id tool not found")

        merged = self.repo.merge(body.from_id, body.to_id)
        _remove_tool_directory(body.from_id)
        return merged

    @router.get("/{item_id}", response_model=ToolOut)
    def get_one(self, item_id: UUID4):
        return self.mixins.get_one(item_id)

    @router.put("/{item_id}", response_model=ToolOut, dependencies=[require(Perm.GROUP_ORGANIZE)])
    def update_one(self, item_id: UUID4, data: ToolCreate):
        save_data = mapper.cast(data, ToolSave, group_id=self.group_id)
        self._validate_parent(save_data, item_id)
        updated = self.mixins.update_one(save_data, item_id)
        self.service.release_accessories_if_needed(updated)
        return updated

    @router.delete("/{item_id}", response_model=ToolOut, dependencies=[require(Perm.GROUP_ORGANIZE)])
    def delete_one(self, item_id: UUID4):
        deleted = self.mixins.delete_one(item_id)  # type: ignore
        _remove_tool_directory(item_id)
        return deleted

    @router.put("/{item_id}/image", response_model=ToolOut, dependencies=[require(Perm.GROUP_ORGANIZE)])
    def update_image(self, item_id: UUID4, image: UploadFile = File(...)):
        """Sets the photo of a tool, stored as webp."""
        self.mixins.get_one(item_id)

        with get_temporary_path() as temp_path:
            # the file name is generated so the user input never reaches the file system
            temp_img = temp_path.joinpath(str(uuid4()))
            with temp_img.open("wb") as buffer:
                shutil.copyfileobj(image.file, buffer)

            try:
                webp = img.PillowMinifier.to_webp(temp_img)
            except Exception as e:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid image") from e

            tool_dir = ToolOut.get_directory(item_id)
            tool_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(webp, tool_dir / TOOL_IMAGE_FILE)

        return self.repo.patch(item_id, {"image": cache.new_key()})

    @router.delete("/{item_id}/image", response_model=ToolOut, dependencies=[require(Perm.GROUP_ORGANIZE)])
    def delete_image(self, item_id: UUID4):
        """Removes the photo of a tool."""
        self.mixins.get_one(item_id)
        _remove_tool_directory(item_id)
        return self.repo.patch(item_id, {"image": None})

    @router.get("/slug/{tool_slug}", response_model=ToolWithRecipes)
    def get_one_by_slug(self, tool_slug: str):
        return self.repo.get_one(tool_slug, "slug", override_schema=ToolWithRecipes)
