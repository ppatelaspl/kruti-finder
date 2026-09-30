"""Split a book into Kruti.

Devotional Kruti are numbered verse by verse (॥1॥ ... ॥7॥). A run of verse numbers that
restarts at 1, or a heading naming a Kruti type (स्तवन, सज्झाय ...), marks a new Kruti.
Each one is recorded with its title, first verse (Aadi Vakya), last verse (Ant Vakya) and
pages. The same Kruti found in several books, places or scripts shares one group ID.
"""
import re
from dataclasses import dataclass

from rapidfuzz import fuzz, process

from .normalize import key_only

# ॥12॥ ; OCR often garbles the number (॥[॥, ॥l॥) - those are inferred from the sequence
_VERSE_MARK = re.compile(r"[।॥]\s*([\dIl|\[\]()!]{1,3}|\s?)\s*[।॥]")
_VERSE_PUNCT = re.compile(r"[।॥,;]")


@dataclass
class Kruti:
    book: str
    start_page: int
    end_page: int
    verses: int
    title: str
    aadi: str
    ant: str
    ocr_quality: str
    span: tuple
    script: str = ""             # Gujarati / Devanagari, as printed in the book
    book_name: str = ""
    kruti_no: object = None      # from the Excel when matched
    kruti_name: str = ""         # from the Excel when matched
    match: str = "New"           # Matched - same script / Matched - other script / New
    match_score: object = None   # weaker of the Aadi/Ant match %
    group_id: str = ""


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


def find_krutis(book, page_conf: dict, cfg) -> list:
    found, prev_end = [], 0
    title_keys = [key_only(t) for t in cfg.get("title_keywords", []) if key_only(t)]
    for block in _verse_blocks(book.light, title_keys):
        first, last = block[0], block[-1]
        block_start = max(prev_end, first[1] - cfg["max_opening_chars"])
        while block_start < first[1] and book.light[block_start].isspace():
            block_start += 1
        block_end = last[2]
        prev_end = block_end
        if len(block) < cfg["min_verses"]:
            continue

        title, aadi = _split_title(book.light[block_start:first[2]])
        ant = _clean(book.light[block[-2][2]:last[2]])
        sp, ep = book.page_of_light(block_start), book.page_of_light(block_end - 1)
        confs = [page_conf.get(p, 100) for p in range(sp, ep + 1)]
        low = min(confs) < cfg["low_ocr_confidence"] if confs else False
        found.append(Kruti(book.name, sp, ep, last[0], title, aadi, ant,
                           "Low - check scan" if low else "OK", (block_start, block_end)))
    return found


def assign_groups(krutis: list, threshold: float = 88) -> None:
    """One group ID per distinct Kruti. Rows matched to the same Excel Kruti share a group;
    other rows join the group whose Aadi+Ant text is most alike (scripts are unified)."""
    groups, keys, by_excel = [], [], {}
    for k in krutis:
        key = key_only(k.aadi)[:120] + "|" + key_only(k.ant)[-120:]
        if k.kruti_no is not None and k.kruti_no in by_excel:
            gid = by_excel[k.kruti_no]
        else:
            match = process.extractOne(key, keys, scorer=fuzz.ratio,
                                       score_cutoff=threshold) if keys else None
            if match:
                gid = groups[match[2]]
            else:
                gid = f"G-{len(set(groups)) + 1:04d}"
            if k.kruti_no is not None:
                by_excel[k.kruti_no] = gid
        groups.append(gid)
        keys.append(key)
        k.group_id = gid
