import sqlite3

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status

from app.database import get_db
from app.schemas import PRODUCT_SORT_FIELDS, ProductCreate, ProductRead, ProductUpdate, SearchParams
from app.services.files import save_upload

router = APIRouter(prefix="/products", tags=["products"])


def as_product(row: sqlite3.Row) -> ProductRead:
    data = dict(row)
    return ProductRead.parse_obj(
        {
            **data,
            "requires_cooking": bool(data["requires_cooking"]),
            "is_vegan": bool(data["is_vegan"]),
            "is_gluten_free": bool(data["is_gluten_free"]),
            "is_sugar_free": bool(data["is_sugar_free"]),
            "photo_url": f"/uploads/{data['photo_path']}" if data.get("photo_path") else None,
        }
    )


def product_from_form(
    name: str = Form(...),
    calories: float = Form(...),
    protein: float = Form(...),
    fat: float = Form(...),
    carbs: float = Form(...),
    composition: str = Form(...),
    category: str = Form(...),
    requires_cooking: bool = Form(False),
    is_vegan: bool = Form(False),
    is_gluten_free: bool = Form(False),
    is_sugar_free: bool = Form(False),
) -> ProductCreate:
    return ProductCreate(
        name=name,
        calories=calories,
        protein=protein,
        fat=fat,
        carbs=carbs,
        composition=composition,
        category=category,
        requires_cooking=requires_cooking,
        is_vegan=is_vegan,
        is_gluten_free=is_gluten_free,
        is_sugar_free=is_sugar_free,
    )


@router.get("", response_model=list[ProductRead])
def list_products(
    search: str | None = None,
    category: str | None = None,
    requiresCooking: bool | None = Query(default=None),
    flags: list[str] = Query(default=[]),
    sortBy: str = Query(default="name"),
    sortOrder: str = Query(default="asc"),
    db: sqlite3.Connection = Depends(get_db),
):
    params = SearchParams(search=search, category=category, requires_cooking=requiresCooking, flags=flags, sort_by=sortBy, sort_order=sortOrder)
    if params.sort_by not in PRODUCT_SORT_FIELDS:
        raise HTTPException(status_code=400, detail="Unsupported sort field")

    clauses: list[str] = []
    values: list[object] = []
    if params.search:
        clauses.append("LOWER(name) LIKE ?")
        values.append(f"%{params.search.lower()}%")
    if params.category:
        clauses.append("category = ?")
        values.append(params.category)
    if params.requires_cooking is not None:
        clauses.append("requires_cooking = ?")
        values.append(int(params.requires_cooking))
    for flag in params.flags:
        clauses.append(f"is_{flag} = 1")

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = db.execute(
        f"SELECT * FROM products {where} ORDER BY {params.sort_by} {params.sort_order.upper()}",
        values,
    ).fetchall()
    return [as_product(row) for row in rows]


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate = Depends(product_from_form),
    photo: UploadFile | None = File(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    cursor = db.execute(
        """
        INSERT INTO products (
            name, photo_path, calories, protein, fat, carbs, composition, category,
            requires_cooking, is_vegan, is_gluten_free, is_sugar_free
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.name,
            save_upload(photo),
            payload.calories,
            payload.protein,
            payload.fat,
            payload.carbs,
            payload.composition,
            payload.category,
            int(payload.requires_cooking),
            int(payload.is_vegan),
            int(payload.is_gluten_free),
            int(payload.is_sugar_free),
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM products WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return as_product(row)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    return as_product(row)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(product_id: int, payload: ProductUpdate, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")

    data = payload.dict(exclude_unset=True)
    if data:
        assignments = ", ".join(f"{field} = ?" for field in data.keys())
        values = list(data.values()) + [product_id]
        db.execute(f"UPDATE products SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", values)
        db.commit()
    return as_product(db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone())


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: sqlite3.Connection = Depends(get_db)):
    product = db.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    linked = db.execute(
        """
        SELECT d.name
        FROM dishes d
        JOIN dish_ingredients di ON di.dish_id = d.id
        WHERE di.product_id = ?
        """,
        (product_id,),
    ).fetchall()
    if linked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"detail": "Product is used in dishes", "dishes": [row["name"] for row in linked]},
        )

    db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
