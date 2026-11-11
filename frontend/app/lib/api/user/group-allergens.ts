import { BaseCRUDAPI } from "../base/base-clients";
import type { AllergenCreate, AllergenOut, AllergenUpdate } from "~/lib/api/types/allergens";

const prefix = "/api";

const routes = {
  allergens: `${prefix}/groups/allergens`,
  allergensId: (id: string | number) => `${prefix}/groups/allergens/${id}`,
};

export class AllergensApi extends BaseCRUDAPI<AllergenCreate, AllergenOut, AllergenUpdate> {
  baseRoute = routes.allergens;
  itemRoute = routes.allergensId;
}
