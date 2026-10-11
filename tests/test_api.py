"""Kiểm tra API /api/chat từ đầu tới cuối với Claude giả lập (đi qua SDK anthropic thật)."""

import json
import time

import httpx
import pytest

from conftest import chay_server


def chat(url, messages, timeout=30):
    """Gửi câu hỏi, trả về (mã HTTP, danh sách (sự kiện, dữ liệu))."""
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
    with httpx.stream("POST", url + "/api/chat", json={"messages": messages}, timeout=timeout) as r:
        if r.status_code != 200:
            r.read()
            return r.status_code, r.json()
        assert r.headers["content-type"].startswith("text/event-stream")
        su_kien = []
        for khoi in r.read().decode().split("\n\n"):
            if not khoi.strip():
                continue
            loai = khoi.split("\n")[0].removeprefix("event: ")
            du_lieu = json.loads(khoi.split("\n")[1].removeprefix("data: "))
            su_kien.append((loai, du_lieu))
        return 200, su_kien


def chu(su_kien):
    return "".join(d["text"] for l, d in su_kien if l == "text")


def test_health(server):
    j = httpx.get(server + "/api/health").json()
    assert j["ok"] and j["so_tin_dang"] == 12 and j["so_doan_tai_lieu"] == 10 and j["co_api_key"]


def test_trang_demo_va_widget(server):
    assert "PropertyChat" in httpx.get(server + "/").text
    r = httpx.get(server + "/widget.js")
    assert r.status_code == 200 and "javascript" in r.headers["content-type"]


def test_rag_gan_tai_lieu_lien_quan(server, yeu_cau_claude):
    ma, sk = chat(server, "Mua nhà phải đóng những loại thuế phí gì?")
    assert ma == 200 and sk[-1][0] == "done"
    assert "Khi mua nhà phải trả những khoản thuế phí nào?" in chu(sk)
    body = yeu_cau_claude[0]["body"]
    # tài liệu không còn nằm trong system prompt mà được tìm theo từng câu hỏi
    assert "lệ phí trước bạ" not in body["system"][0]["text"]
    cuoi = body["messages"][-1]["content"]
    assert cuoi[0]["text"].startswith("<tai_lieu_tham_khao>") and "lệ phí trước bạ" in cuoi[0]["text"]
    assert cuoi[1]["text"] == "Mua nhà phải đóng những loại thuế phí gì?"
    assert {t["name"] for t in body["tools"]} == {"tim_tin_dang", "tra_cuu_tai_lieu"}
    assert body["stream"] is True


def test_cau_hoi_noi_tiep_dung_ngu_canh_cau_truoc(server):
    ma, sk = chat(server, [
        {"role": "user", "content": "Cho mình hỏi về dự án An Lạc Garden"},
        {"role": "assistant", "content": "An Lạc Garden ở Thủ Đức."},
        {"role": "user", "content": "thanh toán thế nào?"},
    ])
    assert ma == 200 and "An Lạc Garden" in chu(sk)


def test_cau_chao_khong_co_tai_lieu(server):
    ma, sk = chat(server, "xin chào")
    assert chu(sk) == "Đã đọc tài liệu: không có" and sk[-1][0] == "done"


def test_tim_tin_dang_tra_ve_the(server, yeu_cau_claude):
    ma, sk = chat(server, "Có căn nào dưới 2 tỷ không?")
    loai = [l for l, _ in sk]
    assert loai.index("listings") < loai.index("text") and loai[-1] == "done"
    the = next(d for l, d in sk if l == "listings")["items"]
    assert [t["id"] for t in the] == ["T005"]
    assert "**1** căn" in chu(sk)
    assert len(yeu_cau_claude) == 2  # vòng 2 gửi kết quả công cụ cho Claude
    kq = yeu_cau_claude[1]["body"]["messages"][-1]["content"][0]
    assert kq["type"] == "tool_result" and not kq.get("is_error")


def test_tim_khong_co_ket_qua_khong_gui_the(server):
    ma, sk = chat(server, "Có căn nào dưới 0,5 tỷ không?")
    assert "listings" not in [l for l, _ in sk] and "**0** căn" in chu(sk)


def test_toi_da_6_the(server):
    ma, sk = chat(server, "nhà dưới 100 tỷ")
    assert len(next(d for l, d in sk if l == "listings")["items"]) == 6
    assert "**12** căn" in chu(sk)


def test_hoi_chi_tiet_theo_ma_tin(server):
    ma, sk = chat(server, "Cho mình xem chi tiết tin T003")
    assert [t["id"] for t in next(d for l, d in sk if l == "listings")["items"]] == ["T003"]


def test_cong_cu_tra_cuu_tai_lieu_va_tach_doan(server):
    ma, sk = chat(server, "tra cứu phí quản lý Sông Xanh")
    t = chu(sk)
    assert t.startswith("Để mình tra cứu.\n\nTheo tài liệu mục: Sông Xanh Residence")


def test_tham_so_cong_cu_sai(server, yeu_cau_claude):
    ma, sk = chat(server, "tham số sai")
    assert sk[-1][0] == "done" and "gặp lỗi" in chu(sk)
    assert yeu_cau_claude[1]["body"]["messages"][-1]["content"][0]["is_error"] is True


def test_claude_goi_cong_cu_mai_khong_dung(server, yeu_cau_claude):
    ma, sk = chat(server, "lặp mãi")
    assert sk[-1][0] == "error" and len(yeu_cau_claude) == 4


def test_tu_choi(server):
    ma, sk = chat(server, "từ chối đi")
    assert sk == [("error", {"message": "Xin lỗi, mình không thể hỗ trợ yêu cầu này."})]


def test_loi_api_claude(server):
    assert chat(server, "lỗi máy chủ")[1][-1] == ("error", {"message": "Có lỗi khi kết nối trợ lý, vui lòng thử lại."})
    assert chat(server, "quá tải")[1][-1][0] == "error"


def test_dut_ket_noi_giua_chung(server):
    ma, sk = chat(server, "đứt mạng")
    assert sk[-1][0] == "error"


def test_xss_duoc_tra_nguyen_van_de_widget_escape(server):
    assert "<img" in chu(chat(server, "xss")[1])


@pytest.mark.parametrize("messages, ma", [
    ([], 422),
    ([{"role": "user", "content": ""}], 422),
    ([{"role": "user", "content": "a" * 2001}], 422),
    ([{"role": "system", "content": "hi"}], 422),
    ([{"role": "user", "content": "hi"}, {"role": "assistant", "content": "chào"}], 400),
    ([{"role": "assistant", "content": "chào"}], 400),
])
def test_yeu_cau_khong_hop_le(server, messages, ma):
    assert chat(server, messages)[0] == ma


def test_body_khong_phai_json(server):
    r = httpx.post(server + "/api/chat", content="abc", headers={"Content-Type": "application/json"})
    assert r.status_code == 422


def test_lich_su_dai_chi_gui_20_tin_va_bat_dau_bang_khach(server, yeu_cau_claude):
    lich_su = []
    for i in range(15):
        lich_su += [{"role": "user", "content": f"câu {i}"}, {"role": "assistant", "content": f"đáp {i}"}]
    lich_su.append({"role": "user", "content": "xin chào"})
    ma, sk = chat(server, lich_su)
    gui = yeu_cau_claude[0]["body"]["messages"]
    assert ma == 200 and len(gui) <= 20 and gui[0]["role"] == "user"


def test_cors(server):
    r = httpx.options(server + "/api/chat", headers={
        "Origin": "https://web-cua-toi.vn", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"})
    assert r.status_code == 200 and r.headers["access-control-allow-origin"] in ("*", "https://web-cua-toi.vn")


def test_cors_gioi_han_ten_mien(claude_gia):
    p, url = chay_server(claude_gia, ALLOWED_ORIGINS="https://web-cua-toi.vn")
    try:
        hop_le = httpx.options(url + "/api/chat", headers={
            "Origin": "https://web-cua-toi.vn", "Access-Control-Request-Method": "POST"})
        la = httpx.options(url + "/api/chat", headers={
            "Origin": "https://web-khac.vn", "Access-Control-Request-Method": "POST"})
        assert hop_le.headers.get("access-control-allow-origin") == "https://web-cua-toi.vn"
        assert "access-control-allow-origin" not in la.headers
    finally:
        p.terminate()


def test_gioi_han_so_lan_hoi(claude_gia):
    p, url = chay_server(claude_gia, RATE_LIMIT_PER_MINUTE="3")
    try:
        ma = [chat(url, "xin chào")[0] for _ in range(4)]
        assert ma == [200, 200, 200, 429]
        assert "đợi" in chat(url, "xin chào")[1]["detail"]
    finally:
        p.terminate()


def test_thieu_api_key(claude_gia):
    p, url = chay_server(claude_gia, ANTHROPIC_API_KEY="")
    try:
        assert httpx.get(url + "/api/health").json()["co_api_key"] is False
        sk = chat(url, "xin chào")[1]
        assert sk[0][0] == "error" and "API key" in sk[0][1]["message"]
    finally:
        p.terminate()


def test_khong_ket_noi_duoc_claude():
    p, url = chay_server(None)  # cổng 9 không có gì
    try:
        bat_dau = time.time()
        sk = chat(url, "xin chào")[1]
        assert sk[-1] == ("error", {"message": "Không kết nối được tới trợ lý, vui lòng thử lại."})
        assert time.time() - bat_dau < 20
    finally:
        p.terminate()
