from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "EcoSync API"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "*"
    simulation_update_interval: int = 15  # seconds

    class Config:
        env_file = ".env"
        extra = "allow"

    def get_cors_origins(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",")]

settings = Settings()
