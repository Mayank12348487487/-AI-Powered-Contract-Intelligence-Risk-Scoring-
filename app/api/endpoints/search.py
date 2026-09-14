from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel

from app.core.vector_store import vector_store
from app.api.endpoints.cuad import DOCUMENT_REGISTRY

router = APIRouter()

class SearchRequest(BaseModel):
    query: str
    top_k: int = 4

class ChatRequest(BaseModel):
    query: str

@router.post("/contracts/{doc_id}/search")
def search_contract_clauses(doc_id: str, req: SearchRequest) -> Dict[str, Any]:
    """Execute dense semantic vector search across clauses in a contract."""
    if doc_id not in DOCUMENT_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    
    results = vector_store.semantic_search(doc_id, req.query, top_k=req.top_k)
    return {
        "doc_id": doc_id,
        "query": req.query,
        "total_results": len(results),
        "results": results
    }

@router.post("/contracts/{doc_id}/chat")
def chat_with_contract(doc_id: str, req: ChatRequest) -> Dict[str, Any]:
    """Legal Q&A Assistant: Ask questions about the contract in natural language."""
    if doc_id not in DOCUMENT_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    
    doc = DOCUMENT_REGISTRY[doc_id]
    answer_payload = vector_store.answer_contract_query(
        doc_id=doc_id,
        query=req.query,
        entities=doc.get("entities"),
        risk_data=doc.get("risk_analysis")
    )
    return answer_payload
