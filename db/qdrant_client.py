import os
from functools import lru_cache
from qdrant_client import QdrantClient

@lru_cache(maxsize=1)
def get_qdrant_client():
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    api_key = os.getenv("QDRANT_API_KEY", "").strip() or None
    return QdrantClient(url=url, api_key=api_key, timeout=30)
