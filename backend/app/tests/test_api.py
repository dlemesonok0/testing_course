import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["RECIPE_BOOK_DB_PATH"] = str(Path("test_recipe_book.db").resolve())

from app.database import Base, SessionLocal, engine, init_db
from app.main import app
from app.models import Dish, DishIngredient, DishPhoto, Product, ProductPhoto

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield


def product_payload(
    name: str,
    *,
    calories: float = 100,
    protein: float = 10,
    fat: float = 5,
    carbs: float = 20,
    composition: str | None = "Test",
    category: str = "Овощи",
    cooking_state: str = "Готовый к употреблению",
    vegan: bool = True,
):
    return {
        "name": name,
        "calories": calories,
        "protein": protein,
        "fat": fat,
        "carbs": carbs,
        "composition": composition,
        "category": category,
        "cooking_state": cooking_state,
        "is_vegan": str(vegan).lower(),
        "is_gluten_free": "true",
        "is_sugar_free": "true",
    }


def dish_payload(
    name: str,
    ingredients: list[dict[str, float | int]],
    **overrides,
):
    payload = {
        "name": name,
        "description": "Protein bowl",
        "category": "Второе",
        "portion_size_grams": 250,
        "calories": 190,
        "protein": 19,
        "fat": 9.5,
        "carbs": 38,
        "is_vegan": "true",
        "is_gluten_free": "true",
        "is_sugar_free": "true",
        "ingredients": json.dumps(ingredients),
    }
    payload.update(overrides)
    return payload


def create_product(name: str, vegan: bool = True, category: str = "Овощи"):
    response = client.post(
        "/products",
        data=product_payload(name, vegan=vegan, category=category),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_product_search():
    create_product("Яблоко")
    create_product("Банан")
    response = client.get("/products", params={"search": "бл"})
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["Яблоко"]


def test_product_search_and_category_filter_support_partial_matches():
    create_product("Apple", category="Овощи")
    create_product("Chicken", category="Мясной")

    response = client.get("/products", params={"search": "овощ"})
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["Apple"]

    response = client.get("/products", params={"category": "ясн"})
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["Chicken"]


def test_product_search_supports_cyrillic_casefold():
    create_product("\u0411\u0430\u043d\u0430\u043d", category="\u0417\u0435\u043b\u0435\u043d\u044c")

    response = client.get("/products", params={"search": "\u0431\u0430\u043d\u0430"})
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["\u0411\u0430\u043d\u0430\u043d"]

    response = client.get("/products", params={"category": "\u0437\u0435\u043b"})
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["\u0411\u0430\u043d\u0430\u043d"]


def test_product_create_supports_multiple_photos():
    response = client.post(
        "/products",
        data=product_payload("Banana", composition="Fruit"),
        files=[
            ("photos", ("first.jpg", b"first-photo", "image/jpeg")),
            ("photos", ("second.jpg", b"second-photo", "image/jpeg")),
        ],
    )
    assert response.status_code == 201, response.text
    assert len(response.json()["photo_urls"]) == 2
    assert response.json()["photo_url"] == response.json()["photo_urls"][0]


def test_product_update_replaces_photo_set():
    created = client.post(
        "/products",
        data=product_payload("Banana", composition="Fruit"),
        files=[("photos", ("first.jpg", b"first-photo", "image/jpeg"))],
    )
    assert created.status_code == 201, created.text

    updated = client.patch(
        f"/products/{created.json()['id']}",
        data=product_payload("Banana premium", calories=101, carbs=21, composition="Fruit"),
        files=[
            ("photos", ("second.jpg", b"second-photo", "image/jpeg")),
            ("photos", ("third.jpg", b"third-photo", "image/jpeg")),
        ],
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Banana premium"
    assert len(updated.json()["photo_urls"]) == 2
    assert updated.json()["photo_url"] == updated.json()["photo_urls"][0]
    assert updated.json()["photo_urls"][0] != created.json()["photo_urls"][0]

    with SessionLocal() as session:
        product = session.get(Product, created.json()["id"])
        assert product is not None
        assert len(product.photos) == 2


def test_dish_draft_and_create():
    tofu = create_product("Tofu", vegan=True)
    sauce = create_product("Sauce", vegan=True)
    ingredients = [
        {"product_id": tofu["id"], "quantity_grams": 150},
        {"product_id": sauce["id"], "quantity_grams": 50},
    ]
    draft = client.get("/dishes/nutrition-draft", params={"ingredients": json.dumps(ingredients)})
    assert draft.status_code == 200
    assert draft.json()["calories"] == 200.0
    assert "vegan" in draft.json()["allowed_flags"]

    response = client.post(
        "/dishes",
        data=dish_payload("Tofu Bowl", ingredients, portion_size_grams=300),
    )
    assert response.status_code == 201, response.text
    assert len(response.json()["ingredients"]) == 2


def test_dish_create_supports_multiple_photos():
    tofu = create_product("Tofu", vegan=True)
    response = client.post(
        "/dishes",
        data=dish_payload("Photo Bowl", [{"product_id": tofu["id"], "quantity_grams": 200}]),
        files=[
            ("photos", ("first.jpg", b"first-photo", "image/jpeg")),
            ("photos", ("second.jpg", b"second-photo", "image/jpeg")),
        ],
    )
    assert response.status_code == 201, response.text
    assert len(response.json()["photo_urls"]) == 2
    assert response.json()["photo_url"] == response.json()["photo_urls"][0]


def test_dish_update_replaces_photo_set():
    tofu = create_product("Tofu", vegan=True)
    created = client.post(
        "/dishes",
        data=dish_payload("Photo Bowl", [{"product_id": tofu["id"], "quantity_grams": 200}]),
        files=[("photos", ("first.jpg", b"first-photo", "image/jpeg"))],
    )
    assert created.status_code == 201, created.text

    updated = client.patch(
        f"/dishes/{created.json()['id']}",
        data=dish_payload("Updated Bowl", [{"product_id": tofu["id"], "quantity_grams": 200}]),
        files=[
            ("photos", ("second.jpg", b"second-photo", "image/jpeg")),
            ("photos", ("third.jpg", b"third-photo", "image/jpeg")),
        ],
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Updated Bowl"
    assert len(updated.json()["photo_urls"]) == 2
    assert updated.json()["photo_url"] == updated.json()["photo_urls"][0]
    assert updated.json()["photo_urls"][0] != created.json()["photo_urls"][0]

    with SessionLocal() as session:
        dish = session.get(Dish, created.json()["id"])
        assert dish is not None
        assert len(dish.photos) == 2


def test_dish_name_macro_sets_category_and_cleans_name():
    tofu = create_product("Tofu", vegan=True)
    response = client.post(
        "/dishes",
        data=dish_payload("!суп !десерт Tofu Bowl", [{"product_id": tofu["id"], "quantity_grams": 200}], category=""),
    )
    assert response.status_code == 201, response.text
    assert response.json()["name"] == "Tofu Bowl"
    assert response.json()["category"] == "Суп"


def test_dish_form_category_overrides_name_macro():
    tofu = create_product("Tofu", vegan=True)
    response = client.post(
        "/dishes",
        data=dish_payload("!салат Tofu Bowl", [{"product_id": tofu["id"], "quantity_grams": 200}], category="Второе"),
    )
    assert response.status_code == 201, response.text
    assert response.json()["name"] == "Tofu Bowl"
    assert response.json()["category"] == "Второе"


def test_dish_update_name_macro_sets_category_when_field_missing():
    tofu = create_product("Tofu", vegan=True)
    created = client.post(
        "/dishes",
        data=dish_payload("Tofu Bowl", [{"product_id": tofu["id"], "quantity_grams": 200}], category="Второе"),
    )
    assert created.status_code == 201, created.text

    updated = client.patch(
        f"/dishes/{created.json()['id']}",
        json={"name": "!напиток Tofu Smoothie"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Tofu Smoothie"
    assert updated.json()["category"] == "Напиток"


def test_dish_search_and_category_filter_support_partial_matches():
    tofu = create_product("Tofu", vegan=True)

    first = client.post(
        "/dishes",
        data=dish_payload("Protein Bowl", [{"product_id": tofu["id"], "quantity_grams": 200}], category="Второе"),
    )
    second = client.post(
        "/dishes",
        data=dish_payload(
            "Morning Oatmeal",
            [{"product_id": tofu["id"], "quantity_grams": 100}],
            description="Warm",
            category="Перекус",
            portion_size_grams=180,
            calories=100,
            protein=10,
            fat=5,
            carbs=20,
        ),
    )
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    response = client.get("/dishes", params={"search": "перек"})
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["Morning Oatmeal"]

    response = client.get("/dishes", params={"category": "тор"})
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["Protein Bowl"]


def test_dish_search_supports_cyrillic_casefold():
    tofu = create_product("Tofu", vegan=True)
    created = client.post(
        "/dishes",
        data=dish_payload(
            "\u0411\u0430\u043d\u0430\u043d\u043e\u0432\u044b\u0439 \u0441\u043c\u0443\u0437\u0438",
            [{"product_id": tofu["id"], "quantity_grams": 100}],
            description="Smoothie",
            category="\u041d\u0430\u043f\u0438\u0442\u043e\u043a",
            portion_size_grams=300,
            calories=100,
            protein=10,
            fat=5,
            carbs=20,
        ),
    )
    assert created.status_code == 201, created.text

    response = client.get("/dishes", params={"search": "\u0431\u0430\u043d\u0430\u043d"})
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["\u0411\u0430\u043d\u0430\u043d\u043e\u0432\u044b\u0439 \u0441\u043c\u0443\u0437\u0438"]

    response = client.get("/dishes", params={"category": "\u043d\u0430\u043f"})
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["\u0411\u0430\u043d\u0430\u043d\u043e\u0432\u044b\u0439 \u0441\u043c\u0443\u0437\u0438"]


def test_delete_product_conflict():
    milk = create_product("Milk", vegan=False)
    dish = client.post(
        "/dishes",
        data=dish_payload(
            "Porridge",
            [{"product_id": milk["id"], "quantity_grams": 100}],
            description="Warm",
            category="Перекус",
            portion_size_grams=220,
            calories=100,
            protein=10,
            fat=5,
            carbs=20,
            is_vegan="false",
        ),
    )
    assert dish.status_code == 201, dish.text
    response = client.delete(f"/products/{milk['id']}")
    assert response.status_code == 409
    assert response.json()["detail"]["dishes"] == ["Porridge"]


def test_reject_invalid_manual_flags():
    cheese = create_product("Cheese", vegan=False)
    response = client.post(
        "/dishes",
        data=dish_payload(
            "Salad",
            [{"product_id": cheese["id"], "quantity_grams": 100}],
            description="Fresh",
            category="Салат",
            portion_size_grams=180,
            calories=100,
            protein=10,
            fat=5,
            carbs=20,
        ),
    )
    assert response.status_code == 400


def test_product_constraints_accept_nullable_composition_and_limit_photo_count():
    created = client.post(
        "/products",
        data=product_payload("Тофу", composition=None, cooking_state="Полуфабрикат"),
    )
    assert created.status_code == 201, created.text
    assert created.json()["composition"] is None
    assert created.json()["cooking_state"] == "Полуфабрикат"

    too_many_photos = client.post(
        "/products",
        data=product_payload("Лапша"),
        files=[
            ("photos", ("1.jpg", b"1", "image/jpeg")),
            ("photos", ("2.jpg", b"2", "image/jpeg")),
            ("photos", ("3.jpg", b"3", "image/jpeg")),
            ("photos", ("4.jpg", b"4", "image/jpeg")),
            ("photos", ("5.jpg", b"5", "image/jpeg")),
            ("photos", ("6.jpg", b"6", "image/jpeg")),
        ],
    )
    assert too_many_photos.status_code == 422


def test_dish_constraints_require_valid_name_and_portion_size():
    tofu = create_product("Tofu", vegan=True)

    short_name = client.post(
        "/dishes",
        data=dish_payload("А", [{"product_id": tofu["id"], "quantity_grams": 100}]),
    )
    assert short_name.status_code == 422

    invalid_portion = client.post(
        "/dishes",
        data=dish_payload(
            "Valid dish",
            [{"product_id": tofu["id"], "quantity_grams": 100}],
            portion_size_grams=0,
        ),
    )
    assert invalid_portion.status_code == 422
