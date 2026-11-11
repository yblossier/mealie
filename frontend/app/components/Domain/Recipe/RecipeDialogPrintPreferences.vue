<template>
  <BaseDialog
    v-model="dialog"
    :icon="$globals.icons.printerSettings"
    :title="$t('general.print-preferences')"
    width="70%"
    max-width="816px"
  >
    <div class="pa-6">
      <div class="print-config mb-3">
        <div class="print-option print-option--image">
          <v-switch
            v-model="preferences.showImage"
            hide-details
            color="primary"
            density="compact"
            data-testid="print-show-image"
            :label="$t('recipe.print-image')"
          />
          <v-btn-toggle
            v-model="preferences.imagePosition"
            mandatory="force"
            density="compact"
            variant="outlined"
            divided
            class="print-image-position flex-shrink-0"
            data-testid="print-image-position"
            :disabled="!preferences.showImage"
          >
            <v-btn
              :value="ImagePosition.left"
              :aria-label="$t('recipe.print-image-left')"
              :title="$t('recipe.print-image-left')"
            >
              <v-icon>{{ $globals.icons.dockLeft }}</v-icon>
            </v-btn>
            <v-btn
              :value="ImagePosition.right"
              :aria-label="$t('recipe.print-image-right')"
              :title="$t('recipe.print-image-right')"
            >
              <v-icon>{{ $globals.icons.dockRight }}</v-icon>
            </v-btn>
          </v-btn-toggle>
        </div>
        <div
          v-for="option in options"
          :key="option.key"
          class="print-option"
        >
          <v-switch
            v-model="preferences[option.key]"
            hide-details
            color="primary"
            density="compact"
            :data-testid="option.testId"
            :label="option.label"
          />
        </div>
      </div>
      <v-card
        height="fit-content"
        max-height="40vh"
        width="100%"
        class="print-preview"
        style="overflow-y: auto;"
      >
        <RecipePrintView :recipe="recipe" />
      </v-card>
    </div>
  </BaseDialog>
</template>

<script setup lang="ts">
import type { RecipeOut } from "~/lib/api/types/recipe";
import { ImagePosition, useUserPrintPreferences } from "~/composables/use-users/preferences";
import type { UserPrintPreferences } from "~/composables/use-users/preferences";
import RecipePrintView from "~/components/Domain/Recipe/RecipePrintView.vue";

interface Props {
  recipe?: RecipeOut;
}
withDefaults(defineProps<Props>(), {
  recipe: undefined,
});

const dialog = defineModel<boolean>({ default: false });
const preferences = useUserPrintPreferences();
const i18n = useI18n();

type BooleanPreference = {
  [K in keyof UserPrintPreferences]: UserPrintPreferences[K] extends boolean ? K : never
}[keyof UserPrintPreferences];

const options = computed<{ key: BooleanPreference; label: string; testId?: string }[]>(() => [
  { key: "showDescription", label: i18n.t("recipe.description") },
  { key: "showNotes", label: i18n.t("recipe.notes") },
  { key: "showNutrition", label: i18n.t("recipe.nutrition") },
  { key: "showTools", label: i18n.t("recipe.print-tools"), testId: "print-show-tools" },
  { key: "expandChildRecipes", label: i18n.t("recipe.include-linked-recipe-ingredients") },
  { key: "showLinkedIngredients", label: i18n.t("recipe.linked-ingredients") },
  { key: "showAllergens", label: i18n.t("recipe.allergy-title") },
  { key: "showSubstitutions", label: i18n.t("recipe.substitutions") },
]);
</script>

<style scoped>
.print-config {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 4px 16px;
  align-items: center;
}

.print-option {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.print-option :deep(.v-switch) {
  flex: 1 1 auto;
  min-width: 0;
}

.print-option--image :deep(.v-switch) {
  flex: 0 1 auto;
}

.print-image-position .v-btn {
  height: auto;
  min-width: 32px;
  margin: 0;
  padding: 0;
}

.print-option :deep(.v-selection-control) {
  min-height: var(--v-selection-control-size);
  height: auto;
}

.print-option :deep(.v-label) {
  white-space: normal;
  overflow: visible;
  text-overflow: clip;
  word-break: break-word;
  line-height: 1.2;
  height: auto;
}
</style>
