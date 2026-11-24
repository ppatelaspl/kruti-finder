#!/usr/bin/env python3
"""Gatha Lines (command line). The desktop app's "Gatha Lines" tab uses the same engine.

  python gatha_finder.py --books ./books --out ./output

--books accepts one or more PDF files and/or folders. Writes output/Gatha_Results.xlsx:
one row per gatha of every Kruti found, with its first and last line.
"""
import argparse
import logging
import sys
from pathlib import Path

from kruti.gatha_lines import GATHA_DEFAULTS, gatha_config
from kruti.gatha_pipeline import run_gatha
from kruti.ocr_setup import configure_ocr
from kruti.pipeline import Cancelled

log = logging.getLogger("kruti")


def load_config(path):
    """config.yaml (feature 1's keys, plus any of this feature's own) over the defaults."""
    if not path or not Path(path).exists():
        return gatha_config(None)
    import yaml
    with open(path, encoding="utf-8") as f:
        return gatha_config(yaml.safe_load(f))


def main():
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--config", default=str(here / "config.yaml"))
    ap.add_argument("--books", required=True, nargs="+", help="PDF files and/or folders")
    ap.add_argument("--out", default="output")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    cfg = load_config(args.config)
    cfg.setdefault("layout_cache_dir", GATHA_DEFAULTS["layout_cache_dir"])
    log.info(configure_ocr(cfg)["message"])
    last = [None]

    def progress(p):
        key = (p.book_index, p.stage)
        if key != last[0] and p.stage == "Reading pages":
            log.info("[%d/%d] %s (%d pages)", p.book_index, p.book_total, p.book_name,
                     p.book_pages_total)
        last[0] = key

    try:
        res = run_gatha(args.books, args.out, cfg, on_progress=progress, log=log.info)
    except Cancelled:
        sys.exit("Cancelled.")
    except ValueError as e:
        sys.exit(str(e))
    log.info("Results: %s", res.results_path)


if __name__ == "__main__":
    main()
