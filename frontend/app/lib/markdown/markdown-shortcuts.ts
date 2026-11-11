export interface MarkdownMarker {
  open: string;
  close: string;
}

export const MARKDOWN_MARKERS = {
  bold: { open: "**", close: "**" },
  italic: { open: "*", close: "*" },
  underline: { open: "<u>", close: "</u>" },
  strikethrough: { open: "~~", close: "~~" },
} satisfies Record<string, MarkdownMarker>;

export type MarkdownFormat = keyof typeof MARKDOWN_MARKERS | "link";

/** Replace `text[from, to)` with `insert`, then select `[selectionStart, selectionEnd)` in the new text. */
export interface MarkdownEdit {
  from: number;
  to: number;
  insert: string;
  selectionStart: number;
  selectionEnd: number;
}

function leadingRun(text: string, char: string): number {
  let count = 0;
  while (text[count] === char) count++;
  return count;
}

function trailingRun(text: string, char: string): number {
  let count = 0;
  while (text[text.length - 1 - count] === char) count++;
  return count;
}

/** The character a marker repeats, such as `*` for `**`, or null for a marker like `<u>`. */
function repeatedChar(marker: MarkdownMarker): string | null {
  const char = marker.open[0]!;
  return marker.open === marker.close && [...marker.open].every(c => c === char) ? char : null;
}

/**
 * Whether a run of `run` marker characters on both sides holds the marker.
 * Asterisks are counted so that italic is not mistaken for half of a bold marker:
 * `**word**` is bold but not italic, `***word***` is both.
 */
function runHoldsMarker(run: number, marker: MarkdownMarker): boolean {
  return marker.open.length === 1 ? run % 2 === 1 : run >= marker.open.length;
}

function isWrappedOutside(before: string, after: string, marker: MarkdownMarker): boolean {
  const char = repeatedChar(marker);
  if (!char) {
    return before.endsWith(marker.open) && after.startsWith(marker.close);
  }
  return runHoldsMarker(Math.min(trailingRun(before, char), leadingRun(after, char)), marker);
}

function isWrappedInside(selected: string, marker: MarkdownMarker): boolean {
  if (selected.length < marker.open.length + marker.close.length) {
    return false;
  }
  const char = repeatedChar(marker);
  if (!char) {
    return selected.startsWith(marker.open) && selected.endsWith(marker.close);
  }
  if (leadingRun(selected, char) === selected.length) {
    return false;
  }
  return runHoldsMarker(Math.min(leadingRun(selected, char), trailingRun(selected, char)), marker);
}

/**
 * Wraps the selection in a marker, or unwraps it when the marker already surrounds it,
 * whether the markers are just outside the selection or part of it.
 * Whitespace at the edges of the selection stays outside, as a double-click often selects it.
 */
export function toggleMarkdownMarker(text: string, start: number, end: number, marker: MarkdownMarker): MarkdownEdit {
  while (start < end && /\s/.test(text[start]!)) start++;
  while (end > start && /\s/.test(text[end - 1]!)) end--;

  const selected = text.slice(start, end);
  const { open, close } = marker;

  if (isWrappedOutside(text.slice(0, start), text.slice(end), marker)) {
    return {
      from: start - open.length,
      to: end + close.length,
      insert: selected,
      selectionStart: start - open.length,
      selectionEnd: end - open.length,
    };
  }

  if (isWrappedInside(selected, marker)) {
    const inner = selected.slice(open.length, selected.length - close.length);
    return { from: start, to: end, insert: inner, selectionStart: start, selectionEnd: start + inner.length };
  }

  return {
    from: start,
    to: end,
    insert: `${open}${selected}${close}`,
    selectionStart: start + open.length,
    selectionEnd: end + open.length,
  };
}

/**
 * Turns the selection into a link. A selected URL becomes the target, with the cursor in the label;
 * other text becomes the label, with a `url` placeholder selected to type over.
 */
export function insertMarkdownLink(text: string, start: number, end: number): MarkdownEdit {
  const selected = text.slice(start, end);
  if (/^https?:\/\/\S+$/.test(selected)) {
    return { from: start, to: end, insert: `[](${selected})`, selectionStart: start + 1, selectionEnd: start + 1 };
  }

  const urlStart = start + selected.length + 3;
  return { from: start, to: end, insert: `[${selected}](url)`, selectionStart: urlStart, selectionEnd: urlStart + 3 };
}

export function markdownEdit(format: MarkdownFormat, text: string, start: number, end: number): MarkdownEdit {
  return format === "link"
    ? insertMarkdownLink(text, start, end)
    : toggleMarkdownMarker(text, start, end, MARKDOWN_MARKERS[format]);
}

const SHORTCUT_KEYS: Record<string, MarkdownFormat> = { b: "bold", i: "italic", u: "underline", k: "link" };

type ShortcutEvent = Pick<KeyboardEvent, "key" | "ctrlKey" | "metaKey" | "altKey" | "shiftKey">;

/** The format bound to a key press: Ctrl/⌘ + B, I, U, K, and Ctrl/⌘ + Shift + X. */
export function markdownShortcut(event: ShortcutEvent): MarkdownFormat | null {
  // AltGr is reported as Ctrl + Alt on Windows, and types characters rather than shortcuts.
  if (!(event.ctrlKey || event.metaKey) || event.altKey) {
    return null;
  }

  const key = event.key.toLowerCase();
  if (event.shiftKey) {
    return key === "x" ? "strikethrough" : null;
  }
  return SHORTCUT_KEYS[key] ?? null;
}

/**
 * Applies a format to a textarea. `insertText` keeps the change in the browser's undo history;
 * the fallback, for browsers without it, still fires `input` so v-model sees the change.
 */
export function applyMarkdownFormat(textarea: HTMLTextAreaElement, format: MarkdownFormat): void {
  const edit = markdownEdit(format, textarea.value, textarea.selectionStart, textarea.selectionEnd);

  textarea.focus();
  textarea.setSelectionRange(edit.from, edit.to);
  const command = edit.insert ? "insertText" : "delete";
  const done = typeof document.execCommand === "function" && document.execCommand(command, false, edit.insert);
  if (!done) {
    textarea.setRangeText(edit.insert, edit.from, edit.to);
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
  }
  textarea.setSelectionRange(edit.selectionStart, edit.selectionEnd);
}
