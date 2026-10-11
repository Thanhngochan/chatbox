"""Tests of the chat widget in a real browser (Chromium) against a fake Claude."""

import http.server
import os
import threading
from functools import partial

import pytest

sync_api = pytest.importorskip("playwright.sync_api")
expect = sync_api.expect

from conftest import free_port, start_server  # noqa: E402


def _find_chromium():
    for path in ("/opt/pw-browsers/chromium",):
        if os.path.isfile(path):
            return path
    return None  # let Playwright use its own browser


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch(executable_path=_find_chromium())
        yield b
        b.close()


@pytest.fixture
def page(browser, server):
    context = browser.new_context()
    pg = context.new_page()
    js_errors = []
    pg.on("pageerror", lambda e: js_errors.append(str(e)))
    pg.goto(server + "/")
    yield pg
    assert js_errors == []
    context.close()


def inside(pg, selector):
    """Find an element inside the widget's Shadow DOM."""
    return pg.locator("#property-chat").locator(selector)


def open_chat(pg):
    inside(pg, ".btn").click()
    expect(inside(pg, ".panel")).to_be_visible()


def ask(pg, question):
    inside(pg, "textarea").fill(question)
    inside(pg, "textarea").press("Enter")
    expect(inside(pg, ".ft button")).to_be_enabled(timeout=20000)


def test_open_close_and_greeting(page):
    expect(inside(page, ".panel")).to_be_hidden()
    open_chat(page)
    expect(inside(page, ".m.a").first).to_contain_text("Xin chào")
    assert inside(page, ".sug button").count() == 3
    inside(page, ".x").click()
    expect(inside(page, ".panel")).to_be_hidden()


def test_rag_answer_and_history_kept(page):
    open_chat(page)
    ask(page, "Dự án nào gần metro?")
    expect(inside(page, ".m.u")).to_have_text("Dự án nào gần metro?")
    expect(inside(page, ".m.a").last).to_contain_text("An Lạc Garden")
    assert inside(page, ".sug").count() == 0
    # after a reload the history is still there for this browser session
    page.reload()
    open_chat(page)
    expect(inside(page, ".m.a").last).to_contain_text("An Lạc Garden")
    inside(page, ".r").click()
    assert inside(page, ".m.u").count() == 0 and inside(page, ".sug button").count() == 3


def test_suggestion_shows_cards_and_card_asks_follow_up(page):
    open_chat(page)
    inside(page, ".sug button").first.click()  # "Căn 2 phòng ngủ dưới 3 tỷ ở Quận 7"
    expect(inside(page, ".card").first).to_be_visible(timeout=20000)
    expect(inside(page, ".ft button")).to_be_enabled(timeout=20000)
    assert inside(page, ".card").count() >= 1
    # the answer bubble sits below the cards
    assert page.evaluate(
        "() => document.querySelector('#property-chat').shadowRoot.querySelector('.body').lastElementChild.className"
    ) == "m a"
    listing_id = inside(page, ".card .id").first.inner_text().split(" ")[0]
    inside(page, ".card button").first.click()
    expect(inside(page, ".m.u").last).to_have_text(f"Cho mình xem chi tiết tin {listing_id}")
    expect(inside(page, ".m.a").last).to_contain_text("1 căn phù hợp", timeout=20000)


def test_host_page_button_calls_ask_api(page):
    page.get_by_role("button", name="Tìm căn dưới 2 tỷ").click()
    expect(inside(page, ".card .id")).to_contain_text("T005", timeout=20000)


def test_error_is_shown_and_user_can_send_again(page):
    open_chat(page)
    ask(page, "server error")
    expect(inside(page, ".m.err")).to_contain_text("Có lỗi")
    stored = page.evaluate("() => Object.values(sessionStorage).join('')")
    assert "server error" not in stored
    ask(page, "xin chào")
    expect(inside(page, ".m.a").last).to_contain_text("Documents read")


def test_markdown_is_safe(page):
    open_chat(page)
    ask(page, "xss")
    expect(inside(page, ".m.a b").last).to_have_text("Đậm")
    assert inside(page, ".m.a li").count() == 2
    assert page.evaluate("() => window.__xss") is None
    assert inside(page, ".m.a img").count() == 0


def test_empty_question_not_sent_and_shift_enter_is_newline(page):
    open_chat(page)
    inside(page, "textarea").fill("   ")
    inside(page, "textarea").press("Enter")
    assert inside(page, ".m.u").count() == 0
    inside(page, "textarea").fill("line 1")
    inside(page, "textarea").press("Shift+Enter")
    assert inside(page, ".m.u").count() == 0


def test_phone_fullscreen(browser, server):
    context = browser.new_context(viewport={"width": 375, "height": 700}, is_mobile=True, has_touch=True)
    pg = context.new_page()
    pg.goto(server + "/")
    inside(pg, ".btn").tap()
    box = inside(pg, ".panel").bounding_box()
    assert box["width"] == 375 and box["height"] == 700
    assert pg.evaluate("() => document.documentElement.scrollWidth") <= 375
    inside(pg, ".x").tap()
    expect(inside(pg, ".btn")).to_be_visible()
    context.close()


@pytest.fixture
def other_website(tmp_path, server):
    """A website on another origin (port) embedding the chat box, with hostile CSS to test isolation."""
    (tmp_path / "index.html").write_text(f"""<!doctype html><html><head><meta charset="utf-8">
<style>* {{ color: red !important; font-size: 40px !important; }} button {{ display:none !important }}</style>
</head><body><h1>Another website</h1>
<script src="{server}/widget.js" data-title="Chat test" data-color="#ff6600" data-position="left" data-lang="en" defer></script>
<script src="{server}/widget.js" defer></script>
</body></html>""", encoding="utf-8")
    port = free_port()
    httpd = http.server.ThreadingHTTPServer(
        ("127.0.0.1", port), partial(http.server.SimpleHTTPRequestHandler, directory=str(tmp_path)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{port}/index.html"
    httpd.shutdown()


def test_embedded_in_other_website(browser, other_website):
    pg = browser.new_page()
    pg.goto(other_website)
    assert pg.locator("#property-chat").count() == 1  # embedded twice, still one widget
    button = inside(pg, ".btn")
    expect(button).to_be_visible()  # the host page's CSS cannot hide the button
    assert button.bounding_box()["x"] < 100  # data-position="left"
    button.click()
    expect(inside(pg, ".hd .t")).to_have_text("Chat test")
    expect(inside(pg, "textarea")).to_have_attribute("placeholder", "Type your question...")  # data-lang="en"
    assert inside(pg, ".hd").evaluate("e => getComputedStyle(e).backgroundColor") == "rgb(255, 102, 0)"
    assert inside(pg, ".m.a").first.evaluate("e => getComputedStyle(e).fontSize") == "14px"
    ask(pg, "Mua nhà phải đóng thuế phí gì?")  # cross-origin API call (CORS)
    expect(inside(pg, ".m.a").last).to_contain_text("thuế phí")
    pg.close()


def test_server_down(browser):
    proc, url = start_server(None)
    pg = browser.new_page()
    pg.goto(url + "/")
    proc.terminate()
    proc.wait()
    open_chat(pg)
    ask(pg, "xin chào")
    expect(inside(pg, ".m.err")).to_contain_text("Không kết nối được tới máy chủ")
    pg.close()
