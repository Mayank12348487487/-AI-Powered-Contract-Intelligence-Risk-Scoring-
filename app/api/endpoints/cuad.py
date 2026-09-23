from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from app.config import SAMPLES_DIR
from app.core.clause_classifier import clause_classifier
from app.core.ingestion import DocumentParser
from app.core.ner_engine import ner_engine
from app.core.risk_scorer import risk_engine
from app.core.vector_store import vector_store
from app.core.registry import document_registry

router = APIRouter()

# Alias for backward compatibility
DOCUMENT_REGISTRY = document_registry

SAMPLE_METADATA = [
    {
        "id": "saas_master_agreement",
        "title": "SaaS Master Services Agreement",
        "description": "Standard commercial enterprise B2B SaaS agreement with mutual protections, 12-month liability cap, and SOC2 audit rights.",
        "risk_profile": "Medium (Score ~28/100)",
        "file_name": "saas_master_agreement.txt"
    },
    {
        "id": "mutual_nda",
        "title": "Mutual Non-Disclosure Agreement",
        "description": "Balanced reciprocal NDA for biotech research collaboration with 3-year survival and reasonable care standard.",
        "risk_profile": "Low (Score ~15/100)",
        "file_name": "mutual_nda.txt"
    },
    {
        "id": "ip_licensing_unfavorable",
        "title": "High-Risk Unfavorable IP Licensing Agreement",
        "description": "Critical risk contract containing unlimited licensee liability, 5-year global non-compete, pre-existing IP forfeiture, and unannounced audits.",
        "risk_profile": "Critical (Score ~88/100)",
        "file_name": "ip_licensing_unfavorable.txt"
    },
    {
        "id": "vendor_supply_contract",
        "title": "Commercial Supply & Manufacturing Agreement",
        "description": "Supply contract featuring automatic renewal, take-or-pay volume obligations, and liquidated delay penalties.",
        "risk_profile": "High (Score ~58/100)",
        "file_name": "vendor_supply_contract.txt"
    }
]

@router.get("/cuad/categories")
def get_cuad_categories() -> Dict[str, Any]:
    """Retrieve full CUAD (Contract Understanding Atticus Dataset) 41 categories schema."""
    return {
        "cuad_version": "1.0",
        "total_categories": len(clause_classifier.categories),
        "categories": clause_classifier.categories
    }

@router.get("/contracts/samples")
def get_sample_contracts() -> List[Dict[str, Any]]:
    """Get list of curated sample contracts available for instant testing."""
    return SAMPLE_METADATA

@router.get("/contracts/samples/{sample_id}")
def load_and_analyze_sample(sample_id: str) -> Dict[str, Any]:
    """Load and perform instant full analysis on a pre-packaged sample contract."""
    sample_info = next((s for s in SAMPLE_METADATA if s["id"] == sample_id), None)
    if not sample_info:
        raise HTTPException(status_code=404, detail=f"Sample contract '{sample_id}' not found")

    file_path = SAMPLES_DIR / sample_info["file_name"]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Sample contract file not found on disk")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Ingest & segment
    parsed = DocumentParser.parse_file(sample_info["file_name"], content.encode('utf-8'))
    
    # NER
    entities = ner_engine.extract_entities(parsed["full_text"])
    
    # CUAD Clause Classification
    enriched_segments = clause_classifier.classify_document_segments(parsed["segments"])
    category_summary = clause_classifier.get_detected_categories_summary(enriched_segments)

    # Risk Scoring & Anomaly Detection
    risk_analysis = risk_engine.evaluate_contract_risk(
        parsed["full_text"], enriched_segments, entities
    )

    doc_id = f"sample_{sample_id}"
    
    # Vector store index
    vector_store.index_document(doc_id, enriched_segments, sample_info["file_name"])

    result = {
        "doc_id": doc_id,
        "filename": sample_info["title"],
        "format": "text",
        "total_segments": parsed["total_segments"],
        "full_text": parsed["full_text"],
        "segments": enriched_segments,
        "entities": entities,
        "category_summary": category_summary,
        "risk_analysis": risk_analysis
    }

    document_registry.set(doc_id, result)
    return result
