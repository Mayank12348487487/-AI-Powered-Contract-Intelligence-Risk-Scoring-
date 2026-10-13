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

def test_sparse_inverted_index():
    from app.core.vector_math import SparseInvertedIndex, batch_sparse_cosine_similarity
    
    doc_vectors = [
        {0: 0.8, 1: 0.6},
        {1: 0.5, 2: 0.866},
        {3: 1.0}
    ]
    index = SparseInvertedIndex(doc_vectors)
    assert index.num_docs == 3
    
    # Query matching doc 0 and doc 1
    query_vec = {1: 1.0}
    results = index.query(query_vec, top_k=2)
    assert len(results) == 2
    matched_doc_indices = [r[0] for r in results]
    assert 0 in matched_doc_indices
    assert 1 in matched_doc_indices
    
    # Query with no overlap
    empty_results = index.query({99: 1.0})
    assert empty_results == []

    # Batch cosine similarity
    batch_sims = batch_sparse_cosine_similarity(query_vec, doc_vectors)
    assert len(batch_sims) == 3
    assert batch_sims[0] == pytest.approx(0.6, rel=1e-3)
    assert batch_sims[1] == pytest.approx(0.5, rel=1e-3)
    assert batch_sims[2] == 0.0

def test_sparse_inverted_index_topk_heapq():
    from app.core.vector_math import SparseInvertedIndex

    doc_vectors = [
        {10: 0.2},
        {10: 0.9},
        {10: 0.5},
        {10: 0.7},
        {10: 0.3}
    ]
    index = SparseInvertedIndex(doc_vectors)
    query_vec = {10: 1.0}
    # Retrieve top 2
    top_2 = index.query(query_vec, top_k=2)
    assert len(top_2) == 2
    assert top_2[0][0] == 1  # highest score is doc 1 (0.9)
    assert pytest.approx(top_2[0][1], rel=1e-3) == 0.9
    assert top_2[1][0] == 3  # second highest is doc 3 (0.7)
    assert pytest.approx(top_2[1][1], rel=1e-3) == 0.7

def test_vector_store_lru_cache_and_invalidation():
    from app.core.vector_store import ContractVectorStore

    store = ContractVectorStore()
    segments = [
        {"id": 1, "heading": "1. Termination", "text": "Either party may terminate upon thirty days written notice."},
        {"id": 2, "heading": "2. Confidentiality", "text": "Recipient shall maintain strict confidentiality."}
    ]
    store.index_document("doc_test", segments, "test.txt")
    
    # First search warms cache
    res1 = store.semantic_search("doc_test", "terminate agreement", top_k=2)
    assert len(res1) > 0
    cache_key = ("doc_test", "terminate agreement", 2)
    assert cache_key in store._query_cache

    # Second search hits cache
    res2 = store.semantic_search("doc_test", "terminate agreement", top_k=2)
    assert res1 == res2

    # Invalidation removes entries
    store.remove_document("doc_test")
    assert cache_key not in store._query_cache
    assert "doc_test" not in store.documents


