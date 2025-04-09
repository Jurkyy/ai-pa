from sqlalchemy import text
# Import engine from session
from .session import engine, SessionLocal
# Import Base from the new central location
from .base import Base
# Import models to ensure they are registered with Base
# Assuming User model exists
from ..models.database import DocumentEmbedding, Conversation, UserSettings # Import all models from database.py

def init_db() -> None:
    """Initialize the database: create tables and vector extension."""
    # Create all tables defined in models that inherit from Base
    Base.metadata.create_all(bind=engine)
    
    # Create vector extension if it doesn't exist
    db = SessionLocal()
    try:
        db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        db.commit()
    finally:
        db.close() 