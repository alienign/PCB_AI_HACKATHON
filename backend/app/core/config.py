from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PCB AI Assistant"

    database_url: str = ""
    storage_path: str = "./storage"
    ml_model_path: str = "./models/best.pt"
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()