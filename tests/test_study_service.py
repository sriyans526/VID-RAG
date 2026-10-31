import json

import pytest

from service.study_service import StudyService


class FakeLLM:
    def __init__(self, content):
        self.content = content
        self.prompt = None

    def invoke(self, prompt):
        self.prompt = prompt
        return type("Response", (), {"content": self.content})()


def test_generate_limits_flashcards_and_prompt_size():
    llm = FakeLLM(json.dumps([{"front": f"Q{i}", "back": f"A{i}"} for i in range(10)]))
    service = StudyService(llm)

    result = service.generate("flashcards", "x" * 9000, count=3)

    assert len(result) == 3
    assert "Generate exactly 3 concise items" in llm.prompt
    assert len(llm.prompt) < 8500
    assert llm.prompt.endswith("x" * 8000)
    assert "no markdown or reasoning" in llm.prompt


def test_generate_preserves_structured_summary():
    summary = {"title": "Short summary", "key_points": ["One point"]}
    llm = FakeLLM(json.dumps(summary))

    assert StudyService(llm).generate("summary", "source") == summary


def test_generate_rejects_invalid_json():
    with pytest.raises(ValueError, match="valid JSON"):
        StudyService(FakeLLM("not JSON")).generate("quiz", "source")
