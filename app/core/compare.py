import logging
from typing import Dict, Any, List

from app.core.vector_math import FastTFIDFVectorizer, sparse_cosine_similarity

logger = logging.getLogger(__name__)

class ContractComparator:
    @staticmethod
    def compare_contracts(
        contract_a: Dict[str, Any],
        contract_b: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare two contract analyses and generate detailed redline diff and risk shift analysis.
        """
        score_a = contract_a.get("risk_analysis", {}).get("composite_score", 0)
        score_b = contract_b.get("risk_analysis", {}).get("composite_score", 0)
        risk_delta = score_b - score_a

        tier_a = contract_a.get("risk_analysis", {}).get("risk_tier", "LOW")
        tier_b = contract_b.get("risk_analysis", {}).get("risk_tier", "LOW")

        # Key entity comparisons
        ent_a = contract_a.get("entities", {})
        ent_b = contract_b.get("entities", {})

        entity_diffs = []

        # Parties
        parties_a_names = [p.get("name", "") for p in ent_a.get("parties", [])] if ent_a.get("parties") else []
        parties_b_names = [p.get("name", "") for p in ent_b.get("parties", [])] if ent_b.get("parties") else []
        str_a = ", ".join(parties_a_names) if parties_a_names else "Unspecified"
        str_b = ", ".join(parties_b_names) if parties_b_names else "Unspecified"
        if set(parties_a_names) != set(parties_b_names) and (parties_a_names or parties_b_names):
            entity_diffs.append({
                "field": "Contracting Parties",
                "contract_a": str_a,
                "contract_b": str_b,
                "impact": "Discrepancy in identified contracting parties or corporate entities."
            })

        # Governing Law
        law_a = ent_a.get("governing_law", {}).get("jurisdiction", "Unspecified") if ent_a.get("governing_law") else "Unspecified"
        law_b = ent_b.get("governing_law", {}).get("jurisdiction", "Unspecified") if ent_b.get("governing_law") else "Unspecified"
        if law_a != law_b:
            entity_diffs.append({
                "field": "Governing Law / Jurisdiction",
                "contract_a": law_a,
                "contract_b": law_b,
                "impact": "Jurisdiction changed from standard domestic to foreign/alternate forum."
            })

        # Effective Date
        eff_a = ent_a.get("effective_date", {}).get("value", "N/A") if ent_a.get("effective_date") else "N/A"
        eff_b = ent_b.get("effective_date", {}).get("value", "N/A") if ent_b.get("effective_date") else "N/A"
        if eff_a != eff_b:
            entity_diffs.append({
                "field": "Effective Date",
                "contract_a": eff_a,
                "contract_b": eff_b,
                "impact": "Effective timeline shift."
            })

        # Expiration Date
        exp_a = ent_a.get("expiration_date", {}).get("value", "N/A") if ent_a.get("expiration_date") else "N/A"
        exp_b = ent_b.get("expiration_date", {}).get("value", "N/A") if ent_b.get("expiration_date") else "N/A"
        if exp_a != exp_b:
            entity_diffs.append({
                "field": "Expiration / Term",
                "contract_a": exp_a,
                "contract_b": exp_b,
                "impact": "Contract duration or expiration date altered."
            })

        # Clause-by-clause similarity alignment
        segs_a = contract_a.get("segments", [])
        segs_b = contract_b.get("segments", [])

        clause_comparisons = []
        texts_b = [s["text"] for s in segs_b]

        if segs_a and texts_b:
            try:
                vectorizer = FastTFIDFVectorizer(ngram_range=(1, 2), max_features=3000)
                tfidf_b = vectorizer.fit_transform(texts_b)
                for seg_a in segs_a:
                    vec_a = vectorizer.transform([seg_a["text"]])[0]
                    sims = [sparse_cosine_similarity(vec_a, vec_b) for vec_b in tfidf_b]
                    
                    if sims:
                        best_sim = max(sims)
                        best_match_idx = sims.index(best_sim)
                    else:
                        best_sim = 0.0
                        best_match_idx = 0

                    if best_sim > 0.40:
                        seg_b = segs_b[best_match_idx]
                        status = "Identical" if best_sim > 0.95 else "Modified"
                        clause_comparisons.append({
                            "category": seg_a.get("primary_category", "General"),
                            "status": status,
                            "similarity": round(best_sim, 2),
                            "clause_a": {
                                "heading": seg_a["heading"],
                                "text": seg_a["text"]
                            },
                            "clause_b": {
                                "heading": seg_b["heading"],
                                "text": seg_b["text"]
                            }
                        })
                    else:
                        clause_comparisons.append({
                            "category": seg_a.get("primary_category", "General"),
                            "status": "Removed in Contract B",
                            "similarity": round(best_sim, 2),
                            "clause_a": {
                                "heading": seg_a["heading"],
                                "text": seg_a["text"]
                            },
                            "clause_b": None
                        })
            except Exception as e:
                logger.error("Clause comparison failed: %s", str(e))

        # Anomalies delta
        anomalies_a = contract_a.get("risk_analysis", {}).get("anomalies", [])
        anomalies_b = contract_b.get("risk_analysis", {}).get("anomalies", [])

        return {
            "contract_a_name": contract_a.get("filename", "Contract A"),
            "contract_b_name": contract_b.get("filename", "Contract B"),
            "score_a": score_a,
            "score_b": score_b,
            "tier_a": tier_a,
            "tier_b": tier_b,
            "risk_delta": risk_delta,
            "risk_trend": "INCREASED RISK" if risk_delta > 0 else ("REDUCED RISK" if risk_delta < 0 else "IDENTICAL RISK"),
            "entity_differences": entity_diffs,
            "anomalies_count_a": len(anomalies_a),
            "anomalies_count_b": len(anomalies_b),
            "clause_comparisons": clause_comparisons[:15]
        }

contract_comparator = ContractComparator()
