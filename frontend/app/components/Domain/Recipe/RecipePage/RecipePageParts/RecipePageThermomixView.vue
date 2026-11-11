<template>
  <div class="thermomix-view">
    <div v-if="loading" class="d-flex justify-center py-8">
      <v-progress-circular indeterminate color="primary" />
    </div>

    <v-card
      v-else-if="!view"
      variant="tonal"
      class="pa-4 text-center"
    >
      <p class="text-body-1 mb-4">
        {{ $t("recipe.thermomix.not-generated") }}
      </p>
      <BaseButton
        v-if="canEdit"
        :loading="generating"
        :disabled="generating"
        @click="generate"
      >
        <template #icon>
          {{ $globals.icons.robot }}
        </template>
        {{ $t("recipe.thermomix.generate") }}
      </BaseButton>
      <p v-if="generating" class="text-body-2 text-medium-emphasis mt-3">
        {{ $t("recipe.thermomix.generating") }}
      </p>
    </v-card>

    <template v-else>
      <v-alert
        type="info"
        variant="tonal"
        density="compact"
        class="mb-4"
        :icon="$globals.icons.robot"
        data-testid="thermomix-ai-notice"
      >
        {{ $t("recipe.thermomix.ai-notice") }}
      </v-alert>
      <template
        v-for="(step, index) in view.steps"
        :key="step.id || index"
      >
        <v-sheet
          v-if="step.title"
          color="primary"
          class="mt-6 mb-2 pa-3 d-flex align-center thermomix-section"
          style="border-radius: 6px; width: 100%;"
        >
          <v-toolbar-title class="section-title-text">
            {{ step.title }}
          </v-toolbar-title>
          <CookTime
            v-if="sectionTotalSeconds(index)"
            class="section-total-time ml-2 mr-1"
            :model-value="sectionTotalSeconds(index)"
            :is-edit-mode="false"
            :icon="$globals.icons.timerOutline"
            :label="$t('recipe.section-total-time')"
            data-testid="thermomix-section-total"
          />
        </v-sheet>
        <v-card
          variant="outlined"
          class="mb-4 thermomix-step"
        >
          <v-card-title class="d-flex align-center flex-wrap ga-2">
            <SafeMarkdown
              v-if="step.summary"
              class="markdown thermomix-step-summary"
              :source="step.summary"
            />
            <span v-else>{{ $t("recipe.step-index", { step: index + 1 }) }}</span>
            <v-spacer />
            <div class="step-times">
              <CookTime
                v-for="field in stepTimeFields"
                :key="field.key"
                :model-value="step[field.key] ?? null"
                :is-edit-mode="false"
                :icon="$globals.icons[field.icon]"
                :label="field.label"
              />
            </div>
          </v-card-title>
          <v-card-text class="markdown">
            <v-row>
              <v-col
                v-if="isCookMode && linkedIngredients(step).length"
                cols="12"
                sm="5"
                data-testid="thermomix-step-ingredients"
              >
                <div class="ml-n4">
                  <RecipeIngredients
                    :value="linkedIngredients(step)"
                    :scale="scale"
                    :is-cook-mode="isCookMode"
                    :storage-key="ingredientStorageKey"
                    :recipe-id="recipe.id"
                  />
                </div>
              </v-col>
              <v-divider
                v-if="isCookMode && linkedIngredients(step).length && $vuetify.display.smAndUp"
                vertical
              />
              <v-col>
                <SafeMarkdown class="markdown thermomix-step-text" :source="tagThermomixSettings(step.text)" />
                <div
                  v-if="step.cautions?.length"
                  class="thermomix-caution d-flex align-start ga-2 mt-3 pa-3"
                  role="note"
                  :aria-label="$t('recipe.thermomix.caution')"
                  data-testid="thermomix-step-caution"
                >
                  <v-icon class="thermomix-caution__icon" size="22">
                    {{ $globals.icons.thermometer }}
                  </v-icon>
                  <div class="thermomix-caution__text">
                    <p v-for="(caution, cautionIndex) in step.cautions" :key="cautionIndex">
                      {{ caution }}
                    </p>
                  </div>
                </div>
                <div
                  v-if="(step.accessory && !isLinkedTool(step, step.accessory)) || linkedTools(step).length"
                  class="d-flex flex-wrap ga-2 mt-3"
                >
                  <v-chip
                    v-if="step.accessory && !isLinkedTool(step, step.accessory)"
                    size="small"
                    variant="tonal"
                    :prepend-icon="$globals.icons.tools"
                  >
                    {{ step.accessory }}
                  </v-chip>
                  <v-chip
                    v-for="tool in linkedTools(step)"
                    :key="tool.id"
                    size="small"
                    variant="tonal"
                    :prepend-icon="toolCategoryIcon(tool.category)"
                    data-testid="thermomix-step-tool"
                  >
                    {{ tool.name }}
                  </v-chip>
                </div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </template>

      <v-card
        v-if="view.notes.length"
        variant="tonal"
        class="mb-4"
      >
        <v-card-title>{{ $t("recipe.thermomix.notes") }}</v-card-title>
        <v-card-text>
          <ul class="ml-4">
            <li v-for="(note, index) in view.notes" :key="index">
              {{ note }}
            </li>
          </ul>
        </v-card-text>
      </v-card>

      <div class="d-flex align-center flex-wrap ga-2">
        <span class="text-caption text-medium-emphasis">
          <v-icon size="14" class="mr-1">{{ $globals.icons.robot }}</v-icon>
          {{ generatedLabel }}
        </span>
        <v-spacer />
        <template v-if="canEdit">
          <BaseButton
            minor
            :loading="generating"
            :disabled="generating"
            @click="generate"
          >
            <template #icon>
              {{ $globals.icons.refresh }}
            </template>
            {{ $t("recipe.thermomix.regenerate") }}
          </BaseButton>
          <BaseButton
            minor
            delete
            :disabled="generating"
            @click="remove"
          />
        </template>
      </div>
    </template>

    <div v-if="!loading" class="mt-4">
      <v-btn
        size="small"
        variant="text"
        :prepend-icon="$globals.icons.history"
        :aria-pressed="showLogs"
        data-testid="toggle-thermomix-logs"
        @click="showLogs = !showLogs"
      >
        {{ showLogs ? $t("recipe.thermomix.hide-logs") : $t("recipe.thermomix.show-logs") }}
      </v-btn>

      <div v-if="showLogs" class="mt-2" data-testid="thermomix-logs">
        <div v-if="logsLoading" class="d-flex justify-center py-4">
          <v-progress-circular indeterminate size="24" />
        </div>
        <p v-else-if="!logs.length" class="text-body-2 text-medium-emphasis ml-2">
          {{ $t("recipe.thermomix.no-logs") }}
        </p>
        <v-expansion-panels v-else variant="accordion">
          <v-expansion-panel v-for="log in logs" :key="log.id">
            <v-expansion-panel-title>
              <div class="d-flex align-center flex-wrap ga-2 flex-grow-1">
                <v-icon :color="log.status === 'success' ? 'success' : 'error'" size="18">
                  {{ log.status === 'success' ? $globals.icons.checkboxMarkedCircle : $globals.icons.alertCircle }}
                </v-icon>
                <span class="text-body-2">{{ formatDate(log.createdAt) }}</span>
                <v-chip size="x-small" variant="tonal">
                  {{ formatDuration(log.durationMs) }}
                </v-chip>
                <span class="text-caption text-medium-emphasis">
                  {{ [log.provider, log.model].filter(Boolean).join(" · ") }}
                </span>
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-table density="compact" class="mb-3 thermomix-log-table">
                <tbody>
                  <tr v-if="log.user">
                    <th>{{ $t("recipe.thermomix.log-user") }}</th>
                    <td>{{ log.user }}</td>
                  </tr>
                  <tr>
                    <th>{{ $t("recipe.thermomix.log-status") }}</th>
                    <td>
                      {{ log.status === 'success'
                        ? $t("recipe.thermomix.log-success", { count: log.stepsCount })
                        : $t("recipe.thermomix.log-error") }}
                    </td>
                  </tr>
                  <tr>
                    <th>{{ $t("recipe.thermomix.log-duration") }}</th>
                    <td>
                      {{ formatDuration(log.durationMs) }}
                      <span v-if="log.timeoutSeconds" class="text-medium-emphasis">
                        ({{ $t("recipe.thermomix.log-timeout", { seconds: log.timeoutSeconds }) }})
                      </span>
                    </td>
                  </tr>
                  <tr>
                    <th>{{ $t("recipe.thermomix.log-input-size") }}</th>
                    <td>{{ $t("recipe.thermomix.log-input-size-value", { chars: log.promptChars, tokens: log.estimatedTokens }) }}</td>
                  </tr>
                </tbody>
              </v-table>
              <v-alert
                v-if="log.error"
                type="error"
                variant="tonal"
                density="compact"
                class="mb-3 text-body-2"
                style="white-space: pre-wrap; word-break: break-word;"
              >
                {{ log.error }}
              </v-alert>
              <div class="text-subtitle-2 mb-1">
                {{ $t("recipe.thermomix.log-request") }}
              </div>
              <pre class="log-pre mb-3">{{ formatJson(log.request) }}</pre>
              <template v-if="log.response">
                <div class="text-subtitle-2 mb-1">
                  {{ $t("recipe.thermomix.log-response") }}
                </div>
                <pre class="log-pre">{{ JSON.stringify(log.response, null, 2) }}</pre>
              </template>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { RecipeIngredient, RecipeOut, RecipeThermomixView, ThermomixLogEntry, ThermomixStep } from "~/lib/api/types/recipe";
import { useUserApi } from "~/composables/api";
import { usePageState } from "~/composables/recipe-page/shared-state";
import { alert } from "~/composables/use-toast";
import { tagThermomixSettings } from "~/lib/recipe/thermomix-settings";
import { toolCategoryIcon } from "~/lib/recipe/tool-display";
import RecipeIngredients from "~/components/Domain/Recipe/RecipeIngredients.vue";
import CookTime from "./CookTime.vue";

const props = withDefaults(defineProps<{
  recipe: RecipeOut;
  canEdit: boolean;
  scale?: number;
  ingredientStorageKey?: string;
}>(), {
  scale: 1,
  ingredientStorageKey: undefined,
});

const { isCookMode } = usePageState(props.recipe.slug);

const i18n = useI18n();
const api = useUserApi();

const toolsById = computed(() => new Map((props.recipe.tools ?? []).filter(tool => tool.id).map(tool => [tool.id, tool])));

function linkedTools(step: ThermomixStep) {
  return (step.toolIds ?? []).map(id => toolsById.value.get(id)).filter(tool => tool !== undefined);
}

function isLinkedTool(step: ThermomixStep, name: string): boolean {
  const key = name.trim().toLowerCase();
  return linkedTools(step).some(tool => tool.name.trim().toLowerCase() === key);
}

type ThermomixTimeKey = "timeSeconds" | "coolingSeconds" | "cookingSeconds" | "restSeconds";
const stepTimeFields = computed<{ key: ThermomixTimeKey; icon: "knife" | "snowflake" | "stove" | "timerSand"; label: string }[]>(() => [
  { key: "timeSeconds", icon: "knife", label: i18n.t("recipe.step-duration-label") },
  { key: "coolingSeconds", icon: "snowflake", label: i18n.t("recipe.step-cooling-label") },
  { key: "cookingSeconds", icon: "stove", label: i18n.t("recipe.step-cooking-label") },
  { key: "restSeconds", icon: "timerSand", label: i18n.t("recipe.step-rest-label") },
]);

function stepTotalSeconds(step: ThermomixStep): number {
  return stepTimeFields.value.reduce((total, field) => total + (step[field.key] ?? 0), 0);
}

/** Sums the times of the steps from the section starting at `index` up to the next section. */
function sectionTotalSeconds(index: number): number {
  const steps = view.value?.steps ?? [];
  let total = 0;
  for (let i = index; i < steps.length; i++) {
    if (i !== index && steps[i].title) {
      break;
    }
    total += stepTotalSeconds(steps[i]);
  }
  return total;
}

const view = ref<RecipeThermomixView | null>(null);
const loading = ref(true);
const generating = ref(false);

const showLogs = ref(false);
const logs = ref<ThermomixLogEntry[]>([]);
const logsLoading = ref(false);

async function loadLogs() {
  logsLoading.value = true;
  const { data } = await api.recipes.getThermomixLogs(props.recipe.slug);
  logs.value = data ?? [];
  logsLoading.value = false;
}

watch(showLogs, (show) => {
  if (show) {
    loadLogs();
  }
});

function formatDate(value: string): string {
  return new Date(value).toLocaleString(i18n.locale.value);
}

function formatDuration(ms: number): string {
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`;
}

function formatJson(text: string): string {
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  }
  catch {
    return text;
  }
}
const stepIngredientRefs = computed(() => {
  const refs = new Map<string, string[]>();
  (props.recipe.recipeInstructions ?? []).forEach((step) => {
    if (step.id) {
      refs.set(step.id, (step.ingredientReferences ?? []).map(ref => ref.referenceId).filter((id): id is string => !!id));
    }
  });
  return refs;
});

/** Ingredients linked to the recipe steps a Thermomix step comes from, in the recipe's order. */
function linkedIngredients(step: ThermomixStep): RecipeIngredient[] {
  const ids = new Set((step.sourceStepIds ?? []).flatMap(id => stepIngredientRefs.value.get(id) ?? []));
  if (!ids.size) {
    return [];
  }
  return (props.recipe.recipeIngredient ?? []).filter(ing => !!ing.referenceId && ids.has(ing.referenceId));
}

const generatedLabel = computed(() => {
  if (!view.value) {
    return "";
  }
  const date = new Date(view.value.createdAt).toLocaleString(i18n.locale.value);
  return view.value.model
    ? i18n.t("recipe.thermomix.generated-by-with-model", { model: view.value.model, date })
    : i18n.t("recipe.thermomix.generated-by", { date });
});

async function load() {
  loading.value = true;
  const { data } = await api.recipes.getThermomixView(props.recipe.slug);
  view.value = data ?? null;
  loading.value = false;
}

async function generate() {
  generating.value = true;
  const { data, error } = await api.recipes.generateThermomixView(props.recipe.slug);
  generating.value = false;
  if (showLogs.value) {
    loadLogs();
  }
  if (error || !data) {
    alert.error(i18n.t("recipe.thermomix.generation-failed"));
    return;
  }
  view.value = data;
}

async function remove() {
  const { error } = await api.recipes.deleteThermomixView(props.recipe.slug);
  if (error) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  view.value = null;
}

onMounted(load);
</script>

<style scoped>
.log-pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.75rem;
  max-height: 320px;
  overflow: auto;
  padding: 8px;
  border-radius: 4px;
  background-color: rgba(var(--v-theme-on-surface), 0.05);
}

.thermomix-log-table th {
  width: 35%;
  font-weight: 500;
}

.thermomix-step {
  border-color: rgba(var(--v-theme-primary), 0.4);
}

.step-times {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px 10px;
}

.section-total-time {
  margin-left: auto;
  opacity: 1;
}

.thermomix-caution {
  border-radius: 6px;
  background-color: #fdecea;
  color: #3b1010;
  print-color-adjust: exact;
  -webkit-print-color-adjust: exact;
}

.thermomix-caution__icon {
  color: #c62828 !important;
  flex-shrink: 0;
}

.thermomix-caution__text p {
  margin: 0;
}

.thermomix-caution__text p + p {
  margin-top: 4px;
}

.thermomix-step-text :deep(.thermomix-setting) {
  display: inline-block;
  padding: 0 8px;
  border-radius: 12px;
  background-color: #00a64f;
  color: #fff;
  font-weight: 600;
  white-space: nowrap;
}
</style>
