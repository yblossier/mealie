from fastapi import APIRouter, HTTPException, status
from pydantic import UUID4
from starlette.responses import FileResponse

from mealie.routes._base.permissions import not_found
from mealie.schema.recipe.recipe_organizers import ToolOut

router = APIRouter(prefix="/tools")


@router.get("/{tool_id}/{file_name}", response_class=FileResponse)
async def get_tool_image(tool_id: UUID4, file_name: str):
    """Returns the photo of a tool."""
    tool_dir = ToolOut.get_directory(tool_id).resolve()
    image = (tool_dir / file_name).resolve()

    if not image.is_relative_to(tool_dir):
        raise HTTPException(status.HTTP_400_BAD_REQUEST)

    if image.is_file():
        return FileResponse(image, media_type="image/webp")

    raise not_found()
