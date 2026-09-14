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
    PROJECT_NAME: str = "AI-Powered Contract Intelligence & Risk Scoring"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # NLP & Embedding Settings
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    SIMILARITY_THRESHOLD: float = 0.55
    
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
