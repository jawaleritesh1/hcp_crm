from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "HCP Log Interaction CRM"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/hcpcrm"
    
    # LLM Integration
    GROQ_API_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
