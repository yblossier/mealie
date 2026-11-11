import { BaseAPI } from "../base/base-clients";
import type { FoodCompositionCiqualUpdate, FoodCompositionStatus } from "~/lib/api/types/group";

const prefix = "/api/groups/food-composition";

const routes = {
  status: prefix,
  ciqual: `${prefix}/ciqual`,
  ciqualRefresh: `${prefix}/ciqual/refresh`,
};

export class FoodCompositionAPI extends BaseAPI {
  async getStatus() {
    return await this.requests.get<FoodCompositionStatus>(routes.status);
  }

  async updateCiqual(payload: FoodCompositionCiqualUpdate) {
    return await this.requests.put<FoodCompositionStatus, FoodCompositionCiqualUpdate>(routes.ciqual, payload);
  }

  async refreshCiqual() {
    return await this.requests.post<FoodCompositionStatus>(routes.ciqualRefresh, {});
  }
}
