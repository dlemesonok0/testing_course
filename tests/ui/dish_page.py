from typing import TypedDict

from playwright.sync_api import Page, expect

from dish_locators import DishesLocators


class DishFormData(TypedDict, total=False):
    name: str
    category: str
    portionSize: str
    calories: str
    protein: str
    fat: str
    carbs: str
    ingredientName: str
    ingredientQuantity: str
    isVegan: bool


class DishesPage:
    def __init__(self, page: Page):
        self.page = page

    def open_list(self):
        self.page.goto("/dishes")

    def open_new_dish(self):
        self.page.goto("/dishes/new")

    def error_banner(self):
        return self.page.get_by_test_id(DishesLocators.ERROR_BANNER)

    def draft_panel(self):
        return self.page.get_by_test_id(DishesLocators.DRAFT_PANEL)

    def fill_dish_form(self, data: DishFormData):
        self.page.get_by_test_id(DishesLocators.NAME).fill(data["name"])

        category = data.get("category")
        if category == "":
            self.page.get_by_test_id(DishesLocators.CATEGORY).select_option("")
        elif category:
            self.page.get_by_test_id(DishesLocators.CATEGORY).select_option(label=category)

        self.page.get_by_test_id(DishesLocators.PORTION_SIZE).fill(data["portionSize"])

        self.page.get_by_test_id(
            DishesLocators.ingredient_product(0)
        ).select_option(label=data["ingredientName"])

        self.page.get_by_test_id(
            DishesLocators.ingredient_quantity(0)
        ).fill(data["ingredientQuantity"])

        has_manual_nutrition = any(
            key in data
            for key in ["calories", "protein", "fat", "carbs"]
        )

        if has_manual_nutrition:
            try:
                self.draft_panel().wait_for(state="visible", timeout=3000)
            except Exception:
                pass

            if "calories" in data:
                self.page.get_by_test_id(DishesLocators.CALORIES).fill(data["calories"])

            if "protein" in data:
                self.page.get_by_test_id(DishesLocators.PROTEIN).fill(data["protein"])

            if "fat" in data:
                self.page.get_by_test_id(DishesLocators.FAT).fill(data["fat"])

            if "carbs" in data:
                self.page.get_by_test_id(DishesLocators.CARBS).fill(data["carbs"])

        if data.get("isVegan"):
            vegan = self.page.get_by_test_id(DishesLocators.VEGAN)
            if vegan.is_enabled():
                vegan.check()

    def save(self):
        self.page.get_by_test_id(DishesLocators.SAVE_BUTTON).click()

    def expect_dish_card(self, name: str):
        expect(
            self.page.get_by_test_id(DishesLocators.DETAIL_TITLE)
        ).to_have_text(name)

        expect(
            self.page.get_by_test_id(DishesLocators.DETAIL)
        ).to_contain_text(name)

    def expect_draft_visible(self):
        expect(self.draft_panel()).to_be_visible()

    def expect_vegan_disabled(self):
        expect(
            self.page.get_by_test_id(DishesLocators.VEGAN)
        ).to_be_disabled()