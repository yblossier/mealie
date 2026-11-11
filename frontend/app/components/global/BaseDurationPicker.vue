<template>
  <div class="base-duration-picker">
    <v-text-field
      :model-value="display"
      :label="label"
      :placeholder="placeholder"
      :density="density"
      :variant="variant"
      :hint="hint"
      :persistent-hint="!!hint"
      hide-details="auto"
      readonly
      clearable
      data-testid="duration-picker-field"
      @click.stop="openPicker"
      @keydown.enter.prevent="openPicker"
      @keydown.space.prevent="openPicker"
      @click:clear="clear"
    >
      <!-- Outside the field so the underline does not run under it -->
      <template #prepend>
        <v-icon
          :color="seconds ? 'primary' : undefined"
          data-testid="duration-picker-icon"
          @click.stop="openPicker"
        >
          {{ icon || $globals.icons.clockOutline }}
        </v-icon>
      </template>
    </v-text-field>
    <component
      :is="$vuetify.display.xs ? VBottomSheet : VDialog"
      v-model="open"
      max-width="340"
    >
      <v-card class="m3-picker" rounded="xl" data-testid="duration-picker">
        <div class="m3-picker__headline">
          {{ label || $t("recipe.step-duration-label") }}
        </div>

        <div class="m3-picker__fields">
          <div v-for="(part, index) in parts" :key="part.key" class="d-contents">
            <span v-if="index" class="m3-picker__separator">:</span>
            <div class="m3-picker__field">
              <input
                v-if="mode === 'input'"
                class="m3-picker__box m3-picker__box--input"
                :class="{ 'm3-picker__box--active': active === part.key }"
                :value="draft[part.key]"
                inputmode="numeric"
                :maxlength="part.key === 'hours' ? 3 : 2"
                :aria-label="part.unit"
                :data-testid="`duration-${part.key}`"
                @focus="active = part.key"
                @input="onType(part.key, $event)"
                @keydown.up.prevent="step(part.key, 1)"
                @keydown.down.prevent="step(part.key, -1)"
              >
              <button
                v-else
                type="button"
                class="m3-picker__box"
                :class="{ 'm3-picker__box--active': active === part.key }"
                :aria-label="part.unit"
                :aria-pressed="active === part.key"
                :data-testid="`duration-${part.key}`"
                @click="active = part.key"
                @keydown.up.prevent="step(part.key, 1)"
                @keydown.down.prevent="step(part.key, -1)"
              >
                {{ pad(draft[part.key]) }}
              </button>
              <span class="m3-picker__unit">{{ part.unit }}</span>
            </div>
          </div>
        </div>

        <div
          v-if="mode === 'dial'"
          ref="dialRef"
          class="m3-picker__dial"
          :style="{ width: `${DIAL}px`, height: `${DIAL}px` }"
          role="slider"
          tabindex="0"
          :aria-label="parts.find(part => part.key === active)?.unit"
          :aria-valuenow="draft[active]"
          aria-valuemin="0"
          :aria-valuemax="active === 'hours' ? 23 : 59"
          data-testid="duration-dial"
          @pointerdown="onDialDown"
          @pointermove="onDialMove"
          @pointerup="onDialUp"
          @keydown.right.prevent="step(active, 1)"
          @keydown.up.prevent="step(active, 1)"
          @keydown.left.prevent="step(active, -1)"
          @keydown.down.prevent="step(active, -1)"
        >
          <svg class="m3-picker__hand" :viewBox="`0 0 ${DIAL} ${DIAL}`">
            <circle :cx="CENTER" :cy="CENTER" r="4" />
            <line :x1="CENTER" :y1="CENTER" :x2="hand.x" :y2="hand.y" />
            <circle :cx="hand.x" :cy="hand.y" r="24" />
          </svg>
          <span
            v-for="mark in marks"
            :key="mark.value"
            class="m3-picker__mark"
            :class="{ 'm3-picker__mark--selected': mark.value === draft[active], 'm3-picker__mark--inner': mark.inner }"
            :style="{ left: `${mark.x}px`, top: `${mark.y}px` }"
          >
            {{ mark.label }}
          </span>
        </div>

        <div class="m3-picker__presets">
          <v-chip
            v-for="preset in PRESET_MINUTES"
            :key="preset"
            size="small"
            variant="tonal"
            :color="draftSeconds === preset * 60 ? 'primary' : undefined"
            :data-testid="`duration-preset-${preset}`"
            @click="applyPreset(preset)"
          >
            {{ shortDuration(preset) }}
          </v-chip>
        </div>

        <div class="m3-picker__preview" data-testid="duration-picker-preview">
          {{ draftSeconds ? formatDuration(draftSeconds, locale) : "—" }}
        </div>

        <v-card-actions class="m3-picker__actions">
          <v-btn
            icon
            variant="text"
            size="small"
            :aria-label="mode === 'dial' ? $t('general.duration-picker-keyboard') : $t('general.duration-picker-dial')"
            data-testid="duration-picker-mode"
            @click="mode = mode === 'dial' ? 'input' : 'dial'"
          >
            <v-icon>{{ mode === "dial" ? $globals.icons.keyboard : $globals.icons.clockOutline }}</v-icon>
          </v-btn>
          <v-spacer />
          <BaseButton
            cancel
            data-testid="duration-picker-cancel"
            @click="open = false"
          />
          <BaseButton
            data-testid="duration-picker-confirm"
            @click="confirm"
          >
            <template #icon>
              {{ $globals.icons.check }}
            </template>
            {{ $t("general.confirm") }}
          </BaseButton>
        </v-card-actions>
      </v-card>
    </component>
  </div>
</template>

<script setup lang="ts">
import { VBottomSheet } from "vuetify/components/VBottomSheet";
import { VDialog } from "vuetify/components/VDialog";
import { durationUnitLabel, formatDuration } from "~/composables/recipes/use-recipe-time";

/**
 * Picks a duration (stored in seconds) the Material Design 3 time picker way: hours and
 * minutes boxes with a clock dial, or typed in with the keyboard.
 */
withDefaults(defineProps<{
  label?: string;
  icon?: string;
  hint?: string;
  placeholder?: string;
  density?: "default" | "comfortable" | "compact";
  variant?: "underlined" | "outlined" | "filled" | "solo" | "plain";
}>(), {
  label: "",
  icon: "",
  hint: undefined,
  placeholder: undefined,
  density: "compact",
  variant: "underlined",
});

const seconds = defineModel<number | null | undefined>({ required: true });

type PartKey = "hours" | "minutes";
const DIAL = 256;
const CENTER = DIAL / 2;
const OUTER_RADIUS = 101;
const INNER_RADIUS = 66;
const MAX_HOURS = 999;
const PRESET_MINUTES = [5, 10, 15, 20, 30, 45, 60, 90, 120];

const i18n = useI18n();
const locale = computed(() => i18n.locale.value);

const open = ref(false);
const mode = ref<"dial" | "input">("dial");
const active = ref<PartKey>("hours");
const draft = reactive<Record<PartKey, number>>({ hours: 0, minutes: 0 });
const dialRef = ref<HTMLElement | null>(null);
const dragging = ref(false);

const display = computed(() => (seconds.value ? formatDuration(seconds.value, locale.value) : ""));
const draftSeconds = computed(() => draft.hours * 3600 + draft.minutes * 60);

const parts = computed(() => [
  { key: "hours" as const, unit: durationUnitLabel("hour", locale.value) },
  { key: "minutes" as const, unit: durationUnitLabel("minute", locale.value) },
]);

function pad(value: number) {
  return String(value).padStart(2, "0");
}

/** "5min", "1h", "1h30" — short enough for a row of chips */
function shortDuration(minutes: number) {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (!hours) return `${rest}min`;
  return rest ? `${hours}h${pad(rest)}` : `${hours}h`;
}

function point(index: number, radius: number) {
  const angle = (index / 12) * 2 * Math.PI;
  return { x: CENTER + radius * Math.sin(angle), y: CENTER - radius * Math.cos(angle) };
}

const marks = computed(() => {
  if (active.value === "minutes") {
    return Array.from({ length: 12 }, (_, i) => ({ value: i * 5, label: pad(i * 5), inner: false, ...point(i, OUTER_RADIUS) }));
  }
  return Array.from({ length: 24 }, (_, value) => {
    const inner = value >= 12;
    return { value, label: String(value), inner, ...point(value % 12, inner ? INNER_RADIUS : OUTER_RADIUS) };
  });
});

const hand = computed(() => {
  if (active.value === "minutes") {
    return point(draft.minutes / 5, OUTER_RADIUS);
  }
  // Durations past a day are typed in; the hand rests on the hour of the day
  const hours = draft.hours % 24;
  return point(hours % 12, hours >= 12 ? INNER_RADIUS : OUTER_RADIUS);
});

function openPicker() {
  const value = seconds.value ?? 0;
  draft.hours = Math.min(MAX_HOURS, Math.floor(value / 3600));
  draft.minutes = Math.floor((value % 3600) / 60);
  active.value = "hours";
  mode.value = "dial";
  open.value = true;
}

function clamp(key: PartKey, value: number) {
  return Math.min(key === "hours" ? MAX_HOURS : 59, Math.max(0, value));
}

function step(key: PartKey, delta: number) {
  draft[key] = clamp(key, draft[key] + delta);
}

function onType(key: PartKey, event: Event) {
  const input = event.target as HTMLInputElement;
  const digits = input.value.replace(/\D/g, "");
  draft[key] = clamp(key, Number(digits || 0));
  input.value = digits ? String(draft[key]) : "";
}

function valueAt(event: PointerEvent): number | null {
  const rect = dialRef.value?.getBoundingClientRect();
  if (!rect || !rect.width) return null;
  const dx = event.clientX - rect.left - rect.width / 2;
  const dy = event.clientY - rect.top - rect.height / 2;
  const turn = ((Math.atan2(dx, -dy) / (2 * Math.PI)) + 1) % 1;
  if (active.value === "minutes") {
    return Math.round(turn * 60) % 60;
  }
  const scale = rect.width / DIAL;
  const inner = Math.hypot(dx, dy) < ((OUTER_RADIUS + INNER_RADIUS) / 2) * scale;
  return (Math.round(turn * 12) % 12) + (inner ? 12 : 0);
}

function pick(event: PointerEvent) {
  const value = valueAt(event);
  if (value !== null) {
    draft[active.value] = value;
  }
}

function onDialDown(event: PointerEvent) {
  dragging.value = true;
  (event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId);
  pick(event);
}

function onDialMove(event: PointerEvent) {
  if (dragging.value) pick(event);
}

function onDialUp(event: PointerEvent) {
  if (!dragging.value) return;
  dragging.value = false;
  pick(event);
  // Same flow as the Material clock: the minutes come right after the hour
  if (active.value === "hours") {
    active.value = "minutes";
  }
}

function applyPreset(minutes: number) {
  draft.hours = Math.floor(minutes / 60);
  draft.minutes = minutes % 60;
}

function confirm() {
  const current = seconds.value ?? 0;
  // Imported times can carry seconds the picker doesn't show; keep them while hours and minutes are unchanged
  if (draftSeconds.value !== current - (current % 60)) {
    seconds.value = draftSeconds.value || null;
  }
  open.value = false;
}

function clear() {
  seconds.value = null;
}

defineExpose({ openPicker });
</script>

<style scoped>
.base-duration-picker :deep(input) {
  cursor: pointer;
}
.base-duration-picker :deep(.v-input__prepend) {
  margin-inline-end: 6px;
}
.d-contents {
  display: contents;
}
.m3-picker {
  padding: 24px 24px 12px;
}
.m3-picker__headline {
  font-size: 0.75rem;
  font-weight: 500;
  letter-spacing: 0.04em;
  opacity: 0.7;
  margin-bottom: 20px;
}
.m3-picker__fields {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 4px;
}
.m3-picker__field {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.m3-picker__box {
  width: 96px;
  height: 80px;
  border-radius: 8px;
  border: 2px solid transparent;
  background: rgba(var(--v-theme-on-surface), 0.08);
  color: rgb(var(--v-theme-on-surface));
  font-size: 3.5rem;
  line-height: 1;
  text-align: center;
  font-variant-numeric: tabular-nums;
  outline: none;
}
.m3-picker__box--active {
  background: rgba(var(--v-theme-primary), 0.16);
  color: rgb(var(--v-theme-primary));
}
.m3-picker__box--input.m3-picker__box--active {
  border-color: rgb(var(--v-theme-primary));
}
.m3-picker__unit {
  font-size: 0.75rem;
  opacity: 0.7;
}
.m3-picker__separator {
  font-size: 3.5rem;
  line-height: 80px;
  width: 24px;
  text-align: center;
}
.m3-picker__dial {
  position: relative;
  margin: 24px auto 0;
  border-radius: 50%;
  background: rgba(var(--v-theme-on-surface), 0.08);
  touch-action: none;
  user-select: none;
  cursor: pointer;
  outline: none;
}
.m3-picker__dial:focus-visible {
  box-shadow: 0 0 0 2px rgb(var(--v-theme-primary));
}
.m3-picker__hand {
  position: absolute;
  inset: 0;
  fill: rgb(var(--v-theme-primary));
  stroke: rgb(var(--v-theme-primary));
  stroke-width: 2;
  pointer-events: none;
}
.m3-picker__mark {
  position: absolute;
  width: 48px;
  height: 48px;
  margin: -24px 0 0 -24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  pointer-events: none;
}
.m3-picker__mark--inner {
  font-size: 0.875rem;
  opacity: 0.8;
}
.m3-picker__mark--selected {
  color: rgb(var(--v-theme-on-primary));
  opacity: 1;
}
.m3-picker__presets {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 4px;
  margin-top: 20px;
}
.m3-picker__preview {
  margin-top: 8px;
  text-align: center;
  font-size: 0.8rem;
  opacity: 0.7;
}
.m3-picker__actions {
  padding: 8px 0 0;
}
</style>
