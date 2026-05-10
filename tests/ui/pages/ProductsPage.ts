import { expect, type Locator, type Page } from "@playwright/test";

import type { ProductFormData } from "../fixtures/data";
import { ProductsLocators } from "../locators/ProductsLocators";

export class ProductsPage {
  constructor(readonly page: Page) {}

  async openList() {
    await this.page.goto("/");
  }

  async openNewProduct() {
    await this.page.goto("/products/new");
  }

  cards() {
    return this.page.getByTestId(ProductsLocators.card);
  }

  visibleCardTitles() {
    return this.page.getByTestId(ProductsLocators.cardTitle);
  }

  cardByName(name: string): Locator {
    return this.cards().filter({ has: this.page.getByTestId(ProductsLocators.cardTitle).filter({ hasText: name }) });
  }

  errorBanner() {
    return this.page.getByTestId(ProductsLocators.errorBanner);
  }

  async fillProductForm(data: ProductFormData) {
    await this.page.getByTestId(ProductsLocators.name).fill(data.name);
    await this.page.getByTestId(ProductsLocators.composition).fill(data.composition ?? "");
    if (data.category) await this.page.getByTestId(ProductsLocators.category).selectOption({ label: data.category });
    if (data.cookingState) await this.page.getByTestId(ProductsLocators.cookingState).selectOption({ label: data.cookingState });

    await this.page.getByTestId(ProductsLocators.calories).fill(data.calories);
    await this.page.getByTestId(ProductsLocators.protein).fill(data.protein);
    await this.page.getByTestId(ProductsLocators.fat).fill(data.fat);
    await this.page.getByTestId(ProductsLocators.carbs).fill(data.carbs);

    await this.setCheckbox(0, Boolean(data.isVegan));
    await this.setCheckbox(1, Boolean(data.isGlutenFree));
    await this.setCheckbox(2, Boolean(data.isSugarFree));
  }

  async setCheckbox(index: number, checked: boolean) {
    const ids = [ProductsLocators.vegan, ProductsLocators.glutenFree, ProductsLocators.sugarFree];
    const checkbox = this.page.getByTestId(ids[index]);
    if ((await checkbox.isChecked()) !== checked) {
      await checkbox.click();
    }
  }

  async uploadPhotos(count: number) {
    await this.page.getByTestId(ProductsLocators.photoInput).setInputFiles(
      Array.from({ length: count }, (_, index) => ({
        name: `photo-${index}.png`,
        mimeType: "image/png",
        buffer: Buffer.from("iVBORw0KGgo=", "base64"),
      })),
    );
  }

  async save() {
    await this.page.getByTestId(ProductsLocators.saveButton).click();
  }

  async expectProductCard(name: string) {
    await expect(this.page.getByTestId(ProductsLocators.detailTitle)).toHaveText(name);
    await expect(this.page.getByTestId(ProductsLocators.detail)).toContainText(name);
  }

  async search(value: string) {
    await this.page.getByTestId(ProductsLocators.search).fill(value);
  }

  async filterByCategory(label: string) {
    await this.page.getByTestId(ProductsLocators.categoryFilter).selectOption({ label });
  }

  async filterByFlag(index: number) {
    if (index !== 0) throw new Error("Only vegan filter is currently used by UI tests");
    await this.page.getByTestId(ProductsLocators.veganFilter).click();
  }

  async sortByCalories(order: "asc" | "desc") {
    await this.page.getByTestId(ProductsLocators.sortBy).selectOption("calories");
    await this.page.getByTestId(ProductsLocators.sortOrder).selectOption(order);
  }

  async deleteCard(name: string) {
    await this.cardByName(name).getByTestId(ProductsLocators.cardDelete).click();
  }

  async visibleTitleTexts() {
    return this.visibleCardTitles().allTextContents();
  }
}
