<template>
  <div>
    <div
      v-for="substitution, i in substitutions"
      :key="i"
      class="mb-3"
      :class="{ 'border-thin rounded-lg pa-3': framed }"
      data-testid="substitution-row"
    >
      <v-btn-toggle
        :model-value="isCombination(substitution) ? 'combination' : 'single'"
        mandatory
        density="compact"
        variant="outlined"
        color="primary"
        divided
        class="mb-2 substitution-kind"
        data-testid="substitution-kind"
        @update:model-value="setKind(substitution, i, $event)"
      >
        <v-btn value="single" size="small">
          <v-icon start size="small">
            {{ $globals.icons.swapHorizontal }}
          </v-icon>
          {{ $t("recipe.substitution-single") }}
        </v-btn>
        <v-btn value="combination" size="small">
          <v-icon start size="small">
            {{ $globals.icons.create }}
          </v-icon>
          {{ $t("recipe.substitution-combination") }}
        </v-btn>
      </v-btn-toggle>
      <!-- wraps rather than stacking: on a narrow screen the food takes its own line and the
           note keeps the delete button company, instead of stranding it on a line of its own -->
      <div class="d-flex ga-2 align-center flex-wrap">
        <v-autocomplete
          v-model="substitution.substituteFoodId"
          :items="foods"
          :custom-filter="normalizeFilter"
          item-value="id"
          item-title="name"
          :placeholder="isCombination(substitution) ? $t('recipe.choose-first-combination-food') : $t('recipe.choose-substitute-food')"
          :style="$vuetify.display.mdAndDown ? 'flex: 1 1 100%;' : 'flex: 6 0 50px;'"
          :menu-props="{ attach: menuAttachTarget, maxHeight: '250px' }"
          density="compact"
          variant="filled"
          clearable
          hide-details
          @update:model-value="emit('food-changed', i)"
        />
        <template v-if="isCombination(substitution)">
          <!-- one row per food of the combination, so it can hold two foods or more -->
          <div
            v-for="(_, k) in substitution.additionalFoodIds"
            :key="k"
            class="d-flex ga-2 align-center w-100"
            data-testid="substitution-combination-food"
          >
            <v-icon class="combination-plus">
              {{ $globals.icons.create }}
            </v-icon>
            <v-autocomplete
              v-model="substitution.additionalFoodIds![k]"
              :items="additionalFoodOptions(substitution, k)"
              :custom-filter="normalizeFilter"
              item-value="id"
              item-title="name"
              :placeholder="$t('recipe.choose-combination-food')"
              :menu-props="{ attach: menuAttachTarget, maxHeight: '250px' }"
              density="compact"
              variant="filled"
              hide-details
              class="flex-grow-1"
              @update:model-value="emit('food-changed', i)"
            />
            <v-btn
              icon
              variant="plain"
              :disabled="substitution.additionalFoodIds!.length < 2"
              :title="$t('recipe.remove-combination-food')"
              data-testid="substitution-combination-remove"
              @click="removeCombinationFood(substitution, i, k)"
            >
              <v-icon>{{ $globals.icons.close }}</v-icon>
            </v-btn>
          </div>
          <v-btn
            variant="text"
            size="small"
            color="primary"
            data-testid="substitution-combination-add"
            @click="addCombinationFood(substitution)"
          >
            <v-icon start>
              {{ $globals.icons.create }}
            </v-icon>
            {{ $t("recipe.add-combination-food") }}
          </v-btn>
          <div class="w-100" />
        </template>
        <v-text-field
          v-model="substitution.note"
          :placeholder="$t('recipe.substitution-note-optional')"
          :style="$vuetify.display.mdAndDown ? 'flex: 1 1 0;' : 'flex: 4 0 50px;'"
          density="compact"
          variant="filled"
          hide-details
        />
        <!-- left at the default size: an icon button is a 36px touch target everywhere else in
             the app, and the smaller sizes fall under the 24px accessible minimum -->
        <v-btn
          icon
          variant="plain"
          :title="$t('general.delete')"
          @click="emit('delete', i)"
        >
          <v-icon>{{ $globals.icons.delete }}</v-icon>
        </v-btn>
      </div>
      <slot name="after-row" :substitution="substitution" :index="i" />
    </div>
    <v-btn
      variant="text"
      color="primary"
      @click="emit('add')"
    >
      <v-icon start>
        {{ $globals.icons.create }}
      </v-icon>
      {{ $t("general.add") }}
    </v-btn>
  </div>
</template>

<script setup lang="ts">
import { normalizeFilter } from "~/composables/use-utils";
import type { IngredientFoodOut } from "~/lib/api/types/recipe";

/**
 * The shape both tiers share. Callers hold richer rows of their own -- the food dialog tracks a
 * reverse-substitution choice alongside each one -- so rows are mutated in place here and added
 * or removed by the caller, which is the only side that knows what a new row should contain.
 */
export interface EditableSubstitution {
  substituteFoodId?: string | null;
  /** The other foods of a combination, used together with the substitute food */
  additionalFoodIds?: string[];
  note?: string | null;
}

interface Props {
  substitutions: EditableSubstitution[];
  foods: IngredientFoodOut[];
  // left unset inside a dialog, so the menu stays in Vuetify's overlay stack rather than being
  // teleported to the body and risking a render behind the dialog
  menuAttachTarget?: string;
  /** Draws a frame around each substitution, to tell them apart */
  framed?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  "add": [];
  "delete": [index: number];
  "food-changed": [index: number];
}>();

// a row switched to a combination stays one while its other foods are still being chosen
const combinationRows = reactive(new WeakSet<EditableSubstitution>());

function isCombination(substitution: EditableSubstitution) {
  return combinationRows.has(substitution) || !!substitution.additionalFoodIds?.length;
}

function setKind(substitution: EditableSubstitution, index: number, kind: unknown) {
  if (kind === "combination") {
    combinationRows.add(substitution);
    if (!substitution.additionalFoodIds?.length) {
      // a combination joins at least two foods: the substitute food and one more
      substitution.additionalFoodIds = [""];
    }
    return;
  }
  combinationRows.delete(substitution);
  if (substitution.additionalFoodIds?.length) {
    substitution.additionalFoodIds = [];
    emit("food-changed", index);
  }
}

/** The foods row `k` of a combination may take: none already used elsewhere in the combination */
function additionalFoodOptions(substitution: EditableSubstitution, k: number) {
  const taken = new Set([
    substitution.substituteFoodId,
    ...(substitution.additionalFoodIds ?? []).filter((_, index) => index !== k),
  ]);
  return props.foods.filter(food => !taken.has(food.id));
}

function addCombinationFood(substitution: EditableSubstitution) {
  substitution.additionalFoodIds = [...(substitution.additionalFoodIds ?? []), ""];
}

function removeCombinationFood(substitution: EditableSubstitution, index: number, k: number) {
  const foods = substitution.additionalFoodIds ?? [];
  if (foods.length < 2) {
    return;
  }
  substitution.additionalFoodIds = foods.filter((_, position) => position !== k);
  emit("food-changed", index);
}
</script>

<style scoped>
.substitution-kind :deep(.v-btn) {
  text-transform: none;
}

.combination-plus {
  opacity: 0.6;
}
</style>
