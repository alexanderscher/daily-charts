from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

db_password = os.getenv("DB_PASSWORD")

DATABASE_URL = f"postgresql+psycopg2://postgres:{db_password}@l2tk.cnk48k6ist5w.us-east-1.rds.amazonaws.com:5432/l2tk"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
