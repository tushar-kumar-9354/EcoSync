from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    app_name: str = "EcoSync API"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    cors_origins: List[str] = ["*"]  # Allow all origins temporarily
    simulation_update_interval: int = 15  # seconds

    class Config:
        env_file = ".env"
        extra = "allow"

    def get_cors_origins(self) -> List[str]:
        return self.cors_origins


settings = Settings()