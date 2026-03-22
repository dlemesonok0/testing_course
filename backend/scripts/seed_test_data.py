from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import delete

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import DB_PATH
from app.database import SessionLocal, init_db
from app.models import Dish, DishIngredient, Product
from app.services.nutrition import calculate_draft


PRODUCTS = [
    {
        "name": "Куриное филе",
        "calories": 110,
        "protein": 23,
        "fat": 1.2,
        "carbs": 0,
        "composition": "Куриное филе охлажденное",
        "category": "Мясо",
        "requires_cooking": True,
        "is_vegan": False,
        "is_gluten_free": True,
        "is_sugar_free": True,
    },
    {
        "name": "Гречка",
        "calories": 343,
        "protein": 13,
        "fat": 3.4,
        "carbs": 71,
        "composition": "Крупа гречневая ядрица",
        "category": "Крупы",
        "requires_cooking": True,
        "is_vegan": True,
        "is_gluten_free": True,
        "is_sugar_free": True,
    },
    {
        "name": "Рис",
        "calories": 344,
        "protein": 6.7,
        "fat": 0.7,
        "carbs": 78.9,
        "composition": "Крупа рисовая шлифованная",
        "category": "Крупы",
        "requires_cooking": True,
        "is_vegan": True,
        "is_gluten_free": True,
        "is_sugar_free": True,
    },
    {
        "name": "Помидор",
        "calories": 20,
        "protein": 1.1,
        "fat": 0.2,
        "carbs": 3.7,
        "composition": "Свежий томат",
        "category": "Овощи",
        "requires_cooking": False,
        "is_vegan": True,
        "is_gluten_free": True,
        "is_sugar_free": True,
    },
    {
        "name": "Огурец",
        "calories": 15,
        "protein": 0.8,
        "fat": 0.1,
        "carbs": 2.8,
        "composition": "Свежий огурец",
        "category": "Овощи",
        "requires_cooking": False,
        "is_vegan": True,
        "is_gluten_free": True,
        "is_sugar_free": True,
    },
    {
        "name": "Оливковое масло",
        "calories": 899,
        "protein": 0,
        "fat": 99.9,
        "carbs": 0,
        "composition": "Масло оливковое extra virgin",
        "category": "Масла",
        "requires_cooking": False,
        "is_vegan": True,
        "is_gluten_free": True,
        "is_sugar_free": True,
    },
    {
        "name": "Йогурт греческий",
        "calories": 66,
        "protein": 5.9,
        "fat": 3.2,
        "carbs": 3.5,
        "composition": "Йогурт натуральный без сахара",
        "category": "Молочные продукты",
        "requires_cooking": False,
        "is_vegan": False,
        "is_gluten_free": True,
        "is_sugar_free": True,
    },
    {
        "name": "Яблоко",
        "calories": 47,
        "protein": 0.4,
        "fat": 0.4,
        "carbs": 9.8,
        "composition": "Яблоко свежее",
        "category": "Фрукты",
        "requires_cooking": False,
        "is_vegan": True,
        "is_gluten_free": True,
        "is_sugar_free": True,
    },
    {
        "name": "Банан",
        "calories": 89,
        "protein": 1.5,
        "fat": 0.5,
        "carbs": 21,
        "composition": "Банан спелый",
        "category": "Фрукты",
        "requires_cooking": False,
        "is_vegan": True,
        "is_gluten_free": True,
        "is_sugar_free": True,
    },
    {
        "name": "Овсяные хлопья",
        "calories": 352,
        "protein": 12.3,
        "fat": 6.2,
        "carbs": 61.8,
        "composition": "Хлопья овсяные цельнозерновые",
        "category": "Крупы",
        "requires_cooking": True,
        "is_vegan": True,
        "is_gluten_free": False,
        "is_sugar_free": True,
    },
    {
        "name": "Молоко 2.5%",
        "calories": 52,
        "protein": 2.8,
        "fat": 2.5,
        "carbs": 4.7,
        "composition": "Пастеризованное молоко",
        "category": "Молочные продукты",
        "requires_cooking": False,
        "is_vegan": False,
        "is_gluten_free": True,
        "is_sugar_free": True,
    },
    {
        "name": "Мёд",
        "calories": 328,
        "protein": 0.8,
        "fat": 0,
        "carbs": 80.3,
        "composition": "Натуральный цветочный мед",
        "category": "Сладости",
        "requires_cooking": False,
        "is_vegan": False,
        "is_gluten_free": True,
        "is_sugar_free": False,
    },
]


DISHES = [
    {
        "name": "Гречка с курицей",
        "description": "Сытное второе блюдо на каждый день.",
        "category": "Второе",
        "servings": 2,
        "ingredients": [
            ("Куриное филе", 250),
            ("Гречка", 120),
            ("Оливковое масло", 10),
        ],
    },
    {
        "name": "Овощной салат",
        "description": "Легкий салат из свежих овощей.",
        "category": "Салат",
        "servings": 2,
        "ingredients": [
            ("Помидор", 180),
            ("Огурец", 180),
            ("Оливковое масло", 12),
        ],
    },
    {
        "name": "Йогуртовый завтрак",
        "description": "Быстрый перекус с фруктами и йогуртом.",
        "category": "Перекус",
        "servings": 1,
        "ingredients": [
            ("Йогурт греческий", 180),
            ("Яблоко", 120),
            ("Банан", 100),
        ],
    },
    {
        "name": "Овсянка с бананом и медом",
        "description": "Теплый сладкий завтрак.",
        "category": "Десерт",
        "servings": 2,
        "ingredients": [
            ("Овсяные хлопья", 90),
            ("Молоко 2.5%", 250),
            ("Банан", 100),
            ("Мёд", 20),
        ],
    },
    {
        "name": "Рис с овощами",
        "description": "Простой гарнир или самостоятельное блюдо.",
        "category": "Второе",
        "servings": 2,
        "ingredients": [
            ("Рис", 120),
            ("Помидор", 120),
            ("Огурец", 100),
            ("Оливковое масло", 8),
        ],
    },
]


def build_draft(ingredients: list[tuple[Product, float]]) -> dict:
    return calculate_draft(
        [
            (
                {
                    "calories": product.calories,
                    "protein": product.protein,
                    "fat": product.fat,
                    "carbs": product.carbs,
                    "is_vegan": product.is_vegan,
                    "is_gluten_free": product.is_gluten_free,
                    "is_sugar_free": product.is_sugar_free,
                },
                quantity_grams,
            )
            for product, quantity_grams in ingredients
        ]
    )


def main() -> None:
    init_db()

    with SessionLocal() as session:
        session.execute(delete(DishIngredient))
        session.execute(delete(Dish))
        session.execute(delete(Product))
        session.commit()

        products_by_name: dict[str, Product] = {}
        for payload in PRODUCTS:
            product = Product(**payload)
            session.add(product)
            products_by_name[product.name] = product
        session.flush()

        for payload in DISHES:
            resolved_ingredients = [
                (products_by_name[product_name], quantity_grams)
                for product_name, quantity_grams in payload["ingredients"]
            ]
            draft = build_draft(resolved_ingredients)
            dish = Dish(
                name=payload["name"],
                description=payload["description"],
                category=payload["category"],
                servings=payload["servings"],
                calories=draft["calories"],
                protein=draft["protein"],
                fat=draft["fat"],
                carbs=draft["carbs"],
                is_vegan="vegan" in draft["allowed_flags"],
                is_gluten_free="gluten_free" in draft["allowed_flags"],
                is_sugar_free="sugar_free" in draft["allowed_flags"],
            )
            for product, quantity_grams in resolved_ingredients:
                dish.ingredients.append(
                    DishIngredient(product_id=product.id, quantity_grams=quantity_grams)
                )
            session.add(dish)

        session.commit()

        product_count = session.query(Product).count()
        dish_count = session.query(Dish).count()

    print(f"Seed complete: {product_count} products, {dish_count} dishes")
    print(f"Database: {DB_PATH}")


if __name__ == "__main__":
    main()
