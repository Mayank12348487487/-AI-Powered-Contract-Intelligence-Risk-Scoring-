import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

def run_all():
    print("========================================", flush=True)
    print("RUNNING CONTRACT INTELLIGENCE TEST SUITE", flush=True)
    print("========================================", flush=True)
    
    t0 = time.time()

    # 1. Ingestion
    print("\n[1/5] Testing Ingestion & Parsing...", end=" ", flush=True)
    from tests.test_ingestion import test_text_normalization, test_clause_segmentation
    test_text_normalization()
    test_clause_segmentation()
    print("PASSED", flush=True)

    # 2. NER
    print("[2/5] Testing Legal NER Engine...", end=" ", flush=True)
    from tests.test_ner import test_ner_party_and_date_extraction, test_ner_international_entities
    test_ner_party_and_date_extraction()
    test_ner_international_entities()
    print("PASSED", flush=True)

    # 3. Clause Classification
    print("[3/5] Testing CUAD 41 Clause Classifier...", end=" ", flush=True)
    from tests.test_clause_classifier import (
        test_cuad_categories_loaded,
        test_classify_liability_clause,
        test_classify_non_compete,
        test_classify_indemnity
    )
    test_cuad_categories_loaded()
    test_classify_liability_clause()
    test_classify_non_compete()
    test_classify_indemnity()
    print("PASSED", flush=True)

    # 4. Risk Scorer
    print("[4/5] Testing Multi-Dimensional Risk Scorer...", end=" ", flush=True)
    from tests.test_risk_scorer import (
        test_safe_mutual_nda_risk,
        test_critical_unfavorable_licensing_risk
    )
    test_safe_mutual_nda_risk()
    test_critical_unfavorable_licensing_risk()
    print("PASSED", flush=True)

    # 5. API Endpoints
    print("[5/5] Testing FastAPI Endpoints...", end=" ", flush=True)
    from tests.test_api import (
        test_health_check,
        test_cuad_categories_endpoint,
        test_samples_endpoint,
        test_load_sample_analysis,
        test_load_sample_not_found,
        test_contract_chat_endpoint,
        test_contract_search_endpoint,
        test_contract_entities_and_risk_endpoints,
        test_contract_compare_endpoint,
        test_contract_compare_not_found,
        test_contract_export_endpoints,
        test_contract_upload_raw_text,
        test_contract_upload_empty_fails
    )
    test_health_check()
    test_cuad_categories_endpoint()
    test_samples_endpoint()
    test_load_sample_analysis()
    test_load_sample_not_found()
    test_contract_chat_endpoint()
    test_contract_search_endpoint()
    test_contract_entities_and_risk_endpoints()
    test_contract_compare_endpoint()
    test_contract_compare_not_found()
    test_contract_export_endpoints()
    test_contract_upload_raw_text()
    test_contract_upload_empty_fails()
    print("PASSED", flush=True)

    elapsed = round(time.time() - t0, 2)
    print("\n========================================", flush=True)
    print(f"ALL 5 TEST SUITES PASSED in {elapsed}s!", flush=True)
    print("========================================", flush=True)

if __name__ == "__main__":
    run_all()
