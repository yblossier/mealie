<template>
  <div v-if="preferences">
    <BaseCardSectionTitle :title="$t('group.group-preferences')" />
    <div class="mb-6">
      <v-checkbox
        v-model="local.privateGroup"
        hide-details
        density="compact"
        color="primary"
        :label="$t('group.private-group')"
      />
      <div class="ml-8">
        <p class="text-title-small my-0 py-0">
          {{ $t("group.private-group-description") }}
        </p>
        <DocLink
          class="mt-2"
          link="/documentation/getting-started/faq/#how-do-private-groups-households-and-recipes-work"
        />
      </div>
    </div>
    <div class="mb-6">
      <v-checkbox
        v-model="local.showAnnouncements"
        hide-details
        density="compact"
        color="primary"
        :label="$t('announcements.show-announcements-from-mealie')"
      />
      <div class="ml-8">
        <p class="text-title-small my-0 py-0">
          {{ $t("announcements.show-announcements-setting-description") }}
        </p>
      </div>
    </div>

    <BaseCardSectionTitle :title="$t('group.data-tables')" />
    <div class="mb-6">
      <v-text-field
        v-model.number="local.defaultTablePageSize"
        type="number"
        :min="TABLE_PAGE_SIZE_MIN"
        :max="TABLE_PAGE_SIZE_MAX"
        :rules="[validPageSize]"
        :label="$t('group.default-table-page-size')"
        :hint="$t('group.default-table-page-size-description')"
        persistent-hint
        density="compact"
        variant="outlined"
        style="max-width: 360px;"
        data-testid="default-table-page-size"
      />
    </div>

    <BaseCardSectionTitle :title="$t('group.tool-suppliers')" />
    <div class="mb-6">
      <v-checkbox
        v-model="local.showToolSupplierLinks"
        hide-details
        density="compact"
        color="primary"
        :label="$t('group.show-tool-supplier-links')"
      />
      <div class="ml-8 mb-4">
        <p class="text-title-small my-0 py-0">
          {{ $t("group.show-tool-supplier-links-description") }}
        </p>
      </div>
      <GroupToolSuppliersEditor v-model="local.toolSuppliers" />
    </div>

    <BaseCardSectionTitle :title="$t('group.food-apis')" />
    <GroupFoodApisEditor v-model="local" />
  </div>
</template>

<script setup lang="ts">
import GroupToolSuppliersEditor from "./GroupToolSuppliersEditor.vue";
import GroupFoodApisEditor from "./GroupFoodApisEditor.vue";
import type { GroupPreferencesOut } from "~/lib/api/types/group";

/** The preferences with the write-only USDA key: undefined keeps the saved key, "" removes it. */
type GroupPreferencesWithUsdaKey = GroupPreferencesOut & { usdaApiKey?: string | null };

const TABLE_PAGE_SIZE_MIN = 5;
const TABLE_PAGE_SIZE_MAX = 500;

const preferences = defineModel<GroupPreferencesWithUsdaKey>({ required: true });
const i18n = useI18n();
const local = reactive<GroupPreferencesWithUsdaKey>({ ...preferences.value, toolSuppliers: [...(preferences.value.toolSuppliers ?? [])] });
watch(local, (newVal) => { preferences.value = { ...newVal }; });
watch(preferences, (newVal) => {
  if (!newVal) {
    return;
  }
  Object.assign(local, newVal);
  // The saved preferences don't carry the write-only USDA key: forget the typed one
  if (!("usdaApiKey" in newVal)) {
    delete local.usdaApiKey;
  }
});

function validPageSize(value: number) {
  return (Number.isInteger(value) && value >= TABLE_PAGE_SIZE_MIN && value <= TABLE_PAGE_SIZE_MAX)
    || i18n.t("group.table-page-size-range", { min: TABLE_PAGE_SIZE_MIN, max: TABLE_PAGE_SIZE_MAX });
}
</script>
