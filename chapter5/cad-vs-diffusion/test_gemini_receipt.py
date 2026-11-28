"""离线测试：Gemini 调用抛异常时，留证必须记为 error。不打任何外部 API。"""
import json
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gemini_image
from receipts import ReceiptBook


class FailingModels:
    def generate_content(self, **_kwargs):
        raise RuntimeError("429 RESOURCE_EXHAUSTED")


def test_failed_call_is_recorded_as_error(tmp_path, monkeypatch):
    genai = types.SimpleNamespace(Client=lambda api_key: types.SimpleNamespace(models=FailingModels()))
    monkeypatch.setitem(sys.modules, "google", types.SimpleNamespace(genai=genai))
    monkeypatch.setitem(sys.modules, "google.genai", genai)
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    book = ReceiptBook(tmp_path / "receipts")

    with pytest.raises(RuntimeError, match="429"):
        gemini_image.generate_image("法兰", tmp_path / "out.png", book, "route-b-image")

    assert [c["status"] for c in book.calls] == ["error"]
    receipt = json.loads(Path(book.calls[0]["path"]).read_text(encoding="utf-8"))
    assert receipt["status"] == "error"
    assert "429" in receipt["response"]["error"]
