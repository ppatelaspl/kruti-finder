"""Tell Kruti text from the rest of a book.

Besides its Kruti a book prints a preface, an editor's note, a biography, an index, a
publisher's list - and in many books an explanation after every verse (व्याख्या, अर्थ,
भावार्थ, बालावबोध). None of it is a Kruti, yet it carries dandas and numbers too, so the
verse splitter would take it for one. This module finds that text so it can be left out:

  * prose pages - running sentences (है, था, किया / छे, हतो, करवामां ...) whose lines
    wrap mid-sentence; verse lines end at a comma or danda instead;
  * index / contents / list pages - many short lines, numbers, no verses;
  * explanations between the verses of a Kruti - a paragraph opened by व्याख्या-, अर्थ:,
    भावार्थ ...; a stretch between two verse numbers that reads as prose; or three and
    more lines wrapping mid-sentence with prose words. Verses the explanation quotes
    ("यतः-“… ॥2॥”") go with it;
  * source notes - "(खरतरगच्छ साहित्य कोश क्रमांक- 2592.)" after a Kruti.

Running headers and footnotes are dropped earlier, with the page furniture (matcher.py).
The text is blanked, not removed, so every offset (and so every page number) stays valid.
"""
import re

from rapidfuzz import fuzz

from .normalize import key_only

PROSE, INDEX, EXPLANATION, NOTE = "prose", "index", "explanation", "note"

# Words of running prose: auxiliaries, pronouns and connectives of modern Hindi and
# Gujarati. Verse rarely uses them; a preface or an explanation is full of them.
PROSE_WORDS = frozenset("""
है हैं था थी थे थीं होता होती होते होगा होगी किया किये किए कीया गया गयी गई गए जाता जाती जाते
जाना करना करने करते करके करवाया करवाने रहा रही रहे इसका इसके इसकी उसका उसके उसकी जिसके
जिसका जिसकी जिससे जिन्होंने उन्होंने उनके उनकी उनका आपने आपकी आपका आपके हमारे हमने हमें
द्वारा तथा एवं परन्तु परंतु किन्तु लेकिन क्योंकि अतः अर्थात् इसलिये इसलिए यह वह इस उस इन उन
छे छीए हतो हती हता हतुं हतां थयो थयेल थयेला थयेली थयुं थई थाय करवामां करवानी करवाथी आवेल
आवेली आवेला एटले तेमज तेथी माटे अमे अमारी अमारा अमने तेओ तेओश्री तेमना तेमनी तेने तेनी तेना
एवा एवी आवा आवी करीने आपेल छपाववा प्रसिद्ध पुस्तक पुस्तकमां ग्रंथ ग्रन्थ इत्यर्थः
""".split())

# Opening word of an explanation paragraph ("व्याख्या-हे श्री सीमंधर ...", "अर्थ: ...")
EXPLANATION_WORDS = ("व्याख्या", "भावार्थ", "विवेचन", "विवरण", "तात्पर्य", "अनुवाद", "शब्दार्थ",
                     "विशेषार्थ", "सारांश", "बालावबोध", "टबार्थ", "अन्वयार्थ", "अर्थ", "टीका",
                     "अन्वय", "समजूती")
# OCR spellings seen in the books: अर्थ -> अर्य, अथे, अर्थृ; व्याख्या -> व्यास्या, न्यार्या, व्यारूपा
_EXPLANATION_KEYS = [key_only(w) for w in EXPLANATION_WORDS + (
    "अर्य", "अथे", "अये", "अर्थृ", "अर्थः", "व्यास्या", "व्वास्या", "व्यार्या", "न्यार्या", "व्यारूपा")]
# the word, then a dash or colon ("व्याख्या-", "अर्थ:", "भावार्थः-"); a visarga alone is
# just the end of a Sanskrit word ("समुद्यताभिः")
# It may follow the verse number it explains on the same line: "॥ 1 ॥ ” अर्थ-…"
_OPENING = re.compile(r"^(?:[\s(\[।॥*”\"']|\d{1,3}(?=\s*[।॥]))*([^\s\-–—:ः()”\"']{2,12})ः?\s*[\-–—:]")
# "38-जयतिहुअण स्तोत्र ।", "॥ श्री संभवनाथजी का स्तवन ॥": the next Kruti's heading
_HEADING_LINE = re.compile(r"^\s*(\d{1,4}\s*[-–—.)]+\s*\S.{2,50}[।॥.]?\s*|[।॥]+[^,।॥]{3,60}[।॥]+\s*)$")

# a quotation inside an explanation: "यतः-“…", "तथा-“…", "उक्तं च", "इत्यादि तथा “…"
_CITATION = re.compile(r"\s*([“\"'‘]|(यतः|यत|तथा|उक्तं|उक्तञ्च|यदुक्तं|इत्यादि|इति)\s*[-–:ः“\"'])")
_VERSE_NO = re.compile(r"[।॥]\s*\d{1,3}\s*[।॥]")
_WORD = re.compile(r"[\u0900-\u097F]+")
# "(खरतरगच्छ साहित्य कोश क्रमांक- 2592.)": where the Kruti was catalogued, not its text
_SOURCE_NOTE = re.compile(r"^\s*\(.{0,60}(कोश|कोष|कोस|क्रमा[ंङ]?क|क\S?माक|साहित्य)")
_INDEX_WORDS = ("अनुक्रम", "अनुक्रमणिका", "विषयानुक्रम", "विषयानुक्रमणिका", "विषयसूची", "सूची",
                "सूचि", "नामावली", "शुद्धिपत्रक", "शुद्धिपत्र")
_INDEX_KEYS = [key_only(w) for w in _INDEX_WORDS]


# "मूर्छा के० ममता": the explainer's "that is" (के०, OCR'd के0 / के° / के")
_KE = re.compile(r"(?<![\u0900-\u097F])के\s?[0०°\"']")


def prose_share(text: str) -> float:
    """Share of the words that belong to running prose."""
    words = [w for w in _WORD.findall(text) if w not in ("।", "॥")]
    hits = sum(w in PROSE_WORDS for w in words) + len(_KE.findall(text))
    return hits / max(1, len(words))


def _lines(text: str) -> list:
    return [ln.strip() for ln in text.split("\n") if ln.strip()]


def line_end_share(text: str, min_len: int = 15) -> float:
    """Share of full lines that end at a comma, danda or verse number. A verse line ends
    there; a prose line wraps in the middle of a sentence."""
    lines = [ln for ln in _lines(text) if len(ln) > min_len]
    if not lines:
        return 1.0
    return sum(map(_ends_like_verse, lines)) / len(lines)


def _ends_like_verse(line: str) -> bool:
    """Ends at a comma, danda, verse number, "रे"/"जी", a refrain cue ("स्वा०"), or the
    dots some books end verse lines with ("…चारे कोर. हो राज.", "…गाढी...")."""
    return bool(re.search(r"[,;।॥!?)\d]\s*$|(रे|जी|हो)$|\S(?<!के)[0०°]$|(\.{2,}|…)\s*\S{0,3}\s*$|\.\s*\S{1,4}\s?\S{0,4}\.\s*$",
                          line.strip()))


# a list of first lines: "प्रत्येक लावणीनुं प्रथमपद", "सज्झाय प्रथम पद रचयिता"
_FIRST_LINES = [key_only(w) for w in ("प्रथमपद", "प्रथम पद", "आदिपद", "आद्यपद", "प्रथम पंक्ति")]


def _index_heading(line: str) -> bool:
    """"विषयानुक्रमणिका", OCR'd "विषयाहुक्रमणिका", "अनुक्रम", "सूची", "… प्रथमपद" on a
    short line."""
    if len(line) > 40:
        return False
    k = key_only(line)
    if any(f in k for f in _FIRST_LINES) or (len(k) >= 6 and any(
            fuzz.partial_ratio(f, k) >= 85 for f in _FIRST_LINES)):
        return True
    if len(line) > 30:
        return False
    for w in line.split():
        k = key_only(w)
        if k in _INDEX_KEYS or (len(k) >= 6 and any(
                len(i) >= 6 and fuzz.ratio(k, i) >= 80 for i in _INDEX_KEYS)):
            return True
    return False


def _looks_like_index(text: str) -> bool:
    """Contents / index / name lists: short lines, many numbers, no verses."""
    lines = _lines(text)
    if len(lines) < 6 or len(_VERSE_NO.findall(text)) > 1:
        return False
    # the heading may sit below a column of serial numbers OCR read as junk ("र4", "र्")
    if any(_index_heading(ln) for ln in lines[:40]) and not _verse_page(text):
        return True
    short = sum(len(ln) <= 45 for ln in lines) / len(lines)
    commas = sum("," in ln for ln in lines) / len(lines)
    # (a page number is never 0: "… हु 0" is an OCR'd refrain cue "हु०")
    numbered = sum(bool(re.match(r"^\W{0,2}\d{1,4}\b|.*\D\s[1-9]\d{0,3}\W{0,2}$", ln))
                   for ln in lines) / len(lines)
    # "विषयानुक्रमणिका", or the column heads "नाम … पृष्ठ" of a contents table
    # "…मनमोहनमेरे 16", "… 17": line-end numbers counting up by one number verses; an
    # index's page numbers jump
    ends = [int(m.group(1)) for ln in lines for m in [re.search(r"\D\s(\d{1,3})\W{0,2}$", ln)] if m]
    if len(ends) >= 3 and sum(b == a + 1 for a, b in zip(ends, ends[1:])) >= 0.6 * (len(ends) - 1):
        return False
    titled = any(re.fullmatch(r"\W*(नाम|नाप|विषय|अंक|आंक|पृष्ठ)(\s+(पृष्ठ|पृष्ट|पत्र|पेज)\S*)?\W*", ln)
            for ln in lines[:4])
    # an entry is a name and a page number; a verse line has twice the words. Short lines
    # alone are not enough: a narrow page sets a sutra in short lines too
    words = sorted(len(_WORD.findall(ln)) for ln in lines)[len(lines) // 2]
    if short >= 0.7 and commas <= 0.2 and words <= 6 and (titled or numbered >= 0.3):
        return True
    # a list of titles whose serial numbers OCR put on lines of their own (dropped as page
    # furniture): no punctuation at all - a verse always has some - and hardly a word
    # broken across lines with a hyphen, as a sutra set in narrow lines has
    bare = sum(not re.search(r"[,;।॥!?]", ln) for ln in lines) / len(lines)
    # Short verse lines whose dandas OCR lost still end like verse ("…रे", "…हु०", "…जी")
    return (len(lines) >= 8 and not _VERSE_NO.search(text) and bare >= 0.85 and short >= 0.9
            and words <= 5 and sum(ln.endswith("-") for ln in lines) <= 0.1 * len(lines)
            and line_end_share(text, 5) < 0.3)


def _verse_page(text: str) -> bool:
    """A page of verses: several verse numbers, and most lines ending like a verse line -
    or, for verse set as running text, hardly a prose word."""
    marks = len(_VERSE_NO.findall(text))
    return marks >= 2 and line_end_share(text) >= 0.4 or marks >= 3 and prose_share(text) < 0.03


def page_kind(text: str, front: bool = False):
    """PROSE, INDEX or None (a page that may hold Kruti). front: the page comes before the
    book's first page of verses, where a preface quoting a few numbered verses, or one
    whose OCR'd Gujarati shows few prose words, is still a preface."""
    words = len(_WORD.findall(text))
    if _looks_like_index(text):
        return INDEX
    if front and words >= 40 and line_end_share(text) < 0.25 and prose_share(text) >= 0.01 \
            and (len(_VERSE_NO.findall(text)) < 2 or prose_share(text) >= 0.04):
        return PROSE
    # a page printing verses with their numbers holds Kruti, however much explanation
    # surrounds them; the explanation is then found paragraph by paragraph
    if words < 40 or len(_VERSE_NO.findall(text)) >= 2:
        return None
    share, ends = prose_share(text), line_end_share(text)
    if (ends < 0.35 and share >= 0.03) or (share >= 0.10 and ends < 0.6):
        return PROSE
    return None


def _explanation_start(line: str) -> bool:
    """"व्याख्या-…", "व्यास्या-…" (OCR), "अर्थ:-…", "भावार्थ :…"."""
    m = _OPENING.match(line)
    if not m:
        return False
    k = key_only(m.group(1))
    if len(k) < 2:
        return False
    return any(k == e or (len(e) >= 6 and len(k) >= 5 and fuzz.ratio(k, e) >= 75)
               for e in _EXPLANATION_KEYS)


def _verse_like(line: str) -> bool:
    return bool(re.search(r"[,;।॥]\s*$", line)) and prose_share(line) < 0.1


def non_kruti_spans(book) -> list:
    """[(start, end, kind)] in book.light offsets: text that is not part of any Kruti."""
    light, starts = book.light, list(book.page_starts) + [len(book.light)]
    pages = [(starts[i], starts[i + 1]) for i in range(len(starts) - 1)]
    first_verses = next((i for i, (s, e) in enumerate(pages) if _verse_page(light[s:e])),
                        len(pages))
    kinds = [page_kind(light[s:e], i < first_verses) for i, (s, e) in enumerate(pages)]
    # a preface page that quotes a few verses scores lower; prose on both sides gives it away
    for i in range(1, len(pages) - 1):
        s, e = pages[i]
        if kinds[i] is None and kinds[i - 1] == PROSE and kinds[i + 1] == PROSE \
                and prose_share(light[s:e]) >= 0.03:
            kinds[i] = PROSE
    spans = [(s, e, k) for (s, e), k in zip(pages, kinds) if k]
    spans += _prose_between_verses(light, spans)
    for i, ((s, e), kind) in enumerate(zip(pages, kinds)):
        if kind:
            continue
        spans += _wrapped_prose(light, s, e)
        pos = s
        while pos < e:
            eol = light.find("\n", pos, e)
            eol = e if eol < 0 else eol
            line = light[pos:eol]
            if _SOURCE_NOTE.match(line) and not _VERSE_NO.search(line):
                spans.append((pos, eol, NOTE))
            elif _explanation_start(line):
                end = _explanation_end(light, pos, pages, i)
                spans.append((pos, end, EXPLANATION))
                pos = end
                continue
            pos = eol + 1
    return sorted(spans)


def _wrapped_prose(light: str, s: int, e: int, run: int = 3) -> list:
    """A paragraph of explanation: lines filled to the margin that wrap mid-sentence, with
    some prose words, plus the short line closing it ("… न जाणे ॥ 8 ॥"). Kruti text set
    as running lines stays: a Prakrit sutra has no prose words, a लावणी numbers its
    verses inside the run."""
    lines, pos = [], s
    while pos < e:
        eol = light.find("\n", pos, e)
        eol = e if eol < 0 else eol
        if light[pos:eol].strip():
            lines.append((pos, eol, light[pos:eol].strip()))
        pos = eol + 1
    found, i = [], 0
    while i < len(lines):
        j = i
        while j < len(lines) and len(lines[j][2]) >= 40 and not _ends_like_verse(lines[j][2]):
            j += 1
        body = "\n".join(ln for _s, _e, ln in lines[i:j])
        if j - i >= run and _explains(body):
            if j < len(lines) and "," not in lines[j][2]:
                j += 1                       # the paragraph's last line
            found.append((lines[i][0], lines[j - 1][1], EXPLANATION))
        i = max(j, i + 1)
    return found


def _explains(text: str) -> bool:
    """Running lines that are an explanation, not verse set as running text: clearly
    prose words, or the explainer's "के०"; never verse numbers inside, nor a danda on
    most lines (a लावणी's refrain cues "॥ सती० ॥")."""
    if _numbers_verses(text):
        return False
    if len(_KE.findall(text)) >= 2:
        return True
    lines = _lines(text)
    words = len(_WORD.findall(text))
    share = prose_share(text)
    dandas = len(re.findall(r"[।॥]", text)) / max(1, len(lines))
    return share >= 0.06 and share * words >= 4 and dandas < 0.8


def _numbers_verses(text: str) -> bool:
    """Verse printed as running lines ("…गमता ॥ सतीन ॥1॥ सती रथ संजम…") numbers its verses
    inside the run. An explanation has its own number only at its end; the numbers inside
    it belong to verses it quotes, closed by a quote mark ("…॥1॥”")."""
    return any(not re.match(r"\s*[”\"']", text[m.end():m.end() + 3])
               for m in _VERSE_NO.finditer(text))


def _stretches(light: str):
    """(start, end) of the text up to each verse number. A number right before a closing
    quote ("… ॥1॥”") numbers a verse quoted inside the explanation; it does not end the
    stretch."""
    start = 0
    for m in _VERSE_NO.finditer(light):
        if re.match(r"\s*[”\"']", light[m.end():m.end() + 3]):
            continue
        yield start, m.start(), m.end()
        start = m.end()


def _first_heading(light: str, start: int, end: int):
    """Offset of the first heading line inside light[start:end] (not its first line)."""
    pos = light.find("\n", start, end)
    while 0 <= pos < end:
        eol = light.find("\n", pos + 1, end)
        eol = end if eol < 0 else eol
        if _HEADING_LINE.match(light[pos + 1:eol]):
            return pos + 1
        pos = eol if eol < end else -1
    return None


def _prose_between_verses(light: str, page_spans) -> list:
    """An explanation printed after each verse runs up to its own verse number, so the
    stretch between two verse numbers is either a verse or an explanation. Prose words
    and lines that wrap mid-sentence tell which; short stretches are always verse.
    Explanations quote other texts ("यतः-“… ॥2॥”", "तथा-“… ॥2॥”"); a quoted verse
    belongs to the explanation around it, not to the Kruti."""
    found, explaining = [], False
    for start, mark, end in _stretches(light):
        if inside(page_spans, start, end):
            explaining = False
            continue
        text = light[start:mark]
        if explaining and _CITATION.match(text):
            found.append((start, end, EXPLANATION))
            continue
        explaining = False
        words = len(_WORD.findall(text))
        if words < 25:
            continue
        # a verse uses तथा, छे, अमे now and then; an explanation keeps using them
        share, ends = prose_share(text), line_end_share(text)
        if (share * words >= 4 and ((share >= 0.08 and ends < 0.4) or share >= 0.12)) \
                or len(_KE.findall(text)) >= 2:
            head = _first_heading(light, start, mark)
            found.append((start, head if head is not None else end, EXPLANATION))
            explaining = head is None
    return found


def _explanation_end(light: str, pos: int, pages: list, page_index: int) -> int:
    """An explanation runs up to its own verse number (॥ 3 ॥). When the page ends first
    and the next page opens with a verse line, the explanation ended with the page."""
    for i in range(page_index, len(pages)):
        s, e = pages[i]
        if i > page_index:
            first = next(iter(_lines(light[s:e])), "")
            if _verse_like(first):
                return s
        m = _VERSE_NO.search(light, max(pos, s), e)
        if m:
            return m.end()
        if i - page_index >= 1:
            return e
    return pages[-1][1]


# Marks where blanked text begins. It is not whitespace, so no pattern can match across a
# blanked stretch ("।" on one page, "॥" twenty blank pages later).
SEPARATOR = "\u2063"


def blank(light: str, spans) -> str:
    """The book's text with the spans blanked out (line breaks kept, offsets unchanged)."""
    out = list(light)
    for s, e, _kind in spans:
        for i in range(s, min(e, len(out))):
            if out[i] != "\n":
                out[i] = " "
        if s < len(out) and out[s] != "\n":
            out[s] = SEPARATOR
    return "".join(out)


def inside(spans, start: int, end: int, kinds=(PROSE, INDEX)) -> bool:
    """True when most of light[start:end] lies in spans of the given kinds."""
    covered = sum(max(0, min(end, e) - max(start, s)) for s, e, k in spans if k in kinds)
    return covered >= 0.5 * max(1, end - start)
