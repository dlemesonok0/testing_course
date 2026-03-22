import json
import sqlite3

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status

from app.database import get_db
from app.schemas import DISH_SORT_FIELDS, DishCreate, DishIngredientInput, DishRead, DishUpdate, NutritionDraft, SearchParams
from app.services.files import save_upload
from app.services.nutrition import calculate_draft

router = APIRouter(prefix="/dishes", tags=["dishes"])


def parse_ingredients(raw: str) -> list[DishIngredientInput]:
    return [DishIngredientInput.parse_obj(item) for item in json.loads(raw)]


def load_products_map(db: sqlite3.Connection, ingredients: list[DishIngredientInput]) -> dict[int, dict]:
    product_ids = sorted({item.product_id for item in ingredients})
    placeholders = ",".join("?" for _ in product_ids)
    rows = db.execute(f"SELECT * FROM products WHERE id IN ({placeholders})", product_ids).fetchall() if product_ids else []
    product_map = {row["id"]: dict(row) for row in rows}
    if len(product_map) != len(product_ids):
        raise HTTPException(status_code=400, detail="One or more products do not exist")
    return product_map


def validate_requested_flags(payload: DishCreate, allowed_flags: list[str]) -> None:
    requested = []
    if payload.is_vegan:
        requested.append("vegan")
    if payload.is_gluten_free:
        requested.append("gluten_free")
    if payload.is_sugar_free:
        requested.append("sugar_free")
    invalid = [flag for flag in requested if flag not in allowed_flags]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Flags not allowed by ingredients: {', '.join(invalid)}")


def dish_from_form(
    name: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    servings: int = Form(...),
    calories: float = Form(...),
    protein: float = Form(...),
    fat: float = Form(...),
    carbs: float = Form(...),
    is_vegan: bool = Form(False),
    is_gluten_free: bool = Form(False),
    is_sugar_free: bool = Form(False),
    ingredients: str = Form(...),
) -> DishCreate:
    return DishCreate(
        name=name,
        description=description,
        category=category,
        servings=servings,
        calories=calories,
        protein=protein,
        fat=fat,
        carbs=carbs,
        is_vegan=is_vegan,
        is_gluten_free=is_gluten_free,
        is_sugar_free=is_sugar_free,
        ingredients=parse_ingredients(ingredients),
    )


def dish_payload(db: sqlite3.Connection, dish_row: sqlite3.Row) -> DishRead:
    ingredients = db.execute(
        """
        SELECT di.product_id, di.quantity_grams, p.name AS product_name, p.calories, p.protein, p.fat, p.carbs,
               p.is_vegan, p.is_gluten_free, p.is_sugar_free
        FROM dish_ingredients di
        JOIN products p ON p.id = di.product_id
        WHERE di.dish_id = ?
        ORDER BY di.id
        """,
        (dish_row["id"],),
    ).fetchall()
    draft = calculate_draft([(dict(row), row["quantity_grams"]) for row in ingredients])
    data = dict(dish_row)
    return DishRead.parse_obj(
        {
            **data,
            "is_vegan": bool(data["is_vegan"]),
            "is_gluten_free": bool(data["is_gluten_free"]),
            "is_sugar_free": bool(data["is_sugar_free"]),
            "photo_url": f"/uploads/{data['photo_path']}" if data.get("photo_path") else None,
            "ingredients": [
                {
                    "product_id": row["product_id"],
                    "product_name": row["product_name"],
                    "quantity_grams": row["quantity_grams"],
                }
                for row in ingredients
            ],
            "allowed_flags": draft["allowed_flags"],
        }
    )


@router.get("/nutrition-draft", response_model=NutritionDraft)
def nutrition_draft(ingredients: str = Query(...), db: sqlite3.Connection = Depends(get_db)):
    parsed = parse_ingredients(ingredients)
    product_map = load_products_map(db, parsed)
    return calculate_draft([(product_map[item.product_id], item.quantity_grams) for item in parsed])


@router.get("", response_model=list[DishRead])
def list_dishes(
    search: str | None = None,
    category: str | None = None,
    flags: list[str] = Query(default=[]),
    sortBy: str = Query(default="name"),
    sortOrder: str = Query(default="asc"),
    db: sqlite3.Connection = Depends(get_db),
):
    params = SearchParams(search=search, category=category, flags=flags, sort_by=sortBy, sort_order=sortOrder)
    if params.sort_by not in DISH_SORT_FIELDS:
        raise HTTPException(status_code=400, detail="Unsupported sort field")
    clauses: list[str] = []
    values: list[object] = []
    if params.search:
        clauses.append("LOWER(name) LIKE ?")
        values.append(f"%{params.search.lower()}%")
    if params.category:
        clauses.append("category = ?")
        values.append(params.category)
    for flag in params.flags:
        clauses.append(f"is_{flag} = 1")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = db.execute(f"SELECT * FROM dishes {where} ORDER BY {params.sort_by} {params.sort_order.upper()}", values).fetchall()
    return [dish_payload(db, row) for row in rows]


@router.post("", response_model=DishRead, status_code=status.HTTP_201_CREATED)
def create_dish(
    payload: DishCreate = Depends(dish_from_form),
    photo: UploadFile | None = File(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    product_map = load_products_map(db, payload.ingredients)
    draft = calculate_draft([(product_map[item.product_id], item.quantity_grams) for item in payload.ingredients])
    validate_requested_flags(payload, draft["allowed_flags"])

    cursor = db.execute(
        """
        INSERT INTO dishes (
            name, photo_path, description, category, servings, calories, protein, fat, carbs,
            is_vegan, is_gluten_free, is_sugar_free
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.name,
            save_upload(photo),
            payload.description,
            payload.category,
            payload.servings,
            payload.calories,
            payload.protein,
            payload.fat,
            payload.carbs,
            int(payload.is_vegan),
            int(payload.is_gluten_free),
            int(payload.is_sugar_free),
        ),
    )
    for item in payload.ingredients:
        db.execute(
            "INSERT INTO dish_ingredients (dish_id, product_id, quantity_grams) VALUES (?, ?, ?)",
            (cursor.lastrowid, item.product_id, item.quantity_grams),
        )
    db.commit()
    row = db.execute("SELECT * FROM dishes WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dish_payload(db, row)


@router.get("/{dish_id}", response_model=DishRead)
def get_dish(dish_id: int, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT * FROM dishes WHERE id = ?", (dish_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Dish not found")
    return dish_payload(db, row)


@router.patch("/{dish_id}", response_model=DishRead)
def update_dish(dish_id: int, payload: DishUpdate, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute("SELECT * FROM dishes WHERE id = ?", (dish_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Dish not found")

    update_data = payload.dict(exclude_unset=True)
    ingredients_payload = update_data.pop("ingredients", None)
    current_ingredients = db.execute("SELECT product_id, quantity_grams FROM dish_ingredients WHERE dish_id = ?", (dish_id,)).fetchall()
    effective_ingredients = ingredients_payload or [DishIngredientInput.parse_obj(dict(row)) for row in current_ingredients]
    product_map = load_products_map(db, effective_ingredients)
    draft = calculate_draft([(product_map[item.product_id], item.quantity_grams) for item in effective_ingredients])

    merged = {
        "name": update_data.get("name", existing["name"]),
        "description": update_data.get("description", existing["description"]),
        "category": update_data.get("category", existing["category"]),
        "servings": update_data.get("servings", existing["servings"]),
        "calories": update_data.get("calories", existing["calories"]),
        "protein": update_data.get("protein", existing["protein"]),
        "fat": update_data.get("fat", existing["fat"]),
        "carbs": update_data.get("carbs", existing["carbs"]),
        "is_vegan": update_data.get("is_vegan", bool(existing["is_vegan"])),
        "is_gluten_free": update_data.get("is_gluten_free", bool(existing["is_gluten_free"])),
        "is_sugar_free": update_data.get("is_sugar_free", bool(existing["is_sugar_free"])),
        "ingredients": effective_ingredients,
    }
    validate_requested_flags(DishCreate.parse_obj(merged), draft["allowed_flags"])

    if update_data:
        assignments = ", ".join(f"{field} = ?" for field in update_data.keys())
        db.execute(f"UPDATE dishes SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", list(update_data.values()) + [dish_id])
    if ingredients_payload is not None:
        db.execute("DELETE FROM dish_ingredients WHERE dish_id = ?", (dish_id,))
        for item in ingredients_payload:
            db.execute(
                "INSERT INTO dish_ingredients (dish_id, product_id, quantity_grams) VALUES (?, ?, ?)",
                (dish_id, item.product_id, item.quantity_grams),
            )
    db.commit()
    return dish_payload(db, db.execute("SELECT * FROM dishes WHERE id = ?", (dish_id,)).fetchone())


@router.delete("/{dish_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dish(dish_id: int, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT id FROM dishes WHERE id = ?", (dish_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Dish not found")
    db.execute("DELETE FROM dishes WHERE id = ?", (dish_id,))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
