<template>
  <div>
    <RecipeIngredients
      :value="recipe.recipeIngredient"
      :scale="scale"
      :is-cook-mode="isCookMode"
      :storage-key="ingredientStorageKey"
      :recipe-id="recipe.id"
    />
    <RecipeAllergenNote
      v-if="!isEditMode && isOwnGroup && recipe.settings?.showAllergens !== false"
      :slug="recipe.slug"
      :revision="allergenRevision"
    />
    <div v-if="!isEditMode && recipe.tools && recipe.tools.length > 0">
      <h2 class="mt-4 text-h5 font-weight-medium opacity-80">
        {{ $t('tool.required-tools') }}
      </h2>
      <v-list density="compact" class="tool-list">
        <v-list-item
          v-for="(row, position) in toolRows"
          :key="row.tool.id || row.index"
          density="compact"
          class="px-1"
          :class="{
            'tool-row--child': row.child,
            'tool-row--last': row.last,
            'tool-row--parent': toolRows[position + 1]?.child,
          }"
          :data-testid="row.child ? 'tool-row-child' : 'tool-row'"
        >
          <template #prepend>
            <v-checkbox
              v-model="recipeTools[row.index].onHand"
              hide-details
              class="pt-0 py-auto"
              color="secondary"
              density="compact"
              @change="updateTool(row.index)"
            />
          </template>
          <v-list-item-title class="d-flex align-center">
            <v-icon size="small" class="mr-2 opacity-70">
              {{ toolCategoryIcon(row.tool.category) }}
            </v-icon>
            <span class="text-truncate">{{ row.tool.name }}</span>
          </v-list-item-title>
          <v-list-item-subtitle
            v-if="toolDetails(row.tool)"
            class="tool-details text-medium-emphasis"
            data-testid="tool-details"
          >
            {{ toolDetails(row.tool) }}
          </v-list-item-subtitle>
          <template #append>
            <RecipeToolLinks
              :tool="row.tool"
              :on-hand="recipeTools[row.index]?.onHand ?? false"
              :suppliers="toolSuppliers"
              :show-suppliers="showToolSuppliers"
              class="ms-2"
            />
          </template>
        </v-list-item>
      </v-list>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { RecipeToolWithOnHand } from "~/composables/store/use-tool-store";
import { useLoggedInState } from "~/composables/use-logged-in-state";
import { usePageState, usePageUser } from "~/composables/recipe-page/shared-state";
import { useToolStore } from "~/composables/store";
import { useGroupSelf } from "~/composables/use-groups";
import type { RecipeOut, ToolOut } from "~/lib/api/types/recipe";
import RecipeIngredients from "~/components/Domain/Recipe/RecipeIngredients.vue";
import RecipeAllergenNote from "~/components/Domain/Recipe/RecipeAllergenNote.vue";
import RecipeToolLinks from "~/components/Domain/Recipe/RecipeToolLinks.vue";
import { dishSizeLabel, toolCategoryIcon, toolHierarchy } from "~/lib/recipe/tool-display";

interface Props {
  recipe: RecipeOut;
  scale: number;
  isCookMode?: boolean;
  ingredientStorageKey?: string;
}
const props = withDefaults(defineProps<Props>(), {
  isCookMode: false,
  ingredientStorageKey: undefined,
});

const { isOwnGroup } = useLoggedInState();

const toolStore = isOwnGroup.value ? useToolStore() : null;
// The group's tool suppliers; the default Amazon search for visitors from other groups
const groupSelf = isOwnGroup.value ? useGroupSelf().group : null;
const groupPreferences = groupSelf ? computed(() => groupSelf.value?.preferences) : null;
const toolSuppliers = computed(() => groupPreferences ? (groupPreferences.value?.toolSuppliers ?? []) : undefined);
const showToolSuppliers = computed(() => groupPreferences ? (groupPreferences.value?.showToolSupplierLinks ?? false) : true);
const { user } = usePageUser();
const { isEditMode } = usePageState(props.recipe.slug);

const recipeTools = ref<RecipeToolWithOnHand[]>([]);
watch(() => props.recipe.tools, () => {
  if (!(user.householdSlug && toolStore)) {
    recipeTools.value = props.recipe.tools.map(tool => ({ ...tool, onHand: false }) as RecipeToolWithOnHand);
  }
  else {
    recipeTools.value = props.recipe.tools.map((tool) => {
      const onHand = tool.householdsWithTool?.includes(user.householdSlug) || false;
      return { ...tool, onHand } as RecipeToolWithOnHand;
    });
  }
}, { immediate: true });

const i18n = useI18n();

const allergenRevision = computed(() => JSON.stringify(
  (props.recipe.recipeIngredient ?? []).map(i => [i.food?.id, i.note, i.originalText]),
));

const toolRows = computed(() => toolHierarchy(props.recipe.tools ?? []));

/** The shape, size and usages of a dish, in one short line. */
function toolDetails(tool: ToolOut): string {
  if (tool.category !== "dishes") {
    return "";
  }
  const parts: string[] = [];
  if (tool.dishShape) parts.push(i18n.t(`tool.shape-${tool.dishShape}`));
  const size = dishSizeLabel(tool);
  if (size) parts.push(size);
  if (tool.usages?.length) parts.push(tool.usages.map(usage => i18n.t(`tool.usage-${usage}`)).join(", "));
  return parts.join(" · ");
}
function updateTool(index: number) {
  if (user.id && user.householdSlug && toolStore) {
    const tool = recipeTools.value[index];
    if (tool.onHand && !tool.householdsWithTool?.includes(user.householdSlug)) {
      if (!tool.householdsWithTool) {
        tool.householdsWithTool = [user.householdSlug];
      }
      else {
        tool.householdsWithTool.push(user.householdSlug);
      }
    }
    else if (!tool.onHand && tool.householdsWithTool?.includes(user.householdSlug)) {
      tool.householdsWithTool = tool.householdsWithTool.filter(household => household !== user.householdSlug);
    }

    toolStore.actions.updateOne(tool);
  }
  else {
    console.log("no user, skipping server update");
  }
}
</script>

<style scoped>
.tool-details {
  font-size: 0.8rem;
  opacity: 1;
}

/*
 * Accessories are indented under their appliance and joined to it by a line
 * running from the appliance checkbox to each accessory checkbox.
 */
.tool-list {
  --tool-link-x: 24px;
  --tool-link-color: rgba(var(--v-theme-on-surface), 0.3);
}
.tool-row--child,
.tool-row--parent {
  position: relative;
}
.tool-row--child {
  margin-inline-start: 28px;
}
.tool-row--parent::after {
  content: "";
  position: absolute;
  left: var(--tool-link-x);
  top: calc(50% + 10px);
  bottom: 0;
  border-left: 2px solid var(--tool-link-color);
}
.tool-row--child::before {
  content: "";
  position: absolute;
  left: calc(var(--tool-link-x) - 28px);
  top: 0;
  height: 50%;
  width: 18px;
  border-left: 2px solid var(--tool-link-color);
  border-bottom: 2px solid var(--tool-link-color);
  border-bottom-left-radius: 6px;
}
.tool-row--child:not(.tool-row--last)::after {
  content: "";
  position: absolute;
  left: calc(var(--tool-link-x) - 28px);
  top: 50%;
  bottom: 0;
  border-left: 2px solid var(--tool-link-color);
}
</style>
