"""Tests for loading data, filtering listings and searching documents (no server needed)."""

import listings as listings_module
from knowledge import KnowledgeBase, split_into_chunks, strip_accents
from listings import knowledge_files, load_listings, search_listings

LISTINGS = load_listings()
KB = KnowledgeBase.from_files(knowledge_files())


def ids(criteria):
    return [item["id"] for item in search_listings(LISTINGS, criteria)]


def test_loads_all_12_listings():
    assert len(LISTINGS) == 12
    assert LISTINGS[0]["price_billion_vnd"] == 3.2 and LISTINGS[0]["bedrooms"] == 2
    assert LISTINGS[0]["type_label"] == "Căn hộ"


def test_no_criteria_returns_everything_cheapest_first():
    results = search_listings(LISTINGS, {})
    assert len(results) == 12
    prices = [item["price_billion_vnd"] for item in results]
    assert prices == sorted(prices)


def test_area_without_accents_and_abbreviations():
    assert set(ids({"area": "Quận 7"})) == {"T001", "T002", "T003"}
    assert ids({"area": "q7"}) == ids({"area": "Q.7"}) == ids({"area": "quan 7"})
    assert set(ids({"area": "thu duc"})) == {"T004", "T005", "T006"}


def test_district_1_does_not_match_district_10():
    assert set(ids({"area": "Quận 1"})) == {"T011", "T012"}
    assert ids({"area": "Quận 10"}) == ["T009"]


def test_unknown_area():
    assert ids({"area": "Hà Nội"}) == []


def test_price_bedrooms_area_certificate_filters():
    assert ids({"max_price_billion": 2}) == ["T005"]
    assert all(t["price_billion_vnd"] >= 5 for t in search_listings(LISTINGS, {"min_price_billion": 5}))
    assert all(t["bedrooms"] >= 3 for t in search_listings(LISTINGS, {"min_bedrooms": 3}))
    assert all(t["area_m2"] >= 90 for t in search_listings(LISTINGS, {"min_area_m2": 90}))
    assert "T004" not in ids({"certificate_only": True})
    assert "T010" in ids({"certificate_only": True})  # "Sổ hồng riêng"


def test_listing_id_keyword_project_type():
    assert ids({"listing_id": "t003"}) == ["T003"]
    assert ids({"keyword": "view song"}) == ["T001"]
    assert ids({"keyword": "hẻm xe hơi"}) == ["T007"]
    assert set(ids({"project": "an lac"})) == {"T004", "T005", "T006"}
    assert ids({"type": "land"}) == ["T010"]


def test_csv_from_excel_with_bom_and_bad_rows(tmp_path, monkeypatch, capsys):
    (tmp_path / "listings.csv").write_text(
        "﻿id,title,type,district,city,price_billion_vnd,area_m2,bedrooms,bathrooms,"
        "legal_status,project,posted_date,description\n"
        'X1,Căn A,apartment,Quận 7,TP.HCM,"3,5",70,2,2,Sổ hồng,,2026-01-01,ok\n'
        "X2,Căn lỗi,apartment,Quận 7,TP.HCM,unknown,70,2,2,Sổ hồng,,2026-01-01,\n"
        ",,,,,,,,,,,,\n",
        encoding="utf-8")
    monkeypatch.setattr(listings_module, "DATA_DIR", tmp_path)
    loaded = listings_module.load_listings()
    assert [t["id"] for t in loaded] == ["X1"] and loaded[0]["price_billion_vnd"] == 3.5
    assert "skipping line 3" in capsys.readouterr().out


def test_missing_files_do_not_crash(tmp_path, monkeypatch):
    monkeypatch.setattr(listings_module, "DATA_DIR", tmp_path)
    assert listings_module.load_listings() == []
    assert listings_module.knowledge_files() == []
    assert KnowledgeBase.from_files([]).search("thuế phí") == []


def test_extra_docs_folder(tmp_path, monkeypatch):
    (tmp_path / "docs" / "sub").mkdir(parents=True)
    (tmp_path / "docs" / "README.md").write_text("ignored", encoding="utf-8")
    (tmp_path / "docs" / "sub" / "loans.txt").write_text("## Vay\nLãi suất", encoding="utf-8")
    (tmp_path / "docs" / "image.png").write_bytes(b"\x89PNG")
    monkeypatch.setattr(listings_module, "DATA_DIR", tmp_path)
    assert [f.name for f in listings_module.knowledge_files()] == ["loans.txt"]


# ---------- RAG ----------
def test_strip_accents():
    assert strip_accents("Sổ Hồng ĐẤT đỏ") == "so hong dat do"


def test_chunks_by_section_and_long_sections_are_split():
    chunks = split_into_chunks("a.md", "# Title\n\nIntro.\n\n## Section 1\nBody 1\n\n## Section 2\n" +
                               "\n\n".join(f"Paragraph number {i}. " * 30 for i in range(10)))
    assert chunks[0]["section"] == "" and chunks[0]["text"] == "Intro."
    assert chunks[1]["section"] == "Section 1" and chunks[1]["document"] == "Title"
    assert len([c for c in chunks if c["section"].startswith("Section 2")]) > 1
    assert all(len(c["text"]) <= 1500 for c in chunks)
    assert len({c["id"] for c in chunks}) == len(chunks)


def test_text_without_headings_and_huge_paragraph():
    chunks = split_into_chunks("b.txt", "A very long sentence with no line breaks. " * 200)
    assert len(chunks) > 1 and all(0 < len(c["text"]) <= 1500 for c in chunks)
    assert split_into_chunks("empty.md", "   ") == []


def top_section(question):
    found = KB.search(question)
    return found[0]["section"] if found else None


def test_finds_the_right_section():
    assert top_section("Mua nhà phải đóng những loại thuế phí gì?").startswith("Khi mua nhà phải trả")
    assert top_section("Dự án nào gần metro?") == "An Lạc Garden"
    assert top_section("An Lạc Garden thanh toán thế nào?") == "An Lạc Garden"
    assert top_section("an lac garden thanh toan the nao") == "An Lạc Garden"  # typed without accents
    assert top_section("đặt cọc rồi đổi ý thì sao").startswith("Đặt cọc")
    assert top_section("vay ngân hàng tối đa bao nhiêu").startswith("Vay ngân hàng")
    assert top_section("Thiên Phú có chỗ đậu ô tô không") == "Thiên Phú Tower"
    assert top_section("sổ hồng khác hợp đồng mua bán").startswith("Sổ hồng và hợp đồng")


def test_unrelated_questions_find_nothing():
    assert KB.search("xin chào") == []
    assert KB.search("") == []
    assert KB.search("!!! ???") == []


def test_limit():
    assert len(KB.search("nhà căn hộ dự án mua bán", limit=2)) <= 2
