"""Đọc dữ liệu bất động sản và tìm tin đăng theo điều kiện."""

import csv
import os
import re
from pathlib import Path

from kho_tai_lieu import bo_dau

THU_MUC_DU_LIEU = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parent.parent))

TEN_LOAI = {"can_ho": "Căn hộ", "nha_pho": "Nhà phố", "dat_nen": "Đất nền"}


def cac_file_tai_lieu():
    """Các file kiến thức cho RAG: du_an.md, hoi_dap_mua_nha.md và mọi file .md/.txt
    bỏ vào thư mục tai_lieu/ (trừ README.md)."""
    cac_file = [THU_MUC_DU_LIEU / ten for ten in ("du_an.md", "hoi_dap_mua_nha.md")
                if (THU_MUC_DU_LIEU / ten).is_file()]
    thu_muc = THU_MUC_DU_LIEU / "tai_lieu"
    if thu_muc.is_dir():
        cac_file += sorted(
            f for f in thu_muc.rglob("*")
            if f.is_file() and f.suffix.lower() in (".md", ".txt") and f.name.lower() != "readme.md"
        )
    return cac_file


def _so(chu, kieu=float):
    """'3,2' hoặc ' 3.2 ' -> 3.2; ô trống -> 0."""
    chu = (chu or "").strip().replace(",", ".")
    return kieu(float(chu)) if chu else kieu(0)


def doc_tin_dang():
    """Đọc tin_dang.csv. Dòng sai định dạng bị bỏ qua (có in cảnh báo) thay vì làm sập server."""
    duong_dan = THU_MUC_DU_LIEU / "tin_dang.csv"
    if not duong_dan.is_file():
        print(f"Cảnh báo: không thấy {duong_dan}, chat box sẽ không có tin đăng.")
        return []
    cac_tin = []
    # utf-8-sig: đọc được cả file CSV lưu từ Excel (có BOM ở đầu)
    with open(duong_dan, encoding="utf-8-sig", newline="") as f:
        for so_dong, dong in enumerate(csv.DictReader(f), start=2):
            dong = {(k or "").strip(): (v or "").strip() for k, v in dong.items()}
            if not dong.get("id"):
                continue
            try:
                cac_tin.append({
                    "id": dong["id"],
                    "tieu_de": dong["tieu_de"],
                    "loai": dong["loai"],
                    "ten_loai": TEN_LOAI.get(dong["loai"], dong["loai"]),
                    "quan": dong["quan"],
                    "thanh_pho": dong["thanh_pho"],
                    "gia_ty": _so(dong["gia_ty"]),
                    "dien_tich_m2": _so(dong["dien_tich_m2"]),
                    "phong_ngu": _so(dong["phong_ngu"], int),
                    "phong_tam": _so(dong["phong_tam"], int),
                    "phap_ly": dong["phap_ly"],
                    "du_an": dong.get("du_an", ""),
                    "ngay_dang": dong.get("ngay_dang", ""),
                    "mo_ta": dong.get("mo_ta", ""),
                })
            except (KeyError, ValueError) as e:
                print(f"Cảnh báo: bỏ qua dòng {so_dong} trong tin_dang.csv ({e!r})")
    return cac_tin


def _chuan_hoa(chu):
    """Bỏ dấu, gộp khoảng trắng, đổi cách viết tắt quận: 'Q.7', 'q7' -> 'quan 7'."""
    chu = bo_dau(chu)
    chu = re.sub(r"(?<!\w)q\.?\s*(\d+)", r"quan \1", chu)
    chu = re.sub(r"[^\w]+", " ", chu)
    return " ".join(chu.split())


def _khop_chu(gia_tri, tu_khoa):
    """So khớp nguyên cụm từ, không phân biệt hoa thường hay dấu.

    "Quận 1" không khớp "Quận 10"; "thu duc" khớp "TP. Thủ Đức"; "Q7" khớp "Quận 7".
    """
    tu_khoa = _chuan_hoa(tu_khoa)
    if not tu_khoa:
        return True
    return re.search(r"(?<!\w)" + re.escape(tu_khoa) + r"(?!\w)", _chuan_hoa(gia_tri)) is not None


def tim_tin_dang(cac_tin, dieu_kien):
    """Lọc tin đăng theo điều kiện; trường nào thiếu thì bỏ qua."""
    ket_qua = []
    for tin in cac_tin:
        if dieu_kien.get("loai") and tin["loai"] != dieu_kien["loai"]:
            continue
        if dieu_kien.get("khu_vuc") and not _khop_chu(f'{tin["quan"]} {tin["thanh_pho"]}', dieu_kien["khu_vuc"]):
            continue
        if dieu_kien.get("du_an") and not _khop_chu(tin["du_an"], dieu_kien["du_an"]):
            continue
        if dieu_kien.get("ma_tin") and tin["id"].lower() != dieu_kien["ma_tin"].strip().lower():
            continue
        if dieu_kien.get("tu_khoa") and not _khop_chu(
                f'{tin["tieu_de"]} {tin["mo_ta"]} {tin["du_an"]}', dieu_kien["tu_khoa"]):
            continue
        if dieu_kien.get("gia_toi_thieu_ty") is not None and tin["gia_ty"] < dieu_kien["gia_toi_thieu_ty"]:
            continue
        if dieu_kien.get("gia_toi_da_ty") is not None and tin["gia_ty"] > dieu_kien["gia_toi_da_ty"]:
            continue
        if dieu_kien.get("phong_ngu_toi_thieu") is not None and tin["phong_ngu"] < dieu_kien["phong_ngu_toi_thieu"]:
            continue
        if dieu_kien.get("dien_tich_toi_thieu_m2") is not None and tin["dien_tich_m2"] < dieu_kien["dien_tich_toi_thieu_m2"]:
            continue
        if dieu_kien.get("chi_co_so_hong") and "so hong" not in _chuan_hoa(tin["phap_ly"]):
            continue
        ket_qua.append(tin)
    return sorted(ket_qua, key=lambda t: t["gia_ty"])
