import re
import logging
from typing import List, Dict, Any, Optional

from app.core.vector_math import FastTFIDFVectorizer, sparse_cosine_similarity

logger = logging.getLogger(__name__)

class ContractVectorStore:
    def __init__(self):
        self.documents: Dict[str, Dict[str, Any]] = {}

    def index_document(self, doc_id: str, segments: List[Dict[str, Any]], filename: str):
        """
        Build vector index for a document's segments.
        """
        texts = [s["text"] for s in segments]
        if not texts:
            return

        vectorizer = FastTFIDFVectorizer(ngram_range=(1, 2), max_features=3000)
        embeddings = vectorizer.fit_transform(texts)

        self.documents[doc_id] = {
            "doc_id": doc_id,
            "filename": filename,
            "segments": segments,
            "vectorizer": vectorizer,
            "embeddings": embeddings,
            "total_segments": len(segments)
        }
        logger.info("Indexed document %s with %d segments into vector store", doc_id, len(segments))

    def semantic_search(self, doc_id: str, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """
        Perform dense semantic vector search across document clauses.
        """
        if doc_id not in self.documents or not query.strip():
            return []

        doc_data = self.documents[doc_id]
        vectorizer = doc_data["vectorizer"]
        embeddings = doc_data["embeddings"]
        segments = doc_data["segments"]

        try:
            query_vec = vectorizer.transform([query])[0]

            results = []
            for idx, seg_vec in enumerate(embeddings):
                sim = sparse_cosine_similarity(query_vec, seg_vec)
                if sim > 0.04:
                    seg = segments[idx]
                    results.append({
                        "segment_id": seg["id"],
                        "heading": seg["heading"],
                        "text": seg["text"],
                        "page_number": seg.get("page_number", 1),
                        "similarity_score": round(float(sim), 4),
                        "primary_category": seg.get("primary_category", "General")
                    })

            results.sort(key=lambda x: x["similarity_score"], reverse=True)
            return results[:top_k]
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
            # Check search results first
            for r in search_results:
                if "liability" in r["text"].lower() or "cap" in r["text"].lower():
                    relevant_clause = r
                    if "unlimited" in r["text"].lower() or "uncapped" in r["text"].lower():
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
                if "non-compete" in r["text"].lower() or "compete" in r["text"].lower():
                    found = True
                    relevant_clause = r
                    answer = f"Non-compete covenant found in **{r['heading']}**: \"{r['text'][:280]}...\""
                    break
            if not found:
                answer = "No explicit non-compete restriction was identified in the contract."

        elif "notice" in q_lower or "renewal" in q_lower or "terminate" in q_lower:
            if search_results:
                relevant_clause = search_results[0]
                answer = f"Regarding termination and notice terms ({search_results[0]['heading']}): \"{search_results[0]['text'][:300]}...\""

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
