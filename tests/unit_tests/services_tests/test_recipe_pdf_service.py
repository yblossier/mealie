from uuid import uuid4

from mealie.lang.providers import get_locale_provider
from mealie.schema.recipe import RecipeOut
from mealie.schema.recipe.recipe_nutrition import Nutrition
from mealie.schema.recipe.recipe_organizers import ToolCategory, ToolOut
from mealie.schema.recipe.recipe_settings import RecipeSettings
from mealie.schema.recipe.recipe_step import RecipeStep, ToolReference
from mealie.services.recipe.recipe_pdf_service import RecipePdfRenderer, _inline_runs, _markdown_blocks


def _styles(text: str) -> list[tuple[str, bool, bool, str | None]]:
    return [(run.text, run.bold, run.italic, run.link) for run in _inline_runs(text)]


def test_inline_markdown_becomes_styled_runs() -> None:
    assert _styles("Mix **5 min/37°C/speed 2** then *rest*.") == [
        ("Mix ", False, False, None),
        ("5 min/37°C/speed 2", True, False, None),
        (" then ", False, False, None),
        ("rest", False, True, None),
        (".", False, False, None),
    ]
    assert _styles("See [the guide](https://example.com) ![photo](/etc/passwd)") == [
        ("See ", False, False, None),
        ("the guide", False, False, "https://example.com"),
        (" ", False, False, None),
    ]
    assert _styles("[local](file:///etc/passwd) 2 \\* 3 snake_case_name") == [
        ("local", False, False, None),
        (" 2 ", False, False, None),
        ("*", False, False, None),
        (" 3 snake_case_name", False, False, None),
    ]


def test_markdown_blocks_keep_line_breaks_and_drop_html() -> None:
    text = "## Dough\nMix the flour\nand the eggs.\n\n- one\n2. two\n> tip\n---\n<b>bold</b> &amp; <img src=x>"
    assert _markdown_blocks(text) == [
        ("heading", "", "Dough"),
        ("text", "", "Mix the flour"),
        ("text", "", "and the eggs."),
        ("gap", "", ""),
        ("item", "•", "one"),
        ("item", "2.", "two"),
        ("quote", "", "tip"),
        ("rule", "", ""),
        ("text", "", "bold &"),
    ]


def _recipe(tools: list[ToolOut], nutrition: Nutrition | None, show_nutrition: bool = True) -> RecipeOut:
    return RecipeOut.model_construct(
        id=uuid4(),
        name="Gâteau",
        slug="gateau",
        recipe_servings=12,
        recipe_yield_quantity=0,
        recipe_yield=None,
        prep_time_seconds=900,
        perform_time_seconds=None,
        total_time_seconds=None,
        prep_time=None,
        perform_time=None,
        total_time=None,
        description="",
        recipe_ingredient=[],
        recipe_instructions=[
            RecipeStep(text="**Mélanger** 5 min", tool_references=[ToolReference(reference_id=tools[0].id)])
        ]
        if tools
        else [RecipeStep(text="Mélanger")],
        notes=[],
        tools=tools,
        nutrition=nutrition,
        settings=RecipeSettings(show_nutrition=show_nutrition),
    )


def _tool(name: str, category: ToolCategory, **kwargs) -> ToolOut:
    return ToolOut(id=uuid4(), group_id=uuid4(), name=name, slug=name.lower(), category=category, **kwargs)


def test_tools_and_nutrition_get_their_own_pages_at_the_end() -> None:
    translator = get_locale_provider("fr-FR")
    tools = [_tool("Moule", ToolCategory.dishes, diameter=24), _tool("Fouet", ToolCategory.utensils)]
    nutrition = Nutrition(calories="250", sodium_content="400", fat_content="12.5")

    renderer = RecipePdfRenderer(translator, include_images=False)
    renderer.render_recipe(_recipe(tools, nutrition))
    assert renderer.pdf.page == 3
    renderer.pdf.output()

    renderer = RecipePdfRenderer(translator, include_images=False)
    renderer.render_recipe(_recipe([], nutrition, show_nutrition=False))
    assert renderer.pdf.page == 1

    assert renderer.t("recipe.servings-text.servings") == "Portions"
    assert renderer._tool_size(tools[0]) == "Ø 24 cm"
    rows = {label: (value, percent) for label, value, percent, _, _ in renderer._nutrition_rows(nutrition)}
    assert rows["Énergie"] == ("1\u00a0046 kJ / 250 kcal", "13%")
    assert rows["Matières grasses"] == ("12,5 g", "18%")
    assert rows["Sel"] == ("1 g", "17%")
    assert rows["Protéines"] == ("—", "")
    renderer.pdf.output()


def test_cookbook_keeps_every_nutrition_page_at_the_end() -> None:
    renderer = RecipePdfRenderer(get_locale_provider("en-US"), include_images=False)
    recipes = [_recipe([], Nutrition(calories="100")), _recipe([], Nutrition(calories="200"))]
    renderer.render_cookbook("Book", "", recipes, recipe_count=2)
    # cover, contents, two recipes, then the two nutrition pages
    assert renderer.pdf.page == 6
    assert [section.name for section in renderer.pdf._outline] == ["Gâteau", "Gâteau"]
    assert [section.page_number for section in renderer.pdf._outline] == [3, 4]
    renderer.pdf.output()


def test_allergy_block_lists_each_allergen_once() -> None:
    texts: list[str] = []
    renderer = RecipePdfRenderer(
        get_locale_provider("fr-FR"), include_images=False, allergens=lambda _: ["Gluten", "Lait", "Gluten"]
    )
    original = renderer.pdf.multi_cell

    def spy(*args, **kwargs):
        if not kwargs.get("dry_run") and len(args) > 2:
            texts.append(args[2])
        return original(*args, **kwargs)

    renderer.pdf.multi_cell = spy  # type: ignore[method-assign]
    renderer.render_recipe(_recipe([], None))
    assert "Contient : **Gluten**, **Lait**." in texts
    renderer.pdf.output()

    texts.clear()
    recipe = _recipe([], None)
    recipe.settings = RecipeSettings(show_allergens=False)
    renderer = RecipePdfRenderer(get_locale_provider("fr-FR"), include_images=False, allergens=lambda _: ["Gluten"])
    original = renderer.pdf.multi_cell
    renderer.pdf.multi_cell = spy  # type: ignore[method-assign]
    renderer.render_recipe(recipe)
    assert not any("Gluten" in text for text in texts)


def test_tools_page_can_be_left_out() -> None:
    tools = [_tool("Fouet", ToolCategory.utensils)]
    renderer = RecipePdfRenderer(get_locale_provider("fr-FR"), include_images=False, include_tools=False)
    renderer.render_recipe(_recipe(tools, None))
    assert renderer.pdf.page == 1
    renderer.pdf.output()


def test_step_groups_and_steps_get_grey_banners() -> None:
    fills: list[tuple[float, ...]] = []
    texts: list[str] = []
    renderer = RecipePdfRenderer(get_locale_provider("fr-FR"), include_images=False)
    original_fill, original_cell = renderer.pdf.set_fill_color, renderer.pdf.multi_cell

    def spy_fill(*args, **kwargs):
        fills.append(args)
        return original_fill(*args, **kwargs)

    def spy_cell(*args, **kwargs):
        if not kwargs.get("dry_run") and len(args) > 2:
            texts.append(args[2])
        return original_cell(*args, **kwargs)

    renderer.pdf.set_fill_color = spy_fill  # type: ignore[method-assign]
    renderer.pdf.multi_cell = spy_cell  # type: ignore[method-assign]
    recipe = _recipe([], None)
    recipe.recipe_instructions = [
        RecipeStep(title="Pâte", text="Mélanger"),
        RecipeStep(summary="Cuire", text="20 min"),
    ]
    renderer.render_recipe(recipe)
    assert (158, 158, 158) in fills
    assert fills.count((224, 224, 224)) == 2
    assert ["Pâte", "Étape 1", "2. Cuire"] == [text for text in texts if text in {"Pâte", "Étape 1", "2. Cuire"}]
    renderer.pdf.output()


def test_nutrition_page_shows_the_recipe_page_badges() -> None:
    texts: list[str] = []
    renderer = RecipePdfRenderer(get_locale_provider("fr-FR"), include_images=False)
    original = renderer.pdf.cell

    def spy(*args, **kwargs):
        if len(args) > 2:
            texts.append(args[2])
        return original(*args, **kwargs)

    renderer.pdf.cell = spy  # type: ignore[method-assign]
    renderer.render_recipe(_recipe([], Nutrition(calories="250", sodium_content="400", sugar_content="45")))
    assert renderer.pdf.page == 2
    # calories 13%, sodium 17%, sugar 50% and salt 17%; fat is missing so it gets no badge
    for text in ["CALORIES", "SODIUM", "SUCRES", "SEL", "13%", "17%", "50%", "KCAL"]:
        assert text in texts
    assert "MATIÈRES GRASSES" not in texts
    renderer.pdf.output()
