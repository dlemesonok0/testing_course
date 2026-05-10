import { test, expect, createProductByApi } from "./fixtures/app.fixture";
import { dishBoundaryCases, dishCategories, dishCategoryMacroCases } from "./fixtures/data";

/**
 * Расширенные граничные UI-проверки блюд.
 * Набор отделен от основных end-to-end сценариев и покрывает границы порции
 * и количества ингредиента через реальную форму блюда.
 */
test.describe("Dishes UI exhaustive boundaries", () => {
  for (const testCase of dishBoundaryCases) {
    test(`dish boundary validation: ${testCase.id}`, async ({ api, dishesPage, suffix }) => {
      const product = await createProductByApi(api, { name: `Boundary seed ${suffix}-${testCase.id}` });
      const dishName = "name" in testCase ? testCase.name : `Boundary Dish ${suffix}-${testCase.id}`;

      await dishesPage.openNewDish();
      await dishesPage.fillDishForm({
        name: dishName,
        category: dishCategories.salad,
        portionSize: testCase.portionSize,
        calories: "calories" in testCase ? testCase.calories : "0",
        protein: "protein" in testCase ? testCase.protein : "0",
        fat: "fat" in testCase ? testCase.fat : "0",
        carbs: "carbs" in testCase ? testCase.carbs : "0",
        ingredientName: product.name,
        ingredientQuantity: testCase.quantity,
      });
      await dishesPage.save();

      if (testCase.valid) {
        await dishesPage.expectDishCard(dishName);
      } else {
        await expect(dishesPage.errorBanner(), "invalid dish boundary should show a UI validation error").toBeVisible();
        await expect(dishesPage.page).toHaveURL(/\/dishes\/new$/);
      }
    });
  }

  for (const testCase of dishCategoryMacroCases) {
    test(`dish category macro: ${testCase.id}`, async ({ api, dishesPage, suffix }) => {
      const product = await createProductByApi(api, { name: `Macro seed ${suffix}-${testCase.id}` });
      const dishName = `Macro Dish ${suffix}-${testCase.id}`;

      await dishesPage.openNewDish();
      await dishesPage.fillDishForm({
        name: `${testCase.macro} ${dishName}`,
        category: "",
        portionSize: "250",
        ingredientName: product.name,
        ingredientQuantity: "100",
      });
      await dishesPage.save();

      await dishesPage.expectDishCard(dishName);
      await expect(dishesPage.page.getByTestId("dish-card")).toContainText(testCase.expectedCategory);
    });
  }

  test("explicit category overrides category macro in dish name", async ({ api, dishesPage, suffix }) => {
    const product = await createProductByApi(api, { name: `Macro explicit seed ${suffix}` });
    const dishName = `Explicit Macro Dish ${suffix}`;

    await dishesPage.openNewDish();
    await dishesPage.fillDishForm({
      name: `!десерт ${dishName}`,
      category: dishCategories.second,
      portionSize: "250",
      ingredientName: product.name,
      ingredientQuantity: "100",
    });
    await dishesPage.save();

    await dishesPage.expectDishCard(dishName);
    await expect(dishesPage.page.getByTestId("dish-card")).toContainText(dishCategories.second);
  });
});
