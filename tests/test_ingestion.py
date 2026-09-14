import pytest
from app.core.ingestion import DocumentParser

def test_text_normalization():
    raw = "This is “smart quotes” and ‘apostrophes’ — with dashes.\r\nNext line."
    cleaned = DocumentParser.normalize_text(raw)
    assert '“' not in cleaned
    assert '”' not in cleaned
    assert '"smart quotes"' in cleaned
    assert "'apostrophes'" in cleaned

def test_clause_segmentation():
    contract_sample = """MASTER SERVICES AGREEMENT

1. SCOPE OF SERVICES
Provider agrees to deliver services as outlined in Exhibit A.

2. PAYMENT TERMS
Client shall pay all undisputed invoices within thirty (30) days of receipt (Net 30).

3. GOVERNING LAW
This agreement shall be governed by the laws of the State of Delaware.
"""
    parsed = DocumentParser.parse_file("test.txt", contract_sample.encode('utf-8'))
    assert parsed["format"] == "text"
    assert parsed["total_segments"] >= 3
    assert len(parsed["segments"]) >= 3
    
    headings = [s["heading"] for s in parsed["segments"]]
    assert any("SCOPE OF SERVICES" in h for h in headings)
    assert any("PAYMENT TERMS" in h for h in headings)
