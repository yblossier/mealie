<template>
  <div class="d-flex align-center ga-4">
    <v-img
      v-if="imageUrl"
      :src="imageUrl"
      :alt="tool.name"
      width="96"
      height="96"
      max-width="96"
      cover
      class="rounded flex-grow-0"
    />
    <v-sheet
      v-else
      width="96"
      height="96"
      class="d-flex align-center justify-center rounded"
      color="surface-variant"
    >
      <v-icon size="40">
        {{ $globals.icons.imageOutline }}
      </v-icon>
    </v-sheet>
    <div class="d-flex flex-column ga-2">
      <AppButtonUpload
        :post="false"
        accept="image/*"
        :icon="$globals.icons.upload"
        :text="$t('tool.upload-photo')"
        :disabled="loading"
        @uploaded="upload"
      />
      <BaseButton
        v-if="imageUrl"
        delete
        :loading="loading"
        @click="remove"
      >
        {{ $t("tool.remove-photo") }}
      </BaseButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useUserApi } from "~/composables/api";
import { toolImageUrl } from "~/lib/recipe/tool-display";
import type { ToolOut } from "~/lib/api/types/recipe";

const props = defineProps<{
  /** A tool without id is not created yet: the picked photo is kept until it is */
  tool: Pick<ToolOut, "name" | "image"> & { id?: string | null };
}>();

const emit = defineEmits<{
  (e: "updated", tool: ToolOut): void;
}>();

/** Photo picked for a tool that is not created yet */
const pendingFile = defineModel<File | null>("file", { default: null });

const api = useUserApi();
const loading = ref(false);

const pendingUrl = ref<string | null>(null);
watch(pendingFile, (file) => {
  if (pendingUrl.value) {
    URL.revokeObjectURL(pendingUrl.value);
  }
  pendingUrl.value = file ? URL.createObjectURL(file) : null;
}, { immediate: true });
onBeforeUnmount(() => {
  if (pendingUrl.value) {
    URL.revokeObjectURL(pendingUrl.value);
  }
});

const imageUrl = computed(() => (props.tool.id ? toolImageUrl(props.tool) : pendingUrl.value));

async function upload(file: unknown) {
  if (!(file instanceof File)) {
    return;
  }
  if (!props.tool.id) {
    pendingFile.value = file;
    return;
  }

  loading.value = true;
  const { data } = await api.tools.updateImage(props.tool.id, file);
  loading.value = false;
  if (data) {
    emit("updated", data);
  }
}

async function remove() {
  if (!props.tool.id) {
    pendingFile.value = null;
    return;
  }

  loading.value = true;
  const { data } = await api.tools.deleteImage(props.tool.id);
  loading.value = false;
  if (data) {
    emit("updated", data);
  }
}
</script>
