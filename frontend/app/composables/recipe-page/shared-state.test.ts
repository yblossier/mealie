import { afterEach, describe, expect, test, vi } from "vitest";
import { clearPageState, usePageState } from "./shared-state";

vi.mock("~/composables/use-navigation-warning", () => ({
  useNavigationWarning: () => ({ activateNavigationWarning: vi.fn(), deactivateNavigationWarning: vi.fn() }),
}));

describe("usePageState thermomix view", () => {
  afterEach(() => {
    clearPageState("pancakes");
    clearPageState("waffles");
  });

  test("starts on the original steps and toggles back and forth", () => {
    const state = usePageState("pancakes");
    expect(state.isThermomixView.value).toBe(false);

    state.toggleThermomixView();
    expect(state.isThermomixView.value).toBe(true);

    state.toggleThermomixView();
    expect(state.isThermomixView.value).toBe(false);
  });

  test("is shared by the components of a recipe page but not across recipes", () => {
    usePageState("pancakes").toggleThermomixView();

    expect(usePageState("pancakes").isThermomixView.value).toBe(true);
    expect(usePageState("waffles").isThermomixView.value).toBe(false);
  });

  test("is forgotten once the page state is cleared", () => {
    usePageState("pancakes").toggleThermomixView();
    clearPageState("pancakes");

    expect(usePageState("pancakes").isThermomixView.value).toBe(false);
  });
});
