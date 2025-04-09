import os
from dotenv import load_dotenv
import shutil
from pathlib import Path

# Explicitly load .env file BEFORE other imports that might need env vars
load_dotenv()

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List, Dict, Any
from pydantic import BaseModel

# Use the new vector store
from personal_assistant.core.vector_store import PostgreSQLVectorStore
from langchain.embeddings import OpenAIEmbeddings
from personal_assistant.core.security import get_current_user
from personal_assistant.core.config import settings
# Import Session and get_db
from sqlalchemy.orm import Session
from personal_assistant.db.session import get_db

# Langchain imports for document loading and splitting
from langchain_community.document_loaders import UnstructuredFileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Initialize embeddings (ensure OPENAI_API_KEY is in .env)
# We now expect load_dotenv() to have loaded it, but we still check settings
if not settings.OPENAI_API_KEY:
    # Check os.getenv as a fallback, though settings should work
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set in the environment variables or .env file.")
    # If found via os.getenv, maybe log a warning that settings didn't pick it up?
    # This case shouldn't ideally happen if Settings is configured correctly.

router = APIRouter()

class DirectoryRequest(BaseModel):
    directory_path: str

class TextRequest(BaseModel):
    text: str
    metadata: Dict[str, Any] = {}

class TextsRequest(BaseModel):
    texts: List[str]
    metadatas: List[Dict[str, Any]] = None

class QueryRequest(BaseModel):
    query: str
    k: int = 4

class QueryResponse(BaseModel):
    results: List[Dict[str, Any]]

@router.post("/query", response_model=QueryResponse)
async def query_rag(
    request: QueryRequest,
    db: Session = Depends(get_db),  # Inject db session
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Query the RAG system"""
    try:
        # Initialize embeddings and vector_store within the request
        if not settings.OPENAI_API_KEY:
             raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
        embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
        vector_store = PostgreSQLVectorStore(db=db, embedding_function=embeddings)

        results = vector_store.similarity_search(
            query=request.query,
            k=request.k
        )
        # Format results for response
        formatted_results = [
            {"content": doc.page_content, "metadata": doc.metadata}
            for doc in results
        ]
        return QueryResponse(results=formatted_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during query: {e}")

@router.post("/add_text")
async def add_text_to_rag(
    request: TextRequest, # Use Pydantic model for request body
    db: Session = Depends(get_db), # Inject db session
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Add a single text snippet to the RAG system"""
    try:
        # Initialize embeddings and vector_store within the request
        if not settings.OPENAI_API_KEY:
             raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
        embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
        vector_store = PostgreSQLVectorStore(db=db, embedding_function=embeddings)

        document_ids = vector_store.add_texts([request.text], [request.metadata])
        return {"status": "success", "document_ids": document_ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding text: {e}")

@router.post("/add_texts")
async def add_texts_to_rag(
    request: TextsRequest, # Use Pydantic model for request body
    db: Session = Depends(get_db), # Inject db session
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Add multiple text snippets to the RAG system"""
    if request.metadatas and len(request.texts) != len(request.metadatas):
        raise HTTPException(status_code=400, detail="Number of texts and metadatas must match")
    try:
        # Initialize embeddings and vector_store within the request
        if not settings.OPENAI_API_KEY:
             raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
        embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
        vector_store = PostgreSQLVectorStore(db=db, embedding_function=embeddings)

        document_ids = vector_store.add_texts(request.texts, request.metadatas)
        return {"status": "success", "document_ids": document_ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding texts: {e}")

@router.post("/add-directory")
async def add_directory(
    request: DirectoryRequest, # Use Pydantic model
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Load, process, and add all supported files from a directory to the RAG database."""
    directory_path = Path(request.directory_path)
    if not directory_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Directory not found: {request.directory_path}")

    processed_files = 0
    total_chunks_added = 0
    errors = []

    try:
        # Initialize Embeddings and Vector Store once for the whole directory
        if not settings.OPENAI_API_KEY:
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
        embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
        vector_store = PostgreSQLVectorStore(db=db, embedding_function=embeddings)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)

        # Iterate through all files in the directory
        for file_path in directory_path.rglob('*'):
            if file_path.is_file():
                file_name = file_path.name
                print(f"Processing file: {file_name}") # Log which file is being processed
                try:
                    # 1. Load the document
                    loader = UnstructuredFileLoader(str(file_path))
                    docs = loader.load()

                    if not docs:
                        errors.append(f"Could not load content from file: {file_name}")
                        continue # Skip to next file

                    # 2. Split the document into chunks
                    split_docs = text_splitter.split_documents(docs)

                    if not split_docs:
                        errors.append(f"Could not split document into chunks: {file_name}")
                        continue # Skip to next file

                    # 3. Prepare texts and metadatas
                    texts = [doc.page_content for doc in split_docs]
                    metadatas = [doc.metadata for doc in split_docs]
                    for meta in metadatas:
                        meta['source'] = file_name # Add source filename

                    # 4. Add texts to the vector store
                    document_ids = vector_store.add_texts(texts=texts, metadatas=metadatas)
                    
                    processed_files += 1
                    total_chunks_added += len(texts)

                except Exception as e:
                    error_message = f"Error processing file {file_name}: {str(e)}"
                    print(error_message) # Log the error
                    errors.append(error_message)
                    # Decide if we should rollback changes for this file? 
                    # The current vector_store implementation commits per add_texts call.
                    # If a full directory rollback is desired on any file error, 
                    # collect all texts/metadatas first, then add them all at once.
                    # For now, we just log the error and continue.
    
        return {
            "status": "completed",
            "message": f"Processed {processed_files} files from directory '{request.directory_path}'.",
            "total_chunks_added": total_chunks_added,
            "errors": errors
        }

    except HTTPException as http_exc:
         # Re-raise HTTPExceptions that occur outside the file loop (e.g., API key error)
         raise http_exc
    except Exception as e:
        # General errors during setup or iteration
        print(f"Error processing directory {request.directory_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing directory {request.directory_path}: {str(e)}")

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Upload, process, and add a single file to the RAG database."""
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename
    processed = False # Flag to check if processing was successful before final return

    try:
        # 1. Save the uploaded file temporarily
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 2. Load the document using Unstructured
        loader = UnstructuredFileLoader(str(file_path))
        docs = loader.load()

        if not docs:
            raise HTTPException(status_code=400, detail=f"Could not load content from file: {file.filename}")

        # 3. Split the document into chunks
        # Adjust chunk_size and chunk_overlap as needed
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        split_docs = text_splitter.split_documents(docs)

        if not split_docs:
            raise HTTPException(status_code=400, detail=f"Could not split document into chunks: {file.filename}")

        # Prepare texts and metadatas for vector store
        texts = [doc.page_content for doc in split_docs]
        # Add original filename to metadata for each chunk
        metadatas = [doc.metadata for doc in split_docs]
        for meta in metadatas:
            meta['source'] = file.filename # Ensure source is tracked

        # 4. Initialize Embeddings and Vector Store
        if not settings.OPENAI_API_KEY:
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
        embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
        vector_store = PostgreSQLVectorStore(db=db, embedding_function=embeddings)

        # 5. Add texts to the vector store
        document_ids = vector_store.add_texts(texts=texts, metadatas=metadatas)
        processed = True # Mark as processed successfully

        return {
            "status": "success",
            "message": f"File '{file.filename}' processed and added successfully.",
            "document_ids": document_ids,
            "chunks_added": len(texts)
            }

    except HTTPException as http_exc:
         # Re-raise HTTPExceptions directly
         raise http_exc
    except Exception as e:
        # Log the error for debugging
        print(f"Error processing file {file.filename}: {e}")
        # Raise a generic server error for other exceptions
        raise HTTPException(status_code=500, detail=f"Error processing file {file.filename}: {str(e)}")
    finally:
        # 6. Clean up the temporarily saved file
        if file_path.exists():
            file_path.unlink()
