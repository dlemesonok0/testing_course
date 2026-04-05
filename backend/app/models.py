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
    composition: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    cooking_state: Mapped[str] = mapped_column(String(64), nullable=False, default="Готовый к употреблению")
    is_vegan: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_gluten_free: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_sugar_free: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    dish_ingredients: Mapped[list["DishIngredient"]] = relationship(back_populates="product")
    photos: Mapped[list["ProductPhoto"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductPhoto.position",
    )


class Dish(Base):
    __tablename__ = "dishes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    portion_size_grams: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
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
        back_populates="dish",
        cascade="all, delete-orphan",
        order_by="DishIngredient.id",
    )
    photos: Mapped[list["DishPhoto"]] = relationship(
        back_populates="dish",
        cascade="all, delete-orphan",
        order_by="DishPhoto.position",
    )


class DishIngredient(Base):
    __tablename__ = "dish_ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dish_id: Mapped[int] = mapped_column(ForeignKey("dishes.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity_grams: Mapped[float] = mapped_column(Float, nullable=False)

    dish: Mapped["Dish"] = relationship(back_populates="ingredients")
    product: Mapped["Product"] = relationship(back_populates="dish_ingredients")


class ProductPhoto(Base):
    __tablename__ = "product_photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    product: Mapped["Product"] = relationship(back_populates="photos")


class DishPhoto(Base):
    __tablename__ = "dish_photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dish_id: Mapped[int] = mapped_column(ForeignKey("dishes.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    dish: Mapped["Dish"] = relationship(back_populates="photos")
