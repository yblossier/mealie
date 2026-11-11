import { describe, expect, test } from "vitest";
import { allStepsDone, useMadeThisPrompt } from "../use-made-this-prompt";

describe("allStepsDone", () => {
  test("is false without steps", () => {
    expect(allStepsDone(0, [])).toBe(false);
  });

  test("is false while a step is left", () => {
    expect(allStepsDone(3, [0, 2])).toBe(false);
  });

  test("is true once every step is checked, whatever the order", () => {
    expect(allStepsDone(3, [2, 0, 1])).toBe(true);
  });
});

describe("useMadeThisPrompt", () => {
  test("knows when a dialog is mounted for the recipe", () => {
    const prompt = useMadeThisPrompt("cake");
    expect(prompt.dialogAvailable.value).toBe(false);

    const unregister = prompt.registerDialog();
    expect(useMadeThisPrompt("cake").dialogAvailable.value).toBe(true);
    expect(useMadeThisPrompt("bread").dialogAvailable.value).toBe(false);

    unregister();
    expect(prompt.dialogAvailable.value).toBe(false);
  });

  test("shares open requests between users of the same recipe", () => {
    const dialog = useMadeThisPrompt("soup");
    const steps = useMadeThisPrompt("soup");
    const before = dialog.requests.value;

    steps.requestDialog();

    expect(dialog.requests.value).toBe(before + 1);
    expect(dialog.fromCompletion.value).toBe(false);
  });

  test("tells the dialog when the request comes from finishing the steps", () => {
    const dialog = useMadeThisPrompt("pie");
    const steps = useMadeThisPrompt("pie");

    steps.requestDialog(true);
    expect(dialog.fromCompletion.value).toBe(true);

    steps.requestDialog();
    expect(dialog.fromCompletion.value).toBe(false);
  });
});
