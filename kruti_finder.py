#!/usr/bin/env python3
"""Kruti Finder (command line). The desktop app uses the same engine.

  python kruti_finder.py run   --excel kruti.xlsx --books ./books --out ./output
  python kruti_finder.py merge --excel kruti.xlsx \
        --results ./output/Kruti_Results.xlsx --out Kruti_Master_v2.xlsx

--books accepts one or more PDF files and/or folders.
"""
import argparse
import logging
import sys
from pathlib import Path

from kruti.config import merged
from kruti.ocr_setup import configure_ocr
from kruti.pipeline import Cancelled, merge, run

log = logging.getLogger("kruti")


def load_config(path):
    if not path or not Path(path).exists():
        return merged(None)
    import yaml
    with open(path, encoding="utf-8") as f:
        return merged(yaml.safe_load(f))


def main():
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--config", default=str(here / "config.yaml"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="Scan books and build the Excel outputs")
    r.add_argument("--excel", required=True)
    r.add_argument("--books", required=True, nargs="+", help="PDF files and/or folders")
    r.add_argument("--out", default="output")
    m = sub.add_parser("merge", help="Add approved new Kruti to a new master Excel")
    m.add_argument("--excel", required=True, help="The team's Kruti Excel")
    m.add_argument("--results", required=True, help="Reviewed Kruti_Results.xlsx")
    m.add_argument("--out", required=True)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    cfg = load_config(args.config)
    if args.cmd == "merge":
        added, total = merge(args.excel, args.results, args.out, cfg)
        log.info("Added %d approved Kruti. Master now has %d rows: %s", added, total, args.out)
        return

    status = configure_ocr(cfg)
    log.info(status["message"])
    last = [None]

    def progress(p):
        key = (p.book_index, p.stage)
        if key != last[0] and p.stage == "Reading pages":
            log.info("[%d/%d] %s (%d pages)", p.book_index, p.book_total, p.book_name,
                     p.book_pages_total)
        last[0] = key

    try:
        res = run(args.excel, args.books, args.out, cfg, on_progress=progress, log=log.info)
    except Cancelled:
        sys.exit("Cancelled.")
    except ValueError as e:
        sys.exit(str(e))
    log.info("Results: %s", res.results_path)


if __name__ == "__main__":
    main()
