from typing import TypedDict

from playwright.sync_api import Page, Locator, expect

from product_locators import ProductsLocators

PNG_1X1 = bytes.fromhex(
    "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
    "0000000D49444154789C6360000002000100FFFF03000006000557BFAB0D000000"
    "0049454E44AE426082"
)


class ProductFormData(TypedDict, total=False):
    name: str
    composition: str
    category: str
    cookingState: str
    calories: str
    protein: str
    fat: str
    carbs: str
    isVegan: bool
    isGlutenFree: bool
    isSugarFree: bool


class ProductsPage:
    def __init__(self, page: Page):
        self.page = page

    def open_list(self):
        self.page.goto("/")

    def open_new_product(self):
        self.page.goto("/products/new")

    def cards(self) -> Locator:
        return self.page.get_by_test_id(ProductsLocators.CARD)

    def visible_card_titles(self) -> Locator:
        return self.page.get_by_test_id(ProductsLocators.CARD_TITLE)

    def card_by_name(self, name: str) -> Locator:
        return self.cards().filter(
            has=self.page.get_by_test_id(
                ProductsLocators.CARD_TITLE
            ).filter(has_text=name)
        )

    def error_banner(self) -> Locator:
        return self.page.get_by_test_id(ProductsLocators.ERROR_BANNER)

    def fill_product_form(self, data: ProductFormData):
        self.page.get_by_test_id(ProductsLocators.NAME).fill(data["name"])
        self.page.get_by_test_id(ProductsLocators.COMPOSITION).fill(
            data.get("composition", "")
        )

        if data.get("category"):
            self.page.get_by_test_id(ProductsLocators.CATEGORY).select_option(
                label=data["category"]
            )

        if data.get("cookingState"):
            self.page.get_by_test_id(ProductsLocators.COOKING_STATE).select_option(
                label=data["cookingState"]
            )

        self.page.get_by_test_id(ProductsLocators.CALORIES).fill(data["calories"])
        self.page.get_by_test_id(ProductsLocators.PROTEIN).fill(data["protein"])
        self.page.get_by_test_id(ProductsLocators.FAT).fill(data["fat"])
        self.page.get_by_test_id(ProductsLocators.CARBS).fill(data["carbs"])

        self.set_checkbox(0, bool(data.get("isVegan")))
        self.set_checkbox(1, bool(data.get("isGlutenFree")))
        self.set_checkbox(2, bool(data.get("isSugarFree")))

    def set_checkbox(self, index: int, checked: bool):
        ids = [
            ProductsLocators.VEGAN,
            ProductsLocators.GLUTEN_FREE,
            ProductsLocators.SUGAR_FREE,
        ]

        checkbox = self.page.get_by_test_id(ids[index])

        if checkbox.is_checked() != checked:
            checkbox.click()

    def upload_photos(self, count: int):
        self.page.get_by_test_id(ProductsLocators.PHOTO_INPUT).set_input_files(
            [
                {
                    "name": f"photo-{index}.png",
                    "mimeType": "image/png",
                    "buffer": PNG_1X1,
                }
                for index in range(count)
            ]
        )

    def save(self):
        self.page.get_by_test_id(ProductsLocators.SAVE_BUTTON).click()

    def expect_product_card(self, name: str):
        expect(
            self.page.get_by_test_id(ProductsLocators.DETAIL_TITLE)
        ).to_have_text(name)

        expect(
            self.page.get_by_test_id(ProductsLocators.DETAIL)
        ).to_contain_text(name)

    def search(self, value: str):
        self.page.get_by_test_id(ProductsLocators.SEARCH).fill(value)

    def filter_by_category(self, label: str):
        self.page.get_by_test_id(
            ProductsLocators.CATEGORY_FILTER
        ).select_option(label=label)

    def filter_by_flag(self, index: int):
        if index != 0:
            raise ValueError("Only vegan filter is currently used by UI tests")

        self.page.get_by_test_id(ProductsLocators.VEGAN_FILTER).click()

    def sort_by_calories(self, order: str):
        if order not in ("asc", "desc"):
            raise ValueError("order must be 'asc' or 'desc'")

        self.page.get_by_test_id(ProductsLocators.SORT_BY).select_option("calories")
        self.page.get_by_test_id(ProductsLocators.SORT_ORDER).select_option(order)

    def delete_card(self, name: str):
        self.card_by_name(name).get_by_test_id(
            ProductsLocators.CARD_DELETE
        ).click()

    def visible_title_texts(self) -> list[str]:
        return self.visible_card_titles().all_text_contents()

    def wait_for_relevant_title_order(self, expected_titles: list[str]):
        self.page.wait_for_function(
            """([testId, expected]) => {
                const titles = Array.from(
                    document.querySelectorAll(`[data-testid="${testId}"]`)
                ).map((item) => item.textContent || "");
                const relevant = titles.filter((title) => expected.includes(title));
                return JSON.stringify(relevant) === JSON.stringify(expected);
            }""",
            arg=[ProductsLocators.CARD_TITLE, expected_titles],
        )
