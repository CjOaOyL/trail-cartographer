from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    data_dir: Path = Path("./backend/data")

    @property
    def projects_dir(self) -> Path:
        return self.data_dir / "projects"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"


settings = Settings()
settings.projects_dir.mkdir(parents=True, exist_ok=True)
settings.cache_dir.mkdir(parents=True, exist_ok=True)
