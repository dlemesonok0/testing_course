import re

import pytest
from playwright.sync_api import expect

from product_locators import ProductsLocators
from data import (
    product_categories,
    product_nutrition_cases,
    valid_product,
)
from conftest import create_product_by_api


@pytest.mark.parametrize(
    "test_case",
    product_nutrition_cases,
    ids=[case["id"] for case in product_nutrition_cases],
)
def test_product_validation_boundary(products_page, suffix, test_case):
    product = {
        **valid_product(f"{suffix}-{test_case['id']}"),
        **test_case["override"],
    }

    products_page.open_new_product()
    products_page.fill_product_form(product)
    products_page.save()

    if test_case["valid"]:
        products_page.expect_product_card(product["name"])
    else:
        expect(
            products_page.error_banner(),
            "invalid product data should stay on the form and show a UI error",
        ).to_be_visible()

        expect(products_page.page).to_have_url(re.compile(r"/products/new$"))


def test_limits_product_photos_by_boundary_values_5_and_6(products_page, suffix):
    products_page.open_new_product()
    products_page.fill_product_form(valid_product(f"{suffix}-five-photos"))
    products_page.upload_photos(5)
    products_page.save()
    products_page.expect_product_card(f"UI Product {suffix}-five-photos")

    products_page.open_new_product()
    products_page.fill_product_form(valid_product(f"{suffix}-six-photos"))
    products_page.upload_photos(6)
    products_page.save()

    expect(products_page.error_banner()).to_be_visible()
    expect(products_page.page).to_have_url(re.compile(r"/products/new$"))


def test_creates_product_with_valid_data_through_ui(products_page, suffix):
    product = valid_product(suffix)

    products_page.open_new_product()
    products_page.fill_product_form(product)
    products_page.save()

    products_page.expect_product_card(product["name"])

    expect(
        products_page.page.get_by_test_id(ProductsLocators.DETAIL)
    ).to_contain_text(product["composition"])

    expect(
        products_page.page.get_by_test_id(ProductsLocators.NUTRITION)
    ).to_contain_text(product["calories"])


def test_searches_filters_by_category_and_flags_and_sorts_products_by_calories(
    api,
    products_page,
    suffix,
):
    low = create_product_by_api(
        api,
        {
            "name": f"Apple {suffix}",
            "calories": "30",
            "category": product_categories["vegetables"],
            "is_vegan": True,
            "is_gluten_free": True,
            "is_sugar_free": True,
        },
    )

    high = create_product_by_api(
        api,
        {
            "name": f"Beef {suffix}",
            "calories": "250",
            "category": product_categories["meat"],
            "is_vegan": False,
            "is_gluten_free": True,
            "is_sugar_free": True,
        },
    )

    candy = create_product_by_api(
        api,
        {
            "name": f"Candy {suffix}",
            "calories": "400",
            "category": product_categories["frozen"],
            "is_vegan": True,
            "is_gluten_free": False,
            "is_sugar_free": False,
        },
    )

    products_page.open_list()

    products_page.search(low["name"])
    expect(products_page.card_by_name(low["name"])).to_be_visible()
    expect(products_page.card_by_name(high["name"])).not_to_be_visible()

    products_page.search("")
    products_page.filter_by_category(product_categories["meat"])
    expect(products_page.card_by_name(high["name"])).to_be_visible()
    expect(products_page.card_by_name(low["name"])).not_to_be_visible()

    products_page.page.get_by_test_id(
        ProductsLocators.CATEGORY_FILTER
    ).select_option("")

    products_page.filter_by_flag(0)
    expect(products_page.card_by_name(low["name"])).to_be_visible()
    expect(products_page.card_by_name(high["name"])).not_to_be_visible()

    products_page.sort_by_calories("desc")

    expect(products_page.card_by_name(candy["name"])).to_be_visible()
    products_page.wait_for_relevant_title_order([candy["name"], low["name"]])

    titles = products_page.visible_title_texts()
    relevant_titles = [
        title
        for title in titles
        if title in [low["name"], high["name"], candy["name"]]
    ]

    assert relevant_titles == [
        candy["name"],
        low["name"],
    ]
