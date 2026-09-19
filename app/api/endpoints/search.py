from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from app.core.vector_store import vector_store
from app.core.registry import document_registry

router = APIRouter()

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(4, ge=1, le=20)

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)

@router.post("/contracts/{doc_id}/search")
def search_contract_clauses(doc_id: str, req: SearchRequest) -> Dict[str, Any]:
    """Execute dense semantic vector search across clauses in a contract."""
    if not document_registry.has(doc_id):
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    
    clean_query = req.query.strip()
    if not clean_query:
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")

    results = vector_store.semantic_search(doc_id, clean_query, top_k=req.top_k)
    return {
        "doc_id": doc_id,
        "query": clean_query,
        "total_results": len(results),
        "results": results
    }

@router.post("/contracts/{doc_id}/chat")
def chat_with_contract(doc_id: str, req: ChatRequest) -> Dict[str, Any]:
    """Legal Q&A Assistant: Ask questions about the contract in natural language."""
    doc = document_registry.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    
    clean_query = req.query.strip()
    if not clean_query:
        raise HTTPException(status_code=400, detail="Chat question cannot be empty.")

    answer_payload = vector_store.answer_contract_query(
        doc_id=doc_id,
        query=clean_query,
        entities=doc.get("entities"),
        risk_data=doc.get("risk_analysis")
    )
    return answer_payload

