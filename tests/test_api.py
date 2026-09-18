import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_cuad_categories_endpoint():
    response = client.get("/api/cuad/categories")
    assert response.status_code == 200
    data = response.json()
    assert data["total_categories"] == 41
    assert len(data["categories"]) == 41

def test_samples_endpoint():
    response = client.get("/api/contracts/samples")
    assert response.status_code == 200
    samples = response.json()
    assert len(samples) >= 4
    sample_ids = [s["id"] for s in samples]
    assert "saas_master_agreement" in sample_ids
    assert "mutual_nda" in sample_ids

def test_load_sample_analysis():
    response = client.get("/api/contracts/samples/saas_master_agreement")
    assert response.status_code == 200
    data = response.json()
    assert data["doc_id"] == "sample_saas_master_agreement"
    assert "risk_analysis" in data
    assert "entities" in data
    assert "risk_tier" in data["risk_analysis"]
    assert data["risk_analysis"]["composite_score"] >= 0

def test_contract_chat_endpoint():
    # First load sample
    client.get("/api/contracts/samples/saas_master_agreement")
    
    # Query Q&A
    response = client.post(
        "/api/contracts/sample_saas_master_agreement/chat",
        json={"query": "What is the liability cap?"}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert "answer" in res_data
    assert len(res_data["answer"]) > 10

def test_load_sample_not_found():
    response = client.get("/api/contracts/samples/non_existent_sample_xyz")
    assert response.status_code == 404

def test_contract_search_endpoint():
    # Ensure sample is loaded
    client.get("/api/contracts/samples/saas_master_agreement")
    
    response = client.post(
        "/api/contracts/sample_saas_master_agreement/search",
        json={"query": "termination notice and cure", "top_k": 3}
    )
    assert response.status_code == 200
    search_data = response.json()
    assert search_data["doc_id"] == "sample_saas_master_agreement"
    assert search_data["total_results"] > 0
    assert len(search_data["results"]) <= 3

def test_contract_entities_and_risk_endpoints():
    client.get("/api/contracts/samples/saas_master_agreement")
    
    # Contract Analysis
    res_analysis = client.get("/api/contracts/sample_saas_master_agreement")
    assert res_analysis.status_code == 200
    assert "segments" in res_analysis.json()

    # Risk Endpoint
    res_risk = client.get("/api/contracts/sample_saas_master_agreement/risk")
    assert res_risk.status_code == 200
    assert "composite_score" in res_risk.json()

    # Entities Endpoint
    res_ent = client.get("/api/contracts/sample_saas_master_agreement/entities")
    assert res_ent.status_code == 200
    assert "parties" in res_ent.json()

def test_contract_compare_endpoint():
    # Ensure both samples are loaded
    client.get("/api/contracts/samples/saas_master_agreement")
    client.get("/api/contracts/samples/ip_licensing_unfavorable")

    response = client.post(
        "/api/contracts/compare",
        json={
            "doc_id_a": "sample_saas_master_agreement",
            "doc_id_b": "sample_ip_licensing_unfavorable"
        }
    )
    assert response.status_code == 200
    diff_data = response.json()
    assert "risk_delta" in diff_data
    assert diff_data["risk_delta"] > 0 # Unfavorable contract should have higher risk
    assert "entity_differences" in diff_data

def test_contract_compare_not_found():
    response = client.post(
        "/api/contracts/compare",
        json={
            "doc_id_a": "sample_saas_master_agreement",
            "doc_id_b": "non_existent_doc"
        }
    )
    assert response.status_code == 404

def test_contract_export_endpoints():
    client.get("/api/contracts/samples/saas_master_agreement")

    # JSON export
    res_json = client.get("/api/contracts/sample_saas_master_agreement/export/json")
    assert res_json.status_code == 200
    assert res_json.headers["content-type"] == "application/json"

    # PDF / HTML export
    res_pdf = client.get("/api/contracts/sample_saas_master_agreement/export/pdf")
    assert res_pdf.status_code == 200
    assert "application/pdf" in res_pdf.headers["content-type"] or "text/html" in res_pdf.headers["content-type"]

def test_contract_upload_raw_text():
    contract_text = """COMMERCIAL SERVICES AGREEMENT
Between Alpha Solutions Corp ("Provider") and Beta Retail LLC ("Customer").
1. Effective Date: January 1, 2026.
2. Limitation of Liability: Liability is capped at $50,000 USD.
3. Governing Law: State of California.
"""
    response = client.post(
        "/api/contracts/upload",
        data={"raw_text": contract_text, "contract_name": "Alpha_Beta_Agreement.txt"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "doc_id" in data
    assert data["filename"] == "Alpha_Beta_Agreement.txt"
    assert len(data["segments"]) >= 3
    assert data["entities"]["governing_law"]["jurisdiction"] == "California"

def test_contract_upload_empty_fails():
    response = client.post("/api/contracts/upload", data={})
    assert response.status_code == 400
