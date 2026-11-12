<template>
  <div v-if="value && value.length > 0">
    <div
      v-if="!isCookMode"
      class="d-flex justify-start"
    >
      <h2 class="mt-1 text-headline-small font-weight-medium opacity-80">
        {{ $t("recipe.ingredients") }}
      </h2>
      <AppButtonCopy
        btn-class="ml-auto"
        :copy-text="ingredientCopyText"
      />
    </div>
    <div>
      <div
        v-for="(ingredient, index) in value"
        :key="'ingredient' + index"
      >
        <h3
          v-if="showTitleEditor[index]"
          class="mt-4 mb-0"
        >
          {{ ingredient.title }}
        </h3>
        <v-divider v-if="showTitleEditor[index]" class="my-2" />
        <v-list-item
          density="compact"
          class="px-0 py-1 ingredient-list-item"
          @click.stop="toggleChecked(index)"
        >
          <template #prepend>
            <v-checkbox
              :model-value="isChecked(index)"
              hide-details
              class="pt-0 mt-0"
              color="secondary"
              density="comfortable"
              @click.stop
              @update:model-value="setChecked(index, !!$event)"
            />
          </template>
          <v-list-item-title>
            <RecipeIngredientListItem
              :ingredient="ingredient"
              :scale="scale"
              show-substitutions
              highlight-allergens
            />
          </v-list-item-title>
          <template
            v-if="ingredientAllergens(ingredient).length || canAddToList(ingredient)"
            #append
          >
            <div class="d-flex align-center ingredient-actions">
              <!-- opens on a tap too: the recipe is read on phones, where nothing hovers -->
              <v-tooltip
                v-if="ingredientAllergens(ingredient).length"
                location="top"
                open-on-click
              >
                <template #activator="{ props: tooltipProps }">
                  <v-icon
                    v-bind="tooltipProps"
                    size="18"
                    color="error"
                    class="ms-1"
                    data-testid="ingredient-allergen-info"
                    :aria-label="$t('recipe.ingredient-allergens', { allergens: ingredientAllergens(ingredient).join(', ') })"
                    @click.stop
                  >
                    {{ $globals.icons.informationOutline }}
                  </v-icon>
                </template>
                <span>{{ $t("recipe.ingredient-allergens", { allergens: ingredientAllergens(ingredient).join(", ") }) }}</span>
              </v-tooltip>
              <RecipeIngredientAddToListMenu
                v-if="canAddToList(ingredient)"
                :ingredient="ingredient"
                :recipe-id="recipeId!"
                :scale="scale"
              />
            </div>
          </template>
        </v-list-item>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import RecipeIngredientListItem from "./RecipeIngredientListItem.vue";
import RecipeIngredientAddToListMenu from "./RecipeIngredientAddToListMenu.vue";
import { useLoggedInState } from "~/composables/use-logged-in-state";
import { useSessionStorage } from "@vueuse/core";
import { useIngredientTextParser } from "~/composables/recipes";
import type { RecipeIngredient } from "~/lib/api/types/recipe";
import { ingredientAllergenNames } from "~/lib/recipe/ingredient-allergens";

interface Props {
  value?: RecipeIngredient[];
  scale?: number;
  isCookMode?: boolean;
  storageKey?: string;
  /** Lets an ingredient the household doesn't have be sent to a shopping list on its own. */
  recipeId?: string | null;
}
const props = withDefaults(defineProps<Props>(), {
  value: () => [],
  scale: 1,
  isCookMode: false,
  storageKey: undefined,
  recipeId: undefined,
});

const auth = useMealieAuth();
const { isOwnGroup } = useLoggedInState();

function ingredientAllergens(ingredient: RecipeIngredient): string[] {
  return ingredientAllergenNames(ingredient);
}

function canAddToList(ingredient: RecipeIngredient) {
  const household = auth.user.value?.householdSlug;
  const food = ingredient.food as { id?: string; householdsWithIngredientFood?: string[] } | null | undefined;
  if (!props.recipeId || !isOwnGroup.value || !household || !food?.id) {
    return false;
  }
  return !(food.householdsWithIngredientFood ?? []).includes(household);
}

const { parseIngredientText } = useIngredientTextParser();

function validateTitle(title?: string | null) {
  return !(title === undefined || title === "" || title === null);
}

const transientChecked = ref<Record<string, boolean>>({});
const sessionChecked = props.storageKey
  ? useSessionStorage<Record<string, boolean>>(props.storageKey, {})
  : null;
const showTitleEditor = computed(() => props.value.map(x => validateTitle(x.title)));

const ingredientCopyText = computed(() => {
  const components: string[] = [];
  props.value.forEach((ingredient) => {
    if (ingredient.title) {
      if (components.length) {
        components.push("");
      }

      components.push(`[${ingredient.title}]`);
    }

    components.push(parseIngredientText(ingredient, props.scale, false));
  });

  return components.join("\n");
});

function toggleChecked(index: number) {
  setChecked(index, !isChecked(index));
}

function checkedState() {
  return sessionChecked?.value ?? transientChecked.value;
}

function checkedKey(index: number) {
  const referenceId = props.value[index]?.referenceId;
  return referenceId ? `ref:${referenceId}` : `idx:${index}`;
}

function isChecked(index: number) {
  return !!checkedState()[checkedKey(index)];
}

function setChecked(index: number, value: boolean) {
  const state = checkedState();
  state[checkedKey(index)] = value;

  if (sessionChecked) {
    sessionChecked.value = { ...state };
  }
  else {
    transientChecked.value = { ...state };
  }
}
</script>

<style>
.dense-markdown p {
  margin: auto !important;
}

/* vuetify clips both of these, which would swallow the substitution button's tap target
   where it reaches past the line of text */
.ingredient-list-item .v-list-item__content,
.ingredient-list-item .v-list-item-title {
  overflow: visible;
}

.ingredient-list-item {
  align-items: flex-start;
}

.ingredient-list-item .v-list-item__prepend,
.ingredient-list-item .v-list-item__content,
.ingredient-list-item .v-list-item__append {
  align-self: flex-start;
}

/* the checkbox is shrunk to the height of a line of text, so its box sits level with the
   first line of the ingredient however many lines it wraps to */
.ingredient-list-item .v-selection-control {
  --v-selection-control-size: 1.5rem;
  align-self: flex-start;
  min-height: 1.5rem;
  height: 1.5rem;
  margin-top: 0;
}

.ingredient-list-item .v-list-item__prepend > .v-input {
  margin-inline-end: 8px;
}

.ingredient-list-item .v-list-item__append,
.ingredient-actions {
  height: 1.5rem;
}

/* the cart only shows on the hovered ingredient; touch screens can't hover, so they always see it */
.ingredient-list-item .ingredient-shop-btn {
  opacity: 0;
  transition: opacity 0.15s;
}

.ingredient-list-item:hover .ingredient-shop-btn,
.ingredient-list-item:focus-within .ingredient-shop-btn,
.ingredient-shop-btn[aria-expanded="true"] {
  opacity: 1;
}

@media (hover: none) {
  .ingredient-list-item .ingredient-shop-btn {
    opacity: 1;
  }
}
</style>
