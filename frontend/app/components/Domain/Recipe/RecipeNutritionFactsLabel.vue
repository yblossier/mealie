<template>
  <div class="nutrition-facts">
    <table>
      <thead>
        <tr>
          <th class="text-start">
            {{ $t("recipe.nutrition-facts-title") }}
          </th>
          <th class="text-end">
            {{ basis || $t("recipe.nutrition-facts-per-100g") }}
          </th>
          <th class="text-end">
            {{ $t("recipe.nutrition-facts-ri") }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in rows"
          :key="row.key"
          :class="{ 'nutrition-facts__section': row.section }"
        >
          <template v-if="row.section">
            <td colspan="3">
              {{ row.label }}
            </td>
          </template>
          <template v-else>
            <td :class="{ 'ps-6': row.indent }">
              {{ row.label }}
            </td>
            <td class="text-end">
              {{ row.value }}
            </td>
            <td class="text-end">
              {{ row.percent }}
            </td>
          </template>
        </tr>
      </tbody>
    </table>
    <div class="nutrition-facts__footnote">
      {{ $t("recipe.nutrition-facts-ri-footnote") }}
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Nutrition } from "~/lib/api/types/recipe";
import {
  formatNumber,
  formatPercent,
  kilojoules,
  nutritionFactValue,
  referenceIntakePercent,
  type NutritionFactKey,
} from "~/lib/recipe/nutrition-facts";

const props = defineProps<{
  nutrition?: Nutrition | null;
  /** Header of the values column; "Per 100 g" by default */
  basis?: string;
}>();

const i18n = useI18n();

interface FactDefinition {
  key: NutritionFactKey;
  label: string;
  unit: string;
  indent?: boolean;
  /** Always listed, as on every EU label, even when unknown */
  mandatory?: boolean;
}

const FACTS: FactDefinition[] = [
  { key: "calories", label: "recipe.nutrition-facts-energy", unit: "kcal", mandatory: true },
  { key: "fatContent", label: "recipe.fat-content", unit: "g", mandatory: true },
  { key: "saturatedFatContent", label: "recipe.nutrition-facts-of-which-saturates", unit: "g", indent: true, mandatory: true },
  { key: "unsaturatedFatContent", label: "recipe.nutrition-facts-of-which-unsaturates", unit: "g", indent: true },
  { key: "transFatContent", label: "recipe.nutrition-facts-of-which-trans", unit: "g", indent: true },
  { key: "cholesterolContent", label: "recipe.cholesterol-content", unit: "mg" },
  { key: "carbohydrateContent", label: "recipe.carbohydrate-content", unit: "g", mandatory: true },
  { key: "sugarContent", label: "recipe.nutrition-facts-of-which-sugars", unit: "g", indent: true, mandatory: true },
  { key: "fiberContent", label: "recipe.fiber-content", unit: "g" },
  { key: "proteinContent", label: "recipe.protein-content", unit: "g", mandatory: true },
  { key: "saltContent", label: "recipe.nutrition-facts-salt", unit: "g", mandatory: true },
];

const MICRONUTRIENTS: FactDefinition[] = [
  { key: "vitaminAContent", label: "recipe.vitamin-a-content", unit: "µg" },
  { key: "vitaminCContent", label: "recipe.vitamin-c-content", unit: "mg" },
  { key: "vitaminDContent", label: "recipe.vitamin-d-content", unit: "µg" },
  { key: "calciumContent", label: "recipe.calcium-content", unit: "mg" },
  { key: "ironContent", label: "recipe.iron-content", unit: "mg" },
  { key: "magnesiumContent", label: "recipe.magnesium-content", unit: "mg" },
  { key: "potassiumContent", label: "recipe.potassium-content", unit: "mg" },
];

interface Row {
  key: string;
  label: string;
  value?: string;
  percent?: string;
  indent?: boolean;
  section?: boolean;
}

function toRow(fact: FactDefinition, locale: string): Row | null {
  const value = nutritionFactValue(props.nutrition, fact.key);
  if (value === null && !fact.mandatory) {
    return null;
  }

  const percent = referenceIntakePercent(fact.key, value);
  let text = "—";
  if (value !== null) {
    text = fact.key === "calories"
      ? `${formatNumber(kilojoules(value), locale, 0)} kJ / ${formatNumber(value, locale, 0)} kcal`
      : `${formatNumber(value, locale, value < 10 ? 2 : 1)} ${fact.unit}`;
  }

  return {
    key: fact.key,
    label: i18n.t(fact.label),
    value: text,
    percent: percent === null ? "" : formatPercent(percent, locale),
    indent: fact.indent,
  };
}

const rows = computed<Row[]>(() => {
  const locale = i18n.locale.value;
  const macros = FACTS.map(fact => toRow(fact, locale)).filter((row): row is Row => !!row);
  const micros = MICRONUTRIENTS.map(fact => toRow(fact, locale)).filter((row): row is Row => !!row);

  if (!micros.length) {
    return macros;
  }
  return [
    ...macros,
    { key: "micronutrients", label: i18n.t("recipe.nutrition-facts-vitamins-minerals"), section: true },
    ...micros,
  ];
});
</script>

<style scoped>
.nutrition-facts {
  border: 2px solid #1a1a1a;
  padding: 6px 10px;
  background: #fff;
  color: #1a1a1a;
  font-size: 0.875rem;
}

.nutrition-facts table {
  width: 100%;
  border-collapse: collapse;
}

.nutrition-facts th {
  padding: 4px 4px 6px;
  border-bottom: 6px solid #1a1a1a;
  font-weight: 800;
  vertical-align: bottom;
}

.nutrition-facts td {
  padding: 3px 4px;
  border-bottom: 1px solid #1a1a1a;
}

.nutrition-facts td:not(:first-child),
.nutrition-facts th:not(:first-child) {
  white-space: nowrap;
}

.nutrition-facts tr:not(.nutrition-facts__section) td:first-child:not(.ps-6) {
  font-weight: 700;
}

.nutrition-facts__section td {
  padding-top: 8px;
  border-bottom-width: 3px;
  font-weight: 800;
}

.nutrition-facts__footnote {
  padding-top: 4px;
  font-size: 0.75rem;
}
</style>
