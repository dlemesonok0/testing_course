import pytest
from types import SimpleNamespace

from app.schemas import DISH_CATEGORIES


@pytest.fixture
def nutrition_product_factory():
    """Build product nutrition snapshots used by the automatic dish calculation service."""

    def build_product(**overrides):
        product = {
            "calories": 100.0,
            "protein": 10.0,
            "fat": 5.0,
            "carbs": 20.0,
            "is_vegan": True,
            "is_gluten_free": True,
            "is_sugar_free": True,
        }
        product.update(overrides)
        return product

    return build_product


@pytest.fixture
def nutrition_product_object_factory():
    """Build product-like objects used by router tests before nutrition snapshots are created."""

    def build_product(**overrides):
        product = {
            "calories": 100.0,
            "protein": 10.0,
            "fat": 5.0,
            "carbs": 20.0,
            "is_vegan": True,
            "is_gluten_free": True,
            "is_sugar_free": True,
        }
        product.update(overrides)
        return SimpleNamespace(**product)

    return build_product


@pytest.fixture
def dish_payload_factory():
    """Build raw dish payloads for validating automatic nutrition input boundaries."""

    def build_payload(**overrides):
        payload = {
            "name": "Test dish",
            "description": None,
            "category": DISH_CATEGORIES[0],
            "portion_size_grams": 100.0,
            "calories": 150.0,
            "protein": 30.0,
            "fat": 20.0,
            "carbs": 50.0,
            "is_vegan": False,
            "is_gluten_free": False,
            "is_sugar_free": False,
            "ingredients": [{"product_id": 1, "quantity_grams": 100.0}],
        }
        payload.update(overrides)
        return payload

    return build_payload
