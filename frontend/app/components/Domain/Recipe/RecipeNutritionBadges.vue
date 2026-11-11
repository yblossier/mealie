<template>
  <div v-if="badges.length" class="nutrition-badges" :aria-label="$t('recipe.nutrition')">
    <div class="nutrition-badges__row d-flex flex-wrap justify-center ga-2">
      <div
        v-for="badge in badges"
        :key="badge.key"
        class="nutrition-badge"
        :data-grade="badge.grade"
      >
        <div class="nutrition-badge__label">
          {{ badge.label }}
        </div>
        <div class="nutrition-badge__value" :class="{ 'nutrition-badge__value--stacked': badge.stacked }">
          <span class="nutrition-badge__number">{{ badge.value }}</span>
          <span class="nutrition-badge__unit">{{ badge.unit }}</span>
        </div>
        <div class="nutrition-badge__percent" :style="{ backgroundColor: badge.color }">
          {{ badge.percent }}
        </div>
      </div>
    </div>
    <div class="text-caption text-center text-medium-emphasis mt-1">
      {{ $t("recipe.nutrition-badges-caption") }}
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Nutrition } from "~/lib/api/types/recipe";
import {
  formatNumber,
  formatPercent,
  NUTRI_SCORE_COLORS,
  nutritionFactValue,
  referenceIntakeGrade,
  referenceIntakePercent,
  type NutritionFactKey,
} from "~/lib/recipe/nutrition-facts";

const props = defineProps<{
  nutrition?: Nutrition | null;
}>();

const i18n = useI18n();

const BADGES: { key: NutritionFactKey; label: string; unit: string; stacked?: boolean }[] = [
  { key: "calories", label: "recipe.calories", unit: "kcal", stacked: true },
  { key: "sodiumContent", label: "recipe.sodium-content", unit: "mg" },
  { key: "sugarContent", label: "recipe.sugar-content", unit: "g" },
  { key: "fatContent", label: "recipe.fat-content", unit: "g" },
  { key: "saltContent", label: "recipe.nutrition-facts-salt", unit: "g" },
];

const badges = computed(() => {
  const locale = i18n.locale.value;
  return BADGES.flatMap((badge) => {
    const value = nutritionFactValue(props.nutrition, badge.key);
    const percent = referenceIntakePercent(badge.key, value);
    if (value === null || percent === null) {
      return [];
    }

    const grade = referenceIntakeGrade(percent);
    return [{
      key: badge.key,
      label: i18n.t(badge.label),
      unit: badge.unit,
      stacked: badge.stacked,
      value: formatNumber(value, locale, value < 10 ? 1 : 0),
      percent: formatPercent(percent, locale),
      grade,
      color: NUTRI_SCORE_COLORS[grade],
    }];
  });
});
</script>

<style scoped>
.nutrition-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 84px;
  max-width: 120px;
  flex: 1 1 0;
  padding: 10px 6px 6px;
  border: 2px solid #e2e2e2;
  border-radius: 22px 22px 18px 18px;
  background: #fff;
  color: #2b2b2b;
  text-align: center;
}

.nutrition-badge__label {
  font-size: 0.7rem;
  font-weight: 800;
  line-height: 1.1;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  min-height: 1.6em;
  display: flex;
  align-items: center;
}

.nutrition-badge__value {
  display: flex;
  align-items: baseline;
  justify-content: center;
  flex-grow: 1;
  margin: 2px 0 6px;
  line-height: 1;
}

.nutrition-badge__value--stacked {
  flex-direction: column;
  align-items: center;
}

.nutrition-badge__number {
  font-size: 1.6rem;
  font-weight: 500;
}

.nutrition-badge__unit {
  font-size: 0.85rem;
  font-weight: 500;
  text-transform: uppercase;
}

.nutrition-badge__percent {
  width: 100%;
  padding: 4px 0;
  border-radius: 14px;
  color: #fff;
  font-size: 1.15rem;
  font-weight: 500;
  line-height: 1.2;
}

/* On a phone the five badges share one line: they shrink and their text scales with the screen width */
@media (max-width: 600px) {
  .nutrition-badges__row {
    flex-wrap: nowrap !important;
    gap: 4px !important;
  }

  .nutrition-badge {
    min-width: 0;
    padding: 6px 2px 4px;
    border-width: 1.5px;
    border-radius: 14px 14px 12px 12px;
  }

  .nutrition-badge__label {
    font-size: clamp(0.5rem, 2.1vw, 0.7rem);
    letter-spacing: 0;
    min-height: 2.2em;
    justify-content: center;
    overflow-wrap: anywhere;
  }

  .nutrition-badge__value {
    margin: 2px 0 4px;
  }

  .nutrition-badge__number {
    font-size: clamp(0.95rem, 4.6vw, 1.6rem);
  }

  .nutrition-badge__unit {
    font-size: clamp(0.55rem, 2.4vw, 0.85rem);
  }

  .nutrition-badge__percent {
    padding: 2px 0;
    border-radius: 10px;
    font-size: clamp(0.7rem, 3.2vw, 1.15rem);
  }
}
</style>
