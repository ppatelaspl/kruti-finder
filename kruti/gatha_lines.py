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
from rapidfuzz import fuzz

from .krutis import _STYLES, _Parts, _is_title, _part_heading, _plausible_title, verse_pattern
from .matcher import (_furniture_key, _is_page_furniture, _page_number_candidates, _printed_page_numbers,
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
                            "शब्दार्थ", "गाथार्थ", "अन्वय", "सारांश", "विशेषार्थ",
                            "अये", "अय", "अप", "अर्थः"],     # OCR readings of अर्थ--
    "tune_words": ["राग", "रागः", "देशी", "देशि", "तर्ज", "तर्जः", "चाल", "छन्द", "छंद", "छन्दः",
                   "छंदः", "ढाल", "ढाळ"],
    "refrain_words": ["आंकणी", "आंकणि", "आंकणीः", "टेक", "ध्रुवपद", "ध्रुव", "स्थायी"],
    "index_headings": ["अनुक्रमणिका", "अनुक्रम", "विषयानुक्रम", "विषयानुक्रमणिका", "विषय-सूची",
                       "विषयसूची", "सूची", "अनुक्रमणिका:"],
    "smooth_window": 2,
    "note_words": ["कोश", "क्रमांक", "क्रमाक", "ग्रंथांक", "पाठांतर", "पाठान्तर", "पाठभेद"],
    "junk_conf": 55,             # OCR confidence below which a line without verse
                                 # punctuation is a border/ornament read as letters
    "max_explanation_pages": 3,  # a longer prose run with no gatha after it ends the Kruti
    "gatha_gap": 0.8,            # an empty gap of this many line heights ends a gatha
    "long_gatha_lines": 8,
    "max_quote_gathas": 6,       # a Kruti this short, without heading, inside prose: a quote
    "min_verse_like": 0.35,       # share of an unnumbered block's lines that must end like verse
}

_DIGITS = str.maketrans("०१२३४५६७८९|", "0123456789।")
_END_VERSE = re.compile(r"[.,;।॥!?)\]’”'\"]\s*$|[,;]\s*\S{0,3}\s*$")
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


# "॥श्रीजिन०३॥": a refrain cue abbreviated with ० (a zero) before the verse number
_REFRAIN_MARK = re.compile(r"[।॥]\s*[^\s\d।॥][^\d।॥]{0,15}?[0.]\s*(\d{1,3})\s*(?:[।॥]+|(?=\s*$))")


# books numbering verses at the line end: "… મારગ૦ ૪." and OCR's letters for digits (છ = ૭)
_END_NUMBER_DOT = re.compile(r"(?:(?<=\S\s)|(?<=\s\.))(\d{1,3})\s*\.?\s*$")
_END_GARBLED = re.compile(r"0\s+[रपछ]\s*\.?\s*$")


_AFTER_STOP_NUMBER = re.compile(r"[^\s\d.।॥;][.।॥;]\s*(\d{1,3})\s*\.?\s*$")
_FOOTNOTES = re.compile(r"(?:^|\s)\d{1,2}\.\s*[^\s\d]")
_NUM_DANDA = re.compile(r"(?:(?<=\s)|^)(\d{1,3})\s*[।॥]+")      # "४।।": ॥४॥ missing its first ॥
_DANDA_NUM = re.compile(r"[।॥]+\s*(\d{1,3})\s*[।॥]+")              # "।।३॥": a number in doubled dandas


def _marks(pattern, text: str) -> list:
    """[(end offset, number or None)] of every verse mark in a line."""
    mt = mark_text(text)
    found = {m.end(): _number(m) for m in pattern.finditer(mt)}
    for m in list(_DANDA_NUM.finditer(mt)) + list(_NUM_DANDA.finditer(mt)):
        inside = [e for e in found if m.start() < e <= m.end()]
        if all(found[e] is None for e in inside):
            for e in inside:
                del found[e]
            found[m.end()] = int(m.group(1))
    if not found:                         # "… डांग. २": a number right after a sentence end
        m = _AFTER_STOP_NUMBER.search(mt)
        if m:
            found[m.end()] = int(m.group(1))
    if _STYLES["line_num"] in pattern.pattern and not found:
        m = _END_NUMBER_DOT.search(mt)
        if m:
            found[m.end()] = int(m.group(1))
        elif _END_GARBLED.search(mt):
            found[len(mt.rstrip())] = None
    for m in _REFRAIN_MARK.finditer(mt):
        if not any(m.start() <= e <= m.end() for e in found):
            found[m.end()] = int(m.group(1))
    marks = [(e, None if n == 0 else n) for e, n in sorted(found.items())]   # ०० is a cue
    # "॥ ३१० ॥ ૧ ॥": a refrain cue read as a number right before the verse number
    keep = []
    for e, n in marks:
        if keep and n is not None and keep[-1][1] is not None and e - keep[-1][0] <= 6 \
                and not re.search(r"[^\W\d_]", re.sub(r"[।॥\d\s]", "", mt[keep[-1][0]:e])):
            keep.pop()
        keep.append((e, n))
    return keep


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

    edge_furniture = _running_edges(lights, title_keys)
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
            marks = _marks(pattern, text)
            t = TLine(p.page, text, light, "", ln.conf, p.source, gap,
                      (ln.x0 - lx) / w, (ln.x1 - ln.x0) / w, marks)
            if _SERIAL_ONLY.match(light) and 0 < i < n - 1 and not marks:
                t.kind = "heading"               # "(२)", "[२३]" inside the page: a Kruti serial
            elif _is_page_furniture(light, repeated, edge=i < 2 or i >= n - 2) or (
                    (p.page, i) in edge_furniture):
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
    _boundary_headings(out, title_keys)
    _headings_need_verse(out)
    return out, printed


def _running_edges(lights: dict, title_keys=()) -> set:
    """(page, line index) of a page's first or last line when it resembles the first or
    last line of other pages: a running header or footer, which OCR reads a little
    differently on every page (મહેદધિ / મહોદધિ)."""
    cands = {}
    for pg, ls in lights.items():
        idx = [i for i, t in enumerate(ls) if t.strip()]
        for i in idx[:1] + idx[-1:]:
            key = _furniture_key(ls[i])
            title = re.sub(r"^[\s\d.()\[\]]+", "", ls[i]).strip(" .।॥")
            if (len(key) >= 6 and len(re.findall(r"[,;]", ls[i])) < 2
                    and not _is_title(title, title_keys, [], 85)):   # a Kruti's own heading
                cands[(pg, i)] = key
    found = set()
    for (pg, i), key in cands.items():
        alike = sum(1 for (pg2, _), k2 in cands.items() if pg2 != pg and fuzz.ratio(key, k2) >= 70)
        if alike >= min(2, max(1, len(lights) - 1)):
            found.add((pg, i))
    return found


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


_REFRAIN_CUE = re.compile(r"[^\W\d_][^\s]*0\W*$")     # "મનડુ'૦", "ધન્ય૦": a refrain cue
# "… રે", "… जो": a gatha line's closing particle; "….ભાખ્યા.": a refrain after dots
_PARTICLE_END = re.compile(r"(?:^|\s)(?:रे|रे़|रै|जी|जो|हो|लाल|राज)\W*$")
REFRAIN_AFTER_DOTS = re.compile(r"(?:\.{3,}|…)\s*[^\W\d_]")


def _core(light: str) -> str:
    """The line without trailing OCR debris (`, ~, "5) after its last word."""
    words = light.split()
    while len(words) > 1 and (
            (not any(c.isalpha() for c in words[-1]) and not any(c in ",;।॥" for c in words[-1]))
            or (sum(c.isalpha() for c in words[-1]) <= 1 and _REFRAIN_CUE.search(words[-2]))):
        words.pop()                     # "… મારગ૦ છ": a verse number OCR'd as a letter
    return " ".join(words)


def _ends_open(light: str) -> bool:
    """Ends mid-sentence (prose wraps); a gatha line ends in punctuation or a number."""
    s = _core(light).rstrip()
    return bool(s) and not _END_VERSE.search(s) and not s[-1].isdigit()


def _is_tune(light: str, cfg) -> bool:
    words = [w for w in _words(re.sub(r"[-–—:]", " ", light)) if w]
    if not words:
        return False
    keys = {key_only(w) for w in cfg["tune_words"]}
    refrain = {key_only(w) for w in cfg["refrain_words"]}
    wk = [key_only(w) for w in words]
    if any(wk) and all(k in refrain or not k for k in wk):
        return True                                  # "आंकणी", "॥ टेक ॥"
    if len(words) > 10:
        return False
    if wk[0] in keys - {key_only("ढाल"), key_only("ढाळ")} and (
            len(words) <= 4 or re.search(r"[:\-–(]", light)) and not REFRAIN_AFTER_DOTS.search(light):
        return True                                  # "राग - आशावरी", "तर्ज: …"
    if _BRACKETED.match(light) and any(k in keys or any(x in k for x in keys if len(x) >= 3)
                                       for k in wk):
        return True                                  # "( मालिनी-छन्दः )"
    return bool(re.search(r"[-–]\s*ए\s+देशी\W*$|देशी\W*$", light))  # "… -ए देशी"


def _is_note(light: str, cfg) -> bool:
    """"खरतरगच्छ साहित्य कोश क्रमांक- 2592", "पाठभेद 1. …": a source or variant note;
    "१. विनति. २. कामदेव …": footnotes glossing words of the verses above."""
    keys = {key_only(w) for w in cfg["note_words"]}
    words = _words(re.sub(r"[-–—:]", " ", light))
    if len(words) <= 10 and any(key_only(w) in keys for w in words):
        return True
    return len(_FOOTNOTES.findall(light)) >= 2 and not re.search(r"[,;]", light)


def _debris(light: str, conf: float, cfg) -> bool:
    """Mostly one-letter fragments and digits (a decorative frame, a framed serial
    number), or a low-confidence line without verse punctuation."""
    tokens = light.split()
    short = sum(sum(c.isalpha() for c in w) <= 1 for w in tokens) / max(1, len(tokens))
    if len(tokens) >= 2 and short >= 0.75:
        return True
    return conf < cfg["junk_conf"] and (short >= 0.5 or not re.search(r"[,;]", light))


def _prose_score(t: TLine, cfg) -> int:
    words = {key_only(w) for w in cfg["prose_words"]}
    score = min(sum(key_only(w) in words for w in _words(t.light)), 3)
    if t.fill >= cfg["prose_fill"] and _ends_open(t.light) and not _PARTICLE_END.search(t.light):
        score += 2                      # full width, broken mid-sentence: wrapped prose
    return score


def _verse_score(t: TLine, cfg) -> int:
    score = 3 * bool(t.marks)
    s = _core(t.light).rstrip()
    if s and s[-1] in ",;":
        score += 2
    elif _REFRAIN_CUE.search(s) or _PARTICLE_END.search(s):
        score += 2
    if REFRAIN_AFTER_DOTS.search(t.light):
        score += 2
    if re.search(r"॥\s*\S", s):
        score += 3                      # a ॥ inside the line: run-on gathas and refrains
    words = {key_only(w) for w in cfg["prose_words"]}
    cut = [m.start() / max(1, len(s)) for m in re.finditer(r"[,;]", s)]
    if any(0.25 <= c <= 0.75 for c in cut) and not any(key_only(w) in words for w in _words(s)):
        score += 2                      # a caesura: two half-lines, no prose words
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
        if sum(c.isalpha() for c in light) < 2:
            t.kind = "furniture"                 # empty, or a stray OCR letter
        elif t.marks and _QUOTED.search(light):
            t.kind = "prose"                     # a verse quoted inside an explanation
        elif _part_heading(light.strip("।॥|()[] ").strip(), section_keys) and not t.marks:
            t.kind = "part"
        elif _is_tune(light, cfg):
            t.kind = "tune"
        elif not t.marks and _debris(light, t.conf, cfg):
            t.kind = "furniture"                 # an ornament, border or frame read as letters
        elif (_BRACKETED.match(light) and not t.marks) or _is_note(light, cfg):
            t.kind = "note"
        elif _heading_shape(light, title_keys, t, cfg):
            t.kind = "heading"
        else:
            t.kind = "prose" if _prose_score(t, cfg) > _verse_score(t, cfg) else "verse"


_SERIAL_ONLY = re.compile(r"^[\s।॥|`'\"]*[(\[]\s*[\dA-Za-z\u0900-\u0aff]{1,3}\s*[)\]][\s।॥|.]*$")
_ORNAMENT = "€©ॐ®✽❀❁✿*>«»~"
_FRAMED = re.compile(rf"^\s*[{_ORNAMENT}`'\"]+\s*\S.*\S\s*[{_ORNAMENT}]+\s*$|^\s*[{_ORNAMENT}]+\s*\S.*$|^.*\S\s*[{_ORNAMENT}]+\s*$")
_QUOTED = re.compile(r"[।॥]\s*[”\"’]")
_SERIAL_START = re.compile(r"^[\s।॥]*(\(\s*\S{1,3}\s*\)|\d{1,4}\s*[.)]|\d{1,4}\s)\s*")


def _heading_shape(light: str, title_keys, t: TLine, cfg) -> bool:
    """Short, no verse mark, no comma inside; a Kruti-type word, or a serial number
    before a plausible title ("8. श्री चन्द्रप्रभ जिन चैत्यवंदन")."""
    if t.marks:
        return False
    if t.fill > cfg["verse_fill_max"]:          # wide: only "… स्तवन" with no comma
        core = re.sub(r"^[\s\d.()\[\]]+", "", light).strip(" .।॥")
        return "," not in core and len(core.split()) <= 6 and _is_title(core, title_keys, [], 85)
    serial = _SERIAL_START.match(light)
    phrase = light[serial.end():] if serial else light
    words = phrase.split()                      # OCR debris around a framed title
    while len(words) > 1 and sum(c.isalpha() for c in words[0]) <= 1:
        words.pop(0)
    phrase = " ".join(words)
    if "," in phrase:                           # "… સજઝાય, રર": debris after a comma
        head, tail = phrase.rsplit(",", 1)
        if len(tail.split()) <= 2 and all(sum(c.isalpha() for c in w) <= 2 for w in tail.split()):
            phrase = head
    phrase = phrase.strip(" .,:-–।॥\"'“”")
    phrase = re.sub(r"\s*\([^)]*\)?\s*$", "", phrase) or phrase
    if not phrase or "," in phrase or len(phrase.split()) > 8:
        return False
    if _is_title(phrase, title_keys, [], 85):
        return True
    if bool(serial) and _plausible_title(phrase) and len(phrase.split()) <= 6:
        return True
    words = phrase.split()
    centred = t.indent >= 0.08 and abs(t.indent + t.fill / 2 - 0.5) < 0.12
    if centred and len(words) <= 8 and _FRAMED.match(t.text) and not re.search(r"[,;।॥]", phrase):
        return True                     # "€ आंख मारी उघडे त्यां ॐ": a title between ornaments
    return centred and len(words) <= 10 and any(key_only(w) in title_keys for w in words)


def _wrapped(t, cfg) -> bool:
    """A full-width prose line that breaks mid-sentence: the next line continues it."""
    return (t.kind == "prose" and t.fill >= cfg["prose_fill"] and _ends_open(t.light)
            and not _PARTICLE_END.search(t.light))


def explanation_opener(cfg):
    openers = "|".join(re.escape(light_normalize(o)) for o in cfg["explanation_openers"])
    return re.compile(rf"^[\s(\[_\-]*({openers})\s*(?:[:ः]|[\-–—]{{2}}|[\-–—](?=\s|$))")


def verse_like(t) -> bool:
    """Ends like a gatha line: punctuation, a closing particle, a refrain cue, a number."""
    s = _core(t.light).rstrip()
    return bool(t.marks) or bool(s) and (s[-1] in ",;।॥!?" or bool(_PARTICLE_END.search(s))
                                         or bool(_REFRAIN_CUE.search(s))
                                         or bool(REFRAIN_AFTER_DOTS.search(t.light)))


def _explanations(lines, cfg):
    """A paragraph opened by व्याख्या-, अर्थ:, भावार्थ … is prose up to the next gatha or
    heading. The next gatha starts at a narrow line that does not continue a wrapped
    prose line, and that has a verse mark or is followed by a narrow line that has one.
    The paragraph's own last line often repeats the gatha number (… ए भाव ॥ ११ ॥)."""
    opener = explanation_opener(cfg)
    body = [t for t in lines if t.kind != "furniture"]
    narrow = cfg["verse_fill_max"]
    inside = False
    for i, t in enumerate(body):
        if t.kind in ("heading", "part", "list"):
            inside = False
            continue
        if opener.match(t.light):
            inside = True
            t.kind = "prose"
            continue
        if not inside:
            continue
        prev = body[i - 1] if i else None
        nxt = body[i + 1] if i + 1 < len(body) else None
        closed = t.fill <= narrow or not _ends_open(t.light)
        starts_gatha = (closed and not (prev and _wrapped(prev, cfg))
                        and not _QUOTED.search(t.light)
                        and (t.marks or (nxt is not None and nxt.marks
                                         and nxt.fill < cfg["prose_fill"]
                                         and not _QUOTED.search(nxt.light))))
        if starts_gatha:
            inside = False
            if t.kind == "prose":
                t.kind = "verse"
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
        if (prev is not None and t.kind == "verse" and not t.marks and _wrapped(prev, cfg)
                and t.page == prev.page and t.gap_above < 0.5
                and not t.light.rstrip().endswith((",", ";"))):
            t.kind = "prose"
        prev = t


def _boundary_headings(lines, title_keys):
    """A line naming a Kruti type (… સજ્ઝાય અથવા …), without verse punctuation or mark,
    standing between one gatha's end and verse lines: a title the layout rules missed."""
    body = [t for t in lines if t.kind != "furniture"]
    for i, t in enumerate(body):
        if t.kind != "verse" or t.marks or i + 1 >= len(body):
            continue
        core = _core(t.light)
        words = core.split()
        if re.search(r"[,;।॥]", core) or not 2 <= len(words) <= 10:
            continue
        if not any(key_only(w) in title_keys for w in words):
            continue
        prev, nxt = (body[i - 1] if i else None), body[i + 1]
        at_boundary = (prev is None or prev.kind != "verse" or bool(prev.marks)
                       or bool(_REFRAIN_CUE.search(_core(prev.light)))
                       or bool(re.search(r"\d\W*$", prev.light)))       # "… .૧૯"
        if at_boundary and nxt.kind == "verse":
            t.kind = "heading"


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
