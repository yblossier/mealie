import { computed, ref, type Ref } from "vue";

interface MadeThisState {
  /** Number of mounted "I made this" dialogs for the recipe */
  dialogs: Ref<number>;
  /** Bumped every time something asks the dialog to open */
  requests: Ref<number>;
  /** True when the last request came from checking off every step */
  fromCompletion: Ref<boolean>;
}

const states = new Map<string, MadeThisState>();

function stateFor(slug: string): MadeThisState {
  let state = states.get(slug);
  if (!state) {
    state = { dialogs: ref(0), requests: ref(0), fromCompletion: ref(false) };
    states.set(slug, state);
  }
  return state;
}

/** True when every step of the recipe has been checked off */
export function allStepsDone(stepCount: number, doneSteps: readonly number[]): boolean {
  if (stepCount <= 0) {
    return false;
  }
  const done = new Set(doneSteps);
  for (let i = 0; i < stepCount; i++) {
    if (!done.has(i)) {
      return false;
    }
  }
  return true;
}

/**
 * Lets the steps ask the recipe's "I made this" dialog to open, without the two components
 * knowing about each other.
 */
export function useMadeThisPrompt(slug: string) {
  const state = stateFor(slug);

  /** Called by the dialog; returns the matching unregister function */
  function registerDialog() {
    state.dialogs.value++;
    return () => {
      state.dialogs.value = Math.max(0, state.dialogs.value - 1);
    };
  }

  /** `fromCompletion` lets the dialog invite the user to record the cook they just finished */
  function requestDialog(fromCompletion = false) {
    state.fromCompletion.value = fromCompletion;
    state.requests.value++;
  }

  return {
    dialogAvailable: computed(() => state.dialogs.value > 0),
    requests: computed(() => state.requests.value),
    fromCompletion: computed(() => state.fromCompletion.value),
    registerDialog,
    requestDialog,
  };
}
