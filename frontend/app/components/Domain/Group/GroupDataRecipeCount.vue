<template>
  <v-tooltip location="bottom" open-delay="200" content-class="text-caption">
    <template #activator="{ props: tooltipProps }">
      <v-chip
        v-bind="tooltipProps"
        size="small"
        :color="count > 0 ? 'primary' : undefined"
        :variant="count > 0 ? 'flat' : 'tonal'"
        :to="count > 0 && to ? to : undefined"
        class="recipe-count-bubble mr-1 justify-center"
        data-testid="recipe-count-bubble"
      >
        {{ count }}
      </v-chip>
    </template>
    <span>{{ $t("data-pages.recipe-count-tooltip", { count }, count) }}</span>
  </v-tooltip>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  count?: number;
  /** Recipe search filtered on the item, followed when the bubble is clicked */
  to?: string | null;
}>(), {
  count: 0,
  to: null,
});
</script>

<style scoped>
.recipe-count-bubble {
  min-width: 32px;
  border-radius: 999px;
}
</style>
