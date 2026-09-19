from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from pydantic import BaseModel

from app.core.registry import document_registry

router = APIRouter()

class AnalyzeRequest(BaseModel):
    doc_id: str

@router.get("/contracts/{doc_id}")
def get_contract_analysis(doc_id: str) -> Dict[str, Any]:
    """Retrieve full cached analysis results for a document ID."""
    doc = document_registry.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found in registry.")
    return doc

@router.get("/contracts/{doc_id}/risk")
def get_contract_risk(doc_id: str) -> Dict[str, Any]:
    """Retrieve only the risk score and anomaly breakdown for a document ID."""
    doc = document_registry.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found in registry.")
    return doc.get("risk_analysis", {})

@router.get("/contracts/{doc_id}/entities")
def get_contract_entities(doc_id: str) -> Dict[str, Any]:
    """Retrieve extracted legal entities for a document ID."""
    doc = document_registry.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found in registry.")
    return doc.get("entities", {})

