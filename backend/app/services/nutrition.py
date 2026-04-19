def calculate_draft(ingredients: list[tuple[dict, float]], portion_size_grams: float | None = None) -> dict:
    totals = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
    if not ingredients:
        return {**totals, "allowed_flags": []}

    vegan = True
    gluten_free = True
    sugar_free = True
    total_ingredient_grams = sum(quantity_grams for _, quantity_grams in ingredients)
    portion_multiplier = 1.0
    if portion_size_grams is not None and total_ingredient_grams > 0:
        portion_multiplier = portion_size_grams / total_ingredient_grams

    for product, quantity_grams in ingredients:
        quantity_in_portion = quantity_grams * portion_multiplier
        multiplier = quantity_in_portion / 100
        totals["calories"] += product["calories"] * multiplier
        totals["protein"] += product["protein"] * multiplier
        totals["fat"] += product["fat"] * multiplier
        totals["carbs"] += product["carbs"] * multiplier
        vegan = vegan and bool(product["is_vegan"])
        gluten_free = gluten_free and bool(product["is_gluten_free"])
        sugar_free = sugar_free and bool(product["is_sugar_free"])

    allowed_flags = []
    if vegan:
        allowed_flags.append("vegan")
    if gluten_free:
        allowed_flags.append("gluten_free")
    if sugar_free:
        allowed_flags.append("sugar_free")

    return {
        "calories": round(totals["calories"], 2),
        "protein": round(totals["protein"], 2),
        "fat": round(totals["fat"], 2),
        "carbs": round(totals["carbs"], 2),
        "allowed_flags": allowed_flags,
    }
