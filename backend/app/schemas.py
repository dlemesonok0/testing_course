from datetime import datetime

from pydantic import BaseModel, Field, validator


FLAG_NAMES = {"vegan", "gluten_free", "sugar_free"}
PRODUCT_SORT_FIELDS = {"name", "calories", "protein", "fat", "carbs", "created_at"}
DISH_SORT_FIELDS = {"name", "calories", "protein", "fat", "carbs", "created_at"}


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    calories: float = Field(ge=0)
    protein: float = Field(ge=0)
    fat: float = Field(ge=0)
    carbs: float = Field(ge=0)
    composition: str = Field(min_length=1)
    category: str = Field(min_length=1, max_length=120)
    requires_cooking: bool = False
    is_vegan: bool = False
    is_gluten_free: bool = False
    is_sugar_free: bool = False


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    calories: float | None = Field(default=None, ge=0)
    protein: float | None = Field(default=None, ge=0)
    fat: float | None = Field(default=None, ge=0)
    carbs: float | None = Field(default=None, ge=0)
    composition: str | None = Field(default=None, min_length=1)
    category: str | None = Field(default=None, min_length=1, max_length=120)
    requires_cooking: bool | None = None
    is_vegan: bool | None = None
    is_gluten_free: bool | None = None
    is_sugar_free: bool | None = None


class ProductRead(ProductBase):
    id: int
    photo_url: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class DishIngredientInput(BaseModel):
    product_id: int
    quantity_grams: float = Field(gt=0)


class DishBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    category: str = Field(min_length=1, max_length=120)
    servings: int = Field(gt=0)
    calories: float = Field(ge=0)
    protein: float = Field(ge=0)
    fat: float = Field(ge=0)
    carbs: float = Field(ge=0)
    is_vegan: bool = False
    is_gluten_free: bool = False
    is_sugar_free: bool = False
    ingredients: list[DishIngredientInput] = Field(min_items=1)


class DishCreate(DishBase):
    pass


class DishUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    category: str | None = Field(default=None, min_length=1, max_length=120)
    servings: int | None = Field(default=None, gt=0)
    calories: float | None = Field(default=None, ge=0)
    protein: float | None = Field(default=None, ge=0)
    fat: float | None = Field(default=None, ge=0)
    carbs: float | None = Field(default=None, ge=0)
    is_vegan: bool | None = None
    is_gluten_free: bool | None = None
    is_sugar_free: bool | None = None
    ingredients: list[DishIngredientInput] | None = Field(default=None, min_items=1)


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
    description: str
    category: str
    servings: int
    calories: float
    protein: float
    fat: float
    carbs: float
    is_vegan: bool
    is_gluten_free: bool
    is_sugar_free: bool
    photo_url: str | None
    created_at: datetime
    updated_at: datetime
    ingredients: list[DishIngredientRead]
    allowed_flags: list[str]


class SearchParams(BaseModel):
    search: str | None = None
    category: str | None = None
    requires_cooking: bool | None = None
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

    @validator("sort_order")
    def validate_sort_order(cls, value: str) -> str:
        if value not in {"asc", "desc"}:
            raise ValueError("sort_order must be asc or desc")
        return value
