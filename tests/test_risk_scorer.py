import pytest
from app.core.ingestion import DocumentParser
from app.core.ner_engine import ner_engine
from app.core.clause_classifier import clause_classifier
from app.core.risk_scorer import risk_engine

def test_safe_mutual_nda_risk():
    nda_text = """MUTUAL NON-DISCLOSURE AGREEMENT
Effective as of January 10, 2026, by and between Company A Inc. ("Disclosing Party") and Company B LLC ("Receiving Party").
1. Confidential Information shall be protected with reasonable care for a term of 2 years.
2. Governing Law: State of Massachusetts.
3. Neither party shall be liable for indirect damages.
"""
    parsed = DocumentParser.parse_file("nda.txt", nda_text.encode('utf-8'))
    entities = ner_engine.extract_entities(nda_text)
    enriched = clause_classifier.classify_document_segments(parsed["segments"])
    
    risk = risk_engine.evaluate_contract_risk(nda_text, enriched, entities)
    assert risk["composite_score"] < 50
    assert risk["risk_tier"] in ["LOW", "MEDIUM"]

def test_critical_unfavorable_licensing_risk():
    unfavorable_text = """UNFAVORABLE IP LICENSE AGREEMENT
1. Licensee's liability shall be completely uncapped and unlimited.
2. Licensee assigns all right, title, and interest in all background source code and pre-existing intellectual property.
3. Licensee agrees to a 5-year global non-compete worldwide.
4. Licensee agrees to defend, indemnify, and hold harmless Licensor regardless of contributory negligence.
5. Licensor may terminate at its sole and absolute discretion without cause upon 24 hours notice.
6. Licensor may inspect and audit premises at any time without prior notice.
"""
    parsed = DocumentParser.parse_file("unfavorable.txt", unfavorable_text.encode('utf-8'))
    entities = ner_engine.extract_entities(unfavorable_text)
    enriched = clause_classifier.classify_document_segments(parsed["segments"])
    
    risk = risk_engine.evaluate_contract_risk(unfavorable_text, enriched, entities)
    assert risk["composite_score"] >= 70
    assert risk["risk_tier"] in ["HIGH", "CRITICAL"]
    assert len(risk["anomalies"]) >= 3

def test_expanded_anomaly_patterns():
    risky_clauses = """TERMS OF SERVICE
1. Provider may modify these terms at any time by posting updates without prior written notice.
2. Customer waives all right to a jury trial and class action.
3. All confidentiality covenants and restrictions shall survive in perpetuity.
"""
    parsed = DocumentParser.parse_file("tos.txt", risky_clauses.encode('utf-8'))
    entities = ner_engine.extract_entities(risky_clauses)
    enriched = clause_classifier.classify_document_segments(parsed["segments"])
    risk = risk_engine.evaluate_contract_risk(risky_clauses, enriched, entities)
    
    categories_flagged = [a["category"] for a in risk["anomalies"]]
    assert "Unilateral Terms Modification" in categories_flagged
    assert "Waiver of Jury Trial & Class Action" in categories_flagged
    assert "Perpetual Restrictive Obligations" in categories_flagged

def test_termination_for_convenience_risk():
    contract_text = """SERVICE AGREEMENT
Effective as of January 1, 2026, between Company A and Company B.
1. Services shall be provided for an initial term of one year.
2. Either party may terminate this Agreement for convenience without cause upon 30 days written notice.
3. Confidential Information shall be protected for three years.
4. Each party shall remain responsible for its own acts and omissions.
"""
    parsed = DocumentParser.parse_file(
        "termination.txt", contract_text.encode("utf-8")
    )
    entities = ner_engine.extract_entities(contract_text)
    enriched = clause_classifier.classify_document_segments(parsed["segments"])

    risk = risk_engine.evaluate_contract_risk(
        contract_text, enriched, entities
    )

    assert "risk_tier" in risk
    assert "composite_score" in risk
    assert 0 <= risk["composite_score"] <= 100
