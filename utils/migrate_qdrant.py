"""Utility to migrate vectors and metadata from local Qdrant to Qdrant Cloud."""

import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

def migrate(local_url="http://localhost:6333", target_url=None, target_api_key=None, collection_name="vidrag_transcripts"):
    target_url = target_url or os.getenv("TARGET_QDRANT_URL") or os.getenv("QDRANT_URL")
    target_api_key = target_api_key or os.getenv("TARGET_QDRANT_API_KEY") or os.getenv("QDRANT_API_KEY")

    if not target_url or "localhost" in target_url:
        print("Please provide a valid remote QDRANT_URL (e.g. your Qdrant Cloud cluster URL).")
        return

    print(f"Connecting to local Qdrant at {local_url}...")
    local_client = QdrantClient(url=local_url, timeout=30)

    print(f"Connecting to target Qdrant at {target_url}...")
    target_client = QdrantClient(url=target_url, api_key=target_api_key, timeout=60)

    # Ensure collection exists on target
    target_collections = {c.name for c in target_client.get_collections().collections}
    if collection_name not in target_collections:
        print(f"Creating collection '{collection_name}' (768 dimensions, Cosine) on target...")
        target_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE)
        )

    # Scroll and transfer points
    print(f"Reading points from local collection '{collection_name}'...")
    offset = None
    total_migrated = 0

    while True:
        points, offset = local_client.scroll(
            collection_name=collection_name,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=True
        )
        if not points:
            break

        to_upsert = [
            PointStruct(id=p.id, vector=p.vector, payload=p.payload)
            for p in points
        ]
        target_client.upsert(collection_name=collection_name, points=to_upsert)
        total_migrated += len(to_upsert)
        print(f"Migrated {total_migrated} points...")

        if offset is None:
            break

    print(f"Migration complete! Successfully transferred {total_migrated} vectors to Qdrant Cloud.")

if __name__ == "__main__":
    migrate()
