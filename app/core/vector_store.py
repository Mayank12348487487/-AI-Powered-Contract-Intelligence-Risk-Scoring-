import logging
from typing import List, Dict, Any, Optional, Tuple

from app.core.vector_math import FastTFIDFVectorizer, SparseInvertedIndex, sparse_cosine_similarity
from app.core.registry import document_registry

logger = logging.getLogger(__name__)

class ContractVectorStore:
    def __init__(self):
        self.documents: Dict[str, Dict[str, Any]] = {}
        self._query_cache: Dict[Tuple[str, str, int], List[Dict[str, Any]]] = {}
        # Register for automatic eviction when registry evicts documents
        document_registry.register_eviction_callback(self.remove_document)

    def index_document(self, doc_id: str, segments: List[Dict[str, Any]], filename: str):
        """
        Build vector index and inverted posting list for a document's segments.
        """
        texts = [s["text"] for s in segments]
        if not texts:
            return

        vectorizer = FastTFIDFVectorizer(ngram_range=(1, 2), max_features=3000)
        embeddings = vectorizer.fit_transform(texts)
        inv_index = SparseInvertedIndex(embeddings)

        self.documents[doc_id] = {
            "doc_id": doc_id,
            "filename": filename,
            "segments": segments,
            "vectorizer": vectorizer,
            "embeddings": embeddings,
            "inv_index": inv_index,
            "total_segments": len(segments)
        }
        # Invalidate any previous query cache for this doc
        self._invalidate_doc_cache(doc_id)
        logger.info("Indexed document %s with %d segments into vector store", doc_id, len(segments))

    def remove_document(self, doc_id: str) -> bool:
        """Evict indexed document and cached queries from memory when pruned from document registry."""
        self._invalidate_doc_cache(doc_id)
        if doc_id in self.documents:
            del self.documents[doc_id]
            logger.debug("Evicted document %s from vector store cache", doc_id)
            return True
        return False

    def _invalidate_doc_cache(self, doc_id: str):
        keys_to_remove = [k for k in self._query_cache if k[0] == doc_id]
        for k in keys_to_remove:
            self._query_cache.pop(k, None)

    def semantic_search(self, doc_id: str, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """
        Perform high-speed inverted index vector search across document clauses.
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        doc_data = self.documents.get(doc_id)
        if not doc_data:
            return []

        cache_key = (doc_id, clean_query.lower(), top_k)
        if cache_key in self._query_cache:
            return self._query_cache[cache_key]

        vectorizer = doc_data["vectorizer"]
        inv_index: SparseInvertedIndex = doc_data["inv_index"]
        segments = doc_data["segments"]

        try:
            query_vec = vectorizer.transform([clean_query])[0]
            if not query_vec:
                return []

            matched = inv_index.query(query_vec, top_k=top_k, min_score=0.04)
            results = []
            for seg_idx, sim in matched:
                seg = segments[seg_idx]
                results.append({
                    "segment_id": seg["id"],
                    "heading": seg["heading"],
                    "text": seg["text"],
                    "page_number": seg.get("page_number", 1),
                    "similarity_score": round(float(sim), 4),
                    "primary_category": seg.get("primary_category", "General")
                })

            # Bounded LRU cache size (max 256 entries)
            if len(self._query_cache) > 256:
                self._query_cache.pop(next(iter(self._query_cache)), None)
            self._query_cache[cache_key] = results
            return results
        except Exception as e:
            logger.error("Semantic search failed: %s", str(e))
            return []

    def answer_contract_query(
        self,
        doc_id: str,
        query: str,
        entities: Optional[Dict[str, Any]] = None,
        risk_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Legal Q&A Assistant: synthesizes grounded legal answer for a contract query.
        """
        search_results = self.semantic_search(doc_id, query, top_k=3)
        
        q_lower = query.lower()
        answer = ""
        confidence = 0.85
        relevant_clause = None

        # 1. Direct Entity Matching if query asks for specific metadata
        if "liability" in q_lower or "cap" in q_lower or "maximum damages" in q_lower:
            for r in search_results:
                r_text_lower = r["text"].lower()
                if "liability" in r_text_lower or "cap" in r_text_lower:
                    relevant_clause = r
                    if "unlimited" in r_text_lower or "uncapped" in r_text_lower:
                        answer = f"⚠️ **Critical Alert:** The liability in this contract is **Unlimited / Uncapped** ({r['heading']}). Counterparty has not agreed to standard liability limitations."
                    else:
                        answer = f"The limitation of liability clause ({r['heading']}) states: \"{r['text'][:250]}...\""
                    break

        elif "parties" in q_lower or "who are the parties" in q_lower or "contracting party" in q_lower:
            if entities and entities.get("parties"):
                p_names = [f"**{p['name']}** ({p.get('role', 'Party')})" for p in entities["parties"]]
                answer = f"The contracting parties are: {', '.join(p_names)}."
            else:
                answer = "The contracting parties identified in the preamble of the document."

        elif "effective date" in q_lower or "start date" in q_lower or "commence" in q_lower:
            if entities and entities.get("effective_date"):
                answer = f"The Effective Date of this contract is **{entities['effective_date']['value']}**."
            else:
                answer = "The contract does not specify a distinct effective date."

        elif "expiration" in q_lower or "term" in q_lower or "how long" in q_lower or "duration" in q_lower:
            if entities and entities.get("expiration_date"):
                answer = f"The contract expires on **{entities['expiration_date']['value']}**."
            elif search_results:
                answer = f"According to {search_results[0]['heading']}: \"{search_results[0]['text'][:220]}...\""

        elif "governing law" in q_lower or "jurisdiction" in q_lower or "which state" in q_lower or "court" in q_lower:
            if entities and entities.get("governing_law"):
                answer = f"This contract is governed by the laws of **{entities['governing_law']['jurisdiction']}**."
            elif search_results:
                answer = f"According to {search_results[0]['heading']}: \"{search_results[0]['text'][:220]}...\""

        elif "non-compete" in q_lower or "compete" in q_lower or "competition" in q_lower:
            found = False
            for r in search_results:
                r_text_lower = r["text"].lower()
                if "non-compete" in r_text_lower or "compete" in r_text_lower:
                    found = True
                    relevant_clause = r
                    answer = f"Non-compete covenant found in **{r['heading']}**: \"{r['text'][:280]}...\""
                    break
            if not found:
                answer = "No explicit non-compete restriction was identified in the contract."

        elif "indemnif" in q_lower or "hold harmless" in q_lower or "indemnity" in q_lower:
            for r in search_results:
                r_text_lower = r["text"].lower()
                if "indemnif" in r_text_lower or "hold harmless" in r_text_lower:
                    relevant_clause = r
                    answer = f"Indemnification provision ({r['heading']}): \"{r['text'][:300]}...\""
                    break

        elif "intellectual property" in q_lower or " ip " in f" {q_lower} " or "ownership" in q_lower or "patent" in q_lower or "copyright" in q_lower or "work made for hire" in q_lower:
            for r in search_results:
                r_text_lower = r["text"].lower()
                if any(k in r_text_lower for k in ("intellectual property", "ownership", "title", "license", "proprietary", "patent")):
                    relevant_clause = r
                    answer = f"Intellectual Property & Ownership provision ({r['heading']}): \"{r['text'][:300]}...\""
                    break

        elif "confidential" in q_lower or "trade secret" in q_lower or "nda" in q_lower or "non-disclosure" in q_lower:
            for r in search_results:
                r_text_lower = r["text"].lower()
                if "confidential" in r_text_lower or "disclosure" in r_text_lower:
                    relevant_clause = r
                    answer = f"Confidentiality & Non-Disclosure clause ({r['heading']}): \"{r['text'][:300]}...\""
                    break

        elif "audit" in q_lower or "inspect" in q_lower or "books and records" in q_lower:
            for r in search_results:
                r_text_lower = r["text"].lower()
                if "audit" in r_text_lower or "inspect" in r_text_lower or "records" in r_text_lower:
                    relevant_clause = r
                    answer = f"Audit & Inspection Rights ({r['heading']}): \"{r['text'][:300]}...\""
                    break

        elif "warranty" in q_lower or "guarantee" in q_lower or "as is" in q_lower or "disclaimer" in q_lower:
            for r in search_results:
                r_text_lower = r["text"].lower()
                if any(k in r_text_lower for k in ("warrant", "as-is", "disclaimer", "merchantability", "fitness")):
                    relevant_clause = r
                    answer = f"Warranty & Disclaimer provision ({r['heading']}): \"{r['text'][:300]}...\""
                    break

        elif "force majeure" in q_lower or "act of god" in q_lower or "disaster" in q_lower or "pandemic" in q_lower:
            for r in search_results:
                r_text_lower = r["text"].lower()
                if any(k in r_text_lower for k in ("force majeure", "acts of god", "war", "disaster", "beyond reasonable control")):
                    relevant_clause = r
                    answer = f"Force Majeure provision ({r['heading']}): \"{r['text'][:300]}...\""
                    break

        elif "assign" in q_lower or "assignment" in q_lower or "transfer" in q_lower or "merger" in q_lower:
            for r in search_results:
                r_text_lower = r["text"].lower()
                if any(k in r_text_lower for k in ("assign", "transfer", "merger", "successor", "consent")):
                    relevant_clause = r
                    answer = f"Assignment & Transfer provision ({r['heading']}): \"{r['text'][:300]}...\""
                    break

        elif "insurance" in q_lower or "coverage" in q_lower or "policy" in q_lower:
            for r in search_results:
                r_text_lower = r["text"].lower()
                if any(k in r_text_lower for k in ("insurance", "policy", "coverage", "liability insurance")):
                    relevant_clause = r
                    answer = f"Insurance Requirements ({r['heading']}): \"{r['text'][:300]}...\""
                    break

        elif "payment" in q_lower or "fee" in q_lower or "invoice" in q_lower or "pricing" in q_lower:
            for r in search_results:
                r_text_lower = r["text"].lower()
                if any(k in r_text_lower for k in ("pay", "fee", "invoice", "net 30", "due date", "price")):
                    relevant_clause = r
                    answer = f"Payment & Pricing Terms ({r['heading']}): \"{r['text'][:300]}...\""
                    break

        # Fallback to top semantic vector search result
        if not answer:
            if search_results:
                relevant_clause = search_results[0]
                answer = f"Based on {search_results[0]['heading']}: \"{search_results[0]['text'][:300]}...\""
            else:
                answer = "I could not find a directly matching clause for your question in this contract."
                confidence = 0.40

        return {
            "query": query,
            "answer": answer,
            "confidence": confidence,
            "cited_clause": relevant_clause,
            "top_semantic_matches": search_results
        }

# Global singleton
vector_store = ContractVectorStore()
