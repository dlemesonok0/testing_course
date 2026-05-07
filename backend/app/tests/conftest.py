import pytest
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.schemas import DISH_CATEGORIES


@pytest.fixture
def nutrition_product_factory():
    """Build product nutrition snapshots used by the automatic dish calculation service."""

    def build_product(**overrides):
        product = {
            "calories": 100.0,
            "protein": 10.0,
            "fat": 5.0,
            "carbs": 20.0,
            "is_vegan": True,
            "is_gluten_free": True,
            "is_sugar_free": True,
        }
        product.update(overrides)
        return product

    return build_product


@pytest.fixture
def nutrition_product_object_factory():
    """Build product-like objects used by router tests before nutrition snapshots are created."""

    def build_product(**overrides):
        product = {
            "calories": 100.0,
            "protein": 10.0,
            "fat": 5.0,
            "carbs": 20.0,
            "is_vegan": True,
            "is_gluten_free": True,
            "is_sugar_free": True,
        }
        product.update(overrides)
        return SimpleNamespace(**product)

    return build_product


@pytest.fixture
def dish_payload_factory():
    """Build raw dish payloads for validating automatic nutrition input boundaries."""

    def build_payload(**overrides):
        payload = {
            "name": "Test dish",
            "description": None,
            "category": DISH_CATEGORIES[0],
            "portion_size_grams": 100.0,
            "calories": 150.0,
            "protein": 30.0,
            "fat": 20.0,
            "carbs": 50.0,
            "is_vegan": False,
            "is_gluten_free": False,
            "is_sugar_free": False,
            "ingredients": [{"product_id": 1, "quantity_grams": 100.0}],
        }
        payload.update(overrides)
        return payload

    return build_payload


@pytest.fixture
def test_engine(tmp_path):
    """Create an isolated SQLite database for API integration tests."""

    database_path = tmp_path / "recipe_book_api_test.db"
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """Provide a real SQLAlchemy session bound to the isolated test database."""

    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def upload_dir(tmp_path, monkeypatch):
    """Route uploaded test files into a temporary directory."""

    directory = tmp_path / "uploads"
    directory.mkdir()
    monkeypatch.setattr("app.config.UPLOAD_DIR", directory)
    monkeypatch.setattr("app.services.files.UPLOAD_DIR", directory)
    return directory


@pytest.fixture
def client(db_session, upload_dir):
    """Run the real FastAPI app against the isolated SQLite test database."""

    from app.main import app

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        cleanup_api_objects(test_client)
        test_client.close()
    app.dependency_overrides.clear()


def cleanup_api_objects(test_client: TestClient) -> None:
    """Delete test data through API routes, preserving the database itself."""

    dishes = test_client.get("/dishes")
    assert dishes.status_code == 200
    for dish in dishes.json():
        response = test_client.delete(f"/dishes/{dish['id']}")
        assert response.status_code in {204, 404}

    products = test_client.get("/products")
    assert products.status_code == 200
    for product in products.json():
        response = test_client.delete(f"/products/{product['id']}")
        assert response.status_code in {204, 404}

    remaining_dishes = test_client.get("/dishes")
    remaining_products = test_client.get("/products")

    assert remaining_dishes.status_code == 200
    assert remaining_products.status_code == 200
    assert remaining_dishes.json() == []
    assert remaining_products.json() == []
