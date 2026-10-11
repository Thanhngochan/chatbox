"""Kho tài liệu cho RAG: cắt tài liệu thành đoạn và tìm đoạn liên quan tới câu hỏi.

Dùng BM25 (tìm theo từ khoá có trọng số) chạy thuần Python, không cần tải model
embedding nên server nhẹ, khởi động nhanh, chạy được trên gói hosting miễn phí.
Tiếng Việt được xử lý thêm:
- bỏ dấu khi so khớp, nên khách gõ không dấu ("thu tuc sang ten") vẫn tìm được;
- đánh chỉ mục cả cặp âm tiết liền nhau ("sổ hồng", "đặt cọc") để ưu tiên đúng cụm từ.
"""

import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

DO_DAI_DOAN_TOI_DA = 1500  # ký tự; mục dài hơn sẽ được cắt theo đoạn văn
K1, B = 1.5, 0.75          # tham số chuẩn của BM25

# Từ quá phổ biến, không giúp phân biệt đoạn nào liên quan
TU_DUNG = set("""
la va cua co cho cac nhung mot duoc khong thi nay do voi trong khi de tu ra vao
nao gi bao nhieu the nhu sao a o oi nhe vay minh em anh toi hay
""".split())


def bo_dau(chu):
    """'Sổ Hồng Đất' -> 'so hong dat'."""
    chu = unicodedata.normalize("NFD", chu.lower()).replace("đ", "d")
    return "".join(c for c in chu if unicodedata.category(c) != "Mn")


def tach_tu(chu):
    """Trả về các âm tiết (đã bỏ dấu, bỏ từ dừng) và các cặp âm tiết liền nhau."""
    am_tiet = re.findall(r"\w+", bo_dau(chu))
    cap = [f"{a}_{b}" for a, b in zip(am_tiet, am_tiet[1:])]
    return [t for t in am_tiet if t not in TU_DUNG] + cap


def cat_doan(ten_nguon, noi_dung):
    """Mỗi mục '## ' là một đoạn; mục quá dài được cắt nhỏ theo đoạn văn.

    Đoạn nào cũng mang theo tiêu đề tài liệu và tiêu đề mục để không mất ngữ cảnh.
    """
    noi_dung = noi_dung.replace("\r\n", "\n").strip()
    tieu_de_tai_lieu = ""
    dong_dau = re.match(r"#\s+(.+)", noi_dung)
    if dong_dau:
        tieu_de_tai_lieu = dong_dau.group(1).strip()

    cac_muc = re.split(r"^##\s+", noi_dung, flags=re.MULTILINE)
    phan_mo_dau = re.sub(r"^#\s+.*\n?", "", cac_muc[0]).strip()
    muc = [("", phan_mo_dau)] if phan_mo_dau else []
    for phan in cac_muc[1:]:
        tieu_de, _, than = phan.partition("\n")
        muc.append((tieu_de.strip(), than.strip()))

    cac_doan = []
    for tieu_de, than in muc:
        if not than and not tieu_de:
            continue
        for i, manh in enumerate(_cat_nho(than) or [""]):
            cac_doan.append({
                "id": f"{ten_nguon}#{len(cac_doan) + 1}",
                "nguon": ten_nguon,
                "tai_lieu": tieu_de_tai_lieu,
                "muc": tieu_de + (f" (phần {i + 1})" if i else ""),
                "noi_dung": manh,
            })
    return cac_doan


def _cat_nho(van_ban):
    """Gom các đoạn văn (cách nhau bằng dòng trống) thành khối không quá DO_DAI_DOAN_TOI_DA."""
    khoi, hien_tai = [], ""
    for doan_van in re.split(r"\n\s*\n", van_ban):
        doan_van = doan_van.strip()
        if not doan_van:
            continue
        while len(doan_van) > DO_DAI_DOAN_TOI_DA:  # một đoạn văn quá dài: cắt theo câu
            vi_tri = doan_van.rfind(". ", 0, DO_DAI_DOAN_TOI_DA)
            vi_tri = vi_tri + 1 if vi_tri > 0 else DO_DAI_DOAN_TOI_DA
            if hien_tai:
                khoi.append(hien_tai)
                hien_tai = ""
            khoi.append(doan_van[:vi_tri].strip())
            doan_van = doan_van[vi_tri:].strip()
        if hien_tai and len(hien_tai) + len(doan_van) + 2 > DO_DAI_DOAN_TOI_DA:
            khoi.append(hien_tai)
            hien_tai = doan_van
        else:
            hien_tai = f"{hien_tai}\n\n{doan_van}" if hien_tai else doan_van
    if hien_tai:
        khoi.append(hien_tai)
    return khoi


class KhoTaiLieu:
    def __init__(self, cac_doan):
        self.cac_doan = cac_doan
        self._tan_suat = []
        self._do_dai = []
        so_doan_chua = Counter()
        for d in cac_doan:
            # tiêu đề lặp 2 lần để khớp tiêu đề được điểm cao hơn khớp thân bài
            tu = tach_tu(f"{d['tai_lieu']} {d['muc']} {d['muc']} {d['noi_dung']}")
            dem = Counter(tu)
            self._tan_suat.append(dem)
            self._do_dai.append(len(tu))
            so_doan_chua.update(dem.keys())
        n = len(cac_doan)
        self._do_dai_tb = (sum(self._do_dai) / n) if n else 0
        self._idf = {t: math.log(1 + (n - df + 0.5) / (df + 0.5)) for t, df in so_doan_chua.items()}

    @classmethod
    def tu_thu_muc(cls, cac_file):
        cac_doan = []
        for duong_dan in cac_file:
            duong_dan = Path(duong_dan)
            cac_doan.extend(cat_doan(duong_dan.name, duong_dan.read_text(encoding="utf-8")))
        return cls(cac_doan)

    def tim(self, cau_hoi, so_doan=4, nguong_tuong_doi=0.35):
        """Trả về tối đa `so_doan` đoạn liên quan nhất, kèm điểm.

        Bỏ các đoạn có điểm thấp hơn `nguong_tuong_doi` lần điểm của đoạn tốt nhất
        để không nhồi tài liệu lạc đề cho Claude.
        """
        tu_hoi = set(tach_tu(cau_hoi or ""))
        if not tu_hoi or not self.cac_doan:
            return []
        diem = []
        for i, dem in enumerate(self._tan_suat):
            s = 0.0
            for t in tu_hoi:
                f = dem.get(t)
                if f:
                    s += self._idf[t] * f * (K1 + 1) / (
                        f + K1 * (1 - B + B * self._do_dai[i] / self._do_dai_tb))
            if s > 0:
                diem.append((s, i))
        if not diem:
            return []
        diem.sort(reverse=True)
        cao_nhat = diem[0][0]
        return [
            {**self.cac_doan[i], "diem": round(s, 3)}
            for s, i in diem[:so_doan]
            if s >= cao_nhat * nguong_tuong_doi
        ]


def dinh_dang(cac_doan):
    """Định dạng các đoạn tìm được để đưa cho Claude."""
    return "\n\n".join(
        f'<tai_lieu nguon="{d["nguon"]}" muc="{d["muc"]}">\n{d["noi_dung"]}\n</tai_lieu>'
        for d in cac_doan
    )
