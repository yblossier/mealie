<template>
  <v-menu
    v-model="open"
    location="bottom end"
    :close-on-content-click="false"
  >
    <template #activator="{ props: menuProps }">
      <v-btn
        v-bind="menuProps"
        icon
        variant="text"
        size="small"
        density="comfortable"
        color="primary"
        class="ingredient-shop-btn"
        :title="$t('recipe.add-ingredient-to-list')"
        :aria-label="$t('recipe.add-ingredient-to-list')"
        data-testid="ingredient-add-to-list"
        @click.stop
      >
        <v-icon size="20">
          {{ $globals.icons.cartPlus }}
        </v-icon>
      </v-btn>
    </template>
    <v-card min-width="220" @click.stop>
      <v-card-subtitle class="pt-3">
        {{ $t("recipe.add-ingredient-to-list") }}
      </v-card-subtitle>
      <div v-if="loading" class="d-flex justify-center pa-4">
        <v-progress-circular indeterminate size="24" color="primary" />
      </div>
      <v-list v-else-if="visibleLists.length" density="compact">
        <v-list-item
          v-for="list in visibleLists"
          :key="list.id"
          :title="list.name || ''"
          :prepend-icon="$globals.icons.cartCheck"
          :disabled="adding"
          data-testid="ingredient-add-to-list-target"
          @click="addTo(list)"
        />
      </v-list>
      <v-card-text v-else class="text-medium-emphasis">
        {{ $t("shopping-list.no-shopping-lists-found") }}
      </v-card-text>
    </v-card>
  </v-menu>
</template>

<script setup lang="ts">
import { useUserApi } from "~/composables/api";
import { alert } from "~/composables/use-toast";
import { useShoppingListPreferences } from "~/composables/use-users/preferences";
import type { RecipeIngredient, ShoppingListSummary } from "~/lib/api/types/household";

interface Props {
  ingredient: RecipeIngredient;
  recipeId: string;
  scale?: number;
}
const props = withDefaults(defineProps<Props>(), {
  scale: 1,
});

const api = useUserApi();
const i18n = useI18n();
const auth = useMealieAuth();
const router = useRouter();
const preferences = useShoppingListPreferences();

const open = ref(false);
const loading = ref(false);
const adding = ref(false);
const lists = ref<ShoppingListSummary[]>([]);

const visibleLists = computed(() => {
  const own = lists.value.filter(list => list.userId === auth.user.value?.id);
  // a household with no list of the user's own still gets somewhere to send the ingredient
  return preferences.value.viewAllLists || !own.length ? lists.value : own;
});

watch(open, async (isOpen) => {
  if (!isOpen) {
    return;
  }
  loading.value = true;
  const { data } = await api.shopping.lists.getAll(1, -1, { orderBy: "name", orderDirection: "asc" });
  lists.value = (data?.items as ShoppingListSummary[] | undefined) ?? [];
  loading.value = false;
});

async function addTo(list: ShoppingListSummary) {
  adding.value = true;
  const { error } = await api.shopping.lists.addRecipes(list.id, [
    { recipeId: props.recipeId, recipeIncrementQuantity: props.scale, recipeIngredients: [props.ingredient] },
  ]);
  adding.value = false;
  open.value = false;

  if (error) {
    alert.error(i18n.t("recipe.failed-to-add-recipes-to-list"));
    return;
  }
  const ingredient = props.ingredient.food?.name || props.ingredient.note || props.ingredient.display || "";
  alert.success(i18n.t("recipe.ingredient-added-to-list", { ingredient, list: list.name }), null, {
    action: {
      message: i18n.t("general.view"),
      onClick: () => router.push(`/shopping-lists/${list.id}`),
    },
  });
}
</script>
