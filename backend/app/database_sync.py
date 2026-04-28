from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base

# psycopg3 同时支持同步和异步模式，URL 无需替换
SYNC_DATABASE_URL = settings.DATABASE_URL

engine = create_engine(SYNC_DATABASE_URL, echo=settings.DEBUG)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)