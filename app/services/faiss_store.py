import os
import threading
import faiss
import numpy as np
from app.core.config import settings

_org_locks: dict[str, threading.RLock] = {}
_global_lock = threading.Lock()

def _get_lock(org_id: str) -> threading.RLock:
    with _global_lock:
        if org_id not in _org_locks:
            _org_locks[org_id] = threading.RLock()
        return _org_locks[org_id]

def _get_index_path(org_id: str) -> str:
    os.makedirs(settings.FAISS_INDEX_DIR, exist_ok=True)
    return os.path.join(settings.FAISS_INDEX_DIR, f"{org_id}.index")

def _load_index_unsafe(org_id: str) -> faiss.IndexFlatL2:
    """Load index WITHOUT acquiring lock. Caller must hold the lock."""
    path = _get_index_path(org_id)
    if os.path.exists(path):
        return faiss.read_index(path)
    return faiss.IndexFlatL2(3072)

def _save_index_unsafe(org_id: str, index: faiss.IndexFlatL2) -> None:
    """Save index WITHOUT acquiring lock. Caller must hold the lock."""
    path = _get_index_path(org_id)
    faiss.write_index(index, path)

def load_index(org_id: str) -> faiss.IndexFlatL2:
    """Public safe load — acquires lock."""
    with _get_lock(org_id):
        return _load_index_unsafe(org_id)

def save_index(org_id: str, index: faiss.IndexFlatL2) -> None:
    """Public safe save — acquires lock."""
    with _get_lock(org_id):
        _save_index_unsafe(org_id, index)

def add_vectors(org_id: str, vectors: list[list[float]], chunk_db_ids: list) -> list[int]:
    if not vectors:
        return []
    if len(vectors) != len(chunk_db_ids):
        raise ValueError("Length of vectors and chunk_db_ids must match")
    with _get_lock(org_id):
        index = _load_index_unsafe(org_id)
        start_id = index.ntotal
        index.add(np.array(vectors, dtype=np.float32))
        _save_index_unsafe(org_id, index)
    return list(range(start_id, start_id + len(vectors)))

def search_vectors(org_id: str, query_vector: list[float], top_k: int = 5) -> list[int]:
    with _get_lock(org_id):
        index = _load_index_unsafe(org_id)
        if index.ntotal == 0:
            return []
        k = min(top_k, index.ntotal)
        query_np = np.array([query_vector], dtype=np.float32)
        distances, indices = index.search(query_np, k)
    return [int(idx) for idx in indices[0] if idx != -1]

def remove_vectors(org_id: str, faiss_ids: list[int]) -> dict[int, int]:
    if not faiss_ids:
        return {}
    with _get_lock(org_id):
        index = _load_index_unsafe(org_id)
        if index.ntotal == 0:
            return {}
        all_vectors = index.reconstruct_n(0, index.ntotal)
        faiss_ids_set = set(faiss_ids)
        keep_indices = [i for i in range(index.ntotal) if i not in faiss_ids_set]
        new_index = faiss.IndexFlatL2(3072)
        if keep_indices:
            kept_vectors = np.array([all_vectors[i] for i in keep_indices], dtype=np.float32)
            new_index.add(kept_vectors)
        _save_index_unsafe(org_id, new_index)
        return {old_idx: new_idx for new_idx, old_idx in enumerate(keep_indices)}
