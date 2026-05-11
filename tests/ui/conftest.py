import time

import pytest
from playwright.sync_api import APIRequestContext, Page

from dish_page import DishesPage
from product_page import ProductsPage
from data import API_BASE, cooking_states, product_categories


UI_BASE = "http://localhost:5173"


def create_product_by_api(
    api: APIRequestContext,
    overrides: dict[str, str | bool] | None = None,
):
    payload = {
        "name": f"API Product {int(time.time() * 1000)}",
        "calories": "100",
        "protein": "10",
        "fat": "5",
        "carbs": "20",
        "composition": "API seed",
        "category": product_categories["vegetables"],
        "cooking_state": cooking_states["ready"],
        "is_vegan": "true",
        "is_gluten_free": "true",
        "is_sugar_free": "true",
    }

    if overrides:
        payload.update({k: str(v) for k, v in overrides.items()})

    response = api.post(f"{API_BASE}/products", multipart=payload)

    assert response.ok, response.text()

    return response.json()


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "base_url": UI_BASE,
    }


@pytest.fixture
def api(playwright):
    context = playwright.request.new_context()
    yield context
    context.dispose()


@pytest.fixture
def suffix(request):
    return f"{int(time.time() * 1000)}-{getattr(request.node, 'rep_call', 0)}"


@pytest.fixture
def products_page(page: Page):
    return ProductsPage(page)


@pytest.fixture
def dishes_page(page: Page):
    return DishesPage(page)


@pytest.fixture(autouse=True)
def before_each(api: APIRequestContext, page: Page):
    health = api.get(f"{API_BASE}/health")

    assert health.ok, (
        "preprod backend healthcheck should be available"
    )

    page.goto("/")