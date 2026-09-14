import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional, Dict, Any

from app.core.ingestion import DocumentParser
from app.core.ner_engine import ner_engine
from app.core.clause_classifier import clause_classifier
from app.core.risk_scorer import risk_engine
from app.core.vector_store import vector_store
from app.api.endpoints.cuad import DOCUMENT_REGISTRY

router = APIRouter()

@router.post("/contracts/upload")
async def upload_contract(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None),
    contract_name: Optional[str] = Form(None)
) -> Dict[str, Any]:
    """
    Ingest and parse contract document (PDF, DOCX, TXT, Image).
    Returns parsed structural segments and document ID.
    """
    doc_id = str(uuid.uuid4())[:8]
    
    if file and file.filename:
        filename = file.filename
        content_bytes = await file.read()
        if len(content_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        parsed = DocumentParser.parse_file(filename, content_bytes)
    elif raw_text and raw_text.strip():
        filename = contract_name or f"Pasted_Contract_{doc_id}.txt"
        parsed = DocumentParser.parse_file(filename, raw_text.encode('utf-8'))
    else:
        raise HTTPException(status_code=400, detail="No file or text content provided.")

    # Execute NLP pipeline
    entities = ner_engine.extract_entities(parsed["full_text"])
    enriched_segments = clause_classifier.classify_document_segments(parsed["segments"])
    category_summary = clause_classifier.get_detected_categories_summary(enriched_segments)
    
    risk_analysis = risk_engine.evaluate_contract_risk(
        parsed["full_text"], enriched_segments, entities
    )

    # Index into vector store
    vector_store.index_document(doc_id, enriched_segments, filename)

    result = {
        "doc_id": doc_id,
        "filename": filename,
        "format": parsed.get("format", "text"),
        "page_count": parsed.get("page_count", 1),
        "total_segments": parsed["total_segments"],
        "full_text": parsed["full_text"],
        "segments": enriched_segments,
        "entities": entities,
        "category_summary": category_summary,
        "risk_analysis": risk_analysis
    }

    DOCUMENT_REGISTRY[doc_id] = result
    return result
