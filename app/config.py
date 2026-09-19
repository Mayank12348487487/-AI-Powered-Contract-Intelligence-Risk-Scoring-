import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "data"
SAMPLES_DIR = DATA_DIR / "sample_contracts"
UPLOADS_DIR = BASE_DIR / "uploads"
EXPORTS_DIR = BASE_DIR / "exports"

# Ensure runtime directories exist
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseModel):
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "AI-Powered Contract Intelligence & Risk Scoring")
    VERSION: str = "1.0.0"
    API_PREFIX: str = os.getenv("API_PREFIX", "/api")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    
    # File limits & registry
    MAX_UPLOAD_SIZE_BYTES: int = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(25 * 1024 * 1024))) # 25 MB
    MAX_REGISTRY_DOCS: int = int(os.getenv("MAX_REGISTRY_DOCS", "100"))

    # NLP & Embedding Settings
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.55"))
    
    # Risk Scoring Weightings
    WEIGHT_MISSING_CLAUSES: float = 0.35
    WEIGHT_UNFAVORABLE_TERMS: float = 0.35
    WEIGHT_OPERATIONAL_RISK: float = 0.20
    WEIGHT_AMBIGUITY_RISK: float = 0.10
    
    # Risk Thresholds
    RISK_LOW_MAX: int = 25
    RISK_MEDIUM_MAX: int = 50
    RISK_HIGH_MAX: int = 75
    # >75 is CRITICAL

settings = Settings()

