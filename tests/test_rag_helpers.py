import sys, types
m1 = types.ModuleType("langchain_qdrant")
m1.QdrantVectorStore = type("QdrantVectorStore", (), {})
sys.modules.setdefault("langchain_qdrant", m1)
m2 = types.ModuleType("langchain_huggingface")
m2.HuggingFaceEmbeddings = type("HuggingFaceEmbeddings", (), {})
sys.modules.setdefault("langchain_huggingface", m2)

from service.RAG_service import fmt, RAGService

def test_timestamp_format():
    assert fmt(0) == "00:00"
    assert fmt(75.9) == "01:15"

def test_json_parser_handles_fenced_output():
    parsed = RAGService._parse('```json\n{"answer":"hello","segments":[]}\n```')
    assert parsed["answer"] == "hello"
