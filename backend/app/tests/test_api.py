import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

os.environ["RECIPE_BOOK_DB_PATH"] = str(Path("test_recipe_book.db").resolve())

from app.database import SessionLocal, init_db
from app.main import app
from app.models import Dish, DishIngredient, Product

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    with SessionLocal() as session:
        session.execute(delete(DishIngredient))
        session.execute(delete(Dish))
        session.execute(delete(Product))
        session.commit()
    yield


def create_product(name: str, vegan: bool = True, category: str = "base"):
    response = client.post(
        "/products",
        data={
            "name": name,
            "calories": 100,
            "protein": 10,
            "fat": 5,
            "carbs": 20,
            "composition": "Test",
            "category": category,
            "requires_cooking": "false",
            "is_vegan": str(vegan).lower(),
            "is_gluten_free": "true",
            "is_sugar_free": "true",
        },
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
    create_product("Apple", category="fruit")
    create_product("Chicken", category="protein")

    response = client.get("/products", params={"search": "fru"})
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["Apple"]

    response = client.get("/products", params={"category": "ote"})
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["Chicken"]


def test_product_search_supports_cyrillic_casefold():
    create_product("\u0411\u0430\u043d\u0430\u043d", category="\u0424\u0440\u0443\u043a\u0442\u044b")

    response = client.get("/products", params={"search": "\u0431\u0430\u043d\u0430"})
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["\u0411\u0430\u043d\u0430\u043d"]

    response = client.get("/products", params={"category": "\u0444\u0440\u0443"})
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["\u0411\u0430\u043d\u0430\u043d"]


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
        data={
            "name": "Tofu Bowl",
            "description": "Protein bowl",
            "category": "dinner",
            "servings": 2,
            "calories": 190,
            "protein": 19,
            "fat": 9.5,
            "carbs": 38,
            "is_vegan": "true",
            "is_gluten_free": "true",
            "is_sugar_free": "true",
            "ingredients": json.dumps(ingredients),
        },
    )
    assert response.status_code == 201, response.text
    assert len(response.json()["ingredients"]) == 2


def test_dish_name_macro_sets_category_and_cleans_name():
    tofu = create_product("Tofu", vegan=True)
    response = client.post(
        "/dishes",
        data={
            "name": "!суп !десерт Tofu Bowl",
            "description": "Protein bowl",
            "category": "",
            "servings": 2,
            "calories": 190,
            "protein": 19,
            "fat": 9.5,
            "carbs": 38,
            "is_vegan": "true",
            "is_gluten_free": "true",
            "is_sugar_free": "true",
            "ingredients": json.dumps([{"product_id": tofu["id"], "quantity_grams": 200}]),
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["name"] == "Tofu Bowl"
    assert response.json()["category"] == "Суп"


def test_dish_form_category_overrides_name_macro():
    tofu = create_product("Tofu", vegan=True)
    response = client.post(
        "/dishes",
        data={
            "name": "!салат Tofu Bowl",
            "description": "Protein bowl",
            "category": "Ужин",
            "servings": 2,
            "calories": 190,
            "protein": 19,
            "fat": 9.5,
            "carbs": 38,
            "is_vegan": "true",
            "is_gluten_free": "true",
            "is_sugar_free": "true",
            "ingredients": json.dumps([{"product_id": tofu["id"], "quantity_grams": 200}]),
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["name"] == "Tofu Bowl"
    assert response.json()["category"] == "Ужин"


def test_dish_update_name_macro_sets_category_when_field_missing():
    tofu = create_product("Tofu", vegan=True)
    created = client.post(
        "/dishes",
        data={
            "name": "Tofu Bowl",
            "description": "Protein bowl",
            "category": "Ужин",
            "servings": 2,
            "calories": 190,
            "protein": 19,
            "fat": 9.5,
            "carbs": 38,
            "is_vegan": "true",
            "is_gluten_free": "true",
            "is_sugar_free": "true",
            "ingredients": json.dumps([{"product_id": tofu["id"], "quantity_grams": 200}]),
        },
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
        data={
            "name": "Protein Bowl",
            "description": "Protein bowl",
            "category": "Dinner",
            "servings": 2,
            "calories": 190,
            "protein": 19,
            "fat": 9.5,
            "carbs": 38,
            "is_vegan": "true",
            "is_gluten_free": "true",
            "is_sugar_free": "true",
            "ingredients": json.dumps([{"product_id": tofu["id"], "quantity_grams": 200}]),
        },
    )
    second = client.post(
        "/dishes",
        data={
            "name": "Morning Oatmeal",
            "description": "Warm",
            "category": "Breakfast",
            "servings": 1,
            "calories": 100,
            "protein": 10,
            "fat": 5,
            "carbs": 20,
            "is_vegan": "true",
            "is_gluten_free": "true",
            "is_sugar_free": "true",
            "ingredients": json.dumps([{"product_id": tofu["id"], "quantity_grams": 100}]),
        },
    )
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    response = client.get("/dishes", params={"search": "break"})
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["Morning Oatmeal"]

    response = client.get("/dishes", params={"category": "inn"})
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["Protein Bowl"]


def test_dish_search_supports_cyrillic_casefold():
    tofu = create_product("Tofu", vegan=True)
    created = client.post(
        "/dishes",
        data={
            "name": "\u0411\u0430\u043d\u0430\u043d\u043e\u0432\u044b\u0439 \u0441\u043c\u0443\u0437\u0438",
            "description": "Smoothie",
            "category": "\u041d\u0430\u043f\u0438\u0442\u043e\u043a",
            "servings": 1,
            "calories": 100,
            "protein": 10,
            "fat": 5,
            "carbs": 20,
            "is_vegan": "true",
            "is_gluten_free": "true",
            "is_sugar_free": "true",
            "ingredients": json.dumps([{"product_id": tofu["id"], "quantity_grams": 100}]),
        },
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
        data={
            "name": "Porridge",
            "description": "Warm",
            "category": "breakfast",
            "servings": 1,
            "calories": 100,
            "protein": 10,
            "fat": 5,
            "carbs": 20,
            "is_vegan": "false",
            "is_gluten_free": "true",
            "is_sugar_free": "true",
            "ingredients": json.dumps([{"product_id": milk["id"], "quantity_grams": 100}]),
        },
    )
    assert dish.status_code == 201, dish.text
    response = client.delete(f"/products/{milk['id']}")
    assert response.status_code == 409
    assert response.json()["detail"]["dishes"] == ["Porridge"]


def test_reject_invalid_manual_flags():
    cheese = create_product("Cheese", vegan=False)
    response = client.post(
        "/dishes",
        data={
            "name": "Salad",
            "description": "Fresh",
            "category": "lunch",
            "servings": 1,
            "calories": 100,
            "protein": 10,
            "fat": 5,
            "carbs": 20,
            "is_vegan": "true",
            "is_gluten_free": "true",
            "is_sugar_free": "true",
            "ingredients": json.dumps([{"product_id": cheese["id"], "quantity_grams": 100}]),
        },
    )
    assert response.status_code == 400
