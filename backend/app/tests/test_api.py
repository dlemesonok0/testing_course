import json
import os
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
os.environ["RECIPE_BOOK_DB_PATH"] = str(Path("test_recipe_book.db").resolve())

from app.database import init_db
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    db_file = Path("test_recipe_book.db")
    init_db()
    connection = sqlite3.connect(db_file)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("DELETE FROM dish_ingredients")
    connection.execute("DELETE FROM dishes")
    connection.execute("DELETE FROM products")
    connection.commit()
    connection.close()
    yield
    # Windows can keep SQLite locked briefly after the test client closes connections.


def create_product(name: str, vegan: bool = True):
    response = client.post(
        "/products",
        data={
            "name": name,
            "calories": 100,
            "protein": 10,
            "fat": 5,
            "carbs": 20,
            "composition": "Test",
            "category": "base",
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
