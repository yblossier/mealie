import { describe, expect, test } from "vitest";
import { markdownEdit, markdownShortcut, type MarkdownFormat } from "./markdown-shortcuts";

/** Applies a format to text where `[` and `]` mark the selection, and returns the result marked the same way. */
function format(kind: MarkdownFormat, marked: string): string {
  const start = marked.indexOf("[");
  const end = marked.indexOf("]") - 1;
  const text = marked.replace("[", "").replace("]", "");
  const edit = markdownEdit(kind, text, start, end);
  const result = text.slice(0, edit.from) + edit.insert + text.slice(edit.to);
  return `${result.slice(0, edit.selectionStart)}[${result.slice(edit.selectionStart, edit.selectionEnd)}]${result.slice(edit.selectionEnd)}`;
}

describe("markdownEdit", () => {
  test.each<[MarkdownFormat, string, string]>([
    ["bold", "Mix the [flour] well", "Mix the **[flour]** well"],
    ["italic", "Mix the [flour] well", "Mix the *[flour]* well"],
    ["underline", "Mix the [flour] well", "Mix the <u>[flour]</u> well"],
    ["strikethrough", "Mix the [flour] well", "Mix the ~~[flour]~~ well"],
    ["bold", "Mix the [flour ]well", "Mix the **[flour]** well"],
    ["bold", "Mix []", "Mix **[]**"],
  ])("%s wraps %s", (kind, input, output) => {
    expect(format(kind, input)).toBe(output);
  });

  test.each<[MarkdownFormat, string, string]>([
    ["bold", "Mix the **[flour]** well", "Mix the [flour] well"],
    ["bold", "Mix the [**flour**] well", "Mix the [flour] well"],
    ["italic", "Mix the *[flour]* well", "Mix the [flour] well"],
    ["italic", "Mix the ***[flour]*** well", "Mix the **[flour]** well"],
    ["bold", "Mix the ***[flour]*** well", "Mix the *[flour]* well"],
    ["underline", "Mix the [<u>flour</u>] well", "Mix the [flour] well"],
    ["strikethrough", "Mix the ~~[flour]~~ well", "Mix the [flour] well"],
    ["bold", "Mix **[]**", "Mix []"],
  ])("%s unwraps %s", (kind, input, output) => {
    expect(format(kind, input)).toBe(output);
  });

  test("italic does not take half of a bold marker", () => {
    expect(format("italic", "Mix the **[flour]** well")).toBe("Mix the ***[flour]*** well");
  });

  test("bold does not take an italic marker", () => {
    expect(format("bold", "Mix the *[flour]* well")).toBe("Mix the ***[flour]*** well");
  });

  test("a link selects the URL placeholder", () => {
    expect(format("link", "See [the video]")).toBe("See [the video]([url])");
  });

  test("a selected URL becomes the link target", () => {
    expect(format("link", "See [https://mealie.io]")).toBe("See [[]](https://mealie.io)");
  });
});

describe("markdownShortcut", () => {
  const key = (key: string, modifiers: Partial<KeyboardEvent> = {}) =>
    markdownShortcut({ key, ctrlKey: true, metaKey: false, altKey: false, shiftKey: false, ...modifiers });

  test("maps Ctrl or Cmd with a letter to a format", () => {
    expect(key("b")).toBe("bold");
    expect(key("I")).toBe("italic");
    expect(key("u")).toBe("underline");
    expect(key("k")).toBe("link");
    expect(key("X", { shiftKey: true })).toBe("strikethrough");
    expect(key("b", { ctrlKey: false, metaKey: true })).toBe("bold");
  });

  test("ignores other keys and AltGr", () => {
    expect(key("b", { ctrlKey: false })).toBeNull();
    expect(key("b", { altKey: true })).toBeNull();
    expect(key("c")).toBeNull();
    expect(key("b", { shiftKey: true })).toBeNull();
  });
});
