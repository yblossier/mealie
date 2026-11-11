"""
Lookup in the food composition tables bundled with Mealie: Ciqual (Anses, France) first, then
USDA FoodData Central. The tables are built by dev/scripts/build_food_composition_tables.py.
"""

import copy
import gzip
import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Literal

from rapidfuzz import fuzz, process
from text_unidecode import unidecode

CompositionSource = Literal["ciqual", "usda", "off"]
SOURCES: tuple[CompositionSource, ...] = ("ciqual", "usda")
"""The bundled tables; Open Food Facts ("off") is searched online by OpenFoodFactsService."""
TABLES_DIR = Path(__file__).resolve().parents[2] / "assets" / "nutrition"

STOPWORDS = {
    "a", "au", "aux", "d", "de", "des", "du", "en", "et", "l", "la", "le", "les", "ou", "un", "une",
    "and", "of", "or", "the", "with", "w",
}  # fmt: skip
RAW_WORDS = {"cru", "crue", "raw", "frai", "fraiche", "fresh"}
# Parts or processed forms that are rarely what a recipe means by the plain food name.
SECONDARY_WORDS = {
    "zeste", "zest", "peel", "jus", "juice", "poudre", "powder", "seche", "sechee", "dried", "dehydrated",
    "deshydrate", "deshydratee", "sirop", "syrup", "concentre", "concentrate", "confit", "confite", "candied",
    "appertise", "appertisee", "canned", "surgele", "surgelee", "frozen", "cuit", "cuite", "cooked", "boiled",
    "bouilli", "bouillie", "roti", "rotie", "roasted", "fried", "frit", "frite", "nectar", "sorbet", "reconstitue",
    "blanc", "jaune", "white", "yolk", "puree", "preemballe", "preemballee", "prepacked",
}  # fmt: skip
GENERIC_PHRASES = ("aliment moyen", "sans precision", "average")

# The food a recipe means by a bare staple name, when the tables list several equally plausible ones
# ("farine" could be any of seven wheat flours). Keys are normalized names, values Ciqual codes.
CIQUAL_DEFAULTS: dict[str, str] = {
    **dict.fromkeys(["farine", "farine ble", "farine ble tendre", "flour", "wheat flour", "all purpose flour"], "9436"),
    **dict.fromkeys(["sucre", "sucre blanc", "sucre poudre", "sucre semoule", "sugar", "white sugar"], "31016"),
    **dict.fromkeys(["sel", "sel fin", "sel table", "salt", "table salt"], "11058"),
    **dict.fromkeys(["poivre", "poivre noir", "pepper", "black pepper"], "11015"),
    **dict.fromkeys(["eau", "water"], "18066"),
    **dict.fromkeys(["chocolat noir", "chocolat patissier", "chocolat noir patissier", "dark chocolate"], "31085"),
    **dict.fromkeys(["creme fraiche", "creme fraiche epaisse", "creme epaisse"], "19410"),
    **dict.fromkeys(["creme liquide", "creme fleurette", "creme fraiche liquide", "heavy cream", "cream"], "19417"),
    **dict.fromkeys(["jambon", "jambon blanc", "ham"], "28900"),
    **dict.fromkeys(["riz", "rice", "white rice"], "9100"),
    **dict.fromkeys(["pate", "pate seche", "pasta"], "9810"),
    **dict.fromkeys(["huile", "huile vegetale", "oil", "vegetable oil"], "17001"),
    **dict.fromkeys(["huile olive", "olive oil"], "17270"),
    **dict.fromkeys(["beurre", "beurre doux", "butter", "unsalted butter"], "16400"),
    **dict.fromkeys(["lait", "lait demi ecreme", "milk"], "19033"),
    **dict.fromkeys(["oeuf", "egg"], "22000"),
    **dict.fromkeys(["vinaigre", "vinegar"], "11018"),
    **dict.fromkeys(["pomme terre", "potato"], "4008"),
    **dict.fromkeys(["tomate", "tomato"], "20385"),
    **dict.fromkeys(["maizena", "fecule mai", "amidon mai", "cornstarch", "corn starch"], "9510"),
    **dict.fromkeys(["levure boulanger", "levure boulangere", "levure fraiche"], "11010"),
    **dict.fromkeys(["levure boulanger seche", "levure seche", "levure deshydratee", "dry yeast"], "11045"),
    **dict.fromkeys(["fromage rape", "grated cheese"], "12775"),
    **dict.fromkeys(["emmental rape", "gruyere rape"], "12118"),
    **dict.fromkeys(["gousse ail", "garlic clove"], "11000"),
    **dict.fromkeys(["blanc poulet", "filet poulet", "escalope poulet", "chicken breast"], "36017"),
    **dict.fromkeys(["steak hache", "boeuf hache", "viande hachee", "ground beef"], "6254"),
    **dict.fromkeys(["mozzarella"], "19590"),
    **dict.fromkeys(["noix coco rapee", "coco rapee", "desiccated coconut"], "15007"),
    **dict.fromkeys(["amande poudre", "poudre amande", "almond flour", "ground almond"], "15041"),
    **dict.fromkeys(["champignon", "champignon paris", "mushroom", "button mushroom"], "20056"),
    **dict.fromkeys(["yaourt", "yaourt nature", "yogurt", "plain yogurt"], "19593"),
    **dict.fromkeys(["sucre glace", "icing sugar", "powdered sugar"], "31016"),
    **dict.fromkeys(["pain", "baguette", "bread"], "7001"),
    **dict.fromkeys(["pain mie", "sandwich bread"], "7200"),
    **dict.fromkeys(["vin blanc", "white wine"], "5215"),
    **dict.fromkeys(["moutarde dijon", "dijon mustard"], "11013"),
    **dict.fromkeys(["muscade", "noix muscade", "nutmeg"], "11048"),
    **dict.fromkeys(["ciboulette", "chive"], "11003"),
    **dict.fromkeys(["semoule", "semolina"], "9610"),
    **dict.fromkeys(["abricot sec", "dried apricot"], "13001"),
    **dict.fromkeys(["spaghetti", "tagliatelle", "penne", "macaroni", "coquillette", "fusilli"], "9810"),
}

FUZZY_LIMIT = 50


def _singular(word: str) -> str:
    if len(word) <= 3:
        return word
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("oes"):
        return word[:-2]
    if word[-1] in "sx" and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def normalize_tokens(text: str) -> list[str]:
    words = re.sub(r"[^a-z0-9]+", " ", unidecode(text or "").lower()).split()
    return [_singular(word) for word in words if word not in STOPWORDS]


def normalize(text: str) -> str:
    return " ".join(normalize_tokens(text))


@dataclass(frozen=True)
class CompositionFood:
    source: CompositionSource
    code: str
    name: str
    name_en: str
    nutrients: dict[str, float | None]
    average_weight: float | None = None


@dataclass(frozen=True)
class CompositionMatch:
    food: CompositionFood
    score: float
    tier: int
    """0: the name's main part is the query; 1: it starts with the query; 2: contains it; 3: fuzzy."""

    @property
    def exact(self) -> bool:
        return self.tier == 0


@dataclass
class _Entry:
    food: CompositionFood
    keys: list[tuple[list[str], list[str]]] = field(default_factory=list)
    """(name tokens, head tokens) for each name of the food (French and English for Ciqual)."""


def head_tokens(name: str) -> list[str]:
    """The main part of a food name, without the qualifiers that don't change what the food is."""
    head = normalize(name.split(",")[0].split("(")[0])
    for phrase in GENERIC_PHRASES:
        head = head.replace(phrase, " ")
    return [word for word in head.split() if word not in RAW_WORDS]


class CompositionTable:
    def __init__(self, data: dict) -> None:
        self.source: CompositionSource = data["source"]
        self.version: str = data.get("version", "")
        self.attribution: str = data.get("attribution", "")
        self.license: str = data.get("license", "")
        fields: list[str] = data.get("fields", [])

        self.entries: list[_Entry] = []
        self.by_code: dict[str, _Entry] = {}
        self._choices: list[str] = []
        self._choice_entry: list[int] = []
        self._index: dict[str, set[int]] = {}
        for row in data.get("rows", []):
            code, name_fr, name_en = str(row[0]), row[1], row[2]
            values = row[3 : 3 + len(fields)]
            self.add(
                CompositionFood(
                    source=self.source,
                    code=code,
                    name=name_fr or name_en,
                    name_en=name_en,
                    nutrients=dict(zip(fields, values, strict=True)),
                    average_weight=row[3 + len(fields)],
                )
            )

    def add(self, food: CompositionFood) -> None:
        """Adds a food to the table, replacing the one with the same code"""
        if food.code in self.by_code:
            self.by_code[food.code].food = food
            return
        entry = _Entry(food)
        for name in dict.fromkeys(n for n in (food.name, food.name_en) if n):
            tokens = normalize_tokens(name)
            entry.keys.append((tokens, head_tokens(name)))
            for token in tokens:
                self._index.setdefault(token, set()).add(len(self.entries))
            self._choices.append(" ".join(tokens))
            self._choice_entry.append(len(self.entries))
        self.entries.append(entry)
        self.by_code[food.code] = entry

    def extended(self, foods: Iterable[CompositionFood]) -> CompositionTable:
        """A copy of the table with more foods, leaving this one untouched (it's shared through a cache)"""
        table = copy.copy(self)
        table.entries = [_Entry(entry.food, entry.keys) for entry in self.entries]
        table.by_code = {entry.food.code: entry for entry in table.entries}
        table._choices = list(self._choices)
        table._choice_entry = list(self._choice_entry)
        table._index = {token: set(indexes) for token, indexes in self._index.items()}
        for food in foods:
            table.add(food)
        return table

    @classmethod
    def from_foods(
        cls, source: CompositionSource, foods: Iterable[CompositionFood], version: str = ""
    ) -> CompositionTable:
        table = cls({"source": source, "version": version})
        for food in foods:
            table.add(food)
        return table

    def __len__(self) -> int:
        return len(self.entries)

    def get(self, code: str) -> CompositionFood | None:
        entry = self.by_code.get(str(code))
        return entry.food if entry else None

    @staticmethod
    def tier(query: list[str], tokens: list[str], head: list[str]) -> int:
        if head == query:
            return 0
        if head[: len(query)] == query:
            return 1
        if set(query) <= set(tokens):
            return 2
        return 3

    def _candidates(self, query: list[str]) -> set[int]:
        """Foods sharing a word with the query, plus close spellings to forgive typos."""
        candidates: set[int] = set()
        for token in query:
            candidates |= self._index.get(token, set())
        for _, _, index in process.extract(
            " ".join(query), self._choices, scorer=fuzz.token_set_ratio, limit=FUZZY_LIMIT, score_cutoff=70
        ):
            candidates.add(self._choice_entry[index])
        return candidates

    def search(self, query: str, limit: int = 10) -> list[CompositionMatch]:
        q = normalize_tokens(query)
        if not q:
            return []
        query_text = " ".join(q)
        query_words = set(q)

        ranked: list[tuple[tuple, CompositionMatch]] = []
        for entry_index in self._candidates(q):
            entry = self.entries[entry_index]
            best: tuple[tuple, CompositionMatch] | None = None
            for tokens, head in entry.keys:
                text = " ".join(tokens)
                score = fuzz.token_set_ratio(query_text, text)
                tier = self.tier(q, tokens, head)
                words = set(tokens)
                rank = (
                    tier,
                    -len(query_words & words),
                    -round(score),
                    len((words - query_words) & SECONDARY_WORDS),
                    0 if words & RAW_WORDS else 1,
                    0 if any(phrase in text for phrase in GENERIC_PHRASES) else 1,
                    len(head) - len(q),
                    len(tokens),
                )
                if best is None or rank < best[0]:
                    best = (rank, CompositionMatch(entry.food, float(score), tier))
            if best and best[1].score >= 50:
                ranked.append(best)

        ranked.sort(key=lambda item: item[0])
        return [match for _, match in ranked[:limit]]

    def default(self, query: str) -> CompositionFood | None:
        code = CIQUAL_DEFAULTS.get(normalize(query)) if self.source == "ciqual" else None
        return self.get(code) if code else None

    def best(self, query: str) -> CompositionMatch | None:
        """The match confident enough to be used without anyone choosing: the food itself, not a dish with it."""
        if default := self.default(query):
            return CompositionMatch(default, 100.0, 0)
        matches = self.search(query, limit=5)
        if not matches or matches[0].tier > 1:
            return None
        top = matches[0]
        if top.tier == 1 and any(other.tier == 1 for other in matches[1:]):
            # "chocolat au lait" could be any of several bars: only take it if there's no real choice.
            return None
        return top

    def has_candidates(self, query: str) -> bool:
        """Whether the table knows foods named like this, even if none is a confident match."""
        return any(match.tier <= 1 for match in self.search(query, limit=5))


@cache
def get_table(source: CompositionSource) -> CompositionTable:
    with gzip.open(TABLES_DIR / f"{source}.json.gz", "rt", encoding="utf-8") as fh:
        return CompositionTable(json.load(fh))


class FoodCompositionService:
    """Search Ciqual first, then USDA, and attach an average piece weight taken from USDA portions."""

    def __init__(
        self,
        sources: tuple[CompositionSource, ...] = SOURCES,
        tables: Callable[[CompositionSource], CompositionTable] | None = None,
    ) -> None:
        self.sources = sources
        self._tables = tables or get_table

    def table(self, source: CompositionSource) -> CompositionTable:
        """The table of the source: the bundled one, or the referential of the database when given"""
        return self._tables(source)

    def get(self, source: str, code: str) -> CompositionFood | None:
        if source not in self.sources:
            return None
        return self.table(source).get(code)  # type: ignore[arg-type]

    def search(self, query: str, limit: int = 10) -> list[CompositionMatch]:
        """Candidates from every table, best first, Ciqual winning ties."""
        matches = [m for source in self.sources for m in self.table(source).search(query, limit)]
        matches.sort(key=lambda m: m.tier)
        return matches[:limit]

    def search_by_source(self, query: str, limit: int = 5) -> dict[CompositionSource, list[CompositionMatch]]:
        return {source: self.table(source).search(query, limit) for source in self.sources}

    def best(self, *names: str) -> CompositionMatch | None:
        """First confident match, trying Ciqual for every name before USDA."""
        for source in self.sources:
            table = self.table(source)
            for name in names:
                if name and (match := table.best(name)):
                    return match
            if any(name and table.has_candidates(name) for name in names):
                # The food is in Ciqual but it's unclear which one: a same-named USDA food is no better.
                return None
        return None

    def average_weight(self, food: CompositionFood) -> float | None:
        """USDA lists piece weights; for a Ciqual food, take the one of the closest same-named USDA food."""
        if food.average_weight:
            return food.average_weight
        if food.source == "usda" or "usda" not in self.sources or not food.name_en:
            return None
        words = set(normalize_tokens(food.name_en))
        matches = [
            match
            for match in self.table("usda").search(food.name_en.split(",")[0], limit=20)
            if match.tier == 0 and match.food.average_weight
        ]
        if not matches:
            return None
        best = max(matches, key=lambda match: len(words & set(normalize_tokens(match.food.name_en))))
        return best.food.average_weight
