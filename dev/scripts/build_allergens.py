"""
Build the allergen seed data bundled with Mealie (mealie/repos/seed/resources/allergens/allergens.json).

The allergens are the 14 major allergens of Annex II of Regulation (EU) No 1169/2011, whose labelling
is mandatory in the European Union. Their synonyms come from the Open Food Facts allergen taxonomy
(Open Database License), completed with the culinary words recipes use for them (flour, pasta, mayonnaise...)
and with the phrases that merely look like them (coconut, nutmeg, a knob of butter...).

Source:
- Open Food Facts allergen taxonomy (ODbL)
  https://github.com/openfoodfacts/openfoodfacts-server/blob/main/taxonomies/allergens.txt

Usage:
    uv run python dev/scripts/build_allergens.py [--source FILE]
"""

import argparse
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "mealie" / "repos" / "seed" / "resources" / "allergens" / "allergens.json"
OFF_URL = "https://raw.githubusercontent.com/openfoodfacts/openfoodfacts-server/main/taxonomies/allergens.txt"

# allergen code -> the English canonical name of its Open Food Facts entry
EU_ALLERGENS = {
    "gluten": "gluten",
    "crustaceans": "crustaceans",
    "eggs": "eggs",
    "fish": "fish",
    "peanuts": "peanuts",
    "soybeans": "soybeans",
    "milk": "milk",
    "nuts": "nuts",
    "celery": "celery",
    "mustard": "mustard",
    "sesame": "sesame seeds",
    "sulphites": "sulphur dioxide and sulphites",
    "lupin": "lupin",
    "molluscs": "molluscs",
}

NAMES = {
    "en": {
        "gluten": "Gluten",
        "crustaceans": "Crustaceans",
        "eggs": "Eggs",
        "fish": "Fish",
        "peanuts": "Peanuts",
        "soybeans": "Soybeans",
        "milk": "Milk",
        "nuts": "Tree nuts",
        "celery": "Celery",
        "mustard": "Mustard",
        "sesame": "Sesame",
        "sulphites": "Sulphites",
        "lupin": "Lupin",
        "molluscs": "Molluscs",
    },
    "fr": {
        "gluten": "Gluten",
        "crustaceans": "Crustacés",
        "eggs": "Œufs",
        "fish": "Poissons",
        "peanuts": "Arachides",
        "soybeans": "Soja",
        "milk": "Lait",
        "nuts": "Fruits à coque",
        "celery": "Céleri",
        "mustard": "Moutarde",
        "sesame": "Sésame",
        "sulphites": "Sulfites",
        "lupin": "Lupin",
        "molluscs": "Mollusques",
    },
}

# words recipes use for an allergen that a food labelling taxonomy has no reason to list
SUPPLEMENTS = {
    "en": {
        "gluten": [
            "flour",
            "all-purpose flour",
            "plain flour",
            "self-raising flour",
            "puff pastry",
            "shortcrust pastry",
            "pizza dough",
            "bread",
            "breadcrumbs",
            "semolina",
            "couscous",
            "pasta",
            "spaghetti",
            "noodles",
            "biscuit",
            "cracker",
            "beer",
            "bulgur",
        ],
        "eggs": ["mayonnaise", "meringue"],
        "fish": ["anchovy", "anchovies", "fish sauce"],
        "soybeans": ["tofu", "soy sauce", "miso", "edamame", "tamari"],
        "milk": ["mozzarella", "parmesan", "ricotta", "mascarpone", "feta", "ghee", "custard"],
        "nuts": ["almond", "hazelnut", "walnut", "marzipan", "praline"],
        "sesame": ["tahini"],
        "sulphites": ["wine"],
    },
    "fr": {
        "gluten": [
            "farine",
            "pâte feuilletée",
            "pâte brisée",
            "pâte sablée",
            "pâte à pizza",
            "pain",
            "pain de mie",
            "chapelure",
            "semoule",
            "couscous",
            "pâtes",
            "spaghetti",
            "tagliatelle",
            "lasagne",
            "nouille",
            "biscuit",
            "bière",
            "levain",
        ],
        "eggs": ["mayonnaise", "meringue"],
        "fish": ["anchois", "sauce poisson", "nuoc-mâm"],
        "soybeans": ["miso", "edamame", "tamari"],
        "milk": ["mozzarella", "parmesan", "ricotta", "mascarpone", "gruyère", "feta", "ghee", "chantilly", "béchamel"],
        "nuts": ["amande", "noisette", "pistache", "noix de pécan", "praliné", "pralin", "frangipane", "massepain"],
        "sesame": ["tahini", "tahin", "gomasio"],
        "sulphites": ["vin"],
    },
}

# phrases containing an allergen keyword without containing the allergen
EXCLUSIONS = {
    "en": {
        "gluten": [
            "rice flour",
            "corn flour",
            "cornflour",
            "buckwheat flour",
            "chickpea flour",
            "almond flour",
            "coconut flour",
            "potato flour",
            "rice noodles",
            "gluten-free",
            "gluten free",
        ],
        "milk": [
            "coconut milk",
            "coconut cream",
            "peanut butter",
            "almond milk",
            "soy milk",
            "oat milk",
            "rice milk",
            "cocoa butter",
            "cream of tartar",
        ],
        "nuts": ["coconut", "nutmeg"],
        "sulphites": ["wine vinegar"],
    },
    "fr": {
        "gluten": [
            "farine de riz",
            "farine de maïs",
            "farine de sarrasin",
            "farine de pois chiche",
            "farine de châtaigne",
            "farine d'amande",
            "farine de coco",
            "semoule de maïs",
            "nouilles de riz",
            "sans gluten",
            "fécule",
        ],
        "milk": [
            "lait de coco",
            "crème de coco",
            "beurre de cacahuète",
            "beurre de cacahuètes",
            "lait d'amande",
            "lait de soja",
            "lait d'avoine",
            "lait de riz",
            "crème de soja",
            "beurre de cacao",
            "crème de marrons",
            "crème de cassis",
        ],
        "nuts": [
            "noix de coco",
            "noix de muscade",
            "noix de saint-jacques",
            "noix de st-jacques",
            "noix de beurre",
            "noix de veau",
        ],
    },
}


def read_source(source: Path | None) -> str:
    if source:
        return source.read_text(encoding="utf-8")
    with urllib.request.urlopen(OFF_URL, timeout=60) as response:
        return response.read().decode("utf-8")


def parse_taxonomy(text: str) -> list[dict[str, list[str]]]:
    """Each entry maps a language to its synonyms, the first one being the entry's name."""
    entries: list[dict[str, list[str]]] = []
    for block in text.split("\n\n"):
        entry: dict[str, list[str]] = {}
        for line in block.splitlines():
            line = line.strip()
            if not line or line.startswith(("#", "<", "stopwords:", "synonyms:")):
                continue
            lang, sep, values = line.partition(":")
            # properties such as "wikidata:en: Q123" have a second colon
            if not sep or len(lang) > 3 or ":" in values.split(",")[0]:
                continue
            synonyms = [value.strip() for value in values.split(",") if value.strip()]
            if synonyms:
                entry[lang.strip()] = synonyms
        if entry:
            entries.append(entry)
    return entries


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for value in values:
        key = value.lower()
        if key not in seen:
            seen.add(key)
            result.append(value.lower())
    return result


def build(text: str) -> dict:
    entries = {entry["en"][0].lower(): entry for entry in parse_taxonomy(text) if "en" in entry}
    allergens: dict[str, dict] = {}
    for code, off_name in EU_ALLERGENS.items():
        entry = entries.get(off_name)
        if entry is None:
            raise SystemExit(f"Allergen '{off_name}' is missing from the Open Food Facts taxonomy")

        locales = {}
        for lang in sorted(set(entry) | set(NAMES)):
            keywords = unique(entry.get(lang, []) + SUPPLEMENTS.get(lang, {}).get(code, []))
            if not keywords:
                continue
            name = NAMES.get(lang, {}).get(code) or keywords[0][:1].upper() + keywords[0][1:]
            locales[lang] = {
                "name": name,
                "keywords": keywords,
                "exclusions": unique(EXCLUSIONS.get(lang, {}).get(code, [])),
            }
        allergens[code] = {"locales": locales}

    return {
        "source": "Regulation (EU) No 1169/2011, Annex II - synonyms from the Open Food Facts allergen taxonomy",
        "license": "ODbL",
        "url": OFF_URL,
        "allergens": allergens,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, help="a local copy of the Open Food Facts allergens.txt")
    args = parser.parse_args()

    data = build(read_source(args.source))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(data['allergens'])} allergens to {OUTPUT.relative_to(ROOT)}")  # noqa: T201


if __name__ == "__main__":
    main()
