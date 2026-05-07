import pytest

from app.schemas import COOKING_STATES, DISH_CATEGORIES, PRODUCT_CATEGORIES


def product_form(**overrides):
    payload = {
        "name": "  Test   Product  ",
        "calories": "120",
        "protein": "40",
        "fat": "30",
        "carbs": "30",
        "composition": "  water, salt  ",
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


class TestProductCreationApi:
    """Integration tests for product creation using equivalence partitioning and boundary values."""

    def test_healthcheck_returns_ok(self, client):
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @pytest.mark.parametrize(
        ("protein", "fat", "carbs", "expected_status"),
        [
            pytest.param("40", "30", "30", 201, id="macro-sum-equals-100-boundary"),
            pytest.param("40", "30", "30.01", 422, id="macro-sum-above-100-boundary"),
            pytest.param("100.01", "0", "0", 422, id="single-protein-above-100-invalid"),
            pytest.param("0", "100.01", "0", 422, id="single-fat-above-100-invalid"),
            pytest.param("0", "0", "100.01", 422, id="single-carbs-above-100-invalid"),
            pytest.param("0", "0", "0", 201, id="zero-nutrients-valid-boundary"),
            pytest.param("-0.01", "0", "0", 422, id="negative-protein-invalid-boundary"),
            pytest.param("0", "-0.01", "0", 422, id="negative-fat-invalid-boundary"),
            pytest.param("0", "0", "-0.01", 422, id="negative-carbs-invalid-boundary"),
        ],
    )
    def test_product_nutrient_boundaries(self, client, protein, fat, carbs, expected_status):
        response = client.post(
            "/products",
            data=product_form(protein=protein, fat=fat, carbs=carbs),
        )

        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        ("field", "value", "expected_status"),
        [
            pytest.param("calories", "-0.01", 422, id="negative-calories-invalid"),
            pytest.param("calories", "0", 201, id="zero-calories-valid-boundary"),
        ],
    )
    def test_product_calorie_boundaries(self, client, field, value, expected_status):
        response = client.post("/products", data=product_form(**{field: value}))

        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "missing_field",
        [
            pytest.param("name", id="missing-name"),
            pytest.param("calories", id="missing-calories"),
            pytest.param("protein", id="missing-protein"),
            pytest.param("fat", id="missing-fat"),
            pytest.param("carbs", id="missing-carbs"),
            pytest.param("category", id="missing-category"),
            pytest.param("cooking_state", id="missing-cooking-state"),
        ],
    )
    def test_create_product_rejects_missing_required_fields(self, client, missing_field):
        payload = product_form()
        payload.pop(missing_field)

        response = client.post("/products", data=payload)

        assert response.status_code == 422

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            pytest.param("category", "unknown", id="unknown-category"),
            pytest.param("cooking_state", "unknown", id="unknown-cooking-state"),
        ],
    )
    def test_create_product_rejects_unknown_choices(self, client, field, value):
        response = client.post("/products", data=product_form(**{field: value}))

        assert response.status_code == 422

    @pytest.mark.parametrize(
        ("photo_count", "expected_status"),
        [
            pytest.param(5, 201, id="five-photos-valid-boundary"),
            pytest.param(6, 422, id="six-photos-invalid-boundary"),
        ],
    )
    def test_create_product_photo_upload_limit(self, client, photo_count, expected_status):
        files = [
            ("photos", (f"photo-{index}.png", b"image-bytes", "image/png"))
            for index in range(photo_count)
        ]

        response = client.post("/products", data=product_form(), files=files)

        assert response.status_code == expected_status

    def test_create_product_rejects_non_image_upload(self, client):
        response = client.post(
            "/products",
            data=product_form(),
            files={"photo": ("notes.txt", b"plain text", "text/plain")},
        )

        assert response.status_code == 422

    @pytest.mark.parametrize(
        ("name", "expected_status"),
        [
            pytest.param("A", 422, id="one-character-name-invalid"),
            pytest.param("    ", 422, id="blank-name-invalid"),
            pytest.param("Ok", 201, id="two-character-name-valid-boundary"),
        ],
    )
    def test_create_product_name_length_and_blank_boundaries(self, client, name, expected_status):
        response = client.post("/products", data=product_form(name=name))

        assert response.status_code == expected_status

    def test_create_product_blank_composition_is_returned_as_null(self, client):
        product = create_product(client, composition="   ")

        assert product["composition"] is None

    @pytest.mark.parametrize(
        ("photo_links", "expected_status"),
        [
            pytest.param([f"/uploads/{index}.png" for index in range(5)], 201, id="five-photo-links-valid-boundary"),
            pytest.param([f"/uploads/{index}.png" for index in range(6)], 422, id="six-photo-links-invalid-boundary"),
        ],
    )
    def test_create_product_photo_link_limit(self, client, photo_links, expected_status):
        response = client.post("/products", data=product_form(photo_links=photo_links))

        assert response.status_code == expected_status


class TestProductListApi:
    """Integration tests for product listing partitions, filters, flags, and sorting."""

    def test_list_products_search_filters_flags_and_sorting(self, client):
        create_product(client, name="Apple Fresh", calories="50", category=PRODUCT_CATEGORIES[0])
        create_product(
            client,
            name="Beef Steak",
            calories="250",
            category=PRODUCT_CATEGORIES[1],
            cooking_state=COOKING_STATES[2],
            is_vegan="false",
            is_gluten_free="true",
            is_sugar_free="true",
        )

        assert len(client.get("/products").json()) == 2
        assert [item["name"] for item in client.get("/products", params={"search": "app"}).json()] == ["Apple Fresh"]
        assert [item["category"] for item in client.get("/products", params={"category": PRODUCT_CATEGORIES[1]}).json()] == [PRODUCT_CATEGORIES[1]]
        assert [item["cooking_state"] for item in client.get("/products", params={"cookingState": COOKING_STATES[2]}).json()] == [COOKING_STATES[2]]
        assert len(client.get("/products", params=[("flags", "vegan")]).json()) == 1
        assert len(client.get("/products", params=[("flags", "gluten_free"), ("flags", "sugar_free")]).json()) == 2
        sorted_products = client.get("/products", params={"sortBy": "calories", "sortOrder": "desc"}).json()
        assert [item["name"] for item in sorted_products] == ["Beef Steak", "Apple Fresh"]
        assert client.get("/products", params={"search": "missing"}).json() == []

    @pytest.mark.parametrize(
        ("flag", "expected_status"),
        [
            pytest.param("vegan", 200, id="valid-flag-vegan"),
            pytest.param("unknown", 422, id="invalid-flag"),
        ],
    )
    def test_product_flag_validation(self, client, flag, expected_status):
        response = client.get("/products", params=[("flags", flag)])

        assert response.status_code == expected_status


class TestProductDetailUpdateDeleteApi:
    """Integration tests for product detail, partial update, photo ordering, and deletion links."""

    def test_get_product_returns_200_or_404(self, client):
        product = create_product(client)

        assert client.get(f"/products/{product['id']}").status_code == 200
        assert client.get("/products/999").status_code == 404

    def test_patch_product_updates_json_and_bju_boundary(self, client):
        product = create_product(client, protein="10", fat="10", carbs="10")

        response = client.patch(
            f"/products/{product['id']}",
            json={"name": "  Updated   Product ", "protein": 40, "fat": 30, "carbs": 30},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Updated Product"
        assert body["protein"] + body["fat"] + body["carbs"] == 100

    def test_patch_product_rejects_invalid_bju_sum(self, client):
        product = create_product(client, protein="10", fat="10", carbs="10")

        response = client.patch(f"/products/{product['id']}", json={"protein": 40, "fat": 30, "carbs": 30.01})

        assert response.status_code == 422

    def test_patch_missing_product_returns_404(self, client):
        response = client.patch("/products/999", json={"name": "Updated"})

        assert response.status_code == 404

    @pytest.mark.parametrize(
        ("payload", "expected_status"),
        [
            pytest.param({"name": "A"}, 422, id="patch-one-character-name-invalid"),
            pytest.param({"composition": "   "}, 200, id="patch-blank-composition-clears-value"),
            pytest.param({"photo_links": [f"/uploads/{index}.png" for index in range(6)]}, 422, id="patch-six-photo-links-invalid"),
        ],
    )
    def test_patch_product_edge_validation(self, client, payload, expected_status):
        product = create_product(client)

        response = client.patch(f"/products/{product['id']}", json=payload)

        assert response.status_code == expected_status
        if payload == {"composition": "   "}:
            assert response.json()["composition"] is None

    def test_patch_product_reorders_and_clears_photo_links(self, client):
        product = create_product(
            client,
            photo_links=["/uploads/first.png", "/uploads/second.png"],
        )

        reordered = client.patch(
            f"/products/{product['id']}",
            json={"photo_links": ["/uploads/second.png", "/uploads/first.png"]},
        )
        cleared = client.patch(f"/products/{product['id']}", json={"photo_links": []})

        assert reordered.status_code == 200
        assert reordered.json()["photo_urls"] == ["/uploads/second.png", "/uploads/first.png"]
        assert cleared.status_code == 200
        assert cleared.json()["photo_urls"] == []

    def test_delete_product_returns_204_404_and_409_when_used_by_dish(self, client):
        unused = create_product(client, name="Unused Product")
        used = create_product(client, name="Used Product")
        dish_response = client.post(
            "/dishes",
            data={
                "name": "Linked Dish",
                "category": DISH_CATEGORIES[0],
                "portion_size_grams": "100",
                "calories": "100",
                "protein": "40",
                "fat": "30",
                "carbs": "30",
                "ingredients": f'[{{"product_id": {used["id"]}, "quantity_grams": 100}}]',
            },
        )
        assert dish_response.status_code == 201, dish_response.text

        assert client.delete(f"/products/{unused['id']}").status_code == 204
        assert client.delete(f"/products/{unused['id']}").status_code == 404
        assert client.delete(f"/products/{used['id']}").status_code == 409
