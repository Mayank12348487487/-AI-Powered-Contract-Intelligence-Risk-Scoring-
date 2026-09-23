import json
import re
import logging
from typing import List, Dict, Any, Optional

from app.config import DATA_DIR
from app.core.vector_math import FastTFIDFVectorizer, sparse_cosine_similarity

logger = logging.getLogger(__name__)

class CUADClauseClassifier:
    def __init__(self):
        self.schema_path = DATA_DIR / "cuad_schema.json"
        self.categories: List[Dict[str, Any]] = []
        self.category_map: Dict[str, Dict[str, Any]] = {}
        self.vectorizer: Optional[FastTFIDFVectorizer] = None
        self.category_embeddings: List[Dict[int, float]] = []
        self._load_schema_and_initialize()

    def _load_schema_and_initialize(self):
        """Load CUAD 41 categories schema and initialize semantic match index."""
        try:
            with open(self.schema_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.categories = data.get("categories", [])
                self.category_map = {c["id"]: c for c in self.categories}

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
        for idx, cat_vec in enumerate(self.category_embeddings):
            sim = sparse_cosine_similarity(query_vec, cat_vec)
            cat = self.categories[idx]
            cat_id = cat["id"]
            
            # 2. Keyword & Heuristic Boosting
            bonus = 0.0
            for kw in cat.get("keywords", []):
                if re.search(rf'\b{re.escape(kw.lower())}\b', cleaned):
                    bonus += 0.18

            # Specific high-accuracy legal phrase triggers
            if cat_id == "cap_on_liability" and re.search(r'aggregate liability|limitation of liability|exceed the total fees', cleaned):
                bonus += 0.35
            elif cat_id == "unlimited_liability" and re.search(r'unlimited liability|shall not be subject to any cap|uncapped', cleaned):
                bonus += 0.40
            elif cat_id == "non_compete" and re.search(r'non-compete|competing business|covenant not to compete', cleaned):
                bonus += 0.40
            elif cat_id == "ip_ownership_assignment" and re.search(r'assigns all right title|work made for hire|exclusive ownership', cleaned):
                bonus += 0.35
            elif cat_id == "mutual_indemnification" and re.search(r'each party shall indemnify|mutually defend|mutual indemn', cleaned):
                bonus += 0.35
            elif cat_id == "unilateral_indemnification" and re.search(r'indemnify, defend, and hold harmless licensor|contractor agrees to defend and indemnify client', cleaned):
                bonus += 0.35
            elif cat_id == "termination_for_convenience" and re.search(r'for convenience|without cause|terminate at will', cleaned):
                bonus += 0.35
            elif cat_id == "force_majeure" and re.search(r'force majeure|acts of god|war|disaster', cleaned):
                bonus += 0.40
            elif cat_id == "governing_law" and re.search(r'governed by|laws of the state|jurisdiction', cleaned):
                bonus += 0.35
            elif cat_id == "renewal_term" and re.search(r'automatically renew|renewal term|successive', cleaned):
                bonus += 0.35
            elif cat_id == "audit_rights" and re.search(r'right to audit|inspect books|independent auditor', cleaned):
                bonus += 0.35

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
            seg_copy["cuad_categories"] = matches
            seg_copy["primary_category"] = matches[0]["name"] if matches else "General Contract Provisions"
            seg_copy["primary_category_id"] = matches[0]["category_id"] if matches else "general"
            seg_copy["category_confidence"] = matches[0]["confidence"] if matches else 0.0
            enriched_segments.append(seg_copy)
        return enriched_segments

    def get_detected_categories_summary(self, enriched_segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Summarize which CUAD categories are present, their counts, and missing essential categories.
        """
        detected = {}
        for seg in enriched_segments:
            for m in seg.get("cuad_categories", []):
                cat_id = m["category_id"]
                if cat_id not in detected:
                    detected[cat_id] = {
                        "category_id": cat_id,
                        "name": m["name"],
                        "importance": m["importance"],
                        "count": 0,
                        "highest_confidence": 0.0,
                        "sample_segment_id": seg["id"]
                    }
                detected[cat_id]["count"] += 1
                detected[cat_id]["highest_confidence"] = max(detected[cat_id]["highest_confidence"], m["confidence"])

        # Check for missing essential categories (CUAD Atticus standard)
        essential_categories = [
            "parties", "effective_date", "expiration_date", "governing_law",
            "cap_on_liability", "mutual_indemnification", "force_majeure",
            "termination_for_convenience", "confidentiality"
        ]

        missing_essential = []
        for cat_id in essential_categories:
            if cat_id not in detected and cat_id in self.category_map:
                missing_essential.append({
                    "category_id": cat_id,
                    "name": self.category_map[cat_id]["name"],
                    "importance": self.category_map[cat_id].get("importance", "Essential"),
                    "mitigation_guidance": self.category_map[cat_id].get("mitigation_guidance", ""),
                    "standard_safe_clause": self.category_map[cat_id].get("standard_safe_clause", "")
                })

        return {
            "total_detected_categories": len(detected),
            "detected_categories": list(detected.values()),
            "missing_essential_categories": missing_essential
        }

# Global singleton
clause_classifier = CUADClauseClassifier()
