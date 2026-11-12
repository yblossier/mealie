<template>
  <div>
    <h3 class="text-title-large mb-1">
      {{ $t("group.open-food-facts-api") }}
    </h3>
    <p class="text-title-small mb-3">
      {{ $t("group.open-food-facts-api-description") }}
    </p>
    <div class="d-flex flex-wrap ga-3 mb-2">
      <v-select
        v-model="preferences.offMode"
        :items="offModes"
        :label="$t('group.off-mode')"
        density="compact"
        variant="outlined"
        hide-details
        style="max-width: 220px;"
        data-testid="off-mode"
      />
      <v-text-field
        :model-value="offUrl"
        :label="$t('group.off-api-url')"
        density="compact"
        variant="outlined"
        hide-details
        readonly
        disabled
        class="flex-grow-1"
        style="min-width: 240px;"
        data-testid="off-url"
      />
    </div>
    <p class="text-body-small mb-2">
      {{ $t("group.off-app-hint") }}
    </p>
    <div class="d-flex flex-wrap ga-3 mb-6">
      <v-text-field
        v-model="preferences.offAppName"
        :label="$t('group.off-app-name')"
        placeholder="Mealie"
        density="compact"
        variant="outlined"
        hide-details
        clearable
        style="min-width: 180px;"
      />
      <v-text-field
        v-model="preferences.offAppVersion"
        :label="$t('group.off-app-version')"
        density="compact"
        variant="outlined"
        hide-details
        clearable
        style="min-width: 120px; max-width: 180px;"
      />
      <v-text-field
        v-model="preferences.offAppUuid"
        :label="$t('group.off-app-uuid')"
        density="compact"
        variant="outlined"
        hide-details
        clearable
        style="min-width: 240px;"
      />
    </div>

    <h3 class="text-title-large mb-1">
      {{ $t("group.usda-api") }}
    </h3>
    <p class="text-title-small mb-1">
      {{ $t("group.usda-api-description") }}
    </p>
    <v-checkbox
      v-model="preferences.usdaApiEnabled"
      hide-details
      density="compact"
      color="primary"
      :label="$t('group.usda-api-enabled')"
    />
    <div class="d-flex flex-wrap align-center ga-2 mt-2">
      <v-text-field
        v-model="usdaApiKey"
        :label="$t('group.usda-api-key')"
        :placeholder="keyPlaceholder"
        :persistent-placeholder="!!keyPlaceholder"
        :type="showKey ? 'text' : 'password'"
        :append-inner-icon="showKey ? $globals.icons.eyeOff : $globals.icons.eye"
        :disabled="!preferences.usdaApiEnabled"
        autocomplete="new-password"
        density="compact"
        variant="outlined"
        hide-details
        class="flex-grow-1"
        style="min-width: 240px;"
        data-testid="usda-api-key"
        @click:append-inner="showKey = !showKey"
      />
      <v-btn
        v-if="preferences.usdaApiKeySet && preferences.usdaApiKey !== ''"
        variant="text"
        color="error"
        size="small"
        :disabled="!preferences.usdaApiEnabled"
        data-testid="usda-api-key-remove"
        @click="preferences.usdaApiKey = ''"
      >
        {{ $t("group.usda-api-key-remove") }}
      </v-btn>
    </div>
    <p class="text-body-small mt-1 mb-0">
      <template v-if="preferences.usdaApiKeySet && preferences.usdaApiKey === ''">
        {{ $t("group.usda-api-key-will-be-removed") }}
      </template>
      <template v-else>
        {{ $t("group.usda-api-key-hint") }}
      </template>
      <a
        href="https://fdc.nal.usda.gov/api-key-signup"
        target="_blank"
        rel="noopener noreferrer"
        class="ml-1"
      >{{ $t("group.usda-api-key-signup") }}</a>
    </p>
  </div>
</template>

<script setup lang="ts">
import type { GroupPreferencesOut, OpenFoodFactsMode } from "~/lib/api/types/group";

/** The preferences with the write-only USDA key: undefined keeps the saved key, "" removes it. */
type GroupPreferencesWithUsdaKey = GroupPreferencesOut & { usdaApiKey?: string | null };

const OFF_URLS: Record<OpenFoodFactsMode, string> = {
  prod: "https://world.openfoodfacts.org",
  dev: "https://world.openfoodfacts.net",
};

const preferences = defineModel<GroupPreferencesWithUsdaKey>({ required: true });
const i18n = useI18n();
const showKey = ref(false);

const offModes = computed(() => [
  { title: i18n.t("group.off-mode-prod"), value: "prod" },
  { title: i18n.t("group.off-mode-dev"), value: "dev" },
]);
const offUrl = computed(() => OFF_URLS[preferences.value.offMode] ?? OFF_URLS.prod);

const usdaApiKey = computed({
  get: () => preferences.value.usdaApiKey ?? "",
  set: (value: string | null) => {
    // An emptied field keeps the saved key; it's removed with the dedicated button
    preferences.value.usdaApiKey = value?.trim() ? value.trim() : undefined;
  },
});

const keyPlaceholder = computed(() => {
  if (preferences.value.usdaApiKey === "") {
    return "DEMO_KEY";
  }
  return preferences.value.usdaApiKeySet ? "••••••••" : "DEMO_KEY";
});
</script>
