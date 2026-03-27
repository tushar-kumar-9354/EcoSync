from pydantic_settings import BaseSettings
from typing import Optional, List, Union
import json


class Settings(BaseSettings):
    app_name: str = "EcoSync API"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    cors_origins: Union[str, List[str]] = "*"  # Accept both string and list
    simulation_update_interval: int = 15  # seconds

    class Config:
        env_file = ".env"
        extra = "allow"

    def get_cors_origins(self) -> List[str]:
        if isinstance(self.cors_origins, list):
            return self.cors_origins
        if self.cors_origins == "*":
            return ["*"]
        # If it's a comma-separated string
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()