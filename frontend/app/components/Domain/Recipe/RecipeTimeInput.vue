<template>
  <div
    class="recipe-time-input"
    :class="{ 'recipe-time-input--with-text': !hideText }"
  >
    <BaseDurationPicker
      v-model="seconds"
      :label="label"
      :icon="icon"
    />
    <!-- Free text shown after the structured time, e.g. "3 hours" + "plus overnight" -->
    <v-text-field
      v-if="!hideText"
      v-model="text"
      :label="$t('recipe.time-note-label')"
      :hint="$t('recipe.time-note-hint')"
      :prepend-icon="$globals.icons.noteTextOutline"
      density="compact"
      variant="underlined"
      hide-details="auto"
      data-testid="recipe-time-note"
    />
  </div>
</template>

<script setup lang="ts">
defineProps<{ label?: string; icon?: string; hideText?: boolean }>();

const seconds = defineModel<number | null | undefined>("seconds", { required: true });
const text = defineModel<string | null | undefined>("text");
</script>

<style scoped>
/* Both fields share the same density, label and prepend icon, so their inputs line up whether side by side or stacked */
.recipe-time-input--with-text {
  display: grid;
  grid-template-columns: 1fr;
  align-items: start;
  gap: 0.25rem 1rem;
  margin-bottom: 0.5rem;
}
@media (min-width: 600px) {
  .recipe-time-input--with-text {
    grid-template-columns: minmax(14em, 20em) minmax(0, 1fr);
  }
}
</style>
