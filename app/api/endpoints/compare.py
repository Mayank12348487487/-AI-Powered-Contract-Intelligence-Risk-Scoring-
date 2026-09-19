from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from pydantic import BaseModel

from app.core.compare import contract_comparator
from app.core.registry import document_registry

router = APIRouter()

class CompareRequest(BaseModel):
    doc_id_a: str
    doc_id_b: str

@router.post("/contracts/compare")
def compare_contracts(req: CompareRequest) -> Dict[str, Any]:
    """Compare two contracts, highlight clause drift, and analyze risk shifts."""
    contract_a = document_registry.get(req.doc_id_a)
    if not contract_a:
        raise HTTPException(status_code=404, detail=f"Contract A ('{req.doc_id_a}') not found in session.")
    
    contract_b = document_registry.get(req.doc_id_b)
    if not contract_b:
        raise HTTPException(status_code=404, detail=f"Contract B ('{req.doc_id_b}') not found in session.")

    diff_result = contract_comparator.compare_contracts(contract_a, contract_b)
    return diff_result

