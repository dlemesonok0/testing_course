import { test, expect } from "./fixtures/app.fixture";
import { productNutritionCases, validProduct } from "./fixtures/data";

/**
 * Расширенные граничные UI-проверки продуктов.
 * Эти тесты вынесены отдельно от основных системных сценариев, чтобы явно
 * показать exhaustive-набор по эквивалентным классам и границам формы.
 */
test.describe("Products UI exhaustive boundaries", () => {
  for (const testCase of productNutritionCases) {
    test(`product validation boundary: ${testCase.id}`, async ({ productsPage, suffix }) => {
      const product = { ...validProduct(`${suffix}-${testCase.id}`), ...testCase.override };

      await productsPage.openNewProduct();
      await productsPage.fillProductForm(product);
      await productsPage.save();

      if (testCase.valid) {
        await productsPage.expectProductCard(product.name);
      } else {
        await expect(productsPage.errorBanner(), "invalid product data should stay on the form and show a UI error").toBeVisible();
        await expect(productsPage.page).toHaveURL(/\/products\/new$/);
      }
    });
  }

  test("limits product photos by boundary values 5 and 6", async ({ productsPage, suffix }) => {
    await test.step("Five photos are accepted", async () => {
      await productsPage.openNewProduct();
      await productsPage.fillProductForm(validProduct(`${suffix}-five-photos`));
      await productsPage.uploadPhotos(5);
      await productsPage.save();
      await productsPage.expectProductCard(`UI Product ${suffix}-five-photos`);
    });

    await test.step("Six photos show a validation message in UI", async () => {
      await productsPage.openNewProduct();
      await productsPage.fillProductForm(validProduct(`${suffix}-six-photos`));
      await productsPage.uploadPhotos(6);
      await expect(productsPage.errorBanner()).toBeVisible();
      await expect(productsPage.page).toHaveURL(/\/products\/new$/);
    });
  });
});
