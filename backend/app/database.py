import sqlite3
from collections.abc import Generator

from app.config import DB_PATH


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    with _connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                photo_path TEXT,
                calories REAL NOT NULL,
                protein REAL NOT NULL,
                fat REAL NOT NULL,
                carbs REAL NOT NULL,
                composition TEXT NOT NULL,
                category TEXT NOT NULL,
                requires_cooking INTEGER NOT NULL DEFAULT 0,
                is_vegan INTEGER NOT NULL DEFAULT 0,
                is_gluten_free INTEGER NOT NULL DEFAULT 0,
                is_sugar_free INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS dishes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                photo_path TEXT,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                servings INTEGER NOT NULL,
                calories REAL NOT NULL,
                protein REAL NOT NULL,
                fat REAL NOT NULL,
                carbs REAL NOT NULL,
                is_vegan INTEGER NOT NULL DEFAULT 0,
                is_gluten_free INTEGER NOT NULL DEFAULT 0,
                is_sugar_free INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS dish_ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dish_id INTEGER NOT NULL REFERENCES dishes(id) ON DELETE CASCADE,
                product_id INTEGER NOT NULL REFERENCES products(id),
                quantity_grams REAL NOT NULL
            );
            """
        )


def get_db() -> Generator[sqlite3.Connection, None, None]:
    connection = _connect()
    try:
        yield connection
    finally:
        connection.close()
