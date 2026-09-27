import threading
from collections import OrderedDict
from typing import Dict, Any, Optional, List, Callable

class DocumentRegistry:
    """
    Thread-safe in-memory document registry with bounded capacity and LRU eviction.
    Prevents memory leaks in long-running services while providing fast O(1) lookups.
    """
    def __init__(self, max_documents: int = 100):
        self.max_documents = max(1, max_documents)
        self._store: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = threading.RLock()
        self._eviction_callbacks: List[Callable[[str], None]] = []

    def register_eviction_callback(self, callback: Callable[[str], None]) -> None:
        """Register a callback function to be called when a document is evicted or deleted."""
        with self._lock:
            self._eviction_callbacks.append(callback)

    def set(self, doc_id: str, document_data: Dict[str, Any]) -> None:
        """Store or update a document in the registry, applying LRU eviction if full."""
        evicted_ids = []
        with self._lock:
            if doc_id in self._store:
                self._store.move_to_end(doc_id)
            self._store[doc_id] = document_data
            
            # Evict oldest if exceeding capacity
            while len(self._store) > self.max_documents:
                evicted_id, _ = self._store.popitem(last=False)
                evicted_ids.append(evicted_id)

        # Notify callbacks outside lock to avoid deadlock
        for eid in evicted_ids:
            for cb in self._eviction_callbacks:
                try:
                    cb(eid)
                except Exception:
                    pass

    def get(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID and mark it as recently accessed."""
        with self._lock:
            if doc_id not in self._store:
                return None
            self._store.move_to_end(doc_id)
            return self._store[doc_id]

    def has(self, doc_id: str) -> bool:
        """Check if document ID exists in registry."""
        with self._lock:
            return doc_id in self._store

    def delete(self, doc_id: str) -> bool:
        """Remove a document from the registry and trigger eviction callbacks."""
        deleted = False
        with self._lock:
            if doc_id in self._store:
                del self._store[doc_id]
                deleted = True

        if deleted:
            for cb in self._eviction_callbacks:
                try:
                    cb(doc_id)
                except Exception:
                    pass
        return deleted

    def list_all(self) -> List[Dict[str, Any]]:
        """Return list of basic metadata for all currently stored documents."""
        with self._lock:
            summary = []
            for doc_id, data in self._store.items():
                summary.append({
                    "doc_id": doc_id,
                    "filename": data.get("filename", "Unknown"),
                    "total_segments": data.get("total_segments", 0),
                    "risk_tier": data.get("risk_analysis", {}).get("risk_tier", "N/A"),
                    "composite_score": data.get("risk_analysis", {}).get("composite_score", 0)
                })
            return summary

    def clear(self) -> None:
        """Clear all stored documents and notify listeners."""
        with self._lock:
            all_ids = list(self._store.keys())
            self._store.clear()

        for eid in all_ids:
            for cb in self._eviction_callbacks:
                try:
                    cb(eid)
                except Exception:
                    pass

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

    def __contains__(self, doc_id: str) -> bool:
        return self.has(doc_id)

    def __getitem__(self, doc_id: str) -> Dict[str, Any]:
        doc = self.get(doc_id)
        if doc is None:
            raise KeyError(f"Document '{doc_id}' not found in registry.")
        return doc

    def __setitem__(self, doc_id: str, document_data: Dict[str, Any]) -> None:
        self.set(doc_id, document_data)

# Global singleton registry instance
document_registry = DocumentRegistry(max_documents=100)
