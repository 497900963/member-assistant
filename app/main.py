"""Member assistant API.

POST /chat (SSE stream):
  - member identity ONLY from the X-Member-Id header (401 if missing).
  - request body carries the question only; it can never set the identity.
  - pipeline: RAG retrieve -> optional preset tool call -> streamed answer.
  - low confidence and no tool data -> transfer to human agent.

GET /healthz: liveness probe.
"""
from __future__ import annotations

import json
import re
import time
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from . import tools
from .config import settings
from .llm import LLMError, chat_once
from .log import get_logger, log_with
from .rag import RAGIndex, RetrievedChunk

logger = get_logger(__name__)
app = FastAPI(title="member-assistant", version=settings.version)
rag = RAGIndex().load()

HUMAN_HANDOFF = "这个问题我暂时无法准确回答，已为您转接人工客服，请稍候。"


class ChatRequest(BaseModel):
    question: str


def _extract_tool_call(text: str) -> Optional[str]:
    """Find {"tool": "<name>"} in a ```json fenced block. Only registry names accepted."""
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not m:
        return None
    try:
        name = json.loads(m.group(1)).get("tool")
    except json.JSONDecodeError:
        return None
    return name if name in tools.TOOLS else None


SYSTEM_PROMPT = """你是商场会员助手。用简洁中文回答，回答末尾注明引用来源（如：来源：积分规则）。
先判断是否需要调用工具；需要时只输出一个 JSON 代码块：
```json
{"tool": "get_points"}
```
不需要时直接回答。不要编造会员数据。"""


def _build_answer(question: str, member_id: str, chunks: list[RetrievedChunk]) -> tuple[str, list[str]]:
    """Run retrieve->tool->generate. Returns (answer_text, tools_used)."""
    context = "\n".join(f"[{c.doc_name}]\n{c.text}" for c in chunks)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"知识库：\n{context}\n\n问题：{question}"},
    ]
    used_tools: list[str] = []
    for _ in range(settings.llm_max_tool_rounds):
        reply = chat_once(messages)
        tool_name = _extract_tool_call(reply)
        if not tool_name:
            return reply, used_tools
        result = tools.call_tool(tool_name, member_id)  # member_id from header only
        used_tools.append(tool_name)
        messages.append({"role": "assistant", "content": reply})
        messages.append({
            "role": "user",
            "content": f"工具 {tool_name} 返回：\n{json.dumps(result, ensure_ascii=False)}\n\n请基于以上信息直接回答用户问题，不要再调用工具。",
        })
    reply = chat_once(messages)
    if _extract_tool_call(reply):
        return HUMAN_HANDOFF, used_tools
    return reply, used_tools


@app.get("/healthz")
def healthz():
    return {"status": "ok", "version": settings.version}


@app.post("/chat")
def chat(
    req: ChatRequest,
    x_member_id: Optional[str] = Header(default=None, alias="X-Member-Id"),
):
    if not x_member_id:
        raise HTTPException(status_code=401, detail="missing X-Member-Id header")
    member_id = x_member_id.strip()
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="question is empty")

    started = time.time()

    def event_stream():
        try:
            chunks = rag.query(question)
            top_score = chunks[0].score if chunks else 0.0
            cited = [c.doc_name for c in chunks]
            if top_score < settings.confidence_threshold:
                log_with(logger, 30, "low confidence, handoff",
                         member_id=member_id, top_score=round(top_score, 3))
                yield f"data: {json.dumps({'text': HUMAN_HANDOFF}, ensure_ascii=False)}\n\n"
            else:
                answer, used_tools = _build_answer(question, member_id, chunks)
                for i in range(0, len(answer), 120):
                    yield f"data: {json.dumps({'text': answer[i:i + 120]}, ensure_ascii=False)}\n\n"
                log_with(logger, 20, "chat done",
                         member_id=member_id, q=question[:60], cited=cited,
                         tools=used_tools,
                         latency_ms=int((time.time() - started) * 1000))
        except LLMError as e:
            log_with(logger, 40, "llm error", member_id=member_id, error=str(e))
            yield f"data: {json.dumps({'text': '服务暂时不可用，请稍后再试。', 'error': True}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
