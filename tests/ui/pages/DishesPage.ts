import { expect, type Page } from "@playwright/test";

import { DishesLocators } from "../locators/DishesLocators";

export type DishFormData = {
  name: string;
  category?: string;
  portionSize: string;
  calories?: string;
  protein?: string;
  fat?: string;
  carbs?: string;
  ingredientName: string;
  ingredientQuantity: string;
  isVegan?: boolean;
};

export class DishesPage {
  constructor(readonly page: Page) {}

  async openList() {
    await this.page.goto("/dishes");
  }

  async openNewDish() {
    await this.page.goto("/dishes/new");
  }

  errorBanner() {
    return this.page.getByTestId(DishesLocators.errorBanner);
  }

  draftPanel() {
    return this.page.getByTestId(DishesLocators.draftPanel);
  }

  async fillDishForm(data: DishFormData) {
    await this.page.getByTestId(DishesLocators.name).fill(data.name);
    if (data.category === "") {
      await this.page.getByTestId(DishesLocators.category).selectOption("");
    } else if (data.category) {
      await this.page.getByTestId(DishesLocators.category).selectOption({ label: data.category });
    }

    await this.page.getByTestId(DishesLocators.portionSize).fill(data.portionSize);

    await this.page.getByTestId(DishesLocators.ingredientProduct(0)).selectOption({ label: data.ingredientName });
    await this.page.getByTestId(DishesLocators.ingredientQuantity(0)).fill(data.ingredientQuantity);

    if (
      data.calories !== undefined ||
      data.protein !== undefined ||
      data.fat !== undefined ||
      data.carbs !== undefined
    ) {
      await this.draftPanel().waitFor({ state: "visible", timeout: 3_000 }).catch(() => undefined);
      if (data.calories !== undefined) await this.page.getByTestId(DishesLocators.calories).fill(data.calories);
      if (data.protein !== undefined) await this.page.getByTestId(DishesLocators.protein).fill(data.protein);
      if (data.fat !== undefined) await this.page.getByTestId(DishesLocators.fat).fill(data.fat);
      if (data.carbs !== undefined) await this.page.getByTestId(DishesLocators.carbs).fill(data.carbs);
    }

    if (data.isVegan) {
      const vegan = this.page.getByTestId(DishesLocators.vegan);
      if (await vegan.isEnabled()) await vegan.check();
    }
  }

  async save() {
    await this.page.getByTestId(DishesLocators.saveButton).click();
  }

  async expectDishCard(name: string) {
    await expect(this.page.getByTestId(DishesLocators.detailTitle)).toHaveText(name);
    await expect(this.page.getByTestId(DishesLocators.detail)).toContainText(name);
  }

  async expectDraftVisible() {
    await expect(this.draftPanel()).toBeVisible();
  }

  async expectVeganDisabled() {
    await expect(this.page.getByTestId(DishesLocators.vegan)).toBeDisabled();
  }
}
