from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from pydantic import BaseModel

from app.core.compare import contract_comparator
from app.api.endpoints.cuad import DOCUMENT_REGISTRY

router = APIRouter()

class CompareRequest(BaseModel):
    doc_id_a: str
    doc_id_b: str

@router.post("/contracts/compare")
def compare_contracts(req: CompareRequest) -> Dict[str, Any]:
    """Compare two contracts, highlight clause drift, and analyze risk shifts."""
    if req.doc_id_a not in DOCUMENT_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Contract A ('{req.doc_id_a}') not found in session.")
    if req.doc_id_b not in DOCUMENT_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Contract B ('{req.doc_id_b}') not found in session.")

    contract_a = DOCUMENT_REGISTRY[req.doc_id_a]
    contract_b = DOCUMENT_REGISTRY[req.doc_id_b]

    diff_result = contract_comparator.compare_contracts(contract_a, contract_b)
    return diff_result
