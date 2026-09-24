import pytest
from app.core.compare import contract_comparator

def test_compare_identical_contracts():
    contract = {
        "filename": "master_services_v1.txt",
        "risk_analysis": {
            "composite_score": 35,
            "risk_tier": "LOW",
            "anomalies": []
        },
        "entities": {
            "parties": [{"name": "Acme Corp", "role": "Provider"}],
            "governing_law": {"jurisdiction": "Delaware"},
            "effective_date": {"value": "2026-01-01"},
            "expiration_date": {"value": "2027-01-01"}
        },
        "segments": [
            {
                "heading": "1. Confidentiality",
                "text": "Each party agrees to maintain confidentiality of proprietary data.",
                "primary_category": "Non-Disclosure"
            }
        ]
    }

    comparison = contract_comparator.compare_contracts(contract, contract)
    assert comparison["score_a"] == 35
    assert comparison["score_b"] == 35
    assert comparison["risk_delta"] == 0
    assert comparison["risk_trend"] == "IDENTICAL RISK"
    assert len(comparison["entity_differences"]) == 0
    assert len(comparison["clause_comparisons"]) == 1
    assert comparison["clause_comparisons"][0]["status"] == "Identical"

def test_compare_divergent_contracts():
    contract_a = {
        "filename": "standard_agreement.txt",
        "risk_analysis": {
            "composite_score": 25,
            "risk_tier": "LOW",
            "anomalies": []
        },
        "entities": {
            "parties": [{"name": "Alpha Corp", "role": "Customer"}],
            "governing_law": {"jurisdiction": "New York"},
            "effective_date": {"value": "2026-01-01"},
            "expiration_date": {"value": "2027-01-01"}
        },
        "segments": [
            {
                "heading": "1. Limitation of Liability",
                "text": "Total aggregate liability of either party shall not exceed total fees paid under this agreement.",
                "primary_category": "Limitation of Liability"
            }
        ]
    }

    contract_b = {
        "filename": "aggressive_vendor_agreement.txt",
        "risk_analysis": {
            "composite_score": 85,
            "risk_tier": "CRITICAL",
            "anomalies": [{"category": "Unlimited Liability"}]
        },
        "entities": {
            "parties": [{"name": "Beta LLC", "role": "Vendor"}],
            "governing_law": {"jurisdiction": "England and Wales"},
            "effective_date": {"value": "2026-06-01"},
            "expiration_date": {"value": "2029-06-01"}
        },
        "segments": [
            {
                "heading": "1. Unlimited Liability",
                "text": "Customer shall indemnify vendor with unlimited un-capped liability for any third party claims.",
                "primary_category": "Indemnity"
            }
        ]
    }

    comparison = contract_comparator.compare_contracts(contract_a, contract_b)
    assert comparison["risk_delta"] == 60
    assert comparison["risk_trend"] == "INCREASED RISK"
    assert comparison["tier_a"] == "LOW"
    assert comparison["tier_b"] == "CRITICAL"
    assert len(comparison["entity_differences"]) > 0
    assert any(d["field"] == "Contracting Parties" for d in comparison["entity_differences"])
    assert any(d["field"] == "Governing Law / Jurisdiction" for d in comparison["entity_differences"])

def test_compare_with_empty_data():
    comparison = contract_comparator.compare_contracts({}, {})
    assert comparison["score_a"] == 0
    assert comparison["score_b"] == 0
    assert comparison["risk_delta"] == 0
    assert comparison["risk_trend"] == "IDENTICAL RISK"
    assert comparison["entity_differences"] == []
    assert comparison["clause_comparisons"] == []
