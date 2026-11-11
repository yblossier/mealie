<template>
  <div>
    <p class="text-subtitle-2 mb-3">
      {{ $t("group.tool-suppliers-description") }}
    </p>
    <div
      v-for="(supplier, index) in suppliers"
      :key="index"
      class="d-flex flex-wrap align-center ga-2 mb-2"
      data-testid="tool-supplier-row"
    >
      <v-text-field
        v-model="supplier.name"
        :label="$t('group.supplier-name')"
        :rules="[required]"
        density="compact"
        variant="outlined"
        hide-details="auto"
        style="min-width: 140px; max-width: 200px;"
      />
      <v-text-field
        v-model="supplier.url"
        :label="$t('group.supplier-url')"
        :rules="[required, validUrl]"
        placeholder="https://www.example.com/search?q={query}"
        density="compact"
        variant="outlined"
        hide-details="auto"
        style="min-width: 240px;"
        class="flex-grow-1"
      />
      <v-switch
        v-model="supplier.enabled"
        :aria-label="$t('group.supplier-enabled')"
        :title="$t('group.supplier-enabled')"
        color="primary"
        density="compact"
        hide-details
        class="flex-grow-0"
      />
      <v-btn
        :icon="$globals.icons.delete"
        :title="$t('group.remove-supplier')"
        :aria-label="$t('group.remove-supplier')"
        variant="text"
        size="small"
        color="error"
        @click="removeSupplier(index)"
      />
    </div>
    <BaseButton
      create
      small
      class="mt-1"
      @click="addSupplier"
    >
      {{ $t("group.add-supplier") }}
    </BaseButton>
  </div>
</template>

<script setup lang="ts">
import type { ToolSupplier } from "~/lib/api/types/group";
import { isValidSupplierUrl } from "~/lib/recipe/tool-suppliers";

const suppliers = defineModel<ToolSupplier[]>({ required: true });
const i18n = useI18n();

function required(value: string) {
  return !!value?.trim() || i18n.t("validators.required");
}

function validUrl(value: string) {
  return isValidSupplierUrl(value) || i18n.t("validators.invalid-url");
}

function addSupplier() {
  suppliers.value = [...suppliers.value, { name: "", url: "", enabled: true }];
}

function removeSupplier(index: number) {
  suppliers.value = suppliers.value.filter((_, i) => i !== index);
}
</script>
