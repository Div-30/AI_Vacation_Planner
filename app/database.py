from sqlmodel import Session, create_engine

from app.config import settings

SQLALCHEMY_DATABASE_URL = settings.database_url

engine = create_engine(SQLALCHEMY_DATABASE_URL)

def get_db():
    with Session(engine) as session:
        yield session