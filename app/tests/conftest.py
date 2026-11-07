import os

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine

from app import models
from app.main import app
from app.config import settings
from app.database import get_db
from app.oauth2 import get_current_user

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    settings.database_url.replace("/ai_vacation_planner", "/ai_vacation_planner_test")
    if "/ai_vacation_planner" in settings.database_url
    else settings.database_url
)

test_engine = create_engine(TEST_DATABASE_URL)

@pytest.fixture(name="session", scope="function")
def session_fixture():
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session
    SQLModel.metadata.drop_all(test_engine)

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_db_override():
        return session

    test_user = models.User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_pw_test",
        is_active=True,
    )

    def get_current_user_override():
        return test_user

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = get_current_user_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()