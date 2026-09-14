from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import Dict, Any

from app.core.report_generator import report_generator
from app.api.endpoints.cuad import DOCUMENT_REGISTRY

router = APIRouter()

@router.get("/contracts/{doc_id}/export/json")
def export_contract_json(doc_id: str):
    """Download the full JSON audit analysis for a document."""
    if doc_id not in DOCUMENT_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    
    file_path = report_generator.generate_json_report(DOCUMENT_REGISTRY[doc_id])
    return FileResponse(
        path=file_path,
        media_type="application/json",
        filename=f"contract_audit_{doc_id}.json"
    )

@router.get("/contracts/{doc_id}/export/pdf")
def export_contract_pdf(doc_id: str):
    """Download the executive PDF/HTML report for a document."""
    if doc_id not in DOCUMENT_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    
    file_path = report_generator.generate_pdf_report(DOCUMENT_REGISTRY[doc_id])
    media_type = "application/pdf" if file_path.endswith(".pdf") else "text/html"
    download_name = f"contract_audit_{doc_id}.pdf" if file_path.endswith(".pdf") else f"contract_audit_{doc_id}.html"

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=download_name
    )
