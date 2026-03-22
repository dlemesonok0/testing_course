def calculate_draft(ingredients: list[tuple[dict, float]]) -> dict:
    totals = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
    if not ingredients:
        return {**totals, "allowed_flags": []}

    vegan = True
    gluten_free = True
    sugar_free = True

    for product, quantity_grams in ingredients:
        multiplier = quantity_grams / 100
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
