"""Máy chủ giả lập Claude Messages API (stream SSE) để kiểm thử không cần API key thật.

Phản hồi được chọn theo câu hỏi mới nhất của khách (xem `kich_ban`).
Mọi request nhận được lưu trong `YEU_CAU` để test kiểm tra lại.
"""

import asyncio
import json
import re

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI()
YEU_CAU = []


def _sse(loai, du_lieu):
    return f"event: {loai}\ndata: {json.dumps(du_lieu, ensure_ascii=False)}\n\n"


def _chu(khoi):
    if isinstance(khoi, str):
        return khoi
    return "".join(b.get("text", "") for b in khoi if b.get("type") == "text")


def kich_ban(body):
    """Trả về (danh sách khối nội dung, stop_reason) hoặc ('http', mã lỗi) hoặc ('dut', chữ)."""
    cuoi = body["messages"][-1]
    noi_dung = cuoi["content"]
    ket_qua_cong_cu = [b for b in noi_dung if isinstance(b, dict) and b.get("type") == "tool_result"] \
        if isinstance(noi_dung, list) else []
    cau_dau = _chu(body["messages"][0]["content"])

    if ket_qua_cong_cu:
        if "lặp mãi" in cau_dau:
            return [_tool("tra_cuu_tai_lieu", {"cau_hoi": "lặp"})], "tool_use"
        kq = ket_qua_cong_cu[0]
        nd = kq["content"] if isinstance(kq["content"], str) else _chu(kq["content"])
        if kq.get("is_error"):
            return [{"type": "text", "text": "Xin lỗi, mình gặp lỗi khi tìm, bạn nói rõ hơn nhé."}], "end_turn"
        if nd.startswith("{"):
            return [{"type": "text", "text": f"Mình tìm được **{json.loads(nd)['so_tin']}** căn phù hợp."}], "end_turn"
        muc = re.findall(r'muc="([^"]*)"', nd)
        return [{"type": "text", "text": "Theo tài liệu mục: " + "; ".join(muc)}], "end_turn"

    hoi = _chu(noi_dung)
    tham_khao = re.findall(r'muc="([^"]*)"', hoi)
    cau = re.sub(r"<tai_lieu_tham_khao>.*</tai_lieu_tham_khao>", "", hoi, flags=re.S).strip()

    if "lỗi máy chủ" in cau:
        return "http", 500
    if "quá tải" in cau:
        return "http", 429
    if "đứt" in cau:
        return "dut", "Đang trả lời dở"
    if "từ chối" in cau:
        return [], "refusal"
    if "tham số sai" in cau:
        return [_tool("tim_tin_dang", {"gia_toi_da_ty": "rẻ"})], "tool_use"
    if "lặp mãi" in cau:
        return [_tool("tra_cuu_tai_lieu", {"cau_hoi": "lặp"})], "tool_use"
    if "tra cứu" in cau:
        return [{"type": "text", "text": "Để mình tra cứu."},
                _tool("tra_cuu_tai_lieu", {"cau_hoi": cau.replace("tra cứu", "")})], "tool_use"
    m = re.search(r"dưới (\d+(?:[.,]\d+)?) tỷ", cau)
    if m:
        return [_tool("tim_tin_dang", {"gia_toi_da_ty": float(m.group(1).replace(",", "."))})], "tool_use"
    m = re.search(r"tin (T\d+)", cau)
    if m:
        return [_tool("tim_tin_dang", {"ma_tin": m.group(1)})], "tool_use"
    if "xss" in cau:
        return [{"type": "text", "text": "**Đậm** <img src=x onerror=\"window.__xss=1\">\n- ý một\n- ý hai"}], "end_turn"
    chu = "Đã đọc tài liệu: " + ("; ".join(tham_khao) if tham_khao else "không có")
    return [{"type": "text", "text": chu}], "end_turn"


_dem = 0


def _tool(ten, tham_so):
    global _dem
    _dem += 1
    return {"type": "tool_use", "id": f"toolu_{_dem:04d}", "name": ten, "input": tham_so}


async def _stream(khoi, stop_reason, dut=None):
    yield _sse("message_start", {"type": "message_start", "message": {
        "id": "msg_gia", "type": "message", "role": "assistant", "model": "gia", "content": [],
        "stop_reason": None, "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 0}}})
    if dut:
        yield _sse("content_block_start", {"type": "content_block_start", "index": 0,
                                           "content_block": {"type": "text", "text": ""}})
        yield _sse("content_block_delta", {"type": "content_block_delta", "index": 0,
                                           "delta": {"type": "text_delta", "text": dut}})
        await asyncio.sleep(0.05)
        raise RuntimeError("cắt kết nối giữa chừng")
    for i, b in enumerate(khoi):
        if b["type"] == "text":
            yield _sse("content_block_start", {"type": "content_block_start", "index": i,
                                               "content_block": {"type": "text", "text": ""}})
            for manh in re.findall(r".{1,8}", b["text"], flags=re.S):
                yield _sse("content_block_delta", {"type": "content_block_delta", "index": i,
                                                   "delta": {"type": "text_delta", "text": manh}})
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
    YEU_CAU.append({"headers": dict(request.headers), "body": body})
    kq = kich_ban(body)
    if kq[0] == "http":
        loai = "rate_limit_error" if kq[1] == 429 else "api_error"
        return JSONResponse({"type": "error", "error": {"type": loai, "message": "giả lập"}},
                            status_code=kq[1], headers={"retry-after": "0"})
    if kq[0] == "dut":
        return StreamingResponse(_stream([], None, dut=kq[1]), media_type="text/event-stream")
    return StreamingResponse(_stream(*kq), media_type="text/event-stream")
