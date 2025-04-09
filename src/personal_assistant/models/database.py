from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from ..db.base import Base

class DocumentEmbedding(Base):
    """Model for document embeddings."""
    __tablename__ = "document_embeddings"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column("vector", nullable=False)  # pgvector type
    metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class Conversation(Base):
    """Model for conversation history."""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class UserSettings(Base):
    """Model for user settings."""
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, unique=True)
    settings = Column(JSONB, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow) 