import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

engine = create_engine(
    "sqlite:///./database.db",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

base = declarative_base()


def init_db():
    base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()

    try:
        yield db
    except Exception as e:
        logging.error("Error when conecting to database: ", e)
    finally:
        db.close
