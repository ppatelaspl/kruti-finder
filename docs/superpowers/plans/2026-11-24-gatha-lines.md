# Gatha Lines Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a second, fully offline option, "Gatha Lines", to Kruti Finder. It lists every
multi-gatha Kruti in PDF books with one Excel row per gatha (first and last line), without
changing feature 1.

**Architecture:**
- New engine modules in `kruti/` read each page as lines with positions (text layer or
  Tesseract), into a separate layout cache.
- Each line is classed (verse / prose / heading / part / tune / note / furniture). Lines are
  then grouped into Kruti and gathas, and the result is written to `Gatha_Results.xlsx`.
- A new tab in the existing window, and a new CLI script, drive it.
- Feature 1 modules are only imported, never edited.

**Tech Stack:** Python 3.12, PyMuPDF, pytesseract + bundled Tesseract, rapidfuzz, openpyxl,
PySide6 6.7.3, pytest.

**Spec:** `docs/superpowers/specs/2026-11-24-gatha-lines-design.md`

## Global Constraints

- Completely offline. No network calls and no new dependencies (`requirements.txt` and
  `packaging/requirements-build.txt` unchanged).
- Do not edit `kruti/krutis.py`, `kruti/matcher.py`, `kruti/pipeline.py`, `kruti/report.py`,
  `kruti/extract.py`, `kruti/config.py`, `kruti/normalize.py` or `kruti_finder.py`. Import
  from them only. `app/window.py` changes only to host tabs; `app/worker.py` only gains a
  class.
- Feature 1's `Kruti_Results.xlsx` on the sample books must be byte-for-byte identical in
  content (cell values) before and after.
- Version `1.1.0` in `app/version.py`.
- Output file `Gatha_Results.xlsx`, sheet `Gatha Lines`, columns in exactly this order:
  `File Name, Book Name, Kruti No., Kruti Name, Part, Gatha No., Total Gathas, First Line,
  Last Line, PDF Page, Book Page, Script, Text Source, OCR Confidence %, How found,
  Confidence, Check, Remarks`.
- `How found` values: `Numbered verse`, `Number inferred (OCR garbled)`, `No number - gap`,
  `No number - line count`.
- `Confidence` values: `High`, `Medium`, `Low`.
- A Kruti with fewer than 2 gathas is not listed.
- Tune, raga, metre and refrain-marker lines are never part of a gatha.
- Explanations between gathas are skipped, and the Kruti continues.
- First and last lines are copied from the read text, in the book's own script. Gujarati
  stays Gujarati, and there is no Devanagari conversion in the output.
- Same OCR settings as feature 1 (`tesseract_langs`, `ocr_dpi`, `ocr_workers`, and the
  same rules for when to OCR a page).
- Pass bar: more than 90% on unseen books for Kruti identified, gathas identified, and
  first/last line correct (fuzzy ratio ≥ 85).

## Review Focus

1. **Several gathas run together on one printed or OCR line** ("…वंदो ॥1॥ विश्वसेन … ॥2॥"):
   each verse mark ends a gatha mid-line. The split pieces become the gathas' lines; one
   line is never shared whole by two gathas. *(Task 3 test
   `test_run_on_line_splits_at_marks`.)*
2. **Two-column pages** (gathas printed in left and right columns): lines are read column
   by column, not across. *(Task 1 test `test_two_columns_read_in_column_order`.)*
3. **Gujarati book:** output text stays in Gujarati, and Gujarati digits (૧૨) and dandas
   count as verse numbers. *(Task 3 test `test_gujarati_numbers_and_script_kept`.)*
4. **Cancel mid-book, then Start again:** the layout cache resumes, and a half-written last
   cache line is ignored. *(Task 1 test `test_cache_ignores_torn_last_line`.)*
5. **A book with no Kruti, or an unreadable PDF:** the run finishes, the Excel is written
   with headers only, and the file is listed as skipped or with 0 Kruti in the log.
   *(Task 5 test `test_run_with_no_kruti_writes_header_only`.)*

---

### Task 0: Environment and feature-1 baseline

**Files:**
- Create: `tools/feature1_snapshot.py`
- Create: `.venv/` (not committed; add `.venv/` to `.gitignore`)

**Interfaces:**
- Produces: `python tools/feature1_snapshot.py --excel X --books B... --out DIR` writes
  `DIR/feature1.json`: the list of row value lists of `Kruti_Results.xlsx`.
  `--compare A.json B.json` exits 0 if they are equal and 1 otherwise, printing the first
  difference.

- [ ] **Step 1:** `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest`.
  Run `PATH=$PWD/vendor/tesseract:$PATH .venv/bin/python -m pytest -q tests`. Expected: the
  existing tests pass. (If `vendor/tesseract` has no binary, use
  `packaging/macos/build_tesseract.sh` or Homebrew Tesseract, and record which one.)
- [ ] **Step 2:** Write `tools/feature1_snapshot.py`. It calls `kruti.pipeline.run` and dumps
  the cell values.
- [ ] **Step 3:** Run it, **in the background**, on the 3 books in `test-results/`
  (`B000505_book.pdf`, `B002637_book.pdf`, `B052034_book.pdf`) with their
  `*_Gitarth Ganga.xlsx`. Save to `test-results/baseline/`. Each book's own Excel is run
  separately.
- [ ] **Step 4:** Commit: `git add tools/feature1_snapshot.py .gitignore && git commit -m "Feature 1 output snapshot tool"`.

### Task 1: Page layout reader and cache (`kruti/layout.py`)

**Files:**
- Create: `kruti/layout.py`
- Test: `tests/test_gatha_layout.py`

**Interfaces:**
- Consumes: `kruti.extract._text_layer_is_usable(text, cfg)`, `_share_cores(workers)`, and
  `page_count`. `kruti.ocr_setup` has already configured `pytesseract`.
- Produces:
  ```python
  @dataclass
  class Line:
      text: str; x0: float; y0: float; x1: float; y1: float   # page units, 0..width/height
      conf: float                                               # 0-100; 100 for text layer
      block: int = 0; par: int = 0
  @dataclass
  class PageLayout:
      page: int; source: str; confidence: float; width: float; height: float
      lines: list[Line]
  LAYOUT_CACHE_VERSION = 1
  def lines_from_tesseract(data: dict, scale: float) -> list[Line]
  def lines_from_text_dict(d: dict) -> list[Line]
  def order_lines(lines: list[Line], width: float) -> list[Line]
  def read_layout(pdf_path: str, cfg: dict, on_page=None, checkpoint=None) -> list[PageLayout]
  ```
  - `on_page(done, total, source)` and `checkpoint()` have the same meaning as in
    `extract_book`.
  - The cache lives in `cfg["layout_cache_dir"]`. It uses the same identity fields as
    `extract._cache_path` plus `LAYOUT_CACHE_VERSION`, one JSONL row per page.

- [ ] **Step 1: Write failing tests**
  - `test_tesseract_words_grouped_into_lines`: a fake `image_to_data` dict (two lines, three
    words, with `left/top/width/height/conf/block_num/par_num/line_num`) gives 2 `Line`s with
    the words joined by spaces, a box that covers them, and `conf` = the mean of the
    non-negative word confs. Coordinates are divided by `scale` (`dpi/72`).
  - `test_text_dict_spans_joined_per_line`: a fake `get_text("dict")` structure (blocks →
    lines → spans) gives one `Line` per dict line, with `conf == 100`.
  - `test_same_row_fragments_merged`: two `Line`s whose vertical ranges overlap by more than
    50% and with `x1` of the first ≤ `x0` of the second are merged into one by
    `order_lines`, joined with a space. This is the spec's "one printed row = one line".
  - `test_two_columns_read_in_column_order`: lines at x0=50 and x0=320 on a 600-wide page,
    interleaved by y, with a clear empty vertical gutter, come out as all left-column lines
    (top→bottom), then all right-column lines.
  - `test_cache_ignores_torn_last_line`: write two good JSONL rows plus `{"page": 3, "sou`.
    The cache reader returns pages 1-2.
- [ ] **Step 2:** Run `.venv/bin/python -m pytest tests/test_gatha_layout.py -v`. Expected:
  FAIL (module missing).
- [ ] **Step 3:** Implement `kruti/layout.py`.
  - The decision to OCR a page is the same as in `extract_book`: text layer if
    `_text_layer_is_usable`, blank if there is no text, images or drawings, otherwise
    render at `cfg["ocr_dpi"]` and OCR with
    `pytesseract.image_to_data(..., lang=cfg["tesseract_langs"], output_type=DICT)`.
  - Use a ThreadPoolExecutor with `cfg["ocr_workers"]` and the same bounded `pending`
    deque pattern.
  - `order_lines`:
    - Merge same-row fragments.
    - Detect two columns: more than 30% of lines start right of `0.45*width`, and no line
      crosses the `[0.45, 0.55]*width` band.
    - Sort by (column, y0).
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit: `git commit -m "Gatha: read pages as positioned lines, with cache"`.

### Task 2: Line classes (`kruti/gatha_lines.py`)

**Files:**
- Create: `kruti/gatha_lines.py`
- Test: `tests/test_gatha_lines.py`

**Interfaces:**
- Consumes: `Line` and `PageLayout` (Task 1). From `kruti.matcher`, `_running_lines`,
  `_is_page_furniture`, `_page_number_candidates` and `_printed_page_numbers`. From
  `kruti.normalize`, `light_normalize`, `key_only` and `script_of`. From `kruti.krutis`,
  `_part_heading`, `_Parts`, `_ends_with_type`, `_plausible_title` and `verse_pattern`.
  From `kruti.config`, `merged`.
- Produces:
  ```python
  KINDS = ("verse", "prose", "heading", "part", "tune", "note", "list", "furniture")
  @dataclass
  class TLine:                       # one line in reading order across the whole book
      page: int; text: str           # text as read (own script)
      light: str                     # light_normalize(text), for rules only
      kind: str; conf: float; source: str
      gap_above: float               # vertical gap to previous line on page / median line height
      indent: float                  # (x0 - page text left) / text width
      fill: float                    # (x1 - x0) / page text width
      marks: list                    # [(end_offset_in_text, number_or_None)] verse marks on this line
  GATHA_DEFAULTS: dict               # all named thresholds; merged over kruti.config DEFAULTS
  def gatha_config(overrides: dict | None) -> dict
  def classify_book(pages: list[PageLayout], cfg: dict) -> tuple[list[TLine], dict]  # (lines, printed page map)
  ```

- [ ] **Step 1: Write failing tests.** The helper `page(rows)` builds a `PageLayout` from
  `(text, x0, x1, y0)` tuples on a 600x800 page.
  - `test_header_and_page_number_removed`: the same short top line on 5 pages, and "12" as
    the bottom line, are classed `furniture`. The printed page map gives PDF page → book
    page.
  - `test_short_lines_ending_in_danda_are_verse`: 4 lines with fill ≈ 0.5 ending `,` `॥1॥`
    `,` `॥2॥` are `verse`.
  - `test_full_width_wrapped_prose_is_prose`: 5 lines with fill ≥ 0.92, no line-end
    punctuation, containing `है`/`छे`, are `prose`.
  - `test_explanation_opener_is_prose`: `भावार्थ- …` and `अर्थ: …` paragraphs are `prose`,
    even if a line is short.
  - `test_tune_line_is_tune`: `राग - आशावरी`, `( मालिनी-छन्दः )`, `… -ए देशी`, `आंकणी`,
    `टेक` and `ध्रुवपद` lines are `tune`.
  - `test_part_heading_is_part`: `ढाल बीजी`, `दुहा` and `कलश` are `part`.
  - `test_kruti_heading_is_heading`: `शांतिनाथ स्तवन` (short, centred, ends in a
    title_keyword) is `heading`.
  - `test_index_page_is_list`: 10 lines, each ending in a page number with dot leaders,
    or under `अनुक्रमणिका`, are `list`.
  - `test_source_note_is_note`: `(खरतरगच्छ साहित्य कोश क्रमांक- 2592.)` is `note`.
  - `test_one_odd_line_smoothed`: a single full-width line in the middle of 8 verse lines
    stays `verse`.
  - `test_gujarati_numbers_and_script_kept` (part 1): `૧`-style digits and Gujarati text are
    classed `verse` with `marks` numbers parsed. `text` stays Gujarati.
- [ ] **Step 2:** Run `.venv/bin/python -m pytest tests/test_gatha_lines.py -v`. Expected:
  FAIL.
- [ ] **Step 3: Implement.**
  - Furniture comes from the matcher helpers, applied to page edge lines.
  - Verse marks come from `verse_pattern(book_light, pages)` on each line's `light`.
  - Each feature has a named threshold in `GATHA_DEFAULTS`, with these starting values:
    - `prose_fill` 0.9
    - `verse_fill_max` 0.8
    - `prose_words`, starting from the 1.0.9 README words: है, था, किया, छे, हतो, करवामां,
      plus the explanation openers व्याख्या, अर्थ, भावार्थ, बालावबोध, टीका
    - `tune_words`: राग, देशी, छन्द, छंद, आंकणी, टेक, ध्रुवपद
    - `index_headings`: अनुक्रमणिका, विषयानुक्रम, सूची
    - `smooth_window` 2
  - Smoothing: a line whose kind differs from both of its 2 neighbours on each side (all of
    the same kind) takes their kind, except `heading`, `part` and `tune`.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit: `git commit -m "Gatha: class each line as verse, prose, heading, tune, part, note, list or furniture"`.

### Task 3: Kruti and gatha segmentation (`kruti/gatha.py`)

**Files:**
- Create: `kruti/gatha.py`
- Test: `tests/test_gatha_split.py`

**Interfaces:**
- Consumes: `TLine` and `classify_book` (Task 2).
- Produces:
  ```python
  @dataclass
  class Gatha:
      part: str; no: str               # printed number, or "(n)" when unnumbered
      first: str; last: str            # text as read; last includes its verse mark if printed
      pages: tuple                     # (first_page, last_page)
      how: str                         # one of the four How-found values
      conf: float                      # mean OCR conf of its lines
      source: str                      # "Text layer" / "OCR" / "Text layer + OCR"
      checks: list
  @dataclass
  class GKruti:
      no: int; title: str; gathas: list[Gatha]; checks: list
  def split_gathas(lines: list[TLine], cfg: dict) -> list[GKruti]
  def confidence(g: Gatha, low_ocr: float) -> str     # "High"/"Medium"/"Low"
  ```

- [ ] **Step 1: Write failing tests**, built from `TLine` lists with a small helper.
  - `test_numbered_gathas_first_and_last_line`: a heading, then 3 gathas of 2 lines each
    ending `॥1॥ ॥2॥ ॥3॥`. This gives 1 Kruti with the heading as title and 3 gathas;
    gatha 2's `first` is its line 1 and its `last` is the line with `॥2॥`. `how ==
    "Numbered verse"`.
  - `test_tune_line_not_in_gatha_one`: heading, `राग - आशावरी` (tune), then verses. Gatha 1's
    `first` is the first verse line.
  - `test_explanation_between_gathas_skipped`: gatha 1, prose `भावार्थ…` ×3, gatha 2, prose,
    gatha 3. This gives **one** Kruti with 3 gathas.
  - `test_quoted_verse_inside_explanation_ignored`: a prose paragraph containing
    `“… ॥2॥”` inline does not add a gatha or break the sequence.
  - `test_restart_at_one_starts_new_kruti`: `॥1॥ ॥2॥ ॥3॥ ॥1॥ ॥2॥`, with no part heading,
    gives 2 Kruti.
  - `test_part_heading_keeps_kruti`: `॥1॥ ॥2॥`, then `ढाल बीजी`, then `॥1॥ ॥2॥`, gives 1
    Kruti with 4 gathas. `part` is "" for the first two and "ढाल बीजी" for the last two.
  - `test_garbled_number_inferred`: marks `1, None, 3`. Gatha 2 has `no == "2"` and `how ==
    "Number inferred (OCR garbled)"`.
  - `test_unnumbered_by_gap`: 8 verse lines with `gap_above` ≥ 1.0 before lines 1, 3, 5 and
    7 (otherwise about 0.3) give 4 gathas `"(1)".."(4)"` with `how == "No number - gap"`.
  - `test_unnumbered_by_line_count`: 8 verse lines, no gaps, ending `, ; , ॥ , ; , ॥`, give
    2 gathas of 4 lines with `how == "No number - line count"`.
  - `test_run_on_line_splits_at_marks`: one line `"अ ब क ॥1॥ ड ए फ ॥2॥ ग ह इ ॥3॥"`. This
    gives 3 gathas whose `first == last ==` the piece of text up to and including each
    mark.
  - `test_gatha_across_pages`: a gatha whose first line is on page 4 and its mark on page
    5 has `pages == (4, 5)` and the check `crosses pages`.
  - `test_single_gatha_kruti_dropped`: a heading plus one verse gives no Kruti.
  - `test_gujarati_numbers_and_script_kept` (part 2): Gujarati gathas `॥૧॥ ॥૨॥` give
    `no == "1","2"`, and `first`/`last` are in Gujarati.
  - `test_confidence_levels`:
    - numbered with conf 95 and no checks → High;
    - gap-based → Medium;
    - line count → Low;
    - numbered with conf 60 → Low;
    - numbered with 2 checks → Low.
- [ ] **Step 2:** Run `.venv/bin/python -m pytest tests/test_gatha_split.py -v`. Expected:
  FAIL.
- [ ] **Step 3: Implement `split_gathas`.**
  - Walk the lines in order and keep only `verse`, `heading` and `part`. `tune`, `note`,
    `list` and `furniture` are dropped. `prose` is dropped, but it is remembered as an
    "explanation run".
  - A Kruti ends at:
    - a `heading` line;
    - a verse number restart to 1 without a preceding `part`;
    - an explanation run longer than `cfg["max_explanation_pages"]` (default 3) with no
      continuing verse number after it.
  - Gathas:
    - Numbered: cut after each verse mark, splitting run-on lines at the mark offsets.
    - Unnumbered: cut before lines with `gap_above ≥ cfg["gatha_gap"]` (default 0.8). If
      no gaps exist, use the dominant cycle of lines-per-gatha (2 or 4) confirmed by
      `॥`/`;` line ends.
  - Number inference follows feature 1: a `None` mark between n-1 and n+1 becomes n.
  - Check strings:
    - `no heading`
    - `low OCR`
    - `inferred break`
    - `one-line gatha`
    - `long gatha` (more than `cfg["long_gatha_lines"]` = 8 lines)
    - `crosses pages`
    - `next to prose`
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit: `git commit -m "Gatha: split Kruti into gathas (numbered, inferred, unnumbered)"`.

### Task 4: Excel writer (`kruti/gatha_report.py`)

**Files:**
- Create: `kruti/gatha_report.py`
- Test: `tests/test_gatha_report.py`

**Interfaces:**
- Consumes: `kruti.report._table`, `FONT`, `RED`, `GOLD`, `ORANGE`, `PINK` and `NAVY`.
  `GKruti` and `Gatha` (Task 3).
- Produces: `GATHA_FILE = "Gatha_Results.xlsx"`, `GATHA_SHEET = "Gatha Lines"`,
  `GATHA_COLUMNS` (exact list from Global Constraints), and
  `write_gatha_results(path: str, books: list[tuple[str, str, dict, list[GKruti]]]) -> int`.
  - Each tuple is `(file_name, book_name, printed_page_map, krutis)`. The function returns
    the number of rows written.

- [ ] **Step 1: Write a failing test**, `test_columns_rows_and_pages`. Write 1 book, 2 Kruti
  (2 and 3 gathas) and a printed map `{4: 12, 5: 13}`, then read it back with openpyxl.
  - The header equals `GATHA_COLUMNS` and there are 5 data rows.
  - The row for a gatha with pages (4, 5) has `PDF Page == "4-5"` and
    `Book Page == "12-13"`. The row for page 4 has `PDF Page == 4` and `Book Page == 12`.
  - `Total Gathas` is 2 or 3 per Kruti.
  - `Check == "OK"` when there are no checks.
  - `Confidence` cells have fills: High = GOLD, Medium = ORANGE, Low = PINK.
- [ ] **Step 2:** Run it. Expected: FAIL.
- [ ] **Step 3: Implement.** Use `_table(..., group_col=<Kruti key column>,
  input_cols=(Remarks,))`. Shade blocks per (file, Kruti No.) by grouping on a hidden key,
  or pass `group_col` = "Kruti No." after sorting by file. Check is in bold RED when not OK.
  Widths: names 30, lines 48, the rest 8-14.
- [ ] **Step 4:** Run it. Expected: PASS.
- [ ] **Step 5:** Commit: `git commit -m "Gatha: write Gatha_Results.xlsx"`.

### Task 5: Gatha pipeline and CLI (`kruti/gatha_pipeline.py`, `gatha_finder.py`)

**Files:**
- Create: `kruti/gatha_pipeline.py`, `gatha_finder.py`
- Test: `tests/test_gatha_pipeline.py`

**Interfaces:**
- Consumes: `kruti.pipeline.Controller`, `Cancelled`, `Progress`, `collect_pdfs` and
  `book_name`. `read_layout` (Task 1), `classify_book` and `gatha_config` (Task 2),
  `split_gathas` (Task 3) and `write_gatha_results` (Task 4).
- Produces:
  ```python
  @dataclass
  class GathaResult:
      results_path: str; books: int; krutis: int; gathas: int; skipped: list
  def run_gatha(inputs, out_dir, cfg, on_progress=None, log=print, ctl=None) -> GathaResult
  ```
  - `Progress.kruti_found` carries the Kruti count. The gatha count goes in a new attribute
    set on the same object, `prog.gathas_found` (set with `setattr`; `Progress` itself is
    not edited).
  - CLI: `python gatha_finder.py --books ... --out DIR [--config config.yaml]`. Config
    keys are read with the same loader as `kruti_finder.load_config`, which is imported.

- [ ] **Step 1: Write failing tests**, with `read_layout` monkeypatched to return synthetic
  pages.
  - `test_run_writes_excel_and_counts`: 1 book with 2 Kruti gives a `GathaResult` with the
    counts, and the file exists.
  - `test_run_with_no_kruti_writes_header_only`: a book of only prose, plus one unreadable
    path, gives an Excel with only the header row. The unreadable file is in `skipped`.
  - `test_cancel_raises`: `ctl.cancel()` before the run → `Cancelled`.
- [ ] **Step 2:** Run them. Expected: FAIL.
- [ ] **Step 3:** Implement. The loop structure mirrors `kruti.pipeline.run`: count pages,
  run per book, ETA by moving average, `emit` throttled at 0.15 s. Stages: `"Reading
  pages"`, `"Finding gathas"`, `"Writing Excel file"`, `"Done"`. The log line per book is
  `[n/N] name: P pages, K Kruti, G gathas`. `cfg["layout_cache_dir"]` defaults to
  `.kruti_layout_cache` (add it to `.gitignore`).
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit: `git commit -m "Gatha: pipeline and command line"`.

### Task 6: Ground truth and accuracy tool

**Files:**
- Create: `tools/eval_gatha.py`, `tests/gatha_truth/README.md`, `tests/gatha_truth/<book>.json`
  (labels; small text, committed)

**Interfaces:**
- Produces:
  - Label format: `{"file": "...pdf", "pages": [from, to], "krutis": [{"title": "...",
    "gathas": [{"part": "", "no": "1", "first": "...", "last": "..."}]}]}`.
  - `python tools/eval_gatha.py --truth tests/gatha_truth --books kruti-samples --set tune|unseen`
    prints, per book and in total:
    - Kruti recall and precision, matched by title fuzz ≥ 80 or first-gatha `first` fuzz ≥ 85;
    - gatha recall and precision, within matched Kruti, by order;
    - first-line and last-line accuracy (fuzz ratio ≥ 85 on `light_normalize`d text);
    - the share of output rows inside labelled pages that match no truth gatha (non-Kruti
      leaked).
  - It exits 1 if any of the three main scores is ≤ 90% on `--set unseen`.

- [ ] **Step 1: Choose the books.** Pick 8 books from `kruti-samples/`:
  - at least one with explanations between gathas (search the OCR text for भावार्थ/अर्थ);
  - one without verse numbers;
  - one with ढाल parts;
  - one Gujarati;
  - one text-layer book.

  Assign 4 to `tune` and 4 to `unseen`. Write the split into `tests/gatha_truth/README.md`
  **before** looking at any output.
- [ ] **Step 2: Label.** For each book, take 5-8 pages that contain Kruti, preface and
  explanation. Render them with PyMuPDF to PNG in the scratchpad and read the page images
  (not the OCR). Write the labels. About 20+ pages per set.
- [ ] **Step 3:** Write `tools/eval_gatha.py`, with `pytest`-style unit checks of its scoring
  on a tiny truth/prediction pair, in `tests/test_gatha_eval.py`.
- [ ] **Step 4:** Commit: `git commit -m "Gatha: ground truth labels and accuracy tool"`.

### Task 7: Tune on the tuning set, then measure on the unseen set

**Files:**
- Modify: `kruti/gatha_lines.py` (`GATHA_DEFAULTS` and rules), `kruti/gatha.py`
- Test: add a unit test to `tests/test_gatha_lines.py` or `tests/test_gatha_split.py` for
  each rule changed or added

- [ ] **Step 1:** OCR the 8 books' labelled pages into the layout cache **in the
  background**, using the vendored Tesseract. Hand back while it runs.
- [ ] **Step 2:** Run `eval_gatha.py --set tune`. For each miss, find the cause (line class,
  split or OCR), fix the rule, add a unit test reproducing it, and re-run. Stop when the
  tune set is above 90% on all three scores.
- [ ] **Step 3:** Run `eval_gatha.py --set unseen` **once**. Record the scores in the commit
  message and in `tests/gatha_truth/README.md`.
  - If it is ≤ 90%, the work is not done. Report the scores and misses to the user before
    any further tuning. Do not tune on the unseen books silently.
- [ ] **Step 4:** Run the whole suite: `.venv/bin/python -m pytest -q tests`. Expected: all
  pass.
- [ ] **Step 5:** Commit: `git commit -m "Gatha: tuned rules; unseen-set accuracy K/G/L = …"`.

### Task 8: App tab, worker, version and docs

**Files:**
- Create: `app/gatha_tab.py`
- Modify: `app/worker.py` (add `GathaWorker` only), `app/window.py` (host a `QTabWidget`,
  run lock, close handling, header subtitle), `app/version.py` (`1.1.0`), `README.md`
  (new "Gatha Lines" section), `INSTALL.md` (Using the app: the second tab),
  `docs/superpowers/specs/2026-11-24-gatha-lines-design.md` (CLI is `gatha_finder.py`, not
  a `kruti_finder.py` sub-command, so that feature 1's CLI file stays unedited)
- Test: `tests/test_gatha_app.py` (`QT_QPA_PLATFORM=offscreen`)

**Interfaces:**
- Consumes: `run_gatha` and `GathaResult` (Task 5).
- Produces:
  - `class GathaWorker(QObject)`: the same signals as `RunWorker`. Its constructor is
    `(inputs, out_dir, cfg)` and it calls `run_gatha`.
  - `class GathaTab(QWidget)`: built from the same widgets as `_find_tab`, with
    `BooksList` reused from `app.window`. It has its own QSettings keys (`gatha/books`,
    `gatha/out`) and a `busy_changed = Signal(bool)`. `set_locked(bool)` disables Start
    while the other tab runs. Its stats are Elapsed, Time left, Pages OCR'd, Kruti found
    and Gathas found. Its Advanced settings are Parallel OCR jobs (the shared `workers`
    setting) and "Clear saved layout results" (`<data dir>/layout_cache`).
  - `MainWindow`:
    - its tabs are "Find Kruti (Excel match)", holding the unchanged `_find_tab()` page,
      and "Gatha Lines";
    - feature 1 start/finish emits busy to lock the other tab;
    - `closeEvent` stops whichever worker runs;
    - the subtitle reads "Read the books · list every Kruti · match the Excel or list
      each gatha".

- [ ] **Step 1: Write a failing test.** `test_tabs_and_lock`: create `MainWindow`. It has 2
  tabs with those titles. Calling `gatha_tab.set_locked(True)` disables its Start button.
  Feature 1's widgets (`excel_edit`, `start_btn`) still exist on tab 0.
- [ ] **Step 2:** Run it. Expected: FAIL.
- [ ] **Step 3:** Implement `app/gatha_tab.py`, `GathaWorker` and the window changes.
  `_config()` for the gatha tab is
  `gatha_config({"ocr_workers": …, "layout_cache_dir": str(data_dir() / "layout_cache")})`.
  The finish dialog reads `"Finished N books.\n\nK Kruti found, G gathas."`, plus the
  skipped note.
- [ ] **Step 4:** Run it. Expected: PASS. Then launch the app (`.venv/bin/pip install
  pyside6==6.7.3`, `python app/main.py`), run the Gatha tab on one sample book, and check
  that progress, pause/resume, cancel/restart and "Open results" all work. Take a
  screenshot.
- [ ] **Step 5:** Commit: `git commit -m "v1.1.0: Gatha Lines tab"`.

### Task 9: Feature 1 regression and packaging check

- [ ] **Step 1:** Re-run `tools/feature1_snapshot.py` on the same 3 books (in the
  background). Run `--compare test-results/baseline/feature1.json <new>`. Expected: exit 0.
- [ ] **Step 2:** `pyinstaller packaging/kruti_finder.spec --noconfirm`, then run the
  packaged app's `--selftest`. Expected: exit 0. Check that `kruti.gatha*` modules are
  bundled (add them to `hiddenimports` only if they are missing).
- [ ] **Step 3:** Run the full tests. Commit any packaging fix. Do **not** push or tag.
  Pushing `main` builds installers, and tagging `v1.1.0` publishes a Release. Both need the
  user's go-ahead.
