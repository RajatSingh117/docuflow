import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.user import User, UserRole
from app.services.auth_service import hash_password, create_access_token

# In-memory test SQLite engine
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        # Seed test users
        admin = User(
            name="Test Admin",
            email="admin@test.com",
            password_hash=hash_password("Admin@123"),
            role=UserRole.ADMIN,
            is_active=True
        )
        manager = User(
            name="Test Manager",
            email="manager@test.com",
            password_hash=hash_password("Manager@123"),
            role=UserRole.PROCESSING_MANAGER,
            is_active=True
        )
        viewer = User(
            name="Test Viewer",
            email="viewer@test.com",
            password_hash=hash_password("Viewer@123"),
            role=UserRole.VIEWER,
            is_active=True
        )
        session.add_all([admin, manager, viewer])
        session.commit()
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Test client with overridden database dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_headers(db_session):
    admin = db_session.query(User).filter(User.email == "admin@test.com").first()
    token = create_access_token({"sub": str(admin.id), "role": admin.role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def manager_headers(db_session):
    manager = db_session.query(User).filter(User.email == "manager@test.com").first()
    token = create_access_token({"sub": str(manager.id), "role": manager.role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_headers(db_session):
    viewer = db_session.query(User).filter(User.email == "viewer@test.com").first()
    token = create_access_token({"sub": str(viewer.id), "role": viewer.role.value})
    return {"Authorization": f"Bearer {token}"}
