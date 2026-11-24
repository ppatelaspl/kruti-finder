#!/usr/bin/env python3
"""Snapshot feature 1's results, to prove a change leaves them as they were.

  python tools/feature1_snapshot.py --pair EXCEL BOOK [--pair EXCEL BOOK ...] --out DIR
      runs feature 1 once per (Excel, book) pair and writes DIR/feature1.json:
      {"<book file>": [[cell values of each row of Kruti_Results.xlsx], ...], ...}
  python tools/feature1_snapshot.py --compare A.json B.json
      exits 0 when both snapshots are equal, 1 otherwise (prints the first difference)
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openpyxl import load_workbook                    # noqa: E402

from kruti.config import merged                       # noqa: E402
from kruti.ocr_setup import configure_ocr             # noqa: E402
from kruti.pipeline import run                        # noqa: E402


def snapshot(pairs, out_dir):
    cfg = merged(None)
    configure_ocr(cfg)
    result = {}
    for excel, book in pairs:
        with tempfile.TemporaryDirectory() as tmp:
            res = run(excel, [book], tmp, cfg, log=lambda *_: None)
            ws = load_workbook(res.results_path, read_only=True).active
            result[Path(book).name] = [list(r) for r in ws.iter_rows(values_only=True)]
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    path = Path(out_dir) / "feature1.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=0, default=str), encoding="utf-8")
    print(path)


def compare(a, b):
    sa, sb = (json.loads(Path(p).read_text(encoding="utf-8")) for p in (a, b))
    if sorted(sa) != sorted(sb):
        print("different books:", sorted(sa), sorted(sb))
        return 1
    for book in sa:
        ra, rb = sa[book], sb[book]
        for i, (x, y) in enumerate(zip(ra, rb)):
            if x != y:
                print(f"{book} row {i + 1}:\n  before {x}\n  after  {y}")
                return 1
        if len(ra) != len(rb):
            print(f"{book}: {len(ra)} rows before, {len(rb)} after")
            return 1
    print("identical:", ", ".join(f"{b} ({len(sa[b])} rows)" for b in sa))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", nargs=2, action="append", metavar=("EXCEL", "BOOK"))
    ap.add_argument("--out")
    ap.add_argument("--compare", nargs=2)
    a = ap.parse_args()
    if a.compare:
        sys.exit(compare(*a.compare))
    snapshot(a.pair, a.out)


if __name__ == "__main__":
    main()
