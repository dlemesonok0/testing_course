API_BASE = "http://127.0.0.1:8001"

product_categories = {
    "frozen": "Замороженный",
    "meat": "Мясной",
    "vegetables": "Овощи",
}

dish_categories = {
    "second": "Второе",
    "salad": "Салат",
}

cooking_states = {
    "ready": "Готовый к употреблению",
    "needs_cooking": "Требует приготовления",
}


def valid_product(suffix: str) -> dict:
    return {
        "name": f"UI Product {suffix}",
        "composition": "Water, salt",
        "category": product_categories["vegetables"],
        "cookingState": cooking_states["ready"],
        "calories": "42",
        "protein": "2",
        "fat": "1",
        "carbs": "5",
        "isVegan": True,
        "isGlutenFree": True,
        "isSugarFree": True,
    }


product_nutrition_cases = [
    {"id": "invalid-name-length-1", "override": {"name": "A"}, "valid": False},
    {"id": "invalid-blank-name", "override": {"name": "    "}, "valid": False},
    {"id": "valid-name-length-2", "override": {"name": "AB"}, "valid": True},
    {"id": "invalid-negative-calories", "override": {"calories": "-0.01"}, "valid": False},
    {"id": "valid-zero-calories", "override": {"calories": "0"}, "valid": True},
    {"id": "valid-positive-calories-boundary", "override": {"calories": "0.01"}, "valid": True},
    {"id": "valid-bju-sum-100", "override": {"protein": "40", "fat": "30", "carbs": "30"}, "valid": True},
    {"id": "invalid-bju-sum-100-01", "override": {"protein": "40", "fat": "30", "carbs": "30.01"}, "valid": False},
    {"id": "invalid-single-protein-100-01", "override": {"protein": "100.01", "fat": "0", "carbs": "0"}, "valid": False},
    {"id": "invalid-single-fat-100-01", "override": {"protein": "0", "fat": "100.01", "carbs": "0"}, "valid": False},
    {"id": "invalid-single-carbs-100-01", "override": {"protein": "0", "fat": "0", "carbs": "100.01"}, "valid": False},
    {"id": "invalid-negative-protein", "override": {"protein": "-0.01"}, "valid": False},
    {"id": "invalid-negative-fat", "override": {"fat": "-0.01"}, "valid": False},
    {"id": "invalid-negative-carbs", "override": {"carbs": "-0.01"}, "valid": False},
]


dish_boundary_cases = [
    {"id": "invalid-portion-zero", "portionSize": "0", "quantity": "100", "valid": False},
    {"id": "valid-portion-001", "portionSize": "0.01", "quantity": "0.01", "valid": True},
    {"id": "invalid-ingredient-zero", "portionSize": "250", "quantity": "0", "valid": False},
    {"id": "valid-ingredient-001", "portionSize": "250", "quantity": "0.01", "valid": True},
    {"id": "invalid-name-length-1", "name": "A", "portionSize": "250", "quantity": "100", "valid": False},
    {"id": "invalid-blank-name", "name": "    ", "portionSize": "250", "quantity": "100", "valid": False},
    {"id": "valid-name-length-2", "name": "Ok", "portionSize": "250", "quantity": "100", "valid": True},
    {"id": "valid-macro-sum-equals-portion", "portionSize": "100", "quantity": "100", "protein": "40", "fat": "30", "carbs": "30", "valid": True},
    {"id": "invalid-macro-sum-above-portion", "portionSize": "100", "quantity": "100", "protein": "40", "fat": "30", "carbs": "30.01", "valid": False},
    {"id": "invalid-negative-calories", "portionSize": "250", "quantity": "100", "calories": "-0.01", "valid": False},
    {"id": "invalid-negative-protein", "portionSize": "250", "quantity": "100", "protein": "-0.01", "valid": False},
    {"id": "invalid-negative-fat", "portionSize": "250", "quantity": "100", "fat": "-0.01", "valid": False},
    {"id": "invalid-negative-carbs", "portionSize": "250", "quantity": "100", "carbs": "-0.01", "valid": False},
]


dish_category_macro_cases = [
    {"id": "dessert", "macro": "!десерт", "expectedCategory": "Десерт"},
    {"id": "first", "macro": "!первое", "expectedCategory": "Первое"},
    {"id": "second", "macro": "!второе", "expectedCategory": "Второе"},
    {"id": "drink", "macro": "!напиток", "expectedCategory": "Напиток"},
    {"id": "salad", "macro": "!салат", "expectedCategory": "Салат"},
    {"id": "soup", "macro": "!суп", "expectedCategory": "Суп"},
    {"id": "snack", "macro": "!перекус", "expectedCategory": "Перекус"},
]
