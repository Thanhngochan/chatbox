"""Kiểm tra widget chat trong trình duyệt thật (Chromium) với Claude giả lập."""

import http.server
import os
import threading
from functools import partial

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from conftest import _cong_trong  # noqa: E402


def _tim_chromium():
    for duong_dan in ("/opt/pw-browsers/chromium",):
        if os.path.isfile(duong_dan):
            return duong_dan
    return None


@pytest.fixture(scope="module")
def trinh_duyet():
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch(executable_path=_tim_chromium())
        yield b
        b.close()


@pytest.fixture
def trang(trinh_duyet, server):
    ctx = trinh_duyet.new_context()
    page = ctx.new_page()
    loi_js = []
    page.on("pageerror", lambda e: loi_js.append(str(e)))
    page.goto(server + "/")
    yield page
    assert loi_js == []
    ctx.close()


def goc(page, chon):
    """Tìm phần tử bên trong Shadow DOM của widget."""
    return page.locator("#property-chat").locator(chon)


def mo(page):
    goc(page, ".btn").click()
    sync_api.expect(goc(page, ".panel")).to_be_visible()


def hoi(page, cau):
    goc(page, "textarea").fill(cau)
    goc(page, "textarea").press("Enter")
    sync_api.expect(goc(page, ".ft button")).to_be_enabled(timeout=20000)


def test_mo_dong_va_loi_chao(trang):
    sync_api.expect(goc(trang, ".panel")).to_be_hidden()
    mo(trang)
    sync_api.expect(goc(trang, ".m.a").first).to_contain_text("Xin chào")
    assert goc(trang, ".sug button").count() == 3
    goc(trang, ".x").click()
    sync_api.expect(goc(trang, ".panel")).to_be_hidden()


def test_hoi_dap_rag_va_luu_lich_su(trang):
    mo(trang)
    hoi(trang, "Dự án nào gần metro?")
    sync_api.expect(goc(trang, ".m.u")).to_have_text("Dự án nào gần metro?")
    sync_api.expect(goc(trang, ".m.a").last).to_contain_text("An Lạc Garden")
    assert goc(trang, ".sug").count() == 0
    # tải lại trang: lịch sử còn nguyên trong phiên
    trang.reload()
    mo(trang)
    sync_api.expect(goc(trang, ".m.a").last).to_contain_text("An Lạc Garden")
    goc(trang, ".r").click()
    assert goc(trang, ".m.u").count() == 0 and goc(trang, ".sug button").count() == 3


def test_goi_y_tim_tin_hien_the_va_hoi_tiep_tu_the(trang):
    mo(trang)
    goc(trang, ".sug button").first.click()  # "Căn 2 phòng ngủ dưới 3 tỷ ở Quận 7"
    sync_api.expect(goc(trang, ".card").first).to_be_visible(timeout=20000)
    sync_api.expect(goc(trang, ".ft button")).to_be_enabled(timeout=20000)
    so_the = goc(trang, ".card").count()
    assert so_the >= 1
    # câu trả lời nằm dưới các thẻ
    assert trang.evaluate(
        "() => document.querySelector('#property-chat').shadowRoot.querySelector('.body').lastElementChild.className"
    ) == "m a"
    ma = goc(trang, ".card .id").first.inner_text().split(" ")[0]
    goc(trang, ".card button").first.click()
    sync_api.expect(goc(trang, ".m.u").last).to_have_text(f"Cho mình xem chi tiết tin {ma}")
    sync_api.expect(goc(trang, ".m.a").last).to_contain_text("1 căn phù hợp", timeout=20000)


def test_nut_cua_website_goi_api_ask(trang):
    trang.get_by_role("button", name="Tìm căn dưới 2 tỷ").click()
    sync_api.expect(goc(trang, ".card .id")).to_contain_text("T005", timeout=20000)


def test_loi_hien_thong_bao_va_gui_lai_duoc(trang):
    mo(trang)
    hoi(trang, "lỗi máy chủ")
    sync_api.expect(goc(trang, ".m.err")).to_contain_text("Có lỗi")
    hist = trang.evaluate("() => Object.values(sessionStorage).join('')")
    assert "lỗi máy chủ" not in hist
    hoi(trang, "xin chào")
    sync_api.expect(goc(trang, ".m.a").last).to_contain_text("Đã đọc tài liệu")


def test_markdown_an_toan(trang):
    mo(trang)
    hoi(trang, "xss")
    sync_api.expect(goc(trang, ".m.a b").last).to_have_text("Đậm")
    assert goc(trang, ".m.a li").count() == 2
    assert trang.evaluate("() => window.__xss") is None
    assert goc(trang, ".m.a img").count() == 0


def test_khong_gui_cau_rong_va_shift_enter_xuong_dong(trang):
    mo(trang)
    goc(trang, "textarea").fill("   ")
    goc(trang, "textarea").press("Enter")
    assert goc(trang, ".m.u").count() == 0
    goc(trang, "textarea").fill("dòng 1")
    goc(trang, "textarea").press("Shift+Enter")
    assert goc(trang, ".m.u").count() == 0


def test_dien_thoai_toan_man_hinh(trinh_duyet, server):
    ctx = trinh_duyet.new_context(viewport={"width": 375, "height": 700}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.goto(server + "/")
    goc(page, ".btn").tap()
    hop = goc(page, ".panel").bounding_box()
    assert hop["width"] == 375 and hop["height"] == 700
    assert page.evaluate("() => document.documentElement.scrollWidth") <= 375
    goc(page, ".x").tap()
    sync_api.expect(goc(page, ".btn")).to_be_visible()
    ctx.close()


@pytest.fixture
def website_khac(tmp_path, server):
    """Một website ở tên miền (cổng) khác nhúng chat box, có CSS 'phá' để thử cô lập."""
    (tmp_path / "index.html").write_text(f"""<!doctype html><html><head><meta charset="utf-8">
<style>* {{ color: red !important; font-size: 40px !important; }} button {{ display:none !important }}</style>
</head><body><h1>Website khác</h1>
<script src="{server}/widget.js" data-title="Chat thử" data-color="#ff6600" data-position="left" defer></script>
<script src="{server}/widget.js" defer></script>
</body></html>""", encoding="utf-8")
    cong = _cong_trong()
    srv = http.server.ThreadingHTTPServer(
        ("127.0.0.1", cong), partial(http.server.SimpleHTTPRequestHandler, directory=str(tmp_path)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{cong}/index.html"
    srv.shutdown()


def test_nhung_vao_website_khac(trinh_duyet, website_khac):
    page = trinh_duyet.new_page()
    page.goto(website_khac)
    assert page.locator("#property-chat").count() == 1  # nhúng 2 lần vẫn chỉ 1 widget
    nut = goc(page, ".btn")
    sync_api.expect(nut).to_be_visible()  # CSS của web chủ không ẩn được nút
    assert nut.bounding_box()["x"] < 100  # data-position="left"
    nut.click()
    sync_api.expect(goc(page, ".hd .t")).to_have_text("Chat thử")
    assert goc(page, ".hd").evaluate("e => getComputedStyle(e).backgroundColor") == "rgb(255, 102, 0)"
    assert goc(page, ".m.a").first.evaluate("e => getComputedStyle(e).fontSize") == "14px"
    hoi(page, "Mua nhà phải đóng thuế phí gì?")  # gọi API khác tên miền (CORS)
    sync_api.expect(goc(page, ".m.a").last).to_contain_text("thuế phí")
    page.close()


def test_may_chu_tat(trinh_duyet, tmp_path):
    from conftest import chay_server
    p, url = chay_server(None)
    page = trinh_duyet.new_page()
    page.goto(url + "/")
    p.terminate()
    p.wait()
    mo(page)
    hoi(page, "xin chào")
    sync_api.expect(goc(page, ".m.err")).to_contain_text("Không kết nối được tới máy chủ")
    page.close()
