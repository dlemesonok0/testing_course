from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()
    dbapi_connection.create_function(
        "unicode_lower",
        1,
        lambda value: value.casefold() if isinstance(value, str) else value,
    )


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        product_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(products)").fetchall()
        }
        if "cooking_state" not in product_columns:
            connection.exec_driver_sql(
                "ALTER TABLE products ADD COLUMN cooking_state VARCHAR(64) NOT NULL DEFAULT 'Готовый к употреблению'"
            )
        if {"requires_cooking", "cooking_state"}.issubset(product_columns | {"cooking_state"}):
            connection.exec_driver_sql(
                """
                UPDATE products
                SET cooking_state = CASE
                    WHEN requires_cooking = 1 THEN 'Требует приготовления'
                    ELSE 'Готовый к употреблению'
                END
                WHERE cooking_state IS NULL OR cooking_state = '' OR cooking_state = 'Готовый к употреблению'
                """
            )

        dish_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(dishes)").fetchall()
        }
        if "portion_size_grams" not in dish_columns:
            connection.exec_driver_sql(
                "ALTER TABLE dishes ADD COLUMN portion_size_grams FLOAT NOT NULL DEFAULT 100.0"
            )
        connection.exec_driver_sql(
            """
            UPDATE dishes
            SET portion_size_grams = 100.0
            WHERE portion_size_grams IS NULL OR portion_size_grams <= 0
            """
        )


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
