from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import Field

from mealie.schema._mealie import MealieModel, MealieOutModel


class ThermomixStep(MealieModel):
    id: UUID = Field(default_factory=uuid4)
    title: str | None = None
    """The title of the section this step starts, as on the recipe steps"""
    summary: str | None = None
    """The title of the step"""
    text: str
    time_seconds: int | None = None
    cooling_seconds: int | None = None
    cooking_seconds: int | None = None
    rest_seconds: int | None = None
    temperature: str | None = None
    speed: str | None = None
    reverse: bool = False
    accessory: str | None = None
    source_step_ids: list[UUID] = []
    tool_ids: list[UUID] = []
    """The recipe tools still used in this step"""
    cautions: list[str] = []
    """Safety warnings about this step, e.g. a hot bowl after cooking"""


class RecipeThermomixView(MealieOutModel):
    """An alternative view of a recipe's steps, adapted for the Thermomix"""

    steps: list[ThermomixStep] = []
    notes: list[str] = []
    model: str | None = None
    created_at: datetime


class ThermomixLogStatus(StrEnum):
    success = "success"
    error = "error"


class ThermomixLogEntry(MealieOutModel):
    """One attempt at generating a recipe's Thermomix view"""

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime
    status: ThermomixLogStatus
    user: str | None = None
    provider: str | None = None
    model: str | None = None
    timeout_seconds: int | None = None
    duration_ms: int = 0
    prompt_chars: int = 0
    """Size of the system prompt, the recipe and the response schema sent to the AI provider"""
    estimated_tokens: int = 0
    """Rough estimate of the input tokens (about 4 characters per token)"""
    request: str = ""
    """The recipe as sent to the AI provider"""
    response: dict | None = None
    """The answer of the AI provider, once parsed"""
    steps_count: int = 0
    error: str | None = None
