"""Locate each Kruti's Aadi Vakya (start) and Ant Vakya (end) inside a book.

Search works in two stages so it stays fast on large books:
  1. a character n-gram index votes for the few regions that could contain the line;
  2. only those regions are scored with a fuzzy alignment (rapidfuzz).
"""
import bisect
import re
from collections import defaultdict
from dataclasses import dataclass, field

from rapidfuzz import fuzz, process

from .normalize import clean_reference, light_normalize, make_key, split_segments

FOUND, PARTIAL, NOT_FOUND = "Found", "Partially Found", "Not Found"
# "first line ....... 12" - an entry in a book's index / table of contents
_INDEX_LEADER = re.compile(r"^[^\n]{0,40}?[.\-_…·]{4,}\s*\d{1,4}\s*$", re.M)


def _furniture_key(line: str) -> str:
    return re.sub(r"\d+", "", line).strip()


def _running_lines(texts, share):
    """Short lines repeated on many pages: running book titles, chapter headers."""
    counts = defaultdict(int)
    for t in texts:
        for k in {_furniture_key(ln) for ln in t.split("\n")
                  if 0 < len(ln.strip()) <= 60 and not re.search(r"[।॥]", ln)}:
            if k:
                counts[k] += 1
    limit = max(3, share * len(texts))
    return {k for k, c in counts.items() if c >= limit}


def _is_page_furniture(line: str, repeated: set, edge: bool) -> bool:
    """Page numbers and running headers/footers must not leak into Kruti text.
    Lines at the top/bottom of a page are also matched fuzzily, because OCR spells a
    header slightly differently on each page."""
    stripped = line.strip()
    if re.fullmatch(r"[\d\s\-–—()\[\].|]+", stripped):
        return True
    if len(stripped) > 60 or re.search(r"[।॥]", stripped):
        return False
    key = _furniture_key(stripped)
    if key in repeated:
        return True
    return edge and bool(repeated) and process.extractOne(
        key, repeated, scorer=fuzz.ratio, score_cutoff=75) is not None


@dataclass
class Book:
    name: str
    light: str                 # whole-book light text
    page_starts: list          # light offset where each page begins
    page_numbers: list         # PDF page number for each entry in page_starts
    key: str = ""
    key_map: list = field(default_factory=list)

    @classmethod
    def from_pages(cls, name, pages, header_share: float = 0.2):
        texts = [light_normalize(p.text) for p in pages]
        repeated = _running_lines(texts, header_share)
        parts, starts, numbers, pos = [], [], [], 0
        for p, raw in zip(pages, texts):
            lines = [ln for ln in raw.split("\n") if ln.strip()]
            lines = [ln for i, ln in enumerate(lines) if not _is_page_furniture(
                ln, repeated, edge=i < 2 or i >= len(lines) - 2)]
            txt = "\n".join(lines) + "\n"
            starts.append(pos)
            numbers.append(p.page)
            parts.append(txt)
            pos += len(txt)
        book = cls(name, "".join(parts), starts, numbers)
        book.key, book.key_map = make_key(book.light)
        return book

    def page_of_light(self, light_pos: int) -> int:
        i = max(0, bisect.bisect_right(self.page_starts, light_pos) - 1)
        return self.page_numbers[i] if self.page_numbers else 0

    def page_of_key(self, key_pos: int) -> int:
        if not self.key_map:
            return 0
        key_pos = min(max(key_pos, 0), len(self.key_map) - 1)
        return self.page_of_light(self.key_map[key_pos])

    def light_of_key(self, key_pos: int) -> int:
        key_pos = min(max(key_pos, 0), len(self.key_map) - 1)
        return self.key_map[key_pos]


@dataclass
class Hit:
    score: float
    start: int   # key offsets in the book
    end: int


class BookIndex:
    def __init__(self, key: str, n: int = 4):
        self.key, self.n = key, n
        idx = defaultdict(list)
        for i in range(len(key) - n + 1):
            idx[key[i:i + n]].append(i)
        self.idx = idx
        # grams that occur everywhere carry no signal
        self.max_freq = max(50, len(key) // 2000)

    def search(self, query: str, min_score: float, bucket: int = 24, top_k: int = 12) -> list:
        n = self.n
        grams = len(query) - n + 1
        if grams < 3:
            return []
        votes = defaultdict(int)
        for off in range(grams):
            positions = self.idx.get(query[off:off + n])
            if not positions or len(positions) > self.max_freq:
                continue
            for p in positions:
                votes[(p - off) // bucket] += 1
        min_votes = max(3, int(0.12 * grams))
        candidates = sorted((b for b, v in votes.items() if v >= min_votes),
                            key=lambda b: -votes[b])[:top_k]

        hits = []
        for b in candidates:
            lo = max(0, b * bucket - bucket - 12)
            hi = min(len(self.key), b * bucket + len(query) + 2 * bucket + 12)
            al = fuzz.partial_ratio_alignment(query, self.key[lo:hi])
            if al and al.score >= min_score:
                hits.append(Hit(round(al.score, 1), lo + al.dest_start, lo + al.dest_end))
        return _dedupe(hits)


def _dedupe(hits):
    """Keep the best hit among overlapping ones."""
    kept = []
    for h in sorted(hits, key=lambda h: -h.score):
        if all(h.end <= k.start or h.start >= k.end for k in kept):
            kept.append(h)
    return sorted(kept, key=lambda h: h.start)


# ------------------------------------------------------------------ queries
def build_query(text: str, part: str, max_len: int, min_len: int = 15) -> str:
    """Aadi uses the first '...' segment, Ant the last usable one; long lines are trimmed
    to their most distinctive end (start of Aadi, end of Ant)."""
    segments = [make_key(s)[0] for s in split_segments(clean_reference(text))]
    segments = [s for s in segments if s] or [""]
    if part == "aadi":
        q = next((s for s in segments if len(s) >= min_len), segments[0])
        return q[:max_len]
    q = next((s for s in reversed(segments) if len(s) >= min_len), segments[-1])
    return q[-max_len:]


@dataclass
class Occurrence:
    book: str
    status: str
    start_page: object
    end_page: object
    aadi_score: object
    ant_score: object
    note: str
    span_light: tuple = None   # (start, end) in book light text, for gap detection


def _is_index_entry(book: Book, hit: Hit) -> bool:
    """True when the matched line is followed by dot leaders and a page number."""
    end = book.light_of_key(hit.end - 1) + 1
    return bool(_INDEX_LEADER.match(book.light[end:end + 60]))


def locate(kruti, book: Book, index: BookIndex, cfg) -> list:
    """All occurrences of one Kruti in one book (empty list = not in this book)."""
    t_found, t_min = cfg["found_threshold"], cfg["min_candidate_score"]
    aq = build_query(kruti["aadi"], "aadi", cfg["query_max_chars"])
    tq = build_query(kruti["ant"], "ant", cfg["query_max_chars"])
    aadi_hits = [h for h in index.search(aq, t_min) if not _is_index_entry(book, h)]
    ant_hits = index.search(tq, t_min)

    occurrences, used_ant = [], set()
    for a in aadi_hits:
        a_page = book.page_of_key(a.start)
        after = [t for t in ant_hits
                 if t.start > a.start and id(t) not in used_ant
                 and book.page_of_key(t.end) - a_page <= cfg["max_kruti_pages"]]
        t = next((x for x in after if x.score >= t_found), after[0] if after else None)
        if t is not None:
            used_ant.add(id(t))
            end_page = book.page_of_key(t.end - 1)
            span = (book.light_of_key(a.start), book.light_of_key(t.end - 1))
            if a.score >= t_found and t.score >= t_found:
                occurrences.append(Occurrence(book.name, FOUND, a_page, end_page,
                                              a.score, t.score, "", span))
            else:
                weak = "start" if a.score < t_found else "end"
                if a.score < t_found and t.score < t_found:
                    weak = "start and end"
                occurrences.append(Occurrence(book.name, PARTIAL, a_page, end_page, a.score,
                                              t.score, f"Weak match at {weak} - verify text", span))
        elif a.score >= t_found:
            occurrences.append(Occurrence(book.name, PARTIAL, a_page, None, a.score, None,
                                          "Start found, end not found",
                                          (book.light_of_key(a.start), book.light_of_key(a.end - 1))))

    for t in ant_hits:
        if id(t) not in used_ant and t.score >= t_found:
            occurrences.append(Occurrence(book.name, PARTIAL, None, book.page_of_key(t.end - 1),
                                          None, t.score, "End found, start not found",
                                          (book.light_of_key(t.start), book.light_of_key(t.end - 1))))

    # A full match makes lone start/end hits in the same book noise
    # (typically an index page listing first lines).
    if any(o.status == FOUND for o in occurrences):
        occurrences = [o for o in occurrences if o.status == FOUND]
    return occurrences
