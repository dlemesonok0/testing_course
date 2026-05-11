import re

import pytest
from playwright.sync_api import expect

from data import (
    dish_boundary_cases,
    dish_categories,
    dish_category_macro_cases,
)
from conftest import create_product_by_api


def test_creates_dish_from_existing_product_and_applies_nutrition_draft(
    api,
    dishes_page,
    suffix,
):
    product = create_product_by_api(
        api,
        {
            "name": f"Dish seed {suffix}",
            "calories": "120",
            "protein": "10",
            "fat": "4",
            "carbs": "12",
            "is_vegan": True,
            "is_gluten_free": True,
            "is_sugar_free": True,
        },
    )

    dish_name = f"UI Dish {suffix}"

    dishes_page.open_new_dish()
    dishes_page.fill_dish_form(
        {
            "name": dish_name,
            "category": dish_categories["second"],
            "portionSize": "250",
            "ingredientName": product["name"],
            "ingredientQuantity": "100",
        }
    )

    dishes_page.expect_draft_visible()

    expect(
        dishes_page.page.get_by_test_id("dish-calories")
    ).to_have_value("120")

    dishes_page.save()
    dishes_page.expect_dish_card(dish_name)

    expect(
        dishes_page.page.get_by_test_id("dish-ingredients")
    ).to_contain_text(product["name"])


def test_disables_vegan_dish_flag_when_ingredient_is_not_vegan(
    api,
    dishes_page,
    suffix,
):
    product = create_product_by_api(
        api,
        {
            "name": f"Non vegan seed {suffix}",
            "is_vegan": False,
            "is_gluten_free": True,
            "is_sugar_free": True,
        },
    )

    dishes_page.open_new_dish()
    dishes_page.fill_dish_form(
        {
            "name": f"Flag Dish {suffix}",
            "category": dish_categories["second"],
            "portionSize": "250",
            "ingredientName": product["name"],
            "ingredientQuantity": "100",
        }
    )

    dishes_page.expect_draft_visible()
    dishes_page.expect_vegan_disabled()


def test_does_not_delete_product_that_is_used_in_dish(
    api,
    products_page,
    dishes_page,
    suffix,
):
    product = create_product_by_api(
        api,
        {"name": f"Protected Product {suffix}"},
    )

    dishes_page.open_new_dish()
    dishes_page.fill_dish_form(
        {
            "name": f"Protected Dish {suffix}",
            "category": dish_categories["second"],
            "portionSize": "250",
            "ingredientName": product["name"],
            "ingredientQuantity": "100",
        }
    )

    dishes_page.save()
    dishes_page.expect_dish_card(f"Protected Dish {suffix}")

    products_page.open_list()

    expect(products_page.card_by_name(product["name"])).to_be_visible()

    products_page.delete_card(product["name"])

    expect(products_page.error_banner()).to_be_visible()
    expect(products_page.card_by_name(product["name"])).to_be_visible()


@pytest.mark.parametrize(
    "test_case",
    dish_boundary_cases,
    ids=[case["id"] for case in dish_boundary_cases],
)
def test_dish_boundary_validation(api, dishes_page, suffix, test_case):
    product = create_product_by_api(
        api,
        {"name": f"Boundary seed {suffix}-{test_case['id']}"},
    )

    dish_name = test_case.get(
        "name",
        f"Boundary Dish {suffix}-{test_case['id']}",
    )

    dishes_page.open_new_dish()
    dishes_page.fill_dish_form(
        {
            "name": dish_name,
            "category": dish_categories["salad"],
            "portionSize": test_case["portionSize"],
            "calories": test_case.get("calories", "0"),
            "protein": test_case.get("protein", "0"),
            "fat": test_case.get("fat", "0"),
            "carbs": test_case.get("carbs", "0"),
            "ingredientName": product["name"],
            "ingredientQuantity": test_case["quantity"],
        }
    )

    dishes_page.save()

    if test_case["valid"]:
        dishes_page.expect_dish_card(dish_name)
    else:
        expect(
            dishes_page.error_banner(),
            "invalid dish boundary should show a UI validation error",
        ).to_be_visible()

        expect(dishes_page.page).to_have_url(re.compile(r"/dishes/new$"))


@pytest.mark.parametrize(
    "test_case",
    dish_category_macro_cases,
    ids=[case["id"] for case in dish_category_macro_cases],
)
def test_dish_category_macro(api, dishes_page, suffix, test_case):
    product = create_product_by_api(
        api,
        {"name": f"Macro seed {suffix}-{test_case['id']}"},
    )

    dish_name = f"Macro Dish {suffix}-{test_case['id']}"

    dishes_page.open_new_dish()
    dishes_page.fill_dish_form(
        {
            "name": f"{test_case['macro']} {dish_name}",
            "category": "",
            "portionSize": "250",
            "ingredientName": product["name"],
            "ingredientQuantity": "100",
        }
    )

    dishes_page.save()
    dishes_page.expect_dish_card(dish_name)

    expect(
        dishes_page.page.get_by_test_id("dish-card")
    ).to_contain_text(test_case["expectedCategory"])


def test_explicit_category_overrides_category_macro_in_dish_name(
    api,
    dishes_page,
    suffix,
):
    product = create_product_by_api(
        api,
        {"name": f"Macro explicit seed {suffix}"},
    )

    dish_name = f"Explicit Macro Dish {suffix}"

    dishes_page.open_new_dish()
    dishes_page.fill_dish_form(
        {
            "name": f"!десерт {dish_name}",
            "category": dish_categories["second"],
            "portionSize": "250",
            "ingredientName": product["name"],
            "ingredientQuantity": "100",
        }
    )

    dishes_page.save()
    dishes_page.expect_dish_card(dish_name)

    expect(
        dishes_page.page.get_by_test_id("dish-card")
    ).to_contain_text(dish_categories["second"])