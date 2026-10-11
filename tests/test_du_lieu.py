"""Kiểm tra phần đọc dữ liệu, lọc tin đăng và tìm tài liệu (không cần server)."""

import du_lieu
from du_lieu import cac_file_tai_lieu, doc_tin_dang, tim_tin_dang
from kho_tai_lieu import KhoTaiLieu, bo_dau, cat_doan

TIN = doc_tin_dang()
KHO = KhoTaiLieu.tu_thu_muc(cac_file_tai_lieu())


def ids(dk):
    return [t["id"] for t in tim_tin_dang(TIN, dk)]


def test_doc_du_12_tin():
    assert len(TIN) == 12
    assert TIN[0]["gia_ty"] == 3.2 and TIN[0]["phong_ngu"] == 2


def test_khong_dieu_kien_tra_ve_tat_ca_theo_gia_tang_dan():
    kq = tim_tin_dang(TIN, {})
    assert len(kq) == 12
    assert [t["gia_ty"] for t in kq] == sorted(t["gia_ty"] for t in kq)


def test_loc_khu_vuc_khong_dau_viet_tat():
    assert set(ids({"khu_vuc": "Quận 7"})) == {"T001", "T002", "T003"}
    assert ids({"khu_vuc": "q7"}) == ids({"khu_vuc": "Q.7"}) == ids({"khu_vuc": "quan 7"})
    assert set(ids({"khu_vuc": "thu duc"})) == {"T004", "T005", "T006"}


def test_quan_1_khong_khop_quan_10():
    assert set(ids({"khu_vuc": "Quận 1"})) == {"T011", "T012"}
    assert ids({"khu_vuc": "Quận 10"}) == ["T009"]


def test_khu_vuc_khong_co():
    assert ids({"khu_vuc": "Hà Nội"}) == []


def test_loc_gia_phong_dien_tich_so_hong():
    assert ids({"gia_toi_da_ty": 2}) == ["T005"]
    assert all(t["gia_ty"] >= 5 for t in tim_tin_dang(TIN, {"gia_toi_thieu_ty": 5}))
    assert all(t["phong_ngu"] >= 3 for t in tim_tin_dang(TIN, {"phong_ngu_toi_thieu": 3}))
    assert all(t["dien_tich_m2"] >= 90 for t in tim_tin_dang(TIN, {"dien_tich_toi_thieu_m2": 90}))
    assert "T004" not in ids({"chi_co_so_hong": True})
    assert "T010" in ids({"chi_co_so_hong": True})  # "Sổ hồng riêng"


def test_ma_tin_tu_khoa_du_an():
    assert ids({"ma_tin": "t003"}) == ["T003"]
    assert ids({"tu_khoa": "view song"}) == ["T001"]
    assert ids({"tu_khoa": "hẻm xe hơi"}) == ["T007"]
    assert set(ids({"du_an": "an lac"})) == {"T004", "T005", "T006"}


def test_csv_tu_excel_co_bom_va_dong_loi(tmp_path, monkeypatch, capsys):
    (tmp_path / "tin_dang.csv").write_text(
        "﻿id,tieu_de,loai,quan,thanh_pho,gia_ty,dien_tich_m2,phong_ngu,phong_tam,phap_ly,du_an,ngay_dang,mo_ta\n"
        'X1,Căn A,can_ho,Quận 7,TP.HCM,"3,5",70,2,2,Sổ hồng,,2026-01-01,ok\n'
        "X2,Căn lỗi,can_ho,Quận 7,TP.HCM,khong-biet,70,2,2,Sổ hồng,,2026-01-01,\n"
        ",,,,,,,,,,,,\n",
        encoding="utf-8")
    monkeypatch.setattr(du_lieu, "THU_MUC_DU_LIEU", tmp_path)
    tin = du_lieu.doc_tin_dang()
    assert [t["id"] for t in tin] == ["X1"] and tin[0]["gia_ty"] == 3.5
    assert "bỏ qua dòng 3" in capsys.readouterr().out


def test_thieu_file_csv_khong_sap(tmp_path, monkeypatch):
    monkeypatch.setattr(du_lieu, "THU_MUC_DU_LIEU", tmp_path)
    assert du_lieu.doc_tin_dang() == []
    assert du_lieu.cac_file_tai_lieu() == []
    assert KhoTaiLieu.tu_thu_muc([]).tim("thuế phí") == []


def test_thu_muc_tai_lieu_them(tmp_path, monkeypatch):
    (tmp_path / "tai_lieu" / "con").mkdir(parents=True)
    (tmp_path / "tai_lieu" / "README.md").write_text("bỏ qua", encoding="utf-8")
    (tmp_path / "tai_lieu" / "con" / "vay.txt").write_text("## Vay\nLãi suất", encoding="utf-8")
    (tmp_path / "tai_lieu" / "anh.png").write_bytes(b"\x89PNG")
    monkeypatch.setattr(du_lieu, "THU_MUC_DU_LIEU", tmp_path)
    assert [f.name for f in du_lieu.cac_file_tai_lieu()] == ["vay.txt"]


# ---------- RAG ----------
def test_bo_dau():
    assert bo_dau("Sổ Hồng ĐẤT đỏ") == "so hong dat do"


def test_cat_doan_theo_muc_va_cat_muc_dai():
    doan = cat_doan("a.md", "# Tiêu đề\n\nMở đầu.\n\n## Mục 1\nNội dung 1\n\n## Mục 2\n" +
                    "\n\n".join(f"Đoạn văn số {i}. " * 30 for i in range(10)))
    assert doan[0]["muc"] == "" and doan[0]["noi_dung"] == "Mở đầu."
    assert doan[1]["muc"] == "Mục 1" and doan[1]["tai_lieu"] == "Tiêu đề"
    phan_muc_2 = [d for d in doan if d["muc"].startswith("Mục 2")]
    assert len(phan_muc_2) > 1
    assert all(len(d["noi_dung"]) <= 1500 for d in doan)
    assert len({d["id"] for d in doan}) == len(doan)


def test_cat_doan_van_ban_khong_tieu_de_va_doan_cuc_dai():
    doan = cat_doan("b.txt", "Câu rất dài không xuống dòng. " * 200)
    assert len(doan) > 1 and all(0 < len(d["noi_dung"]) <= 1500 for d in doan)
    assert cat_doan("rong.md", "   ") == []


def muc_dau(cau):
    kq = KHO.tim(cau)
    return kq[0]["muc"] if kq else None


def test_tim_dung_muc():
    assert muc_dau("Mua nhà phải đóng những loại thuế phí gì?").startswith("Khi mua nhà phải trả")
    assert muc_dau("Dự án nào gần metro?") == "An Lạc Garden"
    assert muc_dau("An Lạc Garden thanh toán thế nào?") == "An Lạc Garden"
    assert muc_dau("an lac garden thanh toan the nao") == "An Lạc Garden"  # gõ không dấu
    assert muc_dau("đặt cọc rồi đổi ý thì sao").startswith("Đặt cọc")
    assert muc_dau("vay ngân hàng tối đa bao nhiêu").startswith("Vay ngân hàng")
    assert muc_dau("Thiên Phú có chỗ đậu ô tô không") == "Thiên Phú Tower"
    assert muc_dau("sổ hồng khác hợp đồng mua bán") .startswith("Sổ hồng và hợp đồng")


def test_cau_khong_lien_quan():
    assert KHO.tim("xin chào") == []
    assert KHO.tim("") == []
    assert KHO.tim("!!! ???") == []


def test_gioi_han_so_doan():
    assert len(KHO.tim("nhà căn hộ dự án mua bán", so_doan=2)) <= 2
