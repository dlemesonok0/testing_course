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
    description: str | None = Form(default=None),
    category: str = Form(""),
    portion_size_grams: float = Form(...),
    calories: float = Form(...),
    protein: float = Form(...),
    fat: float = Form(...),
    carbs: float = Form(...),
    is_vegan: bool = Form(False),
    is_gluten_free: bool = Form(False),
    is_sugar_free: bool = Form(False),
    ingredients: str = Form(...),
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
            payload[field] = form_data[field]

    if "ingredients" in form_data:
        payload["ingredients"] = parse_ingredients(str(form_data["ingredients"]))

    return parse_dish_update_payload(payload)


def uploaded_files_from_form(form_data, field_name: str) -> list[UploadFile]:
    return [item for item in form_data.getlist(field_name) if getattr(item, "filename", None)]


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
        [(product_nutrition_snapshot(item.product), item.quantity_grams) for item in dish.ingredients]
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
def nutrition_draft(ingredients: str = Query(...), db: Session = Depends(get_db)):
    parsed = parse_ingredients(ingredients)
    product_map = load_products_map(db, parsed)
    return calculate_draft(
        [(product_nutrition_snapshot(product_map[item.product_id]), item.quantity_grams) for item in parsed]
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
        raise HTTPException(status_code=400, detail="Unsupported sort field")

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
        [(product_nutrition_snapshot(product_map[item.product_id]), item.quantity_grams) for item in payload.ingredients]
    )
    validate_requested_flags(payload, draft["allowed_flags"])
    uploaded_files = validate_image_uploads(photos)
    if not uploaded_files and photo is not None and photo.filename:
        uploaded_files = validate_image_uploads([photo])
    saved_photo_paths = save_uploads(uploaded_files)

    dish = Dish(
        name=payload.name,
        photo_path=saved_photo_paths[0] if saved_photo_paths else None,
        description=payload.description or "",
        category=payload.category,
        portion_size_grams=payload.portion_size_grams,
        calories=payload.calories,
        protein=payload.protein,
        fat=payload.fat,
        carbs=payload.carbs,
        is_vegan=payload.is_vegan,
        is_gluten_free=payload.is_gluten_free,
        is_sugar_free=payload.is_sugar_free,
    )
    for item in payload.ingredients:
        dish.ingredients.append(
            DishIngredient(product_id=item.product_id, quantity_grams=item.quantity_grams)
        )
    for index, file_path in enumerate(saved_photo_paths):
        dish.photos.append(DishPhoto(file_path=file_path, position=index))

    db.add(dish)
    db.commit()

    created = get_dish(db, dish.id)
    if created is None:
        raise HTTPException(status_code=500, detail="Dish was not created")
    return dish_payload(created)


@router.get("/{dish_id}", response_model=DishRead)
def get_dish_by_id(dish_id: int, db: Session = Depends(get_db)):
    dish = get_dish(db, dish_id)
    if dish is None:
        raise HTTPException(status_code=404, detail="Dish not found")
    return dish_payload(dish)


@router.patch("/{dish_id}", response_model=DishRead)
async def update_dish(dish_id: int, request: Request, db: Session = Depends(get_db)):
    dish = get_dish(db, dish_id)
    if dish is None:
        raise HTTPException(status_code=404, detail="Dish not found")

    content_type = request.headers.get("content-type", "")
    uploaded_files: list[UploadFile] = []
    if content_type.startswith("application/json"):
        try:
            raw_payload = await request.json()
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON body") from exc
        request_payload = parse_dish_update_payload(raw_payload) or DishUpdate()
    else:
        form_data = await request.form()
        request_payload = dish_update_from_form_data(form_data) or DishUpdate()
        uploaded_files = validate_image_uploads(uploaded_files_from_form(form_data, "photos"))
        if not uploaded_files:
            uploaded_files = validate_image_uploads(uploaded_files_from_form(form_data, "photo"))

    new_photo_paths = save_uploads(uploaded_files)

    update_data = request_payload.dict(exclude_unset=True, exclude={"ingredients"})
    if "name" in update_data:
        resolved_name, resolved_category = resolve_dish_name_and_category(
            update_data["name"],
            update_data.get("category"),
            fallback_category=dish.category if "category" not in update_data else None,
        )
        update_data["name"] = resolved_name
        if resolved_category is not None:
            update_data["category"] = resolved_category
    elif "category" in update_data:
        update_data["category"] = normalize_whitespace(update_data["category"])

    ingredients_payload = request_payload.ingredients if "ingredients" in request_payload.__fields_set__ else None
    effective_ingredients = ingredients_payload or [
        DishIngredientInput(product_id=item.product_id, quantity_grams=item.quantity_grams) for item in dish.ingredients
    ]
    product_map = load_products_map(db, effective_ingredients)
    draft = calculate_draft(
        [(product_nutrition_snapshot(product_map[item.product_id]), item.quantity_grams) for item in effective_ingredients]
    )

    merged = {
        "name": update_data.get("name", dish.name),
        "description": update_data.get("description", dish.description),
        "category": update_data.get("category", dish.category),
        "portion_size_grams": update_data.get("portion_size_grams", dish.portion_size_grams),
        "calories": update_data.get("calories", dish.calories),
        "protein": update_data.get("protein", dish.protein),
        "fat": update_data.get("fat", dish.fat),
        "carbs": update_data.get("carbs", dish.carbs),
        "is_vegan": update_data.get("is_vegan", dish.is_vegan),
        "is_gluten_free": update_data.get("is_gluten_free", dish.is_gluten_free),
        "is_sugar_free": update_data.get("is_sugar_free", dish.is_sugar_free),
        "ingredients": effective_ingredients,
    }
    validate_requested_flags(DishCreate.parse_obj(merged), draft["allowed_flags"])

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
    if new_photo_paths:
        dish.photo_path = new_photo_paths[0]
        dish.photos.clear()
        for index, file_path in enumerate(new_photo_paths):
            dish.photos.append(DishPhoto(file_path=file_path, position=index))

    if update_data or ingredients_payload is not None or new_photo_paths:
        db.commit()

    updated = get_dish(db, dish_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Dish not found")
    return dish_payload(updated)


@router.delete("/{dish_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dish(dish_id: int, db: Session = Depends(get_db)):
    dish = db.get(Dish, dish_id)
    if dish is None:
        raise HTTPException(status_code=404, detail="Dish not found")

    db.delete(dish)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
