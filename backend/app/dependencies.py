from sqlalchemy.orm import Session, sessionmaker

from db.models import engine

# fábrica de sessões
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def iniciar_session():
    """Dependency do FastAPI que abre e fecha a sessão do banco."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
