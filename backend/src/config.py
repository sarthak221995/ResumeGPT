from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    APP_NAME: str = "ResumeForge"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    CORS_ORIGINS: List[str] = ["http://localhost", "http://localhost:3000", "https://resumegpt-frontend.vercel.app","https://merit-ai-zeta.vercel.app"]

    # AZURE OPENAI SETTINGS
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_VERSION: str = "2025-01-01-preview"
    
    # Deployments
    DEPLOYMENT_GPT_4O: str = "gpt-4o"
    DEPLOYMENT_GPT_4_1: str = "gpt-4.1"
    DEPLOYMENT_GPT_4O_MINI: str = "gpt-4o-mini"
    
    # Token limits
    MAX_TOKENS_FOR_MODIFY: int = 16000  

    # AUTH
    CLERK_JWKS_URL: str
   
    class Config:
        env_file = ".env"
        extra = "ignore" # Ignore extra env vars

settings = Settings()