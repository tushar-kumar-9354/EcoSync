from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "EcoSync API"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,https://eco-sync-5f1h.vercel.app"
    simulation_update_interval: int = 15  # seconds

    class Config:
        env_file = ".env"
        extra = "allow"

    def get_cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
