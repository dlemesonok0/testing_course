class DishesLocators:
    DETAIL_TITLE = "dish-card-title"
    DETAIL = "dish-card"
    NUTRITION = "dish-nutrition"
    INGREDIENTS = "dish-ingredients"
    ERROR_BANNER = "error-banner"
    DRAFT_PANEL = "dish-nutrition-draft"

    NAME = "dish-name"
    CATEGORY = "dish-category"
    PORTION_SIZE = "dish-portion-size"

    CALORIES = "dish-calories"
    PROTEIN = "dish-protein"
    FAT = "dish-fat"
    CARBS = "dish-carbs"

    VEGAN = "dish-is_vegan"

    SAVE_BUTTON = "dish-save"

    @staticmethod
    def ingredient_product(index: int) -> str:
        return f"dish-ingredient-product-{index}"

    @staticmethod
    def ingredient_quantity(index: int) -> str:
        return f"dish-ingredient-quantity-{index}"