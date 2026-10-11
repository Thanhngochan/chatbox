"""Đọc dữ liệu bất động sản và tìm tin đăng theo điều kiện."""

import csv
import os
import re
from pathlib import Path

THU_MUC_DU_LIEU = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parent.parent))

TEN_LOAI = {"can_ho": "Căn hộ", "nha_pho": "Nhà phố", "dat_nen": "Đất nền"}


def doc_tai_lieu():
    """Gộp các file kiến thức (.md) thành một khối văn bản cho system prompt."""
    cac_phan = []
    for ten_file in ("du_an.md", "hoi_dap_mua_nha.md"):
        noi_dung = (THU_MUC_DU_LIEU / ten_file).read_text(encoding="utf-8")
        cac_phan.append(f'<tai_lieu nguon="{ten_file}">\n{noi_dung.strip()}\n</tai_lieu>')
    return "\n\n".join(cac_phan)


def doc_tin_dang():
    with open(THU_MUC_DU_LIEU / "tin_dang.csv", encoding="utf-8") as f:
        cac_tin = []
        for dong in csv.DictReader(f):
            cac_tin.append({
                "id": dong["id"],
                "tieu_de": dong["tieu_de"],
                "loai": dong["loai"],
                "ten_loai": TEN_LOAI.get(dong["loai"], dong["loai"]),
                "quan": dong["quan"],
                "thanh_pho": dong["thanh_pho"],
                "gia_ty": float(dong["gia_ty"]),
                "dien_tich_m2": float(dong["dien_tich_m2"]),
                "phong_ngu": int(dong["phong_ngu"]),
                "phong_tam": int(dong["phong_tam"]),
                "phap_ly": dong["phap_ly"],
                "du_an": dong["du_an"],
                "ngay_dang": dong["ngay_dang"],
                "mo_ta": dong["mo_ta"],
            })
    return cac_tin


def _khop_chu(gia_tri, tu_khoa):
    """So khớp nguyên cụm từ, không phân biệt hoa thường ("Quận 1" không khớp "Quận 10")."""
    mau = r"(?<!\w)" + re.escape(tu_khoa.strip().lower()) + r"(?!\w)"
    return re.search(mau, gia_tri.lower()) is not None


def tim_tin_dang(cac_tin, dieu_kien):
    """Lọc tin đăng theo điều kiện; trường nào thiếu thì bỏ qua."""
    ket_qua = []
    for tin in cac_tin:
        if dieu_kien.get("loai") and tin["loai"] != dieu_kien["loai"]:
            continue
        if dieu_kien.get("khu_vuc") and not _khop_chu(tin["quan"], dieu_kien["khu_vuc"]):
            continue
        if dieu_kien.get("du_an") and not _khop_chu(tin["du_an"], dieu_kien["du_an"]):
            continue
        if dieu_kien.get("gia_toi_thieu_ty") is not None and tin["gia_ty"] < dieu_kien["gia_toi_thieu_ty"]:
            continue
        if dieu_kien.get("gia_toi_da_ty") is not None and tin["gia_ty"] > dieu_kien["gia_toi_da_ty"]:
            continue
        if dieu_kien.get("phong_ngu_toi_thieu") is not None and tin["phong_ngu"] < dieu_kien["phong_ngu_toi_thieu"]:
            continue
        if dieu_kien.get("dien_tich_toi_thieu_m2") is not None and tin["dien_tich_m2"] < dieu_kien["dien_tich_toi_thieu_m2"]:
            continue
        if dieu_kien.get("chi_co_so_hong") and "sổ hồng" not in tin["phap_ly"].lower():
            continue
        ket_qua.append(tin)
    return sorted(ket_qua, key=lambda t: t["gia_ty"])
