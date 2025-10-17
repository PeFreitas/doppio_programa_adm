import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# String de conexão com o banco de dados (usando variáveis de ambiente)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:sua_senha@localhost/doppio_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()