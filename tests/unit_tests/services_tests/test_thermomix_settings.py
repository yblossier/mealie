import pytest

from mealie.schema.recipe.recipe_thermomix import ThermomixStep
from mealie.services.recipe.thermomix_settings import complete_step


def step(text: str, **settings) -> ThermomixStep:
    return ThermomixStep(text=text, **settings)


def test_fills_placeholder_settings_from_text():
    completed = complete_step(
        step(
            "Mettre les œufs et le sucre. Mélanger 5 min/30°C/vitesse 3.",
            time_seconds=300,
            temperature="default",
            speed="default",
            accessory="default",
        )
    )

    assert completed.time_seconds == 300
    assert completed.temperature == "30°C"
    assert completed.speed == "3"
    assert completed.reverse is False
    assert completed.accessory is None


def test_reads_reverse_time_and_varoma():
    completed = complete_step(step("Cuire 1 min 30 sec/Varoma/sens inverse/vitesse mijotage."))

    assert completed.time_seconds == 90
    assert completed.temperature == "Varoma"
    assert completed.speed == "mijotage"
    assert completed.reverse is True


@pytest.mark.parametrize(
    "text, speed",
    [
        ("Hacher 5 sec/vitesse 5.", "5"),
        ("Chop 10 sec/speed 7.5.", "7.5"),
        ("Mixer 30 sec/turbo.", "Turbo"),
    ],
)
def test_reads_speed(text: str, speed: str):
    assert complete_step(step(text)).speed == speed


def test_keeps_the_settings_given_by_the_model():
    completed = complete_step(step("Mélanger 5 min/30°C/vitesse 3.", temperature="37°C", speed="2", time_seconds=60))

    assert (completed.temperature, completed.speed, completed.time_seconds) == ("37°C", "2", 60)


def test_ignores_text_without_settings_chain():
    completed = complete_step(step("Laisser reposer 10 min puis cuire au four à 180°C.", speed="default"))

    assert completed.time_seconds is None
    assert completed.temperature is None
    assert completed.speed is None
    assert completed.reverse is False


def test_clears_the_settings_of_an_oven_step():
    completed = complete_step(step("Cuire 45 minutes à 170°C.", temperature="170°C", time_seconds=2700, reverse=True))

    assert (completed.temperature, completed.time_seconds, completed.reverse) == (None, None, False)


def test_ignores_a_temperature_beyond_the_thermomix_range():
    completed = complete_step(step("Mélanger.", temperature="180°C", speed="3"))

    assert completed.temperature is None
    assert completed.speed == "3"
