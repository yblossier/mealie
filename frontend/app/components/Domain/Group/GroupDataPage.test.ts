import { mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, test } from "vitest";
import { nextTick } from "vue";
import GroupDataPage from "./GroupDataPage.vue";

const wrappers: VueWrapper[] = [];

const item = { id: "1", name: "Apple", nutrition: { calories: "52" } };

function mountPage(slots: Record<string, string> = {}) {
  const wrapper = mount(GroupDataPage, {
    props: {
      icon: "foods",
      title: "Foods",
      data: [item],
      bulkActions: [],
      rowActions: [{ icon: "foods", text: "View Nutrition", event: "view-nutrition" }],
      tableHeaders: [{ text: "Name", value: "name", show: true }],
      createForm: { items: [], data: {} },
      editForm: { items: [], data: {} },
    },
    slots,
    global: {
      mocks: {
        $globals: { icons: { alertCircle: "alert" } },
      },
      stubs: {
        BaseDialog: {
          props: ["modelValue", "title"],
          template: "<div v-if=\"modelValue\" class=\"dialog\" :data-title=\"title\"><slot /></div>",
        },
        AutoForm: { template: "<div class=\"auto-form\" />" },
        BaseCardSectionTitle: true,
        BaseButton: true,
        VCardText: { template: "<div><slot /></div>" },
        CrudTable: {
          props: ["rowActions"],
          emits: ["edit-one", "row-action"],
          template: `
            <div class="table" :data-row-actions="rowActions?.map(a => a.event).join(',')">
              <button type="button" class="edit" @click="$emit('edit-one', ${JSON.stringify(item).replace(/"/g, "'")})" />
              <button type="button" class="row-action" @click="$emit('row-action', 'view-nutrition', ${JSON.stringify(item).replace(/"/g, "'")})" />
            </div>
          `,
        },
      },
    },
  });

  wrappers.push(wrapper);
  return wrapper;
}

describe("GroupDataPage", () => {
  afterEach(() => {
    wrappers.forEach(wrapper => wrapper.unmount());
    wrappers.length = 0;
  });

  test("shows the edit-dialog-bottom slot below the edit form", async () => {
    const wrapper = mountPage({ "edit-dialog-bottom": "<div class=\"bottom\">nutrition</div>" });

    await wrapper.get(".edit").trigger("click");
    await nextTick();

    const dialog = wrapper.findAll(".dialog").find(d => d.find(".auto-form").exists())!;
    const html = dialog.html();
    expect(dialog.find(".bottom").exists()).toBe(true);
    expect(html.indexOf("auto-form")).toBeLessThan(html.indexOf("bottom"));
  });

  test("passes the row actions to the table and forwards their events", async () => {
    const wrapper = mountPage();

    expect(wrapper.get(".table").attributes("data-row-actions")).toBe("view-nutrition");

    await wrapper.get(".row-action").trigger("click");
    expect(wrapper.emitted("row-action")).toEqual([["view-nutrition", item]]);
  });
});
