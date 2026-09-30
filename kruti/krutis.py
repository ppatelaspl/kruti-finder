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


# A heading candidate: a short phrase right after a number marker (16॥, ॥16॥) or at the
# start of a line, closed by heading punctuation.  "16॥ नेमनाथजीनी लावणी. ।"
_MARKER = re.compile(r"\d{1,3}\s*[।॥]")
_PHRASE = re.compile(r"\s*([^\n.,;:।॥]{3,60}?)\s*([.:।॥\n]|$)")
_HEAD_TRIM = " .:-।॥"


def _is_title(phrase: str, title_keys: list, name_keys: list, name_score: float,
              restart: bool = False) -> bool:
    """Structure alone is not enough: the phrase must also name a Kruti type
    (…लावणी, …स्तवन), match a Kruti name from the Excel (OCR variants tolerated), or be
    followed by verse numbers restarting at 1."""
    if len(phrase.split()) > 8 or not any(c.isalpha() for c in phrase):
        return False
    k = key_only(phrase)
    if len(k) < 3:
        return False
    if restart or any(k.endswith(t) for t in title_keys):
        return True
    return bool(name_keys) and process.extractOne(
        k, name_keys, scorer=fuzz.ratio, score_cutoff=name_score) is not None


def _find_heading(text: str, base: int, title_keys, name_keys, name_score, restart=False):
    """First heading in text (the stretch between two verse marks). Returns
    (start, end, title) in book offsets; end is just past the heading's punctuation."""
    starts = [0] + [m.end() for m in _MARKER.finditer(text)] + \
             [i + 1 for i, c in enumerate(text) if c == "\n"]
    for pos in sorted(set(starts)):
        m = _PHRASE.match(text, pos)
        if not m:
            continue
        phrase = re.sub(r"^[\d\s.]+", "", m.group(1)).strip(_HEAD_TRIM)   # "8569 लावणी"
        # a restart only vouches for a phrase closed by heading punctuation, not a bare line
        vouched = restart and m.group(2) in ".।"
        if _is_title(phrase, title_keys, name_keys, name_score, vouched):
            end = m.end()
            while end < len(text) and text[end] in " .:-।":   # "लावणी. ।"
                end += 1
            return base + pos + (len(m.group(0)) - len(m.group(0).lstrip())), base + end, phrase
    return None


def _verse_blocks(light: str, title_keys: list, name_keys: list, name_score: float):
    """Split the book at headings first, then at verse numbers restarting at 1.
    Each block: {"marks": [(n, start, end)], "heading": (start, end, title) or None}."""
    blocks, current, heading, prev_end = [], [], None, 0

    def close():
        nonlocal current, heading
        if current:
            blocks.append({"marks": current, "heading": heading})
        current, heading = [], None

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
        restart = n == 1 and bool(current) and current[-1][0] > 1
        head = _find_heading(light[prev_end:m.start()], prev_end, title_keys, name_keys,
                             name_score, restart)
        if head:
            close()                         # the heading ends the previous Kruti
            heading, n = head, 1
        elif current and n < current[-1][0] and n <= 2:
            close()
        prev_end = m.end()
        current.append((n, m.start(), m.end()))
    close()
    return blocks


def _clean(text: str) -> str:
    return " ".join(text.split())


def _first_line(text: str) -> str:
    """Aadi Vakya = the opening line: up to the first danda when that is a real line."""
    text = _clean(text).lstrip(_HEAD_TRIM + "0123456789")
    head = re.split(r"[।॥]", text, maxsplit=1)[0].strip()
    return head if len(head) >= 15 else text


def _letters(text: str) -> int:
    return len(re.sub(r"[\s\d।॥.,;:|()\[\]!?%^>“”\"'-]", "", text))


def _last_line(text: str) -> str:
    """Ant Vakya = the closing line: the text after the last danda before the final mark."""
    text = _clean(text)
    m = re.search(r"(.*?)\s*([।॥]\s*\S{0,3}\s*[।॥])\s*$", text)
    body, mark = (m.group(1), m.group(2)) if m else (text, "")
    tail = re.split(r"[।॥]", body)[-1].strip()
    return (tail + " " + mark).strip() if len(tail) >= 15 else text


def _split_title(opening: str):
    """Short heading lines before verse 1 (no dandas/commas) are the Kruti title."""
    lines = [ln.strip() for ln in opening.split("\n") if ln.strip()]
    title = []
    while len(lines) > 1 and len(lines[0]) <= 60 and not _VERSE_PUNCT.search(lines[0]):
        title.append(lines.pop(0))
    return _clean(" ".join(title)).strip(_HEAD_TRIM), _clean(" ".join(lines))


def find_krutis(book, page_conf: dict, cfg, names=()) -> list:
    """names: Kruti names from the Excel; a heading matching one starts a new Kruti."""
    found, prev_end = [], 0
    title_keys = [key_only(t) for t in cfg.get("title_keywords", []) if key_only(t)]
    name_keys = [k for k in (key_only(n) for n in names if n) if len(k) >= 3]
    for block in _verse_blocks(book.light, title_keys, name_keys, cfg["name_match_threshold"]):
        marks, heading = block["marks"], block["heading"]
        first, last = marks[0], marks[-1]
        if heading:                         # a detected heading fixes where the Kruti starts
            block_start, title = heading[0], heading[2]
            opening = book.light[heading[1]:first[2]]
        else:
            block_start = max(prev_end, first[1] - cfg["max_opening_chars"])
            while block_start < first[1] and book.light[block_start].isspace():
                block_start += 1
            title, opening = _split_title(book.light[block_start:first[2]])
        block_end = last[2]
        prev_end = block_end
        if len(marks) < cfg["min_verses"] and not heading:
            continue

        aadi, j = _first_line(opening), 0
        while _letters(aadi) < 5 and j + 1 < len(marks):   # opening held only numbers/marks
            aadi = _first_line(book.light[marks[j][2]:marks[j + 1][2]])
            j += 1
        # the last verse; step back when it is only a refrain cue ("॥ मत । ॥")
        opening_end = heading[1] if heading else block_start
        i = len(marks) - 2
        ant_from = marks[i][2] if i >= 0 else opening_end
        while i >= 0 and _letters(book.light[ant_from:last[1]]) < 15:
            i -= 1
            ant_from = marks[i][2] if i >= 0 else opening_end
        ant = _last_line(book.light[ant_from:last[2]])
        verses = last[0] if first[0] == 1 else len(marks)
        sp, ep = book.page_of_light(block_start), book.page_of_light(block_end - 1)
        confs = [page_conf.get(p, 100) for p in range(sp, ep + 1)]
        low = min(confs) < cfg["low_ocr_confidence"] if confs else False
        found.append(Kruti(book.name, sp, ep, verses, title, aadi, ant,
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
