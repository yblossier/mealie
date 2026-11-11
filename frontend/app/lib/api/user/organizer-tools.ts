import { BaseCRUDAPI } from "../base/base-clients";
import { config } from "../config";
import type { ToolCreate, ToolOut, ToolWithRecipes } from "~/lib/api/types/recipe";

const prefix = config.PREFIX + "/organizers";

const routes = {
  tools: `${prefix}/tools`,
  toolsId: (id: string) => `${prefix}/tools/${id}`,
  toolsSlug: (id: string) => `${prefix}/tools/slug/${id}`,
  toolsEmpty: `${prefix}/tools/empty`,
  toolsMerge: `${prefix}/tools/merge`,
  toolsIdImage: (id: string) => `${prefix}/tools/${id}/image`,
};

export class ToolsApi extends BaseCRUDAPI<ToolCreate, ToolOut> {
  baseRoute: string = routes.tools;
  itemRoute = routes.toolsId;

  async bySlug(slug: string) {
    return await this.requests.get<ToolWithRecipes>(routes.toolsSlug(slug));
  }

  async getEmpty() {
    return await this.requests.get<ToolOut[]>(routes.toolsEmpty);
  }

  merge(fromId: string, toId: string) {
    return this.requests.post<ToolOut>(routes.toolsMerge, { fromId, toId });
  }

  updateImage(id: string, file: File) {
    const formData = new FormData();
    formData.append("image", file);
    return this.requests.put<ToolOut, FormData>(routes.toolsIdImage(id), formData);
  }

  deleteImage(id: string) {
    return this.requests.delete<ToolOut>(routes.toolsIdImage(id));
  }
}
