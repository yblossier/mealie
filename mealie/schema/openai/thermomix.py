from pydantic import Field

from ._base import OpenAIBase


class OpenAIThermomixStep(OpenAIBase):
    title: str | None = Field(
        None,
        description="A short title of this step in French, used when the original step has no title.",
    )
    text: str = Field(
        ...,
        description="One step written in French for the Thermomix, e.g. 'Ajouter l'oignon et hacher 5 sec/Vitesse 5.'",
    )
    time_seconds: int | None = Field(None, description="The time set on the Thermomix for this step, in seconds.")
    cooking_seconds: int | None = Field(
        None,
        description="The cooking time outside the Thermomix, e.g. in the oven, in seconds. Empty when there is none.",
    )
    rest_seconds: int | None = Field(
        None, description="The resting time of this step, e.g. a dough rising, in seconds. Empty when there is none."
    )
    cooling_seconds: int | None = Field(
        None,
        description=(
            "The cooling or chilling time of this step, e.g. in the fridge, in seconds. Empty when there is none."
        ),
    )
    temperature: str | None = Field(
        None,
        description=(
            "The temperature set on the Thermomix, e.g. '100°C' or 'Varoma', as written in the text. "
            "Empty without heating, never 'default'."
        ),
    )
    speed: str | None = Field(
        None,
        description=(
            "The speed set on the Thermomix, e.g. '1', '5', 'mijotage' or 'Turbo', as written in the text. "
            "Empty without mixing, never 'default'."
        ),
    )
    reverse: bool | None = Field(None, description="Whether the blade turns in reverse to stir without chopping.")
    accessory: str | None = Field(
        None,
        description=(
            "The Thermomix accessory used in this step, in French, e.g. 'fouet', 'panier de cuisson', "
            "or the classic utensil of a step done by hand, e.g. 'économe', 'four'."
        ),
    )
    source_steps: list[int] = Field(
        [],
        description=(
            "The numbers, starting at 1, of the original steps this step comes from. "
            "The section and the title of the step are taken from them."
        ),
    )
    tools: list[str] = Field(
        [],
        description=(
            "The names, exactly as in the recipe tools, of the tools still used in this step, "
            "e.g. the cake tin or the oven. Leave out the tools the Thermomix replaces."
        ),
    )
    cautions: list[str] = Field(
        [],
        description=(
            "Short safety warnings in French about a real risk in this very step, e.g. "
            "'Attention, le bol et le couvercle sont très chauds : utiliser des maniques.' "
            "Empty when the step has no specific risk."
        ),
    )


class OpenAIThermomixView(OpenAIBase):
    steps: list[OpenAIThermomixStep] = Field([], description="The steps of the recipe adapted for the Thermomix.")
    notes: list[str] = Field(
        [],
        description=(
            "Expert Thermomix tricks in French that really improve this recipe, never common sense "
            "or safety warnings. Empty when there is no such trick."
        ),
    )
