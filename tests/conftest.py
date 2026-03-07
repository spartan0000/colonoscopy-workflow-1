import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.db.session import Base, get_db

from app.main import app
from fastapi.testclient import TestClient

from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine)

@pytest.fixture(scope="session")
def db_session():
    """create a new database session for testing, then rollback at the end"""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session #test runs here

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    """override the get_db dependency to use the testing database session"""
    from app.db.session import get_db
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client_no_db():
    """client fixture that does not override the db dependency, for tests that do not require db writes"""
    def fake_db():
        yield None
    app.dependency_overrides[get_db] = fake_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()