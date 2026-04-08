from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Displaced People Camp Manager"
    API_V1_STR: str = "/api/v1"

    SQLALCHEMY_DATABASE_URI: str = f"sqlite:///./camp_manager.db"

    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    class Config:
        case_sensitive = True

settings = Settings()