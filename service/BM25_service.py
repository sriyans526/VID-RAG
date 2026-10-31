from rank_bm25 import BM25Okapi

class BM25Service:
    def __init__(self,docs):
        self.docs=docs
        self.model=BM25Okapi([d.page_content.lower().split() for d in docs]) if docs else None
    def search(self,query,top_k=5):
        if not self.model: return []
        scores=self.model.get_scores(query.lower().split())
        ranked=sorted(zip(self.docs,scores),key=lambda pair:pair[1],reverse=True)
        return [doc for doc,score in ranked[:top_k] if score>0]
