"""
Completes the settings of a Thermomix step from its text.

Small models often write the settings in the text ("Mix 5 min/30°C/speed 3.") but fill the
structured fields with placeholders such as "default". The settings chain in the text is then
the source of truth for the fields that are missing.
"""

import re

from mealie.schema.recipe.recipe_thermomix import ThermomixStep

# the TM6 and TM7 heat up to 160°C
MAX_TEMPERATURE = 160
PLACEHOLDERS = {"", "default", "défaut", "par défaut", "none", "null", "n/a", "na", "-", "aucun", "aucune", "empty"}

_TIME = r"\d+\s*(?:h|min|sec|s)\b(?:\s*\d+\s*(?:min|sec|s)\b)?"
_TEMPERATURE = r"(?:\d{2,3}\s*°\s*C?|varoma)"
_SPEED = (
    r"(?:(?:vitesse|speed|stufe|velocidad|velocità|vel\.?)\s*"
    r"(?:\d+(?:[.,]\d+)?|mijotage|cuill[eè]re|spoon|turbo)|turbo)"
)
_REVERSE = r"(?:sens\s+inverse|reverse|linkslauf|giro\s+(?:a\s+la\s+)?izquierda|antiorario)"
_TOKEN = f"(?:{_TIME}|{_TEMPERATURE}|{_SPEED}|{_REVERSE})"
_CHAIN = re.compile(rf"{_TOKEN}(?:\s*/\s*{_TOKEN})+", re.IGNORECASE)
_TIME_PART = re.compile(r"(\d+)\s*(h|min|sec|s)\b", re.IGNORECASE)


def _is_missing(value: str | None) -> bool:
    return value is None or value.strip().lower() in PLACEHOLDERS


def _clean(value: str | None) -> str | None:
    if value is None or _is_missing(value):
        return None
    return value.strip()


def _seconds(token: str) -> int:
    factors = {"h": 3600, "min": 60, "sec": 1, "s": 1}
    return sum(int(amount) * factors[unit.lower()] for amount, unit in _TIME_PART.findall(token))


def _parse(text: str) -> dict:
    settings: dict = {}
    for chain in _CHAIN.finditer(text):
        for token in (part.strip() for part in chain.group(0).split("/")):
            if re.fullmatch(_REVERSE, token, re.IGNORECASE):
                settings["reverse"] = True
            elif re.fullmatch(_TEMPERATURE, token, re.IGNORECASE):
                degrees = re.match(r"\d+", token)
                settings.setdefault("temperature", f"{degrees.group(0)}°C" if degrees else "Varoma")
            elif re.fullmatch(_TIME, token, re.IGNORECASE):
                settings.setdefault("time_seconds", _seconds(token))
            elif re.fullmatch(_SPEED, token, re.IGNORECASE):
                value = re.sub(r"^(?:vitesse|speed|stufe|velocidad|velocità|vel\.?)\s*", "", token, flags=re.IGNORECASE)
                settings.setdefault("speed", "Turbo" if value.lower() == "turbo" else value)
    return settings


def _within_thermomix_range(temperature: str | None) -> bool:
    degrees = re.match(r"\d+", temperature or "")
    return not degrees or int(degrees.group(0)) <= MAX_TEMPERATURE


def complete_step(step: ThermomixStep) -> ThermomixStep:
    """Replaces placeholder settings and fills the missing ones from the step's text"""
    parsed = _parse(step.text)
    temperature = _clean(step.temperature) or parsed.get("temperature")
    speed = _clean(step.speed) or parsed.get("speed")
    time_seconds = step.time_seconds if step.time_seconds and step.time_seconds > 0 else parsed.get("time_seconds")
    reverse = bool(step.reverse or parsed.get("reverse"))

    # the bowl always turns when the Thermomix runs: a step without a speed nor settings in its text
    # is done by hand or in the oven, and its time or temperature are not Thermomix settings
    if not speed and not parsed:
        temperature, time_seconds, reverse = None, None, False
    if not _within_thermomix_range(temperature):
        temperature = None

    return step.model_copy(
        update={
            "temperature": temperature,
            "speed": speed,
            "time_seconds": time_seconds or None,
            "reverse": reverse,
            "accessory": _clean(step.accessory),
        }
    )
