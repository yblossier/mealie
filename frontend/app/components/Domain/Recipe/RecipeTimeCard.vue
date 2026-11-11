<template v-if="_showCards">
  <div class="time-card-container text-center mx-auto">
    <!-- Total Time -->
    <div
      v-if="validateTotalTime"
      class="time-card-flex"
    >
      <v-row
        no-gutters
        class="d-flex flex-no-wrap align-center"
        :class="{
          'justify-center': !$vuetify.display.smAndDown,
          'time-card-item-stacked': $vuetify.display.smAndDown,
        }"
        :style="fontSize"
      >
        <v-icon
          :x-large="!small"
          start
          color="primary"
        >
          {{ $globals.icons.clockOutline }}
        </v-icon>
        <p class="my-0 text-no-wrap">
          <span class="font-weight-bold opacity-80">{{ validateTotalTime.name }}</span><br>{{ validateTotalTime.value }}
        </p>
      </v-row>
    </div>
    <v-divider
      v-if="validateTotalTime && (validatePrepTime || validatePerformTime)"
      class="my-2"
    />
    <!-- Prep Time & Perform Time -->
    <div
      v-if="validatePrepTime || validatePerformTime"
      class="time-card-flex"
    >
      <v-row
        no-gutters
        class="d-flex flex-nowrap justify-center align-center"
        :class="{ 'flex-column': $vuetify.display.smAndDown }"
        style="width: 100%;"
        :style="fontSize"
      >
        <div
          v-if="validatePrepTime"
          class="d-flex flex-no-wrap my-1 align-center"
          :class="{ 'time-card-item-stacked': $vuetify.display.smAndDown }"
        >
          <v-icon
            :size="small ? 'small' : 'large'"
            start
            color="primary"
          >
            {{ $globals.icons.knife }}
          </v-icon>
          <p class="my-0 text-no-wrap">
            <span class="font-weight-bold opacity-80">{{ validatePrepTime.name }}</span><br>{{ validatePrepTime.value }}
          </p>
        </div>
        <v-divider
          v-if="validatePrepTime && validatePerformTime && !$vuetify.display.smAndDown"
          vertical
          class="mx-4"
        />
        <div
          v-if="validatePerformTime"
          class="d-flex flex-no-wrap my-1 align-center"
          :class="{ 'time-card-item-stacked': $vuetify.display.smAndDown }"
        >
          <v-icon
            :size="small ? 'small' : 'large'"
            start
            color="primary"
          >
            {{ $globals.icons.stove }}
          </v-icon>
          <p class="my-0 text-no-wrap">
            <span class="font-weight-bold opacity-80">{{ validatePerformTime.name }}</span><br>{{ validatePerformTime.value }}
          </p>
        </div>
      </v-row>
    </div>
    <v-divider
      v-if="extraTimes.length > 0 && (validateTotalTime || validatePrepTime || validatePerformTime)"
      class="my-2"
    />
    <!-- Cooling Time & Rest Time -->
    <div
      v-if="extraTimes.length > 0"
      class="time-card-flex"
    >
      <v-row
        no-gutters
        class="d-flex flex-nowrap justify-center align-center"
        :class="{ 'flex-column': $vuetify.display.smAndDown }"
        style="width: 100%;"
        :style="fontSize"
      >
        <template
          v-for="(time, index) in extraTimes"
          :key="time.key"
        >
          <v-divider
            v-if="index > 0 && !$vuetify.display.smAndDown"
            vertical
            class="mx-4"
          />
          <div
            class="d-flex flex-no-wrap my-1 align-center"
            :class="{ 'time-card-item-stacked': $vuetify.display.smAndDown }"
            :data-testid="`recipe-${time.key}-time`"
          >
            <v-icon
              :size="small ? 'small' : 'large'"
              start
              color="primary"
            >
              {{ time.icon }}
            </v-icon>
            <p class="my-0 text-no-wrap">
              <span class="font-weight-bold opacity-80">{{ time.name }}</span><br>{{ time.value }}
            </p>
          </div>
        </template>
      </v-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRecipeTime } from "~/composables/recipes";

interface Props {
  prepTime?: string | null;
  totalTime?: string | null;
  performTime?: string | null;
  coolingTime?: string | null;
  restTime?: string | null;
  prepTimeSeconds?: number | null;
  totalTimeSeconds?: number | null;
  performTimeSeconds?: number | null;
  coolingTimeSeconds?: number | null;
  restTimeSeconds?: number | null;
  color?: string;
  small?: boolean;
}
const props = withDefaults(defineProps<Props>(), {
  prepTime: null,
  totalTime: null,
  performTime: null,
  coolingTime: null,
  restTime: null,
  prepTimeSeconds: null,
  totalTimeSeconds: null,
  performTimeSeconds: null,
  coolingTimeSeconds: null,
  restTimeSeconds: null,
  color: "accent custom-transparent",
  small: false,
});

const i18n = useI18n();
const { recipeTimeDisplay } = useRecipeTime();
const { $globals } = useNuxtApp();

const totalTime = computed(() => recipeTimeDisplay(props.totalTimeSeconds, props.totalTime));
const prepTime = computed(() => recipeTimeDisplay(props.prepTimeSeconds, props.prepTime));
const performTime = computed(() => recipeTimeDisplay(props.performTimeSeconds, props.performTime));

const _showCards = computed(() => {
  return [prepTime.value, totalTime.value, performTime.value].some(x => !!x) || extraTimes.value.length > 0;
});

const extraTimes = computed(() => [
  { key: "cooling", icon: $globals.icons.snowflake, name: i18n.t("recipe.step-cooling-label"), value: recipeTimeDisplay(props.coolingTimeSeconds, props.coolingTime) },
  { key: "rest", icon: $globals.icons.timerSand, name: i18n.t("recipe.step-rest-label"), value: recipeTimeDisplay(props.restTimeSeconds, props.restTime) },
].filter(time => !!time.value));

const validateTotalTime = computed(() => {
  return totalTime.value ? { name: i18n.t("recipe.total-time"), value: totalTime.value } : null;
});

const validatePrepTime = computed(() => {
  return prepTime.value ? { name: i18n.t("recipe.prep-time"), value: prepTime.value } : null;
});

const validatePerformTime = computed(() => {
  return performTime.value ? { name: i18n.t("recipe.perform-time"), value: performTime.value } : null;
});

const fontSize = computed(() => {
  return props.small ? { fontSize: "smaller" } : { fontSize: "larger" };
});
</script>

<style scoped>
.text-center {
  font-size: smaller;
}
.time-card-container {
  width: fit-content;
}
.time-card-flex {
  width: 100%;
}
.time-card-item-stacked {
  width: 100%;
  text-align: start;
}
.custom-transparent {
  opacity: 0.7;
}
</style>
