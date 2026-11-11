<template>
  <v-tooltip
    location="bottom"
    nudge-right="50"
    color="secondary"
  >
    <template #activator="{ props: tooltipProps }">
      <!-- Only the heart: white inside until the recipe is a favorite, then red -->
      <v-btn
        v-if="isFavorite || showAlways"
        icon
        variant="text"
        :size="buttonStyle ? 40 : 'small'"
        :aria-pressed="isFavorite"
        :aria-label="isFavorite ? $t('recipe.remove-from-favorites') : $t('recipe.add-to-favorites')"
        data-testid="favorite-button"
        v-bind="{ ...tooltipProps, ...$attrs }"
        :color="isFavorite ? 'error' : undefined"
        @click.prevent="toggleFavorite"
      >
        <span class="favorite-heart" :style="{ fontSize: `${iconSize}px` }">
          <v-icon :size="iconSize" :color="isFavorite ? 'error' : 'white'" data-testid="favorite-fill">
            {{ $globals.icons.heart }}
          </v-icon>
          <v-icon
            class="favorite-heart__outline"
            :size="iconSize"
            :color="isFavorite ? 'error' : (buttonStyle ? 'info' : undefined)"
          >
            {{ $globals.icons.heartOutline }}
          </v-icon>
        </span>
      </v-btn>
    </template>
    <span>{{ isFavorite ? $t("recipe.remove-from-favorites") : $t("recipe.add-to-favorites") }}</span>
  </v-tooltip>
</template>

<script setup lang="ts">
import { useUserSelfRatings } from "~/composables/use-users";
import { useUserApi } from "~/composables/api";

interface Props {
  recipeId?: string;
  showAlways?: boolean;
  buttonStyle?: boolean;
}
const props = withDefaults(defineProps<Props>(), {
  recipeId: "",
  showAlways: false,
  buttonStyle: false,
});

const { userRatings, refreshUserRatings } = useUserSelfRatings();

const isFavorite = computed(() => {
  const rating = userRatings.value.find(r => r.recipeId === props.recipeId);
  return rating?.isFavorite || false;
});

// as big as the round action buttons next to it on the recipe page
const iconSize = computed(() => (props.buttonStyle ? 40 : 24));

async function toggleFavorite() {
  const api = useUserApi();
  const auth = useMealieAuth();

  if (!auth.user.value) return;
  if (!isFavorite.value) {
    await api.users.addFavorite(auth.user.value?.id, props.recipeId);
  }
  else {
    await api.users.removeFavorite(auth.user.value?.id, props.recipeId);
  }
  await refreshUserRatings();
}
</script>

<style scoped>
.favorite-heart {
  position: relative;
  display: inline-flex;
}

.favorite-heart__outline {
  position: absolute;
  inset: 0;
}
</style>
