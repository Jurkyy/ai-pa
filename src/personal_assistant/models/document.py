from datetime import datetime
from sqlalchemy import Column, Integer, String, Text
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