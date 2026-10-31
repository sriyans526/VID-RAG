from functools import lru_cache
from sentence_transformers import CrossEncoder

class RerankerService:
    @staticmethod
    @lru_cache(maxsize=1)
    def get_model():
        return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2",device="cpu")

    @classmethod
    def rerank(cls,query,docs,top_k=None):
        if not docs: return []
        try:
            scores=cls.get_model().predict([(query,d.page_content) for d in docs])
            ranked=[d for d,_ in sorted(zip(docs,scores),key=lambda pair:pair[1],reverse=True)]
        except Exception:
            ranked=docs
        return ranked[:top_k] if top_k else ranked
