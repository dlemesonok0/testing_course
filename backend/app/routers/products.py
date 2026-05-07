from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Dish, DishIngredient, Product, ProductPhoto
from app.schemas import MAX_PHOTO_COUNT, PRODUCT_SORT_FIELDS, ProductCreate, ProductRead, ProductUpdate, SearchParams
from app.services.files import build_asset_url, save_uploads, validate_image_uploads


router = APIRouter(prefix="/products", tags=["products"])

DIET_FLAG_FIELDS = ("is_vegan", "is_gluten_free", "is_sugar_free")


def validate_bju_sum(protein: float, fat: float, carbs: float) -> None:
    if protein + fat + carbs > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Сумма белков, жиров и углеводов не может превышать 100г на 100г продукта",
        )


def serialize_product(product: Product) -> ProductRead:
    photo_urls = [build_asset_url(photo.file_path) for photo in product.photos]
    if not photo_urls and product.photo_path:
        photo_urls = [build_asset_url(product.photo_path)]

    return ProductRead(
        id=product.id,
        name=product.name,
        calories=product.calories,
        protein=product.protein,
        fat=product.fat,
        carbs=product.carbs,
        composition=product.composition or None,
        category=product.category,
        cooking_state=product.cooking_state,
        is_vegan=product.is_vegan,
        is_gluten_free=product.is_gluten_free,
        is_sugar_free=product.is_sugar_free,
        photo_url=photo_urls[0] if photo_urls else None,
        photo_urls=photo_urls,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def clear_invalid_flags_for_linked_dishes(db: Session, product_id: int) -> None:
    linked_dishes = (
        db.scalars(
            select(Dish)
            .options(selectinload(Dish.ingredients).selectinload(DishIngredient.product))
            .join(Dish.ingredients)
            .where(DishIngredient.product_id == product_id)
        )
        .unique()
        .all()
    )

    for dish in linked_dishes:
        for flag_field in DIET_FLAG_FIELDS:
            if getattr(dish, flag_field) and not all(getattr(item.product, flag_field) for item in dish.ingredients):
                setattr(dish, flag_field, False)


def product_from_form(
    name: str = Form(...),
    calories: float = Form(...),
    protein: float = Form(...),
    fat: float = Form(...),
    carbs: float = Form(...),
    composition: str | None = Form(default=None),
    category: str = Form(...),
    cooking_state: str = Form(...),
    is_vegan: bool = Form(False),
    is_gluten_free: bool = Form(False),
    is_sugar_free: bool = Form(False),
    photo_links: list[str] | None = Form(default=None),
) -> ProductCreate:
    try:
        return ProductCreate(
            name=name,
            calories=calories,
            protein=protein,
            fat=fat,
            carbs=carbs,
            composition=composition,
            category=category,
            cooking_state=cooking_state,
            is_vegan=is_vegan,
            is_gluten_free=is_gluten_free,
            is_sugar_free=is_sugar_free,
            photo_links=[link.strip() for link in (photo_links or []) if link.strip()],
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc


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
        "cooking_state",
        "is_vegan",
        "is_gluten_free",
        "is_sugar_free",
    ):
        if field in form_data:
            payload[field] = form_data[field]
    if "photo_links" in form_data:
        payload["photo_links"] = [link.strip() for link in form_data.getlist("photo_links") if str(link).strip()]
    return parse_product_update_payload(payload)


def uploaded_files_from_form(form_data, field_name: str) -> list[UploadFile]:
    return [item for item in form_data.getlist(field_name) if getattr(item, "filename", None)]


def normalize_product_photo_links(photo_links: list[object] | None) -> list[str]:
    from app.services.files import normalize_storage_path
    return [normalize_storage_path(str(link).strip()) for link in (photo_links or []) if str(link).strip()]


def validate_product_photo_batch(uploaded_files: list[UploadFile], photo_links: list[str]) -> None:
    if len(uploaded_files) + len(photo_links) > MAX_PHOTO_COUNT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Нельзя добавить более {MAX_PHOTO_COUNT} фотографий",
        )


@router.get("", response_model=list[ProductRead])
def list_products(
    search: str | None = None,
    category: str | None = None,
    cookingState: str | None = Query(default=None),
    flags: list[str] = Query(default=[]),
    sortBy: str = Query(default="name"),
    sortOrder: str = Query(default="asc"),
    db: Session = Depends(get_db),
):
    params = SearchParams(
        search=search,
        category=category,
        cooking_state=cookingState,
        flags=flags,
        sort_by=sortBy,
        sort_order=sortOrder,
    )
    if params.sort_by not in PRODUCT_SORT_FIELDS:
        raise HTTPException(status_code=400, detail="Неподдерживаемое поле сортировки")

    stmt = select(Product).options(selectinload(Product.photos))
    if params.search:
        search_pattern = f"%{params.search.casefold()}%"
        stmt = stmt.where(func.unicode_lower(Product.name).like(search_pattern))
    if params.category:
        stmt = stmt.where(func.unicode_lower(Product.category).like(f"%{params.category.casefold()}%"))
    if params.cooking_state is not None:
        stmt = stmt.where(Product.cooking_state == params.cooking_state)
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
    validate_bju_sum(payload.protein, payload.fat, payload.carbs)
    uploaded_files = validate_image_uploads(photos)
    if not uploaded_files and photo is not None and photo.filename:
        uploaded_files = validate_image_uploads([photo])
    photo_links = normalize_product_photo_links(payload.photo_links)
    validate_product_photo_batch(uploaded_files, photo_links)
    saved_photo_paths = save_uploads(uploaded_files)
    all_photo_sources = [*saved_photo_paths, *photo_links]

    product = Product(
        name=payload.name,
        photo_path=all_photo_sources[0] if all_photo_sources else None,
        calories=payload.calories,
        protein=payload.protein,
        fat=payload.fat,
        carbs=payload.carbs,
        composition=payload.composition or "",
        category=payload.category,
        cooking_state=payload.cooking_state,
        is_vegan=payload.is_vegan,
        is_gluten_free=payload.is_gluten_free,
        is_sugar_free=payload.is_sugar_free,
    )
    for index, file_path in enumerate(all_photo_sources):
        product.photos.append(ProductPhoto(file_path=file_path, position=index))
    db.add(product)
    db.commit()
    db.refresh(product)
    return serialize_product(product)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.scalar(select(Product).options(selectinload(Product.photos)).where(Product.id == product_id))
    if product is None:
        raise HTTPException(status_code=404, detail="Продукт не найден")
    return serialize_product(product)


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(product_id: int, request: Request, db: Session = Depends(get_db)):
    product = db.scalar(select(Product).options(selectinload(Product.photos)).where(Product.id == product_id))
    if product is None:
        raise HTTPException(status_code=404, detail="Продукт не найден")

    content_type = request.headers.get("content-type", "")
    uploaded_files: list[UploadFile] = []
    if content_type.startswith("application/json"):
        try:
            raw_payload = await request.json()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Некорректное тело JSON-запроса") from exc
        request_payload = parse_product_update_payload(raw_payload) or ProductUpdate()
    else:
        form_data = await request.form()
        request_payload = product_update_from_form_data(form_data) or ProductUpdate()
        uploaded_files = validate_image_uploads(uploaded_files_from_form(form_data, "photos"))
        if not uploaded_files:
            uploaded_files = validate_image_uploads(uploaded_files_from_form(form_data, "photo"))

    photo_links_provided = "photo_links" in request_payload.__fields_set__
    photo_links = normalize_product_photo_links(request_payload.photo_links if photo_links_provided else None)
    validate_product_photo_batch(uploaded_files, photo_links)
    new_photo_paths = save_uploads(uploaded_files)

    update_data = request_payload.dict(exclude_unset=True, exclude={"photo_links"})
    diet_flags_updated = any(field in update_data for field in DIET_FLAG_FIELDS)
    if update_data:
        merged_protein = float(update_data.get("protein", product.protein))
        merged_fat = float(update_data.get("fat", product.fat))
        merged_carbs = float(update_data.get("carbs", product.carbs))
        validate_bju_sum(merged_protein, merged_fat, merged_carbs)
        for field, value in update_data.items():
            if field == "composition":
                setattr(product, field, value or "")
            else:
                setattr(product, field, value)
    if photo_links_provided or new_photo_paths:
        # If photo_links_provided is True, it means we have a list of existing photos to keep/reorder.
        # If it's False, but new_photo_paths is not empty, we keep ALL existing photos and ADD new ones.
        if photo_links_provided:
            all_photo_sources = [*new_photo_paths, *photo_links]
        else:
            existing_paths = [photo.file_path for photo in product.photos]
            all_photo_sources = [*new_photo_paths, *existing_paths]

        product.photo_path = all_photo_sources[0] if all_photo_sources else None
        product.photos.clear()
        for index, file_path in enumerate(all_photo_sources):
            product.photos.append(ProductPhoto(file_path=file_path, position=index))
    if diet_flags_updated:
        clear_invalid_flags_for_linked_dishes(db, product.id)
    if update_data or photo_links_provided or new_photo_paths:
        db.commit()
        db.refresh(product)
    return serialize_product(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Продукт не найден")

    linked_dishes = db.scalars(
        select(Dish.name)
        .distinct()
        .join(Dish.ingredients)
        .where(DishIngredient.product_id == product_id)
        .order_by(Dish.name.asc())
    ).all()
    if linked_dishes:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"detail": "Продукт используется в блюдах", "dishes": linked_dishes},
        )

    db.delete(product)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
