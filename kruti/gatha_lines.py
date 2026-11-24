"""Gatha Lines: decide what each line of a book is.

Every line read from the book (kruti/layout.py) gets one kind:
  verse      part of a gatha
  prose      preface, introduction, explanation (व्याख्या, अर्थ, भावार्थ …), biography
  heading    a Kruti's title
  part       a part heading inside a Kruti (ढाल, दुहा, कलश …)
  tune       tune / raga / metre / refrain-marker lines - never part of a gatha
  note       a source or editor's note in brackets
  list       index / contents entries
  furniture  running headers, footers, page numbers

The words alone were not enough (v1.0.10). The layout decides most cases: prose runs to
the full text width and wraps mid-sentence; a gatha's lines are shorter and end in
। ॥ , ; or a verse number. Every threshold is named in GATHA_DEFAULTS.
"""
import math
import re
import statistics
import unicodedata
from dataclasses import dataclass, field

from .config import merged
from .krutis import _Parts, _is_title, _part_heading, _plausible_title, verse_pattern
from .matcher import (_is_page_furniture, _page_number_candidates, _printed_page_numbers,
                      _running_lines)
from .normalize import gujarati_to_devanagari, key_only, light_normalize

KINDS = ("verse", "prose", "heading", "part", "tune", "note", "list", "furniture")

GATHA_DEFAULTS = {
    "layout_cache_dir": ".kruti_layout_cache",
    "prose_fill": 0.88,          # a line this share of the text width or wider can be prose
    "verse_fill_max": 0.8,       # gatha lines are usually narrower than this
    "prose_words": ["है", "हैं", "था", "थी", "थे", "थीं", "किया", "किये", "किए", "गया", "गई",
                    "गये", "गए", "करते", "करता", "करती", "होता", "होती", "होते", "जाता", "जाती",
                    "हुआ", "हुई", "हुए", "रहा", "रही", "रहे", "चाहिए", "इसलिए", "अर्थात्", "हतो",
                    "हती", "हता", "हतां", "करवामां", "करवानो", "करवानी", "आव्या", "थयो", "थयुं",
                    "थई", "कर्यो", "कर्युं", "गयो", "गयुं", "जोईए", "एटले", "तेमज", "छीए"],
    "explanation_openers": ["व्याख्या", "अर्थ", "भावार्थ", "बालावबोध", "टीका", "विवेचन",
                            "शब्दार्थ", "गाथार्थ", "अन्वय", "सारांश", "विशेषार्थ"],
    "tune_words": ["राग", "रागः", "देशी", "देशि", "तर्ज", "तर्जः", "चाल", "छन्द", "छंद", "छन्दः",
                   "छंदः", "ढाल", "ढाळ"],
    "refrain_words": ["आंकणी", "आंकणि", "आंकणीः", "टेक", "ध्रुवपद", "ध्रुव", "स्थायी"],
    "index_headings": ["अनुक्रमणिका", "अनुक्रम", "विषयानुक्रम", "विषयानुक्रमणिका", "विषय-सूची",
                       "विषयसूची", "सूची", "अनुक्रमणिका:"],
    "smooth_window": 2,
    "max_explanation_pages": 3,  # a longer prose run with no gatha after it ends the Kruti
    "gatha_gap": 0.8,            # an empty gap of this many line heights ends a gatha
    "long_gatha_lines": 8,
}

_DIGITS = str.maketrans("०१२३४५६७८९|", "0123456789।")
_END_VERSE = re.compile(r"[,;।॥!?)\]’”'\"]\s*$|[,;]\s*\S{0,3}\s*$")
_LEADER = re.compile(r"[.\-_…·]{4,}\s*\d{1,4}\s*$")
_ENDS_NUMBER = re.compile(r"(?<![।॥\d])\s\d{1,4}\s*$")
_BRACKETED = re.compile(r"^\s*[(\[{].*[)\]}][\s.।॥]*$")


def gatha_config(overrides: dict | None) -> dict:
    """Feature 1's settings (OCR, keywords) plus this feature's own."""
    cfg = merged(None)
    for k, v in GATHA_DEFAULTS.items():
        cfg[k] = list(v) if isinstance(v, list) else v
    for k, v in (overrides or {}).items():
        if v is not None:
            cfg[k] = v
    return cfg


@dataclass
class TLine:
    page: int
    text: str                 # as read, in the book's own script
    light: str                # light_normalize(text), for the rules
    kind: str
    conf: float
    source: str
    gap_above: float          # empty space above, in line heights (0 for a page's first line)
    indent: float             # start, as a share of the text width from the text's left edge
    fill: float               # width, as a share of the text width
    marks: list = field(default_factory=list)   # [(end offset in text, number or None)]


def mark_text(text: str) -> str:
    """Same length as text, with Gujarati letters and all digits made plain, so verse
    marks found in it can cut the original text at the same offsets."""
    return gujarati_to_devanagari(text).translate(_DIGITS)


def _number(m) -> int | None:
    for g in m.groups():
        if g is not None:
            g = g.strip()
            return int(g) if g.isdigit() else None
    return None


def _words(light: str) -> list:
    return [w.strip(".,;:!?।॥-–—()[]\"'“”‘’") for w in light.split()]


def _text_box(pages):
    """(left edge by page parity, text width) of the book's main text block: the width
    the widest lines of most pages reach."""
    spans, lefts = [], {0: [], 1: []}
    for p in pages:
        if len(p.lines) < 4:
            continue
        x0 = sorted(ln.x0 for ln in p.lines)[len(p.lines) // 10]
        x1 = sorted(ln.x1 for ln in p.lines)[-1 - len(p.lines) // 10]
        spans.append((x1 - x0, x0, p.page % 2))
    if not spans:
        return {}, 0
    width = sorted(s for s, _, _ in spans)[math.ceil(0.9 * (len(spans) - 1))]
    for s, x0, parity in spans:
        if s >= 0.9 * width:
            lefts[parity].append(x0)
    every = lefts[0] + lefts[1]
    left = {par: statistics.median(v or every or [0]) for par, v in lefts.items()}
    return left, width


def classify_book(pages: list, cfg: dict) -> tuple:
    """(TLines in reading order for the whole book, {PDF page: printed page})."""
    title_keys = [key_only(t) for t in cfg.get("title_keywords", []) if key_only(t)]
    section_keys = _Parts([key_only(t) for t in cfg.get("section_keywords", []) if key_only(t)],
                          [key_only(t) for t in cfg.get("part_ordinals", []) if key_only(t)],
                          title_keys)
    texts = {p.page: [unicodedata.normalize("NFC", ln.text) for ln in p.lines] for p in pages}
    lights = {p.page: [light_normalize(t) for t in texts[p.page]] for p in pages}
    repeated = _running_lines(["\n".join(v) for v in lights.values()], 0.2)
    seen = {pg: _page_number_candidates([t for t in v if t.strip()]) for pg, v in lights.items()}
    printed = _printed_page_numbers(seen)
    pattern = verse_pattern("\n".join(mark_text(t) for v in texts.values() for t in v), len(pages))
    left, width = _text_box(pages)

    out = []
    for p in pages:
        heights = [ln.y1 - ln.y0 for ln in p.lines if ln.y1 > ln.y0]
        lh = statistics.median(heights) if heights else 12
        n = len(p.lines)
        page_lines, prev = [], None
        for i, (ln, text, light) in enumerate(zip(p.lines, texts[p.page], lights[p.page])):
            gap = 0.0 if prev is None else max(0.0, (ln.y0 - prev.y1) / lh)
            # the line spacing itself is not a gap: measure only space beyond it
            prev = ln
            w = width or (p.width * 0.8)
            lx = left.get(p.page % 2, 0) if width else 0
            marks = [(m.end(), _number(m)) for m in pattern.finditer(mark_text(text))]
            t = TLine(p.page, text, light, "", ln.conf, p.source, gap,
                      (ln.x0 - lx) / w, (ln.x1 - ln.x0) / w, marks)
            if _is_page_furniture(light, repeated, edge=i < 2 or i >= n - 2):
                t.kind = "furniture"
            page_lines.append(t)
        _relative_gaps(page_lines)
        if _is_index_page(page_lines, cfg):
            for t in page_lines:
                if t.kind != "furniture":
                    t.kind = "list"
        out.extend(page_lines)

    _first_pass(out, cfg, title_keys, section_keys)
    _explanations(out, cfg)
    _smooth(out, cfg["smooth_window"])
    _continuations(out, cfg)
    _headings_need_verse(out)
    return out, printed


def _relative_gaps(lines):
    """Gaps relative to the page's usual line spacing: 0 = normal spacing."""
    gaps = sorted(t.gap_above for t in lines[1:] if t.kind != "furniture")
    if not gaps:
        return
    usual = gaps[len(gaps) // 2]
    for i, t in enumerate(lines):
        t.gap_above = 0.0 if i == 0 else max(0.0, t.gap_above - usual)


def _is_index_page(lines, cfg) -> bool:
    body = [t for t in lines if t.kind != "furniture" and t.light.strip()]
    if not body:
        return False
    heads = {key_only(h) for h in cfg["index_headings"]}
    if any(key_only(t.light) in heads for t in body[:3]):
        return True
    listed = sum(bool(_LEADER.search(t.light) or _ENDS_NUMBER.search(t.light)) and not t.marks
                 for t in body)
    return len(body) >= 5 and listed >= 0.5 * len(body)


def _ends_open(light: str) -> bool:
    """Ends mid-sentence (prose wraps); a gatha line ends in punctuation or a number."""
    s = light.rstrip()
    return bool(s) and not _END_VERSE.search(s) and not s[-1].isdigit()


def _is_tune(light: str, cfg) -> bool:
    words = [w for w in _words(re.sub(r"[-–—:]", " ", light)) if w]
    if not words:
        return False
    keys = {key_only(w) for w in cfg["tune_words"]}
    refrain = {key_only(w) for w in cfg["refrain_words"]}
    wk = [key_only(w) for w in words]
    if all(k in refrain or not k for k in wk):
        return True                                  # "आंकणी", "॥ टेक ॥"
    if len(words) > 10:
        return False
    if wk[0] in keys - {key_only("ढाल"), key_only("ढाळ")}:
        return True                                  # "राग - आशावरी", "तर्ज: …"
    if _BRACKETED.match(light) and any(k in keys or any(x in k for x in keys if len(x) >= 3)
                                       for k in wk):
        return True                                  # "( मालिनी-छन्दः )"
    return bool(re.search(r"[-–]\s*ए\s+देशी\W*$|देशी\W*$", light))  # "… -ए देशी"


def _prose_score(t: TLine, cfg) -> int:
    words = {key_only(w) for w in cfg["prose_words"]}
    hits = sum(key_only(w) in words for w in _words(t.light))
    score = min(hits, 3)
    if t.fill >= cfg["prose_fill"] and _ends_open(t.light):
        score += 2
    if t.fill >= cfg["prose_fill"]:
        score += 1
    return score


def _verse_score(t: TLine, cfg) -> int:
    score = 3 * bool(t.marks)
    s = t.light.rstrip()
    if s and s[-1] in ",;":
        score += 2
    elif s and s[-1] in "।॥":
        score += 1
    if t.fill <= cfg["verse_fill_max"]:
        score += 1
    return score


def _first_pass(lines, cfg, title_keys, section_keys):
    for t in lines:
        if t.kind:
            continue
        light = t.light.strip()
        if not light or not any(c.isalpha() for c in light):
            t.kind = "furniture"
        elif _part_heading(light.strip("।॥ ").strip(), section_keys) and not t.marks:
            t.kind = "part"
        elif _is_tune(light, cfg):
            t.kind = "tune"
        elif _BRACKETED.match(light) and not t.marks:
            t.kind = "note"
        elif _heading_shape(light, title_keys, t, cfg):
            t.kind = "heading"
        else:
            t.kind = "prose" if _prose_score(t, cfg) > _verse_score(t, cfg) else "verse"


_SERIAL_START = re.compile(r"^[\s।॥]*(\(\s*\S{1,3}\s*\)|\d{1,4}\s*[.)]|\d{1,4}\s)\s*")


def _heading_shape(light: str, title_keys, t: TLine, cfg) -> bool:
    """Short, no verse mark, no comma inside; a Kruti-type word, or a serial number
    before a plausible title ("8. श्री चन्द्रप्रभ जिन चैत्यवंदन")."""
    if t.marks or t.fill > cfg["verse_fill_max"]:
        return False
    serial = _SERIAL_START.match(light)
    phrase = light[serial.end():] if serial else light
    phrase = phrase.strip(" .:-–।॥\"'“”")
    phrase = re.sub(r"\s*\([^)]*\)?\s*$", "", phrase) or phrase
    if not phrase or "," in phrase or len(phrase.split()) > 8:
        return False
    if _is_title(phrase, title_keys, [], 85):
        return True
    return bool(serial) and _plausible_title(phrase) and len(phrase.split()) <= 6


def _explanations(lines, cfg):
    """A paragraph opened by व्याख्या-, अर्थ:, भावार्थ … is prose up to the next gatha
    (a line with a verse mark that is not inside a running paragraph) or heading."""
    openers = "|".join(re.escape(light_normalize(o)) for o in cfg["explanation_openers"])
    opener = re.compile(rf"^[\s(\[]*({openers})\s*[:\-–—ः]")
    inside = False
    for t in lines:
        if t.kind in ("heading", "part", "furniture", "list"):
            inside = t.kind == "furniture" and inside
            continue
        if opener.match(t.light):
            inside = True
            t.kind = "prose"
            continue
        if inside:
            if t.marks and t.fill <= cfg["verse_fill_max"] and t.kind == "verse":
                inside = False
            else:
                t.kind = "prose"


def _smooth(lines, window):
    """One odd line among the same kind on both sides takes their kind."""
    soft = ("verse", "prose")
    kinds = [t.kind for t in lines]
    for i, t in enumerate(lines):
        if t.kind not in soft:
            continue
        before = [k for k in kinds[max(0, i - window):i] if k != "furniture"]
        after = [k for k in kinds[i + 1:i + 1 + window] if k != "furniture"]
        if len(before) == window and len(after) == window:
            around = set(before + after)
            if len(around) == 1 and (k := around.pop()) in soft and k != t.kind and not (
                    k == "prose" and t.marks):
                t.kind = k


def _continuations(lines, cfg):
    """The line after a full-width prose line that wraps mid-sentence continues it -
    the short last line of a paragraph is prose too."""
    prev = None
    for t in lines:
        if t.kind == "furniture":
            continue
        if (prev is not None and prev.kind == "prose" and t.kind == "verse" and not t.marks
                and prev.fill >= cfg["prose_fill"] and _ends_open(prev.light)
                and t.page == prev.page and t.gap_above < 0.5
                and not t.light.rstrip().endswith((",", ";"))):
            t.kind = "prose"
        prev = t


def _headings_need_verse(lines):
    """A heading-shaped line inside prose ("कृतित्व") is a section title of the preface,
    not a Kruti title: a heading must be followed by gathas before the next prose."""
    for i, t in enumerate(lines):
        if t.kind != "heading":
            continue
        nxt = next((u.kind for u in lines[i + 1:i + 8]
                    if u.kind not in ("furniture", "tune", "note", "part")), None)
        if nxt == "prose":
            t.kind = "prose"
