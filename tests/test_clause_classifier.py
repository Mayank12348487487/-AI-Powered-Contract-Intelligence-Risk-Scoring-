import pytest
from app.core.clause_classifier import clause_classifier

def test_cuad_categories_loaded():
    assert len(clause_classifier.categories) == 41
    assert "cap_on_liability" in clause_classifier.category_map
    assert "non_compete" in clause_classifier.category_map
    assert "mutual_indemnification" in clause_classifier.category_map

def test_classify_liability_clause():
    text = "In no event shall either Party's total aggregate liability arising out of this Agreement exceed the total fees paid in the preceding twelve (12) months."
    matches = clause_classifier.classify_clause(text)
    assert len(matches) > 0
    cat_ids = [m["category_id"] for m in matches]
    assert "cap_on_liability" in cat_ids

def test_classify_non_compete():
    text = "During the term and for 3 years thereafter, Licensee shall not engage in any competing machine learning business anywhere worldwide."
    matches = clause_classifier.classify_clause(text)
    assert len(matches) > 0
    cat_ids = [m["category_id"] for m in matches]
    assert "non_compete" in cat_ids

def test_classify_indemnity():
    text = "Each Party shall defend, indemnify, and hold harmless the other Party from third-party claims arising from gross negligence or willful misconduct."
    matches = clause_classifier.classify_clause(text)
    assert len(matches) > 0
    cat_ids = [m["category_id"] for m in matches]
    assert "mutual_indemnification" in cat_ids
