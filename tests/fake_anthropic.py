"""Fake Claude Messages API (SSE streaming) so tests run without a real API key.

The response is chosen from the customer's latest question (see `script`).
Every request received is stored in `REQUESTS` so tests can inspect it.
"""

import asyncio
import json
import re

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI()
REQUESTS = []


def _sse(event, data):
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _text(content):
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") for b in content if b.get("type") == "text")


_tool_counter = 0


def _tool(name, params):
    global _tool_counter
    _tool_counter += 1
    return {"type": "tool_use", "id": f"toolu_{_tool_counter:04d}", "name": name, "input": params}


def script(body):
    """Return (content blocks, stop_reason), or ('http', status code), or ('cut', partial text)."""
    last = body["messages"][-1]
    content = last["content"]
    tool_results = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_result"] \
        if isinstance(content, list) else []
    first_question = _text(body["messages"][0]["content"])

    if tool_results:
        if "loop forever" in first_question:
            return [_tool("search_documents", {"query": "loop"})], "tool_use"
        result = tool_results[0]
        text = result["content"] if isinstance(result["content"], str) else _text(result["content"])
        if result.get("is_error"):
            return [{"type": "text", "text": "Xin lỗi, mình gặp lỗi khi tìm, bạn nói rõ hơn nhé."}], "end_turn"
        if text.startswith("{"):
            return [{"type": "text", "text": f"Mình tìm được **{json.loads(text)['count']}** căn phù hợp."}], "end_turn"
        sections = re.findall(r'section="([^"]*)"', text)
        return [{"type": "text", "text": "Sections found: " + "; ".join(sections)}], "end_turn"

    question = _text(content)
    reference_sections = re.findall(r'section="([^"]*)"', question)
    question = re.sub(r"<reference_documents>.*</reference_documents>", "", question, flags=re.S).strip()

    if "server error" in question:
        return "http", 500
    if "overloaded" in question:
        return "http", 429
    if "cut off" in question:
        return "cut", "Half an answer"
    if "refuse" in question:
        return [], "refusal"
    if "bad params" in question:
        return [_tool("search_listings", {"max_price_billion": "cheap"})], "tool_use"
    if "loop forever" in question:
        return [_tool("search_documents", {"query": "loop"})], "tool_use"
    if "look up" in question:
        return [{"type": "text", "text": "Để mình tra cứu."},
                _tool("search_documents", {"query": question.replace("look up", "")})], "tool_use"
    m = re.search(r"dưới (\d+(?:[.,]\d+)?) tỷ", question)  # "under N billion"
    if m:
        return [_tool("search_listings", {"max_price_billion": float(m.group(1).replace(",", "."))})], "tool_use"
    m = re.search(r"tin (T\d+)", question)  # "listing T003"
    if m:
        return [_tool("search_listings", {"listing_id": m.group(1)})], "tool_use"
    if "xss" in question:
        return [{"type": "text", "text": "**Đậm** <img src=x onerror=\"window.__xss=1\">\n- ý một\n- ý hai"}], "end_turn"
    text = "Documents read: " + ("; ".join(reference_sections) if reference_sections else "none")
    return [{"type": "text", "text": text}], "end_turn"


async def _stream(blocks, stop_reason, cut=None):
    yield _sse("message_start", {"type": "message_start", "message": {
        "id": "msg_fake", "type": "message", "role": "assistant", "model": "fake", "content": [],
        "stop_reason": None, "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 0}}})
    if cut:
        yield _sse("content_block_start", {"type": "content_block_start", "index": 0,
                                           "content_block": {"type": "text", "text": ""}})
        yield _sse("content_block_delta", {"type": "content_block_delta", "index": 0,
                                           "delta": {"type": "text_delta", "text": cut}})
        await asyncio.sleep(0.05)
        raise RuntimeError("connection cut mid-stream")
    for i, b in enumerate(blocks):
        if b["type"] == "text":
            yield _sse("content_block_start", {"type": "content_block_start", "index": i,
                                               "content_block": {"type": "text", "text": ""}})
            for piece in re.findall(r".{1,8}", b["text"], flags=re.S):
                yield _sse("content_block_delta", {"type": "content_block_delta", "index": i,
                                                   "delta": {"type": "text_delta", "text": piece}})
                await asyncio.sleep(0.005)
        else:
            yield _sse("content_block_start", {"type": "content_block_start", "index": i, "content_block": {
                "type": "tool_use", "id": b["id"], "name": b["name"], "input": {}}})
            yield _sse("content_block_delta", {"type": "content_block_delta", "index": i, "delta": {
                "type": "input_json_delta", "partial_json": json.dumps(b["input"], ensure_ascii=False)}})
        yield _sse("content_block_stop", {"type": "content_block_stop", "index": i})
    yield _sse("message_delta", {"type": "message_delta",
                                 "delta": {"stop_reason": stop_reason, "stop_sequence": None},
                                 "usage": {"output_tokens": 5}})
    yield _sse("message_stop", {"type": "message_stop"})


@app.post("/v1/messages")
async def messages(request: Request):
    body = await request.json()
    REQUESTS.append({"headers": dict(request.headers), "body": body})
    result = script(body)
    if result[0] == "http":
        kind = "rate_limit_error" if result[1] == 429 else "api_error"
        return JSONResponse({"type": "error", "error": {"type": kind, "message": "fake"}},
                            status_code=result[1], headers={"retry-after": "0"})
    if result[0] == "cut":
        return StreamingResponse(_stream([], None, cut=result[1]), media_type="text/event-stream")
    return StreamingResponse(_stream(*result), media_type="text/event-stream")
