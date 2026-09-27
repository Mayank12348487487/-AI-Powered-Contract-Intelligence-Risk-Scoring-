import json
import re
import logging
from typing import List, Dict, Any, Optional, Tuple

from app.config import DATA_DIR
from app.core.vector_math import FastTFIDFVectorizer, sparse_cosine_similarity

logger = logging.getLogger(__name__)

# Precompiled high-accuracy phrase triggers
PHRASE_TRIGGERS: Dict[str, Tuple[re.Pattern, float]] = {
    "cap_on_liability": (
        re.compile(r'aggregate liability|limitation of liability|exceed the total fees', re.IGNORECASE),
        0.35
    ),
    "unlimited_liability": (
        re.compile(r'unlimited liability|shall not be subject to any cap|uncapped', re.IGNORECASE),
        0.40
    ),
    "non_compete": (
        re.compile(r'non-compete|competing business|covenant not to compete', re.IGNORECASE),
        0.40
    ),
    "ip_ownership_assignment": (
        re.compile(r'assigns all right title|work made for hire|exclusive ownership', re.IGNORECASE),
        0.35
    ),
    "mutual_indemnification": (
        re.compile(r'each party shall indemnify|mutually defend|mutual indemn', re.IGNORECASE),
        0.35
    ),
    "unilateral_indemnification": (
        re.compile(r'indemnify, defend, and hold harmless licensor|contractor agrees to defend and indemnify client', re.IGNORECASE),
        0.35
    ),
    "termination_for_convenience": (
        re.compile(r'for convenience|without cause|terminate at will', re.IGNORECASE),
        0.35
    ),
    "force_majeure": (
        re.compile(r'force majeure|acts of god|war|disaster', re.IGNORECASE),
        0.40
    ),
    "governing_law": (
        re.compile(r'governed by|laws of the state|jurisdiction', re.IGNORECASE),
        0.35
    ),
    "renewal_term": (
        re.compile(r'automatically renew|renewal term|successive', re.IGNORECASE),
        0.35
    ),
    "audit_rights": (
        re.compile(r'right to audit|inspect books|independent auditor', re.IGNORECASE),
        0.35
    ),
}

ESSENTIAL_CATEGORIES = [
    "parties", "effective_date", "expiration_date", "governing_law",
    "cap_on_liability", "mutual_indemnification", "force_majeure",
    "termination_for_convenience", "confidentiality"
]

class CUADClauseClassifier:
    def __init__(self):
        self.schema_path = DATA_DIR / "cuad_schema.json"
        self.categories: List[Dict[str, Any]] = []
        self.category_map: Dict[str, Dict[str, Any]] = {}
        self.vectorizer: Optional[FastTFIDFVectorizer] = None
        self.category_embeddings: List[Dict[int, float]] = []
        self.category_kw_regexes: Dict[str, Optional[re.Pattern]] = {}
        self._load_schema_and_initialize()

    def _load_schema_and_initialize(self):
        """Load CUAD 41 categories schema and initialize semantic match index."""
        try:
            with open(self.schema_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.categories = data.get("categories", [])
                self.category_map = {c["id"]: c for c in self.categories}

            # Precompile keyword patterns for fast multi-keyword matching
            for c in self.categories:
                cat_id = c["id"]
                kws = c.get("keywords", [])
                if kws:
                    # Sort by length descending to match longest phrases first
                    sorted_kws = sorted(kws, key=len, reverse=True)
                    pattern = r'\b(?:' + '|'.join(re.escape(k.lower()) for k in sorted_kws) + r')\b'
                    self.category_kw_regexes[cat_id] = re.compile(pattern, re.IGNORECASE)
                else:
                    self.category_kw_regexes[cat_id] = None

            # Build semantic corpus for TF-IDF / embedding matching
            corpus = []
            for c in self.categories:
                keywords_str = " ".join(c.get("keywords", []))
                text_rep = f"{c['name']} {c['description']} {keywords_str} {c.get('standard_safe_clause', '')}"
                corpus.append(text_rep)

            self.vectorizer = FastTFIDFVectorizer(ngram_range=(1, 2), max_features=5000)
            self.category_embeddings = self.vectorizer.fit_transform(corpus)
            logger.info("Initialized CUAD Clause Classifier with %d categories", len(self.categories))
        except Exception as e:
            logger.error("Failed to initialize CUAD schema: %s", str(e))
            self.categories = []

    def classify_clause(self, clause_text: str, top_k: int = 2) -> List[Dict[str, Any]]:
        """
        Classify a single contract clause against the 41 CUAD legal categories.
        Returns top matched categories with confidence and guidance.
        """
        if not clause_text or not self.categories or self.vectorizer is None:
            return []

        cleaned = clause_text.strip().lower()
        if len(cleaned) < 15:
            return []

        # 1. Semantic Similarity Match
        query_vec = self.vectorizer.transform([cleaned])[0]

        matches = []
        cat_embeddings = self.category_embeddings
        categories = self.categories
        kw_regexes = self.category_kw_regexes

        for idx, cat in enumerate(categories):
            cat_vec = cat_embeddings[idx]
            sim = sparse_cosine_similarity(query_vec, cat_vec)
            cat_id = cat["id"]
            
            # 2. Fast Keyword Boosting via precompiled single pattern
            bonus = 0.0
            kw_regex = kw_regexes.get(cat_id)
            if kw_regex and kw_regex.search(cleaned):
                bonus += 0.18

            # 3. High-accuracy phrase triggers
            trigger = PHRASE_TRIGGERS.get(cat_id)
            if trigger and trigger[0].search(cleaned):
                bonus += trigger[1]

            final_conf = min(0.99, float(sim * 0.55 + bonus))
            
            if final_conf >= 0.30:
                matches.append({
                    "category_id": cat_id,
                    "name": cat["name"],
                    "confidence": round(final_conf, 3),
                    "importance": cat.get("importance", "Medium"),
                    "risk_level_default": cat.get("risk_level_default", "Low"),
                    "mitigation_guidance": cat.get("mitigation_guidance", ""),
                    "standard_safe_clause": cat.get("standard_safe_clause", "")
                })

        # Sort by confidence descending
        matches.sort(key=lambda x: x["confidence"], reverse=True)
        return matches[:top_k]

    def classify_document_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Classify all segments in a document and enrich them with CUAD category metadata.
        """
        enriched_segments = []
        for seg in segments:
            seg_copy = dict(seg)
            matches = self.classify_clause(seg["text"])
            if matches:
                top_match = matches[0]
                seg_copy["cuad_categories"] = matches
                seg_copy["primary_category"] = top_match["name"]
                seg_copy["primary_category_id"] = top_match["category_id"]
                seg_copy["category_confidence"] = top_match["confidence"]
            else:
                seg_copy["cuad_categories"] = []
                seg_copy["primary_category"] = "General Contract Provisions"
                seg_copy["primary_category_id"] = "general"
                seg_copy["category_confidence"] = 0.0
            enriched_segments.append(seg_copy)
        return enriched_segments

    def get_detected_categories_summary(self, enriched_segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Summarize which CUAD categories are present, their counts, and missing essential categories.
        """
        detected: Dict[str, Dict[str, Any]] = {}
        for seg in enriched_segments:
            for m in seg.get("cuad_categories", []):
                cat_id = m["category_id"]
                entry = detected.get(cat_id)
                if entry is None:
                    detected[cat_id] = {
                        "category_id": cat_id,
                        "name": m["name"],
                        "importance": m["importance"],
                        "count": 1,
                        "highest_confidence": m["confidence"],
                        "sample_segment_id": seg["id"]
                    }
                else:
                    entry["count"] += 1
                    if m["confidence"] > entry["highest_confidence"]:
                        entry["highest_confidence"] = m["confidence"]

        # Check for missing essential categories (CUAD Atticus standard)
        cat_map = self.category_map
        missing_essential = []
        for cat_id in ESSENTIAL_CATEGORIES:
            if cat_id not in detected and cat_id in cat_map:
                cat_info = cat_map[cat_id]
                missing_essential.append({
                    "category_id": cat_id,
                    "name": cat_info["name"],
                    "importance": cat_info.get("importance", "Essential"),
                    "mitigation_guidance": cat_info.get("mitigation_guidance", ""),
                    "standard_safe_clause": cat_info.get("standard_safe_clause", "")
                })

        return {
            "total_detected_categories": len(detected),
            "detected_categories": list(detected.values()),
            "missing_essential_categories": missing_essential
        }

# Global singleton
clause_classifier = CUADClauseClassifier()
