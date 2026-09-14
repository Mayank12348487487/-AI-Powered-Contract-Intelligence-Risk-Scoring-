from fastapi import APIRouter

from app.api.endpoints import upload, analyze, search, compare, export, cuad

api_router = APIRouter()

api_router.include_router(cuad.router, tags=["CUAD Taxonomy & Samples"])
api_router.include_router(upload.router, tags=["Document Ingestion"])
api_router.include_router(analyze.router, tags=["Contract Analysis"])
api_router.include_router(search.router, tags=["Semantic Search & Q&A"])
api_router.include_router(compare.router, tags=["Contract Comparison"])
api_router.include_router(export.router, tags=["Audit Reports"])
