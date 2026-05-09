import os
import threading
import faiss
import numpy as np
from app.core.config import settings

_org_locks: dict[str, threading.RLock] = {}
_global_lock = threading.Lock()

def _get_lock(org_id: str) -> threading.RLock:
    """
    Get a reentrant lock specific to an organization for thread-safe file operations.
    """
    with _global_lock:
        if org_id not in _org_locks:
            _org_locks[org_id] = threading.RLock()
        return _org_locks[org_id]

def _get_index_path(org_id: str) -> str:
    """
    Get the file path for the organization's FAISS index.
    Ensures the parent directory exists.
    """
    os.makedirs(settings.FAISS_INDEX_DIR, exist_ok=True)
    return os.path.join(settings.FAISS_INDEX_DIR, f"{org_id}.index")

def load_index(org_id: str) -> faiss.IndexFlatL2:
    """
    Load the FAISS index for the organization.
    Creates a new IndexFlatL2(768) if it doesn't exist.
    """
    path = _get_index_path(org_id)
    with _get_lock(org_id):
        if os.path.exists(path):
            return faiss.read_index(path)
        else:
            return faiss.IndexFlatL2(768)

def save_index(org_id: str, index: faiss.IndexFlatL2) -> None:
    """
    Save the FAISS index for the organization to disk in a thread-safe manner.
    """
    path = _get_index_path(org_id)
    with _get_lock(org_id):
        faiss.write_index(index, path)

def add_vectors(org_id: str, vectors: list[list[float]], chunk_db_ids: list[int]) -> list[int]:
    """
    Add vectors to the organization's FAISS index.
    Returns list of FAISS internal integer IDs (position in index).
    """
    if not vectors:
        return []
    
    if len(vectors) != len(chunk_db_ids):
        raise ValueError("Length of vectors and chunk_db_ids must match")
    
    with _get_lock(org_id):
        index = load_index(org_id)
        start_id = index.ntotal
        index.add(np.array(vectors, dtype=np.float32))
        end_id = index.ntotal
        save_index(org_id, index)
        
    return list(range(start_id, end_id))

def search_vectors(org_id: str, query_vector: list[float], top_k: int = 5) -> list[int]:
    """
    Search for the nearest neighbors of a query vector in the organization's index.
    Returns list of FAISS internal integer IDs of nearest neighbors.
    """
    index = load_index(org_id)
        
    if index.ntotal == 0:
        return []
        
    k = min(top_k, index.ntotal)
    query_np = np.array([query_vector], dtype=np.float32)
    
    # distances is D, indices is I
    distances, indices = index.search(query_np, k)
    
    return [int(idx) for idx in indices[0] if idx != -1]

def remove_vectors(org_id: str, faiss_ids: list[int]) -> dict[int, int]:
    if not faiss_ids:
        return {}
    with _get_lock(org_id):
        index = load_index(org_id)
        if index.ntotal == 0:
            return {}
        # Rebuild index excluding the removed IDs
        all_vectors = index.reconstruct_n(0, index.ntotal)
        faiss_ids_set = set(faiss_ids)
        keep_indices = [i for i in range(index.ntotal) if i not in faiss_ids_set]
        new_index = faiss.IndexFlatL2(768)
        if keep_indices:
            kept_vectors = np.array([all_vectors[i] for i in keep_indices], dtype=np.float32)
            new_index.add(kept_vectors)
        save_index(org_id, new_index)
        
        # Map old index to new index
        mapping = {}
        for new_idx, old_idx in enumerate(keep_indices):
            mapping[old_idx] = new_idx
        return mapping
