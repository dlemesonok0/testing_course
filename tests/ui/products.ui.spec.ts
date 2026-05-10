import { test, expect, createProductByApi } from "./fixtures/app.fixture";
import { productCategories, validProduct } from "./fixtures/data";
import { ProductsLocators } from "./locators/ProductsLocators";

/**
 * Системные UI-тесты продуктов.
 * Покрывают пользовательский путь Product CRUD, валидацию данных,
 * ограничение фотографий, поиск, фильтрацию и сортировку.
 */
test.describe("Products UI", () => {
  test("creates product with valid data through UI", async ({ productsPage, suffix }) => {
    const product = validProduct(suffix);

    await test.step("Fill product form with a valid equivalence class", async () => {
      await productsPage.openNewProduct();
      await productsPage.fillProductForm(product);
      await productsPage.save();
    });

    await test.step("Product card contains saved business data", async () => {
      await productsPage.expectProductCard(product.name);
      await expect(productsPage.page.getByTestId(ProductsLocators.detail)).toContainText(product.composition!);
      await expect(productsPage.page.getByTestId(ProductsLocators.nutrition)).toContainText(product.calories);
    });
  });

  test("searches, filters by category and flags, and sorts products by calories", async ({ api, productsPage, suffix }) => {
    const low = await createProductByApi(api, {
      name: `Apple ${suffix}`,
      calories: "30",
      category: productCategories.vegetables,
      is_vegan: true,
      is_gluten_free: true,
      is_sugar_free: true,
    });
    const high = await createProductByApi(api, {
      name: `Beef ${suffix}`,
      calories: "250",
      category: productCategories.meat,
      is_vegan: false,
      is_gluten_free: true,
      is_sugar_free: true,
    });
    await createProductByApi(api, {
      name: `Candy ${suffix}`,
      calories: "400",
      category: productCategories.frozen,
      is_vegan: true,
      is_gluten_free: false,
      is_sugar_free: false,
    });

    await productsPage.openList();

    await test.step("Search by matching name", async () => {
      await productsPage.search(low.name);
      await expect(productsPage.cardByName(low.name)).toBeVisible();
      await expect(productsPage.visibleCardTitles()).not.toContainText([high.name]);
    });

    await test.step("Filter by category and flags", async () => {
      await productsPage.search("");
      await productsPage.filterByCategory(productCategories.meat);
      await expect(productsPage.cardByName(high.name)).toBeVisible();
      await expect(productsPage.visibleCardTitles()).not.toContainText([low.name]);
      await productsPage.page.getByTestId("products-category-filter").selectOption("");
      await productsPage.filterByFlag(0);
      await expect(productsPage.cardByName(low.name)).toBeVisible();
      await expect(productsPage.visibleCardTitles()).not.toContainText([high.name]);
    });

    await test.step("Sort by calories descending", async () => {
      await productsPage.filterByCategory(productCategories.meat);
      await productsPage.page.getByTestId("products-category-filter").selectOption("");
      await productsPage.filterByFlag(0);
      await productsPage.sortByCalories("desc");
      await expect(productsPage.cardByName(`Candy ${suffix}`)).toBeVisible();
      await expect.poll(async () => {
        const titles = await productsPage.visibleTitleTexts();
        return titles.filter((title) => [low.name, high.name, `Candy ${suffix}`].includes(title));
      }).toEqual([`Candy ${suffix}`, high.name, low.name]);
    });
  });
});
