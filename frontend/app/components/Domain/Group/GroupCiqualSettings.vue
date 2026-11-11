<template>
  <div>
    <BaseCardSectionTitle :title="$t('group.food-composition.title')" />
    <v-card-text class="pt-0 pb-4 px-0">
      {{ $t("group.food-composition.description") }}
    </v-card-text>

    <BaseCardSectionTitle :title="$t('group.food-composition.ciqual')" size="medium" />
    <v-card-subtitle class="px-0 mb-2" style="white-space: normal;">
      {{ $t("group.food-composition.ciqual-description") }}
      <a :href="ciqualUrl || status?.ciqualDefaultUrl" target="_blank" rel="noopener noreferrer">data.gouv.fr</a>
      ({{ $t("group.food-composition.ciqual-license") }})
    </v-card-subtitle>

    <v-form ref="refUrlForm" @submit.prevent="saveUrl">
      <v-text-field
        v-model="ciqualUrl"
        :label="$t('group.food-composition.ciqual-url')"
        :hint="$t('group.food-composition.ciqual-url-hint')"
        :placeholder="status?.ciqualDefaultUrl"
        :rules="[validUrl]"
        persistent-hint
        variant="outlined"
        density="comfortable"
      />
      <div class="d-flex flex-wrap ga-2 pt-2">
        <BaseButton
          type="button"
          color="info"
          :icon="$globals.icons.refresh"
          :loading="running"
          :disabled="!status || running"
          @click="refresh"
        >
          {{ $t("group.food-composition.ciqual-refresh") }}
        </BaseButton>
        <BaseButton
          type="submit"
          save
          class="ml-auto"
          :loading="saving"
          :disabled="!status || ciqualUrl === (status.ciqualUrl ?? '')"
        />
      </div>
    </v-form>

    <AppLoader v-if="!status" />
    <template v-else>
      <v-alert
        v-if="status.ciqualStatus === 'error' && status.ciqualError"
        type="error"
        variant="tonal"
        density="compact"
        class="mt-4"
      >
        {{ $t("group.food-composition.ciqual-error", { error: status.ciqualError }) }}
      </v-alert>
      <v-alert
        v-else-if="running"
        type="info"
        variant="tonal"
        density="compact"
        class="mt-4"
      >
        {{ $t("group.food-composition.ciqual-running") }}
      </v-alert>

      <v-table density="compact" class="mt-4">
        <tbody>
          <tr>
            <td>{{ $t("group.food-composition.ciqual-version") }}</td>
            <td>{{ status.ciqualVersion || $t("group.food-composition.bundled-version") }}</td>
          </tr>
          <tr v-if="status.ciqualReleaseTime">
            <td>{{ $t("group.food-composition.ciqual-release-date") }}</td>
            <td>{{ formatDate(status.ciqualReleaseTime) }}</td>
          </tr>
          <tr v-if="status.ciqualImportedAt">
            <td>{{ $t("group.food-composition.ciqual-imported-at") }}</td>
            <td>{{ formatDate(status.ciqualImportedAt) }}</td>
          </tr>
        </tbody>
      </v-table>

      <BaseCardSectionTitle :title="$t('group.food-composition.referential')" size="medium" class="pt-6" />
      <v-card-subtitle class="px-0 mb-2" style="white-space: normal;">
        {{ $t("group.food-composition.referential-description") }}
      </v-card-subtitle>
      <v-table density="compact">
        <thead>
          <tr>
            <th>{{ $t("group.food-composition.source") }}</th>
            <th class="text-right">
              {{ $t("group.food-composition.imported-count") }}
            </th>
            <th class="text-right">
              {{ $t("group.food-composition.api-count") }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="source in status.sources" :key="source.source">
            <td>{{ sourceName(source.source) }}</td>
            <td class="text-right">
              {{ source.importedCount }}
              <v-chip v-if="source.bundled" size="x-small" label class="ml-1">
                {{ $t("group.food-composition.bundled") }}
              </v-chip>
            </td>
            <td class="text-right">
              {{ source.apiCount }}
            </td>
          </tr>
        </tbody>
      </v-table>
    </template>
  </div>
</template>

<script setup lang="ts">
import { useUserApi } from "~/composables/api";
import { alert } from "~/composables/use-toast";
import type { FoodCompositionStatus } from "~/lib/api/types/group";
import type { VForm } from "~/types/auto-forms";

const POLL_INTERVAL = 3000;

const i18n = useI18n();
const api = useUserApi();

const status = ref<FoodCompositionStatus | null>(null);
const ciqualUrl = ref("");
const saving = ref(false);
const refUrlForm = ref<VForm | null>(null);
let poll: ReturnType<typeof setTimeout> | null = null;

const running = computed(() => status.value?.ciqualStatus === "running");

const SOURCE_NAMES: Record<string, string> = {
  ciqual: "Ciqual (ANSES)",
  usda: "USDA FoodData Central",
  off: "Open Food Facts",
};

function sourceName(source: string) {
  return SOURCE_NAMES[source] ?? source;
}

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString(i18n.locale.value);
}

function validUrl(value: string) {
  return !value || /^https:\/\/\S+$/i.test(value.trim()) || i18n.t("group.food-composition.ciqual-url-invalid");
}

function setStatus(data: FoodCompositionStatus, syncUrl = false) {
  const finished = status.value?.ciqualStatus === "running" && data.ciqualStatus !== "running";
  status.value = data;
  if (syncUrl) {
    ciqualUrl.value = data.ciqualUrl ?? "";
  }
  if (finished) {
    if (data.ciqualStatus === "success") {
      alert.success(i18n.t("group.food-composition.ciqual-refresh-success", { count: data.sources.find(s => s.source === "ciqual")?.importedCount ?? 0 }));
    }
    else {
      alert.error(i18n.t("group.food-composition.ciqual-refresh-failed"));
    }
  }
  schedulePoll();
}

function schedulePoll() {
  if (poll) {
    clearTimeout(poll);
    poll = null;
  }
  if (running.value) {
    poll = setTimeout(load, POLL_INTERVAL);
  }
}

async function load(syncUrl = false) {
  const { data } = await api.foodComposition.getStatus();
  if (data) {
    setStatus(data, syncUrl);
  }
}

async function saveUrl() {
  if (!refUrlForm.value?.validate() || !status.value) {
    return;
  }
  saving.value = true;
  // An empty field restores the default dataset URL
  const url = ciqualUrl.value.trim() || status.value.ciqualDefaultUrl;
  const { data } = await api.foodComposition.updateCiqual({ url });
  saving.value = false;
  if (data) {
    setStatus(data, true);
    alert.success(i18n.t("settings.settings-updated"));
  }
  else {
    alert.error(i18n.t("settings.settings-update-failed"));
  }
}

async function refresh() {
  const { data, response } = await api.foodComposition.refreshCiqual();
  if (data) {
    // The import may already be over (or have failed) when the request returns
    status.value = { ...data, ciqualStatus: "running" };
    alert.info(i18n.t("group.food-composition.ciqual-refresh-started"));
    await load();
  }
  else if (response?.status === 409) {
    alert.warning(i18n.t("group.food-composition.ciqual-running"));
    await load();
  }
  else {
    alert.error(i18n.t("group.food-composition.ciqual-refresh-failed"));
  }
}

onMounted(() => load(true));
onBeforeUnmount(() => {
  if (poll) {
    clearTimeout(poll);
  }
});
</script>
