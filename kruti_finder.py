#!/usr/bin/env python3
"""Kruti Finder (command line). The desktop app uses the same engine.

  python kruti_finder.py --excel kruti.xlsx --books ./books --out ./output

--books accepts one or more PDF files and/or folders. Writes output/Kruti_Results.xlsx:
every Kruti found in the books, flagged as in the Excel (same/other script) or new.
"""
import argparse
import logging
import sys
from pathlib import Path

from kruti.config import merged
from kruti.ocr_setup import configure_ocr
from kruti.pipeline import Cancelled, run

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
    ap.add_argument("--excel", required=True, help="The team's Kruti Excel")
    ap.add_argument("--books", required=True, nargs="+", help="PDF files and/or folders")
    ap.add_argument("--out", default="output")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    cfg = load_config(args.config)

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
