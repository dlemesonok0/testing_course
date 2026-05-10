import pytest
import socket
import threading
import time
from types import SimpleNamespace

import httpx
import uvicorn
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.schemas import DISH_CATEGORIES


@pytest.fixture(scope="session")
def api_server():
    """Run one real uvicorn server for the API integration test session."""

    from app.main import app

    state = SimpleNamespace(session_factory=None)

    def override_get_db():
        if state.session_factory is None:
            raise RuntimeError("Test database session factory is not configured")
        session = state.session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    host = "127.0.0.1"
    port = unused_tcp_port()
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="warning",
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://{host}:{port}"
    wait_for_server(base_url)
    state.base_url = base_url

    try:
        yield state
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        app.dependency_overrides.clear()


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
    """Create an SQLite database for API integration tests."""

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
def client(api_server, test_engine, upload_dir):
    """Run the real FastAPI app against the isolated SQLite test database."""

    api_server.session_factory = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    test_client = httpx.Client(base_url=api_server.base_url)
    try:
        yield test_client
    finally:
        cleanup_api_objects(test_client)
        test_client.close()
        api_server.session_factory = None


def unused_tcp_port() -> int:
    """Reserve a currently unused localhost TCP port for the test server."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_server(base_url: str) -> None:
    """Wait until uvicorn is accepting HTTP connections."""

    deadline = time.monotonic() + 5
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{base_url}/health", timeout=0.2)
            if response.status_code == 200:
                return
        except (httpx.HTTPError, OSError) as exc:
            last_error = exc
        time.sleep(0.05)
    raise RuntimeError("Test server did not start in time") from last_error


def cleanup_api_objects(test_client: httpx.Client) -> None:
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
