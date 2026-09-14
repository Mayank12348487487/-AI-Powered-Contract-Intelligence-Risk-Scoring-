import pytest
from app.core.ner_engine import ner_engine

def test_ner_party_and_date_extraction():
    sample_text = """This Agreement is made effective as of October 15, 2025, by and between CloudMatrix Technologies, Inc. ("Provider"), and Global Logistics Solutions LLC ("Customer").
The initial term shall expire on October 14, 2027.
This agreement shall be governed by the laws of the State of Delaware.
Customer shall pay $120,000 USD within thirty (30) days of invoice (Net 30).
Either party may terminate upon sixty (60) days prior written notice.
"""
    entities = ner_engine.extract_entities(sample_text)
    
    # Check Parties
    party_names = [p["name"] for p in entities["parties"]]
    assert any("CloudMatrix" in name for name in party_names)
    assert any("Global Logistics" in name for name in party_names)

    # Check Dates
    assert entities["effective_date"] is not None
    assert "2025" in entities["effective_date"]["value"]
    assert entities["expiration_date"] is not None
    assert "2027" in entities["expiration_date"]["value"]

    # Check Governing Law
    assert entities["governing_law"] is not None
    assert entities["governing_law"]["jurisdiction"] == "Delaware"

    # Check Monetary Values
    amounts = [m["amount"] for m in entities["monetary_values"]]
    assert any("120,000" in amt for amt in amounts)

    # Check Notice Periods
    notices = [n["duration"] for n in entities["notice_periods"]]
    assert any("60" in n or "sixty" in n.lower() for n in notices)
