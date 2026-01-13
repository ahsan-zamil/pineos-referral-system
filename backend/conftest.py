"""
Pytest configuration and fixtures for testing.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import uuid

from database import Base
from main import app
from database import get_db
from config import settings


# Use separate test database
TEST_DATABASE_URL = "postgresql://pineos:pineos_password@localhost:5432/pineos_referral_test"

# Create test engine
engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database session override."""
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
def idempotency_key():
    """Generate a unique idempotency key for each test."""
    return str(uuid.uuid4())


@pytest.fixture
def second_idempotency_key():
    """Generate a second unique idempotency key."""
    return str(uuid.uuid4())
