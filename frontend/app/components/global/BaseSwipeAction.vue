<template>
  <div
    ref="root"
    class="base-swipe-action"
    :class="{ 'base-swipe-action--active': isActive }"
    :style="active ? { touchAction: 'pan-y' } : undefined"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointercancel="onPointerCancel"
    @click.capture="onClickCapture"
  >
    <div
      v-if="isActive && visibleSide"
      class="base-swipe-action__background"
      :class="[`bg-${currentAction?.color}`, visibleSide === 'left' ? 'justify-end' : 'justify-start']"
    >
      <button
        type="button"
        class="base-swipe-action__button"
        :style="{ width: `${actionWidth}px` }"
        :aria-label="currentAction?.label"
        :data-testid="`swipe-action-${visibleSide}`"
        @click.stop="runAction(visibleSide)"
      >
        <v-icon>{{ currentAction?.icon }}</v-icon>
        <span class="base-swipe-action__label">{{ currentAction?.label }}</span>
      </button>
    </div>
    <div
      class="base-swipe-action__content"
      :style="{
        transform: offset ? `translateX(${offset}px)` : undefined,
        transition: dragging ? 'none' : 'transform 0.2s ease',
      }"
    >
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onClickOutside } from "@vueuse/core";
import { useDisplay } from "vuetify";
import {
  classifySwipeGesture,
  clampSwipeOffset,
  resolveSwipeRelease,
  swipeSideForOffset,
  type SwipeGesture,
  type SwipeSide,
} from "~/composables/use-swipe-action";

export interface SwipeActionConfig {
  icon: string;
  label: string;
  color?: string;
}

const props = withDefaults(defineProps<{
  /** action uncovered by swiping left */
  leftAction?: SwipeActionConfig | null;
  /** action uncovered by swiping right */
  rightAction?: SwipeActionConfig | null;
  disabled?: boolean;
  /** touches starting on these elements are ignored (e.g. drag-and-drop handles) */
  ignoreSelector?: string;
  actionWidth?: number;
}>(), {
  leftAction: null,
  rightAction: null,
  disabled: false,
  ignoreSelector: ".handle",
  actionWidth: 88,
});

const emit = defineEmits<{
  (e: "swipe-left" | "swipe-right"): void;
}>();

const root = ref<HTMLElement | null>(null);
const offset = ref(0);
const dragging = ref(false);
const revealed = ref<SwipeSide | null>(null);

const { mdAndDown } = useDisplay();

// swiping is meant for phones and tablets; desktop keeps the regular buttons
const active = computed(() => !props.disabled && mdAndDown.value && !!(props.leftAction || props.rightAction));
const isActive = computed(() => offset.value !== 0 || dragging.value);
const visibleSide = computed(() => swipeSideForOffset(offset.value));
const currentAction = computed(() => {
  const side = visibleSide.value;
  const action = side === "left" ? props.leftAction : side === "right" ? props.rightAction : null;
  return action ? { color: "primary", ...action } : null;
});

let pointerId: number | null = null;
let startX = 0;
let startY = 0;
let startOffset = 0;
let gesture: SwipeGesture = "pending";
let suppressClick = false;

function close() {
  offset.value = 0;
  revealed.value = null;
  dragging.value = false;
}

function resetTracking() {
  pointerId = null;
  gesture = "pending";
  dragging.value = false;
}

function widthOf() {
  return root.value?.offsetWidth ?? 0;
}

function onPointerDown(e: PointerEvent) {
  // a swipe does not always end in a click, so a stale guard must not swallow this new tap
  suppressClick = false;
  // mouse users keep the existing buttons; swiping is a touch gesture only
  if (!active.value || e.pointerType === "mouse" || pointerId !== null) return;
  const target = e.target as Element | null;
  if (props.ignoreSelector && target?.closest?.(props.ignoreSelector)) return;
  if (target?.closest?.(".base-swipe-action__button")) return;

  pointerId = e.pointerId;
  startX = e.clientX;
  startY = e.clientY;
  startOffset = offset.value;
  gesture = "pending";
}

function onPointerMove(e: PointerEvent) {
  if (pointerId === null || e.pointerId !== pointerId) return;
  const dx = e.clientX - startX;
  const dy = e.clientY - startY;

  if (gesture === "pending") {
    gesture = classifySwipeGesture(dx, dy);
    if (gesture === "scroll") {
      resetTracking();
      return;
    }
    if (gesture === "swipe") {
      dragging.value = true;
      try {
        root.value?.setPointerCapture?.(e.pointerId);
      }
      catch {
        // the pointer may already be gone
      }
    }
  }

  if (gesture === "swipe") {
    offset.value = clampSwipeOffset(startOffset + dx, widthOf(), !!props.leftAction, !!props.rightAction);
  }
}

function onPointerUp(e: PointerEvent) {
  if (pointerId === null || e.pointerId !== pointerId) return;
  const wasSwipe = gesture === "swipe";
  resetTracking();

  if (!wasSwipe) {
    // a tap on an open row closes it rather than reaching the content beneath
    if (revealed.value) {
      suppressClick = true;
      close();
    }
    return;
  }

  suppressClick = true;
  const release = resolveSwipeRelease(offset.value, { actionWidth: props.actionWidth, width: widthOf() });
  if (release.kind === "trigger") {
    runAction(release.side);
  }
  else if (release.kind === "reveal") {
    revealed.value = release.side;
    offset.value = release.side === "left" ? -props.actionWidth : props.actionWidth;
  }
  else {
    close();
  }
}

function onPointerCancel(e: PointerEvent) {
  if (pointerId === null || e.pointerId !== pointerId) return;
  const wasSwipe = gesture === "swipe";
  resetTracking();
  if (wasSwipe) {
    close();
  }
}

function onClickCapture(e: MouseEvent) {
  if (!suppressClick) return;
  suppressClick = false;
  if ((e.target as Element | null)?.closest?.(".base-swipe-action__button")) return;
  e.stopPropagation();
  e.preventDefault();
}

function runAction(side: SwipeSide) {
  close();
  suppressClick = false;
  emit(side === "left" ? "swipe-left" : "swipe-right");
}

onClickOutside(root, () => {
  if (revealed.value) close();
});

watch(active, (value) => {
  if (!value) {
    resetTracking();
    close();
  }
});

defineExpose({ close });
</script>

<style scoped>
.base-swipe-action {
  position: relative;
}

.base-swipe-action--active {
  /* clip rather than hidden: no new block formatting context, so child margins still collapse and nothing jumps */
  overflow: clip;
}

.base-swipe-action__background {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: stretch;
  border-radius: 6px;
}

.base-swipe-action__button {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  color: inherit;
}

.base-swipe-action__label {
  font-size: 0.75rem;
  line-height: 1.1;
  text-align: center;
  padding: 0 4px;
}

.base-swipe-action__content {
  position: relative;
}

/* the row may be transparent; while it slides it must hide the action it is uncovering */
.base-swipe-action--active > .base-swipe-action__content {
  background: rgb(var(--v-theme-surface));
  will-change: transform;
}
</style>
