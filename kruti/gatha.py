"""Gatha Lines: split a book's classed lines (kruti/gatha_lines.py) into Kruti and gathas.

A Kruti starts at a heading, or where verse numbers restart at 1 without a part heading
(ढाल, दुहा, कलश) before them. Explanations printed between gathas are skipped and the
Kruti goes on; only a long run of prose with no gatha continuing the numbering after it,
or an index page, ends it. Tune, metre and refrain-marker lines never belong to a gatha.

Each gatha's first and last line are copied from the lines as read:
  numbered  - a gatha ends at its verse mark (॥3॥); a line holding several marks is cut
              at each one, so every gatha gets its own piece of it;
  no number - the layout decides: an empty gap or the indent of a gatha's first line;
              failing that, a steady count of lines per gatha confirmed by the line
              endings (॥ ; ।). Without either the block is not split.
"""
import re
import statistics
from dataclasses import dataclass, field

NUMBERED, INFERRED = "Numbered verse", "Number inferred (OCR garbled)"
BY_GAP, BY_COUNT = "No number - gap", "No number - line count"

C_NO_HEADING, C_LOW_OCR, C_INFERRED = "no heading", "low OCR", "inferred break"
C_ONE_LINE, C_LONG, C_PAGES, C_PROSE = "one-line gatha", "long gatha", "crosses pages", "next to prose"


@dataclass
class Gatha:
    part: str
    no: str                  # printed number, or "(n)" when the book prints none
    first: str
    last: str
    pages: tuple             # (first page, last page)
    how: str
    conf: float
    source: str              # "Text layer" / "OCR" / "Text layer + OCR"
    checks: list = field(default_factory=list)
    lines: int = 1           # printed lines (pieces) in the gatha


@dataclass
class GKruti:
    no: int
    title: str
    gathas: list
    checks: list = field(default_factory=list)


@dataclass
class _Piece:
    line: object             # TLine
    text: str
    number: object = None    # verse number at its end (None = garbled mark)
    marked: bool = False     # ends at a verse mark


@dataclass
class _Unit:
    title: str = ""
    items: list = field(default_factory=list)   # _Piece, ("part", label) or ("prose",)
    prose_before: bool = False     # running prose right before its first gatha
    prose_after: bool = False      # … and right after its last one
    commentary: bool = False       # its prose includes explanation openers (अर्थ--)


def confidence(g: Gatha, low_ocr: float) -> str:
    if g.how == BY_COUNT or g.conf < low_ocr or len(g.checks) >= 2:
        return "Low"
    if g.how != NUMBERED or g.checks:
        return "Medium"
    return "High"


# ---------------------------------------------------------------- phase A: Kruti units
def _pieces(t) -> list:
    """A verse line cut at its verse marks. A line ending in a refrain cue (… મનડુ'૦)
    whose number was lost still ends its gatha."""
    from .gatha_lines import _REFRAIN_CUE, _core
    core = _core(t.light)
    cue = _REFRAIN_CUE.search(core)
    before = core[:cue.start()].rstrip() if cue else ""
    ends = bool(cue) and not before.endswith((",", ";"))     # "…सिरदार; ऐसें०" is a half-line
    marks = t.marks or ([(len(t.text), None)] if ends else [])
    out, start = [], 0
    for end, number in marks:
        piece = t.text[start:end].strip()
        if piece:                          # a mark alone ("४।।") still closes its gatha
            out.append(_Piece(t, piece, number, True))
        start = end
    rest = t.text[start:].lstrip(" ।॥|").strip()
    if rest and any(c.isalpha() for c in rest):
        out.append(_Piece(t, rest))
    return out


def _units(lines, cfg) -> list:
    from .gatha_lines import explanation_opener
    opener = explanation_opener(cfg)
    units, cur = [], _Unit()
    title_open = False                     # consecutive heading lines make one title
    last_no, part_since, part_label = 0, False, ""
    prose_from = None                      # page where the current prose run started
    pending_start = 0                      # index in cur.items where the open gatha began
    prose_since_mark = False
    prose_lines, run_opener = 0, False        # the prose run just before this line

    def close():
        nonlocal cur, last_no, part_since, part_label
        if any(isinstance(x, _Piece) for x in cur.items):
            cur.prose_after = cur.items[-1] == ("prose",)
            units.append(cur)
        cur, last_no, part_since, part_label = _Unit(), 0, False, ""

    verse_lines = [t for t in lines if t.kind == "verse"]
    upcoming = {id(t): i for i, t in enumerate(verse_lines)}

    def next_numbers(t, k=3):
        i = upcoming[id(t)]
        nums = []
        for u in verse_lines[i:]:
            nums += [n for _, n in u.marks]
            if len(nums) >= k:
                break
        return nums

    for t in lines:
        if t.kind == "heading":
            if title_open:
                cur.title = f"{cur.title} {t.text.strip()}".strip()
            else:
                close()
                cur.title = t.text.strip()
                title_open = True
                cur.prose_before = False
            prose_from = None
            continue
        if t.kind == "list":
            close()
            title_open = False
            continue
        if t.kind == "part":
            part_label = t.text.strip(" ।॥|:-")
            cur.items.append(("part", part_label))
            part_since, title_open, last_no = True, False, 0
            pending_start = len(cur.items)
            continue
        if t.kind == "prose":
            prose_since_mark = True
            prose_lines += 1
            if opener.match(t.light):
                cur.commentary = True
                run_opener = True
            if not any(isinstance(x, _Piece) for x in cur.items):
                cur.prose_before = True
            if prose_from is None:
                prose_from = t.page
                if any(isinstance(x, _Piece) for x in cur.items):
                    cur.items.append(("prose",))
            title_open = False
            continue
        last_line = next((x.line for x in reversed(cur.items) if isinstance(x, _Piece)), None)
        ended = pending_start == len(cur.items) or bool(
            last_line and re.search(r"[.।॥]\s*(?:\S{1,5}\s*){0,2}$", last_line.text))
        if t.kind == "tune" and not title_open and ended and any(
                isinstance(x, _Piece) for x in cur.items) and cur.items[-1] != ("prose",) and not (
                isinstance(cur.items[-1], tuple) and cur.items[-1][0] == "part"):
            close()                     # a tune line after a finished gatha: the next Kruti,
            pending_start = 0           # printed without a title
            continue
        if t.kind != "verse":
            continue                                   # tune, note, furniture
        title_open = False
        if prose_from is not None and prose_lines >= 2 and not run_opener and not cur.commentary:
            close()                     # running prose with no अर्थ/भावार्थ: not a commentary
            cur.prose_before = True
            pending_start = 0
        if prose_from is not None:
            nums = [n for n in next_numbers(t) if n is not None]
            continues = bool(nums) and last_no and nums[0] in (last_no + 1, last_no + 2)
            if t.page - prose_from > cfg["max_explanation_pages"] and not continues:
                close()
                pending_start = 0
            prose_from = None
        prose_lines, run_opener = 0, False
        for p in _pieces(t):
            if p.marked and p.number is not None and p.number == last_no and prose_since_mark:
                # "… ए भाव ॥ ११ ॥": an explanation closing with the gatha's number
                cut = max((i for i, x in enumerate(cur.items) if x == ("prose",)), default=None)
                if cut is not None and cut >= pending_start:
                    cur.items = cur.items[:cut + 1]
                continue
            if p.marked and p.number == 1 and last_no >= 2 and not part_since:
                after = [n for n in next_numbers(t, 4) if n is not None]
                after = after[after.index(1) + 1:] if 1 in after else after
                if part_label:
                    # inside a named part (દોહા): its next part, whose heading OCR lost
                    cur.items.insert(pending_start, ("part", ""))
                    part_label = ""
                elif not after or after[0] in (2, None) or after[0] != last_no + 2:
                    # verses restart at 1: a new Kruti begins with the open gatha
                    carried = [x for x in cur.items[pending_start:] if isinstance(x, _Piece)]
                    cur.items = cur.items[:pending_start]
                    close()
                    cur.items.extend(carried)
            cur.items.append(p)
            if p.marked:
                if p.number is not None:
                    last_no = p.number
                elif last_no:
                    last_no += 1
                part_since = part_since and p.number is None
                pending_start = len(cur.items)
                prose_since_mark = False
    close()
    return units


# ---------------------------------------------------------------- phase B: gathas
def _fix_numbers(raw: list) -> list:
    """[(number, inferred)] for the raw verse numbers of one part."""
    out, prev = [], 0
    for i, n in enumerate(raw):
        expected = prev + 1
        nxt = next((x for x in raw[i + 1:] if x is not None), None)
        if n is None:
            out.append((expected, True))
        elif n == expected:
            out.append((n, False))
        elif prev == 0:                       # a part's first number: 1, unless the book
            misread = nxt is not None and (nxt <= 3 and n > nxt or nxt == n)   # starts later
            out.append((max(1, nxt - 1) if nxt != n else 1, True) if misread else (n, False))
        elif nxt is not None and nxt == expected + 1 or n > expected + 3 or n < expected:
            out.append((expected, True))
        else:
            out.append((n, False))
        prev = out[-1][0]
    return out


def _numbered(items, cfg):
    """[(part, [pieces], number_str, how, after_prose)]"""
    out, part, open_, prose = [], "", [], False
    groups = []                                   # per part: [(pieces, raw number, prose)]
    cur = []
    for x in items:
        if isinstance(x, tuple):
            if x[0] == "part":
                if open_:
                    cur.append((open_, None, prose, False))
                    open_ = []
                groups.append((part, cur))
                part, cur = x[1], []
            else:
                prose = True
            continue
        open_.append(x)
        if x.marked:
            cur.append((open_, x.number, prose, True))
            open_, prose = [], False
    if open_:
        cur.append((open_, None, prose, False))
    groups.append((part, cur))
    for part, gs in groups:
        fixed = _fix_numbers([n for _, n, _, _ in gs])
        for (pieces, raw, prose, marked), (n, inferred) in zip(gs, fixed):
            how = INFERRED if inferred else NUMBERED
            out.append((part, pieces, str(n), how, prose, not marked))
    return out


def _weight(text: str) -> float:
    s = text.rstrip()
    return 1.0 if s.endswith("॥") else 0.75 if s.endswith(".") else 0.5 if s.endswith((";", "।")) else 0.0


def _split_unnumbered(pieces, cfg):
    """[(pieces)] and how, or (None, None) when no layout or ending pattern agrees."""
    n, max_len = len(pieces), cfg["long_gatha_lines"]

    def cut(starts):
        starts = sorted(set([0] + starts))
        parts = [pieces[a:b] for a, b in zip(starts, starts[1:] + [n])]
        return parts if len(parts) >= 2 and max(len(p) for p in parts) <= max_len else None

    from .gatha_lines import REFRAIN_AFTER_DOTS
    ends = [i + 1 for i in range(n - 1) if REFRAIN_AFTER_DOTS.search(pieces[i].line.light)]
    if len(ends) >= 1 and REFRAIN_AFTER_DOTS.search(pieces[-1].line.light) and (parts := cut(ends)):
        return parts, BY_GAP                     # each stanza closes with its refrain cue
    gaps = [i for i in range(1, n) if pieces[i].line.gap_above >= cfg["gatha_gap"]]
    if gaps and (parts := cut(gaps)):
        return parts, BY_GAP
    a = pieces[0].line.indent
    ind = [i for i in range(1, n) if abs(pieces[i].line.indent - a) < 0.04
           and abs(pieces[i - 1].line.indent - a) >= 0.04]
    if ind and (parts := cut(ind)):
        return parts, BY_GAP
    best = None
    for k in (2, 4, 3):
        if n < 2 * k:
            continue
        at = [_weight(pieces[i].text) for i in range(k - 1, n, k)]
        other = [_weight(pieces[i].text) for i in range(n) if (i + 1) % k]
        score = sum(at) / len(at) - (sum(other) / len(other) if other else 0)
        if score >= 0.5 and (best is None or score > best[0]):
            best = (score, k)
    if best:
        k = best[1]
        return [pieces[i:i + k] for i in range(0, n, k)], BY_COUNT
    return None, None


def _source(pieces) -> str:
    kinds = {p.line.source for p in pieces}
    if kinds == {"text"}:
        return "Text layer"
    return "OCR" if kinds == {"ocr"} else "Text layer + OCR"


def _gatha(part, no, pieces, how, cfg, extra=()) -> Gatha:
    first = pieces[0].text
    last = pieces[-1].text
    bare = re.sub(r"[।॥|.\s\d०-९૦-૯]", "", re.sub(r"\S*[0०૦](?=[\s.।॥]|$)", "", last))
    if len(pieces) > 1 and not re.search(r"[^\W\d_]", bare):
        last = f"{pieces[-2].text} {last}"          # a verse mark (and cue) alone on its line
    confs = [p.line.conf for p in pieces]
    pages = (pieces[0].line.page, pieces[-1].line.page)
    g = Gatha(part, no, first, last, pages, how, round(sum(confs) / len(confs), 1),
              _source(pieces), list(extra), len(pieces))
    if g.conf < cfg["low_ocr_confidence"]:
        g.checks.append(C_LOW_OCR)
    if how != NUMBERED:
        g.checks.append(C_INFERRED)
    if len(pieces) > cfg["long_gatha_lines"]:
        g.checks.append(C_LONG)
    if pages[0] != pages[1]:
        g.checks.append(C_PAGES)
    return g


def _unit_gathas(unit, cfg) -> list:
    pieces = [x for x in unit.items if isinstance(x, _Piece)]
    out = []
    if sum(p.marked for p in pieces) >= 2:
        rows = _numbered(unit.items, cfg)
        sizes = sorted(len(ps) for _, ps, _, how, _, unmarked in rows if how == NUMBERED)
        usual = sizes[len(sizes) // 2] if len(sizes) >= 3 else 0
        for part, ps, no, how, prose, unmarked in rows:
            extra = [C_PROSE] if prose else []
            if not ps:
                continue
            k = len(ps) // usual if usual else 1
            if usual and k >= 2 and len(ps) == k * usual and no.isdigit():
                # a lost verse number joined k gathas of the usual size: split them again
                for j in range(k):
                    out.append(_gatha(part, str(int(no) - k + 1 + j),
                                      ps[j * usual:(j + 1) * usual],
                                      how if j == k - 1 else INFERRED, cfg, extra if j == 0 else []))
                continue
            out.append(_gatha(part, no, ps, how, cfg, extra))
    else:
        part, run, prose_before, blocks = "", [], False, []
        for x in unit.items + [("end",)]:
            if isinstance(x, _Piece):
                run.append(x)
                continue
            if run:
                blocks.append((part, run, prose_before))
                run, prose_before = [], False
            if x[0] == "part":
                part = x[1]
            elif x[0] == "prose":
                prose_before = True
        from .gatha_lines import verse_like
        for part, run, prose in blocks:
            if sum(verse_like(x.line) for x in run) < cfg["min_verse_like"] * len(run):
                continue                # a title page, an address: lines that end like no verse
            parts, how = _split_unnumbered(run, cfg)
            for i, ps in enumerate(parts or [], 1):
                out.append(_gatha(part, f"({i})", ps, how, cfg, [C_PROSE] if prose and i == 1 else []))
    return out


def _drop_stray_marks(lines) -> None:
    """A number far out of sequence, right before the expected one (… માંસ, ३० then
    … ॥7॥): a refrain cue such as રૂ૦ read as digits, not a verse mark."""
    marks = [(t, k) for t in lines if t.kind == "verse" for k in range(len(t.marks))]
    nums = [t.marks[k][1] for t, k in marks]
    drop, prev = set(), None
    # the same number again and again (३० on every first half-line): a cue, not a verse
    counts, fits, before = {}, set(), None
    for n in nums:
        if n is not None and before is not None:
            if n == before + 1:
                fits.add(n)                            # continues the numbering somewhere
            elif n not in (1, before + 2):
                counts[n] = counts.get(n, 0) + 1       # out of sequence here
        before = n if n is not None else before
    suspect = {n for n, c in counts.items() if n >= 10 and c >= 3 and n not in fits}
    last = None
    for i, n in enumerate(nums):
        if n in suspect and (last is None or n != last + 1):
            drop.add(i)
        elif n is not None:
            last = n
    for i, n in enumerate(nums):
        if n is None or i in drop:
            continue
        nxt = next((x for j, x in enumerate(nums[i + 1:], i + 1) if x is not None and j not in drop),
                   None)
        if (prev is not None and n > prev + 2       # far ahead; a misread lower number
                and nxt is not None and nxt in (prev + 1, prev + 2)):   # stays (inferred)
            drop.add(i)
            continue
        prev = n
    # "…लाल।।" closing every half-line: empty marks between two consecutive numbers (or
    # more of them than numbers are missing) are not verse marks
    known = [i for i, n in enumerate(nums) if n is not None and i not in drop]
    for a, b in zip([-1] + known, known):
        empties = [i for i in range(a + 1, b) if nums[i] is None and i not in drop]
        if not empties:
            continue
        lo = nums[a] if a >= 0 else 0
        missing = nums[b] - lo - 1 if nums[b] > lo else nums[b] - 1
        if nums[b] <= lo and a >= 0:
            missing += 1                # a restart: the old Kruti may still have one gatha
        excess = len(empties) - max(0, missing)
        if excess <= 0:
            continue

        def doubtful(i):
            """An empty danda pair ("लाल।।"), or a mark ending a half-line ("…તાસ; ર"),
            not a gatha end written with dots or a garbled digit after a full stop."""
            t, k = marks[i]
            before = t.text[:t.marks[k][0]].rstrip()
            core = re.sub(r"\s*\S{0,2}$", "", before).rstrip()   # without the garbled digit
            return before[-1:] in "।॥|" or core[-1:] in ",;"
        order = [i for i in empties if doubtful(i)]
        drop.update(order[:excess])
    # "…પંક્તિ..." then the short refrain line "મોહ રે ઉતારો મુનિરાજજી ૨": the number on
    # the refrain line ends the gatha, the dots before it do not
    verse = [t for t in lines if t.kind == "verse"]
    for t, nxt in zip(verse, verse[1:]):
        if (t.marks and t.marks[-1][1] is None and len(nxt.marks) == 1 and nxt.fill < 0.5
                and nxt.page == t.page):
            k = len(t.marks) - 1
            i = next((j for j, (tt, kk) in enumerate(marks) if tt is t and kk == k), None)
            if i is not None:
                drop.add(i)
    for i in sorted(drop, reverse=True):
        t, k = marks[i]
        t.marks = t.marks[:k] + t.marks[k + 1:]


def split_gathas(lines: list, cfg: dict) -> list:
    """GKruti with 2 or more gathas, in book order, numbered 1, 2, 3 …"""
    _drop_stray_marks(lines)
    krutis = []
    for unit in _units(lines, cfg):
        gathas = _unit_gathas(unit, cfg)
        if len(gathas) < 2:
            continue
        if (not unit.title and unit.prose_before and unit.prose_after and not unit.commentary
                and len(gathas) <= cfg["max_quote_gathas"]):
            continue                    # verses quoted inside a preface or biography
        checks = [] if unit.title else [C_NO_HEADING]
        if statistics.median(g.lines for g in gathas) >= 2:
            for g in gathas:
                if g.lines == 1:
                    g.checks.append(C_ONE_LINE)     # among multi-line gathas: a missed mark?
        for g in gathas:
            g.checks = checks + g.checks
        krutis.append(GKruti(len(krutis) + 1, unit.title, gathas, checks))
    return krutis

