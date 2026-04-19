import asyncio
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.routers import dishes
from app.schemas import DISH_CATEGORIES, DishCreate, DishIngredientInput, DishUpdate
from app.services.nutrition import calculate_draft


@pytest.fixture
def product_snapshot_factory():
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

    def test_calculate_draft_scales_recipe_composition_to_requested_portion_size(self, product_snapshot_factory):
        """Recalculate nutrition from the recipe composition to the selected serving size."""

        first_product = product_snapshot_factory(calories=100.0, protein=10.0, fat=5.0, carbs=20.0)
        second_product = product_snapshot_factory(calories=200.0, protein=20.0, fat=10.0, carbs=40.0)

        result = calculate_draft(
            [
                (first_product, 100.0),
                (second_product, 100.0),
            ],
            portion_size_grams=300.0,
        )

        assert result["calories"] == 450.0
        assert result["protein"] == 45.0
        assert result["fat"] == 22.5
        assert result["carbs"] == 90.0

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

    def fake_calculate_draft(ingredients, portion_size_grams=None):
        captured["calculator_input"] = ingredients
        captured["portion_size_grams"] = portion_size_grams
        return expected_draft

    monkeypatch.setattr(dishes, "load_products_map", fake_load_products_map)
    monkeypatch.setattr(dishes, "calculate_draft", fake_calculate_draft)

    result = dishes.nutrition_draft(
        ingredients=json.dumps([{"product_id": 1, "quantity_grams": 50.0}]),
        portion_size_grams=250.0,
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
    assert captured["portion_size_grams"] == 250.0


def test_dish_create_accepts_portion_macros_above_the_100_gram_limit():
    """Dish nutrition is stored per serving, so macros may legitimately exceed 100 g in total."""

    dish = DishCreate(
        name="Сытная паста",
        description=None,
        category=DISH_CATEGORIES[0],
        portion_size_grams=450.0,
        calories=920.0,
        protein=48.0,
        fat=32.0,
        carbs=128.0,
        is_vegan=False,
        is_gluten_free=False,
        is_sugar_free=False,
        ingredients=[DishIngredientInput(product_id=1, quantity_grams=450.0)],
    )

    assert dish.protein == 48.0
    assert dish.fat == 32.0
    assert dish.carbs == 128.0


def test_dish_update_accepts_portion_macros_above_the_100_gram_limit():
    """Partial updates must not reject portion-based macros that are larger than per-100 g limits."""

    update = DishUpdate(protein=42.0, fat=24.0, carbs=118.0)

    assert update.protein == 42.0
    assert update.fat == 24.0
    assert update.carbs == 118.0


def test_create_dish_preserves_user_overridden_portion_nutrition(monkeypatch):
    """Store user-edited macros while still calculating draft data from current inputs."""

    captured: dict[str, object] = {}
    expected_draft = {
        "calories": 640.0,
        "protein": 36.0,
        "fat": 18.0,
        "carbs": 92.0,
        "allowed_flags": [],
    }
    fake_product = SimpleNamespace(
        calories=320.0,
        protein=18.0,
        fat=9.0,
        carbs=46.0,
        is_vegan=False,
        is_gluten_free=False,
        is_sugar_free=False,
    )

    class FakeDb:
        def add(self, dish):
            dish.id = 101
            captured["dish"] = dish

        def commit(self):
            return None

    monkeypatch.setattr(dishes, "load_products_map", lambda db, ingredients: {1: fake_product})
    def fake_calculate_draft(ingredients, portion_size_grams=None):
        captured["portion_size_grams"] = portion_size_grams
        return expected_draft

    monkeypatch.setattr(dishes, "calculate_draft", fake_calculate_draft)
    monkeypatch.setattr(dishes, "validate_image_uploads", lambda uploads: [])
    monkeypatch.setattr(dishes, "save_uploads", lambda uploads: [])
    monkeypatch.setattr(dishes, "get_dish", lambda db, dish_id: captured["dish"])
    monkeypatch.setattr(dishes, "dish_payload", lambda dish: dish)

    saved = dishes.create_dish(
        payload=DishCreate(
            name="Паста",
            description=None,
            category=DISH_CATEGORIES[0],
            portion_size_grams=350.0,
            calories=1.0,
            protein=2.0,
            fat=3.0,
            carbs=4.0,
            is_vegan=False,
            is_gluten_free=False,
            is_sugar_free=False,
            ingredients=[DishIngredientInput(product_id=1, quantity_grams=200.0)],
        ),
        photo=None,
        photos=None,
        db=FakeDb(),
    )

    assert saved.calories == 1.0
    assert saved.protein == 2.0
    assert saved.fat == 3.0
    assert saved.carbs == 4.0
    assert captured["portion_size_grams"] == 350.0


def test_update_dish_preserves_user_overridden_portion_nutrition(monkeypatch):
    """Manual macro edits are saved, while later input changes can still trigger a new draft calculation."""

    expected_draft = {
        "calories": 510.0,
        "protein": 28.0,
        "fat": 22.0,
        "carbs": 54.0,
        "allowed_flags": [],
    }
    fake_product = SimpleNamespace(
        calories=170.0,
        protein=9.33,
        fat=7.33,
        carbs=18.0,
        is_vegan=False,
        is_gluten_free=False,
        is_sugar_free=False,
    )
    existing_dish = SimpleNamespace(
        id=11,
        name="Лазанья",
        description="",
        category=DISH_CATEGORIES[0],
        portion_size_grams=300.0,
        calories=1.0,
        protein=2.0,
        fat=3.0,
        carbs=4.0,
        is_vegan=False,
        is_gluten_free=False,
        is_sugar_free=False,
        ingredients=[SimpleNamespace(product_id=1, quantity_grams=300.0)],
        photos=[],
        photo_path=None,
    )

    class FakeDb:
        def commit(self):
            return None

    class FakeRequest:
        headers = {"content-type": "application/json"}

        async def json(self):
            return {
                "portion_size_grams": 150.0,
                "calories": 10.0,
                "protein": 11.0,
                "fat": 12.0,
                "carbs": 13.0,
            }

    monkeypatch.setattr(dishes, "get_dish", lambda db, dish_id: existing_dish)
    monkeypatch.setattr(dishes, "load_products_map", lambda db, ingredients: {1: fake_product})

    def fake_calculate_draft(ingredients, portion_size_grams=None):
        captured["portion_size_grams"] = portion_size_grams
        return expected_draft

    captured: dict[str, object] = {}
    monkeypatch.setattr(dishes, "calculate_draft", fake_calculate_draft)
    monkeypatch.setattr(dishes, "dish_payload", lambda dish: dish)

    updated = asyncio.run(dishes.update_dish(11, FakeRequest(), FakeDb()))

    assert updated.portion_size_grams == 150.0
    assert updated.calories == 10.0
    assert updated.protein == 11.0
    assert updated.fat == 12.0
    assert updated.carbs == 13.0
    assert captured["portion_size_grams"] == 150.0
