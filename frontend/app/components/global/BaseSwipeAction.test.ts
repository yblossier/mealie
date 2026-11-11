import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { ref } from "vue";
import { createVuetify } from "vuetify";
import * as components from "vuetify/components";
import BaseSwipeAction from "./BaseSwipeAction.vue";

const mdAndDown = ref(true);

vi.mock("vuetify", async (importOriginal) => {
  const actual = await importOriginal<typeof import("vuetify")>();
  return { ...actual, useDisplay: () => ({ mdAndDown }) };
});

const WIDTH = 360;

function pointer(type: string, init: { x: number; y?: number; pointerType?: string; target?: Element }) {
  const event = new Event(type, { bubbles: true, cancelable: true });
  Object.assign(event, {
    clientX: init.x,
    clientY: init.y ?? 0,
    pointerId: 1,
    pointerType: init.pointerType ?? "touch",
  });
  (init.target ?? document.body).dispatchEvent(event);
}

function mountSwipe(props: Record<string, unknown> = {}) {
  const wrapper = mount(BaseSwipeAction, {
    attachTo: document.body,
    props: {
      leftAction: { icon: "delete", label: "Delete", color: "error" },
      rightAction: { icon: "link", label: "Link references" },
      ...props,
    },
    slots: { default: "<div class=\"row\"><span class=\"handle\">h</span><span class=\"text\">row</span></div>" },
    global: { plugins: [createVuetify({ components })] },
  });
  Object.defineProperty(wrapper.element, "offsetWidth", { configurable: true, value: WIDTH });
  return wrapper;
}

async function swipe(wrapper: ReturnType<typeof mountSwipe>, dx: number, opts: { dy?: number; pointerType?: string; selector?: string } = {}) {
  const target = wrapper.find(opts.selector ?? ".text").element;
  pointer("pointerdown", { x: 200, y: 100, pointerType: opts.pointerType, target });
  pointer("pointermove", { x: 200 + dx / 2, y: 100 + (opts.dy ?? 0) / 2, pointerType: opts.pointerType, target });
  pointer("pointermove", { x: 200 + dx, y: 100 + (opts.dy ?? 0), pointerType: opts.pointerType, target });
  await wrapper.vm.$nextTick();
  pointer("pointerup", { x: 200 + dx, y: 100 + (opts.dy ?? 0), pointerType: opts.pointerType, target });
  await wrapper.vm.$nextTick();
}

function contentTransform(wrapper: ReturnType<typeof mountSwipe>) {
  return (wrapper.find(".base-swipe-action__content").element as HTMLElement).style.transform;
}

describe("BaseSwipeAction", () => {
  beforeEach(() => {
    mdAndDown.value = true;
  });

  test("a long left swipe emits swipe-left and animates back", async () => {
    const wrapper = mountSwipe();
    await swipe(wrapper, -250);
    expect(wrapper.emitted("swipe-left")).toHaveLength(1);
    expect(wrapper.emitted("swipe-right")).toBeUndefined();
    expect(contentTransform(wrapper)).toBe("");
    wrapper.unmount();
  });

  test("a long right swipe emits swipe-right", async () => {
    const wrapper = mountSwipe();
    await swipe(wrapper, 250);
    expect(wrapper.emitted("swipe-right")).toHaveLength(1);
    wrapper.unmount();
  });

  test("a medium swipe reveals the action, which runs on tap", async () => {
    const wrapper = mountSwipe();
    await swipe(wrapper, -80);
    expect(wrapper.emitted("swipe-left")).toBeUndefined();
    expect(contentTransform(wrapper)).toBe("translateX(-88px)");

    const button = wrapper.find("[data-testid='swipe-action-left']");
    expect(button.attributes("aria-label")).toBe("Delete");
    await button.trigger("click");
    expect(wrapper.emitted("swipe-left")).toHaveLength(1);
    expect(contentTransform(wrapper)).toBe("");
    wrapper.unmount();
  });

  test("a vertical move is left to the scroll", async () => {
    const wrapper = mountSwipe();
    await swipe(wrapper, 5, { dy: 200 });
    expect(wrapper.emitted("swipe-left")).toBeUndefined();
    expect(wrapper.emitted("swipe-right")).toBeUndefined();
    expect(contentTransform(wrapper)).toBe("");
    wrapper.unmount();
  });

  test("ignores mouse pointers", async () => {
    const wrapper = mountSwipe();
    await swipe(wrapper, -250, { pointerType: "mouse" });
    expect(wrapper.emitted("swipe-left")).toBeUndefined();
    wrapper.unmount();
  });

  test("ignores touches starting on the drag handle", async () => {
    const wrapper = mountSwipe();
    await swipe(wrapper, -250, { selector: ".handle" });
    expect(wrapper.emitted("swipe-left")).toBeUndefined();
    wrapper.unmount();
  });

  test("does nothing on large screens or when disabled", async () => {
    mdAndDown.value = false;
    const desktop = mountSwipe();
    await swipe(desktop, -250);
    expect(desktop.emitted("swipe-left")).toBeUndefined();
    desktop.unmount();

    mdAndDown.value = true;
    const disabled = mountSwipe({ disabled: true });
    await swipe(disabled, -250);
    expect(disabled.emitted("swipe-left")).toBeUndefined();
    disabled.unmount();
  });

  test("a side without an action does not move", async () => {
    const wrapper = mountSwipe({ rightAction: null });
    await swipe(wrapper, 250);
    expect(wrapper.emitted("swipe-right")).toBeUndefined();
    expect(contentTransform(wrapper)).toBe("");
    wrapper.unmount();
  });
});
