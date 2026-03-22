from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Dish, DishIngredient, Product
from app.schemas import PRODUCT_SORT_FIELDS, ProductCreate, ProductRead, ProductUpdate, SearchParams
from app.services.files import save_upload

router = APIRouter(prefix="/products", tags=["products"])


def serialize_product(product: Product) -> ProductRead:
    return ProductRead(
        id=product.id,
        name=product.name,
        calories=product.calories,
        protein=product.protein,
        fat=product.fat,
        carbs=product.carbs,
        composition=product.composition,
        category=product.category,
        requires_cooking=product.requires_cooking,
        is_vegan=product.is_vegan,
        is_gluten_free=product.is_gluten_free,
        is_sugar_free=product.is_sugar_free,
        photo_url=f"/uploads/{product.photo_path}" if product.photo_path else None,
        created_at=product.created_at,
        updated_at=product.updated_at,
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
    db: Session = Depends(get_db),
):
    params = SearchParams(
        search=search,
        category=category,
        requires_cooking=requiresCooking,
        flags=flags,
        sort_by=sortBy,
        sort_order=sortOrder,
    )
    if params.sort_by not in PRODUCT_SORT_FIELDS:
        raise HTTPException(status_code=400, detail="Unsupported sort field")

    stmt = select(Product)
    if params.search:
        search_pattern = f"%{params.search.casefold()}%"
        stmt = stmt.where(
            or_(
                func.unicode_lower(Product.name).like(search_pattern),
                func.unicode_lower(Product.category).like(search_pattern),
            )
        )
    if params.category:
        stmt = stmt.where(func.unicode_lower(Product.category).like(f"%{params.category.casefold()}%"))
    if params.requires_cooking is not None:
        stmt = stmt.where(Product.requires_cooking.is_(params.requires_cooking))
    for flag in params.flags:
        stmt = stmt.where(getattr(Product, f"is_{flag}").is_(True))

    sort_column = getattr(Product, params.sort_by)
    stmt = stmt.order_by(sort_column.desc() if params.sort_order == "desc" else sort_column.asc())
    return [serialize_product(product) for product in db.scalars(stmt).all()]


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate = Depends(product_from_form),
    photo: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    product = Product(
        name=payload.name,
        photo_path=save_upload(photo),
        calories=payload.calories,
        protein=payload.protein,
        fat=payload.fat,
        carbs=payload.carbs,
        composition=payload.composition,
        category=payload.category,
        requires_cooking=payload.requires_cooking,
        is_vegan=payload.is_vegan,
        is_gluten_free=payload.is_gluten_free,
        is_sugar_free=payload.is_sugar_free,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return serialize_product(product)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return serialize_product(product)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = payload.dict(exclude_unset=True)
    if update_data:
        for field, value in update_data.items():
            setattr(product, field, value)
        db.commit()
        db.refresh(product)
    return serialize_product(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    linked_dishes = db.scalars(
        select(Dish.name)
        .join(Dish.ingredients)
        .where(DishIngredient.product_id == product_id)
        .order_by(Dish.name.asc())
    ).all()
    if linked_dishes:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"detail": "Product is used in dishes", "dishes": linked_dishes},
        )

    db.delete(product)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
