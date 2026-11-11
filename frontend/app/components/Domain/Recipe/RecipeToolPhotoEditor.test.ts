import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, test, vi } from "vitest";
import RecipeToolPhotoEditor from "./RecipeToolPhotoEditor.vue";

const updateImage = vi.fn();
const deleteImage = vi.fn();

vi.mock("~/composables/api", () => ({
  useUserApi: () => ({ tools: { updateImage, deleteImage } }),
}));

function mountEditor(image: string | null, id: string | null = "t1") {
  return mount(RecipeToolPhotoEditor, {
    props: { tool: { id, name: "Fouet", image } },
    global: {
      mocks: { $globals: { icons: { imageOutline: "image", upload: "upload" } } },
      stubs: {
        VImg: { props: ["src"], template: "<img :src=\"src\">" },
        VSheet: { template: "<div class=\"placeholder\"><slot /></div>" },
        VIcon: { template: "<i><slot /></i>" },
        AppButtonUpload: {
          emits: ["uploaded"],
          setup: (_: unknown, { emit }: { emit: (e: string, file: File) => void }) => ({ pick: () => emit("uploaded", new File(["x"], "a.png")) }),
          template: "<button class=\"upload\" @click=\"pick\" />",
        },
        BaseButton: { emits: ["click"], template: "<button class=\"remove\" @click=\"$emit('click')\"><slot /></button>" },
      },
    },
  });
}

describe("RecipeToolPhotoEditor", () => {
  beforeEach(() => {
    updateImage.mockReset();
    deleteImage.mockReset();
  });

  test("shows a placeholder and no remove button without photo", () => {
    const wrapper = mountEditor(null);

    expect(wrapper.find(".placeholder").exists()).toBe(true);
    expect(wrapper.find("img").exists()).toBe(false);
    expect(wrapper.find(".remove").exists()).toBe(false);
  });

  test("uploads the picked file and emits the updated tool", async () => {
    const updated = { id: "t1", image: "new" };
    updateImage.mockResolvedValue({ data: updated });
    const wrapper = mountEditor(null);

    await wrapper.find(".upload").trigger("click");
    await flushPromises();

    expect(updateImage).toHaveBeenCalledWith("t1", expect.any(File));
    expect(wrapper.emitted("updated")).toEqual([[updated]]);
  });

  test("removes the photo", async () => {
    const updated = { id: "t1", image: null };
    deleteImage.mockResolvedValue({ data: updated });
    const wrapper = mountEditor("key");

    expect(wrapper.find("img").attributes("src")).toBe("/api/media/tools/t1/original.webp?version=key");
    await wrapper.find(".remove").trigger("click");
    await flushPromises();

    expect(deleteImage).toHaveBeenCalledWith("t1");
    expect(wrapper.emitted("updated")).toEqual([[updated]]);
  });

  test("keeps the photo of a tool not created yet instead of uploading it", async () => {
    URL.createObjectURL ??= () => "";
    URL.revokeObjectURL ??= () => {};
    const createObjectURL = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:preview");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    const wrapper = mountEditor(null, null);
    expect(createObjectURL).not.toHaveBeenCalled();

    await wrapper.find(".upload").trigger("click");
    const file = wrapper.emitted("update:file")?.[0]?.[0];
    expect(file).toBeInstanceOf(File);
    expect(updateImage).not.toHaveBeenCalled();

    await wrapper.setProps({ file: file as File });
    expect(wrapper.find("img").attributes("src")).toBe("blob:preview");

    await wrapper.find(".remove").trigger("click");
    expect(wrapper.emitted("update:file")?.[1]).toEqual([null]);
    expect(deleteImage).not.toHaveBeenCalled();
  });
});
