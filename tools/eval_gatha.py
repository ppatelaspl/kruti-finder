#!/usr/bin/env python3
"""Measure Gatha Lines against hand-labelled pages (tests/gatha_truth/*.json).

  python tools/eval_gatha.py --truth tests/gatha_truth --set tune
  python tools/eval_gatha.py --truth tests/gatha_truth --set unseen    # measured once

Per book and in total it prints:
  Kruti   - labelled Kruti found as one Kruti (most of its gathas in one output Kruti,
            and that output Kruti not holding another labelled Kruti's gathas)
  Gathas  - labelled gathas found (an output row whose first or last line matches)
  First / Last - labelled gathas whose first / last line the output got right
  Extra   - output rows inside the labelled pages that match no labelled gatha
Lines match when their normalised text scores >= 85 (rapidfuzz ratio), so OCR slips
are tolerated. With --set unseen it exits 1 unless Kruti, Gathas, First and Last are
all above 90%.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rapidfuzz import fuzz                                  # noqa: E402

from kruti.normalize import light_normalize                 # noqa: E402

MATCH = 85
BAR = 0.90


def _norm(text: str) -> str:
    return " ".join(light_normalize(text).replace("॥", " ").replace("।", " ").split())


def _sim(a: str, b: str) -> float:
    return fuzz.ratio(_norm(a), _norm(b))


def score(truth: list, pred: list) -> dict:
    """truth: [{"title", "gathas": [{"first", "last", …}]}]; pred: [(kruti id, first, last)]
    for the output rows inside the labelled pages, in book order."""
    flat = [(k, g) for k, kr in enumerate(truth) for g in kr["gathas"]]
    used, match = set(), {}
    start = 0
    for t, (_, g) in enumerate(flat):
        best = None
        for j in range(start, len(pred)):
            if j in used:
                continue
            f, l = _sim(g["first"], pred[j][1]), _sim(g["last"], pred[j][2])
            s = max(f, l)
            if s >= MATCH and (best is None or s > best[0]):
                best = (s, j, f, l)
            if best and j > best[1] + 3:
                break
        if best:
            used.add(best[1])
            match[t] = best
            start = best[1] + 1
    s = Counter(kruti=len(truth), gatha=len(flat), pred=len(pred))
    s["gatha_ok"] = len(match)
    s["first_ok"] = sum(m[2] >= MATCH for m in match.values())
    s["last_ok"] = sum(m[3] >= MATCH for m in match.values())
    s["extra"] = len(pred) - len(used)
    owner = {}                                   # output Kruti -> labelled Kruti of its rows
    for t, m in match.items():
        owner.setdefault(pred[m[1]][0], set()).add(flat[t][0])
    for k, kr in enumerate(truth):
        ids = Counter(pred[match[t][1]][0] for t, (kk, _) in enumerate(flat) if kk == k and t in match)
        if not ids:
            continue
        top, n = ids.most_common(1)[0]
        if n * 2 > len(kr["gathas"]) and owner[top] == {k}:
            s["kruti_ok"] += 1
    s.setdefault("kruti_ok", 0)
    return dict(s)


def _pct(a, b):
    return a / b if b else 1.0


def run_book(label: dict, cfg) -> tuple:
    from kruti.gatha import split_gathas
    from kruti.gatha_lines import classify_book
    from kruti.layout import read_layout
    a, b = label["pages"]
    pages = read_layout(str(ROOT / label["file"]), cfg, only=set(range(a - 3, b + 4)))
    lines, _ = classify_book(pages, cfg)
    krutis = split_gathas(lines, cfg)
    pred = [(k.no, g.first, g.last) for k in krutis for g in k.gathas
            if a <= g.pages[0] and g.pages[1] <= b]
    return score(label["krutis"], pred), pred


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--truth", default=str(ROOT / "tests" / "gatha_truth"))
    ap.add_argument("--set", required=True, choices=["tune", "unseen"])
    ap.add_argument("--show", action="store_true", help="print the output rows as well")
    args = ap.parse_args()
    from kruti.gatha_lines import gatha_config
    from kruti.ocr_setup import configure_ocr
    cfg = gatha_config(None)
    configure_ocr(cfg)
    total = Counter()
    print(f"{'book':10} {'Kruti':>9} {'Gathas':>9} {'First':>9} {'Last':>9} {'Extra':>7}")
    for f in sorted(Path(args.truth).glob("*.json")):
        label = json.loads(f.read_text(encoding="utf-8"))
        if label.get("set") != args.set:
            continue
        s, pred = run_book(label, cfg)
        total.update(s)
        print(f"{f.stem:10} {s['kruti_ok']:>4}/{s['kruti']:<4} {s['gatha_ok']:>4}/{s['gatha']:<4} "
              f"{s['first_ok']:>4}/{s['gatha']:<4} {s['last_ok']:>4}/{s['gatha']:<4} "
              f"{s['extra']:>3}/{s['pred']:<3}")
        if args.show:
            for k, first, last in pred:
                print(f"     K{k} | {first}  ||  {last}")
    res = {"Kruti": _pct(total["kruti_ok"], total["kruti"]),
           "Gathas": _pct(total["gatha_ok"], total["gatha"]),
           "First": _pct(total["first_ok"], total["gatha"]),
           "Last": _pct(total["last_ok"], total["gatha"])}
    print("TOTAL  " + "  ".join(f"{k} {v:.1%}" for k, v in res.items())
          + f"  Extra {_pct(total['extra'], total['pred']):.1%}")
    if args.set == "unseen" and min(res.values()) <= BAR:
        sys.exit(1)


if __name__ == "__main__":
    main()
