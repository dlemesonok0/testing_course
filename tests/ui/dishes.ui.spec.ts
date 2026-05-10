import { test, expect, createProductByApi } from "./fixtures/app.fixture";
import { dishCategories } from "./fixtures/data";

/**
 * Системные UI-тесты блюд.
 * Проверяют создание блюда из существующего продукта, автоматический расчет
 * КБЖУ, ограничения диетических флагов и запрет удаления используемого продукта.
 * Сценарии выбраны по эквивалентному разбиению и граничным значениям.
 */
test.describe("Dishes UI", () => {
  test("creates dish from existing product and applies nutrition draft", async ({ api, dishesPage, suffix }) => {
    const product = await createProductByApi(api, {
      name: `Dish seed ${suffix}`,
      calories: "120",
      protein: "10",
      fat: "4",
      carbs: "12",
      is_vegan: true,
      is_gluten_free: true,
      is_sugar_free: true,
    });
    const dishName = `UI Dish ${suffix}`;

    await test.step("Select product ingredient and wait for draft nutrition", async () => {
      await dishesPage.openNewDish();
      await dishesPage.fillDishForm({
        name: dishName,
        category: dishCategories.second,
        portionSize: "250",
        ingredientName: product.name,
        ingredientQuantity: "100",
      });
      await dishesPage.expectDraftVisible();
      await expect(dishesPage.page.getByTestId("dish-calories")).toHaveValue("120");
    });

    await test.step("Save dish and verify the user-facing card", async () => {
      await dishesPage.save();
      await dishesPage.expectDishCard(dishName);
      await expect(dishesPage.page.getByTestId("dish-ingredients")).toContainText(product.name);
    });
  });

  test("disables vegan dish flag when ingredient is not vegan", async ({ api, dishesPage, suffix }) => {
    const product = await createProductByApi(api, {
      name: `Non vegan seed ${suffix}`,
      is_vegan: false,
      is_gluten_free: true,
      is_sugar_free: true,
    });

    await dishesPage.openNewDish();
    await dishesPage.fillDishForm({
      name: `Flag Dish ${suffix}`,
      category: dishCategories.second,
      portionSize: "250",
      ingredientName: product.name,
      ingredientQuantity: "100",
    });

    await dishesPage.expectDraftVisible();
    await dishesPage.expectVeganDisabled();
  });

  test("does not delete a product that is used in a dish", async ({ api, productsPage, dishesPage, suffix }) => {
    const product = await createProductByApi(api, { name: `Protected Product ${suffix}` });

    await test.step("Create dish that references the product", async () => {
      await dishesPage.openNewDish();
      await dishesPage.fillDishForm({
        name: `Protected Dish ${suffix}`,
        category: dishCategories.second,
        portionSize: "250",
        ingredientName: product.name,
        ingredientQuantity: "100",
      });
      await dishesPage.save();
      await dishesPage.expectDishCard(`Protected Dish ${suffix}`);
    });

    await test.step("Try to delete linked product through UI", async () => {
      await productsPage.openList();
      await expect(productsPage.cardByName(product.name)).toBeVisible();
      await productsPage.deleteCard(product.name);
      await expect(productsPage.errorBanner()).toBeVisible();
      await expect(productsPage.cardByName(product.name)).toBeVisible();
    });
  });
});
