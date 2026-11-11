"""
Rule-based French ingredient parsing.

The CRF model shipped with `ingredient-parser-nlp` is trained on English sentences only, so French
lines ("2 c. à soupe d'huile d'olive") come out mangled. This module detects French ingredient lines
and splits them into quantity, unit, food and note with French-specific rules. It has no database
access: matching the result against the group's units and foods is done by the caller.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from fractions import Fraction

from text_unidecode import unidecode

from .string_utils import convert_vulgar_fractions_to_regular_fractions, remove_footnote_markers

_ACCENT_CLASSES = {
    "a": "[aàâä]",
    "c": "[cç]",
    "e": "[eéèêë]",
    "i": "[iîï]",
    "o": "[oôö]",
    "u": "[uùûü]",
}


def _fold(pattern: str) -> str:
    """Makes an ASCII regex accent-insensitive, e.g. "pincee" also matches "pincée"."""
    return "".join(_ACCENT_CLASSES.get(char, char) for char in pattern)


def fold_text(text: str) -> str:
    """Lowercase, accent-free version of a text, used for lookups."""
    return unidecode(text).lower().strip()


@dataclass(frozen=True)
class FrenchUnit:
    key: str
    name: str
    plural_name: str
    abbreviation: str = ""
    patterns: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    """Other names the unit may be stored under in the database (English names, other spellings)"""
    requires_connector: bool = False
    """The word is also a food ("noix"), so it is only a unit when followed by "de"/"d'"."""

    @property
    def match_candidates(self) -> list[str]:
        candidates = [self.name, self.plural_name, self.abbreviation, *self.aliases]
        return [c for c in candidates if c]


_SPOON = r"cuiller(?:ee?)?s?"

FRENCH_UNITS: tuple[FrenchUnit, ...] = (
    FrenchUnit(
        "tablespoon",
        "cuillère à soupe",
        "cuillères à soupe",
        "c. à s.",
        (
            _SPOON + r"\s+a\s+(?:soupe|table|s\.?)",
            r"cuil\.?\s*a\s*s(?:oupe)?\.?",
            r"c\.?\s*a\.?\s*s(?:oupe)?\.?",
            r"c/s",
            r"cs",
        ),
        ("càs", "cas", "cs", "cuillerée à soupe", "tablespoon", "tablespoons", "tbsp", "tbs"),
    ),
    FrenchUnit(
        "teaspoon",
        "cuillère à café",
        "cuillères à café",
        "c. à c.",
        (
            _SPOON + r"\s+a\s+(?:cafe|the|c\.?)",
            r"cuil\.?\s*a\s*c(?:afe)?\.?",
            r"c\.?\s*a\.?\s*c(?:afe)?\.?",
            r"c/c",
            r"cc",
        ),
        ("càc", "cac", "cc", "cuillerée à café", "teaspoon", "teaspoons", "tsp"),
    ),
    FrenchUnit(
        "dessertspoon",
        "cuillère à dessert",
        "cuillères à dessert",
        "",
        (_SPOON + r"\s+a\s+dessert",),
        ("dessertspoon",),
    ),
    FrenchUnit("spoon", "cuillère", "cuillères", "", (_SPOON,), ("spoon",)),
    FrenchUnit("kilogram", "kilogramme", "kilogrammes", "kg", (r"kilogrammes?", r"kilos?", r"kgs?"), ("kilogram",)),
    FrenchUnit("milligram", "milligramme", "milligrammes", "mg", (r"milligrammes?", r"mg"), ("milligram",)),
    FrenchUnit("gram", "gramme", "grammes", "g", (r"grammes?", r"grs?\.?", r"g\.?"), ("gram", "grams", "gr")),
    FrenchUnit("deciliter", "décilitre", "décilitres", "dl", (r"decilitres?", r"dl"), ("deciliter",)),
    FrenchUnit("centiliter", "centilitre", "centilitres", "cl", (r"centilitres?", r"cl"), ("centiliter",)),
    FrenchUnit("milliliter", "millilitre", "millilitres", "ml", (r"millilitres?", r"ml"), ("milliliter",)),
    FrenchUnit("liter", "litre", "litres", "l", (r"litres?", r"l"), ("liter", "liters")),
    FrenchUnit("pinch", "pincée", "pincées", "", (r"pincees?",), ("pinch",)),
    FrenchUnit("handful", "poignée", "poignées", "", (r"poignees?",), ("handful",)),
    FrenchUnit("clove", "gousse", "gousses", "", (r"gousses?",), ("clove", "cloves")),
    FrenchUnit("slice", "tranche", "tranches", "", (r"tranches?",), ("slice",)),
    FrenchUnit("can", "boîte", "boîtes", "", (r"boites?",), ("can", "tin")),
    FrenchUnit("sachet", "sachet", "sachets", "", (r"sachets?",), ("packet", "sachet")),
    FrenchUnit("sprig", "brin", "brins", "", (r"brins?",), ("sprig",)),
    FrenchUnit("bunch", "botte", "bottes", "", (r"bottes?",), ("bunch",)),
    FrenchUnit("bouquet", "bouquet", "bouquets", "", (r"bouquets?",), ("bouquet",)),
    FrenchUnit("glass", "verre", "verres", "", (r"verres?",), ("glass",)),
    FrenchUnit("cup", "tasse", "tasses", "", (r"tasses?",), ("cup", "cups")),
    FrenchUnit("bowl", "bol", "bols", "", (r"bols?",), ("bowl",)),
    FrenchUnit("knob", "noix", "noix", "", (r"noix",), ("knob",), True),
    FrenchUnit("hazelnut-sized", "noisette", "noisettes", "", (r"noisettes?",), (), True),
    FrenchUnit("leaf", "feuille", "feuilles", "", (r"feuilles?",), ("leaf", "leaves")),
    FrenchUnit("fillet", "filet", "filets", "", (r"filets?",), ("fillet", "drizzle"), True),
    FrenchUnit("zest", "zeste", "zestes", "", (r"zestes?",), ("zest",), True),
    FrenchUnit("pot", "pot", "pots", "", (r"pots?",), ("pot", "jar")),
    FrenchUnit("pack", "paquet", "paquets", "", (r"paquets?",), ("pack", "package")),
    FrenchUnit("piece", "morceau", "morceaux", "", (r"morceaux?", r"pieces?"), ("piece",)),
    FrenchUnit("tip", "pointe", "pointes", "", (r"pointes?",), (), True),
    FrenchUnit("cube", "cube", "cubes", "", (r"cubes?",), ("cube",), True),
    FrenchUnit("tray", "barquette", "barquettes", "", (r"barquettes?",), ("tray", "punnet")),
    FrenchUnit("jar", "bocal", "bocaux", "", (r"bocal", r"bocaux"), ("jar",)),
    FrenchUnit("roll", "rouleau", "rouleaux", "", (r"rouleaux?",), ("roll",)),
    FrenchUnit("bar", "tablette", "tablettes", "", (r"tablettes?",), ("bar",)),
    FrenchUnit("square", "carré", "carrés", "", (r"carres?",), ("square",), True),
    FrenchUnit("strip", "lamelle", "lamelles", "", (r"lamelles?",), ("strip",), True),
    FrenchUnit("round", "rondelle", "rondelles", "", (r"rondelles?",), (), True),
    FrenchUnit("branch", "branche", "branches", "", (r"branches?",), ("stalk", "stick"), True),
    FrenchUnit("stem", "tige", "tiges", "", (r"tiges?",), ("stem", "stalk"), True),
    FrenchUnit("stick", "bâton", "bâtons", "", (r"batons?",), ("stick",), True),
    FrenchUnit("drop", "goutte", "gouttes", "", (r"gouttes?",), ("drop", "dash", "splash")),
    FrenchUnit("dash", "trait", "traits", "", (r"traits?",), ("dash",), True),
    FrenchUnit("dose", "dose", "doses", "", (r"doses?",), ("dose",)),
    FrenchUnit("ladle", "louche", "louches", "", (r"louches?",), ("ladle",)),
    FrenchUnit("scoop", "boule", "boules", "", (r"boules?",), ("scoop",), True),
    FrenchUnit("serving", "portion", "portions", "", (r"portions?", r"parts?"), ("serving",)),
    FrenchUnit("dozen", "douzaine", "douzaines", "", (r"douzaines?",), ("dozen",)),
    FrenchUnit("bottle", "bouteille", "bouteilles", "", (r"bouteilles?",), ("bottle",)),
    FrenchUnit("carton", "brique", "briques", "", (r"briques?",), ("carton",), True),
    FrenchUnit("head", "tête", "têtes", "", (r"tetes?",), ("head",), True),
    FrenchUnit("pound", "livre", "livres", "lb", (r"livres?", r"lbs?"), ("pound",)),
    FrenchUnit("ounce", "once", "onces", "oz", (r"onces?", r"oz"), ("ounce",)),
)

# a unit must not be glued to a following letter or elision ("l'huile" is not "1 l")
_UNIT_END = r"(?![^\W\d_]|')"
_CONNECTOR = r"(?:de\s+la\s+|de\s+l'|de\s+|d'|du\s+|des\s+)"
_CONNECTOR_RE = re.compile(r"^" + _CONNECTOR, re.IGNORECASE)

_COMPILED_UNITS: list[tuple[FrenchUnit, re.Pattern[str]]] = [
    (
        unit,
        re.compile(
            r"^(?:"
            + "|".join(_fold(p) for p in unit.patterns)
            + r")"
            + _UNIT_END
            + (r"(?=\s*" + _fold(_CONNECTOR) + r")" if unit.requires_connector else ""),
            re.IGNORECASE,
        ),
    )
    for unit in FRENCH_UNITS
]

NUMBER_WORDS: dict[str, float] = {
    "un": 1,
    "une": 1,
    "deux": 2,
    "trois": 3,
    "quatre": 4,
    "cinq": 5,
    "six": 6,
    "sept": 7,
    "huit": 8,
    "neuf": 9,
    "dix": 10,
    "onze": 11,
    "douze": 12,
    "quinze": 15,
    "vingt": 20,
    "trente": 30,
    "quarante": 40,
    "cinquante": 50,
    "cent": 100,
}
_FRACTION_WORDS: dict[str, float] = {"demi": 0.5, "demie": 0.5, "quart": 0.25, "quarts": 0.25, "tiers": 1 / 3}

_NUM = r"\d+\s+\d+/\d+|\d+/\d+|\d+(?:[.,]\d+)?"
_NUM_RE = re.compile(rf"^({_NUM})")
_RANGE_RE = re.compile(rf"^({_NUM})\s*(?:-|–|à|a|ou)\s*({_NUM})(?!\s*/)", re.IGNORECASE)
_MULTIPLY_RE = re.compile(rf"^({_NUM})\s*[x×]\s*({_NUM})", re.IGNORECASE)
_NUMBER_WORD_RE = re.compile(
    r"^(" + "|".join(sorted(NUMBER_WORDS, key=len, reverse=True)) + r")\b(?:[\s-]+(demie?|quarts?|tiers)\b)?",
    re.IGNORECASE,
)
_HALF_RE = re.compile(r"^(demie?)\b[\s-]*", re.IGNORECASE)
_AND_HALF_RE = re.compile(r"^et\s+(demie?|quart)\b", re.IGNORECASE)
_VAGUE_QUANTITY_RE = re.compile(
    _fold(r"^(un\s+peu|quelques|plusieurs|un\s+soupcon|une\s+larme|une\s+lichette)\b\s*") + _CONNECTOR + "?",
    re.IGNORECASE,
)
_APPROX_RE = re.compile(r"^(environ|env\.|~|≈)\s*", re.IGNORECASE)
_UNIT_MODIFIER_RE = re.compile(
    _fold(r"^(rases?|bombees?|bien\s+pleines?|pleines?|bien\s+remplies?|genereuses?|a\s+ras)\b\s*"),
    re.IGNORECASE,
)
_SIZE_RE = re.compile(
    r"^(petite?s?|grosses?|gros|grande?s?|moyenne?s?|moyens?|belles?|beaux|beau|bonnes?|bons?)\s+",
    re.IGNORECASE,
)
_SIZE_FOOD_EXCEPTIONS = (
    "petits pois",
    "petit pois",
    "gros sel",
    "petit suisse",
    "petits suisses",
    "petit beurre",
    "petits beurres",
    "grand marnier",
    "petit epeautre",
    "petit-lait",
)
_LEADING_ARTICLE_RE = re.compile(r"^(?:de\s+la|de\s+l'|de|d'|du|des|le|la|les|l')(?:\s+|(?<='))", re.IGNORECASE)
_PARENS_RE = re.compile(r"\(([^()]*)\)|\[([^\[\]]*)\]")

_PREPARATION_TOKEN_RE = re.compile(
    r"^(?:(?:hach|eminc|coup|rap|cisel|pel|epluch|ecras|press|tranch|mix|concass|denoyaut|epepin|egoutt|rinc|"
    r"lav|sech|grill|torrefi|decortiqu|effeuill|equeut|pil|tamis|surgel|decongel|degerm|detaill|"
    r"ramolli|ecal|blanchi|poch|sale|dessal|marin|fum)(?:e|ee|es|ees|s)?|"
    r"fondue?s?|battue?s?|moulue?s?|cuite?s?|crue?s?|froide?s?|chaude?s?|tiedes?|frais|fraiches?|"
    r"mure?s?|ramollie?s?|mou|molle|facultatif|facultative|optionnel(?:le)?|qs|q\.s\.?|bio|environ|"
    r"pour|selon|bien|tres|finement|grossierement|legerement|petite?s?|grosses?|gros|grande?s?|moyenne?s?|moyens?)$"
)
_PREPARATION_PHRASE_RE = re.compile(
    r"^(?:en\s+(?:des|morceaux|rondelles|lamelles|cubes|tranches|petits|fines?|fins|julienne|brunoise|"
    r"quartiers|deux|quatre|huit|batonnets|puree|lanieres|copeaux|pommade|des)\b|"
    r"a\s+(?:temperature|volonte|votre|convenance|la\s+convenance)\b|au\s+(?:gout|choix)\b|de\s+preference\b|"
    r"ou\s+plus\b|ou\s+moins\b|si\s+besoin\b|sans\s+(?:la|le|les)\b|avec\s+(?:la|le|les)\b)"
)
_FOOD_EXCEPTIONS = (
    "creme fraiche",
    "fromage frais",
    "fromages frais",
    "viande hachee",
    "steak hache",
    "steaks haches",
    "boeuf hache",
    "porc hache",
    "veau hache",
    "tomates concassees",
    "tomate concassee",
    "tomates sechees",
    "fromage rape",
    "gruyere rape",
    "emmental rape",
    "parmesan rape",
    "pois casses",
    "noix de coco rapee",
    "lait de coco",
    "sucre cuit",
)
_PAIR_SEPARATOR_RE = re.compile(r"\s+et\s+", re.IGNORECASE)
_ALTERNATIVE_SEPARATOR_RE = re.compile(r"\s+ou\s+", re.IGNORECASE)

_FRENCH_STOP_WORDS = frozenset(
    {
        "de",
        "du",
        "des",
        "d",
        "la",
        "le",
        "les",
        "l",
        "et",
        "ou",
        "au",
        "aux",
        "avec",
        "pour",
        "sans",
        "en",
        "quelques",
        "peu",
        "demi",
        "demie",
        "environ",
        "selon",
        "gout",
        "volonte",
        "qs",
        *NUMBER_WORDS.keys(),
    }
)
_FRENCH_UNIT_WORDS = frozenset(
    {
        "cuillere",
        "cuilleres",
        "cuilleree",
        "cuillerees",
        "cas",
        "cac",
        "soupe",
        "cafe",
        "pincee",
        "pincees",
        "poignee",
        "poignees",
        "gousse",
        "gousses",
        "tranche",
        "tranches",
        "boite",
        "boites",
        "sachet",
        "sachets",
        "brin",
        "brins",
        "botte",
        "bottes",
        "verre",
        "verres",
        "tasse",
        "tasses",
        "morceau",
        "morceaux",
        "paquet",
        "paquets",
        "feuille",
        "feuilles",
        "litre",
        "litres",
        "gramme",
        "grammes",
    }
)
_FRENCH_FOOD_WORDS = frozenset(
    {
        "sel",
        "poivre",
        "farine",
        "sucre",
        "beurre",
        "lait",
        "oeuf",
        "oeufs",
        "huile",
        "ail",
        "oignon",
        "oignons",
        "eau",
        "creme",
        "levure",
        "echalote",
        "echalotes",
        "persil",
        "ciboulette",
        "citron",
        "pomme",
        "pommes",
        "terre",
        "tomate",
        "tomates",
        "carotte",
        "carottes",
        "poulet",
        "boeuf",
        "porc",
        "jambon",
        "lardons",
        "fromage",
        "gruyere",
        "chocolat",
        "miel",
        "vinaigre",
        "moutarde",
        "riz",
        "pates",
        "courgette",
        "courgettes",
        "poireau",
        "poireaux",
        "champignons",
        "thym",
        "laurier",
        "basilic",
        "cannelle",
        "muscade",
        "amandes",
        "vanille",
        "pain",
        "bouillon",
        "vin",
        "poivron",
        "poivrons",
        "chapelure",
        "fraises",
        "framboises",
    }
)
_ENGLISH_WORDS = frozenset(
    {
        "of",
        "and",
        "or",
        "the",
        "a",
        "an",
        "to",
        "taste",
        "for",
        "with",
        "into",
        "chopped",
        "minced",
        "sliced",
        "diced",
        "fresh",
        "large",
        "small",
        "medium",
        "ground",
        "salt",
        "pepper",
        "flour",
        "sugar",
        "butter",
        "milk",
        "egg",
        "eggs",
        "oil",
        "garlic",
        "onion",
        "onions",
        "water",
        "cream",
        "cloves",
        "clove",
        "can",
        "pinch",
        "cheese",
        "chicken",
        "beef",
        "juice",
        "lemon",
        "powder",
        "baking",
        "brown",
        "white",
        "black",
        "red",
        "green",
        "olive",
        "peeled",
        "cut",
        "optional",
        "divided",
        "plus",
        "more",
        "about",
    }
)
_ENGLISH_UNIT_WORDS = frozenset(
    {
        "cup",
        "cups",
        "tablespoon",
        "tablespoons",
        "teaspoon",
        "teaspoons",
        "tbsp",
        "tsp",
        "tbs",
        "ounce",
        "ounces",
        "oz",
        "pound",
        "pounds",
        "lb",
        "lbs",
        "quart",
        "pint",
        "gallon",
        "stick",
        "sticks",
        "grams",
        "inch",
    }
)
_WORD_RE = re.compile(r"[a-z]+")
_ACCENTED_RE = re.compile(r"[éèêëàâçîïôûùœ]", re.IGNORECASE)
_FRENCH_ABBREVIATION_RE = re.compile(
    _fold(r"\b(?:c\.?\s?a\s?(?:s|c)\b\.?|cas|cac|cs|cc|c/s|c/c)\b|\bd'|\bl'|\d,\d"), re.IGNORECASE
)


def french_language_scores(text: str) -> tuple[float, float]:
    """Returns (french_score, english_score) for an ingredient line, based on known words."""

    french = 0.0
    english = 0.0

    if _ACCENTED_RE.search(text):
        french += 0.5
    french += 1.0 * len(_FRENCH_ABBREVIATION_RE.findall(text))

    for word in _WORD_RE.findall(fold_text(text)):
        if word in _FRENCH_STOP_WORDS or word in _FRENCH_UNIT_WORDS:
            french += 1
        elif word in _FRENCH_FOOD_WORDS:
            french += 0.5

        if word in _ENGLISH_UNIT_WORDS:
            english += 1.5
        elif word in _ENGLISH_WORDS:
            english += 1

    return french, english


def is_french_locale(locale: str | None) -> bool:
    if not locale:
        return False
    return locale.lower().replace("_", "-").split("-")[0] == "fr"


def is_french_ingredient(text: str, locale: str | None = None) -> bool:
    """
    Whether an ingredient line should be parsed with the French rules.

    The text decides first; the locale only breaks ties, so an English line typed by a French user
    still goes through the English model, and a French line is detected without a French locale.
    """

    french, english = french_language_scores(text)
    if french > english:
        return True
    if is_french_locale(locale) and french >= english:
        return True
    return False


@dataclass
class FrenchParsedIngredient:
    original: str
    quantity: float = 0
    has_quantity: bool = False
    unit: FrenchUnit | None = None
    unit_text: str = ""
    food: str = ""
    preparation: str = ""
    """Preparation split from the end of the food ("hachées"); the caller may re-attach it on a DB match"""
    notes: list[str] = field(default_factory=list)
    companions: list[str] = field(default_factory=list)
    """Other foods listed with the main one ("poivre" in "sel et poivre")"""
    alternatives: list[str] = field(default_factory=list)

    @property
    def note(self) -> str:
        return ", ".join(part for part in [*self.companions, self.preparation, *self.notes] if part)


def _parse_number(value: str) -> float:
    value = value.strip().replace(",", ".")
    parts = value.split()
    total = 0.0
    for part in parts:
        if "/" in part:
            numerator, denominator = part.split("/", 1)
            try:
                total += float(Fraction(int(numerator), int(denominator)))
            except ZeroDivisionError:
                continue
        else:
            total += float(part)
    return total


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" \t,;:.-–")


def _match_unit(text: str) -> tuple[FrenchUnit, str, str] | None:
    """Returns the longest unit at the start of `text` as (unit, matched text, remaining text)."""

    best: tuple[FrenchUnit, re.Match[str]] | None = None
    for unit, pattern in _COMPILED_UNITS:
        if (match := pattern.match(text)) and (best is None or len(match.group(0)) > len(best[1].group(0))):
            best = (unit, match)

    if best is None:
        return None

    unit, match = best
    return unit, match.group(0).strip(), text[match.end() :].strip()


def _strip_size(text: str, notes: list[str]) -> str:
    if (match := _SIZE_RE.match(text)) and not fold_text(text).startswith(_SIZE_FOOD_EXCEPTIONS):
        notes.append(match.group(1))
        return text[match.end() :]
    return text


def _split_preparation(food: str) -> tuple[str, str]:
    """Splits trailing preparation words from a food, e.g. "ail hachées" -> ("ail", "hachées")."""

    tokens = food.split()
    for i in range(1, len(tokens)):
        token = fold_text(tokens[i]).strip(".,;:")
        rest = fold_text(" ".join(tokens[i:]))
        if not (_PREPARATION_TOKEN_RE.match(token) or _PREPARATION_PHRASE_RE.match(rest)):
            continue

        candidate = fold_text(" ".join(tokens[: i + 1]))
        if any(candidate == exc or candidate.startswith(exc + " ") for exc in _FOOD_EXCEPTIONS):
            continue

        return " ".join(tokens[:i]), " ".join(tokens[i:])

    return food, ""


def _parse_quantity(text: str, result: FrenchParsedIngredient) -> str:
    if match := _APPROX_RE.match(text):
        result.notes.append(match.group(1))
        text = text[match.end() :]

    if match := _VAGUE_QUANTITY_RE.match(text):
        result.notes.append(_clean(re.sub(r"\s+(?:de|d'|du|des)\s*$", "", match.group(0).strip())))
        return text[match.end() :]

    if match := _MULTIPLY_RE.match(text):
        result.quantity = _parse_number(match.group(1)) * _parse_number(match.group(2))
        result.has_quantity = True
        return text[match.end() :]

    if match := _RANGE_RE.match(text):
        result.quantity = _parse_number(match.group(1))
        result.has_quantity = True
        result.notes.append(_clean(match.group(0)))
        return text[match.end() :]

    if match := _NUM_RE.match(text):
        result.quantity = _parse_number(match.group(1))
        result.has_quantity = True
        return text[match.end() :]

    if match := _NUMBER_WORD_RE.match(text):
        quantity = NUMBER_WORDS[match.group(1).lower()]
        if match.group(2):
            quantity *= _FRACTION_WORDS[fold_text(match.group(2))]
        result.quantity = quantity
        result.has_quantity = True
        return text[match.end() :].lstrip(" -")

    if match := _HALF_RE.match(text):
        result.quantity = 0.5
        result.has_quantity = True
        return text[match.end() :]

    return text


def _parse_and_half(text: str, result: FrenchParsedIngredient) -> str:
    if result.has_quantity and (match := _AND_HALF_RE.match(text)):
        result.quantity += _FRACTION_WORDS[fold_text(match.group(1))]
        return text[match.end() :].strip()
    return text


def _prepare(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("’", "'").replace("‘", "'").replace("`", "'").replace("\u00a0", " ")
    text = re.sub(r"^\s*[-•*·▪●]\s+", "", text)
    text = convert_vulgar_fractions_to_regular_fractions(text)
    # "200g" -> "200 g", "2x400g" -> "2 x 400 g"
    text = re.sub(r"(?<=\d)(?=[^\W\d_])", " ", text)
    text = re.sub(r"(?<=\d)\s*([x×])(?=\s*\d)", r" \1", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_french_ingredient(text: str) -> FrenchParsedIngredient:
    """Splits a French ingredient line into quantity, unit, food and note."""

    result = FrenchParsedIngredient(original=text)
    working = _prepare(remove_footnote_markers(text.strip()))

    paren_notes: list[str] = []

    def _collect(match: re.Match[str]) -> str:
        content = _clean(match.group(1) if match.group(1) is not None else match.group(2))
        if content:
            paren_notes.append(content)
        return " "

    working = _clean(_PARENS_RE.sub(_collect, working))

    working = _parse_quantity(working, result).strip()
    working = _parse_and_half(working, result)
    working = _strip_size(working, result.notes)

    if unit_match := _match_unit(working):
        unit, unit_text, remaining = unit_match
        # without a quantity, a unit word is only a unit when it introduces the food ("pincée de sel")
        if result.has_quantity or result.notes or _CONNECTOR_RE.match(remaining):
            result.unit, result.unit_text = unit, unit_text
            working = _parse_and_half(remaining, result)
            if match := _UNIT_MODIFIER_RE.match(working):
                result.notes.append(match.group(1))
                working = working[match.end() :]

    if (match := _CONNECTOR_RE.match(working)) and (result.unit or result.has_quantity or result.notes):
        working = working[match.end() :]
    working = _strip_size(working.strip(), result.notes)
    working = _LEADING_ARTICLE_RE.sub("", working, count=1) if not result.unit else working

    food_part, _, comment = working.partition(",")
    if not comment and ";" in food_part:
        food_part, _, comment = food_part.partition(";")

    alternatives = _ALTERNATIVE_SEPARATOR_RE.split(food_part)
    food_part = alternatives[0]
    if len(alternatives) > 1 and not _PREPARATION_PHRASE_RE.match("ou " + fold_text(alternatives[1])):
        result.alternatives = [
            _LEADING_ARTICLE_RE.sub("", _clean(alt), count=1) for alt in alternatives[1:] if _clean(alt)
        ]
    else:
        food_part = " ou ".join(alternatives)

    food, preparation = _split_preparation(_clean(food_part))

    # "sel et poivre": keep the first food, the second one goes to the note
    pair = _PAIR_SEPARATOR_RE.split(food)
    if len(pair) == 2 and all(0 < len(p.split()) <= 2 for p in pair):
        food = pair[0]
        result.companions.append(pair[1])

    result.food = _clean(food)
    result.preparation = _clean(preparation)
    if comment := _clean(comment):
        result.notes.append(comment)
    result.notes.extend(paren_notes)

    return result


def singular_candidates(food: str) -> list[str]:
    """French singular forms of a food name, e.g. "pommes de terre" -> "pomme de terre"."""

    def _singular(word: str) -> str:
        lowered = word.lower()
        if len(word) <= 3 or lowered in {"de", "des", "du", "aux", "noix", "pois", "riz", "jus", "anchois"}:
            return word
        if lowered.endswith("eaux") or lowered.endswith("eux"):
            return word[:-1]
        if lowered.endswith(("s", "x")):
            return word[:-1]
        return word

    words = food.split()
    if not words:
        return []

    candidates = [
        " ".join([_singular(words[0]), *words[1:]]),
        " ".join(_singular(w) for w in words),
    ]
    return [c for i, c in enumerate(candidates) if c != food and c not in candidates[:i]]
