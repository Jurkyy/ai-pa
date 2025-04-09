from typing import List, Optional
from pydantic import AnyHttpUrl, validator, EmailStr
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Personal Assistant"
    API_V1_STR: str = "/api/v1"
    
    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database Configuration
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "personal_assistant"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # API Keys, provide these in .env
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # Email Configuration
    EMAIL_IMAP_SERVER: Optional[str] = None
    EMAIL_SMTP_SERVER: Optional[str] = None
    EMAIL_SMTP_PORT: Optional[int] = 587
    EMAIL_ADDRESS: Optional[EmailStr] = None
    EMAIL_PASSWORD: Optional[str] = None

    # Security
    SECRET_KEY: str = "a_very_secret_key_please_change_me" # Default value, should be overridden in .env

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "allow"  # Allow extra fields

settings = Settings() 