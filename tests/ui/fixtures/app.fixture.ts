import { expect, test as base } from "@playwright/test";
import type { APIRequestContext, Page } from "@playwright/test";

import { DishesPage } from "../pages/DishesPage";
import { ProductsPage } from "../pages/ProductsPage";
import { API_BASE, cookingStates, productCategories } from "./data";

type UiFixtures = {
  api: APIRequestContext;
  productsPage: ProductsPage;
  dishesPage: DishesPage;
  suffix: string;
};

export async function createProductByApi(
  api: APIRequestContext,
  overrides: Record<string, string | boolean> = {},
) {
  const payload = {
    name: `API Product ${Date.now()}`,
    calories: "100",
    protein: "10",
    fat: "5",
    carbs: "20",
    composition: "API seed",
    category: productCategories.vegetables,
    cooking_state: cookingStates.ready,
    is_vegan: "true",
    is_gluten_free: "true",
    is_sugar_free: "true",
    ...overrides,
  };

  const multipart = Object.fromEntries(Object.entries(payload).map(([key, value]) => [key, String(value)]));
  const response = await api.post(`${API_BASE}/products`, { multipart });
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json();
}

export const test = base.extend<UiFixtures>({
  api: async ({ request }, use) => {
    await use(request);
  },

  suffix: async ({}, use, testInfo) => {
    await use(`${testInfo.workerIndex}-${Date.now()}-${testInfo.retry}`);
  },

  productsPage: async ({ page }, use) => {
    await use(new ProductsPage(page));
  },

  dishesPage: async ({ page }, use) => {
    await use(new DishesPage(page));
  },

});

test.beforeEach(async ({ api, page }) => {
  const health = await api.get(`${API_BASE}/health`);
  expect(health.ok(), "preprod backend healthcheck should be available").toBeTruthy();
  await page.goto("/");
});

export { expect };
export type { Page };
