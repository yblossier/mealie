<template>
  <div>
    <!-- Seed Dialog -->
    <BaseDialog
      v-model="seedDialog"
      bottom-sheet
      :icon="$globals.icons.allergies"
      :title="$t('data-pages.seed-data')"
      can-confirm
      @confirm="seedDatabase"
    >
      <v-card-text>
        <div class="pb-2">
          {{ $t("data-pages.allergens.seed-dialog-text") }}
        </div>
        <v-autocomplete
          v-model="locale"
          :items="locales"
          item-title="name"
          :label="$t('data-pages.select-language')"
          class="my-3"
          hide-details
          variant="outlined"
          offset
        >
          <template #item="{ item, props }">
            <v-list-item v-bind="props">
              <v-list-item-subtitle>
                {{ item.raw.progress }}% {{ $t("language-dialog.translated") }}
              </v-list-item-subtitle>
            </v-list-item>
          </template>
        </v-autocomplete>
      </v-card-text>
    </BaseDialog>

    <!-- AI matching Dialog -->
    <BaseDialog
      v-model="matchDialog"
      :icon="$globals.icons.robot"
      :title="$t('data-pages.allergens.match-foods')"
      can-confirm
      @confirm="matchFoods"
    >
      <v-card-text>
        <div class="pb-2">
          {{ $t("data-pages.allergens.match-foods-description") }}
        </div>
        <v-checkbox
          v-model="matchOverwrite"
          hide-details
          density="compact"
          color="primary"
          :label="$t('data-pages.allergens.match-foods-overwrite')"
        />
      </v-card-text>
    </BaseDialog>

    <GroupDataPage
      :items-per-page="tablePageSize"
      :icon="$globals.icons.allergies"
      :title="$t('data-pages.allergens.allergens')"
      :create-title="$t('data-pages.allergens.create-allergen')"
      :edit-title="$t('data-pages.allergens.edit-allergen')"
      :table-headers="tableHeaders"
      :table-config="tableConfig"
      :data="allergenStore || []"
      :bulk-actions="[{ icon: $globals.icons.delete, text: $t('general.delete'), event: 'delete-selected' }]"
      :create-form="createForm"
      :edit-form="editForm"
      @create-one="handleCreate"
      @edit-one="handleEdit"
      @delete-one="allergenActions.deleteOne"
      @bulk-action="handleBulkAction"
    >
      <template #[`item.keywords`]="{ item }">
        <span class="allergen-keywords text-medium-emphasis">{{ item.keywords }}</span>
      </template>

      <template #table-button-bottom>
        <BaseButton
          :icon="$globals.icons.database"
          data-testid="seed-allergens"
          @click="seedDialog = true"
        >
          {{ $t('data-pages.seed') }}
        </BaseButton>
        <BaseButton
          color="info"
          :icon="$globals.icons.robot"
          :loading="matching"
          :disabled="!(allergenStore || []).length"
          data-testid="match-food-allergens"
          @click="matchDialog = true"
        >
          {{ $t('data-pages.allergens.match-foods') }}
        </BaseButton>
      </template>
    </GroupDataPage>
  </div>
</template>

<script setup lang="ts">
import type { LocaleObject } from "@nuxtjs/i18n";
import { validators } from "~/composables/use-validators";
import { useUserApi } from "~/composables/api";
import type { AllergenCreate, AllergenOut } from "~/lib/api/types/allergens";
import { useLocales } from "~/composables/use-locales";
import { useAllergenStore } from "~/composables/store";
import type { AutoFormItems } from "~/types/auto-forms";
import type { TableHeaders, TableConfig } from "~/components/global/CrudTable.vue";
import { fieldTypes } from "~/composables/forms";
import { alert } from "~/composables/use-toast";
import { useTablePageSize } from "~/composables/use-table-page-size";

const tablePageSize = useTablePageSize();

const userApi = useUserApi();
const i18n = useI18n();

const tableConfig: TableConfig = {
  hideColumns: true,
  canExport: true,
};
const tableHeaders: TableHeaders[] = [
  { text: i18n.t("general.id"), value: "id", show: false },
  { text: i18n.t("general.name"), value: "name", show: true, sortable: true },
  { text: i18n.t("data-pages.allergens.code"), value: "code", show: false, sortable: true },
  { text: i18n.t("data-pages.allergens.keywords"), value: "keywords", show: true },
  { text: i18n.t("data-pages.allergens.exclusions"), value: "exclusions", show: false },
];

const { store: allergenStore, actions: allergenActions } = useAllergenStore();

const formItems = computed<AutoFormItems>(() => [
  {
    label: i18n.t("general.name"),
    varName: "name",
    type: fieldTypes.TEXT,
    rules: [validators.required],
  },
  {
    label: i18n.t("data-pages.allergens.keywords"),
    hint: i18n.t("data-pages.allergens.keywords-hint"),
    varName: "keywords",
    type: fieldTypes.TEXT_AREA,
  },
  {
    label: i18n.t("data-pages.allergens.exclusions"),
    hint: i18n.t("data-pages.allergens.exclusions-hint"),
    varName: "exclusions",
    type: fieldTypes.TEXT_AREA,
  },
]);

function emptyAllergen(): AllergenCreate {
  return { name: "", keywords: "", exclusions: "" };
}

const createForm = reactive({
  items: formItems,
  data: emptyAllergen(),
});

async function handleCreate(createFormData: AllergenCreate) {
  // @ts-expect-error createOne expects an id which is not set at creation time
  await allergenActions.createOne(createFormData);
  createForm.data = emptyAllergen();
}

const editForm = reactive({
  items: formItems,
  data: {} as AllergenOut,
});

async function handleEdit(editFormData: AllergenOut) {
  await allergenActions.updateOne(editFormData);
  editForm.data = {} as AllergenOut;
}

async function handleBulkAction(event: string, items: AllergenOut[]) {
  if (event === "delete-selected") {
    await allergenActions.deleteMany(items.map(item => item.id));
  }
}

// ============================================================
// Seed

const seedDialog = ref(false);
const locale = ref("");

const { locales: LOCALES, locale: currentLocale } = useLocales();

onMounted(() => {
  locale.value = currentLocale.value;
});

const locales = LOCALES.filter(locale =>
  (i18n.locales.value as LocaleObject[]).map(i18nLocale => i18nLocale.code).includes(locale.value as any),
);

// ============================================================
// AI matching

const matchDialog = ref(false);
const matchOverwrite = ref(false);
const matching = ref(false);

async function matchFoods() {
  matching.value = true;
  const { data, error } = await userApi.foods.fillAllergens({ overwrite: matchOverwrite.value });
  matching.value = false;

  if (error || !data) {
    alert.error(i18n.t("data-pages.allergens.match-foods-failed"));
    return;
  }
  alert.success(i18n.t("data-pages.allergens.match-foods-done", { count: data.length }, data.length));
}

async function seedDatabase() {
  const { data } = await userApi.seeders.allergens({ locale: locale.value });

  if (data) {
    allergenActions.refresh();
  }
}
</script>

<style scoped>
.allergen-keywords {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  max-width: 40rem;
}
</style>
