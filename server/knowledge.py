"""Knowledge base for RAG: split documents into chunks and find the chunks relevant to a question.

Uses BM25 (weighted keyword search) in pure Python, so no embedding model has to be
downloaded: the server stays small, starts fast and runs on free hosting tiers.
Extra handling for Vietnamese:
- diacritics are removed before matching, so a question typed without accents
  ("thu tuc sang ten") still finds "thủ tục sang tên";
- pairs of adjacent syllables are indexed too ("sổ hồng", "đặt cọc"), so exact phrases rank higher.
"""

import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

MAX_CHUNK_CHARS = 1500  # longer sections are split by paragraph
K1, B = 1.5, 0.75       # standard BM25 parameters

# Very common Vietnamese words (accents removed) that do not help tell chunks apart
STOPWORDS = set("""
la va cua co cho cac nhung mot duoc khong thi nay do voi trong khi de tu ra vao
nao gi bao nhieu the nhu sao a o oi nhe vay minh em anh toi hay
""".split())


def strip_accents(text):
    """'Sổ Hồng Đất' -> 'so hong dat'."""
    text = unicodedata.normalize("NFD", text.lower()).replace("đ", "d")
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def tokenize(text):
    """Return the syllables (accents removed, stopwords dropped) plus adjacent syllable pairs."""
    syllables = re.findall(r"\w+", strip_accents(text))
    pairs = [f"{a}_{b}" for a, b in zip(syllables, syllables[1:])]
    return [t for t in syllables if t not in STOPWORDS] + pairs


def split_into_chunks(source, content):
    """Each '## ' section becomes one chunk; sections that are too long are split by paragraph.

    Every chunk keeps the document title and section heading so it does not lose its context.
    """
    content = content.replace("\r\n", "\n").strip()
    doc_title = ""
    first_line = re.match(r"#\s+(.+)", content)
    if first_line:
        doc_title = first_line.group(1).strip()

    parts = re.split(r"^##\s+", content, flags=re.MULTILINE)
    intro = re.sub(r"^#\s+.*\n?", "", parts[0]).strip()
    sections = [("", intro)] if intro else []
    for part in parts[1:]:
        heading, _, body = part.partition("\n")
        sections.append((heading.strip(), body.strip()))

    chunks = []
    for heading, body in sections:
        if not body and not heading:
            continue
        for i, piece in enumerate(_split_long(body) or [""]):
            chunks.append({
                "id": f"{source}#{len(chunks) + 1}",
                "source": source,
                "document": doc_title,
                "section": heading + (f" (part {i + 1})" if i else ""),
                "text": piece,
            })
    return chunks


def _split_long(text):
    """Group paragraphs (separated by blank lines) into blocks of at most MAX_CHUNK_CHARS."""
    blocks, current = [], ""
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        while len(paragraph) > MAX_CHUNK_CHARS:  # a single huge paragraph: split by sentence
            cut = paragraph.rfind(". ", 0, MAX_CHUNK_CHARS)
            cut = cut + 1 if cut > 0 else MAX_CHUNK_CHARS
            if current:
                blocks.append(current)
                current = ""
            blocks.append(paragraph[:cut].strip())
            paragraph = paragraph[cut:].strip()
        if current and len(current) + len(paragraph) + 2 > MAX_CHUNK_CHARS:
            blocks.append(current)
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}" if current else paragraph
    if current:
        blocks.append(current)
    return blocks


class KnowledgeBase:
    def __init__(self, chunks):
        self.chunks = chunks
        self._term_freqs = []
        self._lengths = []
        doc_freq = Counter()
        for c in chunks:
            # the heading is repeated so a heading match scores higher than a body match
            terms = tokenize(f"{c['document']} {c['section']} {c['section']} {c['text']}")
            counts = Counter(terms)
            self._term_freqs.append(counts)
            self._lengths.append(len(terms))
            doc_freq.update(counts.keys())
        n = len(chunks)
        self._avg_length = (sum(self._lengths) / n) if n else 0
        self._idf = {t: math.log(1 + (n - df + 0.5) / (df + 0.5)) for t, df in doc_freq.items()}

    @classmethod
    def from_files(cls, paths):
        chunks = []
        for path in paths:
            path = Path(path)
            chunks.extend(split_into_chunks(path.name, path.read_text(encoding="utf-8")))
        return cls(chunks)

    def search(self, question, limit=4, relative_threshold=0.35):
        """Return up to `limit` of the most relevant chunks, with their scores.

        Chunks scoring below `relative_threshold` times the best score are dropped
        so off-topic text is not stuffed into Claude's context.
        """
        query_terms = set(tokenize(question or ""))
        if not query_terms or not self.chunks:
            return []
        scores = []
        for i, counts in enumerate(self._term_freqs):
            s = 0.0
            for t in query_terms:
                f = counts.get(t)
                if f:
                    s += self._idf[t] * f * (K1 + 1) / (
                        f + K1 * (1 - B + B * self._lengths[i] / self._avg_length))
            if s > 0:
                scores.append((s, i))
        if not scores:
            return []
        scores.sort(reverse=True)
        best = scores[0][0]
        return [
            {**self.chunks[i], "score": round(s, 3)}
            for s, i in scores[:limit]
            if s >= best * relative_threshold
        ]


def format_chunks(chunks):
    """Format the retrieved chunks for Claude."""
    return "\n\n".join(
        f'<document source="{c["source"]}" section="{c["section"]}">\n{c["text"]}\n</document>'
        for c in chunks
    )
