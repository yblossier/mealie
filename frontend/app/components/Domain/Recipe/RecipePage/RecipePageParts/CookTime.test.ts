import { mount } from "@vue/test-utils";
import { createI18n } from "vue-i18n";
import { afterEach, describe, expect, it } from "vitest";
import { createVuetify } from "vuetify";
import * as components from "vuetify/components";
import messages from "@/lang/messages/en-US.json";
import BaseDurationPicker from "~/components/global/BaseDurationPicker.vue";
import CookTime from "./CookTime.vue";

const BaseButton = {
  props: ["cancel"],
  emits: ["click"],
  template: `<button type="button" @click="$emit('click')"><slot /></button>`,
};

// Renders the dialog content in place, without Vuetify's overlay positioning
const InlineDialog = {
  props: ["modelValue"],
  template: `<div v-if="modelValue"><slot /></div>`,
};

function mountCookTime(value: number | null = null, isEditMode = true) {
  return mount(CookTime, {
    props: { modelValue: value, isEditMode },
    attachTo: document.body,
    global: {
      plugins: [
        createVuetify({ components }),
        createI18n({ legacy: false, locale: "en-US", messages: { "en-US": messages } }),
      ],
      components: { BaseDurationPicker, BaseButton },
      stubs: { VDialog: InlineDialog, VBottomSheet: InlineDialog },
      mocks: { $globals: { icons: { clockOutline: "clock", check: "check", keyboard: "keyboard" } } },
    },
  });
}

function body(testId: string) {
  return document.body.querySelector<HTMLElement>(`[data-testid="${testId}"]`);
}

async function openPicker(wrapper: ReturnType<typeof mountCookTime>) {
  await wrapper.find("input").trigger("click");
  await new Promise(resolve => setTimeout(resolve, 0));
  await wrapper.vm.$nextTick();
}

afterEach(() => {
  document.body.replaceChildren();
});

describe("step duration with the duration picker", () => {
  it("shows a blank read-only field without emitting a duration", () => {
    const wrapper = mountCookTime();
    expect(wrapper.find("input").element.value).toBe("");
    expect(wrapper.find("input").attributes("readonly")).toBeDefined();
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
    wrapper.unmount();
  });

  it("displays the saved duration in words", () => {
    const wrapper = mountCookTime(5400);
    expect(wrapper.find("input").element.value).toBe("1 hour 30 minutes");
    wrapper.unmount();
  });

  it("emits the picked preset in seconds once confirmed", async () => {
    const wrapper = mountCookTime();
    await openPicker(wrapper);
    body("duration-preset-90")!.click();
    await wrapper.vm.$nextTick();
    expect(body("duration-picker-preview")!.textContent).toContain("1 hour 30 minutes");
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
    body("duration-picker-confirm")!.click();
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual([5400]);
    wrapper.unmount();
  });

  it("keeps the value when cancelled", async () => {
    const wrapper = mountCookTime(600);
    await openPicker(wrapper);
    body("duration-preset-30")!.click();
    body("duration-picker-cancel")!.click();
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
    wrapper.unmount();
  });

  it("preserves imported seconds while hours and minutes are unchanged", async () => {
    const wrapper = mountCookTime(3661);
    await openPicker(wrapper);
    body("duration-picker-confirm")!.click();
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
    wrapper.unmount();
  });

  it("labels the presets with short durations", async () => {
    const wrapper = mountCookTime();
    await openPicker(wrapper);
    expect(body("duration-preset-5")!.textContent!.trim()).toBe("5min");
    expect(body("duration-preset-60")!.textContent!.trim()).toBe("1h");
    expect(body("duration-preset-90")!.textContent!.trim()).toBe("1h30");
    expect(body("duration-preset-120")!.textContent!.trim()).toBe("2h");
    wrapper.unmount();
  });

  it("colours the icon outside the underline once a duration is set", () => {
    const empty = mountCookTime();
    expect(empty.find(".v-input__prepend [data-testid='duration-picker-icon']").exists()).toBe(true);
    expect(empty.find("[data-testid='duration-picker-icon']").classes()).not.toContain("text-primary");
    empty.unmount();

    const filled = mountCookTime(600);
    expect(filled.find("[data-testid='duration-picker-icon']").classes()).toContain("text-primary");
    filled.unmount();
  });

  it("shows the hours and minutes boxes and accepts typed values", async () => {
    const wrapper = mountCookTime(5400);
    await openPicker(wrapper);
    expect(body("duration-hours")!.textContent!.trim()).toBe("01");
    expect(body("duration-minutes")!.textContent!.trim()).toBe("30");

    body("duration-picker-mode")!.click();
    await wrapper.vm.$nextTick();
    const hours = body("duration-hours") as HTMLInputElement;
    hours.value = "2";
    hours.dispatchEvent(new Event("input"));
    const minutes = body("duration-minutes") as HTMLInputElement;
    minutes.value = "75";
    minutes.dispatchEvent(new Event("input"));
    await wrapper.vm.$nextTick();
    expect(minutes.value).toBe("59");

    body("duration-picker-confirm")!.click();
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual([2 * 3600 + 59 * 60]);
    wrapper.unmount();
  });

  it("clears the duration", async () => {
    const wrapper = mountCookTime(600);
    await wrapper.find(".v-field__clearable .v-icon").trigger("click");
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual([null]);
    wrapper.unmount();
  });

  it.each([[3661, "1h 1m 1s"], [90, "1m 30s"], [60, "1m"], [30, "30s"], [null, ""]] as const)(
    "displays %s with units outside edit mode",
    (value, text) => {
      const wrapper = mountCookTime(value, false);
      expect(wrapper.text()).toBe(text);
      expect(wrapper.findAll("input")).toHaveLength(0);
      wrapper.unmount();
    },
  );
});
