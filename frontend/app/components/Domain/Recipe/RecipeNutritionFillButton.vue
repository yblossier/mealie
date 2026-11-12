<template>
  <div class="d-inline-flex">
    <v-tooltip location="bottom" color="info">
      <template #activator="{ props: tooltipProps }">
        <v-btn
          icon
          :variant="fab ? 'flat' : 'text'"
          rounded="circle"
          :size="compact ? 'x-small' : 'small'"
          :color="fab ? 'info' : undefined"
          :loading="loading"
          v-bind="tooltipProps"
          @click="calculate"
        >
          <BaseNutritionAiIcon :size="iconSize" :background="fab ? 'info' : 'surface'" />
        </v-btn>
      </template>
      <span>{{ $t("recipe.fill-nutrition-from-ingredients") }}</span>
    </v-tooltip>

    <BaseDialog
      v-model="problemsDialog"
      :title="$t('recipe.fill-nutrition-from-ingredients')"
      :icon="$globals.icons.alertCircle"
      color="warning"
      :can-submit="!!result?.usedCount"
      :submit-text="$t('recipe.nutrition-calculation-ignore')"
      :submit-icon="$globals.icons.calculator"
      :cancel-text="result?.usedCount ? $t('general.cancel') : $t('general.close')"
      @submit="applyResult"
    >
      <v-card-text v-if="result">
        <div class="pb-2">
          {{ result.usedCount
            ? $t("recipe.nutrition-calculation-problems")
            : $t("recipe.nutrition-no-usable-ingredient") }}
        </div>
        <v-list density="compact">
          <v-list-item v-for="(problem, index) in result.problems" :key="index" class="px-0">
            <v-list-item-title class="text-wrap font-weight-bold">
              {{ ingredientName(problem.ingredient) }}
            </v-list-item-title>
            <v-list-item-subtitle class="text-wrap">
              {{ problemText(problem) }}
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>
        <div class="pt-2 text-body-small">
          {{ $t("recipe.nutrition-calculation-hint") }}
        </div>
      </v-card-text>
    </BaseDialog>
  </div>
</template>

<script setup lang="ts">
import { useUserApi } from "~/composables/api";
import { alert } from "~/composables/use-toast";
import {
  calculateRecipeNutrition,
  type NutritionProblem,
  type RecipeNutritionResult,
} from "~/composables/recipes/recipe-nutrition-calculator";
import type { Nutrition, RecipeIngredient, RecipeOut } from "~/lib/api/types/recipe";

interface Props {
  recipe: RecipeOut;
  /** Round, filled button matching the recipe action menu */
  fab?: boolean;
  /** Smaller size, to fit in a card title bar */
  compact?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  fab: false,
  compact: false,
});

const iconSize = computed(() => {
  if (props.compact) {
    return 20;
  }
  return props.fab ? 30 : 24;
});

const emit = defineEmits<{
  fill: [nutrition: Nutrition];
}>();

const i18n = useI18n();
const api = useUserApi();

const loading = ref(false);
const problemsDialog = ref(false);
const result = ref<RecipeNutritionResult | null>(null);

function ingredientName(ingredient: RecipeIngredient): string {
  return ingredient.display?.trim()
    || ingredient.note?.trim()
    || ingredient.food?.name
    || ingredient.originalText
    || "?";
}

function problemText(problem: NutritionProblem): string {
  const { ingredient, reason } = problem;
  switch (reason) {
    case "sub-recipe":
      return i18n.t("recipe.nutrition-ingredient-sub-recipe");
    case "no-food":
      return i18n.t("recipe.nutrition-ingredient-no-food");
    case "no-quantity":
      return i18n.t("recipe.nutrition-ingredient-no-quantity");
    case "no-unit":
      return i18n.t("recipe.nutrition-ingredient-no-unit");
    case "unit-not-convertible":
      return i18n.t("recipe.nutrition-ingredient-unit-not-convertible", { unit: ingredient.unit?.name || "" });
    case "food-no-nutrition":
      return i18n.t("recipe.nutrition-ingredient-food-no-nutrition", { food: ingredient.food?.name || "" });
  }
}

interface FoodsData {
  nutrition: Record<string, Nutrition | null>;
  averageWeights: Record<string, number | null>;
}

/** The nutrition facts embedded in a recipe can be stale, so the foods are read again */
async function loadFoods(): Promise<FoodsData | null> {
  const ids = [...new Set(
    props.recipe.recipeIngredient
      .map(ingredient => (ingredient.food && "id" in ingredient.food ? ingredient.food.id : undefined))
      .filter((id): id is string => !!id),
  )];

  const responses = await Promise.all(ids.map(id => api.foods.getOne(id)));
  const foods: FoodsData = { nutrition: {}, averageWeights: {} };
  for (const [index, { data, error }] of responses.entries()) {
    if (!data) {
      const status = (error as any)?.response?.status;
      const reason = [status ? `HTTP ${status}` : "", (error as any)?.message || ""].filter(Boolean).join(" - ");
      alert.error(i18n.t("recipe.nutrition-calculation-failed", { error: reason || ids[index] }));
      return null;
    }
    foods.nutrition[data.id] = data.nutrition ?? null;
    foods.averageWeights[data.id] = data.averageWeight ?? null;
  }

  return foods;
}

async function calculate() {
  const servings = props.recipe.recipeServings || 0;
  if (servings <= 0) {
    alert.error(i18n.t("recipe.nutrition-no-servings"));
    return;
  }

  loading.value = true;
  try {
    const foods = await loadFoods();
    if (!foods) {
      return;
    }

    result.value = calculateRecipeNutrition(props.recipe.recipeIngredient, servings, foods.nutrition, foods.averageWeights);
    if (result.value.problems.length || !result.value.usedCount) {
      problemsDialog.value = true;
      return;
    }

    applyResult();
  }
  finally {
    loading.value = false;
  }
}

function applyResult() {
  if (!result.value?.usedCount) {
    return;
  }

  emit("fill", result.value.nutrition);
  result.value = null;
}
</script>
