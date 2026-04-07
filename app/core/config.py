from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Displaced People Camp Manager"
    API_V1_STR: str = "/api/v1"

    SQLALCHEMY_DATABASE_URI: str = f"sqlite:///./camp_manager.db"

    class Config:
        case_sensitive = True

settings = Settings()