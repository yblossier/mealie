import asyncio

import pytest
from pydantic import UUID4

from mealie.db.db_setup import session_context
from mealie.lang.providers import get_locale_provider
from mealie.repos.repository_factory import AllRepositories
from mealie.schema.recipe.recipe_ingredient import (
    IngredientFoodOut,
    IngredientFoodSave,
    IngredientUnitAliasCreate,
    IngredientUnitOut,
    IngredientUnitSave,
)
from mealie.services.parser_services import RegisteredParser, get_parser
from mealie.services.parser_services.parser_utils.french import (
    is_french_ingredient,
    parse_french_ingredient,
    singular_candidates,
)

# input, quantity, unit (canonical French name), food, note
FRENCH_LINES: list[tuple[str, float, str, str, str]] = [
    ("2 c. à soupe d'huile d'olive", 2, "cuillère à soupe", "huile d'olive", ""),
    ("200 g de farine", 200, "gramme", "farine", ""),
    ("1 pincée de sel", 1, "pincée", "sel", ""),
    ("3 gousses d'ail hachées", 3, "gousse", "ail", "hachées"),
    ("½ cuillère à café de sel", 0.5, "cuillère à café", "sel", ""),
    ("1 boîte de tomates concassées (400 g)", 1, "boîte", "tomates concassées", "400 g"),
    ("sel, poivre", 0, "", "sel", "poivre"),
    ("2 œufs", 2, "", "œufs", ""),
    ("1 l de lait", 1, "litre", "lait", ""),
    ("10 cl de crème liquide", 10, "centilitre", "crème liquide", ""),
    ("1 sachet de levure chimique", 1, "sachet", "levure chimique", ""),
    ("quelques feuilles de basilic", 0, "feuille", "basilic", "quelques"),
    ("1,5 kg de pommes de terre", 1.5, "kilogramme", "pommes de terre", ""),
    ("un oignon émincé", 1, "", "oignon", "émincé"),
    ("2 à 3 càs de sucre", 2, "cuillère à soupe", "sucre", "2 à 3"),
    ("200g de beurre fondu, pour le moule", 200, "gramme", "beurre", "fondu, pour le moule"),
    ("1 cuillère à soupe rase de sucre", 1, "cuillère à soupe", "sucre", "rase"),
    ("Sel et poivre au goût", 0, "", "Sel", "poivre, au goût"),
    ("1 gros oignon", 1, "", "oignon", "gros"),
    ("1 noix de beurre", 1, "noix", "beurre", ""),
    ("100 g de noix", 100, "gramme", "noix", ""),
    ("2 x 400 g de pois chiches", 800, "gramme", "pois chiches", ""),
    ("1 kg et demi de pommes", 1.5, "kilogramme", "pommes", ""),
    ("1 c.à.c de cannelle", 1, "cuillère à café", "cannelle", ""),
    ("3 cs de sauce soja", 3, "cuillère à soupe", "sauce soja", ""),
    ("1 cc de curry", 1, "cuillère à café", "curry", ""),
    ("25 cl de vin blanc sec", 25, "centilitre", "vin blanc sec", ""),
    ("1/2 citron", 0.5, "", "citron", ""),
    ("1 1/2 tasse de riz", 1.5, "tasse", "riz", ""),
    ("2 tranches de jambon", 2, "tranche", "jambon", ""),
    ("1 brin de thym", 1, "brin", "thym", ""),
    ("1 botte de radis", 1, "botte", "radis", ""),
    ("1 verre de vin rouge", 1, "verre", "vin rouge", ""),
    ("1 poignée de roquette", 1, "poignée", "roquette", ""),
    ("deux échalotes ciselées", 2, "", "échalotes", "ciselées"),
    ("1 bouquet de persil plat", 1, "bouquet", "persil plat", ""),
    ("500 ml de bouillon de volaille", 500, "millilitre", "bouillon de volaille", ""),
    ("1 morceau de gingembre frais", 1, "morceau", "gingembre", "frais"),
    ("150 gr de chocolat noir", 150, "gramme", "chocolat noir", ""),
    ("1 dl d'eau tiède", 1, "décilitre", "eau", "tiède"),
    ("2 carottes coupées en dés", 2, "", "carottes", "coupées en dés"),
    ("100 g de parmesan râpé", 100, "gramme", "parmesan râpé", ""),
    ("20 cl de crème fraîche", 20, "centilitre", "crème fraîche", ""),
    ("1 pot de yaourt nature", 1, "pot", "yaourt nature", ""),
    ("sel QS", 0, "", "sel", "QS"),
    ("poivre à volonté", 0, "", "poivre", "à volonté"),
    ("1 paquet de pâte feuilletée", 1, "paquet", "pâte feuilletée", ""),
    ("beurre pour le moule", 0, "", "beurre", "pour le moule"),
    ("1 zeste de citron", 1, "zeste", "citron", ""),
    ("4 pommes de terre moyennes, épluchées", 4, "", "pommes de terre", "moyennes, épluchées"),
    ("2 filets de poulet", 2, "filet", "poulet", ""),
    ("1 c. à s. de miel", 1, "cuillère à soupe", "miel", ""),
    ("une demi-cuillère à café de piment", 0.5, "cuillère à café", "piment", ""),
    ("environ 300 g de lardons", 300, "gramme", "lardons", "environ"),
    ("1 kg de pommes de terre (type Charlotte)", 1, "kilogramme", "pommes de terre", "type Charlotte"),
]


@pytest.mark.parametrize(("text", "quantity", "unit", "food", "note"), FRENCH_LINES)
def test_parse_french_ingredient(text: str, quantity: float, unit: str, food: str, note: str):
    parsed = parse_french_ingredient(text)

    assert parsed.quantity == pytest.approx(quantity)
    assert (parsed.unit.name if parsed.unit else "") == unit
    assert parsed.food == food
    assert parsed.note == note


@pytest.mark.parametrize(("text", "_q", "_u", "_f", "_n"), FRENCH_LINES)
def test_french_lines_are_detected(text: str, _q, _u, _f, _n):
    assert is_french_ingredient(text)


@pytest.mark.parametrize(
    "text",
    [
        "½ cup all-purpose flour",
        "1 ½ teaspoons ground black pepper",
        "2 pounds russet potatoes, peeled, and cut into 3/4-inch cubes",
        "2 teaspoons salt (to taste)",
        "1/2 cup",
        "1 cup crème fraîche",
        "2 cups chicken broth or beef broth",
        "153 grams 00 flour (1 cup plus 1 tablespoon)",
        "2 tablespoons (30ml) vegetable oil",
        "3 cloves garlic, minced",
    ],
)
def test_english_lines_are_not_detected_as_french(text: str):
    assert not is_french_ingredient(text)
    assert not is_french_ingredient(text, "fr-FR")


def test_locale_breaks_ties():
    assert not is_french_ingredient("200 g")
    assert is_french_ingredient("200 g", "fr-FR")
    assert is_french_ingredient("200 g", "fr-CA")


def test_alternatives():
    parsed = parse_french_ingredient("50 g de beurre ou de margarine")
    assert parsed.food == "beurre"
    assert parsed.alternatives == ["margarine"]


def test_singular_candidates():
    assert "pomme de terre" in singular_candidates("pommes de terre")
    assert "oeuf" in singular_candidates("oeufs")
    assert singular_candidates("noix") == []


@pytest.fixture()
def french_data(unique_db: AllRepositories, unique_local_group_id: UUID4):
    foods = unique_db.ingredient_foods.create_many(
        [
            IngredientFoodSave(name="huile d'olive", group_id=unique_local_group_id),
            IngredientFoodSave(name="farine", group_id=unique_local_group_id),
            IngredientFoodSave(name="ail", group_id=unique_local_group_id),
            IngredientFoodSave(name="œuf", plural_name="œufs", group_id=unique_local_group_id),
            IngredientFoodSave(name="pomme de terre", group_id=unique_local_group_id),
            IngredientFoodSave(name="tomates concassées", group_id=unique_local_group_id),
            IngredientFoodSave(name="tomate", group_id=unique_local_group_id),
            IngredientFoodSave(name="oignon", group_id=unique_local_group_id),
            IngredientFoodSave(name="margarine", group_id=unique_local_group_id),
            IngredientFoodSave(name="beurre", group_id=unique_local_group_id),
        ]
    )
    units = unique_db.ingredient_units.create_many(
        [
            IngredientUnitSave(
                name="cuillère à soupe",
                plural_name="cuillères à soupe",
                abbreviation="càs",
                group_id=unique_local_group_id,
            ),
            IngredientUnitSave(name="gramme", plural_name="grammes", abbreviation="g", group_id=unique_local_group_id),
            IngredientUnitSave(name="clove", group_id=unique_local_group_id),
            IngredientUnitSave(name="kilogram", abbreviation="kg", group_id=unique_local_group_id),
            IngredientUnitSave(
                name="can", group_id=unique_local_group_id, aliases=[IngredientUnitAliasCreate(name="boîte")]
            ),
            IngredientUnitSave(name="botte", group_id=unique_local_group_id),
        ]
    )
    return {f.name: f for f in foods}, {u.name: u for u in units}


@pytest.mark.parametrize("parser_type", [RegisteredParser.nlp, RegisteredParser.brute])
@pytest.mark.parametrize(
    ("text", "quantity", "unit", "food", "note"),
    [
        ("2 c. à soupe d'huile d'olive", 2, "cuillère à soupe", "huile d'olive", ""),
        ("200 g de farine", 200, "gramme", "farine", ""),
        ("3 gousses d'ail hachées", 3, "clove", "ail", "hachées"),
        ("2 œufs", 2, "", "œuf", ""),
        ("1,5 kg de pommes de terre", 1.5, "kilogram", "pomme de terre", ""),
        ("1 boîte de tomates concassées (400 g)", 1, "can", "tomates concassées", "400 g"),
        ("un oignon émincé", 1, "", "oignon", "émincé"),
    ],
)
def test_french_parser_matches_database(
    unique_local_group_id: UUID4,
    french_data: tuple[dict[str, IngredientFoodOut], dict[str, IngredientUnitOut]],
    parser_type: RegisteredParser,
    text: str,
    quantity: float,
    unit: str,
    food: str,
    note: str,
):
    with session_context() as session:
        parser = get_parser(parser_type, unique_local_group_id, session, get_locale_provider())
        parsed = asyncio.run(parser.parse_one(text))

    ing = parsed.ingredient
    assert ing.original_text == text
    assert ing.quantity == pytest.approx(quantity)
    if unit:
        assert isinstance(ing.unit, IngredientUnitOut)
        assert ing.unit.name == unit
    else:
        assert ing.unit is None
    assert isinstance(ing.food, IngredientFoodOut)
    assert ing.food.name == food
    assert (ing.note or "") == note
    assert parsed.confidence.food == 1
    assert parsed.confidence.average and parsed.confidence.average > 0.9


def test_french_parser_unknown_unit_does_not_fuzzy_match(
    unique_local_group_id: UUID4, french_data: tuple[dict[str, IngredientFoodOut], dict[str, IngredientUnitOut]]
):
    with session_context() as session:
        parser = get_parser(RegisteredParser.nlp, unique_local_group_id, session, get_locale_provider())
        parsed = asyncio.run(parser.parse_one("1 sachet de levure chimique"))

    ing = parsed.ingredient
    assert ing.unit is not None and ing.unit.name == "sachet"
    assert not isinstance(ing.unit, IngredientUnitOut)
    assert ing.food is not None and ing.food.name == "levure chimique"
    assert parsed.confidence.food == pytest.approx(0.75)


def test_french_parser_alternatives_become_substitutions(
    unique_local_group_id: UUID4, french_data: tuple[dict[str, IngredientFoodOut], dict[str, IngredientUnitOut]]
):
    foods, _ = french_data
    with session_context() as session:
        parser = get_parser(RegisteredParser.nlp, unique_local_group_id, session, get_locale_provider())
        parsed = asyncio.run(parser.parse_one("50 g de beurre ou margarine"))

    ing = parsed.ingredient
    assert ing.food is not None and ing.food.name == "beurre"
    assert [s.substitute_food_id for s in ing.substitutions] == [foods["margarine"].id]
