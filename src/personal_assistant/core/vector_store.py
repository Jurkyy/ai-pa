from typing import List, Dict, Any, Type, Optional, Iterable
from langchain.vectorstores.base import VectorStore
from langchain.schema import Document
from langchain.embeddings.base import Embeddings
from sqlalchemy import text
from sqlalchemy.orm import Session
from personal_assistant.db.session import SessionLocal
from langchain.embeddings import OpenAIEmbeddings

class PostgreSQLVectorStore(VectorStore):
    """Vector store implementation using PostgreSQL with pgvector."""
    
    def __init__(self, db: Session, embedding_function: Embeddings):
        """Initialize the PostgreSQL vector store.
        
        Args:
            db: SQLAlchemy session
            embedding_function: Function to generate embeddings for documents
        """
        self.db = db
        self.embedding_function = embedding_function
        
    def add_texts(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[str]:
        """Add texts to the vector store.
        
        Args:
            texts: List of texts to add
            metadatas: List of metadata dicts for each text
            **kwargs: Additional arguments
            
        Returns:
            List of document IDs
        """
        if metadatas is None:
            metadatas = [{} for _ in texts]
            
        embeddings = self.embedding_function.embed_documents(texts)
        document_ids = []
        
        try:
            for i, (text_content, embedding, metadata) in enumerate(zip(texts, embeddings, metadatas)):
                # Generate a unique document ID (Consider using UUID)
                doc_id = f"doc_{metadata.get('source', 'unknown')}_{i}" # Improved ID generation
                
                # Insert into database using the session
                self.db.execute(
                    text("""
                        INSERT INTO document_embeddings
                        (document_id, content, embedding, metadata)
                        VALUES (:doc_id, :content, CAST(:embedding AS vector), :metadata::jsonb)
                        ON CONFLICT (document_id) DO UPDATE SET
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        metadata = EXCLUDED.metadata;
                    """),
                    {
                        "doc_id": doc_id,
                        "content": text_content,
                        "embedding": embedding, # Send as list
                        "metadata": metadata # Send as dict, cast happens in SQL
                    }
                )
                document_ids.append(doc_id)
            
            self.db.commit() # Commit is handled by the session manager usually, but might be needed here depending on usage context
        except Exception as e: # Catch exceptions and rollback
            self.db.rollback()
            raise e
            
        return document_ids
    
    def similarity_search(
        self, query: str, k: int = 4, **kwargs: Any
    ) -> List[Document]:
        """Search for similar documents.
        
        Args:
            query: Query text
            k: Number of results to return
            **kwargs: Additional arguments
            
        Returns:
            List of similar documents
        """
        query_embedding = self.embedding_function.embed_query(query)
        
        try:
            results = self.db.execute(
                text("""
                    SELECT content, metadata,
                           embedding <=> CAST(:query_embedding AS vector) as distance
                    FROM document_embeddings
                    ORDER BY distance
                    LIMIT :k
                """),
                {
                    "query_embedding": query_embedding, # Send as list
                    "k": k
                }
            ).fetchall()
        except Exception as e:
             self.db.rollback()
             raise e
            
        return [
            Document(
                page_content=row[0],
                metadata=row[1]
            )
            for row in results
        ]
    
    def delete(self, document_ids: List[str], **kwargs: Any) -> bool:
        """Delete documents from the vector store.
        
        Args:
            document_ids: List of document IDs to delete
            **kwargs: Additional arguments
            
        Returns:
            True if successful
        """
        try:
            self.db.execute(
                text("""
                    DELETE FROM document_embeddings
                    WHERE document_id = ANY(:doc_ids)
                """),
                {"doc_ids": document_ids}
            )
            self.db.commit() # Commit might be needed here
        except Exception as e:
            self.db.rollback()
            raise e
        return True

    @classmethod
    def from_texts(
        cls: Type["PostgreSQLVectorStore"],
        texts: List[str],
        embedding: Embeddings,
        metadatas: Optional[List[dict]] = None,
        **kwargs: Any,
    ) -> "PostgreSQLVectorStore":
        """Create a PostgreSQLVectorStore instance and add texts.
           NOTE: This method now requires a db session passed via kwargs or needs refactoring
           if used outside a request context.
        """
        # Requires db session, how to handle this? Pass via kwargs?
        if 'db' not in kwargs:
             raise ValueError("Database session ('db') must be provided in kwargs for from_texts")
        db_session = kwargs.pop('db')
        vector_store = cls(db=db_session, embedding_function=embedding)
        vector_store.add_texts(texts=texts, metadatas=metadatas, **kwargs)
        return vector_store

# Remove global initialization
# embeddings = OpenAIEmbeddings()
# vector_store = PostgreSQLVectorStore(embeddings)
#
# # Add documents
# vector_store.add_texts(["Your document text here"])
#
# # Search for similar documents
# results = vector_store.similarity_search("Your query here") 