#!/usr/bin/env python3
"""Build a tests/gatha_truth/<book>.json label file from a compact spec that points at
OCR lines ("page:line"), so the labelled text is exactly the OCR text at that place.

  python tools/make_gatha_truth.py SPEC.py OUT.json

SPEC.py defines SET, FILE, PAGES = (from, to) and KRUTIS = [(title, [gatha, …]), …],
where a gatha is ("p:i", "p:j") for its first and last line. For a line that holds
several gathas, "p:i>TEXT" is the part of line p:i after TEXT and "p:i<TEXT" the part up
to and including TEXT; "A + B" joins two such pieces with a space; "=text" is literal.
Helper: regular(page, first_line, n, per=2) -> n gathas of `per` lines each.
"""
import json
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kruti.gatha_lines import gatha_config    # noqa: E402
from kruti.layout import read_layout          # noqa: E402


def regular(page, first_line, n, per=2):
    return [(f"{page}:{first_line + per * i}", f"{page}:{first_line + per * i + per - 1}")
            for i in range(n)]


def main(spec_path, out):
    spec = runpy.run_path(spec_path, init_globals={"regular": regular})
    cfg = gatha_config(None)
    a, b = spec["PAGES"]
    pages = {p.page: p for p in read_layout(str(ROOT / spec["FILE"]), cfg, only=set(range(a, b + 1)))}

    def text(ref):
        if ref.startswith("="):
            return ref[1:]
        if " + " in ref:
            return " ".join(text(r) for r in ref.split(" + "))
        for sep in (">", "<"):
            if sep in ref:
                base, cut = ref.split(sep, 1)
                line = text(base)
                k = line.index(cut)
                return (line[k + len(cut):] if sep == ">" else line[:k + len(cut)]).strip()
        pg, i = ref.split(":")
        return pages[int(pg)].lines[int(i)].text

    krutis = [{"title": title, "gathas": [{"no": str(n), "first": text(f), "last": text(l)}
                                          for n, (f, l) in enumerate(gs, 1)]}
              for title, gs in spec["KRUTIS"]]
    data = {"set": spec["SET"], "file": spec["FILE"], "pages": [a, b], "krutis": krutis}
    Path(out).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(out, len(krutis), "Kruti,", sum(len(k["gathas"]) for k in krutis), "gathas")


if __name__ == "__main__":
    main(*sys.argv[1:3])
