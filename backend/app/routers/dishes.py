import json
import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Dish, DishIngredient, DishPhoto, Product
from app.schemas import DISH_SORT_FIELDS, DishCreate, DishIngredientInput, DishRead, DishUpdate, NutritionDraft, SearchParams
from app.services.files import build_asset_url, save_uploads, validate_image_uploads
from app.services.nutrition import calculate_draft

router = APIRouter(prefix="/dishes", tags=["dishes"])

DISH_CATEGORY_MACROS = {
    "!десерт": "Десерт",
    "!первое": "Первое",
    "!второе": "Второе",
    "!напиток": "Напиток",
    "!салат": "Салат",
    "!суп": "Суп",
    "!перекус": "Перекус",
}
DISH_CATEGORY_MACRO_PATTERN = re.compile(
    r"(?<!\S)(?P<macro>"
    + "|".join(re.escape(macro) for macro in DISH_CATEGORY_MACROS)
    + r")(?=\s|$)",
    re.IGNORECASE,
)

def normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def resolve_dish_name_and_category(
    name: str,
    category: str | None,
    fallback_category: str | None = None,
) -> tuple[str, str | None]:
    raw_name = name.strip()
    matches = list(DISH_CATEGORY_MACRO_PATTERN.finditer(raw_name))
    cleaned_name = normalize_whitespace(DISH_CATEGORY_MACRO_PATTERN.sub(" ", raw_name))
    explicit_category = normalize_whitespace(category or "")

    macro_category = None
    if matches:
        macro_category = DISH_CATEGORY_MACROS[matches[0].group("macro").lower()]

    return cleaned_name, explicit_category or macro_category or fallback_category


def parse_ingredients(raw: str) -> list[DishIngredientInput]:
    return [DishIngredientInput.parse_obj(item) for item in json.loads(raw)]


def product_nutrition_snapshot(product: Product) -> dict:
    return {
        "calories": product.calories,
        "protein": product.protein,
        "fat": product.fat,
        "carbs": product.carbs,
        "is_vegan": product.is_vegan,
        "is_gluten_free": product.is_gluten_free,
        "is_sugar_free": product.is_sugar_free,
    }


def load_products_map(db: Session, ingredients: list[DishIngredientInput]) -> dict[int, Product]:
    product_ids = sorted({item.product_id for item in ingredients})
    if not product_ids:
        return {}

    rows = db.scalars(select(Product).where(Product.id.in_(product_ids))).all()
    product_map = {row.id: row for row in rows}
    if len(product_map) != len(product_ids):
        raise HTTPException(status_code=400, detail="Один или несколько продуктов не существуют")
    return product_map


def get_allowed_flags_subset(requested_vegan: bool, requested_gluten_free: bool, requested_sugar_free: bool, allowed_flags: list[str]) -> tuple[bool, bool, bool]:
    return (
        requested_vegan and "vegan" in allowed_flags,
        requested_gluten_free and "gluten_free" in allowed_flags,
        requested_sugar_free and "sugar_free" in allowed_flags,
    )


def dish_from_form(
    name: str = Form(...),
    description: str | None = Form(default=None),
    category: str = Form(""),
    portion_size_grams: float = Form(...),
    calories: float = Form(0),
    protein: float = Form(0),
    fat: float = Form(0),
    carbs: float = Form(0),
    is_vegan: bool = Form(False),
    is_gluten_free: bool = Form(False),
    is_sugar_free: bool = Form(False),
    ingredients: str = Form(...),
    photo_links: list[str] | None = Form(default=None),
) -> DishCreate:
    resolved_name, resolved_category = resolve_dish_name_and_category(name, category)
    try:
        return DishCreate(
            name=resolved_name,
            description=description,
            category=resolved_category or "",
            portion_size_grams=portion_size_grams,
            calories=calories,
            protein=protein,
            fat=fat,
            carbs=carbs,
            is_vegan=is_vegan,
            is_gluten_free=is_gluten_free,
            is_sugar_free=is_sugar_free,
            ingredients=parse_ingredients(ingredients),
            photo_links=[link.strip() for link in (photo_links or []) if link.strip()],
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc


def parse_dish_update_payload(payload: dict[str, object]) -> DishUpdate | None:
    if not payload:
        return None

    try:
        return DishUpdate(**payload)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc


def dish_update_from_form_data(form_data) -> DishUpdate | None:
    payload: dict[str, object] = {}
    for field in (
        "name",
        "description",
        "category",
        "portion_size_grams",
        "calories",
        "protein",
        "fat",
        "carbs",
        "is_vegan",
        "is_gluten_free",
        "is_sugar_free",
    ):
        if field in form_data:
            val = form_data[field]
            if field == "category" and (not val or val == "Без категории"):
                val = None
            payload[field] = val

    if "ingredients" in form_data:
        payload["ingredients"] = parse_ingredients(str(form_data["ingredients"]))
    
    if "photo_links" in form_data:
        payload["photo_links"] = [link.strip() for link in form_data.getlist("photo_links") if str(link).strip()]

    return parse_dish_update_payload(payload)


def uploaded_files_from_form(form_data, field_name: str) -> list[UploadFile]:
    return [item for item in form_data.getlist(field_name) if getattr(item, "filename", None)]


def normalize_dish_photo_links(photo_links: list[object] | None) -> list[str]:
    from app.services.files import normalize_storage_path
    return [normalize_storage_path(str(link).strip()) for link in (photo_links or []) if str(link).strip()]


def get_dish(db: Session, dish_id: int) -> Dish | None:
    stmt = (
        select(Dish)
        .options(
            selectinload(Dish.ingredients).selectinload(DishIngredient.product),
            selectinload(Dish.photos),
        )
        .where(Dish.id == dish_id)
    )
    return db.scalar(stmt)


def dish_payload(dish: Dish) -> DishRead:
    photo_urls = [build_asset_url(photo.file_path) for photo in dish.photos]
    if not photo_urls and dish.photo_path:
        photo_urls = [build_asset_url(dish.photo_path)]
    draft = calculate_draft(
        [(product_nutrition_snapshot(item.product), item.quantity_grams) for item in dish.ingredients],
        target_portion_grams=dish.portion_size_grams
    )
    return DishRead(
        id=dish.id,
        name=dish.name,
        description=dish.description or None,
        category=dish.category,
        portion_size_grams=dish.portion_size_grams,
        calories=dish.calories,
        protein=dish.protein,
        fat=dish.fat,
        carbs=dish.carbs,
        is_vegan=dish.is_vegan,
        is_gluten_free=dish.is_gluten_free,
        is_sugar_free=dish.is_sugar_free,
        photo_url=photo_urls[0] if photo_urls else None,
        photo_urls=photo_urls,
        created_at=dish.created_at,
        updated_at=dish.updated_at,
        ingredients=[
            {
                "product_id": item.product_id,
                "product_name": item.product.name,
                "quantity_grams": item.quantity_grams,
            }
            for item in dish.ingredients
        ],
        allowed_flags=draft["allowed_flags"],
    )


@router.get("/nutrition-draft", response_model=NutritionDraft)
def nutrition_draft(
    ingredients: str = Query(...),
    portion_size_grams: float | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    if not portion_size_grams:
        raise HTTPException(
            status_code=400,
            detail="Размер порции обязателен. Пожалуйста, укажите параметр portion_size_grams."
        )
    parsed = parse_ingredients(ingredients)
    product_map = load_products_map(db, parsed)
    return calculate_draft(
        [(product_nutrition_snapshot(product_map[item.product_id]), item.quantity_grams) for item in parsed],
        target_portion_grams=portion_size_grams
    )


@router.get("", response_model=list[DishRead])
def list_dishes(
    search: str | None = None,
    category: str | None = None,
    flags: list[str] = Query(default=[]),
    sortBy: str = Query(default="name"),
    sortOrder: str = Query(default="asc"),
    db: Session = Depends(get_db),
):
    params = SearchParams(search=search, category=category, flags=flags, sort_by=sortBy, sort_order=sortOrder)
    if params.sort_by not in DISH_SORT_FIELDS:
        raise HTTPException(status_code=400, detail="Неподдерживаемое поле сортировки")

    stmt = select(Dish).options(
        selectinload(Dish.ingredients).selectinload(DishIngredient.product),
        selectinload(Dish.photos),
    )
    if params.search:
        search_pattern = f"%{params.search.casefold()}%"
        stmt = stmt.where(
            or_(
                func.unicode_lower(Dish.name).like(search_pattern),
                func.unicode_lower(Dish.category).like(search_pattern),
            )
        )
    if params.category:
        stmt = stmt.where(func.unicode_lower(Dish.category).like(f"%{params.category.casefold()}%"))
    for flag in params.flags:
        stmt = stmt.where(getattr(Dish, f"is_{flag}").is_(True))

    sort_column = getattr(Dish, params.sort_by)
    stmt = stmt.order_by(sort_column.desc() if params.sort_order == "desc" else sort_column.asc())
    return [dish_payload(dish) for dish in db.scalars(stmt).all()]


@router.post("", response_model=DishRead, status_code=status.HTTP_201_CREATED)
def create_dish(
    payload: DishCreate = Depends(dish_from_form),
    photo: UploadFile | None = File(default=None),
    photos: list[UploadFile] | None = File(default=None),
    db: Session = Depends(get_db),
):
    product_map = load_products_map(db, payload.ingredients)
    draft = calculate_draft(
        [(product_nutrition_snapshot(product_map[item.product_id]), item.quantity_grams) for item in payload.ingredients],
        target_portion_grams=payload.portion_size_grams
    )
    final_vegan, final_gluten_free, final_sugar_free = get_allowed_flags_subset(
        payload.is_vegan, payload.is_gluten_free, payload.is_sugar_free, draft["allowed_flags"]
    )
    uploaded_files = validate_image_uploads(photos)
    if not uploaded_files and photo is not None and photo.filename:
        uploaded_files = validate_image_uploads([photo])
    saved_photo_paths = save_uploads(uploaded_files)

    photo_links = normalize_dish_photo_links(payload.photo_links)
    all_photo_sources = [*saved_photo_paths, *photo_links]

    dish = Dish(
        name=payload.name,
        photo_path=all_photo_sources[0] if all_photo_sources else None,
        description=payload.description or "",
        category=payload.category,
        portion_size_grams=payload.portion_size_grams,
        calories=payload.calories,
        protein=payload.protein,
        fat=payload.fat,
        carbs=payload.carbs,
        is_vegan=final_vegan,
        is_gluten_free=final_gluten_free,
        is_sugar_free=final_sugar_free,
    )
    for item in payload.ingredients:
        dish.ingredients.append(
            DishIngredient(product_id=item.product_id, quantity_grams=item.quantity_grams)
        )
    for index, file_path in enumerate(all_photo_sources):
        dish.photos.append(DishPhoto(file_path=file_path, position=index))

    db.add(dish)
    db.commit()

    created = get_dish(db, dish.id)
    if created is None:
        raise HTTPException(status_code=500, detail="Блюдо не было создано")
    return dish_payload(created)


@router.get("/{dish_id}", response_model=DishRead)
def get_dish_by_id(dish_id: int, db: Session = Depends(get_db)):
    dish = get_dish(db, dish_id)
    if dish is None:
        raise HTTPException(status_code=404, detail="Блюдо не найдено")
    return dish_payload(dish)


@router.patch("/{dish_id}", response_model=DishRead)
async def update_dish(dish_id: int, request: Request, db: Session = Depends(get_db)):
    dish = get_dish(db, dish_id)
    if dish is None:
        raise HTTPException(status_code=404, detail="Блюдо не найдено")

    content_type = request.headers.get("content-type", "")
    uploaded_files: list[UploadFile] = []
    if content_type.startswith("application/json"):
        try:
            raw_payload = await request.json()
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Некорректное тело JSON-запроса") from exc
        request_payload = parse_dish_update_payload(raw_payload) or DishUpdate()
    else:
        form_data = await request.form()
        request_payload = dish_update_from_form_data(form_data) or DishUpdate()
        uploaded_files = validate_image_uploads(uploaded_files_from_form(form_data, "photos"))
        if not uploaded_files:
            uploaded_files = validate_image_uploads(uploaded_files_from_form(form_data, "photo"))

    new_photo_paths = save_uploads(uploaded_files)

    update_data = request_payload.dict(exclude_unset=True, exclude={"ingredients", "photo_links"})
    if "name" in update_data:
        resolved_name, resolved_category = resolve_dish_name_and_category(
            update_data["name"],
            update_data.get("category"),
            fallback_category=dish.category,
        )
        update_data["name"] = resolved_name
        update_data["category"] = resolved_category
    elif "category" in update_data:
        update_data["category"] = normalize_whitespace(update_data["category"] or dish.category)

    ingredients_payload = request_payload.ingredients if "ingredients" in request_payload.__fields_set__ else None
    effective_ingredients = ingredients_payload or [
        DishIngredientInput(product_id=item.product_id, quantity_grams=item.quantity_grams) for item in dish.ingredients
    ]
    effective_portion_size = float(update_data.get("portion_size_grams", dish.portion_size_grams))
    product_map = load_products_map(db, effective_ingredients)
    draft = calculate_draft(
        [(product_nutrition_snapshot(product_map[item.product_id]), item.quantity_grams) for item in effective_ingredients],
        target_portion_grams=effective_portion_size
    )

    merged = {
        "name": update_data.get("name", dish.name),
        "description": update_data.get("description", dish.description),
        "category": update_data.get("category", dish.category),
        "portion_size_grams": effective_portion_size,
        "calories": update_data.get("calories", dish.calories),
        "protein": update_data.get("protein", dish.protein),
        "fat": update_data.get("fat", dish.fat),
        "carbs": update_data.get("carbs", dish.carbs),
        "is_vegan": update_data.get("is_vegan", dish.is_vegan),
        "is_gluten_free": update_data.get("is_gluten_free", dish.is_gluten_free),
        "is_sugar_free": update_data.get("is_sugar_free", dish.is_sugar_free),
        "ingredients": effective_ingredients,
    }
    try:
        merged_payload = DishCreate.parse_obj(merged)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc
    final_vegan, final_gluten_free, final_sugar_free = get_allowed_flags_subset(
        merged_payload.is_vegan, merged_payload.is_gluten_free, merged_payload.is_sugar_free, draft["allowed_flags"]
    )
    update_data["is_vegan"] = final_vegan
    update_data["is_gluten_free"] = final_gluten_free
    update_data["is_sugar_free"] = final_sugar_free

    if update_data:
        for field, value in update_data.items():
            if field == "description":
                setattr(dish, field, value or "")
            else:
                setattr(dish, field, value)
    if ingredients_payload is not None:
        dish.ingredients.clear()
        for item in ingredients_payload:
            dish.ingredients.append(
                DishIngredient(product_id=item.product_id, quantity_grams=item.quantity_grams)
            )
    photo_links_provided = "photo_links" in request_payload.__fields_set__
    if photo_links_provided or new_photo_paths:
        photo_links = normalize_dish_photo_links(request_payload.photo_links if photo_links_provided else None)
        if photo_links_provided:
            all_photo_sources = [*new_photo_paths, *photo_links]
        else:
            existing_paths = [photo.file_path for photo in dish.photos]
            all_photo_sources = [*new_photo_paths, *existing_paths]

        dish.photo_path = all_photo_sources[0] if all_photo_sources else None
        dish.photos.clear()
        for index, file_path in enumerate(all_photo_sources):
            dish.photos.append(DishPhoto(file_path=file_path, position=index))

    if update_data or ingredients_payload is not None or new_photo_paths:
        db.commit()

    updated = get_dish(db, dish_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Блюдо не найдено")
    return dish_payload(updated)


@router.delete("/{dish_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dish(dish_id: int, db: Session = Depends(get_db)):
    dish = db.get(Dish, dish_id)
    if dish is None:
        raise HTTPException(status_code=404, detail="Блюдо не найдено")

    db.delete(dish)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
