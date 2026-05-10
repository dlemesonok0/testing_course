import json

import pytest

from app.schemas import COOKING_STATES, DISH_CATEGORIES, PRODUCT_CATEGORIES
from app.routers.dishes import DISH_CATEGORY_MACROS


def product_form(**overrides):
    payload = {
        "name": "Base Product",
        "calories": "100",
        "protein": "10",
        "fat": "5",
        "carbs": "20",
        "category": PRODUCT_CATEGORIES[0],
        "cooking_state": COOKING_STATES[0],
        "is_vegan": "true",
        "is_gluten_free": "true",
        "is_sugar_free": "true",
    }
    payload.update(overrides)
    return payload


def create_product(client, **overrides):
    response = client.post("/products", data=product_form(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def dish_form(product_id, **overrides):
    payload = {
        "name": "  Test   Dish ",
        "description": "  tasty  ",
        "category": DISH_CATEGORIES[0],
        "portion_size_grams": "100",
        "calories": "100",
        "protein": "40",
        "fat": "30",
        "carbs": "30",
        "is_vegan": "true",
        "is_gluten_free": "true",
        "is_sugar_free": "true",
        "ingredients": json.dumps([{"product_id": product_id, "quantity_grams": 100}]),
    }
    payload.update(overrides)
    return payload


def create_dish(client, product_id, **overrides):
    response = client.post("/dishes", data=dish_form(product_id, **overrides))
    assert response.status_code == 201, response.text
    return response.json()


class TestDishCreationApi:
    """Integration tests for dish creation using real Product to DishIngredient to Dish links."""

    def test_create_dish_with_existing_product_and_normalized_fields(self, client):
        product = create_product(client)

        dish = create_dish(client, product["id"])

        assert dish["name"] == "Test Dish"
        assert dish["description"] == "tasty"
        assert dish["ingredients"] == [{"product_id": product["id"], "product_name": "Base Product", "quantity_grams": 100.0}]
        assert sorted(dish["allowed_flags"]) == ["gluten_free", "sugar_free", "vegan"]

    def test_create_dish_with_multiple_ingredients_and_filtered_requested_flags(self, client):
        vegan = create_product(client, name="Vegan Product")
        meat = create_product(client, name="Meat Product", is_vegan="false", is_gluten_free="true", is_sugar_free="true")

        dish = create_dish(
            client,
            vegan["id"],
            ingredients=json.dumps(
                [
                    {"product_id": vegan["id"], "quantity_grams": 50},
                    {"product_id": meat["id"], "quantity_grams": 50},
                ]
            ),
        )

        assert dish["is_vegan"] is False
        assert dish["is_gluten_free"] is True
        assert dish["is_sugar_free"] is True
        assert sorted(dish["allowed_flags"]) == ["gluten_free", "sugar_free"]

    def test_create_dish_rejects_missing_product_and_empty_ingredients(self, client):
        product = create_product(client)

        missing = client.post("/dishes", data=dish_form(999))
        empty = client.post("/dishes", data=dish_form(product["id"], ingredients="[]"))

        assert missing.status_code == 400
        assert empty.status_code == 422

    @pytest.mark.parametrize(
        ("name", "expected_status"),
        [
            pytest.param("A", 422, id="one-character-dish-name-invalid"),
            pytest.param("    ", 422, id="blank-dish-name-invalid"),
            pytest.param("Ok", 201, id="two-character-dish-name-valid-boundary"),
        ],
    )
    def test_create_dish_name_length_and_blank_boundaries(self, client, name, expected_status):
        product = create_product(client)

        response = client.post("/dishes", data=dish_form(product["id"], name=name))

        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        ("ingredients", "expected_status"),
        [
            pytest.param("not-json", 422, id="malformed-ingredients-json"),
            pytest.param("{}", 422, id="ingredients-object-instead-of-list"),
            pytest.param('[{"product_id": 1}]', 422, id="missing-ingredient-quantity"),
        ],
    )
    def test_create_dish_rejects_malformed_ingredients_payloads(self, client, ingredients, expected_status):
        product = create_product(client)
        payload = ingredients.replace('"product_id": 1', f'"product_id": {product["id"]}')

        response = client.post("/dishes", data=dish_form(product["id"], ingredients=payload))

        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        ("macro", "expected_category"),
        [pytest.param(macro, category, id=f"macro-{index}") for index, (macro, category) in enumerate(DISH_CATEGORY_MACROS.items())],
    )
    def test_create_dish_assigns_category_from_name_macro(self, client, macro, expected_category):
        product = create_product(client)

        dish = create_dish(client, product["id"], name=f"{macro} Macro Dish", category="")

        assert dish["name"] == "Macro Dish"
        assert dish["category"] == expected_category

    def test_create_dish_explicit_category_overrides_name_macro(self, client):
        product = create_product(client)
        macro = next(iter(DISH_CATEGORY_MACROS))

        dish = create_dish(client, product["id"], name=f"{macro} Explicit Category Dish", category=DISH_CATEGORIES[1])

        assert dish["name"] == "Explicit Category Dish"
        assert dish["category"] == DISH_CATEGORIES[1]

    def test_create_dish_uses_first_macro_when_several_are_present(self, client):
        product = create_product(client)
        macros = list(DISH_CATEGORY_MACROS.items())
        first_macro, first_category = macros[0]
        second_macro, _ = macros[1]

        dish = create_dish(client, product["id"], name=f"{first_macro} {second_macro} Multi Macro Dish", category="")

        assert dish["category"] == first_category

    @pytest.mark.parametrize(
        ("photo_count", "expected_status"),
        [
            pytest.param(5, 201, id="five-dish-photos-valid-boundary"),
            pytest.param(6, 422, id="six-dish-photos-invalid-boundary"),
        ],
    )
    def test_create_dish_photo_upload_limit(self, client, photo_count, expected_status):
        product = create_product(client)
        files = [
            ("photos", (f"dish-photo-{index}.png", b"image-bytes", "image/png"))
            for index in range(photo_count)
        ]

        response = client.post("/dishes", data=dish_form(product["id"]), files=files)

        assert response.status_code == expected_status

    def test_create_dish_rejects_non_image_upload(self, client):
        product = create_product(client)

        response = client.post(
            "/dishes",
            data=dish_form(product["id"]),
            files={"photo": ("notes.txt", b"plain text", "text/plain")},
        )

        assert response.status_code == 422

    @pytest.mark.parametrize(
        ("photo_links", "expected_status"),
        [
            pytest.param([f"/uploads/dish-{index}.png" for index in range(5)], 201, id="five-dish-photo-links-valid-boundary"),
            pytest.param([f"/uploads/dish-{index}.png" for index in range(6)], 422, id="six-dish-photo-links-invalid-boundary"),
        ],
    )
    def test_create_dish_photo_link_limit(self, client, photo_links, expected_status):
        product = create_product(client)

        response = client.post("/dishes", data=dish_form(product["id"], photo_links=photo_links))

        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "missing_field",
        [
            pytest.param("name", id="missing-dish-name"),
            pytest.param("portion_size_grams", id="missing-portion-size"),
            pytest.param("calories", id="missing-dish-calories"),
            pytest.param("protein", id="missing-dish-protein"),
            pytest.param("fat", id="missing-dish-fat"),
            pytest.param("carbs", id="missing-dish-carbs"),
            pytest.param("ingredients", id="missing-dish-ingredients"),
        ],
    )
    def test_create_dish_rejects_missing_required_fields(self, client, missing_field):
        product = create_product(client)
        payload = dish_form(product["id"])
        payload.pop(missing_field)

        response = client.post("/dishes", data=payload)

        assert response.status_code == 422

    @pytest.mark.parametrize(
        ("quantity", "expected_status"),
        [
            pytest.param(0.01, 201, id="ingredient-quantity-0-01-valid-boundary"),
            pytest.param(0, 422, id="ingredient-quantity-zero-invalid-boundary"),
        ],
    )
    def test_create_dish_ingredient_quantity_boundaries(self, client, quantity, expected_status):
        product = create_product(client)

        response = client.post(
            "/dishes",
            data=dish_form(product["id"], ingredients=json.dumps([{"product_id": product["id"], "quantity_grams": quantity}])),
        )

        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        ("portion_size", "protein", "fat", "carbs", "expected_status"),
        [
            pytest.param(0.01, 0.01, 0, 0, 201, id="portion-0-01-valid-boundary"),
            pytest.param(0, 0, 0, 0, 422, id="portion-zero-invalid-boundary"),
            pytest.param(100, 40, 30, 30, 201, id="dish-macro-sum-equals-portion-boundary"),
            pytest.param(100, 40, 30, 30.01, 422, id="dish-macro-sum-above-portion-boundary"),
        ],
    )
    def test_create_dish_portion_and_macro_boundaries(self, client, portion_size, protein, fat, carbs, expected_status):
        product = create_product(client)

        response = client.post(
            "/dishes",
            data=dish_form(
                product["id"],
                portion_size_grams=str(portion_size),
                protein=str(protein),
                fat=str(fat),
                carbs=str(carbs),
            ),
        )

        assert response.status_code == expected_status


class TestDishNutritionDraftApi:
    """Integration tests for nutrition draft calculations and ingredient boundary values."""

    def test_nutrition_draft_for_one_and_multiple_products(self, client):
        first = create_product(client, calories="100", protein="10", fat="5", carbs="20")
        second = create_product(client, calories="200", protein="20", fat="10", carbs="40", is_sugar_free="false")

        one = client.get("/dishes/nutrition-draft", params={"ingredients": json.dumps([{"product_id": first["id"], "quantity_grams": 50}])})
        many = client.get(
            "/dishes/nutrition-draft",
            params={
                "ingredients": json.dumps(
                    [
                        {"product_id": first["id"], "quantity_grams": 50},
                        {"product_id": second["id"], "quantity_grams": 25},
                    ]
                )
            },
        )

        assert one.status_code == 200
        assert one.json()["calories"] == 50
        assert many.status_code == 200
        assert many.json()["calories"] == 100
        assert sorted(many.json()["allowed_flags"]) == ["gluten_free", "vegan"]

    def test_nutrition_draft_values_can_be_manually_corrected_when_creating_dish(self, client):
        product = create_product(client, calories="100", protein="10", fat="5", carbs="20")
        draft = client.get("/dishes/nutrition-draft", params={"ingredients": json.dumps([{"product_id": product["id"], "quantity_grams": 100}])})
        assert draft.status_code == 200
        assert draft.json()["calories"] == 100

        dish = create_dish(client, product["id"], calories="111", protein="11", fat="6", carbs="21")

        assert dish["calories"] == 111
        assert dish["protein"] == 11
        assert dish["fat"] == 6
        assert dish["carbs"] == 21

    @pytest.mark.parametrize(
        ("ingredients", "expected_status"),
        [
            pytest.param([{"product_id": 999, "quantity_grams": 1}], 400, id="missing-product-invalid"),
            pytest.param([{"product_id": 1, "quantity_grams": 0.01}], 200, id="draft-quantity-0-01-valid-boundary"),
            pytest.param([{"product_id": 1, "quantity_grams": 0}], 422, id="draft-quantity-zero-invalid-boundary"),
        ],
    )
    def test_nutrition_draft_validation(self, client, ingredients, expected_status):
        product = create_product(client)
        normalized = [
            {**item, "product_id": product["id"] if item["product_id"] == 1 else item["product_id"]}
            for item in ingredients
        ]

        response = client.get("/dishes/nutrition-draft", params={"ingredients": json.dumps(normalized)})

        assert response.status_code == expected_status

    def test_nutrition_draft_rejects_invalid_json(self, client):
        response = client.get("/dishes/nutrition-draft", params={"ingredients": "not-json"})

        assert response.status_code == 422

    def test_nutrition_draft_rejects_missing_required_query(self, client):
        response = client.get("/dishes/nutrition-draft")

        assert response.status_code == 422


class TestDishListDetailUpdateDeleteApi:
    """Integration tests for dish list partitions, updates, recalculation, and deletion."""

    def test_list_dishes_search_category_flags_and_sorting(self, client):
        product = create_product(client)
        create_dish(client, product["id"], name="Apple Cake", calories="200", category=DISH_CATEGORIES[0])
        create_dish(client, product["id"], name="Green Soup", calories="80", category=DISH_CATEGORIES[5])

        assert len(client.get("/dishes").json()) == 2
        assert [item["name"] for item in client.get("/dishes", params={"search": "cake"}).json()] == ["Apple Cake"]
        assert [item["category"] for item in client.get("/dishes", params={"category": DISH_CATEGORIES[5]}).json()] == [DISH_CATEGORIES[5]]
        assert len(client.get("/dishes", params=[("flags", "vegan")]).json()) == 2
        sorted_dishes = client.get("/dishes", params={"sortBy": "calories", "sortOrder": "desc"}).json()
        assert [item["name"] for item in sorted_dishes] == ["Apple Cake", "Green Soup"]
        assert client.get("/dishes", params={"search": "missing"}).json() == []

    @pytest.mark.parametrize(
        ("flag", "expected_status"),
        [
            pytest.param("vegan", 200, id="valid-dish-flag-vegan"),
            pytest.param("unknown", 422, id="invalid-dish-flag"),
        ],
    )
    def test_dish_flag_validation(self, client, flag, expected_status):
        response = client.get("/dishes", params=[("flags", flag)])

        assert response.status_code == expected_status

    def test_get_dish_returns_200_or_404(self, client):
        product = create_product(client)
        dish = create_dish(client, product["id"])

        assert client.get(f"/dishes/{dish['id']}").status_code == 200
        assert client.get("/dishes/999").status_code == 404

    def test_patch_dish_changes_fields_replaces_ingredients_and_recalculates_flags(self, client):
        vegan = create_product(client, name="Vegan Product")
        meat = create_product(client, name="Meat Product", is_vegan="false", is_gluten_free="true", is_sugar_free="true")
        dish = create_dish(client, vegan["id"])

        response = client.patch(
            f"/dishes/{dish['id']}",
            json={
                "name": " Updated Dish ",
                "description": " updated ",
                "ingredients": [{"product_id": meat["id"], "quantity_grams": 0.01}],
                "is_vegan": True,
                "is_gluten_free": True,
                "is_sugar_free": True,
                "portion_size_grams": 0.01,
                "protein": 0.01,
                "fat": 0,
                "carbs": 0,
            },
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["name"] == "Updated Dish"
        assert body["description"] == "updated"
        assert body["portion_size_grams"] == 0.01
        assert body["protein"] == 0.01
        assert body["fat"] == 0
        assert body["carbs"] == 0
        assert body["ingredients"][0]["product_id"] == meat["id"]
        assert body["is_vegan"] is False
        assert sorted(body["allowed_flags"]) == ["gluten_free", "sugar_free"]

    def test_patch_dish_rejects_invalid_boundaries(self, client):
        product = create_product(client)
        dish = create_dish(client, product["id"])

        zero_quantity = client.patch(f"/dishes/{dish['id']}", json={"ingredients": [{"product_id": product["id"], "quantity_grams": 0}]})
        bad_macros = client.patch(f"/dishes/{dish['id']}", json={"portion_size_grams": 100, "protein": 40, "fat": 30, "carbs": 30.01})

        assert zero_quantity.status_code == 422
        assert bad_macros.status_code == 422

    def test_patch_missing_dish_returns_404(self, client):
        response = client.patch("/dishes/999", json={"name": "Updated Dish"})

        assert response.status_code == 404

    @pytest.mark.parametrize(
        ("payload", "expected_status"),
        [
            pytest.param({"name": "A"}, 422, id="patch-one-character-dish-name-invalid"),
            pytest.param({"description": "   "}, 200, id="patch-blank-description-clears-value"),
            pytest.param({"ingredients": []}, 422, id="patch-empty-ingredients-invalid"),
        ],
    )
    def test_patch_dish_edge_validation(self, client, payload, expected_status):
        product = create_product(client)
        dish = create_dish(client, product["id"])

        response = client.patch(f"/dishes/{dish['id']}", json=payload)

        assert response.status_code == expected_status
        if payload == {"description": "   "}:
            assert response.json()["description"] is None

    def test_patch_dish_reorders_and_clears_photo_links(self, client):
        product = create_product(client)
        dish = create_dish(
            client,
            product["id"],
            photo_links=["/uploads/first-dish.png", "/uploads/second-dish.png"],
        )

        reordered = client.patch(
            f"/dishes/{dish['id']}",
            json={"photo_links": ["/uploads/second-dish.png", "/uploads/first-dish.png"]},
        )
        cleared = client.patch(f"/dishes/{dish['id']}", json={"photo_links": []})

        assert reordered.status_code == 200
        assert reordered.json()["photo_urls"] == ["/uploads/second-dish.png", "/uploads/first-dish.png"]
        assert cleared.status_code == 200
        assert cleared.json()["photo_urls"] == []

    def test_delete_dish_then_repeat_returns_404(self, client):
        product = create_product(client)
        dish = create_dish(client, product["id"])

        assert client.delete(f"/dishes/{dish['id']}").status_code == 204
        assert client.delete(f"/dishes/{dish['id']}").status_code == 404
