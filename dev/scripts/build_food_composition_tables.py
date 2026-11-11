"""
Build the food composition tables bundled with Mealie (mealie/assets/nutrition/*.json.gz).

Sources:
- Anses. Table de composition nutritionnelle des aliments Ciqual 2025 (Licence Ouverte / Etalab 2.0)
  https://ciqual.anses.fr/ - doi:10.57745/RDMHWY
- USDA FoodData Central, SR Legacy (April 2018, public domain)
  https://fdc.nal.usda.gov/

Usage:
    uv run python dev/scripts/build_food_composition_tables.py [--source-dir DIR]

Files already present in --source-dir are reused instead of being downloaded again.
"""

import argparse
import csv
import gzip
import io
import json
import re
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

from mealie.services.recipe.ciqual_import import clean, parse_ciqual, round_value
from mealie.services.recipe.food_reference_types import NUTRIENT_KEYS

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "mealie" / "assets" / "nutrition"

CIQUAL_VERSION = "2025"
CIQUAL_FILES = {"alim.xml": 666252, "compo.xml": 666249}
CIQUAL_URL = "https://entrepot.recherche.data.gouv.fr/api/access/datafile/{}"
USDA_VERSION = "SR Legacy 2018-04"
USDA_URL = "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip"

FIELDS = list(NUTRIENT_KEYS)

# Branded, fast food, restaurant, baby food, regional and quality-control entries.
USDA_EXCLUDED_CATEGORIES = {"3", "21", "24", "25", "26", "27"}

# Portions that weigh one whole item ("1 medium", "1 fruit"), not a slice, cup or "piece" of meat.
PIECE_MODIFIERS = ("medium", "fruit", "whole", "each", "large", "small", "clove")
CONTAINER_WORDS = {"box", "package", "packet", "cup", "slice", "can", "bottle", "container", "serving", "bar", "scoop"}


def usda_nutrients(values: dict[str, float]) -> dict[str, float | None]:
    """Map USDA nutrient ids to Mealie's nutrition fields, per 100 g."""
    carbs = values.get("1005")
    if carbs is not None and values.get("1079") is not None:
        # USDA counts fibre in carbohydrates; the EU (and Ciqual) does not.
        carbs = max(carbs - values["1079"], 0.0)
    mono, poly = values.get("1292"), values.get("1293")
    return {
        "calories": values.get("1008"),
        "carbohydrate_content": carbs,
        "sugar_content": values.get("2000"),
        "fiber_content": values.get("1079"),
        "fat_content": values.get("1004"),
        "saturated_fat_content": values.get("1258"),
        "unsaturated_fat_content": (mono or 0) + (poly or 0) if mono is not None or poly is not None else None,
        "trans_fat_content": values.get("1257"),
        "protein_content": values.get("1003"),
        "cholesterol_content": values.get("1253"),
        "sodium_content": values.get("1093"),
        "calcium_content": values.get("1087"),
        "iron_content": values.get("1089"),
        "magnesium_content": values.get("1090"),
        "potassium_content": values.get("1092"),
        "vitamin_a_content": values.get("1106"),
        "vitamin_c_content": values.get("1162"),
        "vitamin_d_content": values.get("1114"),
    }


def piece_weight(portions: list[tuple[float, str, float]]) -> float | None:
    """Average weight of one piece from USDA portions, preferring the "medium" one."""
    best: tuple[int, float] | None = None
    for amount, modifier, grams in portions:
        if amount != 1 or grams <= 0:
            continue
        words = re.findall(r"[a-z]+", modifier.lower())
        if not words:
            continue
        if CONTAINER_WORDS & set(words[:3]):
            continue
        for rank, keyword in enumerate(PIECE_MODIFIERS):
            if keyword in words[:2]:
                if best is None or rank < best[0]:
                    best = (rank, grams)
                break
    return best[1] if best else None


def _row(code: str, name_fr: str, name_en: str, nutrients: dict[str, float | None], weight: float | None) -> list:
    return [code, name_fr, name_en, *(round_value(nutrients[field]) for field in FIELDS), round_value(weight)]


def _fetch(url: str, target: Path) -> Path:
    if not target.exists():
        print(f"Downloading {url}")  # noqa: T201
        request = urllib.request.Request(url, headers={"User-Agent": "mealie-build"})
        with urllib.request.urlopen(request) as response:  # noqa: S310 - fixed, trusted URLs
            target.write_bytes(response.read())
    return target


def build_ciqual(source_dir: Path) -> dict:
    alim = _fetch(CIQUAL_URL.format(CIQUAL_FILES["alim.xml"]), source_dir / "alim.xml")
    compo = _fetch(CIQUAL_URL.format(CIQUAL_FILES["compo.xml"]), source_dir / "compo.xml")

    foods = parse_ciqual(alim, compo)
    rows = [_row(food.code, food.name, food.name_en, food.nutrients, None) for food in foods]
    return {
        "source": "ciqual",
        "version": CIQUAL_VERSION,
        "license": "Licence Ouverte / Etalab 2.0",
        "attribution": f"Anses. Table de composition nutritionnelle des aliments Ciqual {CIQUAL_VERSION}",
        "fields": FIELDS,
        "rows": sorted(rows, key=lambda row: int(row[0])),
    }


def build_usda(source_dir: Path) -> dict:
    archive = _fetch(USDA_URL, source_dir / "usda-sr.zip")

    with zipfile.ZipFile(archive) as zf:

        def read(name: str):
            member = next(m for m in zf.namelist() if m.endswith(f"/{name}") or m == name)
            return csv.DictReader(io.TextIOWrapper(zf.open(member), encoding="utf-8"))

        foods = {
            r["fdc_id"]: clean(r["description"])
            for r in read("food.csv")
            if r["food_category_id"] not in USDA_EXCLUDED_CATEGORIES
        }
        values: dict[str, dict[str, float]] = defaultdict(dict)
        for r in read("food_nutrient.csv"):
            if r["fdc_id"] in foods and r["amount"]:
                values[r["fdc_id"]][r["nutrient_id"]] = float(r["amount"])
        portions: dict[str, list[tuple[float, str, float]]] = defaultdict(list)
        for r in read("food_portion.csv"):
            if r["fdc_id"] in foods and r["amount"] and r["gram_weight"]:
                portions[r["fdc_id"]].append((float(r["amount"]), r["modifier"] or "", float(r["gram_weight"])))

    rows = [
        _row(fdc_id, "", name, usda_nutrients(values[fdc_id]), piece_weight(portions[fdc_id]))
        for fdc_id, name in foods.items()
    ]
    rows = [row for row in rows if row[3] is not None]
    return {
        "source": "usda",
        "version": USDA_VERSION,
        "license": "Public domain (CC0 1.0)",
        "attribution": f"U.S. Department of Agriculture, FoodData Central, {USDA_VERSION}",
        "fields": FIELDS,
        "rows": sorted(rows, key=lambda row: int(row[0])),
    }


def write(table: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUTPUT_DIR / f"{table['source']}.json.gz"
    payload = json.dumps(table, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    # mtime=0 keeps the output identical across rebuilds of the same data.
    with gzip.GzipFile(target, "wb", compresslevel=9, mtime=0) as fh:
        fh.write(payload)
    print(f"{target.relative_to(ROOT)}: {len(table['rows'])} foods, {target.stat().st_size // 1024} KB")  # noqa: T201


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "dev" / "data" / "nutrition-sources")
    args = parser.parse_args()
    args.source_dir.mkdir(parents=True, exist_ok=True)

    write(build_ciqual(args.source_dir))
    write(build_usda(args.source_dir))


if __name__ == "__main__":
    main()
