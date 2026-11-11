"""
Import of the Ciqual food composition table (Anses, Licence Ouverte / Etalab 2.0), published as open data on
Recherche Data Gouv (a Dataverse): the dataset's latest `alim_*.xml` (the foods) and `compo_*.xml` (their
composition) files are downloaded and parsed into the foods of the nutrition referential.

Also used by dev/scripts/build_food_composition_tables.py to build the table bundled with Mealie.
"""

import re
import tempfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

from mealie.services.recipe.food_reference_types import NUTRIENT_KEYS

DEFAULT_CIQUAL_URL = "https://entrepot.recherche.data.gouv.fr/dataset.xhtml?persistentId=doi:10.57745/RDMHWY"
DATASET_API_PATH = "/api/datasets/:persistentId/"
DATAFILE_API_PATH = "/api/access/datafile/{id}"

CIQUAL_EXCLUDED_GROUPS = {"11"}
"""Infant foods are never what a recipe means by "milk" or "cereal"."""

ALIM_FILE = re.compile(r"^alim_(\d{4})_(\d{2})_(\d{2})\.xml$", re.IGNORECASE)
COMPO_FILE = re.compile(r"^compo_(\d{4})_(\d{2})_(\d{2})\.xml$", re.IGNORECASE)

TIMEOUT = httpx.Timeout(30.0, read=120.0)
CHUNK_SIZE = 1024 * 1024


class CiqualImportError(Exception):
    """The Ciqual dataset could not be found, downloaded or read"""


def parse_ciqual_value(raw: str | None) -> float | None:
    """Ciqual values use comma decimals and may read "traces", "< 0,5" or "-"."""
    if raw is None:
        return None
    value = raw.strip().lower().replace(",", ".")
    if not value or value == "-":
        return None
    if value == "traces":
        return 0.0
    if value.startswith("<"):
        try:
            return float(value[1:].strip()) / 2
        except ValueError:
            return None
    try:
        return float(value)
    except ValueError:
        return None


def ciqual_nutrients(values: dict[str, float | None]) -> dict[str, float | None]:
    """Map Ciqual constituent codes to Mealie's nutrition fields, per 100 g."""

    def first(*codes: str) -> float | None:
        for code in codes:
            if values.get(code) is not None:
                return values[code]
        return None

    def total(*codes: str) -> float | None:
        parts = [values[code] for code in codes if values.get(code) is not None]
        return sum(parts) if parts else None  # type: ignore[arg-type]

    retinol, beta_carotene = values.get("51200"), values.get("51330")
    if retinol is not None or beta_carotene is not None:
        vitamin_a: float | None = (retinol or 0) + (beta_carotene or 0) / 12
    else:
        vitamin_a = values.get("51104")

    return {
        "calories": first("328", "333"),
        "carbohydrate_content": first("31000"),
        "sugar_content": first("32000"),
        "fiber_content": first("34100"),
        "fat_content": first("40000"),
        "saturated_fat_content": first("40302"),
        "unsaturated_fat_content": total("40303", "40304"),
        "trans_fat_content": None,
        "protein_content": first("25000", "25003"),
        "cholesterol_content": first("75100"),
        "sodium_content": first("10110"),
        "calcium_content": first("10200"),
        "iron_content": first("10260"),
        "magnesium_content": first("10120"),
        "potassium_content": first("10190"),
        "vitamin_a_content": vitamin_a,
        "vitamin_c_content": first("55100"),
        "vitamin_d_content": first("52100"),
    }


def round_value(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 3) if abs(value) < 10 else round(value, 1)


def clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


@dataclass(frozen=True)
class CiqualFood:
    code: str
    name: str
    name_en: str
    group_code: str
    nutrients: dict[str, float | None]


def parse_ciqual(alim: Path, compo: Path) -> list[CiqualFood]:
    """The foods of the table with their energy known, sorted by code, without the excluded groups"""
    foods: dict[str, tuple[str, str, str]] = {}
    for element in ET.parse(alim).getroot().iter("ALIM"):
        group = clean(element.findtext("alim_grp_code"))
        code = clean(element.findtext("alim_code"))
        if not code or group in CIQUAL_EXCLUDED_GROUPS:
            continue
        foods[code] = (clean(element.findtext("alim_nom_fr")), clean(element.findtext("alim_nom_eng")), group)

    values: dict[str, dict[str, float | None]] = defaultdict(dict)
    for _, element in ET.iterparse(compo):
        if element.tag != "COMPO":
            continue
        code = clean(element.findtext("alim_code"))
        if code in foods:
            values[code][clean(element.findtext("const_code"))] = parse_ciqual_value(element.findtext("teneur"))
        element.clear()

    result: list[CiqualFood] = []
    for code, (name_fr, name_en, group) in foods.items():
        nutrients = {key: round_value(value) for key, value in ciqual_nutrients(values[code]).items()}
        if nutrients["calories"] is None or not (name_fr or name_en):
            continue
        result.append(CiqualFood(code, name_fr or name_en, name_en, group, {k: nutrients[k] for k in NUTRIENT_KEYS}))
    return sorted(result, key=lambda food: int(food.code) if food.code.isdigit() else 0)


# ======================================================================================================================
# Dataverse


@dataclass(frozen=True)
class DatasetLocation:
    base_url: str
    persistent_id: str


def parse_dataset_url(url: str) -> DatasetLocation:
    """The server and the persistent id (doi) of a Dataverse dataset page or API URL"""
    parsed = urlparse((url or "").strip())
    if parsed.scheme != "https" or not parsed.netloc:
        raise CiqualImportError("The Ciqual URL must be an https URL")
    persistent_id = (parse_qs(parsed.query).get("persistentId") or [""])[0].strip()
    if not persistent_id:
        raise CiqualImportError("The Ciqual URL must contain the persistentId of the dataset")
    return DatasetLocation(f"https://{parsed.netloc}", persistent_id)


@dataclass(frozen=True)
class DatasetFile:
    id: int
    label: str


@dataclass
class DatasetInfo:
    version: str | None
    release_time: str | None
    files: list[DatasetFile] = field(default_factory=list)

    def latest(self, pattern: re.Pattern[str]) -> DatasetFile | None:
        """The file named like the pattern with the most recent date"""
        matches = [(m.groups(), f) for f in self.files if (m := pattern.match(f.label))]
        return max(matches, key=lambda item: item[0])[1] if matches else None


def read_dataset_info(data: dict) -> DatasetInfo:
    latest = (data.get("data") or {}).get("latestVersion") or {}
    major, minor = latest.get("versionNumber"), latest.get("versionMinorNumber")
    version = f"{major}.{minor or 0}" if major is not None else None
    files = []
    for item in latest.get("files") or []:
        file_id = (item.get("dataFile") or {}).get("id")
        label = item.get("label") or (item.get("dataFile") or {}).get("filename")
        if file_id is not None and label:
            files.append(DatasetFile(int(file_id), str(label)))
    return DatasetInfo(version=version, release_time=latest.get("releaseTime"), files=files)


@dataclass
class CiqualDownload:
    foods: list[CiqualFood]
    version: str | None
    release_time: str | None
    table_version: str
    """The date of the files, e.g. 2025-11-03"""


class CiqualDataverseClient:
    transport: httpx.BaseTransport | None = None
    """The default transport, replaced by the tests"""

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        if transport:
            self.transport = transport

    def _client(self) -> httpx.Client:
        return httpx.Client(
            transport=self.transport, timeout=TIMEOUT, follow_redirects=True, headers={"User-Agent": "Mealie"}
        )

    def dataset(self, client: httpx.Client, location: DatasetLocation) -> DatasetInfo:
        response = client.get(location.base_url + DATASET_API_PATH, params={"persistentId": location.persistent_id})
        if response.status_code != 200:
            raise CiqualImportError(f"The Ciqual dataset could not be read (status {response.status_code})")
        try:
            return read_dataset_info(response.json())
        except (ValueError, AttributeError, TypeError) as e:
            raise CiqualImportError("The Ciqual dataset gave an invalid answer") from e

    def download(self, client: httpx.Client, location: DatasetLocation, file: DatasetFile, target: Path) -> Path:
        url = location.base_url + DATAFILE_API_PATH.format(id=file.id)
        with client.stream("GET", url) as response:
            if response.status_code != 200:
                raise CiqualImportError(
                    f"The file {file.label} could not be downloaded (status {response.status_code})"
                )
            with target.open("wb") as fh:
                for chunk in response.iter_bytes(CHUNK_SIZE):
                    fh.write(chunk)
        return target

    def fetch(self, url: str) -> CiqualDownload:
        """Downloads and parses the latest version of the table published at the URL"""
        location = parse_dataset_url(url)
        try:
            with self._client() as client:
                info = self.dataset(client, location)
                alim, compo = info.latest(ALIM_FILE), info.latest(COMPO_FILE)
                if not alim or not compo:
                    raise CiqualImportError("The Ciqual dataset has no alim_*.xml or compo_*.xml file")
                with tempfile.TemporaryDirectory(prefix="mealie-ciqual-") as directory:
                    alim_path = self.download(client, location, alim, Path(directory) / "alim.xml")
                    compo_path = self.download(client, location, compo, Path(directory) / "compo.xml")
                    try:
                        foods = parse_ciqual(alim_path, compo_path)
                    except ET.ParseError as e:
                        raise CiqualImportError(f"The Ciqual files could not be read: {e}") from e
        except httpx.HTTPError as e:
            raise CiqualImportError(f"Could not reach {location.base_url}: {e}") from e

        if not foods:
            raise CiqualImportError("The Ciqual files contain no food")
        match = ALIM_FILE.match(alim.label)
        table_version = "-".join(match.groups()) if match else alim.label
        return CiqualDownload(foods, info.version, info.release_time, table_version)
