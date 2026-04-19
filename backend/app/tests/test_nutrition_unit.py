import json
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.routers import dishes
from app.schemas import DishCreate
from app.services.nutrition import calculate_draft


class TestAutomaticDishNutrition:
    """Unit tests for automatic dish nutrition calculation."""

    @pytest.mark.parametrize(
        ("build_ingredients", "expected"),
        [
            pytest.param(
                lambda product: [],
                {
                    "calories": 0.0,
                    "protein": 0.0,
                    "fat": 0.0,
                    "carbs": 0.0,
                    "allowed_flags": [],
                },
                id="empty-dish",
            ),
            pytest.param(
                lambda product: [
                    (
                        product(
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
                id="single-product-dish",
            ),
            pytest.param(
                lambda product: [
                    (
                        product(
                            calories=80.0,
                            protein=3.0,
                            fat=1.0,
                            carbs=16.0,
                            is_sugar_free=False,
                        ),
                        200.0,
                    ),
                    (
                        product(
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
                id="multi-product-dish",
            ),
        ],
    )
    def test_calculates_expected_nutrition_for_equivalence_classes(
        self,
        nutrition_product_factory,
        build_ingredients,
        expected,
    ):
        """Cover empty, single-product and multi-product dish classes using equivalence partitioning."""

        ingredients = build_ingredients(nutrition_product_factory)

        assert calculate_draft(ingredients) == expected

    @pytest.mark.parametrize(
        ("quantity_grams", "expected_calories"),
        [
            pytest.param(99.99, 123.44, id="just-below-100g-reference"),
            pytest.param(100.0, 123.45, id="exact-100g-reference"),
            pytest.param(100.01, 123.46, id="just-above-100g-reference"),
        ],
    )
    def test_calories_scale_around_100_gram_reference_boundary(
        self,
        nutrition_product_factory,
        quantity_grams,
        expected_calories,
    ):
        """Check the boundary around the product nutrition reference value of 100 g."""

        product = nutrition_product_factory(calories=123.45, protein=0.0, fat=0.0, carbs=0.0)

        result = calculate_draft([(product, quantity_grams)])

        assert result["calories"] == expected_calories

    @pytest.mark.parametrize(
        ("portion_size_grams", "expected_calories"),
        [
            pytest.param(99.9, 149.85, id="just-below-100g-portion"),
            pytest.param(100.0, 150.0, id="exact-100g-portion"),
            pytest.param(100.1, 150.15, id="just-above-100g-portion"),
            pytest.param(300.0, 450.0, id="larger-serving-portion"),
        ],
    )
    def test_recalculates_nutrition_to_requested_portion_size(
        self,
        nutrition_product_factory,
        portion_size_grams,
        expected_calories,
    ):
        """Check that dish calories are calculated for the selected serving size, not per 100 g of dish."""

        ingredients = [
            (
                nutrition_product_factory(
                    calories=100.0,
                    protein=10.0,
                    fat=5.0,
                    carbs=20.0,
                ),
                50.0,
            ),
            (
                nutrition_product_factory(
                    calories=200.0,
                    protein=20.0,
                    fat=10.0,
                    carbs=40.0,
                ),
                50.0,
            ),
        ]

        result = calculate_draft(ingredients, portion_size_grams=portion_size_grams)

        assert result["calories"] == expected_calories


class TestNutritionDraftEndpointWithMocks:
    """Unit tests for endpoint delegation using mocked collaborators."""

    def test_nutrition_draft_endpoint_delegates_to_calculation_service_with_portion(
        self,
        monkeypatch,
        nutrition_product_object_factory,
    ):
        """Mock endpoint collaborators and verify that serving size is forwarded to the calculator."""

        expected_draft = {
            "calories": 375.0,
            "protein": 37.5,
            "fat": 18.75,
            "carbs": 75.0,
            "allowed_flags": ["vegan", "gluten_free", "sugar_free"],
        }
        product = nutrition_product_object_factory(
            calories=150.0,
            protein=15.0,
            fat=7.5,
            carbs=30.0,
        )
        load_products_map_mock = Mock(return_value={7: product})
        calculate_draft_mock = Mock(return_value=expected_draft)
        monkeypatch.setattr(dishes, "load_products_map", load_products_map_mock)
        monkeypatch.setattr(dishes, "calculate_draft", calculate_draft_mock)

        result = dishes.nutrition_draft(
            ingredients=json.dumps([{"product_id": 7, "quantity_grams": 100.0}]),
            portion_size_grams=250.0,
            db=object(),
        )

        assert result == expected_draft
        load_products_map_mock.assert_called_once()
        _, parsed_ingredients = load_products_map_mock.call_args.args
        assert parsed_ingredients[0].product_id == 7
        assert parsed_ingredients[0].quantity_grams == 100.0
        calculate_draft_mock.assert_called_once_with(
            [
                (
                    {
                        "calories": 150.0,
                        "protein": 15.0,
                        "fat": 7.5,
                        "carbs": 30.0,
                        "is_vegan": True,
                        "is_gluten_free": True,
                        "is_sugar_free": True,
                    },
                    100.0,
                )
            ],
            250.0,
        )

    def test_nutrition_draft_endpoint_delegates_to_calculation_service_without_portion(
        self,
        monkeypatch,
        nutrition_product_object_factory,
    ):
        """Mock endpoint collaborators and verify that missing serving size is passed as None."""

        expected_draft = {
            "calories": 40.0,
            "protein": 1.5,
            "fat": 0.5,
            "carbs": 8.0,
            "allowed_flags": ["vegan", "gluten_free"],
        }
        product = nutrition_product_object_factory(
            calories=80.0,
            protein=3.0,
            fat=1.0,
            carbs=16.0,
            is_sugar_free=False,
        )
        load_products_map_mock = Mock(return_value={3: product})
        calculate_draft_mock = Mock(return_value=expected_draft)
        monkeypatch.setattr(dishes, "load_products_map", load_products_map_mock)
        monkeypatch.setattr(dishes, "calculate_draft", calculate_draft_mock)

        result = dishes.nutrition_draft(
            ingredients=json.dumps([{"product_id": 3, "quantity_grams": 50.0}]),
            portion_size_grams=None,
            db=object(),
        )

        assert result == expected_draft
        calculate_draft_mock.assert_called_once_with(
            [
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
            ],
            None,
        )


class TestAutomaticDishNutritionNegativeInputValidation:
    """Negative unit tests for invalid inputs used by automatic dish nutrition calculation."""

    @pytest.mark.parametrize(
        ("field_name", "invalid_value"),
        [
            pytest.param("portion_size_grams", -0.01, id="negative-portion-size"),
            pytest.param("calories", -0.01, id="negative-calories"),
            pytest.param("protein", -0.01, id="negative-protein"),
            pytest.param("fat", -0.01, id="negative-fat"),
            pytest.param("carbs", -0.01, id="negative-carbs"),
        ],
    )
    def test_dish_payload_rejects_negative_nutrition_values(
        self,
        dish_payload_factory,
        field_name,
        invalid_value,
    ):
        """Reject negative dish nutrition and serving-size inputs before automatic calculation is used."""

        with pytest.raises(ValidationError):
            DishCreate(**dish_payload_factory(**{field_name: invalid_value}))

    @pytest.mark.parametrize(
        "ingredients",
        [
            pytest.param([{"product_id": 1, "quantity_grams": -0.01}], id="negative-ingredient-quantity"),
            pytest.param([{"product_id": -1, "quantity_grams": 100.0}], id="negative-product-id"),
        ],
    )
    def test_dish_payload_rejects_negative_ingredient_values(self, dish_payload_factory, ingredients):
        """Reject invalid ingredient references before products are loaded for calculation."""

        with pytest.raises(ValidationError):
            DishCreate(**dish_payload_factory(ingredients=ingredients))

    @pytest.mark.parametrize(
        ("protein", "fat", "carbs", "should_pass"),
        [
            pytest.param(40.0, 30.0, 30.0, True, id="macro-sum-equals-portion-size"),
            pytest.param(40.0, 30.0, 30.01, False, id="macro-sum-exceeds-portion-size"),
        ],
    )
    def test_dish_payload_rejects_macro_sum_above_portion_size(
        self,
        dish_payload_factory,
        protein,
        fat,
        carbs,
        should_pass,
    ):
        """Use boundary values for the rule: protein + fat + carbs <= portion_size_grams."""

        payload = dish_payload_factory(
            portion_size_grams=100.0,
            protein=protein,
            fat=fat,
            carbs=carbs,
        )

        if should_pass:
            dish = DishCreate(**payload)
            assert dish.protein + dish.fat + dish.carbs == dish.portion_size_grams
            return

        with pytest.raises(ValidationError, match="protein \\+ fat \\+ carbs"):
            DishCreate(**payload)
