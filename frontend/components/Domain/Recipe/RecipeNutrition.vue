<template>
  <div v-if="valueNotNull || edit">
    <v-card class="mt-2">
      <v-card-title class="pt-2 pb-0 d-flex align-center">
        {{ $t("recipe.nutrition") }}
        <BaseButton
          v-if="edit"
          class="ml-auto"
          size="small"
          :loading="isCalculating"
          variant="text"
          @click="calculateNutrition"
        >
          <template #prepend>
            <v-icon icon="mdi-calculator-variant-outline" />
          </template>
          {{ $t("recipe.calculate-nutrition") }}
        </BaseButton>
      </v-card-title>
      <v-divider class="mx-2 my-1" />
      <v-card-text v-if="edit">
        <div
          v-for="(item, key, index) in modelValue"
          :key="index"
        >
          <v-text-field
            density="compact"
            :model-value="modelValue[key]"
            :label="labels[key].label"
            :suffix="labels[key].suffix"
            type="number"
            autocomplete="off"
            variant="underlined"
            @update:model-value="updateValue(key, $event)"
          />
        </div>
      </v-card-text>
      <v-list
        v-if="showViewer"
        density="compact"
        class="mt-0 pt-0"
      >
        <v-list-item
          v-for="(item, key, index) in renderedList"
          :key="index"
          style="min-height: 25px"
        >
          <v-list-item-title class="pl-2 d-flex">
            <div>{{ item.label }}</div>
            <div class="ml-auto mr-1">
              {{ item.value }}
            </div>
            <div>{{ item.suffix }}</div>
          </v-list-item-title>
        </v-list-item>
      </v-list>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { alert } from "~/composables/use-toast";
import { useNutritionLabels } from "~/composables/recipes";
import type { Nutrition, RecipeIngredient } from "~/lib/api/types/recipe";
import type { NutritionLabelType } from "~/composables/recipes/use-recipe-nutrition";

interface Props {
  edit?: boolean;
  ingredients?: RecipeIngredient[];
  servings?: number | null;
}
const props = withDefaults(defineProps<Props>(), {
  edit: true,
  ingredients: () => [],
  servings: null,
});

const modelValue = defineModel<Nutrition>({ required: true });

const { labels } = useNutritionLabels();
const { t } = useI18n();

const isCalculating = ref(false);

const valueNotNull = computed(() => {
  let key: keyof Nutrition;
  for (key in modelValue.value) {
    if (modelValue.value[key] !== null) {
      return true;
    }
  }
  return false;
});

const showViewer = computed(() => !props.edit && valueNotNull.value);
const nutritionKeys = computed(() => Object.keys(labels));

function updateValue(key: number | string, event: Event) {
  modelValue.value = { ...modelValue.value, [key]: event };
}

function toNumber(value: unknown): number | null {
  const parsedValue = typeof value === "string" ? Number(value.replace(",", ".")) : Number(value);
  return Number.isFinite(parsedValue) ? parsedValue : null;
}

function calculateNutrition() {
  if (!props.ingredients?.length) {
    alert.warning(t("recipe.ingredients"));
    return;
  }

  isCalculating.value = true;

  const totals = nutritionKeys.value.reduce<Record<string, number>>((acc, key) => {
    acc[key] = 0;
    return acc;
  }, {});

  let hasData = false;

  props.ingredients.forEach((ingredient) => {
    const baseQuantity = ingredient.quantity ?? 1;
    const quantity = Number.isFinite(baseQuantity) ? baseQuantity : 1;
    const ingredientNutrition = (ingredient.food as Record<string, unknown> | undefined)?.extras ?? {};

    nutritionKeys.value.forEach((key) => {
      const parsedValue = toNumber((ingredientNutrition as Record<string, unknown>)[key]);
      if (parsedValue !== null) {
        totals[key] += parsedValue * quantity;
        hasData = true;
      }
    });
  });

  if (!hasData) {
    alert.warning(t("recipe.nutrition-calculation-missing-data"));
    isCalculating.value = false;
    return;
  }

  const perServingMultiplier = props.servings && props.servings > 0 ? 1 / props.servings : 1;

  modelValue.value = {
    ...modelValue.value,
    ...nutritionKeys.value.reduce<Nutrition>((acc, key) => {
      const value = totals[key] * perServingMultiplier;
      acc[key as keyof Nutrition] = Number.isFinite(value) ? value.toString() : null;
      return acc;
    }, {} as Nutrition),
  };

  alert.success(t("recipe.nutrition-calculated"));
  isCalculating.value = false;
}

// Build a new list that only contains nutritional information that has a value
const renderedList = computed(() => {
  return Object.entries(labels).reduce((item: NutritionLabelType, [key, label]) => {
    if (modelValue.value[key]?.trim()) {
      item[key] = {
        ...label,
        value: modelValue.value[key],
      };
    }
    return item;
  }, {});
});
</script>

<style lang="scss" scoped></style>
