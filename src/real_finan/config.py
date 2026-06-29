from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .llm import LLMSettings

load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    output_dir: Path
    upload_dir: Path
    db_path: Path
    database_url: str
    redis_url: str | None
    redis_queue_name: str
    neo4j_uri: str | None
    neo4j_username: str | None
    neo4j_password: str | None
    market_data_provider: str
    alphavantage_api_key: str | None
    host: str
    port: int
    api_key: str | None
    llm: LLMSettings

    @classmethod
    def from_env(cls) -> "AppConfig":
        raw_output_dir = os.getenv("MAS_OUTPUT_DIR", "outputs")
        raw_db_path = os.getenv("MAS_DB_PATH", "data/real_finan.db")
        return cls(
            output_dir=Path(raw_output_dir),
            upload_dir=Path(os.getenv("MAS_UPLOAD_DIR", "uploads")),
            db_path=Path(raw_db_path),
            database_url=os.getenv("MAS_DATABASE_URL", f"sqlite:///{raw_db_path.replace(os.sep, '/')}"),
            redis_url=os.getenv("MAS_REDIS_URL"),
            redis_queue_name=os.getenv("MAS_REDIS_QUEUE_NAME", "finance-analysis"),
            neo4j_uri=os.getenv("MAS_NEO4J_URI"),
            neo4j_username=os.getenv("MAS_NEO4J_USERNAME"),
            neo4j_password=os.getenv("MAS_NEO4J_PASSWORD"),
            market_data_provider=os.getenv("MAS_MARKET_DATA_PROVIDER", "yahoo"),
            alphavantage_api_key=os.getenv("ALPHAVANTAGE_API_KEY"),
            host=os.getenv("MAS_HOST", "127.0.0.1"),
            port=int(os.getenv("MAS_PORT", "8000")),
            api_key=os.getenv("MAS_API_KEY"),
            llm=LLMSettings.from_env(),
        )
