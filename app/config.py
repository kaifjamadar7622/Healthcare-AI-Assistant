"""Application configuration and path helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
VECTOR_STORE_DIR = ROOT_DIR / "vector_store"
OCR_SOURCE_DIR = DATA_DIR / "ocr_sources"

load_dotenv(ROOT_DIR / ".env")


def _env_bool(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: str) -> int:
    return int(os.getenv(name, default))


def _env_float(name: str, default: str) -> float:
    return float(os.getenv(name, default))


def _env_path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    return Path(value) if value else default


@dataclass(frozen=True, slots=True)
class AssistantConfig:
    """Runtime settings for the assistant."""

    app_name: str = os.getenv("APP_NAME", "Healthcare AI Assistant")
    environment: str = os.getenv("ENV", "development")
    knowledge_base_path: Path = _env_path("KNOWLEDGE_BASE_PATH", DATA_DIR / "knowledge_base.json")
    ocr_source_dir: Path = _env_path("OCR_SOURCE_DIR", OCR_SOURCE_DIR)
    vector_store_path: Path = _env_path("VECTOR_STORE_PATH", VECTOR_STORE_DIR / "index.json")
    top_k: int = _env_int("TOP_K", "3")
    min_score: float = _env_float("MIN_SCORE", "0.08")
    embedding_dimension: int = _env_int("EMBEDDING_DIMENSION", "256")
    enable_ocr_ingestion: bool = _env_bool("ENABLE_OCR_INGESTION", "1")
    use_ollama: bool = _env_bool("USE_OLLAMA", "1")
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1")
    use_openai: bool = _env_bool("USE_OPENAI", "0")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    emergency_disclaimer: str = (
        "If this might be an emergency, call local emergency services now or seek urgent medical care."
    )
    medical_safety_note: str = (
        "This assistant is for general information only and does not replace a licensed clinician."
    )


def load_config() -> AssistantConfig:
    """Create a config object from the current environment."""

    return AssistantConfig()
