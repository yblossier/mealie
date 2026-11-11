<template>
  <div
    v-if="names.length > 0"
    class="allergy-block mt-4"
    :class="{ 'allergy-block--print': print }"
    role="note"
    data-testid="recipe-allergen-note"
  >
    <v-icon class="allergy-block__icon" size="28">
      {{ $globals.icons.allergies }}
    </v-icon>
    <div>
      <div class="allergy-block__title">
        {{ $t("recipe.allergy-title") }}
      </div>
      <i18n-t keypath="recipe.allergy-contains" tag="div" scope="global" class="allergy-block__text">
        <template #allergens>
          <template v-for="(name, index) in names" :key="name">
            <span v-if="index > 0">, </span><strong>{{ name }}</strong>
          </template>
        </template>
      </i18n-t>
      <div v-if="!print" class="text-caption text-medium-emphasis mt-1">
        {{ $t("recipe.allergens-hint") }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useUserApi } from "~/composables/api";
import type { RecipeAllergen } from "~/lib/api/types/allergens";

const props = defineProps<{
  slug: string;
  /** Changes whenever the ingredients change, to refresh the detection. */
  revision?: string | null;
  /** Drops the on-screen hint, which has nothing to offer on paper. */
  print?: boolean;
}>();

const api = useUserApi();
const allergens = ref<RecipeAllergen[]>([]);
const names = computed(() => [...new Set(allergens.value.map(allergen => allergen.name.trim()).filter(Boolean))]);

async function refresh() {
  if (!props.slug) {
    allergens.value = [];
    return;
  }
  const { data } = await api.recipes.getAllergens(props.slug);
  allergens.value = data ?? [];
}

watch(() => [props.slug, props.revision], refresh, { immediate: true });
</script>

<style scoped>
.allergy-block {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  border-left: 4px solid #c62828;
  background-color: #fdecea;
  color: #3b1010;
  break-inside: avoid;
  print-color-adjust: exact;
  -webkit-print-color-adjust: exact;
}

.allergy-block__icon {
  color: #c62828 !important;
  flex: 0 0 auto;
}

.allergy-block__title {
  font-weight: 600;
  color: #c62828;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-size: 0.8rem;
}

.allergy-block__text {
  font-size: 0.95rem;
}

.allergy-block .text-medium-emphasis {
  color: #5f3a3a !important;
}
</style>
