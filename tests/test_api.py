"""API tests with a mocked LLM (the Zen free tier only answers the opencode CLI,
so the generation step is stubbed; all app logic is exercised for real)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient  # noqa: E402

import app.main as main  # noqa: E402

client = TestClient(main.app)

HDR = {"X-Member-Id": "M10001"}


def _sse_texts(resp):
    texts = []
    for line in resp.text.splitlines():
        if line.startswith("data:"):
            data = line[5:].strip()
            if data == "[DONE]":
                break
            texts.append(json.loads(data).get("text", ""))
    return "".join(texts)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_missing_header_401():
    r = client.post("/chat", json={"question": "hi"})
    assert r.status_code == 401


def test_empty_question_422():
    r = client.post("/chat", json={"question": "  "}, headers=HDR)
    assert r.status_code == 422


def test_chat_tool_loop(monkeypatch):
    calls = {"n": 0}

    def fake_chat_once(messages):
        calls["n"] += 1
        if calls["n"] == 1:
            return '```json\n{"tool": "get_points"}\n```'
        return "您的积分余额是 12580 分。来源：积分规则"

    monkeypatch.setattr(main, "chat_once", fake_chat_once)
    r = client.post("/chat", json={"question": "我的积分有多少？"}, headers=HDR)
    assert r.status_code == 200
    text = _sse_texts(r)
    assert "12580" in text
    assert calls["n"] == 2


def test_chat_direct_answer(monkeypatch):
    monkeypatch.setattr(main, "chat_once", lambda m: "前2小时免费。来源：停车规则")
    r = client.post("/chat", json={"question": "停车怎么收费？"}, headers=HDR)
    assert r.status_code == 200
    assert "免费" in _sse_texts(r)


def test_chat_handoff_on_low_confidence(monkeypatch):
    # gibberish should not match any KB doc above the threshold
    monkeypatch.setattr(main, "chat_once", lambda m: "should not be called")
    r = client.post("/chat", json={"question": "xyzqwe asdfgh jklnm"}, headers=HDR)
    assert r.status_code == 200
    assert "转接人工" in _sse_texts(r)


def test_body_cannot_spoof_identity(monkeypatch):
    """member_id in body must be ignored; header wins."""
    monkeypatch.setattr(
        main, "chat_once",
        lambda m: '```json\n{"tool": "get_points"}\n```' if len(m) == 2 else "done",
    )
    seen = {}

    orig = main.tools.call_tool

    def spy(name, member_id):
        seen["member_id"] = member_id
        return orig(name, member_id)

    monkeypatch.setattr(main.tools, "call_tool", spy)
    r = client.post(
        "/chat",
        json={"question": "我的积分？", "member_id": "ATTACKER"},
        headers={"X-Member-Id": "M10001"},
    )
    assert r.status_code == 200
    assert seen["member_id"] == "M10001"
