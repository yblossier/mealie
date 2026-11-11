from pydantic import UUID4

from mealie.repos.repository_factory import RepositoryTools
from mealie.schema.recipe.recipe_organizers import ToolCategory, ToolOut, ToolSave
from mealie.services._base_service import BaseService


class InvalidToolParent(ValueError):
    pass


class ToolService(BaseService):
    """Keeps the accessory links between tools consistent.

    An accessory points at the appliance it can't be used without. Only an appliance that is not
    itself an accessory can be a parent, which keeps the links one level deep and free of cycles.
    """

    def __init__(self, repo: RepositoryTools) -> None:
        self.repo = repo
        super().__init__()

    def validate_parent(self, data: ToolSave, tool_id: UUID4 | None = None) -> None:
        if data.parent_id is None:
            return

        if tool_id is not None and data.parent_id == tool_id:
            raise InvalidToolParent("A tool can't be an accessory of itself")

        parent = self.repo.get_one(data.parent_id)
        if parent is None:
            raise InvalidToolParent("Parent tool not found")
        if parent.category != ToolCategory.appliance or parent.parent_id is not None:
            raise InvalidToolParent("The parent tool must be an appliance that is not itself an accessory")

        if tool_id is not None and self.repo.has_accessories(tool_id):
            raise InvalidToolParent("A tool with accessories can't be an accessory")

    def release_accessories_if_needed(self, tool: ToolOut) -> None:
        """Detaches the accessories of a tool that can no longer be a parent."""
        if tool.category != ToolCategory.appliance or tool.parent_id is not None:
            self.repo.detach_accessories(tool.id)
