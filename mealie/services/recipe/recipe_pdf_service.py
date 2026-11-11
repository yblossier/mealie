from __future__ import annotations

import html
import math
import re
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import Align, MethodReturnValue, XPos, YPos
from PIL import Image, ImageOps, UnidentifiedImageError

from mealie.lang.providers import Translator, get_locale_provider
from mealie.repos.repository_recipes import RepositoryRecipes
from mealie.schema.cookbook.cookbook import CookBookOut
from mealie.schema.recipe import RecipeOut
from mealie.schema.recipe.recipe_image_types import RecipeImageTypes
from mealie.schema.recipe.recipe_nutrition import Nutrition
from mealie.schema.recipe.recipe_organizers import ToolCategory, ToolOut
from mealie.schema.response.pagination import OrderDirection, PaginationQuery
from mealie.services.scraper.cleaner import pretty_print_timedelta

FONT_DIR = Path(__file__).parents[2] / "assets" / "fonts"
SANS = "NotoSans"
SERIF = "NotoSerif"

INK = (17, 17, 17)
MUTED = (105, 105, 105)
ACCENT = INK
RULE = (210, 210, 210)
ALLERGY_RED = (198, 40, 40)
ALLERGY_FILL = (253, 236, 234)
# Instruction sections get a medium grey band and each step a lighter one, as on the printed page.
GROUP_BANNER_FILL = (158, 158, 158)
STEP_BANNER_FILL = (224, 224, 224)
BANNER_PADDING_MM = 2.5
BANNER_PADDING_Y_MM = 1.2
# The Nutri-Score colors the recipe page grades its nutrition badges with, from A to E.
NUTRI_SCORE_COLORS: dict[str, tuple[int, int, int]] = {
    "A": (3, 129, 65),
    "B": (133, 187, 47),
    "C": (254, 203, 2),
    "D": (238, 129, 0),
    "E": (230, 62, 17),
}
GRADE_THRESHOLDS: list[tuple[float, str]] = [(5, "A"), (10, "B"), (20, "C"), (30, "D")]
BADGE_BORDER = (226, 226, 226)
BADGE_GAP_MM = 3
BADGE_HEIGHT_MM = 26
# The badges of the recipe page: (field, label key, unit, reference intake). Sodium uses the salt one.
NUTRITION_BADGES: list[tuple[str, str, str, float]] = [
    ("calories", "calories", "kcal", 2000),
    ("sodium_content", "sodium", "mg", 2400),
    ("sugar_content", "sugar", "g", 90),
    ("fat_content", "fat", "g", 70),
    ("salt", "salt", "g", 6),
]

MARGIN_MM = 20
BOTTOM_MM = 24
FOOTER_RULE_FROM_BOTTOM_MM = 15

# Every image is center-cropped to one banner shape so recipe pages line up. They are re-encoded
# as small JPEGs because fpdf2 stores anything that isn't JPEG as deflated raw pixels, which makes
# a cookbook with hundreds of photos balloon in size.
IMAGE_ASPECT = 2.4
IMAGE_PX = (1080, round(1080 / IMAGE_ASPECT))
IMAGE_JPEG_QUALITY = 78

TOC_ROW_MM = 8
TOC_PAGE_NUMBER_MM = 10
TOC_HEADING_BLOCK_MM = 24

# Ingredient lists shorter than this read better in a single column.
TWO_COLUMN_MIN_INGREDIENTS = 7
COLUMN_GUTTER_MM = 10
BULLET_INDENT_MM = 4.5
INGREDIENT_LINE_MM = 4.8
INGREDIENT_GAP_MM = 1.6
INGREDIENT_TITLE_GAP_MM = 3

TOOL_CHECKBOX_MM = 3
TOOL_INDENT_MM = 6
NUTRITION_ROW_MM = 6.5
NUTRITION_VALUE_MM = 50
NUTRITION_PERCENT_MM = 25
NUTRITION_INDENT_MM = 5

# Reference intakes of an average adult (EU regulation 1169/2011, Annex XIII), as on the recipe page.
# Each fact is (field, label key, unit, indented, always listed).
NUTRITION_FACTS: list[tuple[str, str, str, bool, bool]] = [
    ("calories", "energy", "kcal", False, True),
    ("fat_content", "fat", "g", False, True),
    ("saturated_fat_content", "saturates", "g", True, True),
    ("unsaturated_fat_content", "unsaturates", "g", True, False),
    ("trans_fat_content", "trans-fats", "g", True, False),
    ("cholesterol_content", "cholesterol", "mg", False, False),
    ("carbohydrate_content", "carbohydrate", "g", False, True),
    ("sugar_content", "sugars", "g", True, True),
    ("fiber_content", "fiber", "g", False, False),
    ("protein_content", "protein", "g", False, True),
    ("salt", "salt", "g", False, True),
]
MICRONUTRIENT_FACTS: list[tuple[str, str, str, bool, bool]] = [
    ("vitamin_a_content", "vitamin-a", "µg", False, False),
    ("vitamin_c_content", "vitamin-c", "mg", False, False),
    ("vitamin_d_content", "vitamin-d", "µg", False, False),
    ("calcium_content", "calcium", "mg", False, False),
    ("iron_content", "iron", "mg", False, False),
    ("magnesium_content", "magnesium", "mg", False, False),
    ("potassium_content", "potassium", "mg", False, False),
]
REFERENCE_INTAKES: dict[str, float] = {
    "calories": 2000,
    "fat_content": 70,
    "saturated_fat_content": 20,
    "carbohydrate_content": 260,
    "sugar_content": 90,
    "protein_content": 50,
    "salt": 6,
    "calcium_content": 800,
    "iron_content": 14,
    "magnesium_content": 375,
    "potassium_content": 2000,
    "vitamin_a_content": 800,
    "vitamin_c_content": 80,
    "vitamin_d_content": 5,
}
KJ_PER_KCAL = 4.184
SALT_PER_SODIUM = 2.5
_LEADING_NUMBER = re.compile(r"^\s*[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")

# Markdown is turned into font styles by hand: nothing in a recipe is handed to an HTML renderer,
# so recipe text can never load an image or a file.
_AUTOLINK = re.compile(r"<(https?://[^>\s]+)>")
_HTML_LIST_ITEM = re.compile(r"<li\b[^>]*>", re.IGNORECASE)
_HTML_BREAK = re.compile(r"<br\s*/?>|</(?:p|div|li|h[1-6]|tr|ul|ol)>", re.IGNORECASE)
_HTML_TAG = re.compile(r"</?[a-zA-Z][^>]*>")
_RULE_LINE = re.compile(r"^(?:(?:\*\s*){3,}|(?:-\s*){3,}|(?:_\s*){3,})$")
_HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*$")
_BULLET = re.compile(r"^[-*+]\s+(.*)$")
_NUMBERED = re.compile(r"^(\d+)[.)]\s+(.*)$")
_QUOTE = re.compile(r"^>\s?(.*)$")
_TABLE_SEPARATOR = re.compile(r"^\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)*\|?$")
_INLINE = re.compile(
    r"\\(?P<escaped>[\\`*_{}\[\]()#+\-.!~|>])"
    r"|(?P<image>!\[[^\]]*\]\([^)]*\))"
    r"|\[(?P<link_text>[^\]]+)\]\((?P<link_url>[^)\s]+)(?:\s+\"[^\"]*\")?\)"
    r"|`(?P<code>[^`]+)`"
    r"|\*\*(?P<bold_star>.+?)\*\*|__(?P<bold_under>.+?)__"
    r"|~~(?P<strike>.+?)~~"
    r"|\*(?P<italic_star>[^\s*](?:.*?[^\s*])?)\*"
    r"|(?<!\w)_(?P<italic_under>[^\s_](?:.*?[^\s_])?)_(?!\w)"
)
LINK_SCHEMES = ("http://", "https://", "mailto:")


@dataclass
class _Run:
    text: str
    bold: bool = False
    italic: bool = False
    link: str | None = None


def _inline_runs(text: str, bold: bool = False, italic: bool = False, link: str | None = None) -> list[_Run]:
    """Splits one line of Markdown into runs of text sharing a style."""
    runs: list[_Run] = []
    position = 0
    for match in _INLINE.finditer(text):
        if match.start() > position:
            runs.append(_Run(text[position : match.start()], bold, italic, link))
        position = match.end()
        groups = match.groupdict()
        if groups["escaped"] is not None:
            runs.append(_Run(groups["escaped"], bold, italic, link))
        elif groups["image"] is not None:
            continue
        elif groups["link_text"] is not None:
            url = groups["link_url"]
            runs += _inline_runs(groups["link_text"], bold, italic, url if url.startswith(LINK_SCHEMES) else link)
        elif groups["code"] is not None:
            runs.append(_Run(groups["code"], bold, italic, link))
        elif (inner := groups["bold_star"] or groups["bold_under"]) is not None:
            runs += _inline_runs(inner, True, italic, link)
        elif groups["strike"] is not None:
            runs += _inline_runs(groups["strike"], bold, italic, link)
        else:
            runs += _inline_runs(groups["italic_star"] or groups["italic_under"] or "", bold, True, link)
    if position < len(text):
        runs.append(_Run(text[position:], bold, italic, link))
    return runs


def _markdown_blocks(text: str) -> list[tuple[str, str, str]]:
    """Splits Markdown into (kind, list marker, inline text) lines. A single newline is a line break, as on the page."""
    text = _AUTOLINK.sub(r"[\1](\1)", text)
    text = _HTML_LIST_ITEM.sub("\n- ", text)
    text = _HTML_BREAK.sub("\n", text)
    text = html.unescape(_HTML_TAG.sub("", text))

    blocks: list[tuple[str, str, str]] = []
    for line in text.replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        if not stripped:
            if blocks and blocks[-1][0] != "gap":
                blocks.append(("gap", "", ""))
        elif _RULE_LINE.match(stripped):
            blocks.append(("rule", "", ""))
        elif match := _HEADING.match(stripped):
            blocks.append(("heading", "", match[1]))
        elif match := _BULLET.match(stripped):
            blocks.append(("item", "•", match[1]))
        elif match := _NUMBERED.match(stripped):
            blocks.append(("item", f"{match[1]}.", match[2]))
        elif match := _QUOTE.match(stripped):
            blocks.append(("quote", "", match[1]))
        elif _TABLE_SEPARATOR.match(stripped) and "-" in stripped:
            continue
        elif stripped.startswith("|"):
            blocks.append(("text", "", " · ".join(cell.strip() for cell in stripped.strip("|").split("|"))))
        else:
            blocks.append(("text", "", stripped))
    while blocks and blocks[-1][0] == "gap":
        blocks.pop()
    return blocks


def _parse_number(value: str | None) -> float | None:
    """Reads a nutrition value like the recipe page does: the number it starts with."""
    if not value or not (match := _LEADING_NUMBER.match(value)):
        return None
    try:
        number = float(match[0])
    except ValueError:
        return None
    return number if math.isfinite(number) else None


class _RecipePdf(FPDF):
    running_title = ""
    show_footer = True

    def footer(self) -> None:
        if not self.show_footer:
            return
        # Markdown is indented by moving the left margin, which may still be moved when a page breaks.
        y = self.h - FOOTER_RULE_FROM_BOTTOM_MM
        self.set_draw_color(*RULE)
        self.set_line_width(0.2)
        self.line(MARGIN_MM, y, self.w - MARGIN_MM, y)
        self.set_xy(MARGIN_MM, y + 2)
        self.set_font(SANS, size=7.5)
        self.set_text_color(*MUTED)
        self.cell(self.w - 2 * MARGIN_MM - 20, 4, self.running_title)
        self.cell(20, 4, str(self.page_no()), align="R")
        self.set_text_color(*INK)


class RecipePdfRenderer:
    """
    Draws recipes straight to PDF with fpdf2. Step and note Markdown is only turned into font
    styles by a small parser of our own, so nothing in a recipe reaches an HTML renderer, and
    images are only read from the recipe's own image directory.

    The tools a recipe needs get a page of their own right after it, and the nutrition facts get
    pages of their own at the very end of the document, so both can be left out when printing.
    """

    def __init__(
        self,
        translator: Translator,
        include_images: bool = True,
        allergens: Callable[[RecipeOut], Iterable[str]] | None = None,
        include_tools: bool = True,
    ) -> None:
        """`allergens` gives the names of the allergens found in a recipe, for its allergy block."""
        self.translator = translator
        self.allergens = allergens
        self._fallback = get_locale_provider("en-US")
        self.include_images = include_images
        self.include_tools = include_tools
        self._nutrition: list[tuple[str, Nutrition]] = []

        pdf = _RecipePdf(format="A4")
        pdf.set_auto_page_break(auto=True, margin=BOTTOM_MM)
        pdf.set_margins(MARGIN_MM, MARGIN_MM, MARGIN_MM)
        # fpdf2 pads cell text by 1mm by default, which pushes text off the margin that rules and
        # images align to.
        pdf.c_margin = 0
        pdf.add_font(SANS, style="", fname=FONT_DIR / "NotoSans-Regular.ttf")
        pdf.add_font(SANS, style="B", fname=FONT_DIR / "NotoSans-SemiBold.ttf")
        pdf.add_font(SANS, style="I", fname=FONT_DIR / "NotoSans-Italic.ttf")
        pdf.add_font(SERIF, style="B", fname=FONT_DIR / "NotoSerif-SemiBold.ttf")
        pdf.add_font(SERIF, style="I", fname=FONT_DIR / "NotoSerif-Italic.ttf")
        pdf.set_text_color(*INK)
        self.pdf = pdf
        self._next_recipe_needs_page = True
        self._toc_page_count = 0

    def t(self, key: str, **kwargs) -> str:
        """Translates `key`, in English when the current language doesn't have it yet."""
        value = self.translator.t(key, **kwargs)
        return self._fallback.t(key, **kwargs) if value == key else value

    def render_cookbook(
        self, name: str, description: str, recipes: Iterable[RecipeOut], recipe_count: int
    ) -> RecipePdfRenderer:
        pdf = self.pdf
        pdf.set_title(name)
        pdf.running_title = name
        self._cover(name, description)
        if recipe_count == 0:
            return self

        pdf.add_page()
        # fpdf2 draws a page's footer when the next page starts, so the cover's footer has already
        # been skipped by now and every later page gets one.
        pdf.show_footer = True
        # The ToC spans a fixed, precomputed number of pages. Letting fpdf2 add pages on overflow
        # (allow_extra_pages) inserts them after the footers are drawn, so every printed page
        # number after the ToC would be wrong.
        self._toc_page_count = self._toc_pages(recipe_count)
        pdf.insert_toc_placeholder(self._render_toc, pages=self._toc_page_count)
        # The placeholder already broke onto a fresh page for the first recipe.
        self._next_recipe_needs_page = False

        for recipe in recipes:
            self._recipe(recipe)

        self._nutrition_pages()
        return self

    def render_recipe(self, recipe: RecipeOut) -> RecipePdfRenderer:
        self.pdf.set_title(recipe.name)
        self.pdf.running_title = recipe.name
        self._recipe(recipe)
        self._nutrition_pages()
        return self

    def output(self, path: Path) -> Path:
        self.pdf.output(str(path))
        return path

    # ==============================================================================================
    # Cover and contents

    def _cover(self, name: str, description: str) -> None:
        pdf = self.pdf
        pdf.show_footer = False
        pdf.add_page()
        pdf.set_y(pdf.h * 0.36)

        self._label(self.t("recipe.pdf.cookbook"))
        pdf.ln(4)
        pdf.set_font(SERIF, "B", 34)
        pdf.multi_cell(0, 14, name, align=Align.L, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(5)
        self._rule(width=24, color=ACCENT, thickness=0.8)
        if description:
            pdf.ln(7)
            pdf.set_font(SERIF, "I", 13)
            pdf.set_text_color(*MUTED)
            pdf.multi_cell(pdf.epw * 0.8, 6.5, description, align=Align.L, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(*INK)

    def _toc_rows_per_page(self) -> tuple[int, int]:
        usable = self.pdf.h - self.pdf.t_margin - BOTTOM_MM
        return int((usable - TOC_HEADING_BLOCK_MM) // TOC_ROW_MM), int(usable // TOC_ROW_MM)

    def _toc_pages(self, entries: int) -> int:
        first_page, other_pages = self._toc_rows_per_page()
        if entries <= first_page:
            return 1
        return 1 + math.ceil((entries - first_page) / other_pages)

    def _render_toc(self, pdf: FPDF, outline: list) -> None:
        # Page breaks are done by hand so the ToC fills exactly the pages _toc_pages reserved.
        pdf.set_auto_page_break(False)
        start_page = pdf.page

        pdf.set_xy(pdf.l_margin, pdf.t_margin)
        pdf.set_font(SERIF, "B", 26)
        pdf.cell(0, 12, self.t("recipe.pdf.contents"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(3)
        self._rule(width=24, color=ACCENT, thickness=0.8)
        pdf.set_y(pdf.t_margin + TOC_HEADING_BLOCK_MM)

        rows_left, rows_per_page = self._toc_rows_per_page()
        for section in outline:
            if rows_left == 0:
                pdf.page += 1
                pdf.set_xy(pdf.l_margin, pdf.t_margin)
                # A page's content stream must select its own font; fpdf2 only re-emits it when
                # it thinks the page has none yet.
                pdf.current_font_is_set_on_page = False
                rows_left = rows_per_page
            rows_left -= 1
            self._toc_row(section.name, section.page_number)

        # Fewer entries than reserved rows (a recipe deleted mid-render) leaves trailing ToC pages
        # blank; fpdf2 still requires the ToC to end on its last reserved page.
        pdf.page = start_page + self._toc_page_count - 1
        pdf.set_auto_page_break(True, margin=BOTTOM_MM)

    def _toc_row(self, name: str, page_number: int) -> None:
        pdf = self.pdf
        link = pdf.add_link(page=page_number)
        title_room = pdf.epw - TOC_PAGE_NUMBER_MM - 6

        pdf.set_font(SANS, size=10.5)
        pdf.set_text_color(*INK)
        title = self._fit(name, title_room)
        title_width = pdf.get_string_width(title) + 1.5
        pdf.cell(title_width, TOC_ROW_MM, title, link=link)

        leader_width = pdf.epw - TOC_PAGE_NUMBER_MM - title_width
        dot = pdf.get_string_width(" .")
        pdf.set_text_color(*RULE)
        pdf.cell(leader_width, TOC_ROW_MM, " ." * int((leader_width - 2) / dot), align="R", link=link)

        pdf.set_text_color(*MUTED)
        pdf.cell(
            TOC_PAGE_NUMBER_MM,
            TOC_ROW_MM,
            str(page_number),
            align="R",
            link=link,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.set_text_color(*INK)

    def _fit(self, text: str, width: float) -> str:
        if self.pdf.get_string_width(text) <= width:
            return text
        while text and self.pdf.get_string_width(text + "…") > width:
            text = text[:-1]
        return text.rstrip() + "…"

    # ==============================================================================================
    # Recipe pages

    def _recipe(self, recipe: RecipeOut) -> None:
        pdf = self.pdf
        if self._next_recipe_needs_page:
            pdf.add_page()
        self._next_recipe_needs_page = True
        pdf.start_section(recipe.name)

        pdf.set_font(SERIF, "B", 24)
        pdf.multi_cell(0, 10.5, recipe.name, align=Align.L, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2.5)
        self._meta(recipe)
        pdf.ln(5)

        if self.include_images:
            self._image(recipe)

        if recipe.description:
            pdf.set_font(SERIF, "I", 11)
            pdf.set_text_color(*MUTED)
            pdf.multi_cell(0, 5.8, recipe.description, align=Align.L, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(*INK)
            pdf.ln(6)

        if recipe.recipe_ingredient:
            self._section_heading(self.t("recipe.pdf.ingredients"))
            self._ingredients(recipe)
            pdf.ln(6)

        self._allergy_block(recipe)

        if recipe.recipe_instructions:
            self._section_heading(self.t("recipe.pdf.instructions"))
            self._instructions(recipe)
            pdf.ln(4)

        if recipe.notes:
            self._section_heading(self.t("recipe.pdf.notes"))
            for note in recipe.notes:
                if note.title:
                    pdf.set_font(SANS, "B", 9.5)
                    pdf.multi_cell(0, 5.2, note.title, align=Align.L, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self._markdown(note.text, pdf.l_margin, size=9.5, line_height=5.2, color=MUTED)
                pdf.ln(2.5)

        if self.include_tools:
            self._tools_page(recipe)
        if self._has_nutrition(recipe):
            self._nutrition.append((recipe.name, recipe.nutrition))  # type: ignore[arg-type]

    def _meta(self, recipe: RecipeOut) -> None:
        items: list[tuple[str, str]] = []
        if recipe.recipe_servings:
            items.append((self.t("recipe.servings-text.servings"), f"{recipe.recipe_servings:g}"))
        if recipe.recipe_yield_quantity or recipe.recipe_yield:
            qty = f"{recipe.recipe_yield_quantity:g} " if recipe.recipe_yield_quantity else ""
            items.append((self.t("recipe.servings-text.yield"), f"{qty}{recipe.recipe_yield or ''}".strip()))
        for key, seconds, text in (
            ("recipe.pdf.prep-time", recipe.prep_time_seconds, recipe.prep_time),
            ("recipe.pdf.cook-time", recipe.perform_time_seconds, recipe.perform_time),
            ("recipe.pdf.total-time", recipe.total_time_seconds, recipe.total_time),
            ("recipe.pdf.cooling-time", recipe.cooling_time_seconds, recipe.cooling_time),
            ("recipe.pdf.rest-time", recipe.rest_time_seconds, recipe.rest_time),
        ):
            if value := self._time(seconds, text):
                items.append((self.t(key), value))

        pdf = self.pdf
        if items:
            for label, value in items:
                pdf.set_font(SANS, "B", 7)
                pdf.set_char_spacing(0.8)
                label_text = label.upper()
                label_width = pdf.get_string_width(label_text) + 2
                pdf.set_font(SANS, size=9.5)
                pdf.set_char_spacing(0)
                value_width = pdf.get_string_width(value) + 7
                if pdf.get_x() + label_width + value_width > pdf.w - pdf.r_margin:
                    pdf.ln(6)
                self._label(label_text, width=label_width, height=6, color=MUTED)
                pdf.set_font(SANS, size=9.5)
                pdf.cell(value_width, 6, value)
            pdf.ln(7)
        self._rule()

    def _time(self, seconds: int | None, text: str | None) -> str:
        """The structured time followed by the recipe's free text, matching the recipe page."""
        duration = pretty_print_timedelta(timedelta(seconds=seconds), self.translator) if seconds else ""
        return " ".join(part for part in (duration, (text or "").strip()) if part)

    def _image(self, recipe: RecipeOut) -> None:
        image_path = RecipeOut.image_dir_from_id(recipe.id) / RecipeImageTypes.min.value
        if not image_path.is_file():
            return

        try:
            with Image.open(image_path) as img:
                banner = ImageOps.fit(img.convert("RGB"), IMAGE_PX)
                buffer = BytesIO()
                banner.save(buffer, "JPEG", quality=IMAGE_JPEG_QUALITY)
        except OSError, UnidentifiedImageError:
            return

        pdf = self.pdf
        height = pdf.epw / IMAGE_ASPECT
        if pdf.will_page_break(height):
            pdf.add_page()
        pdf.image(buffer, x=pdf.l_margin, w=pdf.epw, h=height)
        pdf.ln(7)

    def _ingredients(self, recipe: RecipeOut) -> None:
        rows: list[tuple[bool, str]] = []
        for ingredient in recipe.recipe_ingredient:
            if ingredient.title:
                rows.append((True, ingredient.title))
            if text := ingredient.display or ingredient.original_text or "":
                rows.append((False, text))

        pdf = self.pdf
        column_width = (pdf.epw - COLUMN_GUTTER_MM) / 2
        if len(rows) >= TWO_COLUMN_MIN_INGREDIENTS:
            heights = [self._ingredient_row_height(row, column_width, first=i == 0) for i, row in enumerate(rows)]
            split = self._balanced_split(rows, heights)
            column_height = max(sum(heights[:split]), sum(heights[split:]))
            if column_height <= pdf.h - pdf.t_margin - BOTTOM_MM:
                if pdf.will_page_break(column_height):
                    pdf.add_page()
                top = pdf.get_y()
                self._ingredient_column(rows[:split], pdf.l_margin, column_width)
                pdf.set_y(top)
                self._ingredient_column(rows[split:], pdf.l_margin + column_width + COLUMN_GUTTER_MM, column_width)
                pdf.set_xy(pdf.l_margin, top + column_height)
                return

        self._ingredient_column(rows, pdf.l_margin, pdf.epw)

    @staticmethod
    def _balanced_split(rows: list[tuple[bool, str]], heights: list[float]) -> int:
        total = sum(heights)
        best_split, best_height = 1, total
        running = 0.0
        for split in range(1, len(rows)):
            running += heights[split - 1]
            # A section title must not end the left column.
            if rows[split - 1][0]:
                continue
            tallest = max(running, total - running)
            if tallest < best_height:
                best_split, best_height = split, tallest
        return best_split

    def _ingredient_row_height(self, row: tuple[bool, str], width: float, first: bool) -> float:
        is_title, text = row
        pdf = self.pdf
        if is_title:
            pdf.set_font(SANS, "B", 9.5)
            lines = pdf.multi_cell(width, INGREDIENT_LINE_MM, text, dry_run=True, output=MethodReturnValue.LINES)
            return (0 if first else INGREDIENT_TITLE_GAP_MM) + len(lines) * INGREDIENT_LINE_MM + INGREDIENT_GAP_MM
        pdf.set_font(SANS, size=9.5)
        lines = pdf.multi_cell(
            width - BULLET_INDENT_MM, INGREDIENT_LINE_MM, text, dry_run=True, output=MethodReturnValue.LINES
        )
        return len(lines) * INGREDIENT_LINE_MM + INGREDIENT_GAP_MM

    def _ingredient_column(self, rows: list[tuple[bool, str]], x: float, width: float) -> None:
        pdf = self.pdf
        for index, (is_title, text) in enumerate(rows):
            if is_title:
                if index > 0:
                    pdf.ln(INGREDIENT_TITLE_GAP_MM)
                pdf.set_font(SANS, "B", 9.5)
                pdf.set_x(x)
                pdf.multi_cell(width, INGREDIENT_LINE_MM, text, align=Align.L, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            else:
                pdf.set_font(SANS, size=9.5)
                pdf.set_text_color(*MUTED)
                pdf.set_x(x)
                pdf.cell(BULLET_INDENT_MM, INGREDIENT_LINE_MM, "•")
                pdf.set_text_color(*INK)
                pdf.multi_cell(
                    width - BULLET_INDENT_MM,
                    INGREDIENT_LINE_MM,
                    text,
                    align=Align.L,
                    new_x=XPos.LMARGIN,
                    new_y=YPos.NEXT,
                )
            pdf.ln(INGREDIENT_GAP_MM)

    def _allergy_block(self, recipe: RecipeOut) -> None:
        if self.allergens is None or not (recipe.settings is None or recipe.settings.show_allergens):
            return
        names = list(dict.fromkeys(name.strip() for name in self.allergens(recipe) if name and name.strip()))
        if not names:
            return

        pdf = self.pdf
        # fpdf2 reads ** and __ as markdown, which no allergen name should toggle
        listed = ", ".join(f"**{re.sub(r'[*_~-]{2,}', ' ', name)}**" for name in names)
        text = self.t("recipe.pdf.allergens-text", allergens=listed)

        padding, badge, line = 3.5, 5.0, 5.2
        text_x = pdf.l_margin + padding + badge + 3
        text_width = pdf.epw - (text_x - pdf.l_margin) - padding
        pdf.set_font(SANS, "", 9.5)
        lines = pdf.multi_cell(text_width, line, text, markdown=True, dry_run=True, output=MethodReturnValue.LINES)
        height = padding * 2 + 5 + len(lines) * line
        if pdf.will_page_break(height):
            pdf.add_page()

        top = pdf.get_y()
        pdf.set_fill_color(*ALLERGY_FILL)
        pdf.rect(pdf.l_margin, top, pdf.epw, height, style="F")
        pdf.set_fill_color(*ALLERGY_RED)
        pdf.rect(pdf.l_margin, top, 1.2, height, style="F")

        # a red disc with an exclamation mark stands in for the allergy icon the fonts don't have
        pdf.ellipse(pdf.l_margin + padding, top + padding, badge, badge, style="F")
        pdf.set_xy(pdf.l_margin + padding, top + padding)
        pdf.set_font(SANS, "B", 9)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(badge, badge, "!", align="C")

        pdf.set_xy(text_x, top + padding)
        self._label(self.t("recipe.pdf.allergens"), height=5, size=8, color=ALLERGY_RED, spacing=1)
        pdf.set_xy(text_x, top + padding + 5)
        pdf.set_font(SANS, "", 9.5)
        pdf.set_text_color(*INK)
        pdf.multi_cell(text_width, line, text, markdown=True, align=Align.L, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_y(top + height)
        pdf.ln(6)

    def _instructions(self, recipe: RecipeOut) -> None:
        pdf = self.pdf

        for number, step in enumerate(recipe.recipe_instructions, start=1):
            if step.title:
                # Keep a section title with its step's banner and first lines.
                if pdf.will_page_break(30):
                    pdf.add_page()
                pdf.ln(1.5)
                self._banner(step.title, GROUP_BANNER_FILL, SERIF, 12, 6)
                pdf.ln(2)

            if pdf.will_page_break(18):
                pdf.add_page()

            header = f"{number}. {step.summary}" if step.summary else self.t("recipe.pdf.step", number=number)
            self._banner(header, STEP_BANNER_FILL, SANS, 10, 5.4)
            pdf.ln(1.5)
            self._markdown(self._strip_step_number(step.text, number), pdf.l_margin, size=10, line_height=5.4)
            pdf.ln(3.5)

    def _banner(self, text: str, fill: tuple[int, int, int], family: str, size: float, line_height: float) -> None:
        """A full-width grey band behind a heading, as on the printed page."""
        pdf = self.pdf
        width = pdf.epw - 2 * BANNER_PADDING_MM
        pdf.set_font(family, "B", size)
        lines = pdf.multi_cell(width, line_height, text, dry_run=True, output=MethodReturnValue.LINES)
        height = len(lines) * line_height + 2 * BANNER_PADDING_Y_MM
        top = pdf.get_y()
        pdf.set_fill_color(*fill)
        pdf.rect(pdf.l_margin, top, pdf.epw, height, style="F")
        pdf.set_text_color(*INK)
        pdf.set_xy(pdf.l_margin + BANNER_PADDING_MM, top + BANNER_PADDING_Y_MM)
        pdf.multi_cell(width, line_height, text, align=Align.L, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_y(top + height)

    @staticmethod
    def _strip_step_number(text: str, number: int) -> str:
        # Scraped steps often carry their own "3." prefix, which would print next to our number.
        return re.sub(rf"^\s*{number}[.)]\s+", "", text, count=1)

    def _markdown(
        self, text: str, x: float, size: float, line_height: float, color: tuple[int, int, int] = INK
    ) -> None:
        """Writes Markdown from `x` to the right margin, then moves below it."""
        pdf = self.pdf
        margin = pdf.l_margin
        try:
            for kind, marker, inline in _markdown_blocks(text):
                if kind == "gap":
                    pdf.ln(line_height * 0.5)
                    continue
                if kind == "rule":
                    pdf.set_left_margin(x)
                    y = pdf.get_y() + line_height / 2
                    pdf.set_draw_color(*RULE)
                    pdf.set_line_width(0.25)
                    pdf.line(x, y, pdf.w - pdf.r_margin, y)
                    pdf.ln(line_height)
                    continue

                indent = 0.0
                if marker:
                    pdf.set_font(SANS, size=size)
                    indent = max(BULLET_INDENT_MM, pdf.get_string_width(marker) + 1.5)
                    pdf.set_left_margin(x)
                    pdf.set_x(x)
                    pdf.set_text_color(*MUTED)
                    pdf.cell(indent, line_height, marker)
                pdf.set_left_margin(x + indent)
                pdf.set_x(x + indent)
                for run in _inline_runs(inline, bold=kind == "heading", italic=kind == "quote"):
                    # There is no bold italic face; bold reads as the stronger emphasis.
                    pdf.set_font(SANS, "B" if run.bold else "I" if run.italic else "", size)
                    pdf.set_text_color(*(MUTED if kind == "quote" else color))
                    pdf.write(line_height, run.text, link=run.link or "")
                pdf.ln(line_height)
        finally:
            pdf.set_left_margin(margin)
            pdf.set_x(margin)
            pdf.set_text_color(*INK)

    # ==============================================================================================
    # Pages kept apart, so they can be left out when printing

    def _detached_page_heading(self, label: str, recipe_name: str) -> None:
        pdf = self.pdf
        self._label(label, size=8, color=MUTED, spacing=1.4, height=5)
        pdf.ln(6)
        pdf.set_font(SERIF, "B", 18)
        pdf.multi_cell(0, 8, recipe_name, align=Align.L, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(3)
        self._rule(width=24, color=ACCENT, thickness=0.8)
        pdf.ln(7)

    def _tools_page(self, recipe: RecipeOut) -> None:
        if not recipe.tools:
            return
        pdf = self.pdf
        pdf.add_page()
        self._detached_page_heading(self.t("recipe.pdf.tools"), recipe.name)

        steps_by_tool: dict[str, list[int]] = {}
        for number, step in enumerate(recipe.recipe_instructions, start=1):
            for reference in step.tool_references:
                if reference.reference_id:
                    steps_by_tool.setdefault(str(reference.reference_id), []).append(number)

        ids = {str(tool.id) for tool in recipe.tools}
        children: dict[str, list[ToolOut]] = {}
        for tool in recipe.tools:
            if tool.parent_id and str(tool.parent_id) in ids:
                children.setdefault(str(tool.parent_id), []).append(tool)

        categories = list(ToolCategory)
        top_level = [tool for tool in recipe.tools if not (tool.parent_id and str(tool.parent_id) in ids)]
        top_level.sort(key=lambda tool: (categories.index(tool.category), tool.name.lower()))

        current: ToolCategory | None = None
        for tool in top_level:
            if tool.category != current:
                current = tool.category
                if pdf.will_page_break(16):
                    pdf.add_page()
                pdf.ln(2)
                self._label(self.t(f"recipe.pdf.tool-categories.{tool.category.value}"), size=7.5, color=MUTED)
                pdf.ln(7)
            self._tool_row(tool, 0, steps_by_tool)
            for child in sorted(children.get(str(tool.id), []), key=lambda child: child.name.lower()):
                self._tool_row(child, TOOL_INDENT_MM, steps_by_tool)

    def _tool_row(self, tool: ToolOut, indent: float, steps_by_tool: dict[str, list[int]]) -> None:
        pdf = self.pdf
        if pdf.will_page_break(7):
            pdf.add_page()
        x = pdf.l_margin + indent
        top = pdf.get_y()
        pdf.set_draw_color(*MUTED)
        pdf.set_line_width(0.3)
        pdf.rect(x, top + 1.1, TOOL_CHECKBOX_MM, TOOL_CHECKBOX_MM)

        details = [self._tool_size(tool)]
        if steps := steps_by_tool.get(str(tool.id)):
            details.append(self.t("recipe.pdf.used-in-steps", count=len(steps), steps=", ".join(map(str, steps))))

        margin = pdf.l_margin
        pdf.set_left_margin(x + TOOL_CHECKBOX_MM + 3)
        pdf.set_x(x + TOOL_CHECKBOX_MM + 3)
        pdf.set_font(SANS, size=10)
        pdf.write(5.2, tool.name)
        if detail_text := " · ".join(detail for detail in details if detail):
            pdf.set_font(SANS, size=8.5)
            pdf.set_text_color(*MUTED)
            pdf.write(5.2, f"   {detail_text}")
            pdf.set_text_color(*INK)
        pdf.ln(5.2)
        pdf.set_left_margin(margin)
        pdf.set_x(margin)
        pdf.ln(1.8)

    def _tool_size(self, tool: ToolOut) -> str:
        if tool.category != ToolCategory.dishes:
            return ""
        if tool.diameter:
            return f"Ø {self._number(tool.diameter, 1)} cm"
        sides = [side for side in (tool.length, tool.width, tool.height) if side]
        return f"{' × '.join(self._number(side, 1) for side in sides)} cm" if sides else ""

    @staticmethod
    def _has_nutrition(recipe: RecipeOut) -> bool:
        if not recipe.nutrition or not (recipe.settings and recipe.settings.show_nutrition):
            return False
        return any(_parse_number(value) is not None for value in recipe.nutrition.model_dump().values())

    def _nutrition_pages(self) -> None:
        for name, nutrition in self._nutrition:
            self._nutrition_page(name, nutrition)
        self._nutrition = []

    def _nutrition_value(self, nutrition: Nutrition, field: str) -> float | None:
        if field == "salt":
            sodium = _parse_number(nutrition.sodium_content)
            return None if sodium is None else sodium * SALT_PER_SODIUM / 1000
        return _parse_number(getattr(nutrition, field))

    def _nutrition_rows(self, nutrition: Nutrition) -> list[tuple[str, str, str, bool, bool]]:
        """(label, value, % of the reference intake, indented, section title) rows, as on the recipe page."""

        def rows(facts: list[tuple[str, str, str, bool, bool]]) -> list[tuple[str, str, str, bool, bool]]:
            out = []
            for field, label, unit, indent, mandatory in facts:
                value = self._nutrition_value(nutrition, field)
                if value is None and not mandatory:
                    continue
                text, percent = "—", ""
                if value is not None:
                    if field == "calories":
                        text = f"{self._number(value * KJ_PER_KCAL, 0)} kJ / {self._number(value, 0)} kcal"
                    else:
                        text = f"{self._number(value, 2 if value < 10 else 1)} {unit}"
                    if reference := REFERENCE_INTAKES.get(field):
                        share = value / reference * 100
                        percent = f"{self._number(share, 1 if share < 10 else 0)}%"
                out.append((self.t(f"recipe.pdf.nutrition-facts.{label}"), text, percent, indent, False))
            return out

        macros, micros = rows(NUTRITION_FACTS), rows(MICRONUTRIENT_FACTS)
        if not micros:
            return macros
        return [*macros, (self.t("recipe.pdf.nutrition-facts.vitamins-minerals"), "", "", False, True), *micros]

    def _nutrition_badges(self, nutrition: Nutrition) -> None:
        """The row of graded badges shown above the facts table on the recipe page."""
        badges = []
        for field, label, unit, reference in NUTRITION_BADGES:
            value = self._nutrition_value(nutrition, field)
            if value is None:
                continue
            share = value / reference * 100
            grade = next((grade for limit, grade in GRADE_THRESHOLDS if share <= limit), "E")
            badges.append((self.t(f"recipe.pdf.badges.{label}"), value, unit, share, grade))
        if not badges:
            return

        pdf = self.pdf
        width = (pdf.epw - BADGE_GAP_MM * (len(NUTRITION_BADGES) - 1)) / len(NUTRITION_BADGES)
        row_width = len(badges) * width + (len(badges) - 1) * BADGE_GAP_MM
        x = pdf.l_margin + (pdf.epw - row_width) / 2
        top = pdf.get_y()
        pill_height = 6.5
        for label, value, unit, share, grade in badges:
            pdf.set_draw_color(*BADGE_BORDER)
            pdf.set_fill_color(255, 255, 255)
            pdf.set_line_width(0.6)
            pdf.rect(x, top, width, BADGE_HEIGHT_MM, style="DF", round_corners=True, corner_radius=3)

            pdf.set_xy(x, top + 2)
            pdf.set_font(SANS, "B", 7)
            pdf.cell(width, 4, self._fit(label.upper(), width - 2), align="C")
            pdf.set_xy(x, top + 6.5)
            pdf.set_font(SANS, "", 15)
            pdf.cell(width, 7, self._number(value, 1 if value < 10 else 0), align="C")
            pdf.set_xy(x, top + 13)
            pdf.set_font(SANS, "", 7.5)
            pdf.cell(width, 4, unit.upper(), align="C")

            pdf.set_fill_color(*NUTRI_SCORE_COLORS[grade])
            pill_top = top + BADGE_HEIGHT_MM - pill_height - 1.5
            pdf.rect(x + 1.5, pill_top, width - 3, pill_height, style="F", round_corners=True, corner_radius=2.5)
            pdf.set_xy(x + 1.5, pill_top)
            pdf.set_font(SANS, "B", 10.5)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(width - 3, pill_height, f"{self._number(share, 1 if share < 10 else 0)}%", align="C")
            pdf.set_text_color(*INK)
            x += width + BADGE_GAP_MM

        pdf.set_xy(pdf.l_margin, top + BADGE_HEIGHT_MM + 1.5)
        pdf.set_font(SANS, size=8)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(0, 4.2, self.t("recipe.pdf.badges.caption"), align=Align.C, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(*INK)
        pdf.ln(6)

    def _nutrition_page(self, name: str, nutrition: Nutrition) -> None:
        pdf = self.pdf
        pdf.add_page()
        self._detached_page_heading(self.t("recipe.pdf.nutrition"), name)
        self._nutrition_badges(nutrition)

        left = pdf.l_margin
        label_width = pdf.epw - NUTRITION_VALUE_MM - NUTRITION_PERCENT_MM
        top = pdf.get_y()
        pdf.set_x(left)
        pdf.set_font(SANS, "B", 10)
        pdf.cell(label_width, 8, self.t("recipe.pdf.nutrition-facts.title"))
        pdf.cell(NUTRITION_VALUE_MM, 8, self.t("recipe.pdf.nutrition-facts.per-serving"), align="R")
        pdf.cell(NUTRITION_PERCENT_MM, 8, self.t("recipe.pdf.nutrition-facts.ri"), align="R")
        pdf.ln(8)
        self._table_line(left, 1.4)

        for label, value, percent, indent, section in self._nutrition_rows(nutrition):
            pdf.set_x(left)
            if section:
                pdf.ln(1.5)
                pdf.set_font(SANS, "B", 9.5)
                pdf.cell(pdf.epw, NUTRITION_ROW_MM, label)
                pdf.ln(NUTRITION_ROW_MM)
                self._table_line(left, 0.8)
                continue
            pdf.set_font(SANS, "" if indent else "B", 9.5)
            pdf.set_x(left + (NUTRITION_INDENT_MM if indent else 0))
            pdf.cell(label_width - (NUTRITION_INDENT_MM if indent else 0), NUTRITION_ROW_MM, label)
            pdf.set_font(SANS, size=9.5)
            pdf.cell(NUTRITION_VALUE_MM, NUTRITION_ROW_MM, value, align="R")
            pdf.cell(NUTRITION_PERCENT_MM, NUTRITION_ROW_MM, percent, align="R")
            pdf.ln(NUTRITION_ROW_MM)
            self._table_line(left, 0.2)

        bottom = pdf.get_y()
        pdf.set_draw_color(*INK)
        pdf.set_line_width(0.5)
        pdf.rect(left - 2, top - 1.5, pdf.epw + 4, bottom - top + 3)
        pdf.set_y(bottom + 4)
        pdf.set_font(SANS, size=8)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(
            0, 4.2, self.t("recipe.pdf.nutrition-facts.ri-footnote"), align=Align.L, new_x=XPos.LMARGIN, new_y=YPos.NEXT
        )
        pdf.set_text_color(*INK)

    def _table_line(self, left: float, thickness: float) -> None:
        pdf = self.pdf
        y = pdf.get_y()
        pdf.set_draw_color(*INK)
        pdf.set_line_width(thickness)
        pdf.line(left, y, left + pdf.epw, y)

    def _number(self, value: float, digits: int) -> str:
        """Formats like the page does: at most `digits` decimals, with the language's separators."""
        # Rounds half up, like Intl.NumberFormat on the page, where Python would round half to even.
        rounded = Decimal(repr(value)).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)
        text = f"{rounded:,f}"
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        decimal = self.t("recipe.pdf.decimal-separator")
        thousands = self.t("recipe.pdf.thousands-separator")
        return text.replace(",", "\0").replace(".", decimal).replace("\0", thousands)

    # ==============================================================================================
    # Shared pieces

    def _section_heading(self, text: str) -> None:
        pdf = self.pdf
        # Keep a heading with at least a few lines of what follows it.
        if pdf.will_page_break(24):
            pdf.add_page()
        self._label(text, size=8, color=ACCENT, spacing=1.4, height=5)
        pdf.ln(5.5)
        self._rule()
        pdf.ln(3.5)

    def _label(
        self,
        text: str,
        width: float = 0,
        height: float = 5,
        size: float = 7,
        color: tuple[int, int, int] = ACCENT,
        spacing: float = 0.8,
    ) -> None:
        pdf = self.pdf
        pdf.set_font(SANS, "B", size)
        pdf.set_char_spacing(spacing)
        pdf.set_text_color(*color)
        pdf.cell(width, height, text.upper())
        pdf.set_char_spacing(0)
        pdf.set_text_color(*INK)

    def _rule(self, width: float | None = None, color: tuple[int, int, int] = RULE, thickness: float = 0.25) -> None:
        pdf = self.pdf
        y = pdf.get_y()
        pdf.set_draw_color(*color)
        pdf.set_line_width(thickness)
        pdf.line(pdf.l_margin, y, pdf.l_margin + (width if width is not None else pdf.epw), y)


def render_cookbook_pdf(
    renderer: RecipePdfRenderer, recipes: RepositoryRecipes, cookbook: CookBookOut
) -> RecipePdfRenderer:
    """
    Renders every recipe in a cookbook, sorted by name. Only summaries are listed up front; full
    recipes are loaded one at a time so a large cookbook never sits in memory all at once.
    """
    query = PaginationQuery(page=1, per_page=-1, order_by="name", order_direction=OrderDirection.asc)
    summaries = recipes.page_all(query, cookbook=cookbook).items

    def load() -> Iterator[RecipeOut]:
        for summary in summaries:
            if recipe := recipes.get_one(summary.id, "id"):
                yield recipe

    return renderer.render_cookbook(cookbook.name, cookbook.description, load(), recipe_count=len(summaries))
