from functools import lru_cache
from langchain_huggingface import HuggingFaceEmbeddings

class EmbeddingService:
    @staticmethod
    @lru_cache(maxsize=1)
    def get_model():
        return HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-base",
          model_kwargs={"device":"cpu"},encode_kwargs={"normalize_embeddings":True})
