<template>
  <div>
    <!-- Merge Dialog -->
    <BaseDialog
      v-model="mergeDialog"
      :icon="$globals.icons.tools"
      :title="$t('data-pages.tools.combine-tool')"
      can-confirm
      @confirm="mergeTools"
      @close="resetMergeDialog"
    >
      <v-card-text>
        <div>
          {{ $t("data-pages.tools.merge-dialog-text") }}
        </div>
        <v-autocomplete
          v-model="fromTool"
          return-object
          :items="tools"
          :custom-filter="normalizeFilter"
          item-title="name"
          :label="$t('data-pages.tools.source-tool')"
        />
        <v-autocomplete
          v-model="toTool"
          return-object
          :items="tools"
          :custom-filter="normalizeFilter"
          item-title="name"
          :label="$t('data-pages.tools.target-tool')"
        />

        <template v-if="canMerge && fromTool && toTool">
          <div class="text-center">
            {{ $t("data-pages.tools.merge-tool-example", { tool1: fromTool.name, tool2: toTool.name }) }}
          </div>
        </template>
      </v-card-text>
    </BaseDialog>

    <!-- Delete Unused Dialog -->
    <BaseDialog
      v-model="deleteUnusedDialog"
      :title="$t('general.confirm')"
      :icon="$globals.icons.alertCircle"
      color="error"
      can-confirm
      @confirm="confirmDeleteUnused"
    >
      <v-card-text>
        {{ $t('data-pages.tools.delete-unused-confirm', { count: unusedToolIds.length }, unusedToolIds.length) }}
        <ul style="margin: 0.5rem 0 0; padding-left: 1.25rem; font-size: 0.85rem; color: rgba(var(--v-theme-on-surface), 0.7); line-height: 1.8;">
          <li v-for="name in unusedToolNamesPreview" :key="name">
            {{ name }}
          </li>
        </ul>
        <div v-if="unusedToolNamesRemaining > 0" class="text-body-2 pl-2">
          {{ $t('data-pages.delete-unused-more', { count: unusedToolNamesRemaining }) }}
        </div>
      </v-card-text>
    </BaseDialog>

    <GroupDataPage
      :items-per-page="tablePageSize"
      :icon="$globals.icons.tools"
      :title="$t('data-pages.tools.tool-data')"
      :create-title="$t('data-pages.tools.new-tool')"
      :edit-title="$t('data-pages.tools.edit-tool')"
      :table-headers="tableHeaders"
      :table-config="tableConfig"
      :data="tools || []"
      :bulk-actions="bulkActions"
      :row-actions="rowActions"
      :create-form="createForm"
      :edit-form="editForm"
      @create-one="handleCreate"
      @edit-one="handleEdit"
      @delete-one="toolStore.actions.deleteOne"
      @bulk-action="handleBulkAction"
      @row-action="handleRowAction"
    >
      <template #create-dialog-bottom>
        <RecipeToolDetailsFields v-model="createForm.data" :tools="tools" />
        <div class="text-subtitle-2 mb-2">
          {{ $t("tool.photo") }}
        </div>
        <RecipeToolPhotoEditor
          v-model:file="createPhoto"
          :tool="{ name: createForm.data.name, image: null }"
          class="mb-4"
        />
      </template>

      <template #edit-dialog-bottom>
        <RecipeToolDetailsFields v-model="editForm.data" :tools="tools" :tool-id="editForm.data.id" />
        <div class="text-subtitle-2 mb-2">
          {{ $t("tool.photo") }}
        </div>
        <RecipeToolPhotoEditor
          v-if="editForm.data.id"
          :tool="editForm.data"
          class="mb-4"
          @updated="handlePhotoUpdated"
        />
      </template>

      <template #[`item.category`]="{ item }">
        <span class="text-no-wrap">
          <v-icon class="me-2">
            {{ toolCategoryIcon(item.category) }}
          </v-icon>
          {{ $t(`tool.category-${item.category || "utensils"}`) }}
        </span>
      </template>

      <template #[`item.details`]="{ item }">
        <template v-if="item.category === 'dishes'">
          <div v-if="dishSizeLabel(item)">
            {{ dishSizeLabel(item) }}
          </div>
          <div v-if="item.usages?.length" class="text-caption text-medium-emphasis">
            {{ item.usages.map(usage => $t(`tool.usage-${usage}`)).join(", ") }}
          </div>
        </template>
        <span v-else-if="item.parentId && toolNames[item.parentId]">
          {{ $t("tool.accessory-of") }} {{ toolNames[item.parentId] }}
        </span>
      </template>

      <template #[`item.image`]="{ item }">
        <v-avatar v-if="toolImageUrl(item)" size="32" rounded>
          <v-img :src="toolImageUrl(item)!" :alt="item.name" cover />
        </v-avatar>
      </template>

      <template #[`item.recipeCount`]="{ item }">
        <GroupDataRecipeCount
          :count="item.recipeCount || 0"
          :to="groupSlug ? `/g/${groupSlug}?tools=${item.id}` : null"
        />
      </template>

      <template #[`item.onHand`]="{ item }">
        <v-icon :color="item.onHand ? 'success' : 'error'">
          {{ item.onHand ? $globals.icons.check : $globals.icons.close }}
        </v-icon>
      </template>

      <template #table-button-row>
        <BaseButton @click="mergeDialog = true">
          <template #icon>
            {{ $globals.icons.externalLink }}
          </template>
          {{ $t("data-pages.combine") }}
        </BaseButton>

        <v-divider vertical class="mx-2" />

        <BaseButton color="error" :loading="loadingEmpty" @click="openDeleteUnusedDialog">
          <template #icon>
            {{ $globals.icons.broom }}
          </template>
          {{ $t("data-pages.delete-unused") }}
        </BaseButton>
      </template>
    </GroupDataPage>
  </div>
</template>

<script setup lang="ts">
import type { RecipeToolWithOnHand } from "~/composables/store/use-tool-store";
import { validators } from "~/composables/use-validators";
import { fieldTypes } from "~/composables/forms";
import { normalizeFilter } from "~/composables/use-utils";
import { alert } from "~/composables/use-toast";
import { toolOnHandUpdates } from "~/lib/recipe/tool-on-hand";
import type { AutoFormItems } from "~/types/auto-forms";
import { amazonSearchUrl, DEFAULT_TOOL_CATEGORY, dishSizeLabel, toolCategoryIcon, toolFormPayload, toolImageUrl } from "~/lib/recipe/tool-display";
import RecipeToolDetailsFields from "~/components/Domain/Recipe/RecipeToolDetailsFields.vue";
import RecipeToolPhotoEditor from "~/components/Domain/Recipe/RecipeToolPhotoEditor.vue";
import GroupDataRecipeCount from "~/components/Domain/Group/GroupDataRecipeCount.vue";
import { useToolStore } from "~/composables/store";
import { useUserApi } from "~/composables/api";
import type { ToolOut, ToolCreate } from "~/lib/api/types/recipe";
import type { TableHeaders, TableConfig, BulkAction } from "~/components/global/CrudTable.vue";
import { useTablePageSize } from "~/composables/use-table-page-size";

const tablePageSize = useTablePageSize();

const i18n = useI18n();
const auth = useMealieAuth();
const groupSlug = computed(() => auth.user.value?.groupSlug || "");
const userApi = useUserApi();

const tableConfig: TableConfig = {
  hideColumns: true,
  canExport: true,
};
const tableHeaders: TableHeaders[] = [
  {
    text: i18n.t("general.id"),
    value: "id",
    show: false,
  },
  {
    text: i18n.t("tool.category"),
    value: "category",
    show: true,
    sortable: true,
  },
  {
    text: i18n.t("tool.photo"),
    value: "image",
    show: true,
  },
  {
    text: i18n.t("general.name"),
    value: "name",
    show: true,
    sortable: true,
  },
  {
    text: i18n.t("tool.details"),
    value: "details",
    show: true,
  },
  {
    text: i18n.t("tool.on-hand"),
    value: "onHand",
    show: true,
    sortable: true,
    align: "center",
  },
  {
    text: i18n.t("general.recipes"),
    value: "recipeCount",
    show: true,
    sortable: true,
    align: "center",
  },
];

const userHousehold = computed(() => auth.user.value?.householdSlug || "");
const toolStore = useToolStore();
const tools = computed(() => toolStore.store.value.map((tool) => {
  const onHand = tool.householdsWithTool?.includes(userHousehold.value) || false;
  return { ...tool, onHand } as RecipeToolWithOnHand;
}));

const toolNames = computed<Record<string, string>>(() => Object.fromEntries(tools.value.map(tool => [tool.id, tool.name])));

onMounted(() => {
  toolStore.actions.refresh();
});

// ============================================================
// Form items (shared)
const formItems = [
  {
    label: i18n.t("general.name"),
    varName: "name",
    type: fieldTypes.TEXT,
    rules: [validators.required],
  },
  {
    label: i18n.t("tool.on-hand"),
    varName: "onHand",
    type: fieldTypes.BOOLEAN,
  },
] as AutoFormItems;

// ============================================================
// Create
const createForm = reactive({
  items: formItems,
  data: emptyCreateData(),
});

function emptyCreateData() {
  return { name: "", onHand: false, category: DEFAULT_TOOL_CATEGORY, usages: [] } as ToolCreate;
}

const createPhoto = ref<File | null>(null);

async function handleCreate(createFormData: ToolCreate) {
  const photo = createPhoto.value;
  // @ts-expect-error createOne eroniusly expects id and slug which are not preset at time of creation
  const created = await toolStore.actions.createOne({ ...toolFormPayload(createFormData), householdsWithTool: createFormData.onHand ? [userHousehold.value] : [] } as ToolCreate);
  createForm.data = emptyCreateData();
  createPhoto.value = null;

  // the photo needs the id of the tool, so it is uploaded once the tool exists
  if (created?.id && photo) {
    const { data } = await userApi.tools.updateImage(created.id, photo);
    if (data) {
      await toolStore.actions.refresh();
    }
  }
}

// ============================================================
// Edit
const editForm = reactive({
  items: formItems,
  data: {} as RecipeToolWithOnHand,
});

async function handleEdit(editFormData: RecipeToolWithOnHand) {
  // if list of households is undefined default to empty array
  if (!editFormData.householdsWithTool) {
    editFormData.householdsWithTool = [];
  }

  if (editFormData.onHand && !editFormData.householdsWithTool.includes(userHousehold.value)) {
    editFormData.householdsWithTool.push(userHousehold.value);
  }
  else if (!editFormData.onHand && editFormData.householdsWithTool.includes(userHousehold.value)) {
    const idx = editFormData.householdsWithTool.indexOf(userHousehold.value);
    if (idx !== -1) editFormData.householdsWithTool.splice(idx, 1);
  }

  await toolStore.actions.updateOne({ ...editFormData, ...toolFormPayload(editFormData), id: editFormData.id } as ToolOut);
  editForm.data = {} as RecipeToolWithOnHand;
}

// the photo is saved as soon as it is picked, so the table shows it even if the edit is cancelled
async function handlePhotoUpdated(tool: ToolOut) {
  editForm.data = { ...editForm.data, image: tool.image };
  await toolStore.actions.refresh();
}

// ============================================================
// Row Actions
const rowActions = computed<BulkAction[]>(() => [
  { icon: $globals.icons.link, text: i18n.t("tool.search-on-amazon"), event: "amazon" },
]);

function handleRowAction(event: string, item: RecipeToolWithOnHand) {
  if (event === "amazon") {
    window.open(amazonSearchUrl(item.name), "_blank", "noopener,noreferrer");
  }
}

// ============================================================
// Bulk Actions
const { $globals } = useNuxtApp();
const bulkActions: BulkAction[] = [
  { icon: $globals.icons.delete, text: i18n.t("general.delete"), event: "delete-selected" },
  { icon: $globals.icons.check, text: i18n.t("data-pages.tools.mark-on-hand"), event: "on-hand-selected" },
  { icon: $globals.icons.close, text: i18n.t("data-pages.tools.mark-off-hand"), event: "off-hand-selected" },
];

async function setOnHand(items: RecipeToolWithOnHand[], onHand: boolean) {
  const updates = toolOnHandUpdates(items, userHousehold.value, onHand);
  if (!updates.length) {
    return;
  }

  // sent one by one with the API directly, so the store is only refreshed once at the end
  const results = await Promise.all(updates.map(({ id, payload }) => userApi.tools.updateOne(id, payload)));

  await toolStore.actions.refresh();
  const updated = results.filter(result => result.data).length;
  if (updated) {
    alert.success(i18n.t("data-pages.tools.on-hand-updated", { count: updated }, updated));
  }
}

async function handleBulkAction(event: string, items: RecipeToolWithOnHand[]) {
  if (event === "delete-selected") {
    const ids = items.map(item => item.id);
    await toolStore.actions.deleteMany(ids);
  }
  else if (event === "on-hand-selected") {
    await setOnHand(items, true);
  }
  else if (event === "off-hand-selected") {
    await setOnHand(items, false);
  }
}

// ============================================================
// Merge Tools
const mergeDialog = ref(false);
const fromTool = ref<RecipeToolWithOnHand | null>(null);
const toTool = ref<RecipeToolWithOnHand | null>(null);

const canMerge = computed(() => {
  return fromTool.value && toTool.value && fromTool.value.id !== toTool.value.id;
});

function resetMergeDialog() {
  fromTool.value = null;
  toTool.value = null;
}

async function mergeTools() {
  if (!canMerge.value || !fromTool.value?.id || !toTool.value?.id) {
    return;
  }

  const { data } = await userApi.tools.merge(fromTool.value.id, toTool.value.id);

  if (data) {
    fromTool.value = null;
    toTool.value = null;
    toolStore.actions.refresh();
  }
}

// ============================================================
// Delete Unused
const DELETE_UNUSED_PREVIEW_LIMIT = 10;

const deleteUnusedDialog = ref(false);
const unusedTools = ref<ToolOut[]>([]);
const unusedToolIds = computed(() => unusedTools.value.filter(t => t.id != null).map(t => t.id!));
const unusedToolNamesPreview = computed(() => unusedTools.value.slice(0, DELETE_UNUSED_PREVIEW_LIMIT).map(t => t.name));
const unusedToolNamesRemaining = computed(() => Math.max(unusedTools.value.length - DELETE_UNUSED_PREVIEW_LIMIT, 0));
const loadingEmpty = ref(false);

async function openDeleteUnusedDialog() {
  loadingEmpty.value = true;
  const { data } = await userApi.tools.getEmpty();
  loadingEmpty.value = false;
  unusedTools.value = data ?? [];

  if (unusedTools.value.length === 0) {
    alert.info(i18n.t("data-pages.tools.no-unused-tools"));
    return;
  }

  deleteUnusedDialog.value = true;
}

async function confirmDeleteUnused() {
  await toolStore.actions.deleteMany(unusedToolIds.value);
  unusedTools.value = [];
}
</script>
