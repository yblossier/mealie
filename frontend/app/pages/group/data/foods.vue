<template>
  <div>
    <!-- Merge Dialog -->
    <BaseDialog
      v-model="mergeDialog"
      bottom-sheet
      :icon="$globals.icons.foods"
      :title="$t('data-pages.foods.combine-food')"
      can-confirm
      @confirm="mergeFoods"
      @close="resetMergeDialog"
    >
      <v-card-text>
        <div>
          {{ $t("data-pages.foods.merge-dialog-text") }}
        </div>
        <v-autocomplete
          v-model="fromFood"
          return-object
          :items="foods"
          :custom-filter="normalizeFilter"
          item-title="name"
          :label="$t('data-pages.foods.source-food')"
        />
        <v-autocomplete
          v-model="toFood"
          return-object
          :items="foods"
          :custom-filter="normalizeFilter"
          item-title="name"
          :label="$t('data-pages.foods.target-food')"
        />

        <template v-if="canMerge && fromFood && toFood">
          <div class="text-center">
            {{ $t("data-pages.foods.merge-food-example", { food1: fromFood.name, food2: toFood.name }) }}
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
        {{ $t('data-pages.foods.delete-unused-confirm', { count: unusedFoodIds.length }, unusedFoodIds.length) }}
        <ul style="margin: 0.5rem 0 0; padding-left: 1.25rem; font-size: 0.85rem; color: rgba(var(--v-theme-on-surface), 0.7); line-height: 1.8;">
          <li v-for="name in unusedFoodNamesPreview" :key="name">
            {{ name }}
          </li>
        </ul>
        <div v-if="unusedFoodNamesRemaining > 0" class="text-body-2 pl-2">
          {{ $t('data-pages.delete-unused-more', { count: unusedFoodNamesRemaining }) }}
        </div>
      </v-card-text>
    </BaseDialog>

    <!-- Seed Dialog -->
    <BaseDialog
      v-model="seedDialog"
      bottom-sheet
      :icon="$globals.icons.foods"
      :title="$t('data-pages.seed-data')"
      can-confirm
      @confirm="seedDatabase"
    >
      <v-card-text>
        <div class="pb-2">
          {{ $t("data-pages.foods.seed-dialog-text") }}
        </div>
        <v-autocomplete
          v-model="locale"
          :items="locales"
          item-title="name"
          :custom-filter="normalizeFilter"
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

        <v-alert v-if="foods && foods.length > 0" type="error" class="mb-0 text-body-2">
          {{ $t("data-pages.foods.seed-dialog-warning") }}
        </v-alert>
      </v-card-text>
    </BaseDialog>

    <!-- Substitution Sub-Dialog -->
    <RecipeDataSubstitutionManagerDialog
      v-if="editForm.data"
      v-model="substitutionManagerDialog"
      :data="editForm.data"
      @submit="updateFoodSubstitutions"
      @cancel="substitutionManagerDialog = false"
    />

    <!-- View Nutrition Dialog -->
    <BaseDialog
      v-model="nutritionViewDialog"
      :title="$t('data-pages.foods.view-nutrition')"
      :icon="$globals.icons.foods"
      :cancel-text="$t('general.close')"
    >
      <v-card-text>
        <div class="pb-2 text-subtitle-1 font-weight-bold">
          {{ nutritionViewTarget?.name }}
        </div>
        <template v-if="nutritionViewHasValues">
          <RecipeNutritionFactsLabel :nutrition="nutritionViewTarget?.nutrition" />
          <RecipeDataNutritionSource
            class="pt-3"
            :source="nutritionViewTarget?.nutritionSource"
            :reference-code="nutritionViewTarget?.nutritionReferenceCode"
            :reference-name="nutritionViewTarget?.nutritionReferenceName"
          />
        </template>
        <v-alert v-else type="info" variant="tonal" density="compact">
          {{ $t("data-pages.foods.no-nutrition-values", { food: nutritionViewTarget?.name }) }}
        </v-alert>
      </v-card-text>
      <template v-if="!nutritionViewHasValues" #custom-card-action>
        <BaseButton
          color="info"
          :loading="nutritionAI.loading.value"
          data-testid="generate-nutrition"
          @click="generateViewedNutrition"
        >
          <template #icon>
            <BaseNutritionAiIcon :size="20" background="info" />
          </template>
          {{ $t("data-pages.foods.generate-nutrition") }}
        </BaseButton>
      </template>
    </BaseDialog>

    <!-- Nutrition History Dialog -->
    <RecipeDataNutritionLogDialog v-model="nutritionLogDialog" :food="nutritionLogTarget" />

    <!-- Bulk Assign Labels Dialog -->
    <BaseDialog
      v-model="bulkAssignLabelDialog"
      bottom-sheet
      :title="$t('data-pages.labels.assign-label')"
      :icon="$globals.icons.tags"
      can-confirm
      @confirm="assignSelected"
    >
      <v-card-text>
        <v-card class="mb-4">
          <v-card-title>{{ $t("general.caution") }}</v-card-title>
          <v-card-text>{{ $t("data-pages.foods.label-overwrite-warning") }}</v-card-text>
        </v-card>

        <v-autocomplete
          v-model="bulkAssignLabelId"
          clearable
          :items="allLabels"
          :custom-filter="normalizeFilter"
          item-value="id"
          item-title="name"
          :label="$t('data-pages.foods.food-label')"
        />
        <v-card variant="outlined">
          <v-virtual-scroll height="400" item-height="25" :items="bulkAssignTarget">
            <template #default="{ item }">
              <v-list-item class="pb-2">
                <v-list-item-title>{{ item.name }}</v-list-item-title>
              </v-list-item>
            </template>
          </v-virtual-scroll>
        </v-card>
      </v-card-text>
    </BaseDialog>

    <GroupDataPage
      :items-per-page="tablePageSize"
      :icon="$globals.icons.foods"
      :title="$t('data-pages.foods.food-data')"
      :create-title="$t('data-pages.foods.create-food')"
      :edit-title="$t('data-pages.foods.edit-food')"
      :table-headers="tableHeaders"
      :table-config="tableConfig"
      :data="foods || []"
      :bulk-actions="bulkActions"
      :row-actions="rowActions"
      :create-form="createForm"
      :edit-form="editForm"
      :on-delete-dialog-open="onDeleteDialogOpen"
      @create-one="handleCreate"
      @edit-one="handleEdit"
      @delete-one="foodStore.actions.deleteOne"
      @bulk-action="handleBulkAction"
      @row-action="handleRowAction"
    >
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

      <template #[`item.actions-prepend`]="{ item }">
        <v-tooltip
          location="bottom"
          open-delay="200"
          content-class="text-caption"
          :text="item.hasNutrition ? $t('data-pages.foods.view-nutrition') : $t('data-pages.foods.no-nutrition-values')"
        >
          <template #activator="{ props: tooltipProps }">
            <v-btn
              v-if="item.hasNutrition"
              v-bind="tooltipProps"
              tile
              icon
              size="small"
              variant="plain"
              data-testid="view-nutrition"
              @click="openNutritionView(item)"
            >
              <v-icon>{{ $globals.icons.foods }}</v-icon>
            </v-btn>
            <span
              v-else
              v-bind="tooltipProps"
              class="nutrition-off d-inline-flex align-center justify-center"
              data-testid="no-nutrition"
            >
              <v-icon>{{ $globals.icons.foods }}</v-icon>
            </span>
          </template>
        </v-tooltip>
      </template>

      <template #[`item.averageWeight`]="{ item }">
        {{ item.averageWeight ? `${$n(item.averageWeight)} g` : "" }}
      </template>

      <template #[`item.label`]="{ item }">
        <MultiPurposeLabel v-if="item.label" :label="item.label">
          {{ item.label.name }}
        </MultiPurposeLabel>
      </template>

      <template #[`item.onHand`]="{ item }">
        <v-icon :color="item.onHand ? 'success' : 'error'">
          {{ item.onHand ? $globals.icons.check : $globals.icons.close }}
        </v-icon>
      </template>

      <template #[`item.substitutions`]="{ item }">
        {{ item.substitutions ? item.substitutions.length : 0 }}
      </template>

      <template #[`item.allergens`]="{ item }">
        <v-tooltip location="bottom" open-delay="200" content-class="text-caption">
          <template #activator="{ props: tooltipProps }">
            <v-chip
              v-bind="tooltipProps"
              size="small"
              color="grey"
              variant="flat"
              class="count-bubble justify-center"
              data-testid="allergen-count-bubble"
            >
              {{ item.allergens?.length || 0 }}
            </v-chip>
          </template>
          <span>
            {{ item.allergens?.length
              ? item.allergens.map(allergen => allergen.name).join(", ")
              : $t("data-pages.foods.no-allergens") }}
          </span>
        </v-tooltip>
      </template>

      <template #[`item.recipeCount`]="{ item }">
        <GroupDataRecipeCount
          :count="item.recipeCount || 0"
          :to="userGroup ? `/g/${userGroup}?foods=${item.id}` : null"
        />
      </template>

      <template #[`item.createdAt`]="{ item }">
        {{ item.createdAt ? $d(new Date(item.createdAt)) : "" }}
      </template>

      <template #table-button-bottom>
        <BaseButton @click="seedDialog = true">
          <template #icon>
            {{ $globals.icons.database }}
          </template>
          {{ $t("data-pages.seed") }}
        </BaseButton>
      </template>

      <template #create-dialog-top>
        <div class="text-subtitle-1 font-weight-medium px-2" data-testid="food-section-general">
          {{ $t("data-pages.foods.section-general") }}
        </div>
      </template>

      <template #edit-dialog-top>
        <div class="text-subtitle-1 font-weight-medium px-2" data-testid="food-section-general">
          {{ $t("data-pages.foods.section-general") }}
        </div>
      </template>

      <template #create-field-after-description>
        <RecipeDataFoodAliasesField
          v-model="createForm.data.aliases"
          :excluded-names="[createForm.data.name, createForm.data.pluralName]"
        />
      </template>

      <template #edit-field-after-description>
        <RecipeDataFoodAliasesField
          v-if="editForm.data"
          v-model="editForm.data.aliases"
          :excluded-names="[editForm.data.name, editForm.data.pluralName]"
        />
      </template>

      <template #create-dialog-bottom>
        <RecipeDataFoodFormSections
          v-model:allergens="createForm.data.allergens"
          v-model:nutrition="createForm.data.nutrition"
          v-model:source="createForm.data.nutritionSource"
          v-model:reference-code="createForm.data.nutritionReferenceCode"
          v-model:reference-name="createForm.data.nutritionReferenceName"
          :food="createForm.data"
          :fill-loading="nutritionAI.loading.value"
          @fill-nutrition="fillCreatedNutrition"
          @average-weight="applyCreatedReferenceWeight"
        />
      </template>

      <template #edit-dialog-bottom>
        <RecipeDataFoodFormSections
          v-if="editForm.data"
          v-model:allergens="editForm.data.allergens"
          v-model:nutrition="editForm.data.nutrition"
          v-model:source="editForm.data.nutritionSource"
          v-model:reference-code="editForm.data.nutritionReferenceCode"
          v-model:reference-name="editForm.data.nutritionReferenceName"
          :food="editForm.data"
          :food-names="foodNames"
          manage-links
          :fill-loading="nutritionAI.loading.value"
          @manage-substitutions="substitutionManagerDialog = true"
          @fill-nutrition="fillEditedNutrition"
          @average-weight="applyReferenceWeight"
        />
      </template>

      <template #delete-dialog-bottom>
        <v-alert v-if="affectedRecipes.length > 0" type="warning" density="compact" class="mt-4 mb-0">
          {{ $t("data-pages.foods.delete-affects-recipes", { count: affectedRecipesTotal }) }}
          <ul class="mt-1 pl-5 mb-0">
            <li v-for="recipe in affectedRecipes.slice(0, 5)" :key="recipe.slug">
              <NuxtLink :to="recipe.url" class="text-white">{{ recipe.name }}</NuxtLink>
            </li>
          </ul>
          <NuxtLink
            v-if="affectedRecipesTotal > 5"
            :to="affectedRecipesMoreLink"
            class="text-white d-inline-block mt-1"
          >
            {{ $t("data-pages.foods.delete-affects-recipes-more", { count: affectedRecipesTotal }) }}
          </NuxtLink>
        </v-alert>
      </template>
    </GroupDataPage>
  </div>
</template>

<script setup lang="ts">
import type { LocaleObject } from "@nuxtjs/i18n";
import RecipeDataSubstitutionManagerDialog from "~/components/Domain/Recipe/RecipeDataSubstitutionManagerDialog.vue";
import RecipeDataFoodAliasesField from "~/components/Domain/Recipe/RecipeDataFoodAliasesField.vue";
import RecipeDataNutritionSource from "~/components/Domain/Recipe/RecipeDataNutritionSource.vue";
import RecipeNutritionFactsLabel from "~/components/Domain/Recipe/RecipeNutritionFactsLabel.vue";
import RecipeDataNutritionLogDialog from "~/components/Domain/Recipe/RecipeDataNutritionLogDialog.vue";
import RecipeDataFoodFormSections from "~/components/Domain/Recipe/RecipeDataFoodFormSections.vue";
import GroupDataRecipeCount from "~/components/Domain/Group/GroupDataRecipeCount.vue";
import type { ReverseSubstitutionChanges } from "~/components/Domain/Recipe/RecipeDataSubstitutionManagerDialog.vue";
import { validators } from "~/composables/use-validators";
import { useUserApi } from "~/composables/api";
import type {
  IngredientFoodCreate,
  IngredientFoodOut,
  IngredientFoodSubstitution,
  Nutrition,
} from "~/lib/api/types/recipe";
import MultiPurposeLabel from "~/components/Domain/ShoppingList/MultiPurposeLabel.vue";
import { useLocales } from "~/composables/use-locales";
import { normalizeFilter } from "~/composables/use-utils";
import { alert } from "~/composables/use-toast";
import { useFoodStore, useLabelStore } from "~/composables/store";
import type { MultiPurposeLabelOut } from "~/lib/api/types/labels";
import type { AutoFormItems } from "~/types/auto-forms";
import type { TableHeaders, TableConfig, BulkAction } from "~/components/global/CrudTable.vue";
import { fieldTypes } from "~/composables/forms";
import { hasNutritionValues } from "~/composables/recipes/use-recipe-nutrition";
import { useFoodNutritionAI } from "~/composables/recipes/use-food-nutrition-ai";
import { useTablePageSize } from "~/composables/use-table-page-size";

const tablePageSize = useTablePageSize();

interface CreateIngredientFoodWithOnHand extends IngredientFoodCreate {
  onHand: boolean;
  householdsWithIngredientFood: string[];
}

interface IngredientFoodWithOnHand extends IngredientFoodOut {
  onHand: boolean;
  hasNutrition: boolean;
}

const userApi = useUserApi();
const i18n = useI18n();
const auth = useMealieAuth();
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
    text: i18n.t("general.name"),
    value: "name",
    show: true,
    sortable: true,
  },
  {
    text: i18n.t("general.plural-name"),
    value: "pluralName",
    show: true,
    sortable: true,
  },
  {
    text: i18n.t("recipe.description"),
    value: "description",
    show: true,
  },
  {
    text: i18n.t("shopping-list.label"),
    value: "label",
    show: true,
    sortable: true,
    sort: (label1: MultiPurposeLabelOut | null, label2: MultiPurposeLabelOut | null) => {
      const label1Name = label1?.name || "";
      const label2Name = label2?.name || "";
      return label1Name.localeCompare(label2Name);
    },
  },
  {
    text: i18n.t("tool.on-hand"),
    value: "onHand",
    show: true,
    sortable: true,
    align: "center",
  },
  {
    text: i18n.t("data-pages.foods.average-weight"),
    value: "averageWeight",
    show: false,
    sortable: true,
  },
  {
    text: i18n.t("data-pages.foods.substitutions"),
    value: "substitutions",
    show: true,
    sortable: true,
    align: "center",
    sort: (subs1: IngredientFoodSubstitution[] | null, subs2: IngredientFoodSubstitution[] | null) => {
      return (subs1?.length || 0) - (subs2?.length || 0);
    },
  },
  {
    text: i18n.t("data-pages.foods.allergens"),
    value: "allergens",
    show: true,
    sortable: true,
    align: "center",
    sort: (allergens1: unknown[] | null, allergens2: unknown[] | null) => {
      return (allergens1?.length || 0) - (allergens2?.length || 0);
    },
  },
  {
    text: i18n.t("general.recipes"),
    value: "recipeCount",
    show: true,
    sortable: true,
    align: "center",
  },
  {
    text: i18n.t("general.date-added"),
    value: "createdAt",
    show: false,
    sortable: true,
  },
];

const userHousehold = computed(() => auth.user.value?.householdSlug || "");
const userGroup = computed(() => auth.user.value?.groupSlug || "");
const foodStore = useFoodStore();
const foods = computed(() =>
  foodStore.store.value.map((food) => {
    const onHand = food.householdsWithIngredientFood?.includes(userHousehold.value) || false;
    return { ...food, onHand, hasNutrition: hasNutritionValues(food.nutrition) } as IngredientFoodWithOnHand;
  }),
);

// names the substitutes of a food whose substitutions were not expanded by the API
const foodNames = computed(() => Object.fromEntries(foodStore.store.value.map(food => [food.id, food.name])));

onMounted(() => {
  foodStore.actions.refresh();
});

// ============================================================
// Labels
const labelStore = useLabelStore();
const { store: allLabels } = labelStore;
const labelOptions = computed(() => allLabels.value.map(label => ({ text: label.name, value: label.id })) || []);

// ============================================================
// Form items (shared)
const formItems = computed<AutoFormItems>(() => [
  {
    label: i18n.t("general.name"),
    varName: "name",
    type: fieldTypes.TEXT,
    rules: [validators.required],
  },
  {
    label: i18n.t("general.plural-name"),
    varName: "pluralName",
    type: fieldTypes.TEXT,
  },
  {
    label: i18n.t("recipe.description"),
    varName: "description",
    type: fieldTypes.TEXT,
  },
  {
    label: i18n.t("data-pages.foods.food-label"),
    varName: "labelId",
    type: fieldTypes.SELECT,
    options: labelOptions.value,
    selectReturnValue: "value",
  },
  {
    label: i18n.t("data-pages.foods.average-weight"),
    varName: "averageWeight",
    type: fieldTypes.NUMBER,
    hint: i18n.t("data-pages.foods.average-weight-hint"),
    numberInputConfig: { min: 0, precision: 1, controlVariant: "hidden" },
  },
  {
    label: i18n.t("tool.on-hand"),
    varName: "onHand",
    type: fieldTypes.BOOLEAN,
    hint: i18n.t("data-pages.foods.on-hand-checkbox-label"),
  },
]);

// ===============================================================
// Create

const createForm = reactive({
  get items() {
    return formItems.value;
  },
  data: emptyCreateData(),
});

function emptyCreateData(): CreateIngredientFoodWithOnHand {
  return { name: "", onHand: false, householdsWithIngredientFood: [], aliases: [], allergens: [], nutrition: null };
}

async function fillCreatedNutrition() {
  const data = createForm.data;
  const estimate = await nutritionAI.estimate(data);
  if (!estimate) {
    return;
  }
  if (estimate.nutrition) {
    data.nutrition = { ...(data.nutrition || {}), ...estimate.nutrition };
    data.nutritionSource = estimate.source;
    data.nutritionReferenceCode = estimate.referenceCode;
    data.nutritionReferenceName = estimate.referenceName;
  }
  if (estimate.averageWeight && !data.averageWeight) {
    data.averageWeight = estimate.averageWeight;
  }
}

function applyCreatedReferenceWeight(weight: number) {
  if (!createForm.data.averageWeight) {
    createForm.data.averageWeight = weight;
  }
}

async function handleCreate() {
  if (!createForm.data || !createForm.data.name) {
    return;
  }

  if (createForm.data.onHand) {
    createForm.data.householdsWithIngredientFood = [userHousehold.value];
  }

  createForm.data.nutrition = cleanNutrition(createForm.data.nutrition);
  if (!createForm.data.nutrition) {
    createForm.data.nutritionSource = null;
    createForm.data.nutritionReferenceCode = null;
    createForm.data.nutritionReferenceName = null;
  }

  // @ts-expect-error the createOne function erroneously expects an id because it uses the IngredientFood type
  await foodStore.actions.createOne(createForm.data);
  createForm.data = emptyCreateData();
}

// ===============================================================
// Edit

const editForm = reactive({
  get items() {
    return formItems.value;
  },
  data: {} as IngredientFoodWithOnHand,
});

async function handleEdit() {
  if (!editForm.data) {
    return;
  }
  if (!editForm.data.householdsWithIngredientFood) {
    editForm.data.householdsWithIngredientFood = [];
  }

  const foodId = editForm.data.id;

  if (editForm.data.onHand && !editForm.data.householdsWithIngredientFood.includes(userHousehold.value)) {
    editForm.data.householdsWithIngredientFood.push(userHousehold.value);
  }
  else if (!editForm.data.onHand && editForm.data.householdsWithIngredientFood.includes(userHousehold.value)) {
    const idx = editForm.data.householdsWithIngredientFood.indexOf(userHousehold.value);
    if (idx !== -1) editForm.data.householdsWithIngredientFood.splice(idx, 1);
  }

  editForm.data.nutrition = cleanNutrition(editForm.data.nutrition);
  if (!editForm.data.nutrition) {
    editForm.data.nutritionSource = null;
    editForm.data.nutritionReferenceCode = null;
    editForm.data.nutritionReferenceName = null;
  }
  await foodStore.actions.updateOne(editForm.data);
  editForm.data = {} as IngredientFoodWithOnHand;
  await applyReverseSubstitutions(foodId);
}

// ============================================================
// Bulk Actions
const { $globals } = useNuxtApp();
const bulkActions = computed<BulkAction[]>(() => [
  { icon: $globals.icons.delete, text: i18n.t("general.delete"), event: "delete-selected" },
  { icon: $globals.icons.tags, text: i18n.t("data-pages.labels.assign-label"), event: "assign-selected" },
  { icon: $globals.icons.check, text: i18n.t("data-pages.tools.mark-on-hand"), event: "on-hand-selected" },
  { icon: $globals.icons.close, text: i18n.t("data-pages.tools.mark-off-hand"), event: "off-hand-selected" },
]);

async function setOnHand(items: IngredientFoodWithOnHand[], onHand: boolean) {
  const household = userHousehold.value;
  if (!household) {
    return;
  }
  const updates = items
    .filter(food => onHand !== (food.householdsWithIngredientFood || []).includes(household))
    .map((food) => {
      const { onHand: _onHand, hasNutrition: _hasNutrition, ...data } = food;
      const others = (food.householdsWithIngredientFood || []).filter(slug => slug !== household);
      return { ...data, householdsWithIngredientFood: onHand ? [...others, household] : others };
    });
  if (!updates.length) {
    return;
  }

  // sent one by one with the API directly, so the store is only refreshed once at the end
  const results = await Promise.all(updates.map(food => userApi.foods.updateOne(food.id, food)));

  await foodStore.actions.refresh();
  const updated = results.filter(result => result.data).length;
  if (updated) {
    alert.success(i18n.t("data-pages.foods.on-hand-updated", { count: updated }, updated));
  }
}

async function handleBulkAction(event: string, items: IngredientFoodWithOnHand[]) {
  if (event === "delete-selected") {
    const ids = items.map(item => item.id);
    await foodStore.actions.deleteMany(ids);
    affectedRecipes.value = [];
    affectedRecipesTotal.value = 0;
    affectedRecipesMoreLink.value = "";
  }
  else if (event === "assign-selected") {
    bulkAssignEventHandler(items);
  }
  else if (event === "on-hand-selected") {
    await setOnHand(items, true);
  }
  else if (event === "off-hand-selected") {
    await setOnHand(items, false);
  }
}

// ============================================================
// Nutrition

const rowActions = computed<BulkAction[]>(() => [
  { icon: $globals.icons.history, text: i18n.t("data-pages.foods.nutrition-history"), event: "nutrition-history" },
]);

const nutritionAI = useFoodNutritionAI();

const nutritionViewDialog = ref(false);
const nutritionViewTarget = ref<IngredientFoodWithOnHand | null>(null);
const nutritionViewHasValues = computed(() => hasNutritionValues(nutritionViewTarget.value?.nutrition));

const nutritionLogDialog = ref(false);
const nutritionLogTarget = ref<IngredientFoodWithOnHand | null>(null);

function openNutritionView(item: IngredientFoodWithOnHand) {
  nutritionViewTarget.value = item;
  nutritionViewDialog.value = true;
}

function handleRowAction(event: string, item: IngredientFoodWithOnHand) {
  if (event === "nutrition-history") {
    nutritionLogTarget.value = item;
    nutritionLogDialog.value = true;
  }
}

async function generateViewedNutrition() {
  const target = nutritionViewTarget.value;
  if (!target) {
    return;
  }
  const food = await nutritionAI.generate(target);
  if (food) {
    nutritionViewTarget.value = {
      ...target,
      nutrition: food.nutrition,
      nutritionSource: food.nutritionSource,
      nutritionReferenceCode: food.nutritionReferenceCode,
      nutritionReferenceName: food.nutritionReferenceName,
      hasNutrition: true,
    };
    await foodStore.actions.refresh();
  }
}

/** Fills the edit form with estimated values, which are saved with the rest of the form */
async function fillEditedNutrition() {
  if (!editForm.data) {
    return;
  }
  const estimate = await nutritionAI.estimate(editForm.data);
  if (!estimate) {
    return;
  }
  if (estimate.nutrition) {
    editForm.data.nutrition = { ...(editForm.data.nutrition || {}), ...estimate.nutrition };
    editForm.data.nutritionSource = estimate.source;
    editForm.data.nutritionReferenceCode = estimate.referenceCode;
    editForm.data.nutritionReferenceName = estimate.referenceName;
  }
  // a weight entered by the user is kept, unlike the nutrition facts the button is asked to fill
  if (estimate.averageWeight && !editForm.data.averageWeight) {
    editForm.data.averageWeight = estimate.averageWeight;
  }
}

/** A weight entered by the user is kept */
function applyReferenceWeight(weight: number) {
  if (editForm.data && !editForm.data.averageWeight) {
    editForm.data.averageWeight = weight;
  }
}

function cleanNutrition(nutrition: Nutrition | null | undefined): Nutrition | null {
  return hasNutritionValues(nutrition) ? nutrition! : null;
}

// ============================================================
// Substitution Manager

const substitutionManagerDialog = ref(false);

// reverse substitutions live on other foods, so they can't ride along with the food being edited.
// they're held until the edit is confirmed, and tagged with the food they were built for so
// a cancelled edit can't leak them onto the next food the user opens
const pendingReverseSubstitutions = ref<({ foodId: string } & ReverseSubstitutionChanges) | null>(null);

function updateFoodSubstitutions(
  newSubstitutions: IngredientFoodSubstitution[],
  reverseChanges: ReverseSubstitutionChanges,
) {
  if (!editForm.data) {
    return;
  }
  editForm.data.substitutions = newSubstitutions;
  pendingReverseSubstitutions.value = reverseChanges.add.length || reverseChanges.remove.length
    ? { foodId: editForm.data.id, ...reverseChanges }
    : null;
  substitutionManagerDialog.value = false;
}

async function applyReverseSubstitutions(foodId: string) {
  const pending = pendingReverseSubstitutions.value;
  pendingReverseSubstitutions.value = null;
  if (!pending || !foodId || pending.foodId !== foodId) {
    return;
  }

  let updated = false;
  for (const reverseFoodId of [...pending.add, ...pending.remove]) {
    const reverseFood = foodStore.store.value.find(food => food.id === reverseFoodId);
    if (!reverseFood) {
      continue;
    }

    // rebuilt from what's on the other food right now, so a stale dialog can't resurrect
    // a row someone else removed in the meantime
    const others = (reverseFood.substitutions || []).filter(sub => sub.substituteFoodId !== foodId);
    const substitutions = pending.add.includes(reverseFoodId)
      ? [...others, { substituteFoodId: foodId }]
      : others;

    if (substitutions.length === (reverseFood.substitutions || []).length) {
      continue;
    }

    const payload = { ...reverseFood, substitutions };
    await userApi.foods.updateOne(reverseFoodId, payload);
    updated = true;
  }

  if (updated) {
    await foodStore.actions.refresh();
  }
}

// ============================================================
// Delete Foods

// fetch affected recipes before confirming deletion
const affectedRecipes = ref<{ name: string; slug: string; url: string }[]>([]);
const affectedRecipesTotal = ref(0);
const affectedRecipesMoreLink = ref("");

async function onDeleteDialogOpen(items: IngredientFoodWithOnHand[]) {
  const ids = items.map(item => item.id);
  const { data } = await userApi.recipes.search({ foods: ids, perPage: 5 });
  affectedRecipes.value = (data?.items ?? []).map(r => ({
    name: r.name,
    slug: r.slug,
    url: `/g/${userGroup.value}/r/${r.slug}`,
  }));
  affectedRecipesTotal.value = data?.total ?? 0;
  affectedRecipesMoreLink.value = `/g/${userGroup.value}?${ids.map(id => `foods=${id}`).join("&")}`;
}

// ============================================================
// Merge Foods

const mergeDialog = ref(false);
const fromFood = ref<IngredientFoodWithOnHand | null>(null);
const toFood = ref<IngredientFoodWithOnHand | null>(null);

const canMerge = computed(() => {
  return fromFood.value && toFood.value && fromFood.value.id !== toFood.value.id;
});

function resetMergeDialog() {
  fromFood.value = null;
  toFood.value = null;
}

async function mergeFoods() {
  if (!canMerge.value || !fromFood.value || !toFood.value) {
    return;
  }

  const { data } = await userApi.foods.merge(fromFood.value.id, toFood.value.id);

  if (data) {
    foodStore.actions.refresh();
  }
}

// ============================================================
// Delete Unused
const DELETE_UNUSED_PREVIEW_LIMIT = 10;

const deleteUnusedDialog = ref(false);
const unusedFoods = ref<IngredientFoodWithOnHand[]>([]);
const unusedFoodIds = computed(() => unusedFoods.value.filter(f => f.id != null).map(f => f.id!));
const unusedFoodNamesPreview = computed(() => unusedFoods.value.slice(0, DELETE_UNUSED_PREVIEW_LIMIT).map(f => f.name));
const unusedFoodNamesRemaining = computed(() => Math.max(unusedFoods.value.length - DELETE_UNUSED_PREVIEW_LIMIT, 0));
const loadingEmpty = ref(false);

async function openDeleteUnusedDialog() {
  loadingEmpty.value = true;
  const { data } = await userApi.foods.getEmpty();
  loadingEmpty.value = false;
  unusedFoods.value = (data ?? []) as IngredientFoodWithOnHand[];

  if (unusedFoods.value.length === 0) {
    alert.info(i18n.t("data-pages.foods.no-unused-foods"));
    return;
  }

  deleteUnusedDialog.value = true;
}

async function confirmDeleteUnused() {
  await foodStore.actions.deleteMany(unusedFoodIds.value);
  unusedFoods.value = [];
}

// ============================================================
// Seed

const seedDialog = ref(false);
const locale = ref("");

const { locales: LOCALES, locale: currentLocale } = useLocales();

onMounted(() => {
  locale.value = currentLocale.value;
  foodStore.actions.refresh();
});

const locales = LOCALES.filter(locale =>
  (i18n.locales.value as LocaleObject[]).map(i18nLocale => i18nLocale.code).includes(locale.value as any),
);

async function seedDatabase() {
  const { data } = await userApi.seeders.foods({ locale: locale.value });

  if (data) {
    // seeding foods also creates the labels that group them
    foodStore.actions.refresh();
    labelStore.actions.refresh();
  }
}

// ============================================================
// Bulk Assign Labels
const bulkAssignLabelDialog = ref(false);
const bulkAssignTarget = ref<IngredientFoodWithOnHand[]>([]);
const bulkAssignLabelId = ref<string | undefined>();

function bulkAssignEventHandler(selection: IngredientFoodWithOnHand[]) {
  bulkAssignTarget.value = selection;
  bulkAssignLabelDialog.value = true;
}

async function assignSelected() {
  if (!bulkAssignLabelId.value) {
    return;
  }
  for (const item of bulkAssignTarget.value) {
    item.labelId = bulkAssignLabelId.value;
    await foodStore.actions.updateOne(item);
  }
  bulkAssignTarget.value = [];
  bulkAssignLabelId.value = undefined;
  foodStore.actions.refresh();
}
</script>

<style scoped>
/* Too many custom actions for one row: wrap so the confirm button sits alone on a second row, right-aligned. */
:global(.v-card-actions:not(.grid-small):has(> .edit-actions-break)) {
  flex-wrap: wrap;
  row-gap: 8px;
}
:global(.v-card-actions:not(.grid-small) > .edit-actions-break) {
  flex-basis: 100%;
  height: 0;
}
:global(.v-card-actions:not(.grid-small) > .edit-actions-break ~ *) {
  margin-inline-start: auto !important;
}
:global(.v-card-actions.grid-small > .edit-actions-break) {
  display: none;
}

.count-bubble {
  min-width: 32px;
  border-radius: 999px;
}

/* no nutrition values: the view icon, struck through and not clickable */
.nutrition-off {
  position: relative;
  width: 40px;
  height: 40px;
  opacity: 0.45;
}
.nutrition-off::after {
  content: "";
  position: absolute;
  width: 26px;
  height: 2px;
  background: currentColor;
  transform: rotate(-45deg);
  border-radius: 1px;
}
</style>
