export type SwipeGesture = "pending" | "swipe" | "scroll";
export type SwipeSide = "left" | "right";

export interface SwipeReleaseOptions {
  /** width of the revealed action button */
  actionWidth: number;
  /** width of the swiped element; a release past `triggerRatio` of it runs the action at once */
  width: number;
  triggerRatio?: number;
  /** a full swipe never needs less travel than this, so narrow rows stay forgiving */
  minTriggerDistance?: number;
}

export type SwipeRelease
  = | { kind: "trigger"; side: SwipeSide }
    | { kind: "reveal"; side: SwipeSide }
    | { kind: "close" };

/** Movement (px) before a touch is committed to being a scroll or a horizontal swipe */
export const SWIPE_SLOP = 10;

/**
 * Decides what a touch is doing from how far it moved. A gesture that is mostly vertical (or
 * diagonal) is left to the browser so the page keeps scrolling; only a clearly horizontal one
 * becomes a swipe.
 */
export function classifySwipeGesture(dx: number, dy: number, slop = SWIPE_SLOP): SwipeGesture {
  const absX = Math.abs(dx);
  const absY = Math.abs(dy);
  if (absX < slop && absY < slop) {
    return "pending";
  }
  return absX > absY * 1.2 ? "swipe" : "scroll";
}

/** The side whose action a given offset uncovers: dragging the row left uncovers the right edge */
export function swipeSideForOffset(offset: number): SwipeSide | null {
  if (offset < 0) return "left";
  if (offset > 0) return "right";
  return null;
}

/**
 * Clamps a drag offset: a side without an action does not move at all, and the travel is capped
 * to the element's width.
 */
export function clampSwipeOffset(offset: number, width: number, allowLeft: boolean, allowRight: boolean): number {
  const max = Math.max(width, 0);
  if (offset < 0) {
    return allowLeft ? Math.max(offset, -max) : 0;
  }
  if (offset > 0) {
    return allowRight ? Math.min(offset, max) : 0;
  }
  return 0;
}

export function swipeTriggerDistance(options: SwipeReleaseOptions): number {
  const { actionWidth, width, triggerRatio = 0.5, minTriggerDistance = 120 } = options;
  return Math.max(width * triggerRatio, minTriggerDistance, actionWidth * 1.5);
}

/**
 * What happens when the finger lifts: past the trigger distance the action runs; past half the
 * action button the row stays open so the action can be tapped; otherwise it snaps back.
 */
export function resolveSwipeRelease(offset: number, options: SwipeReleaseOptions): SwipeRelease {
  const side = swipeSideForOffset(offset);
  if (!side) {
    return { kind: "close" };
  }
  const distance = Math.abs(offset);
  if (distance >= swipeTriggerDistance(options)) {
    return { kind: "trigger", side };
  }
  if (distance >= options.actionWidth / 2) {
    return { kind: "reveal", side };
  }
  return { kind: "close" };
}
