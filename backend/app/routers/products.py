from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Dish, DishIngredient, Product, ProductPhoto
from app.schemas import PRODUCT_SORT_FIELDS, ProductCreate, ProductRead, ProductUpdate, SearchParams
from app.services.files import save_upload, save_uploads

router = APIRouter(prefix="/products", tags=["products"])


def serialize_product(product: Product) -> ProductRead:
    photo_urls = [f"/uploads/{photo.file_path}" for photo in product.photos]
    if not photo_urls and product.photo_path:
        photo_urls = [f"/uploads/{product.photo_path}"]

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
        photo_url=photo_urls[0] if photo_urls else None,
        photo_urls=photo_urls,
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


def parse_product_update_payload(payload: dict[str, object]) -> ProductUpdate | None:
    if not payload:
        return None
    try:
        return ProductUpdate(**payload)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc


def product_update_from_form_data(form_data) -> ProductUpdate | None:
    payload: dict[str, object] = {}
    for field in (
        "name",
        "calories",
        "protein",
        "fat",
        "carbs",
        "composition",
        "category",
        "requires_cooking",
        "is_vegan",
        "is_gluten_free",
        "is_sugar_free",
    ):
        if field in form_data:
            payload[field] = form_data[field]
    return parse_product_update_payload(payload)


def uploaded_files_from_form(form_data, field_name: str) -> list[UploadFile]:
    return [item for item in form_data.getlist(field_name) if getattr(item, "filename", None)]


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

    stmt = select(Product).options(selectinload(Product.photos))
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
    photos: list[UploadFile] | None = File(default=None),
    db: Session = Depends(get_db),
):
    saved_photo_paths = save_uploads(photos)
    if not saved_photo_paths:
        legacy_photo = save_upload(photo)
        if legacy_photo:
            saved_photo_paths = [legacy_photo]

    product = Product(
        name=payload.name,
        photo_path=saved_photo_paths[0] if saved_photo_paths else None,
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
    for index, file_path in enumerate(saved_photo_paths):
        product.photos.append(ProductPhoto(file_path=file_path, position=index))
    db.add(product)
    db.commit()
    db.refresh(product)
    return serialize_product(product)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.scalar(select(Product).options(selectinload(Product.photos)).where(Product.id == product_id))
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return serialize_product(product)


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(product_id: int, request: Request, db: Session = Depends(get_db)):
    product = db.scalar(select(Product).options(selectinload(Product.photos)).where(Product.id == product_id))
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    content_type = request.headers.get("content-type", "")
    new_photo_paths: list[str] = []
    if content_type.startswith("application/json"):
        try:
            raw_payload = await request.json()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON body") from exc
        request_payload = parse_product_update_payload(raw_payload) or ProductUpdate()
    else:
        form_data = await request.form()
        request_payload = product_update_from_form_data(form_data) or ProductUpdate()
        uploaded_photos = uploaded_files_from_form(form_data, "photos")
        if not uploaded_photos:
            uploaded_photos = uploaded_files_from_form(form_data, "photo")
        new_photo_paths = save_uploads(uploaded_photos)

    update_data = request_payload.dict(exclude_unset=True, exclude_none=True)
    if update_data:
        for field, value in update_data.items():
            setattr(product, field, value)
    if new_photo_paths:
        product.photo_path = new_photo_paths[0]
        product.photos.clear()
        for index, file_path in enumerate(new_photo_paths):
            product.photos.append(ProductPhoto(file_path=file_path, position=index))
    if update_data or new_photo_paths:
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
