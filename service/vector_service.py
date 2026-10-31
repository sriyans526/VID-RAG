import os
from qdrant_client.models import Distance, VectorParams, Filter, FieldCondition, MatchValue
from langchain_qdrant import QdrantVectorStore
from db.qdrant_client import get_qdrant_client
from service.embedding_service import EmbeddingService

class VectorService:
    def __init__(self):
        self.client=get_qdrant_client()
        self.collection_name=os.getenv("QDRANT_COLLECTION","vidrag_transcripts")
        self.embedding=EmbeddingService.get_model()
        names={c.name for c in self.client.get_collections().collections}
        if self.collection_name not in names:
            self.client.create_collection(collection_name=self.collection_name,
              vectors_config=VectorParams(size=768,distance=Distance.COSINE))
        self.store=QdrantVectorStore(client=self.client,collection_name=self.collection_name,embedding=self.embedding)

    def _filter(self, source_id):
        return Filter(must=[FieldCondition(key="metadata.video_id",match=MatchValue(value=source_id))])

    def has_video(self, video_id):
        return self.client.count(collection_name=self.collection_name,count_filter=self._filter(video_id),exact=True).count>0

    def add_documents(self, docs, replace=False):
        if not docs: return 0
        source_id=str(docs[0].metadata["video_id"])
        if replace: self.client.delete(collection_name=self.collection_name,points_selector=self._filter(source_id),wait=True)
        elif self.has_video(source_id): return 0
        self.store.add_documents(docs)
        return len(docs)

    def search(self, query, video_id, k=12):
        return self.store.similarity_search(query=query,k=k,filter=self._filter(video_id))

    def search_many(self, query, source_ids, k=6):
        # Search within each source separately, then merge by retrieval order to avoid cross-tenant leaks.
        found=[]
        for source_id in source_ids:
            try:
                for doc in self.store.similarity_search(query=query,k=max(1,k),filter=self._filter(source_id)):
                    doc.metadata.setdefault('source_id', source_id)
                    found.append(doc)
            except Exception:
                continue
        return found[:k*max(1,len(source_ids))]

    def delete_video(self, video_id):
        self.client.delete(collection_name=self.collection_name,points_selector=self._filter(video_id),wait=True)
