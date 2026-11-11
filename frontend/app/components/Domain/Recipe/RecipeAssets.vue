<template>
  <div v-if="model.length > 0 || edit">
    <v-card
      class="mt-4"
      @dragenter.prevent="onDragEnter"
      @dragover.prevent="onDragOver"
      @dragleave="onDragLeave"
      @drop.prevent="onDrop"
    >
      <v-list-item class="pr-2 pl-0">
        <v-card-title>
          {{ $t("asset.assets") }}
        </v-card-title>
        <template #append>
          <v-btn
            v-if="edit"
            variant="plain"
            :icon="$globals.icons.create"
            @click="state.newAssetDialog = true"
          />
        </template>
      </v-list-item>
      <v-divider class="mx-2" />
      <div
        v-if="edit"
        class="asset-drop-zone ma-2 pa-3 d-flex align-center justify-center text-center text-body-2"
        :class="{ 'asset-drop-zone--active': dropping }"
        data-testid="asset-drop-zone"
      >
        <v-progress-circular
          v-if="uploadingCount > 0"
          indeterminate
          size="20"
          width="2"
          color="primary"
          class="mr-2"
        />
        <v-icon
          v-else
          class="mr-2"
          :color="dropping ? 'primary' : undefined"
        >
          {{ $globals.icons.upload }}
        </v-icon>
        {{ $t("asset.drop-files-here") }}
      </div>
      <v-list
        v-if="model.length > 0"
        lines="two"
        :flat="!edit"
      >
        <v-list-item
          v-for="(item, i) in model"
          :key="i"
          :href="!edit && !isImage(item.fileName) ? assetURL(item.fileName ?? '') : undefined"
          :target="!edit && !isImage(item.fileName) ? '_blank' : undefined"
          class="pr-2"
          @click="handleRowClick($event, item)"
        >
          <template #prepend>
            <v-avatar size="48" rounded="lg" class="elevation-1">
              <v-img
                v-if="isImage(item.fileName)"
                :src="assetURL(item.fileName ?? '')"
                :alt="item.name"
                loading="lazy"
                cover
              />
              <v-icon v-else size="large">
                {{ getIconDefinition(item.icon).icon }}
              </v-icon>
            </v-avatar>
          </template>

          <v-list-item-title>
            {{ item.name }}
          </v-list-item-title>
          <template #append>
            <v-menu v-if="edit" location="bottom end">
              <template #activator="{ props: menuProps }">
                <v-btn
                  v-bind="menuProps"
                  icon
                  variant="plain"
                >
                  <v-icon :icon="$globals.icons.dotsVertical" />
                </v-btn>
              </template>
              <v-list density="compact" min-width="220">
                <v-list-item
                  :href="!isImage(item.fileName) ? assetURL(item.fileName ?? '') : undefined"
                  :target="!isImage(item.fileName) ? '_blank' : undefined"
                  :prepend-icon="$globals.icons.eye"
                  :title="$t('general.view')"
                  @click="handleViewClick($event, item)"
                />
                <v-list-item
                  :href="assetURL(item.fileName ?? '')"
                  :prepend-icon="$globals.icons.download"
                  :title="$t('general.download')"
                  download
                  @click.stop
                />
                <v-list-item
                  v-if="edit"
                  :prepend-icon="$globals.icons.contentCopy"
                  :title="$t('general.copy')"
                  @click="copyText(assetEmbed(item.fileName ?? ''))"
                />
                <v-list-item
                  v-if="edit"
                  :prepend-icon="$globals.icons.delete"
                  :title="$t('general.delete')"
                  @click="model.splice(i, 1)"
                />
              </v-list>
            </v-menu>
            <v-btn
              v-if="!edit"
              icon
              variant="plain"
              :href="assetURL(item.fileName ?? '')"
              download
              @click.stop
            >
              <v-icon> {{ $globals.icons.download }} </v-icon>
            </v-btn>
          </template>
        </v-list-item>
      </v-list>
    </v-card>
    <RecipeImageLightbox
      v-if="lightbox.open"
      v-model="lightbox.open"
      v-model:index="lightbox.index"
      :items="lightboxItems"
    />
    <div class="d-flex ml-auto mt-2">
      <v-spacer />
      <BaseDialog
        v-model="state.newAssetDialog"
        :title="$t('asset.new-asset')"
        :icon="getIconDefinition(state.newAsset.icon).icon"
        can-submit
        @submit="addAsset"
      >
        <v-card-text class="pt-4">
          <v-text-field
            v-model="state.newAsset.name"
            :label="$t('general.name')"
          />
          <div class="d-flex justify-space-between">
            <v-select
              v-model="state.newAsset.icon"
              density="compact"
              :prepend-icon="getIconDefinition(state.newAsset.icon).icon"
              :items="iconOptions"
              item-title="title"
              item-value="name"
              class="mr-2"
            >
              <template #item="{ props: itemProps, item }">
                <v-list-item v-bind="itemProps">
                  <template #prepend>
                    <v-avatar>
                      <v-icon>
                        {{ item.icon }}
                      </v-icon>
                    </v-avatar>
                  </template>
                </v-list-item>
              </template>
            </v-select>
            <AppButtonUpload
              :post="false"
              file-name="file"
              :text-btn="false"
              @uploaded="setFileObject"
            />
          </div>
        </v-card-text>
      </BaseDialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useStaticRoutes, useUserApi } from "~/composables/api";
import { alert } from "~/composables/use-toast";
import type { RecipeAsset } from "~/lib/api/types/recipe";
import { useCopy } from "~/composables/use-copy";
import { isImage, useRecipeLightboxItems, findLightboxStartIndex } from "~/composables/recipe-page/use-recipe-lightbox-items";

const props = defineProps({
  slug: {
    type: String,
    required: true,
  },
  recipeId: {
    type: String,
    required: true,
  },
  edit: {
    type: Boolean,
    default: true,
  },
  // Optional so the lightbox can open a gallery that includes the recipe's hero image
  // ahead of the asset list; omit when the caller has no hero to show (or doesn't care).
  heroImageUrl: {
    type: String,
    default: undefined,
  },
  heroImageAlt: {
    type: String,
    default: undefined,
  },
});

const model = defineModel<RecipeAsset[]>({ required: true });

const api = useUserApi();

const state = reactive({
  newAssetDialog: false,
  fileObject: {} as File,
  newAsset: {
    name: "",
    icon: "mdi-file",
  },
});

const i18n = useI18n();
const { $globals } = useNuxtApp();
const { copyText } = useCopy();

const iconOptions = [
  {
    name: "mdi-file",
    title: i18n.t("asset.file"),
    icon: $globals.icons.file,
  },
  {
    name: "mdi-file-pdf-box",
    title: i18n.t("asset.pdf"),
    icon: $globals.icons.filePDF,
  },
  {
    name: "mdi-file-image",
    title: i18n.t("asset.image"),
    icon: $globals.icons.fileImage,
  },
  {
    name: "mdi-code-json",
    title: i18n.t("asset.code"),
    icon: $globals.icons.codeJson,
  },
  {
    name: "mdi-silverware-fork-knife",
    title: i18n.t("asset.recipe"),
    icon: $globals.icons.primary,
  },
];

const serverBase = useRequestURL().origin;

function getIconDefinition(icon: string) {
  return iconOptions.find(item => item.name === icon) || iconOptions[0];
}

const { buildItems } = useRecipeLightboxItems();
const lightboxItems = computed(() => buildItems(props.recipeId, {
  heroUrl: props.heroImageUrl,
  heroAlt: props.heroImageAlt,
  assets: model.value,
}));

const lightbox = reactive({
  open: false,
  index: 0,
});

function openLightbox(item: RecipeAsset) {
  lightbox.index = findLightboxStartIndex(lightboxItems.value, assetURL(item.fileName ?? ""));
  lightbox.open = true;
}

function handleViewClick(event: Event, item: RecipeAsset) {
  if (!isImage(item.fileName)) {
    return;
  }

  event.preventDefault();
  openLightbox(item);
}

// The row itself only opens the lightbox outside edit mode; the menu's view action
// (which exists only while editing) goes straight to handleViewClick.
function handleRowClick(event: Event, item: RecipeAsset) {
  if (props.edit) {
    return;
  }

  handleViewClick(event, item);
}

const { recipeAssetPath } = useStaticRoutes();
function assetURL(assetName: string) {
  return recipeAssetPath(props.recipeId, assetName);
}

function assetEmbed(name: string) {
  return `<img src="${serverBase}${assetURL(name)}" height="100%" width="100%" />`;
}

function setFileObject(fileObject: File) {
  state.fileObject = fileObject;
  // If the user didn't provide a name, default to the file base name
  if (!state.newAsset.name?.trim()) {
    state.newAsset.name = fileObject.name.substring(0, fileObject.name.lastIndexOf("."));
  }
}

function validFields() {
  // Only require a file; name will fall back to the file name if empty
  return Boolean(state.fileObject?.name);
}

async function addAsset() {
  if (!validFields()) {
    alert.error(i18n.t("asset.error-submitting-form") as string);
    return;
  }

  const nameToUse = state.newAsset.name?.trim() || state.fileObject.name;

  const { data } = await api.recipes.createAsset(props.slug, {
    name: nameToUse,
    icon: state.newAsset.icon,
    file: state.fileObject,
    extension: state.fileObject.name.split(".").pop() || "",
  });
  if (data) {
    model.value = [...model.value, data];
  }
  state.newAsset = { name: "", icon: "mdi-file" };
  state.fileObject = {} as File;
}

// dropping files on the block uploads them straight away, the type being deduced from the file
const DROPPABLE_ASSET_ICONS: Record<string, string> = {
  png: "mdi-file-image",
  jpg: "mdi-file-image",
  jpeg: "mdi-file-image",
  gif: "mdi-file-image",
  webp: "mdi-file-image",
  bmp: "mdi-file-image",
  avif: "mdi-file-image",
  txt: "mdi-file",
  doc: "mdi-file",
  docx: "mdi-file",
  pdf: "mdi-file-pdf-box",
};

const dropping = ref(false);
const uploadingCount = ref(0);
let dragDepth = 0;

function hasFiles(event: DragEvent) {
  return Array.from(event.dataTransfer?.types ?? []).includes("Files");
}

function onDragEnter(event: DragEvent) {
  if (!props.edit || !hasFiles(event)) {
    return;
  }
  dragDepth++;
  dropping.value = true;
}

function onDragOver(event: DragEvent) {
  if (props.edit && hasFiles(event) && event.dataTransfer) {
    event.dataTransfer.dropEffect = "copy";
  }
}

function onDragLeave() {
  if (!dropping.value) {
    return;
  }
  dragDepth = Math.max(0, dragDepth - 1);
  if (dragDepth === 0) {
    dropping.value = false;
  }
}

async function onDrop(event: DragEvent) {
  dragDepth = 0;
  dropping.value = false;
  if (!props.edit) {
    return;
  }

  const files = Array.from(event.dataTransfer?.files ?? []);
  const rejected: string[] = [];
  for (const file of files) {
    const extension = file.name.split(".").pop()?.toLowerCase() ?? "";
    const icon = DROPPABLE_ASSET_ICONS[extension];
    if (!icon) {
      rejected.push(file.name);
      continue;
    }

    uploadingCount.value++;
    try {
      const dot = file.name.lastIndexOf(".");
      const { data } = await api.recipes.createAsset(props.slug, {
        name: dot > 0 ? file.name.substring(0, dot) : file.name,
        icon,
        file,
        extension,
      });
      if (data) {
        model.value = [...model.value, data];
      }
    }
    finally {
      uploadingCount.value--;
    }
  }

  if (rejected.length) {
    alert.warning(i18n.t("asset.unsupported-dropped-files", { files: rejected.join(", ") }));
  }
}
</script>

<style scoped>
.asset-drop-zone {
  border: 2px dashed rgba(var(--v-border-color), 0.3);
  border-radius: 8px;
  color: rgba(var(--v-theme-on-surface), 0.6);
  transition:
    border-color 0.15s,
    background-color 0.15s;
}

.asset-drop-zone--active {
  border-color: rgb(var(--v-theme-primary));
  background-color: rgba(var(--v-theme-primary), 0.08);
  color: rgb(var(--v-theme-primary));
}
</style>
