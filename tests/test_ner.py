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

def test_ner_international_entities():
    intl_text = """This Consulting Agreement is entered into by and between Nova Dynamics Pty Ltd ("Consultant") and Horizon Ventures PLC ("Client").
Governing Law: This agreement shall be governed by the laws of England and Wales.
Consultant fee is £85,000 GBP payable within 45 days of receipt (Net 45).
"""
    entities = ner_engine.extract_entities(intl_text)
    party_names = [p["name"] for p in entities["parties"]]
    assert any("Nova Dynamics" in name for name in party_names)
    assert any("Horizon Ventures" in name for name in party_names)
    assert entities["governing_law"] is not None
    assert entities["governing_law"]["jurisdiction"] == "England and Wales"
    assert any("85,000" in m["amount"] for m in entities["monetary_values"])

def test_ner_global_currencies_and_jurisdictions():
    global_text = """MASTER LICENSING AGREEMENT
This Agreement is entered into by Zenith Global GmbH ("Licensor") and Apex Innovations Pte Ltd ("Licensee").
Governing Law: This agreement shall be governed by the laws of Singapore.
Fees: Licensee shall pay €500,000 EUR on the Effective Date, ¥10,000,000 JPY in annual maintenance, and CHF 250,000 for integration services.
"""
    entities = ner_engine.extract_entities(global_text)
    assert entities["governing_law"]["jurisdiction"] == "Singapore"
    
    amounts = [m["amount"] for m in entities["monetary_values"]]
    assert any("500,000" in amt for amt in amounts)
    assert any("10,000,000" in amt for amt in amounts)
    assert any("250,000" in amt for amt in amounts)

def test_ner_payment_terms_and_notice_periods():
    text = """SERVICES AGREEMENT
This Agreement is entered into on June 1, 2025, by and between Alpha Tech AG ("Provider") and Beta Corp ("Client").
Expiration Date: May 31, 2028.
Payment terms: Net 60. Client shall pay within 30 business days of invoice.
Termination: Either party may terminate with ninety (90) calendar days notice.
Governing Law: This agreement shall be governed by the laws of Switzerland.
"""
    entities = ner_engine.extract_entities(text)
    payment_terms = entities["payment_terms"]
    assert any("Net 60" in t or "30" in t for t in payment_terms)

    notices = [n["duration"] for n in entities["notice_periods"]]
    assert any("ninety" in n or "90" in n for n in notices)

    assert entities["governing_law"] is not None
    assert entities["governing_law"]["jurisdiction"] == "Switzerland"

    assert entities["effective_date"] is not None
    assert "2025" in entities["effective_date"]["value"]
    assert entities["expiration_date"] is not None
    assert "2028" in entities["expiration_date"]["value"]

def test_ner_handles_governing_law_case_insensitively():
    contract_text = """
    AGREEMENT
    THIS AGREEMENT SHALL BE GOVERNED BY THE LAWS OF INDIA.
    """

    entities = ner_engine.extract_entities(contract_text)

    assert entities["governing_law"] is not None
    assert entities["governing_law"]["jurisdiction"] == "India"

def test_ner_extracts_net_payment_term():
    contract_text = """
    PAYMENT AGREEMENT
    The customer shall pay all invoices under Net 90 payment terms.
    """

    entities = ner_engine.extract_entities(contract_text)

    payment_terms = entities["payment_terms"]

    assert any("Net 90" in term for term in payment_terms)

def test_ner_extracts_net_60_payment_term():
    contract_text = """
    SERVICE AGREEMENT
    All invoices shall be payable within Net 60 payment terms.
    """

    entities = ner_engine.extract_entities(contract_text)

    payment_terms = entities["payment_terms"]

    assert any("Net 60" in term for term in payment_terms)


