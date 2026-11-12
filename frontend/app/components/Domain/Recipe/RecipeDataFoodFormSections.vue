<template>
  <div class="px-2 pb-2">
    <template v-if="manageLinks">
      <v-divider class="my-2" />
      <div class="d-flex align-center" data-testid="food-section-substitutions">
        <v-card-title class="pl-0 pt-1">
          {{ $t("data-pages.foods.substitutions") }}
        </v-card-title>
        <v-tooltip location="bottom" :text="$t('data-pages.foods.manage-substitutions')">
          <template #activator="{ props: tooltipProps }">
            <v-btn
              v-bind="tooltipProps"
              icon
              variant="text"
              color="info"
              class="ml-auto"
              :aria-label="$t('data-pages.foods.manage-substitutions')"
              data-testid="manage-substitutions"
              @click="emit('manage-substitutions')"
            >
              <v-icon>{{ $globals.icons.edit }}</v-icon>
            </v-btn>
          </template>
        </v-tooltip>
      </div>
      <div class="d-flex flex-wrap ga-1 pb-2" data-testid="food-substitutions">
        <v-chip
          v-for="(substitution, index) in substitutionTags"
          :key="index"
          size="small"
          label
          class="substitution-tag"
        >
          {{ substitution.label }}
          <v-tooltip
            v-if="substitution.note"
            location="bottom"
            open-on-click
            max-width="300"
            :text="substitution.note"
          >
            <template #activator="{ props: tooltipProps }">
              <v-icon
                v-bind="tooltipProps"
                end
                size="small"
                :aria-label="substitution.note"
                data-testid="substitution-note"
                @click.stop
              >
                {{ $globals.icons.informationOutline }}
              </v-icon>
            </template>
          </v-tooltip>
        </v-chip>
        <span v-if="!substitutionTags.length" class="text-body-medium text-disabled" data-testid="food-substitutions-empty">
          {{ $t("data-pages.foods.none") }}
        </span>
      </div>
    </template>

    <v-divider class="my-2" />
    <v-card-title class="pl-0 pt-1" data-testid="food-section-allergens">
      {{ $t("data-pages.foods.allergens") }}
    </v-card-title>
    <RecipeDataFoodAllergensField v-model="allergens" :food="food" class="mb-2" />

    <v-divider class="my-2" />
    <RecipeDataNutritionPanel
      v-model="nutrition"
      v-model:source="source"
      v-model:reference-code="referenceCode"
      v-model:reference-name="referenceName"
      :food-name="food.name"
      can-fill
      :fill-loading="fillLoading"
      @fill="emit('fill-nutrition')"
      @average-weight="emit('average-weight', $event)"
    />
  </div>
</template>

<script setup lang="ts">
import RecipeDataFoodAllergensField from "./RecipeDataFoodAllergensField.vue";
import RecipeDataNutritionPanel from "./RecipeDataNutritionPanel.vue";
import type { AllergenSummary } from "~/lib/api/types/allergens";
import type {
  IngredientFoodNutritionSource,
  IngredientFoodSubstitution,
  Nutrition,
} from "~/lib/api/types/recipe";

/**
 * The sections of the food create/edit form shown under its identity and availability fields:
 * substitutions (only for an existing food), allergens and nutrition facts.
 */
const props = withDefaults(defineProps<{
  food: {
    name?: string | null;
    pluralName?: string | null;
    description?: string | null;
    aliases?: { name: string }[] | null;
    substitutions?: IngredientFoodSubstitution[] | null;
  };
  /** Substitutions are managed in a sub-dialog that needs a saved food */
  manageLinks?: boolean;
  fillLoading?: boolean;
  /** Names of the foods, to name the substitutes the API did not expand */
  foodNames?: Record<string, string>;
}>(), {
  manageLinks: false,
  fillLoading: false,
  foodNames: () => ({}),
});

const emit = defineEmits<{
  "manage-substitutions": [];
  "fill-nutrition": [];
  "average-weight": [weight: number];
}>();

const allergens = defineModel<AllergenSummary[] | null | undefined>("allergens");
const nutrition = defineModel<Nutrition | null | undefined>("nutrition");
const source = defineModel<IngredientFoodNutritionSource | null | undefined>("source");
const referenceCode = defineModel<string | null | undefined>("referenceCode");
const referenceName = defineModel<string | null | undefined>("referenceName");

/**
 * One tag per substitution: its foods ("butter + flour") with its instruction behind an info icon,
 * or the instruction itself when it has no food
 */
const substitutionTags = computed(() =>
  (props.food.substitutions ?? [])
    .map((substitution) => {
      const main = substitution.substituteFood?.name
        || (substitution.substituteFoodId ? props.foodNames[substitution.substituteFoodId] : "")
        || "";
      const additional = (substitution.additionalFoods ?? []).map(food => food.name)
        .concat((substitution.additionalFoods?.length ? [] : substitution.additionalFoodIds ?? [])
          .map(id => props.foodNames[id] || ""))
        .filter(Boolean);
      const foods = [main, ...additional].filter(Boolean).join(" + ");
      const note = (substitution.note || "").trim();
      return foods ? { label: foods, note } : { label: note, note: "" };
    })
    .filter(tag => tag.label),
);
</script>

<style scoped>
.substitution-tag :deep(.v-icon) {
  cursor: pointer;
}
</style>
