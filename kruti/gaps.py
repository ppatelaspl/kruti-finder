"""Find content in the books that the team has not yet entered in the Excel.

Devotional Kruti are numbered verse by verse (॥1॥ ... ॥7॥). A run of verse numbers that
restarts at 1 marks a new Kruti. Every such block not covered by a Kruti from the Excel
becomes a "missing Kruti" with its title, first verse (Aadi Vakya), last verse (Ant Vakya)
and pages. The same missing Kruti found in several books is grouped into one row.
"""
import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz, process

from .normalize import key_only

# ॥12॥ ; OCR often garbles the number (॥[॥, ॥l॥) - those are inferred from the sequence
_VERSE_MARK = re.compile(r"[।॥]\s*([\dIl|\[\]()!]{1,3}|\s?)\s*[।॥]")
_VERSE_PUNCT = re.compile(r"[।॥,;]")


@dataclass
class Gap:
    book: str
    start_page: int
    end_page: int
    verses: int
    author_signature: str
    title: str
    aadi: str
    ant: str
    ocr_quality: str
    span: tuple
    temp_id: str = ""
    also_in: list = field(default_factory=list)   # (book, start, end) of duplicate copies


def _heading_between(text: str, title_keys: list) -> bool:
    """A short line naming a Kruti type (स्तवन, सज्झाय, गीत ...) starts a new Kruti,
    even when OCR has garbled the verse numbers."""
    for ln in text.split("\n")[1:]:           # [0] is the tail of the previous verse
        ln = ln.strip()
        if 2 < len(ln) <= 60 and not _VERSE_PUNCT.search(ln):
            k = key_only(ln)
            if any(k.endswith(t) for t in title_keys):
                return True
    return False


def _verse_blocks(light: str, title_keys: list):
    blocks, current, prev_end = [], [], 0
    for m in _VERSE_MARK.finditer(light):
        raw = m.group(1).strip()
        if raw.isdigit():
            n = int(raw)
        elif current:
            n = current[-1][0] + 1          # unreadable number: assume next verse
        else:
            n = 1
        if n == 0:                          # OCR misread; keep the sequence going
            n = current[-1][0] + 1 if current else 1
        if current and _heading_between(light[prev_end:m.start()], title_keys):
            blocks.append(current)
            current = []
            n = 1
        prev_end = m.end()
        if current and n < current[-1][0] and n <= 2:
            blocks.append(current)
            current = []
        current.append((n, m.start(), m.end()))
    if current:
        blocks.append(current)
    return blocks


def _clean(text: str) -> str:
    return " ".join(text.split())


def _split_title(opening: str):
    """Short heading lines before verse 1 (no dandas/commas) are the Kruti title."""
    lines = [ln.strip() for ln in opening.split("\n") if ln.strip()]
    title = []
    while len(lines) > 1 and len(lines[0]) <= 60 and not _VERSE_PUNCT.search(lines[0]):
        title.append(lines.pop(0))
    return _clean(" ".join(title)), _clean(" ".join(lines))


def _has_signature(text: str, keywords: list) -> bool:
    k = key_only(text)
    return any(fuzz.partial_ratio(key_only(w), k) >= 85 for w in keywords if w.strip())


def find_gaps(book, covered_spans: list, page_conf: dict, cfg) -> list:
    gaps, prev_end = [], 0
    title_keys = [key_only(t) for t in cfg.get("title_keywords", []) if key_only(t)]
    for block in _verse_blocks(book.light, title_keys):
        first, last = block[0], block[-1]
        block_start = max(prev_end, first[1] - cfg["gap_max_verse_chars"])
        while block_start < first[1] and book.light[block_start].isspace():
            block_start += 1
        block_end = last[2]
        prev_end = block_end
        if len(block) < cfg["gap_min_verses"]:
            continue
        length = max(1, block_end - block_start)
        overlap = sum(max(0, min(block_end, e) - max(block_start, s)) for s, e in covered_spans)
        # skip blocks already accounted for: mostly covered by a matched Kruti, or holding
        # the lone start/end of a Partially Found one
        anchored = any(block_start <= s < block_end for s, _ in covered_spans)
        if overlap / length >= 0.5 or anchored:
            continue

        title, aadi = _split_title(book.light[block_start:first[2]])
        ant = _clean(book.light[block[-2][2]:last[2]])
        sp, ep = book.page_of_light(block_start), book.page_of_light(block_end - 1)
        confs = [page_conf.get(p, 100) for p in range(sp, ep + 1)]
        low = min(confs) < cfg["low_ocr_confidence"] if confs else False
        gaps.append(Gap(book.name, sp, ep, last[0],
                        "Yes" if _has_signature(ant, cfg["author_keywords"]) else "No",
                        title, aadi, ant, "Low - check scan" if low else "OK",
                        (block_start, block_end)))
    return gaps


def group_duplicates(gaps: list, threshold: float = 88) -> list:
    """Merge the same missing Kruti found in different books/editions into one row."""
    groups, keys = [], []
    for g in gaps:
        k = key_only(g.aadi)[:120] + "|" + key_only(g.ant)[-120:]
        match = process.extractOne(k, keys, scorer=fuzz.ratio, score_cutoff=threshold) if keys else None
        if match:
            groups[match[2]].also_in.append((g.book, g.start_page, g.end_page))
        else:
            groups.append(g)
            keys.append(k)
    for i, g in enumerate(groups, 1):
        g.temp_id = f"NEW-{i:04d}"
    return groups
