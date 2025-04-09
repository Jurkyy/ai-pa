import nltk
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from personal_assistant.core.config import settings
from personal_assistant.api.v1.api import api_router

# --- NLTK Data Check ---
def ensure_nltk_data(packages: list):
    """Checks if NLTK packages are downloaded, and downloads them if missing."""
    try:
        # Use the first path in nltk.data.path, usually the default user location
        nltk_data_path = nltk.data.path[0]
        # Ensure the root NLTK data directory exists
        os.makedirs(nltk_data_path, exist_ok=True)
        print(f"Ensuring NLTK data in: {nltk_data_path}")

        for package_id in packages:
            try:
                # Attempt to find the package
                # Example: find 'tokenizers/punkt' or 'corpora/wordnet'
                # Adjust the resource type ('tokenizers', 'corpora', etc.) if needed
                if package_id == 'punkt' or package_id == 'punkt_tab': # punkt is under 'tokenizers'
                     resource_path = f'tokenizers/{package_id}'
                else:
                     # Add more cases or a default guess (e.g., 'corpora/') if necessary
                     resource_path = f'corpora/{package_id}' # Default assumption

                nltk.data.find(resource_path)
                print(f"NLTK package '{package_id}' found.")
            except LookupError:
                print(f"NLTK package '{package_id}' not found. Downloading...")
                # Download to the specified path
                nltk.download(package_id, download_dir=nltk_data_path)
                print(f"NLTK package '{package_id}' downloaded.")
    except Exception as e:
        print(f"Error during NLTK data check/download: {e}")
        # Depending on severity, you might want to raise the error or exit
        # raise e

# Ensure required NLTK packages are available at startup
ensure_nltk_data(['punkt', 'punkt_tab'])
# --- End NLTK Data Check ---

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "Welcome to Personal Assistant API"} 