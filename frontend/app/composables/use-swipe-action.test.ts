import { describe, expect, test } from "vitest";
import {
  clampSwipeOffset,
  classifySwipeGesture,
  resolveSwipeRelease,
  swipeSideForOffset,
  swipeTriggerDistance,
} from "./use-swipe-action";

describe("classifySwipeGesture", () => {
  test("waits until the finger moved past the slop", () => {
    expect(classifySwipeGesture(4, 3)).toBe("pending");
  });

  test("a mostly horizontal move is a swipe", () => {
    expect(classifySwipeGesture(-30, 5)).toBe("swipe");
    expect(classifySwipeGesture(30, -5)).toBe("swipe");
  });

  test("vertical and diagonal moves are left to the page scroll", () => {
    expect(classifySwipeGesture(2, 40)).toBe("scroll");
    expect(classifySwipeGesture(20, 20)).toBe("scroll");
  });
});

describe("swipeSideForOffset", () => {
  test("maps the drag direction to a side", () => {
    expect(swipeSideForOffset(-10)).toBe("left");
    expect(swipeSideForOffset(10)).toBe("right");
    expect(swipeSideForOffset(0)).toBeNull();
  });
});

describe("clampSwipeOffset", () => {
  test("a side without an action does not move", () => {
    expect(clampSwipeOffset(50, 300, true, false)).toBe(0);
    expect(clampSwipeOffset(-50, 300, false, true)).toBe(0);
  });

  test("travel is capped to the element width", () => {
    expect(clampSwipeOffset(-500, 300, true, true)).toBe(-300);
    expect(clampSwipeOffset(500, 300, true, true)).toBe(300);
    expect(clampSwipeOffset(-40, 300, true, true)).toBe(-40);
  });
});

describe("resolveSwipeRelease", () => {
  const options = { actionWidth: 88, width: 360 };

  test("trigger distance is half the width but never too short", () => {
    expect(swipeTriggerDistance(options)).toBe(180);
    expect(swipeTriggerDistance({ actionWidth: 88, width: 100 })).toBe(132);
  });

  test("a long swipe runs the action", () => {
    expect(resolveSwipeRelease(-200, options)).toEqual({ kind: "trigger", side: "left" });
    expect(resolveSwipeRelease(190, options)).toEqual({ kind: "trigger", side: "right" });
  });

  test("a medium swipe keeps the action revealed", () => {
    expect(resolveSwipeRelease(-60, options)).toEqual({ kind: "reveal", side: "left" });
    expect(resolveSwipeRelease(100, options)).toEqual({ kind: "reveal", side: "right" });
  });

  test("a short swipe snaps back", () => {
    expect(resolveSwipeRelease(-20, options)).toEqual({ kind: "close" });
    expect(resolveSwipeRelease(0, options)).toEqual({ kind: "close" });
  });
});
