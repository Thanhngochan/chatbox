"""End-to-end tests of /api/chat against a fake Claude (through the real anthropic SDK)."""

import json
import time

import httpx
import pytest

from conftest import start_server


def chat(url, messages, timeout=30):
    """Send a question; return (HTTP status, list of (event, data))."""
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
    with httpx.stream("POST", url + "/api/chat", json={"messages": messages}, timeout=timeout) as r:
        if r.status_code != 200:
            r.read()
            return r.status_code, r.json()
        assert r.headers["content-type"].startswith("text/event-stream")
        events = []
        for block in r.read().decode().split("\n\n"):
            if not block.strip():
                continue
            event = block.split("\n")[0].removeprefix("event: ")
            data = json.loads(block.split("\n")[1].removeprefix("data: "))
            events.append((event, data))
        return 200, events


def text_of(events):
    return "".join(d["text"] for e, d in events if e == "text")


def test_health(server):
    j = httpx.get(server + "/api/health").json()
    assert j["ok"] and j["listings"] == 12 and j["document_chunks"] == 10 and j["has_api_key"]


def test_demo_page_and_widget(server):
    assert "PropertyChat" in httpx.get(server + "/").text
    r = httpx.get(server + "/widget.js")
    assert r.status_code == 200 and "javascript" in r.headers["content-type"]


def test_rag_attaches_relevant_documents(server, claude_requests):
    status, events = chat(server, "Mua nhà phải đóng những loại thuế phí gì?")
    assert status == 200 and events[-1][0] == "done"
    assert "Khi mua nhà phải trả những khoản thuế phí nào?" in text_of(events)
    body = claude_requests[0]["body"]
    # the documents are no longer in the system prompt; they are retrieved per question
    assert "lệ phí trước bạ" not in body["system"][0]["text"]
    last = body["messages"][-1]["content"]
    assert last[0]["text"].startswith("<reference_documents>") and "lệ phí trước bạ" in last[0]["text"]
    assert last[1]["text"] == "Mua nhà phải đóng những loại thuế phí gì?"
    assert {t["name"] for t in body["tools"]} == {"search_listings", "search_documents"}
    assert body["stream"] is True


def test_follow_up_uses_previous_question_as_context(server):
    status, events = chat(server, [
        {"role": "user", "content": "Cho mình hỏi về dự án An Lạc Garden"},
        {"role": "assistant", "content": "An Lạc Garden ở Thủ Đức."},
        {"role": "user", "content": "thanh toán thế nào?"},
    ])
    assert status == 200 and "An Lạc Garden" in text_of(events)


def test_greeting_gets_no_documents(server):
    status, events = chat(server, "xin chào")
    assert text_of(events) == "Documents read: none" and events[-1][0] == "done"


def test_listing_search_sends_cards(server, claude_requests):
    status, events = chat(server, "Có căn nào dưới 2 tỷ không?")
    kinds = [e for e, _ in events]
    assert kinds.index("listings") < kinds.index("text") and kinds[-1] == "done"
    cards = next(d for e, d in events if e == "listings")["items"]
    assert [t["id"] for t in cards] == ["T005"]
    assert "**1** căn" in text_of(events)
    assert len(claude_requests) == 2  # round 2 sends the tool result back to Claude
    result = claude_requests[1]["body"]["messages"][-1]["content"][0]
    assert result["type"] == "tool_result" and not result.get("is_error")


def test_no_matches_sends_no_cards(server):
    status, events = chat(server, "Có căn nào dưới 0,5 tỷ không?")
    assert "listings" not in [e for e, _ in events] and "**0** căn" in text_of(events)


def test_at_most_6_cards(server):
    status, events = chat(server, "nhà dưới 100 tỷ")
    assert len(next(d for e, d in events if e == "listings")["items"]) == 6
    assert "**12** căn" in text_of(events)


def test_details_by_listing_id(server):
    status, events = chat(server, "Cho mình xem chi tiết tin T003")
    assert [t["id"] for t in next(d for e, d in events if e == "listings")["items"]] == ["T003"]


def test_search_documents_tool_and_paragraph_break(server):
    status, events = chat(server, "look up phí quản lý Sông Xanh")
    assert text_of(events).startswith("Để mình tra cứu.\n\nSections found: Sông Xanh Residence")


def test_invalid_tool_parameters(server, claude_requests):
    status, events = chat(server, "bad params")
    assert events[-1][0] == "done" and "gặp lỗi" in text_of(events)
    assert claude_requests[1]["body"]["messages"][-1]["content"][0]["is_error"] is True


def test_claude_keeps_calling_tools(server, claude_requests):
    status, events = chat(server, "loop forever")
    assert events[-1][0] == "error" and len(claude_requests) == 4


def test_refusal(server):
    status, events = chat(server, "refuse this")
    assert events == [("error", {"message": "Xin lỗi, mình không thể hỗ trợ yêu cầu này."})]


def test_claude_api_errors(server):
    assert chat(server, "server error")[1][-1] == ("error", {"message": "Có lỗi khi kết nối trợ lý, vui lòng thử lại."})
    assert chat(server, "overloaded")[1][-1][0] == "error"


def test_connection_cut_mid_stream(server):
    status, events = chat(server, "cut off")
    assert events[-1][0] == "error"


def test_html_is_passed_through_for_the_widget_to_escape(server):
    assert "<img" in text_of(chat(server, "xss")[1])


@pytest.mark.parametrize("messages, status", [
    ([], 422),
    ([{"role": "user", "content": ""}], 422),
    ([{"role": "user", "content": "a" * 2001}], 422),
    ([{"role": "system", "content": "hi"}], 422),
    ([{"role": "user", "content": "hi"}, {"role": "assistant", "content": "chào"}], 400),
    ([{"role": "assistant", "content": "chào"}], 400),
])
def test_invalid_requests(server, messages, status):
    assert chat(server, messages)[0] == status


def test_body_is_not_json(server):
    r = httpx.post(server + "/api/chat", content="abc", headers={"Content-Type": "application/json"})
    assert r.status_code == 422


def test_long_history_sends_20_messages_starting_with_user(server, claude_requests):
    history = []
    for i in range(15):
        history += [{"role": "user", "content": f"câu {i}"}, {"role": "assistant", "content": f"đáp {i}"}]
    history.append({"role": "user", "content": "xin chào"})
    status, events = chat(server, history)
    sent = claude_requests[0]["body"]["messages"]
    assert status == 200 and len(sent) <= 20 and sent[0]["role"] == "user"


def test_cors(server):
    r = httpx.options(server + "/api/chat", headers={
        "Origin": "https://my-site.vn", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"})
    assert r.status_code == 200 and r.headers["access-control-allow-origin"] in ("*", "https://my-site.vn")


def test_cors_restricted_to_allowed_origins(fake_claude):
    proc, url = start_server(fake_claude, ALLOWED_ORIGINS="https://my-site.vn")
    try:
        allowed = httpx.options(url + "/api/chat", headers={
            "Origin": "https://my-site.vn", "Access-Control-Request-Method": "POST"})
        other = httpx.options(url + "/api/chat", headers={
            "Origin": "https://other-site.vn", "Access-Control-Request-Method": "POST"})
        assert allowed.headers.get("access-control-allow-origin") == "https://my-site.vn"
        assert "access-control-allow-origin" not in other.headers
    finally:
        proc.terminate()


def test_rate_limit(fake_claude):
    proc, url = start_server(fake_claude, RATE_LIMIT_PER_MINUTE="3")
    try:
        statuses = [chat(url, "xin chào")[0] for _ in range(4)]
        assert statuses == [200, 200, 200, 429]
        assert "đợi" in chat(url, "xin chào")[1]["detail"]
    finally:
        proc.terminate()


def test_missing_api_key(fake_claude):
    proc, url = start_server(fake_claude, ANTHROPIC_API_KEY="")
    try:
        assert httpx.get(url + "/api/health").json()["has_api_key"] is False
        events = chat(url, "xin chào")[1]
        assert events[0][0] == "error" and "API key" in events[0][1]["message"]
    finally:
        proc.terminate()


def test_claude_unreachable():
    proc, url = start_server(None)  # nothing listens on port 9
    try:
        started = time.time()
        events = chat(url, "xin chào")[1]
        assert events[-1] == ("error", {"message": "Không kết nối được tới trợ lý, vui lòng thử lại."})
        assert time.time() - started < 20
    finally:
        proc.terminate()
