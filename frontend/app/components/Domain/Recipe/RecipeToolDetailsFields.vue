<template>
  <div>
    <v-select
      v-model="model.category"
      :items="categoryItems"
      :label="$t('tool.category')"
      :prepend-inner-icon="toolCategoryIcon(model.category)"
      data-testid="tool-category"
    >
      <template #item="{ item, props: itemProps }">
        <v-list-item v-bind="itemProps">
          <template #prepend>
            <v-icon>{{ item.icon }}</v-icon>
          </template>
        </v-list-item>
      </template>
    </v-select>

    <template v-if="model.category === 'dishes'">
      <v-btn-toggle
        v-model="model.dishShape"
        mandatory
        density="compact"
        color="primary"
        variant="outlined"
        divided
        class="mb-4"
        data-testid="tool-dish-shape"
      >
        <v-btn v-for="shape in DISH_SHAPES" :key="shape" :value="shape" size="small">
          {{ $t(`tool.shape-${shape}`) }}
        </v-btn>
      </v-btn-toggle>

      <div class="d-flex ga-2">
        <template v-if="model.dishShape === 'round'">
          <v-text-field v-model.number="model.diameter" v-bind="sizeFieldProps" :label="$t('tool.diameter')" data-testid="tool-diameter" />
        </template>
        <template v-else>
          <v-text-field v-model.number="model.length" v-bind="sizeFieldProps" :label="$t('tool.length')" data-testid="tool-length" />
          <v-text-field v-model.number="model.width" v-bind="sizeFieldProps" :label="$t('tool.width')" data-testid="tool-width" />
        </template>
        <v-text-field v-model.number="model.height" v-bind="sizeFieldProps" :label="$t('tool.height')" data-testid="tool-height" />
      </div>

      <v-select
        v-model="model.usages"
        :items="usageItems"
        :label="$t('tool.usages')"
        multiple
        chips
        closable-chips
        data-testid="tool-usages"
      />
    </template>

    <v-autocomplete
      v-if="model.category === 'appliance'"
      v-model="model.parentId"
      :items="parentItems"
      :custom-filter="normalizeFilter"
      item-title="name"
      item-value="id"
      :label="$t('tool.accessory-of')"
      :hint="hasAccessories ? $t('tool.has-accessories-hint') : $t('tool.accessory-of-hint')"
      :disabled="hasAccessories"
      persistent-hint
      clearable
      class="mb-4"
      data-testid="tool-parent"
    />
  </div>
</template>

<script setup lang="ts">
import { normalizeFilter } from "~/composables/use-utils";
import { DISH_SHAPES, DISH_USAGES, TOOL_CATEGORIES, toolCategoryIcon, type ToolFormData } from "~/lib/recipe/tool-display";

interface KnownTool {
  id: string;
  name: string;
  category?: string | null;
  parentId?: string | null;
}

const props = withDefaults(defineProps<{
  /** All the tools of the group, to pick the appliance of an accessory. */
  tools?: KnownTool[];
  /** The id of the edited tool, unset when creating one. */
  toolId?: string | null;
}>(), {
  tools: () => [],
  toolId: null,
});

const model = defineModel<ToolFormData>({ required: true });

const i18n = useI18n();

const categoryItems = computed(() => TOOL_CATEGORIES.map(category => ({
  value: category,
  title: i18n.t(`tool.category-${category}`),
  icon: toolCategoryIcon(category),
})));

const usageItems = computed(() => DISH_USAGES.map(usage => ({ value: usage, title: i18n.t(`tool.usage-${usage}`) })));

const sizeFieldProps = { type: "number", min: 0, step: 0.5, suffix: "cm", hideSpinButtons: true };

// an appliance with accessories cannot become an accessory itself
const hasAccessories = computed(() => !!props.toolId && props.tools.some(tool => tool.parentId === props.toolId));

const parentItems = computed(() => props.tools.filter(tool =>
  tool.category === "appliance" && !tool.parentId && tool.id !== props.toolId,
));

watch(() => model.value.category, (category) => {
  if (category === "dishes" && !model.value.dishShape) {
    model.value.dishShape = "rectangular";
  }
}, { immediate: true });
</script>
