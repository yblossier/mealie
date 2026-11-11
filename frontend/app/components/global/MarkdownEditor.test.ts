import { mount } from "@vue/test-utils";
import { describe, expect, test } from "vitest";
import MarkdownEditor from "./MarkdownEditor.vue";

function mountEditor(text: string) {
  return mount(MarkdownEditor, {
    props: {
      modelValue: text,
      displayPreview: false,
    },
    global: {
      stubs: {
        VTextarea: {
          props: ["modelValue"],
          emits: ["update:modelValue"],
          template: "<textarea :value=\"modelValue\" @input=\"$emit('update:modelValue', $event.target.value)\" />",
        },
      },
    },
    attachTo: document.body,
  });
}

describe("MarkdownEditor shortcuts", () => {
  test("Ctrl+B makes the selection bold", async () => {
    const wrapper = mountEditor("Mix the flour");
    const textarea = wrapper.find("textarea").element as HTMLTextAreaElement;
    textarea.setSelectionRange(8, 13);

    await wrapper.find("textarea").trigger("keydown", { key: "b", ctrlKey: true });

    expect(wrapper.emitted("update:modelValue")!.at(-1)).toEqual(["Mix the **flour**"]);
    expect([textarea.selectionStart, textarea.selectionEnd]).toEqual([10, 15]);
    wrapper.unmount();
  });

  test("leaves other keys alone", async () => {
    const wrapper = mountEditor("Mix the flour");

    await wrapper.find("textarea").trigger("keydown", { key: "c", ctrlKey: true });

    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
    wrapper.unmount();
  });
});
