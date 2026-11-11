<template>
  <BaseDurationPicker
    v-if="isEditMode"
    :model-value="modelValue ?? null"
    class="step-duration"
    :label="label || $t('recipe.step-duration-label')"
    :icon="icon"
    @update:model-value="emit('update:modelValue', $event ?? null)"
    @click.stop
  />
  <span
    v-else-if="modelValue"
    class="step-time"
    :title="label"
  >
    <v-icon v-if="icon" size="14" class="step-time__icon">{{ icon }}</v-icon>
    {{ formattedDuration }}
  </span>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";

const props = defineProps<{
  modelValue?: number | null;
  isEditMode: boolean;
  label?: string;
  icon?: string;
}>();
const emit = defineEmits<{ "update:modelValue": [value: number | null] }>();
const { t } = useI18n();

const formattedDuration = computed(() => {
  const seconds = props.modelValue ?? 0;
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainder = seconds % 60;
  return [
    hours ? t("recipe.step-duration-value-hours", { hours }) : "",
    minutes ? t("recipe.step-duration-value-minutes", { minutes }) : "",
    remainder ? t("recipe.step-duration-value-seconds", { seconds: remainder }) : "",
  ].filter(Boolean).join(" ");
});
</script>

<style scoped>
/* All step times share the same reduced size. */
.step-time {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 0.8rem;
  line-height: 1.2;
  white-space: nowrap;
  opacity: 0.85;
}

/* Override the instruction title's larger input text only for this field. */
.step-duration :deep(input) {
  font-size: 1rem;
}
</style>
