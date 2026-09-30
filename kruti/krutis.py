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

# How a verse ends differs from book to book. OCR often garbles the number (॥[॥, ...र...);
# a garbled one is inferred from the sequence.
_STYLES = {
    "danda": r"[।॥]\s*([\dIl|\[\]()!]{1,3}|\s?)\s*[।॥]",          # ॥12॥  । 3 ।
    "dots": r"\.{2,}\s*([^\s.]{0,2})\s*\.*[ \t]*(?=\n|$)",        # ...1...  ...2  ...
    "num_stop": r"(?<=[\s,;])(\d{1,3})\.(?=\s)",                 # श्रीठ 15. एकवरस
    "line_num": r"(?<=\S[ \t])(\d{1,3})[ \t]*(?=\n|$)",          # रूडा0 धन्य0 11⏎
}
_ALWAYS = ("danda", "dots")


def _sequential(nums) -> float:
    """Share of numbers that continue the previous one (or restart at 1)."""
    hits = sum(1 for a, b in zip(nums, nums[1:]) if b == a + 1 or b == 1)
    return hits / max(1, len(nums) - 1)


def verse_pattern(light: str, pages: int = 1):
    """The verse-end styles this book uses. The bare-number styles would also catch stray
    numbers, so they are used only where the book numbers verses that way throughout:
    often, and mostly in sequence."""
    use = list(_ALWAYS)
    for name in ("num_stop", "line_num"):
        nums = [int(m.group(1)) for m in re.finditer(_STYLES[name], light)]
        if len(nums) >= max(8, pages) and _sequential(nums) >= 0.4:
            use.append(name)
    return re.compile("|".join(_STYLES[n] for n in use))


_VERSE_MARK = verse_pattern("")
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
    checks: list                 # reasons a reviewer should look at this row (empty = OK)
    span: tuple
    book_start: object = None    # page numbers printed in the book
    book_end: object = None
    script: str = ""             # Gujarati / Devanagari, as printed in the book
    book_name: str = ""
    kruti_no: object = None      # from the Excel when matched
    kruti_name: str = ""         # from the Excel when matched
    match: str = "New"           # Matched - same script / Matched - other script / New
    match_score: object = None   # weaker of the Aadi/Ant match %
    group_no: int = 0            # same number = same Kruti (other books, places, scripts)


# A heading candidate: a short phrase right after a number marker (16॥, ॥16॥) or at the
# start of a line, closed by heading punctuation.  "16॥ नेमनाथजीनी लावणी. ।"
_MARKER = re.compile(r"\d{1,3}\s*[।॥]")
# (an optional book serial first: "173. सुनंदा रूपसेननी सज्झाय")
_PHRASE = re.compile(r"[\s।॥|'\"“]*(\(\s*[^\s()]{1,3}\s*\)\s*|\d{1,4}\s*[.)]\s+|\d{1,4}\s+(?=[^\d\s]))?"
                     r"([^\n.,;:।॥]{3,60}?)\s*([.:।॥\n]|$)")
_HEAD_TRIM = " .:-।॥\"'“”"
_SERIAL = re.compile(r"\s*[\[(]\s*[^\s\[\]()]{1,3}\s*[\])]?\s*$")          # "नु [8]" inside the phrase
_SERIAL_REST = re.compile(r"\s*[।॥|\[(]?\s*[^\s\[\]()]{1,3}\s*[\])]\s*")  # "नु । 12]" after it


def _ends_with_type(key: str, type_key: str) -> bool:
    """…लावणी, tolerating one OCR slip in longer type words (लावणुं)."""
    if key.endswith(type_key):
        return True
    n = len(type_key)
    return n >= 4 and len(key) >= n and max(
        fuzz.ratio(key[-w:], type_key) for w in (n, n + 1)) >= 70


def _plausible_title(phrase: str) -> bool:
    """Not OCR junk ("द्वरिझे 939 ल्दिझे 9798") or a stray verse fragment ("जये")."""
    chars = [c for c in phrase if not c.isspace()]
    letters = _letters(phrase)
    return (letters >= 5 and letters >= 0.8 * len(chars)
            and not re.search(r"\d{3,}", phrase) and len(key_only(phrase)) >= 4)


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
    if any(_ends_with_type(k, t) for t in title_keys):
        return True
    if restart:                  # vouched by structure alone: it must also look like words
        return _plausible_title(phrase)
    words = phrase.split()                   # "पद बारमुं", "स्तवन 5": type word first
    if len(words) <= 4 and key_only(words[0]) in title_keys:
        return True
    return bool(name_keys) and process.extractOne(
        k, name_keys, scorer=fuzz.ratio, score_cutoff=name_score) is not None


def _find_heading(text: str, base: int, title_keys, name_keys, name_score, restart=False):
    """First heading in text (the stretch between two verse marks). Returns
    (start, end, title) in book offsets; end is just past the heading's punctuation."""
    starts = [0] + [m.end() for m in _MARKER.finditer(text)] + \
             [i + 1 for i, c in enumerate(text) if c == "\n"]
    colophon = None          # "इति … स्तवनं समाप्तम् ॥" closes a Kruti: the next one follows
    for pos in sorted(set(starts)):
        if pos == 0 or text[pos - 1] == "\n":
            eol = text.find("\n", pos)
            line = text[pos:len(text) if eol < 0 else eol]
            if colophon is None and re.match(r"[\s।॥|]*इति\s", line):
                colophon = (base + pos, base + pos + len(line))
                continue
            # "(च)", "(क)": a letter serial alone on its line; "(राग - …)": a tune line.
            # Both open a new Kruti even when no title is printed.
            if re.fullmatch(r"\s*\(\s*[^\s()\d]{1,2}\s*\)\s*", line) or \
                    re.match(r"\s*\(?\s*राग\s*[:\-–]", line):
                return base + pos, base + pos + len(line), ""
            # "लावणी," - a Kruti-type word alone on its line, closed by a comma
            only = re.fullmatch(r"[\s।॥|]*(\S+?)\s*,\s*", line)
            if only and key_only(only.group(1)) in title_keys:
                return base + pos, base + pos + len(line), only.group(1)
        m = _PHRASE.match(text, pos)
        if not m or text.startswith("..", m.start(3)):   # "…रयण भंडार... 1..." is a verse
            continue
        if m.group(3) == "." and re.search(r"\d\s*$", m.group(2)):
            continue                          # "…विचार जी 1.": a verse number, not a heading
        phrase = re.sub(r"^[\d\s.]+", "", m.group(2))                      # "8569 लावणी"
        # "सुपाश्वेनाथ नु [7]": a line holding only a name and a bracketed serial number
        # (often OCR-garbled: [छ], । 12]) is as strong a sign as verses restarting at 1
        line_end = text.find("\n", m.start(2))
        line_end = len(text) if line_end < 0 else line_end
        serial = _SERIAL.search(phrase)
        if serial:
            phrase = phrase[:serial.start()]
        rest = text[m.start(2) + len(m.group(2)):line_end]
        bracketed = bool(serial) and not rest.strip() or bool(_SERIAL_REST.fullmatch(rest))
        phrase = phrase.strip(_HEAD_TRIM)
        atha = re.match(r"अथ\s+(.{3,})", phrase)   # "॥ अथ गुण विषे दोहा ॥": a text begins
        if atha:
            phrase = atha.group(1).strip(_HEAD_TRIM)
        # a restart only vouches for a phrase closed by heading punctuation, not a bare line
        # "294. वैराग्यनी साय" / "(१) अभिनंदन जिन सवत.": a short phrase after the book's
        # serial number, alone on its line, is a heading even when OCR garbled its type word
        at_line_start = pos == 0 or text[pos - 1] == "\n"
        numbered = (bool(m.group(1)) and len(phrase.split()) <= 6 and m.group(3) in ".:।\n"
                    and (at_line_start or not m.group(1).strip()[-1:].isdigit()))
        # when verses restart at 1, the title may stand alone on its line with no heading
        # punctuation ("…सगुढ 6⏎वैराग्यनी साय⏎सार नहि रे…"): short, no comma
        lone = (m.group(3) == "\n" and len(phrase) <= 45 and len(phrase.split()) <= 6
                and not re.search(r"[,;]", text[m.start(2):line_end]))
        vouched = bracketed or numbered or bool(atha) or (
            restart and (m.group(3) in ".।" or lone))
        core = re.sub(r"\s*\([^)]*\)?\s*$", "", phrase)   # "…सज्झाय (ढाळ-2)": note on parts
        if _is_title(core or phrase, title_keys, name_keys, name_score, vouched):
            end = line_end if bracketed else m.end()
            while end < len(text) and text[end] in " .:-।":   # "लावणी. ।"
                end += 1
            start = base + pos + (len(m.group(0)) - len(m.group(0).lstrip()))
            return (colophon[0] if colophon else start), base + end, phrase
    return (colophon[0], colophon[1], "") if colophon else None


_PART_LINE = 80      # "ढाल तेरहवीं - नारायणकी देशी …": a part heading may carry its tune


class _Parts(list):
    """Part words (keys) plus ordinals ("बीजी", "तीसरी") that identify part headings."""

    def __init__(self, keys, ordinals=(), kruti_words=()):
        super().__init__(keys)
        self.ordinals = list(ordinals)
        self.kruti_words = set(kruti_words)   # "पद बारमुं" is the 12th पद: a Kruti


def _ordinal(word: str, ordinals) -> bool:
    """"बीजी", or an OCR slip of the same length ("खीजी"); "परम" is not "प्रथम"."""
    k = key_only(word)
    return len(k) >= 3 and any(len(o) == len(k) and fuzz.ratio(k, o) >= 75 for o in ordinals)


def _part_heading(piece: str, section_keys) -> bool:
    """"ढाळ ४", "॥ हाल त्रीनी ॥", "डुहाः-", "ढाल तेरहवीं -नारायणकी देशी": a part word first,
    on a heading-shaped piece - short, or with a colon/dash/tune note. A verse that just
    starts with such a word ("हाल बेहाल थयो जीवडो, …") is not one."""
    piece = piece.strip()
    words = [w for w in re.split(r"[\s:\-–ः]+", piece) if w]
    if not words or len(piece) > _PART_LINE:
        return False
    first = key_only(words[0])
    if (len(words) >= 2 and len(piece) <= 40 and len(first) <= 3 and "," not in piece
            and first not in getattr(section_keys, "kruti_words", ())
            and _ordinal(words[1], getattr(section_keys, "ordinals", ()))):
        return True                          # "हाश खीजीः-", "हार त्रीजी": OCR'd "ढाल बीजी"
    if key_only(words[0]) not in section_keys:
        return False
    return len(words) <= 4 or bool(re.search(r"[:\-–ः]|देशी|राग", piece))


def _section_break(text: str, section_keys: list) -> bool:
    """A part heading inside one Kruti, on its own line or between dandas. Verse numbers
    restart after it, yet the Kruti goes on."""
    return any(_part_heading(p, section_keys) for p in re.split(r"[\n।॥]", text))


def _without_part_headings(body: str, section_keys) -> str:
    """Aadi/Ant must not include "ढाळ १:" lines; a heading sharing its line with the first
    verse ("डुहाः-इयादिक अनेक छे, …") loses only the heading word."""
    out = []
    for ln in body.split("\n"):
        head = re.split(r"[\n।॥]", ln)[0]
        if _part_heading(head, section_keys):
            words = [w for w in re.split(r"[\s:\-–ः]+", head) if w]
            if len(words) <= 4 and not re.search(r",", ln):
                continue                      # a heading line of its own
            ln = re.sub(r"^\s*\S+?[\s:\-–ः]+", "", ln, count=1)
        out.append(ln)
    return "\n".join(out)


def _verse_blocks(light: str, title_keys: list, name_keys: list, name_score: float,
                  pattern=_VERSE_MARK, section_keys=()):
    """Split the book at headings first, then at verse numbers restarting at 1.
    Each block: {"marks": [(n, start, end)], "heading": (start, end, title) or None}."""
    blocks, current, heading, prev_end = [], [], None, 0
    section_open = False

    def close():
        nonlocal current, heading
        if current:
            blocks.append({"marks": current, "heading": heading})
        current, heading = [], None

    for m in pattern.finditer(light):
        raw = next((g for g in m.groups() if g is not None), "").strip()
        if raw.isdigit():
            n = int(raw)
        elif current:
            n = current[-1][0] + 1          # unreadable number: assume next verse
        else:
            n = 1
        if n == 0:                          # OCR misread; keep the sequence going
            n = current[-1][0] + 1 if current else 1
        restart = n == 1 and bool(current) and current[-1][0] > 1
        segment = light[prev_end:m.start()]
        before = re.split(r"[\n।॥]", segment)[-1]     # words just before this number
        # "ढाळ ४" / "दुहा" / "कलश": a part of the same Kruti, whose verses restart at 1
        own_part = bool(current) and bool(section_keys) and _section_break(before, section_keys)
        in_part = own_part or (bool(current) and bool(section_keys) and (
            section_open or _section_break(segment, section_keys)))
        # a Kruti heading still wins ("172. …सज्झाय" followed by "ढाळ १"); inside a part a
        # restart alone does not vouch for a heading (it would take refrains for titles)
        head = _find_heading(segment, prev_end, title_keys, name_keys, name_score,
                             restart and not in_part)
        if head and head[2] and section_keys and _part_heading(head[2], section_keys):
            head = None                      # "हार त्रीजी ड--कळावती" is a part, not a Kruti
        if head:
            close()                         # the heading ends the previous Kruti
            heading, n, section_open = head, 1, own_part
            if own_part:                    # the number belongs to "ढाळ १", not a verse
                prev_end = m.end()
                continue
        elif own_part:
            prev_end, section_open = m.end(), True
            continue
        elif in_part:
            section_open = False
            if not raw.isdigit():            # "ढाळ प" (OCR): the new part starts at verse 1
                n = 1
        elif current and n < current[-1][0] and n <= 2:
            close()
        prev_end = m.end()
        current.append((n, m.start(), m.end()))
    close()
    return blocks


def _clean(text: str) -> str:
    return " ".join(text.split())


def _verse_count(marks) -> int:
    """Verses in the Kruti: in each part (numbering restarts at every dhal/doha), the
    highest verse number that fits the sequence. Books print a running Kruti number after
    the last verse (॥ 6॥ ॥98॥) and OCR invents numbers (॥ 020 ॥); neither counts."""
    runs, run = [], []
    for n, _s, _e in marks:
        if run and (n == 1 or (n == 2 and run[-1] > 2)):
            runs.append(run)
            run = []
        run.append(n)
    runs.append(run)
    total = 0
    for run in runs:
        fitting = [n for i, n in enumerate(run) if n <= i + 4]
        total += max(fitting) if fitting else len(run)
    return total


_LETTER = re.compile(r"[\u0900-\u0963\u0970-\u097F\u0A80-\u0AE5\u0AF0-\u0AFFA-Za-z]")


def _letters(text: str) -> int:
    """Devanagari/Gujarati letters and signs (and Latin); not digits, dandas or symbols -
    a decorative rule "~-~--~---" has none."""
    return len(_LETTER.findall(text))


# A sentence ends at a danda, ! ?, an ellipsis, or a full stop closing a line.
_SENTENCE_END = re.compile(r"[।॥!?]+|\.{2,}|\.(?=[ \t]*(?:\n|$))")
_LONG_SENTENCE = 160


_VAKYA_TRIM = _HEAD_TRIM + "0123456789,;()[]"


def _sentences(text: str, raw: bool = False) -> list:
    """The Kruti's sentences, dropping refrain cues and verse numbers (under 8 letters).
    raw=True keeps each sentence's line breaks."""
    text = "\n".join(ln for ln in text.split("\n") if _letters(ln))   # rules, ornaments
    out = []
    for piece in _SENTENCE_END.split(text):
        clean = _clean(piece).strip(_VAKYA_TRIM)
        if _letters(clean) >= 8:
            out.append(piece if raw else clean)
    return out


def _vakya(sentence: str, first: bool) -> str:
    """Aadi/Ant Vakya from the first/last sentence. Many books punctuate only at the verse
    end, so a "sentence" can be a whole multi-line verse; then its first/last line is used."""
    clean = _clean(sentence).strip(_VAKYA_TRIM)
    if len(clean) <= _LONG_SENTENCE:
        return clean
    lines = [_clean(ln).strip(_VAKYA_TRIM) for ln in sentence.split("\n")]
    lines = [ln for ln in lines if _letters(ln) >= 8]
    if len(lines) > 1:
        return lines[0] if first else lines[-1]
    return clean


def _short(sentence: str) -> str:
    if len(sentence) <= _LONG_SENTENCE:
        return sentence
    return sentence[:_LONG_SENTENCE].rsplit(" ", 1)[0] + " …"


def _not_a_kruti(body, sents, marks, heading, light) -> bool:
    """Book text that is not a Kruti and is left out: index/contents lists, and prose
    (preface, explanations) - no heading, under 2 numbered verses, long sentences."""
    if _looks_like_list(body):
        return True
    numbered = sum(1 for _n, s, e in marks if re.search(r"\d", light[s:e]))
    long_sentences = bool(sents) and sum(map(len, sents)) / len(sents) > 120
    return not heading and numbered < 2 and long_sentences


def _looks_like_list(text: str) -> bool:
    """Index / contents / list pages: many page or serial numbers between few words."""
    numbers = re.findall(r"\b\d{1,4}\b", text)
    return len(numbers) >= 6 and len(numbers) / max(1, _letters(text)) > 0.1


def _split_title(opening: str, title_keys=(), name_keys=(), name_score=85):
    """Short heading lines before verse 1 are the Kruti title - but only when they look like
    one (a Kruti-type word, an Excel name, or closed by a full stop): OCR often drops the
    commas of a verse line, so shortness alone would make verse lines into titles."""
    lines = [ln.strip() for ln in opening.split("\n") if ln.strip()]
    title = []
    while len(lines) > 1 and len(lines[0]) <= 60 and not _VERSE_PUNCT.search(lines[0]):
        line = re.sub(r"^\d{1,4}\s*[.)]\s*", "", lines[0])
        core = re.sub(r"\s*\([^)]*\)?\s*$", "", line).strip(_HEAD_TRIM)
        looks = _is_title(core, list(title_keys), list(name_keys), name_score) or \
            bool(re.search(r"[^.]\.\s*$", line))
        if not looks:
            break
        title.append(lines.pop(0))
    title = re.sub(r"^\d{1,4}\s*[.)]\s*", "", _clean(" ".join(title)))   # "172. …"
    return title.strip(_HEAD_TRIM), "\n".join(lines)     # keep lines: sentences need them


def find_krutis(book, page_conf: dict, cfg, names=()) -> list:
    """names: Kruti names from the Excel; a heading matching one starts a new Kruti."""
    found, prev_end = [], 0
    title_keys = [key_only(t) for t in cfg.get("title_keywords", []) if key_only(t)]
    section_keys = _Parts([key_only(t) for t in cfg.get("section_keywords", []) if key_only(t)],
                          [key_only(t) for t in cfg.get("part_ordinals", []) if key_only(t)],
                          title_keys)
    name_keys = [k for k in (key_only(n) for n in names if n) if len(k) >= 3]
    pattern = verse_pattern(book.light, len(book.page_numbers))
    for block in _verse_blocks(book.light, title_keys, name_keys, cfg["name_match_threshold"],
                               pattern, section_keys):
        marks, heading = block["marks"], block["heading"]
        first, last = marks[0], marks[-1]
        if heading:                         # a detected heading fixes where the Kruti starts
            block_start, title = heading[0], heading[2]
            opening = book.light[heading[1]:first[2]]
        else:
            block_start = max(prev_end, first[1] - cfg["max_opening_chars"])
            while block_start < first[1] and book.light[block_start].isspace():
                block_start += 1
            title, opening = _split_title(book.light[block_start:first[2]], title_keys,
                                          name_keys, cfg["name_match_threshold"])
        block_end = last[2]
        prev_end = block_end
        if len(marks) < cfg["min_verses"] and not heading:
            continue

        body = opening + book.light[first[2]:block_end]      # the Kruti's text after its title
        body = _without_part_headings(body, section_keys)
        sents = _sentences(body, raw=True)
        if not sents:
            continue                         # no text of its own (a colophon between marks)
        aadi_full = _vakya(sents[0], True) if sents else ""
        ant_full = _vakya(sents[-1], False) if sents else ""
        aadi, ant = _short(aadi_full), _short(ant_full)
        verses = _verse_count(marks)
        sp, ep = book.page_of_light(block_start), book.page_of_light(block_end - 1)
        confs = [page_conf.get(p, 100) for p in range(sp, ep + 1)]
        checks = []
        if not title:
            checks.append("No heading found - check where it starts")
        if not sents or max(len(aadi_full), len(ant_full)) > _LONG_SENTENCE:
            checks.append("Aadi/Ant is not one clear sentence")
        if _not_a_kruti(body, sents, marks, heading, book.light):
            continue                         # index/contents or preface/explanation prose
        if ep - sp + 1 > cfg["max_kruti_pages_check"]:
            checks.append(f"Spans {ep - sp + 1} pages - may hold several Kruti")
        if confs and min(confs) < cfg["low_ocr_confidence"]:
            checks.append("Low OCR quality - check the scan")
        found.append(Kruti(book.name, sp, ep, verses, title, aadi, ant, checks,
                           (block_start, block_end), book.printed_page(sp),
                           book.printed_page(ep)))
    return found


def assign_groups(krutis: list, threshold: float = 88) -> None:
    """One group number per distinct Kruti, numbered 1, 2, 3 ... in order of first
    appearance. Rows matched to the same Excel Kruti share a group; other rows join the
    group whose Aadi+Ant text is most alike (scripts are unified)."""
    groups, keys, by_excel = [], [], {}
    for k in krutis:
        key = key_only(k.aadi)[:120] + "|" + key_only(k.ant)[-120:]
        if k.kruti_no is not None and k.kruti_no in by_excel:
            gid = by_excel[k.kruti_no]
        elif len(key) < 12:                  # no text to compare: a group of its own
            gid = len(set(groups)) + 1
        else:
            match = process.extractOne(key, keys, scorer=fuzz.ratio,
                                       score_cutoff=threshold) if keys else None
            if match:
                gid = groups[match[2]]
            else:
                gid = len(set(groups)) + 1
            if k.kruti_no is not None:
                by_excel[k.kruti_no] = gid
        groups.append(gid)
        keys.append(key)
        k.group_no = gid
