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
