"""Load the real-estate data and filter listings by criteria."""

import csv
import os
import re
from pathlib import Path

from knowledge import strip_accents

DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parent.parent))

# Shown to customers, so the labels are in Vietnamese
TYPE_LABELS = {"apartment": "Căn hộ", "townhouse": "Nhà phố", "land": "Đất nền"}


def knowledge_files():
    """Knowledge files for RAG: projects.md, buying_faq.md and every .md/.txt file
    placed in the docs/ folder (except README.md)."""
    files = [DATA_DIR / name for name in ("projects.md", "buying_faq.md")
             if (DATA_DIR / name).is_file()]
    docs_dir = DATA_DIR / "docs"
    if docs_dir.is_dir():
        files += sorted(
            f for f in docs_dir.rglob("*")
            if f.is_file() and f.suffix.lower() in (".md", ".txt") and f.name.lower() != "readme.md"
        )
    return files


def _number(text, kind=float):
    """'3,2' or ' 3.2 ' -> 3.2; an empty cell -> 0."""
    text = (text or "").strip().replace(",", ".")
    return kind(float(text)) if text else kind(0)


def load_listings():
    """Read listings.csv. Malformed rows are skipped (with a warning) instead of crashing the server."""
    path = DATA_DIR / "listings.csv"
    if not path.is_file():
        print(f"Warning: {path} not found, the chat box will have no listings.")
        return []
    listings = []
    # utf-8-sig also reads CSV files saved from Excel (which start with a BOM)
    with open(path, encoding="utf-8-sig", newline="") as f:
        for line_no, row in enumerate(csv.DictReader(f), start=2):
            row = {(k or "").strip(): (v or "").strip() for k, v in row.items()}
            if not row.get("id"):
                continue
            try:
                listings.append({
                    "id": row["id"],
                    "title": row["title"],
                    "type": row["type"],
                    "type_label": TYPE_LABELS.get(row["type"], row["type"]),
                    "district": row["district"],
                    "city": row["city"],
                    "price_billion_vnd": _number(row["price_billion_vnd"]),
                    "area_m2": _number(row["area_m2"]),
                    "bedrooms": _number(row["bedrooms"], int),
                    "bathrooms": _number(row["bathrooms"], int),
                    "legal_status": row["legal_status"],
                    "project": row.get("project", ""),
                    "posted_date": row.get("posted_date", ""),
                    "description": row.get("description", ""),
                })
            except (KeyError, ValueError) as e:
                print(f"Warning: skipping line {line_no} of listings.csv ({e!r})")
    return listings


def _normalize(text):
    """Remove accents, collapse spaces, expand district abbreviations: 'Q.7', 'q7' -> 'quan 7'."""
    text = strip_accents(text)
    text = re.sub(r"(?<!\w)q\.?\s*(\d+)", r"quan \1", text)
    text = re.sub(r"[^\w]+", " ", text)
    return " ".join(text.split())


def _matches(value, keyword):
    """Whole-phrase match, ignoring case and accents.

    "Quận 1" does not match "Quận 10"; "thu duc" matches "TP. Thủ Đức"; "Q7" matches "Quận 7".
    """
    keyword = _normalize(keyword)
    if not keyword:
        return True
    return re.search(r"(?<!\w)" + re.escape(keyword) + r"(?!\w)", _normalize(value)) is not None


def search_listings(listings, criteria):
    """Filter listings by criteria; missing criteria are ignored. Sorted by price, cheapest first."""
    results = []
    for item in listings:
        if criteria.get("type") and item["type"] != criteria["type"]:
            continue
        if criteria.get("area") and not _matches(f'{item["district"]} {item["city"]}', criteria["area"]):
            continue
        if criteria.get("project") and not _matches(item["project"], criteria["project"]):
            continue
        if criteria.get("listing_id") and item["id"].lower() != criteria["listing_id"].strip().lower():
            continue
        if criteria.get("keyword") and not _matches(
                f'{item["title"]} {item["description"]} {item["project"]}', criteria["keyword"]):
            continue
        if criteria.get("min_price_billion") is not None and item["price_billion_vnd"] < criteria["min_price_billion"]:
            continue
        if criteria.get("max_price_billion") is not None and item["price_billion_vnd"] > criteria["max_price_billion"]:
            continue
        if criteria.get("min_bedrooms") is not None and item["bedrooms"] < criteria["min_bedrooms"]:
            continue
        if criteria.get("min_area_m2") is not None and item["area_m2"] < criteria["min_area_m2"]:
            continue
        # "Sổ hồng" is the Vietnamese ownership certificate
        if criteria.get("certificate_only") and "so hong" not in _normalize(item["legal_status"]):
            continue
        results.append(item)
    return sorted(results, key=lambda item: item["price_billion_vnd"])
