import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.routers import dishes
from app.schemas import DishIngredientInput
from app.services.nutrition import calculate_draft


@pytest.fixture
def product_snapshot_factory():
    """Build product snapshots in the format consumed by calculate_draft."""

    def build_snapshot(**overrides):
        snapshot = {
            "calories": 100.0,
            "protein": 10.0,
            "fat": 5.0,
            "carbs": 20.0,
            "is_vegan": True,
            "is_gluten_free": True,
            "is_sugar_free": True,
        }
        snapshot.update(overrides)
        return snapshot

    return build_snapshot


class TestCalculateDraftEquivalencePartitioning:
    """Check representative equivalence classes for automatic nutrition calculation."""

    @pytest.mark.parametrize(
        ("build_ingredients", "expected"),
        [
            (
                lambda factory: [],
                {
                    "calories": 0.0,
                    "protein": 0.0,
                    "fat": 0.0,
                    "carbs": 0.0,
                    "allowed_flags": [],
                },
            ),
            (
                lambda factory: [
                    (
                        factory(
                            calories=120.0,
                            protein=18.0,
                            fat=4.0,
                            carbs=6.0,
                        ),
                        150.0,
                    )
                ],
                {
                    "calories": 180.0,
                    "protein": 27.0,
                    "fat": 6.0,
                    "carbs": 9.0,
                    "allowed_flags": ["vegan", "gluten_free", "sugar_free"],
                },
            ),
            (
                lambda factory: [
                    (
                        factory(
                            calories=80.0,
                            protein=3.0,
                            fat=1.0,
                            carbs=16.0,
                            is_sugar_free=False,
                        ),
                        200.0,
                    ),
                    (
                        factory(
                            calories=250.0,
                            protein=20.0,
                            fat=15.0,
                            carbs=5.0,
                            is_gluten_free=False,
                        ),
                        50.0,
                    ),
                ],
                {
                    "calories": 285.0,
                    "protein": 16.0,
                    "fat": 9.5,
                    "carbs": 34.5,
                    "allowed_flags": ["vegan"],
                },
            ),
        ],
        ids=[
            "empty-ingredient-list",
            "single-ingredient-with-all-flags",
            "multiple-ingredients-with-mixed-diet-flags",
        ],
    )
    def test_calculate_draft_returns_expected_totals_for_equivalence_classes(
        self,
        product_snapshot_factory,
        build_ingredients,
        expected,
    ):
        """Use equivalence partitioning for empty, single-item and mixed-item recipes."""

        ingredients = build_ingredients(product_snapshot_factory)

        assert calculate_draft(ingredients) == expected


class TestCalculateDraftBoundaryValues:
    """Check boundary values near the most meaningful calculation thresholds."""

    @pytest.mark.parametrize(
        ("quantity_grams", "expected_calories"),
        [
            pytest.param(99.99, 123.44, id="just-below-reference-100g"),
            pytest.param(100.0, 123.45, id="exact-reference-100g"),
            pytest.param(100.01, 123.46, id="just-above-reference-100g"),
        ],
    )
    def test_calculate_draft_scales_calories_around_the_100_gram_reference(
        self,
        product_snapshot_factory,
        quantity_grams,
        expected_calories,
    ):
        """Use boundary value analysis around the 100 g nutrition reference point."""

        product = product_snapshot_factory(calories=123.45, protein=0.0, fat=0.0, carbs=0.0)

        result = calculate_draft([(product, quantity_grams)])

        assert result["calories"] == expected_calories

    @pytest.mark.parametrize(
        ("quantity_grams", "should_pass"),
        [
            pytest.param(-0.01, False, id="negative-quantity"),
            pytest.param(0.0, False, id="zero-quantity"),
            pytest.param(0.01, True, id="minimum-positive-quantity"),
        ],
    )
    def test_dish_ingredient_input_validates_quantity_boundaries(self, quantity_grams, should_pass):
        """Use boundary value analysis for the lower quantity limit accepted by the API schema."""

        if should_pass:
            ingredient = DishIngredientInput(product_id=1, quantity_grams=quantity_grams)
            assert ingredient.quantity_grams == quantity_grams
            return

        with pytest.raises(ValidationError):
            DishIngredientInput(product_id=1, quantity_grams=quantity_grams)

    @pytest.mark.parametrize(
        ("product_id", "should_pass"),
        [
            pytest.param(0, False, id="zero-product-id"),
            pytest.param(1, True, id="minimum-valid-product-id"),
        ],
    )
    def test_dish_ingredient_input_validates_product_id_boundaries(self, product_id, should_pass):
        """Check the lower product identifier boundary used by ingredient references."""

        if should_pass:
            ingredient = DishIngredientInput(product_id=product_id, quantity_grams=1.0)
            assert ingredient.product_id == product_id
            return

        with pytest.raises(ValidationError):
            DishIngredientInput(product_id=product_id, quantity_grams=1.0)


def test_nutrition_draft_endpoint_delegates_to_the_calculation_service(monkeypatch):
    """Stub collaborators to keep the endpoint test isolated from the database and service internals."""

    captured: dict[str, object] = {}
    fake_product = SimpleNamespace(
        calories=80.0,
        protein=3.0,
        fat=1.0,
        carbs=16.0,
        is_vegan=True,
        is_gluten_free=True,
        is_sugar_free=False,
    )
    expected_draft = {
        "calories": 40.0,
        "protein": 1.5,
        "fat": 0.5,
        "carbs": 8.0,
        "allowed_flags": ["vegan", "gluten_free"],
    }

    def fake_load_products_map(db, ingredients):
        captured["parsed_ingredients"] = ingredients
        return {1: fake_product}

    def fake_calculate_draft(ingredients):
        captured["calculator_input"] = ingredients
        return expected_draft

    monkeypatch.setattr(dishes, "load_products_map", fake_load_products_map)
    monkeypatch.setattr(dishes, "calculate_draft", fake_calculate_draft)

    result = dishes.nutrition_draft(
        ingredients=json.dumps([{"product_id": 1, "quantity_grams": 50.0}]),
        db=object(),
    )

    assert result == expected_draft
    assert len(captured["parsed_ingredients"]) == 1
    parsed_ingredient = captured["parsed_ingredients"][0]
    assert parsed_ingredient.product_id == 1
    assert parsed_ingredient.quantity_grams == 50.0
    assert captured["calculator_input"] == [
        (
            {
                "calories": 80.0,
                "protein": 3.0,
                "fat": 1.0,
                "carbs": 16.0,
                "is_vegan": True,
                "is_gluten_free": True,
                "is_sugar_free": False,
            },
            50.0,
        )
    ]
