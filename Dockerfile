# Use an official Python runtime as a parent image
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# Poetry specific environment variables
ENV POETRY_VERSION=2.1.2 # Pin poetry version for consistency
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_VIRTUALENVS_CREATE=false # Don't create virtualenvs inside the container
ENV PATH="$POETRY_HOME/bin:$PATH"

# Install system dependencies (if any - e.g., tesseract if needed later)
# RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Set the working directory in the container
WORKDIR /app

# Copy only files necessary for dependency installation
COPY pyproject.toml poetry.lock ./

# Install project dependencies
# Use --no-root to skip installing the project itself initially
# Use --no-dev to skip development dependencies
RUN poetry install --no-interaction --no-ansi --no-dev

# Download NLTK data *after* dependencies are installed
# Add other packages here if needed (e.g., 'wordnet', 'stopwords')
RUN python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('punkt_tab', quiet=True)"

# Copy the rest of the application source code
COPY ./src ./src

# Expose the port the app runs on
EXPOSE 8000

# Define the command to run the application
# Use the specific host 0.0.0.0 to accept connections from outside the container
CMD ["poetry", "run", "uvicorn", "personal_assistant.main:app", "--host", "0.0.0.0", "--port", "8000"] 
