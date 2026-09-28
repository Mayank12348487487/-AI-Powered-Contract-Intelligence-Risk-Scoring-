import math
import re
from typing import List, Dict, Tuple, Set, Optional
from collections import Counter

# Standard English stopwords
STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves"
}

WORD_PATTERN = re.compile(r'[a-zA-Z0-9_\-]+')

# Precomputed log table for fast sublinear TF scaling (1 + log(tf)) for counts 1..64
_PRECOMPUTED_LOG_TF: Tuple[float, ...] = tuple(1.0 + math.log(i) for i in range(1, 65))
_MAX_PRECOMPUTED_TF = 64

class FastTFIDFVectorizer:
    """
    High-performance, pure-Python TF-IDF vectorizer with n-grams, L2 normalization,
    and lookup-accelerated sublinear TF scaling.
    """
    __slots__ = ('ngram_range', 'max_features', 'vocab', 'idf', 'is_fitted')

    def __init__(self, ngram_range: Tuple[int, int] = (1, 2), max_features: int = 5000):
        self.ngram_range = ngram_range
        self.max_features = max_features
        self.vocab: Dict[str, int] = {}
        self.idf: List[float] = []
        self.is_fitted = False

    def tokenize(self, text: str) -> List[str]:
        """Extract unigrams and bigrams, filtering out single chars and stopwords."""
        words = WORD_PATTERN.findall(text.lower())
        
        # 1. Unigrams
        filtered_words = [w for w in words if len(w) > 1 and w not in STOPWORDS]
        n_filtered = len(filtered_words)
        
        if self.ngram_range[1] < 2 or n_filtered < 2:
            return filtered_words

        # 2. Bigrams if requested
        tokens = list(filtered_words)
        tokens.extend(f"{filtered_words[i]} {filtered_words[i+1]}" for i in range(n_filtered - 1))
        return tokens

    def fit_transform(self, corpus: List[str]) -> List[Dict[int, float]]:
        """Fit vocabulary on corpus and return sparse vector representations in a single pass."""
        n_docs = len(corpus)
        if n_docs == 0:
            return []

        # 1. Single-pass tokenization and document frequency counting
        df: Counter = Counter()
        doc_tokens_list: List[List[str]] = []
        
        for doc in corpus:
            tokens = self.tokenize(doc)
            df.update(set(tokens))
            doc_tokens_list.append(tokens)

        # 2. Build vocabulary of top features
        most_common = df.most_common(self.max_features)
        self.vocab = {term: idx for idx, (term, _) in enumerate(most_common)}
        
        # 3. Compute smooth IDF
        vocab_size = len(self.vocab)
        self.idf = [0.0] * vocab_size
        log_n = math.log(1 + n_docs)
        for term, idx in self.vocab.items():
            self.idf[idx] = log_n - math.log(1 + df[term]) + 1.0

        self.is_fitted = True

        # 4. Transform corpus into unit-norm sparse vectors
        return [self._transform_tokens(doc_tokens) for doc_tokens in doc_tokens_list]

    def transform(self, corpus: List[str]) -> List[Dict[int, float]]:
        """Transform new documents using fitted vocabulary."""
        if not self.is_fitted:
            raise ValueError("Vectorizer must be fitted before calling transform.")
        
        return [self._transform_tokens(self.tokenize(doc)) for doc in corpus]

    def _transform_tokens(self, tokens: List[str]) -> Dict[int, float]:
        """Convert token stream to normalized sparse vector."""
        if not tokens:
            return {}
            
        tf = Counter(tokens)
        sparse_vec: Dict[int, float] = {}
        sq_sum = 0.0
        vocab = self.vocab
        idf = self.idf

        for term, count in tf.items():
            idx = vocab.get(term)
            if idx is not None:
                # Sublinear TF scaling with fast log table lookup
                if count <= _MAX_PRECOMPUTED_TF:
                    sublinear_tf = _PRECOMPUTED_LOG_TF[count - 1]
                else:
                    sublinear_tf = 1.0 + math.log(count)
                val = sublinear_tf * idf[idx]
                sparse_vec[idx] = val
                sq_sum += val * val

        # L2 Normalization
        if sq_sum > 0.0:
            norm = 1.0 / math.sqrt(sq_sum)
            for idx in sparse_vec:
                sparse_vec[idx] *= norm

        return sparse_vec


class SparseInvertedIndex:
    """
    Inverted index mapping feature index -> list of (doc_index, weight) tuples.
    Provides sub-millisecond sparse cosine similarity searches across large sets of documents.
    """
    __slots__ = ('postings', 'num_docs')

    def __init__(self, doc_vectors: Optional[List[Dict[int, float]]] = None):
        self.postings: Dict[int, List[Tuple[int, float]]] = {}
        self.num_docs = 0
        if doc_vectors:
            self.build(doc_vectors)

    def build(self, doc_vectors: List[Dict[int, float]]) -> None:
        self.num_docs = len(doc_vectors)
        self.postings.clear()
        for doc_idx, vec in enumerate(doc_vectors):
            for term_idx, weight in vec.items():
                if term_idx not in self.postings:
                    self.postings[term_idx] = []
                self.postings[term_idx].append((doc_idx, weight))

    def query(self, query_vec: Dict[int, float], top_k: int = 10, min_score: float = 0.0) -> List[Tuple[int, float]]:
        """
        Fast dot-product search against indexed documents using accumulator.
        """
        if not query_vec or self.num_docs == 0:
            return []

        # Sparse accumulation
        scores: Dict[int, float] = {}
        postings = self.postings

        for term_idx, q_weight in query_vec.items():
            postings_list = postings.get(term_idx)
            if postings_list:
                for doc_idx, d_weight in postings_list:
                    scores[doc_idx] = scores.get(doc_idx, 0.0) + (q_weight * d_weight)

        if not scores:
            return []

        # Filter by min_score and sort
        scored_items = [
            (doc_idx, min(1.0, max(0.0, score)))
            for doc_idx, score in scores.items()
            if score >= min_score
        ]
        scored_items.sort(key=lambda x: x[1], reverse=True)
        return scored_items[:top_k]


def sparse_cosine_similarity(vec_a: Dict[int, float], vec_b: Dict[int, float]) -> float:
    """Compute cosine similarity between two unit-normalized sparse vectors."""
    if not vec_a or not vec_b:
        return 0.0
    
    # Iterate over smaller dict
    if len(vec_a) > len(vec_b):
        vec_a, vec_b = vec_b, vec_a

    dot_product = 0.0
    for idx, val_a in vec_a.items():
        val_b = vec_b.get(idx)
        if val_b is not None:
            dot_product += val_a * val_b

    return max(0.0, min(1.0, dot_product))


def batch_sparse_cosine_similarity(query_vec: Dict[int, float], vectors: List[Dict[int, float]]) -> List[float]:
    """Compute cosine similarities of a query vector against a list of vectors."""
    if not query_vec or not vectors:
        return [0.0] * len(vectors)
    return [sparse_cosine_similarity(query_vec, v) for v in vectors]

