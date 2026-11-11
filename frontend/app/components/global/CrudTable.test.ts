import { mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, test } from "vitest";
import CrudTable, { type BulkAction } from "./CrudTable.vue";

const wrappers: VueWrapper[] = [];

const items = [{ id: "1", name: "Apple" }, { id: "2", name: "Pear" }];

function mountTable(rowActions: BulkAction[] = [], bulkActions: BulkAction[] = []) {
  const wrapper = mount(CrudTable, {
    props: {
      headers: [{ text: "Name", value: "name", show: true }],
      data: items,
      rowActions,
      bulkActions,
    },
    global: {
      mocks: {
        $globals: { icons: { edit: "edit", delete: "delete", cog: "cog", download: "download" } },
      },
      stubs: {
        VCardActions: { template: "<div><slot /></div>" },
        VTextField: true,
        BaseButton: true,
        BaseOverflowButton: {
          props: ["items"],
          template: "<div class=\"bulk\"><button v-for=\"item in items\" :key=\"item.event\" type=\"button\" :class=\"'bulk-' + item.event\" @click=\"$emit(item.event)\" /></div>",
        },
        VDataTable: {
          props: ["items"],
          template: "<div><div v-for=\"item in items\" :key=\"item.id\" class=\"row\"><slot name=\"item.actions\" :item=\"item\" /></div></div>",
        },
        BaseButtonGroup: {
          props: ["buttons", "size"],
          template: "<div class=\"button-group\" :data-size=\"size\"><button v-for=\"button in buttons\" :key=\"button.event\" type=\"button\" :class=\"'action-' + button.event\" @click=\"$emit(button.event)\" /></div>",
        },
      },
    },
  });

  wrappers.push(wrapper);
  return wrapper;
}

describe("CrudTable", () => {
  afterEach(() => {
    wrappers.forEach(wrapper => wrapper.unmount());
    wrappers.length = 0;
  });

  test("puts the row actions before edit and delete", () => {
    const wrapper = mountTable([{ icon: "foods", text: "View Nutrition", event: "view-nutrition" }]);

    const buttons = wrapper.findAll(".row")[0]!.findAll("button").map(button => button.classes()[0]);
    expect(buttons).toEqual(["action-view-nutrition", "action-edit", "action-delete"]);
  });

  test("keeps the actions on one line, smaller, when there are row actions", () => {
    const group = mountTable([{ icon: "foods", text: "View Nutrition", event: "view-nutrition" }]).get(".button-group");
    expect(group.attributes("data-size")).toBe("small");
    expect(group.classes()).toContain("flex-nowrap");

    const plain = mountTable().get(".button-group");
    expect(plain.attributes("data-size")).toBeUndefined();
    expect(plain.classes()).not.toContain("flex-nowrap");
  });

  test("emits the row action with its item", async () => {
    const wrapper = mountTable([{ icon: "foods", text: "View Nutrition", event: "view-nutrition" }]);

    await wrapper.findAll(".row")[1]!.get(".action-view-nutrition").trigger("click");

    expect(wrapper.emitted("row-action")).toEqual([["view-nutrition", items[1]]]);
    expect(wrapper.emitted("edit-one")).toBeUndefined();
  });

  test("keeps the edit and delete actions without row actions", async () => {
    const wrapper = mountTable();

    await wrapper.findAll(".row")[0]!.get(".action-edit").trigger("click");
    await wrapper.findAll(".row")[0]!.get(".action-delete").trigger("click");

    expect(wrapper.emitted("edit-one")).toEqual([[items[0]]]);
    expect(wrapper.emitted("delete-one")).toEqual([[items[0]]]);
    expect(wrapper.emitted("row-action")).toBeUndefined();
  });

  test("emits the bulk actions, like marking tools on hand", async () => {
    const wrapper = mountTable([], [
      { icon: "check", text: "Mark as On Hand", event: "on-hand-selected" },
      { icon: "close", text: "Mark as Not On Hand", event: "off-hand-selected" },
    ]);

    await wrapper.get(".bulk-off-hand-selected").trigger("click");

    expect(wrapper.emitted("bulk-action")).toEqual([["off-hand-selected", []]]);
  });
});
