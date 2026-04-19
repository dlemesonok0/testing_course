from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, Field, root_validator, validator


FLAG_NAMES = {"vegan", "gluten_free", "sugar_free"}
MAX_PHOTO_COUNT = 5
PRODUCT_SORT_FIELDS = {"name", "calories", "protein", "fat", "carbs", "created_at"}
DISH_SORT_FIELDS = {"name", "calories", "protein", "fat", "carbs", "created_at"}
PRODUCT_CATEGORIES = (
    "Замороженный",
    "Мясной",
    "Овощи",
    "Зелень",
    "Специи",
    "Крупы",
    "Консервы",
    "Жидкость",
    "Сладости",
)
DISH_CATEGORIES = (
    "Десерт",
    "Первое",
    "Второе",
    "Напиток",
    "Салат",
    "Суп",
    "Перекус",
)
COOKING_STATES = (
    "Готовый к употреблению",
    "Полуфабрикат",
    "Требует приготовления",
)


def normalize_required_text(value: str, field_name: str) -> str:
    normalized = " ".join(value.split())
    if len(normalized) < 2:
        raise ValueError(f"{field_name} must be at least 2 characters long")
    return normalized


def validate_choice(value: str, field_name: str, allowed: tuple[str, ...]) -> str:
    normalized = " ".join(value.split())
    if normalized not in allowed:
        raise ValueError(f"{field_name} must be one of: {', '.join(allowed)}")
    return normalized


class ProductBase(BaseModel):
    name: str = Field(max_length=255)
    calories: float = Field(ge=0)
    protein: float = Field(ge=0, le=100)
    fat: float = Field(ge=0, le=100)
    carbs: float = Field(ge=0, le=100)
    composition: str | None = None
    category: str = Field(max_length=120)
    cooking_state: str = Field(max_length=64)
    is_vegan: bool = False
    is_gluten_free: bool = False
    is_sugar_free: bool = False

    @validator("name")
    def validate_name(cls, value: str) -> str:
        return normalize_required_text(value, "name")

    @validator("composition", pre=True)
    def normalize_composition(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @validator("category")
    def validate_category(cls, value: str) -> str:
        return validate_choice(value, "category", PRODUCT_CATEGORIES)

    @validator("cooking_state")
    def validate_cooking_state(cls, value: str) -> str:
        return validate_choice(value, "cooking_state", COOKING_STATES)

    @root_validator
    def validate_bju_sum(cls, values: dict[str, object]) -> dict[str, object]:
        protein = float(values.get("protein", 0))
        fat = float(values.get("fat", 0))
        carbs = float(values.get("carbs", 0))
        if protein + fat + carbs > 100:
            raise ValueError("protein + fat + carbs must be less than or equal to 100")
        return values


class ProductCreate(ProductBase):
    photo_links: list[AnyHttpUrl] = Field(default_factory=list, max_items=MAX_PHOTO_COUNT)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    calories: float | None = Field(default=None, ge=0)
    protein: float | None = Field(default=None, ge=0, le=100)
    fat: float | None = Field(default=None, ge=0, le=100)
    carbs: float | None = Field(default=None, ge=0, le=100)
    composition: str | None = None
    category: str | None = Field(default=None, max_length=120)
    cooking_state: str | None = Field(default=None, max_length=64)
    is_vegan: bool | None = None
    is_gluten_free: bool | None = None
    is_sugar_free: bool | None = None
    photo_links: list[AnyHttpUrl] | None = Field(default=None, max_items=MAX_PHOTO_COUNT)

    @validator("name")
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_required_text(value, "name")

    @validator("composition", pre=True)
    def normalize_composition(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @validator("category")
    def validate_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_choice(value, "category", PRODUCT_CATEGORIES)

    @validator("cooking_state")
    def validate_cooking_state(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_choice(value, "cooking_state", COOKING_STATES)


class ProductRead(BaseModel):
    id: int
    name: str
    calories: float
    protein: float
    fat: float
    carbs: float
    composition: str | None
    category: str
    cooking_state: str
    is_vegan: bool
    is_gluten_free: bool
    is_sugar_free: bool
    photo_url: str | None
    photo_urls: list[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class DishIngredientInput(BaseModel):
    product_id: int = Field(gt=0)
    quantity_grams: float = Field(gt=0)


class DishBase(BaseModel):
    name: str = Field(max_length=255)
    description: str | None = None
    category: str = Field(max_length=120)
    portion_size_grams: float = Field(gt=0)
    calories: float = Field(ge=0)
    protein: float = Field(ge=0)
    fat: float = Field(ge=0)
    carbs: float = Field(ge=0)
    is_vegan: bool = False
    is_gluten_free: bool = False
    is_sugar_free: bool = False
    ingredients: list[DishIngredientInput] = Field(min_items=1)

    @validator("name")
    def validate_name(cls, value: str) -> str:
        return normalize_required_text(value, "name")

    @validator("description", pre=True)
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @validator("category")
    def validate_category(cls, value: str) -> str:
        return validate_choice(value, "category", DISH_CATEGORIES)

class DishCreate(DishBase):
    pass


class DishUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    category: str | None = Field(default=None, max_length=120)
    portion_size_grams: float | None = Field(default=None, gt=0)
    calories: float | None = Field(default=None, ge=0)
    protein: float | None = Field(default=None, ge=0)
    fat: float | None = Field(default=None, ge=0)
    carbs: float | None = Field(default=None, ge=0)
    is_vegan: bool | None = None
    is_gluten_free: bool | None = None
    is_sugar_free: bool | None = None
    ingredients: list[DishIngredientInput] | None = Field(default=None, min_items=1)

    @validator("name")
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_required_text(value, "name")

    @validator("description", pre=True)
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @validator("category")
    def validate_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_choice(value, "category", DISH_CATEGORIES)


class DishIngredientRead(BaseModel):
    product_id: int
    product_name: str
    quantity_grams: float


class NutritionDraft(BaseModel):
    calories: float
    protein: float
    fat: float
    carbs: float
    allowed_flags: list[str]


class DishRead(BaseModel):
    id: int
    name: str
    description: str | None
    category: str
    portion_size_grams: float
    calories: float
    protein: float
    fat: float
    carbs: float
    is_vegan: bool
    is_gluten_free: bool
    is_sugar_free: bool
    photo_url: str | None
    photo_urls: list[str]
    created_at: datetime
    updated_at: datetime
    ingredients: list[DishIngredientRead]
    allowed_flags: list[str]


class SearchParams(BaseModel):
    search: str | None = None
    category: str | None = None
    cooking_state: str | None = None
    flags: list[str] = Field(default_factory=list)
    sort_by: str = "name"
    sort_order: str = "asc"

    @validator("flags")
    def validate_flags(cls, value: list[str]) -> list[str]:
        normalized = sorted(set(value))
        invalid = [flag for flag in normalized if flag not in FLAG_NAMES]
        if invalid:
            raise ValueError(f"Invalid flags: {', '.join(invalid)}")
        return normalized

    @validator("cooking_state")
    def validate_cooking_state(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_choice(value, "cooking_state", COOKING_STATES)

    @validator("sort_order")
    def validate_sort_order(cls, value: str) -> str:
        if value not in {"asc", "desc"}:
            raise ValueError("sort_order must be asc or desc")
        return value
