<template>
  <BaseDialog
    v-model="dialog"
    :title="$t('data-pages.foods.nutrition-history')"
    :icon="$globals.icons.history"
    :cancel-text="$t('general.close')"
    width="800"
  >
    <v-card-text>
      <div class="pb-2 text-body-large font-weight-bold">
        {{ food?.name }}
      </div>
      <div v-if="loading" class="d-flex justify-center py-4">
        <v-progress-circular indeterminate color="primary" />
      </div>
      <v-alert v-else-if="!logs.length" type="info" variant="tonal" density="compact" data-testid="nutrition-history-empty">
        {{ $t("data-pages.foods.nutrition-history-empty", { food: food?.name }) }}
      </v-alert>
      <v-expansion-panels v-else v-model="openLogs" multiple>
        <v-expansion-panel v-for="log in logs" :key="log.id" :value="log.id" data-testid="nutrition-history-log">
          <v-expansion-panel-title>
            <div class="d-flex align-center flex-wrap ga-2 flex-grow-1">
              <v-icon :color="log.error ? 'error' : log.result ? 'success' : 'warning'" size="small">
                {{ log.error ? $globals.icons.alertCircle : log.result ? $globals.icons.check : $globals.icons.close }}
              </v-icon>
              <span class="font-weight-bold">{{ formatDate(log.createdAt) }}</span>
              <v-chip size="x-small" variant="tonal">
                {{ $t(`data-pages.foods.nutrition-history-origin-${log.origin}`) }}
              </v-chip>
              <span v-if="log.aiModel" class="text-body-small text-medium-emphasis">
                {{ $t("data-pages.foods.nutrition-history-model", { model: log.aiModel }) }}
              </span>
            </div>
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-alert v-if="log.error" type="error" variant="tonal" density="compact" class="mb-3">
              {{ $t("data-pages.foods.nutrition-history-error", { error: log.error }) }}
            </v-alert>

            <div
              v-for="(step, index) in log.steps"
              :key="index"
              class="mb-3 pa-2 border-thin rounded"
              data-testid="nutrition-history-step"
            >
              <div class="d-flex align-center flex-wrap ga-2">
                <span class="font-weight-bold">{{ stepTitle(step) }}</span>
                <v-chip v-if="!step.error" size="x-small" :color="step.kept ? 'success' : undefined" variant="tonal">
                  {{ $t(step.kept ? "data-pages.foods.nutrition-history-kept" : "data-pages.foods.nutrition-history-discarded") }}
                </v-chip>
              </div>
              <div v-if="step.error" class="text-error text-body-medium">
                {{ $t("data-pages.foods.nutrition-history-error", { error: step.error }) }}
              </div>
              <template v-else>
                <ul v-if="step.issues?.length" class="ml-4 text-body-medium text-warning">
                  <li v-for="issue in step.issues" :key="issue.code">
                    {{ issueText(issue) }}
                  </li>
                </ul>
                <div v-else class="text-body-medium text-medium-emphasis">
                  {{ $t("data-pages.foods.nutrition-history-no-issues") }}
                </div>
                <details v-if="step.response" class="mt-1">
                  <summary class="text-body-small cursor-pointer">
                    {{ $t("data-pages.foods.nutrition-history-raw-response") }}
                  </summary>
                  <pre class="text-body-small raw-response">{{ JSON.stringify(step.response, null, 2) }}</pre>
                </details>
              </template>
            </div>

            <template v-if="log.corrections.length">
              <div class="font-weight-bold mb-1">
                {{ $t("data-pages.foods.nutrition-history-corrections") }}
              </div>
              <ul class="ml-4 mb-3 text-body-medium" data-testid="nutrition-history-corrections">
                <li v-for="correction in log.corrections" :key="correction.field">
                  {{ fieldLabel(correction.field) }} : {{ formatValue(correction.before) }} → {{ formatValue(correction.after) }}
                </li>
              </ul>
            </template>

            <div class="font-weight-bold mb-1">
              {{ $t("data-pages.foods.nutrition-history-result") }}
            </div>
            <div v-if="resultFields(log).length" class="text-body-medium" data-testid="nutrition-history-result">
              <span v-for="field in resultFields(log)" :key="field.key" class="mr-4 d-inline-block">
                {{ field.label }} : <strong>{{ field.value }}</strong> {{ field.suffix }}
              </span>
            </div>
            <div v-else class="text-body-medium text-medium-emphasis">
              {{ $t("data-pages.foods.nutrition-history-no-result") }}
            </div>
            <RecipeDataNutritionSource
              v-if="log.result?.source"
              class="pt-2"
              :source="log.result.source"
              :reference-code="log.result.referenceCode"
              :reference-name="log.result.referenceName"
            />
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>
  </BaseDialog>
</template>

<script setup lang="ts">
import RecipeDataNutritionSource from "./RecipeDataNutritionSource.vue";
import { useUserApi } from "~/composables/api";
import { filledNutritionFields, useNutritionLabels } from "~/composables/recipes/use-recipe-nutrition";
import type { NutritionField } from "~/composables/recipes/use-recipe-nutrition";
import type {
  IngredientFoodNutritionIssue,
  IngredientFoodNutritionLogOut,
  IngredientFoodNutritionLogStep,
} from "~/lib/api/types/recipe";

interface FoodReference {
  id: string;
  name: string;
}

const props = defineProps<{
  food: FoodReference | null;
}>();

const dialog = defineModel<boolean>({ default: false });

const i18n = useI18n();
const api = useUserApi();
const { labels } = useNutritionLabels();

const loading = ref(false);
const logs = ref<IngredientFoodNutritionLogOut[]>([]);
const openLogs = ref<string[]>([]);

async function load() {
  logs.value = [];
  if (!props.food) {
    return;
  }
  loading.value = true;
  const { data } = await api.foods.getNutritionLogs(props.food.id);
  loading.value = false;
  logs.value = data || [];
  // the latest estimate is the one users usually look for
  openLogs.value = logs.value.slice(0, 1).map(log => log.id);
}

watch([dialog, () => props.food?.id], ([open]) => {
  if (open) {
    load();
  }
}, { immediate: true });

function formatDate(date: string) {
  return new Date(date).toLocaleString(i18n.locale.value);
}

function formatValue(value: number | null | undefined) {
  return value === null || value === undefined ? "—" : String(value);
}

/** The AI fields are in snake case, while the nutrition labels use the camel case of the API */
function fieldLabel(field: string) {
  if (field === "average_weight") {
    return i18n.t("data-pages.foods.average-weight");
  }
  const key = field.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase());
  return labels[key]?.label || field;
}

function stepTitle(step: IngredientFoodNutritionLogStep) {
  return i18n.t(`data-pages.foods.nutrition-history-step-${step.kind}`, { count: step.foodsCount ?? 1 });
}

function issueText(issue: IngredientFoodNutritionIssue) {
  const params = { ...(issue.params || {}) };
  if (typeof params.fields === "string") {
    params.fields = params.fields.split(",").map(fieldLabel).join(", ");
  }
  const key = `data-pages.foods.nutrition-issue-${issue.code}`;
  return i18n.te(key) ? i18n.t(key, params) : issue.code;
}

function resultFields(log: IngredientFoodNutritionLogOut): NutritionField[] {
  const fields = filledNutritionFields(log.result?.nutrition, labels);
  if (log.result?.averageWeight) {
    fields.push({ key: "averageWeight", label: i18n.t("data-pages.foods.average-weight"), value: String(log.result.averageWeight), suffix: "" });
  }
  return fields;
}
</script>

<style scoped>
.raw-response {
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 240px;
  overflow: auto;
}
</style>
