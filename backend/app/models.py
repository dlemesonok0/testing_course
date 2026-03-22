from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    calories: Mapped[float] = mapped_column(Float, nullable=False)
    protein: Mapped[float] = mapped_column(Float, nullable=False)
    fat: Mapped[float] = mapped_column(Float, nullable=False)
    carbs: Mapped[float] = mapped_column(Float, nullable=False)
    composition: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    requires_cooking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_vegan: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_gluten_free: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_sugar_free: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    dish_ingredients: Mapped[list["DishIngredient"]] = relationship(back_populates="product")


class Dish(Base):
    __tablename__ = "dishes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    servings: Mapped[int] = mapped_column(Integer, nullable=False)
    calories: Mapped[float] = mapped_column(Float, nullable=False)
    protein: Mapped[float] = mapped_column(Float, nullable=False)
    fat: Mapped[float] = mapped_column(Float, nullable=False)
    carbs: Mapped[float] = mapped_column(Float, nullable=False)
    is_vegan: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_gluten_free: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_sugar_free: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    ingredients: Mapped[list["DishIngredient"]] = relationship(
        back_populates="dish", cascade="all, delete-orphan"
    )


class DishIngredient(Base):
    __tablename__ = "dish_ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dish_id: Mapped[int] = mapped_column(ForeignKey("dishes.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity_grams: Mapped[float] = mapped_column(Float, nullable=False)

    dish: Mapped["Dish"] = relationship(back_populates="ingredients")
    product: Mapped["Product"] = relationship(back_populates="dish_ingredients")
