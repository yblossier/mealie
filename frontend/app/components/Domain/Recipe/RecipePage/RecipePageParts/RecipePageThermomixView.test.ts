import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, test, vi } from "vitest";
import RecipePageThermomixView from "./RecipePageThermomixView.vue";
import type { RecipeOut } from "~/lib/api/types/recipe";

const mocks = vi.hoisted(() => ({
  recipes: {
    getThermomixView: vi.fn(),
    getThermomixLogs: vi.fn(),
    generateThermomixView: vi.fn(),
    deleteThermomixView: vi.fn(),
  },
}));
vi.mock("~/composables/api", () => ({
  useUserApi: () => ({ recipes: mocks.recipes }),
}));
const pageState = vi.hoisted(() => ({ isCookMode: { value: false, __v_isRef: true } }));

vi.mock("~/composables/recipe-page/shared-state", () => ({
  usePageState: () => pageState,
}));

vi.mock("~/components/Domain/Recipe/RecipeIngredients.vue", () => ({
  default: {
    props: ["value", "scale", "isCookMode"],
    template: "<ul class=\"linked-ingredients\"><li v-for=\"ing in value\" :key=\"ing.referenceId\">{{ ing.note }} x{{ scale }}</li></ul>",
  },
}));

vi.mock("~/composables/use-toast", () => ({
  alert: { success: vi.fn(), error: vi.fn() },
}));
const recipe = { id: "r", slug: "risotto", recipeInstructions: [] } as unknown as RecipeOut;
const log = {
  id: "l1",
  createdAt: "2026-11-09T09:00:00Z",
  status: "error",
  user: "Yoann",
  provider: "Ollama",
  model: "chef",
  timeoutSeconds: 300,
  durationMs: 300000,
  promptChars: 4000,
  estimatedTokens: 1000,
  request: "{\"name\":\"Risotto\"}",
  response: null,
  stepsCount: 0,
  error: "Exception: APITimeoutError",
};
function mountView(viewRecipe: RecipeOut = recipe, scale = 1) {
  return mount(RecipePageThermomixView, {
    props: { recipe: viewRecipe, canEdit: true, scale },
    global: {
      mocks: {
        $globals: { icons: new Proxy({}, { get: (_, key) => String(key) }) },
        $vuetify: { display: { smAndUp: true } },
      },
      stubs: {
        BaseButton: { template: "<button><slot /></button>" },
        VBtn: { emits: ["click"], template: "<button v-bind=\"$attrs\" @click=\"$emit('click')\"><slot /></button>" },
        VProgressCircular: true,
        VExpansionPanels: { template: "<div><slot /></div>" },
        VExpansionPanel: { template: "<div class=\"log\"><slot /></div>" },
        VExpansionPanelTitle: { template: "<div><slot /></div>" },
        VExpansionPanelText: { template: "<div><slot /></div>" },
      },
    },
  });
}
describe("RecipePageThermomixView", () => {
  test("hides the log by default and loads it when shown", async () => {
    mocks.recipes.getThermomixView.mockResolvedValue({ data: null });
    mocks.recipes.getThermomixLogs.mockResolvedValue({ data: [log] });
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.find("[data-testid='thermomix-logs']").exists()).toBe(false);
    expect(mocks.recipes.getThermomixLogs).not.toHaveBeenCalled();
    await wrapper.get("[data-testid='toggle-thermomix-logs']").trigger("click");
    await flushPromises();
    expect(mocks.recipes.getThermomixLogs).toHaveBeenCalledWith("risotto");
    const logs = wrapper.get("[data-testid='thermomix-logs']");
    expect(logs.findAll(".log")).toHaveLength(1);
    expect(logs.text()).toContain("APITimeoutError");
    expect(logs.text()).toContain("Ollama · chef");
  });
  test("shows the sections and step titles, and tags the settings without chips", async () => {
    mocks.recipes.getThermomixView.mockResolvedValue({
      data: {
        steps: [
          { id: "s1", title: "Pâte", summary: "Mélanger", text: "Mélanger 5 min/30°C/vitesse 3.", timeSeconds: 300, speed: "3" },
          { id: "s2", title: null, summary: null, text: "Verser dans le moule.", accessory: "moule à cake" },
        ],
        notes: [],
        model: "chef",
        createdAt: "2026-11-09T09:00:00Z",
      },
    });
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.findAll(".thermomix-section .section-title-text").map(s => s.text())).toEqual(["Pâte"]);
    const titles = wrapper.findAll(".thermomix-step v-card-title");
    expect(titles[0].find(".thermomix-step-summary").attributes("source")).toBe("Mélanger");
    expect(titles[0].text()).not.toContain("Step: 1");
    expect(titles[1].find(".thermomix-step-summary").exists()).toBe(false);
    expect(titles[1].text()).toContain("Step: 2");
    expect(wrapper.get(".thermomix-step-text").attributes("source"))
      .toBe("Mélanger <span class=\"thermomix-setting\">5 min/30°C/Vitesse 3</span>.");
    expect(wrapper.text()).toContain("moule à cake");
    expect(wrapper.text()).not.toContain("recipe.thermomix.speed");
  });
  test("shows the generated step times and sums them per section", async () => {
    mocks.recipes.getThermomixView.mockResolvedValue({
      data: {
        steps: [
          { id: "s1", title: "Pâte", text: "Mélanger 5 min/30°C/vitesse 3.", timeSeconds: 300, restSeconds: 3600 },
          { id: "s2", title: null, text: "Cuire au four.", cookingSeconds: 2100, coolingSeconds: 1800 },
          { id: "s3", title: "Sirop", text: "Chauffer 5 min/100°C/vitesse 2.", timeSeconds: 300 },
        ],
        notes: [],
        model: "chef",
        createdAt: "2026-11-09T09:00:00Z",
      },
    });
    const wrapper = mountView();
    await flushPromises();
    const steps = wrapper.findAll(".thermomix-step");
    expect(steps[0].findAll(".step-time").map(t => t.attributes("title")))
      .toEqual(["Duration", "Resting time"]);
    expect(steps[1].findAll(".step-time").map(t => t.attributes("title")))
      .toEqual(["Cooling time", "Cooking time"]);
    const totals = wrapper.findAll("[data-testid='thermomix-section-total']");
    expect(totals).toHaveLength(2);
    expect(totals.map(t => t.text())).toEqual(["timerOutline 2h 10m", "timerOutline 5m"]);
  });
  test("shows the recipe tools kept on a step without repeating the accessory", async () => {
    mocks.recipes.getThermomixView.mockResolvedValue({
      data: {
        steps: [
          { id: "s1", title: null, text: "Éplucher les carottes.", toolIds: ["knife"] },
          { id: "s2", title: null, text: "Cuire.", accessory: "Poêle", toolIds: ["pan"] },
          { id: "s3", title: null, text: "Mixer 10 s/vitesse 5.", toolIds: [] },
        ],
        notes: [],
        model: "chef",
        createdAt: "2026-11-09T09:00:00Z",
      },
    });
    const withTools = {
      ...recipe,
      tools: [
        { id: "knife", name: "Couteau", slug: "couteau", category: "cutlery" },
        { id: "pan", name: "Poêle", slug: "poele", category: "dishes" },
      ],
    } as unknown as RecipeOut;
    const wrapper = mountView(withTools);
    await flushPromises();
    const steps = wrapper.findAll(".thermomix-step");
    expect(steps[0].findAll("[data-testid='thermomix-step-tool']").map(t => t.text())).toEqual(["Couteau"]);
    expect(steps[1].findAll("[data-testid='thermomix-step-tool']").map(t => t.text())).toEqual(["Poêle"]);
    expect(steps[1].text().match(/Poêle/g)).toHaveLength(1);
    expect(steps[2].findAll("[data-testid='thermomix-step-tool']")).toHaveLength(0);
  });
  test("shows the cautions in the concerned step only", async () => {
    mocks.recipes.getThermomixView.mockResolvedValue({
      data: {
        steps: [
          { id: "s1", title: null, text: "Cuire 20 min/100°C/vitesse 1.", cautions: ["Le bol est brûlant."] },
          { id: "s2", title: null, text: "Mixer 10 s/vitesse 5." },
        ],
        notes: [],
        model: "chef",
        createdAt: "2026-11-09T09:00:00Z",
      },
    });
    const wrapper = mountView();
    await flushPromises();
    const steps = wrapper.findAll(".thermomix-step");
    const caution = steps[0].get("[data-testid='thermomix-step-caution']");
    expect(caution.text()).toContain("thermometer");
    expect(caution.text()).toContain("Le bol est brûlant.");
    expect(steps[1].find("[data-testid='thermomix-step-caution']").exists()).toBe(false);
  });
  test("warns that the steps come from the AI and no longer cites the source steps", async () => {
    mocks.recipes.getThermomixView.mockResolvedValue({
      data: {
        steps: [{ id: "s1", title: null, text: "Mixer 10 s/vitesse 5.", sourceStepIds: ["a"] }],
        notes: [],
        model: "chef",
        createdAt: "2026-11-09T09:00:00Z",
      },
    });

    const wrapper = mountView({ ...recipe, recipeInstructions: [{ id: "a", text: "Mixer" }] } as unknown as RecipeOut);
    await flushPromises();

    expect(wrapper.find("[data-testid='thermomix-ai-notice']").exists()).toBe(true);
    expect(wrapper.text()).not.toMatch(/From step|D'après/);
  });

  test("shows the ingredients linked to the source steps in cook mode only", async () => {
    mocks.recipes.getThermomixView.mockResolvedValue({
      data: {
        steps: [
          { id: "s1", title: null, text: "Mixer.", sourceStepIds: ["a", "b"] },
          { id: "s2", title: null, text: "Servir.", sourceStepIds: ["c"] },
        ],
        notes: [],
        model: "chef",
        createdAt: "2026-11-09T09:00:00Z",
      },
    });
    const linkedRecipe = {
      ...recipe,
      recipeIngredient: [
        { referenceId: "i1", note: "riz" },
        { referenceId: "i2", note: "oignon" },
        { referenceId: "i3", note: "sel" },
      ],
      recipeInstructions: [
        { id: "a", text: "", ingredientReferences: [{ referenceId: "i2" }] },
        { id: "b", text: "", ingredientReferences: [{ referenceId: "i1" }, { referenceId: "i2" }] },
        { id: "c", text: "", ingredientReferences: [] },
      ],
    } as unknown as RecipeOut;

    pageState.isCookMode.value = false;
    let wrapper = mountView(linkedRecipe, 2);
    await flushPromises();
    expect(wrapper.find(".linked-ingredients").exists()).toBe(false);

    pageState.isCookMode.value = true;
    wrapper = mountView(linkedRecipe, 2);
    await flushPromises();
    const steps = wrapper.findAll(".thermomix-step");
    expect(steps[0].findAll(".linked-ingredients li").map(li => li.text())).toEqual(["riz x2", "oignon x2"]);
    expect(steps[1].find("[data-testid='thermomix-step-ingredients']").exists()).toBe(false);
    pageState.isCookMode.value = false;
  });
});
