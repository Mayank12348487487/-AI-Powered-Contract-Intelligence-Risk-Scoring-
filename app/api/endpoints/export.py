from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.report_generator import report_generator
from app.core.registry import document_registry

router = APIRouter()

@router.get("/contracts/{doc_id}/export/json")
def export_contract_json(doc_id: str):
    """Download the full JSON audit analysis for a document."""
    doc = document_registry.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    
    file_path = report_generator.generate_json_report(doc)
    if not Path(file_path).exists():
        raise HTTPException(status_code=500, detail="Failed to create JSON report file.")
        
    return FileResponse(
        path=file_path,
        media_type="application/json",
        filename=f"contract_audit_{doc_id}.json"
    )

@router.get("/contracts/{doc_id}/export/pdf")
def export_contract_pdf(doc_id: str):
    """Download the executive PDF/HTML report for a document."""
    doc = document_registry.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    
    file_path = report_generator.generate_pdf_report(doc)
    if not Path(file_path).exists():
        raise HTTPException(status_code=500, detail="Failed to create export report file.")

    media_type = "application/pdf" if file_path.endswith(".pdf") else "text/html"
    download_name = f"contract_audit_{doc_id}.pdf" if file_path.endswith(".pdf") else f"contract_audit_{doc_id}.html"

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=download_name
    )

