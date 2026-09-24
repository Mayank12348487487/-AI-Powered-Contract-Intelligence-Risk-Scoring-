import pytest
from app.core.vector_math import FastTFIDFVectorizer, sparse_cosine_similarity

def test_tfidf_tokenization_and_ngrams():
    vectorizer = FastTFIDFVectorizer(ngram_range=(1, 2), max_features=100)
    tokens = vectorizer.tokenize("The quick brown fox jumps over the lazy dog.")
    # English stopwords like 'the', 'over' should be removed
    assert "quick" in tokens
    assert "brown" in tokens
    assert "fox" in tokens
    assert "quick brown" in tokens
    assert "the" not in tokens

def test_tfidf_fit_transform_and_transform():
    corpus = [
        "Confidential information shall be kept secret by recipient.",
        "Either party may terminate this agreement with 30 days written notice.",
        "Liability shall be limited to direct damages and exclude lost profits."
    ]
    vectorizer = FastTFIDFVectorizer(ngram_range=(1, 2), max_features=500)
    vecs = vectorizer.fit_transform(corpus)
    
    assert len(vecs) == len(corpus)
    assert vectorizer.is_fitted is True
    assert len(vectorizer.vocab) > 0

    # Test transform with new unseen query
    query_vecs = vectorizer.transform(["liability damages limitation"])
    assert len(query_vecs) == 1
    assert isinstance(query_vecs[0], dict)

def test_unfitted_transform_raises():
    vectorizer = FastTFIDFVectorizer()
    with pytest.raises(ValueError, match="Vectorizer must be fitted"):
        vectorizer.transform(["some test query"])

def test_empty_corpus():
    vectorizer = FastTFIDFVectorizer()
    vecs = vectorizer.fit_transform([])
    assert vecs == []

def test_sparse_cosine_similarity():
    vec_a = {0: 0.6, 1: 0.8}
    vec_b = {0: 0.6, 1: 0.8}
    vec_c = {2: 1.0}
    empty_vec = {}

    # Identical vectors should have similarity ~1.0
    sim_identical = sparse_cosine_similarity(vec_a, vec_b)
    assert pytest.approx(sim_identical, rel=1e-3) == 1.0

    # Orthogonal vectors should have similarity 0.0
    sim_orthogonal = sparse_cosine_similarity(vec_a, vec_c)
    assert sim_orthogonal == 0.0

    # Empty vector should return 0.0
    assert sparse_cosine_similarity(vec_a, empty_vec) == 0.0
    assert sparse_cosine_similarity(empty_vec, vec_a) == 0.0
