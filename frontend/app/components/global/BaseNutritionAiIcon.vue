<template>
  <span
    class="base-nutrition-ai-icon"
    :style="{ width: `${size}px`, height: `${size}px` }"
    data-testid="nutrition-ai-icon"
    aria-hidden="true"
  >
    <svg viewBox="0 0 24 24" width="100%" height="100%">
      <path :d="$globals.icons.robot" fill="currentColor" />
    </svg>
  </span>
</template>

<script setup lang="ts">
/**
 * The AI robot, used by every button that fills nutrition facts automatically.
 * `background` is kept for API compatibility with existing callers.
 */
withDefaults(defineProps<{
  size?: number;
  background?: string;
}>(), {
  size: 24,
  background: "surface",
});
</script>

<style scoped>
.base-nutrition-ai-icon {
  display: inline-flex;
  flex: none;
  vertical-align: middle;
}
</style>
