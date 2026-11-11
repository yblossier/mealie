import { beforeEach, describe, expect, it } from "vitest";
import { ImagePosition, useUserPrintPreferences } from "./preferences";

describe("useUserPrintPreferences", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("converts the legacy hidden image placement into a disabled image switch", () => {
    localStorage.setItem("recipe-print-preferences", JSON.stringify({ imagePosition: "hidden", showImage: true }));

    const preferences = useUserPrintPreferences();

    expect(preferences.value.showImage).toBe(false);
    expect(preferences.value.imagePosition).toBe(ImagePosition.left);
  });

  it("keeps a stored placement when the image is disabled", () => {
    localStorage.setItem("recipe-print-preferences", JSON.stringify({ imagePosition: "right", showImage: false }));

    const preferences = useUserPrintPreferences();

    expect(preferences.value.showImage).toBe(false);
    expect(preferences.value.imagePosition).toBe(ImagePosition.right);
  });
});
