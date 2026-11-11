<template>
  <div v-if="imageUrl || supplierLinks.length" class="d-flex align-center flex-nowrap flex-shrink-0 ga-1">
    <v-menu
      v-if="imageUrl"
      open-on-hover
      open-on-click
      location="top"
      :close-on-content-click="false"
    >
      <template #activator="{ props: activator }">
        <v-btn
          v-bind="activator"
          icon
          variant="text"
          density="comfortable"
          size="small"
          :aria-label="$t('tool.view-photo')"
          data-testid="tool-photo"
        >
          <v-icon :size="22">
            {{ $globals.icons.informationOutline }}
          </v-icon>
        </v-btn>
      </template>
      <v-card max-width="260">
        <v-img
          :src="imageUrl"
          :alt="tool.name"
          width="260"
          max-height="260"
          contain
        />
        <v-card-text class="py-2 text-center">
          {{ tool.name }}
        </v-card-text>
      </v-card>
    </v-menu>
    <template v-if="supplierLinks.length <= MAX_INLINE_SUPPLIERS">
      <v-btn
        v-for="link in supplierLinks"
        :key="link.url"
        :href="link.url"
        target="_blank"
        rel="noopener noreferrer"
        icon
        variant="text"
        density="comfortable"
        size="small"
        :title="supplierTitle(link)"
        :aria-label="supplierTitle(link)"
        :data-testid="link.amazon ? 'tool-amazon' : 'tool-supplier'"
      >
        <v-icon :size="20" :color="link.amazon ? AMAZON_COLOR : 'primary'">
          {{ link.amazon ? AMAZON_LOGO_PATH : $globals.icons.cartPlus }}
        </v-icon>
      </v-btn>
    </template>
    <v-menu v-else location="bottom">
      <template #activator="{ props: activator }">
        <v-btn
          v-bind="activator"
          icon
          variant="text"
          density="comfortable"
          size="small"
          :title="$t('tool.search-on-suppliers')"
          :aria-label="$t('tool.search-on-suppliers')"
          data-testid="tool-suppliers"
        >
          <v-icon :size="20" color="primary">
            {{ $globals.icons.cartPlus }}
          </v-icon>
        </v-btn>
      </template>
      <v-list density="compact">
        <v-list-item
          v-for="link in supplierLinks"
          :key="link.url"
          :href="link.url"
          target="_blank"
          rel="noopener noreferrer"
          :title="link.name"
          :data-testid="link.amazon ? 'tool-amazon' : 'tool-supplier'"
        >
          <template #prepend>
            <v-icon :size="20" :color="link.amazon ? AMAZON_COLOR : 'primary'">
              {{ link.amazon ? AMAZON_LOGO_PATH : $globals.icons.cartPlus }}
            </v-icon>
          </template>
        </v-list-item>
      </v-list>
    </v-menu>
  </div>
</template>

<script setup lang="ts">
import { AMAZON_COLOR, AMAZON_LOGO_PATH, toolImageUrl } from "~/lib/recipe/tool-display";
import { DEFAULT_TOOL_SUPPLIERS, toolSupplierLinks } from "~/lib/recipe/tool-suppliers";
import type { ToolSupplierLink } from "~/lib/recipe/tool-suppliers";
import type { ToolOut } from "~/lib/api/types/recipe";
import type { ToolSupplier } from "~/lib/api/types/group";

const MAX_INLINE_SUPPLIERS = 2;

const props = withDefaults(defineProps<{
  tool: Pick<ToolOut, "id" | "name" | "image">;
  onHand: boolean;
  /** The group's suppliers; the default Amazon search when not given */
  suppliers?: ToolSupplier[] | null;
  showSuppliers?: boolean;
}>(), {
  suppliers: undefined,
  showSuppliers: true,
});

const i18n = useI18n();

const imageUrl = computed(() => toolImageUrl(props.tool));
const supplierLinks = computed(() => {
  if (props.onHand || !props.showSuppliers) {
    return [];
  }
  return toolSupplierLinks(props.suppliers ?? DEFAULT_TOOL_SUPPLIERS, props.tool.name);
});

function supplierTitle(link: ToolSupplierLink) {
  return link.amazon && link.name.toLowerCase() === "amazon"
    ? i18n.t("tool.search-on-amazon")
    : i18n.t("tool.search-on-supplier", { supplier: link.name });
}
</script>
