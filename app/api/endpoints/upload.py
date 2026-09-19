import uuid
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional, Dict, Any

from app.config import settings
from app.core.ingestion import DocumentParser
from app.core.ner_engine import ner_engine
from app.core.clause_classifier import clause_classifier
from app.core.risk_scorer import risk_engine
from app.core.vector_store import vector_store
from app.core.registry import document_registry

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/contracts/upload")
async def upload_contract(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None),
    contract_name: Optional[str] = Form(None)
) -> Dict[str, Any]:
    """
    Ingest and parse contract document (PDF, DOCX, TXT, Image).
    Returns parsed structural segments, extracted entities, CUAD taxonomy, and risk analysis.
    """
    doc_id = str(uuid.uuid4())[:8]
    
    try:
        if file and file.filename:
            filename = Path(file.filename).name # Sanitize filename
            content_bytes = await file.read()
            
            if len(content_bytes) == 0:
                raise HTTPException(status_code=400, detail="Uploaded file is empty.")
            
            if len(content_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB."
                )
            
            parsed = DocumentParser.parse_file(filename, content_bytes)
        elif raw_text and raw_text.strip():
            raw_clean = raw_text.strip()
            if len(raw_clean) < 10:
                raise HTTPException(status_code=400, detail="Provided text is too short to analyze as a contract.")
            filename = contract_name.strip() if (contract_name and contract_name.strip()) else f"Pasted_Contract_{doc_id}.txt"
            parsed = DocumentParser.parse_file(filename, raw_clean.encode('utf-8'))
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

        document_registry.set(doc_id, result)
        return result

    except HTTPException:
        raise
    except ValueError as ve:
        logger.warning("Validation/parsing error for doc %s: %s", doc_id, str(ve))
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error("Unexpected error analyzing document %s: %s", doc_id, str(e), exc_info=True)
        raise HTTPException(status_code=422, detail=f"Failed to process contract document: {str(e)}")

