import type { Composer } from "vue-i18n";
import { useStore } from "../partials/use-store-factory";
import type { AllergenOut } from "~/lib/api/types/allergens";
import { useUserApi } from "~/composables/api";

const store: Ref<AllergenOut[]> = ref([]);
const loading = ref(false);
const initialized = ref(false);

export function resetAllergenStore() {
  store.value = [];
  loading.value = false;
  initialized.value = false;
}

export const useAllergenStore = function (i18n?: Composer) {
  const api = useUserApi(i18n);
  return useStore<AllergenOut>("allergen", store, loading, initialized, api.allergens);
};
