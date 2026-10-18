"""Server-level smoke test: exercises the real HTTP server."""
import json
import sys

import httpx

BASE = "http://localhost:8001"


def sse_texts(resp: httpx.Response) -> str:
    out = []
    for line in resp.iter_lines():
        if line.startswith("data:"):
            data = line[5:].strip()
            if data == "[DONE]":
                break
            out.append(json.loads(data).get("text", ""))
    return "".join(out)


def main() -> int:
    # 1. healthz
    r = httpx.get(f"{BASE}/healthz", timeout=10)
    assert r.status_code == 200, r.text
    print("healthz OK")

    # 2. 401 without header
    r = httpx.post(f"{BASE}/chat", json={"question": "hi"}, timeout=10)
    assert r.status_code == 401, r.status_code
    print("401 OK")

    # 3. handoff path (gibberish -> low confidence -> human, no LLM needed)
    with httpx.stream(
        "POST", f"{BASE}/chat",
        json={"question": "xyzqwe asdfgh jklnm"},
        headers={"X-Member-Id": "M10001"},
        timeout=60,
    ) as r:
        assert r.status_code == 200, r.status_code
        text = sse_texts(r)
    assert "转接人工" in text, text
    print("handoff OK:", text[:30])

    print("ALL SERVER TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
