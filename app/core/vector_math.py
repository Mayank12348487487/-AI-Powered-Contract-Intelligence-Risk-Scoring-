import math
import re
from typing import List, Dict, Tuple, Set
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

class FastTFIDFVectorizer:
    """
    High-performance, pure-Python TF-IDF vectorizer with n-grams and L2 normalization.
    Zero C-threading dependencies, ultra-fast and lightweight.
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
                # Sublinear TF scaling: 1 + log(tf)
                val = (1.0 + math.log(count)) * idf[idx]
                sparse_vec[idx] = val
                sq_sum += val * val

        # L2 Normalization
        if sq_sum > 0:
            norm = 1.0 / math.sqrt(sq_sum)
            for idx in sparse_vec:
                sparse_vec[idx] *= norm

        return sparse_vec

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
