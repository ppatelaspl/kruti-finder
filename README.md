# Kruti Finder

Kruti Finder reads PDF books (scanned or not) and lists **every Kruti it finds**, with the file and book name, title, Aadi Vakya, Ant Vakya and start/end page. Each Kruti is compared with the team's Kruti Excel and flagged:

- **Matched - same script:** in the Excel, printed in the same script (Devanagari or Gujarati) as the Excel entry;
- **Matched - other script:** in the Excel, but this book prints it in the other script;
- **New:** not in the Excel.

The same Kruti in several books, places or scripts shares one **Group ID**.

## Desktop app

Kruti Finder is a desktop app for **Windows 10/11, macOS (Apple silicon) and Ubuntu / Linux Mint / Debian**, with OCR built in.

- **Installing:** see [INSTALL.md](INSTALL.md).
- **Building the installers:** see [BUILD.md](BUILD.md). GitHub builds all three automatically.

The command-line version described below uses the same engine and gives identical results.

## How it works

1. **Read each page.** If the PDF has a proper Unicode text layer it is used directly. If the page is a scan, or the text layer is garbage (old legacy Gujarati/Hindi fonts, broken conjuncts), the page is OCR'd. OCR results are cached, so a stopped or repeated run never OCRs the same page twice.
2. **Clean up.** Running headers, footers and page numbers are removed, so they never leak into the Vakya text or break a Kruti that crosses a page.
3. **Split into Kruti.** A new Kruti starts wherever verse numbers restart at ॥1॥, or at a heading ending in a Kruti-type word (स्तवन, सज्झाय, गीत, पद …; configurable in `title_keywords`). Numbers garbled by OCR (॥[॥) are inferred from the sequence. For each Kruti the tool records:
   - **Title:** the heading lines above verse 1;
   - **Aadi Vakya:** the first verse;
   - **Ant Vakya:** the last verse;
   - **pages** and **number of verses**.
4. **Compare with the Excel.** Gujarati is converted to Devanagari and common spelling variants are treated as equal (ण/न, श/ष/स, ब/व, ी/ि …); the Excel's `#…#` markers and `{variant}` readings are ignored. Each Excel Kruti's Aadi Vakya and Ant Vakya are searched in the book with a fuzzy match, so OCR mistakes are tolerated (both must match ≥ 85%, in order, within 40 pages). A Kruti from the book that such a match covers gets the Excel's Kruti क्रमांक and name, and a *same script* or *other script* flag. An Excel Kruti matched in a book where no verse numbers split it out is still listed.
5. **Group copies.** Rows matched to the same Excel Kruti share a Group ID; new Kruti join the group whose text is most alike, across scripts.

## Command line: setup (one time)

Python 3.10+ is required.

```bash
pip install -r requirements.txt
```

Install Tesseract OCR with the Hindi, Gujarati and Sanskrit languages:

- **Windows:** use the UB-Mannheim installer (github.com/UB-Mannheim/tesseract/wiki). Tick *Hindi, Gujarati, Sanskrit* under "Additional language data". If `tesseract` is not on PATH, set `tesseract_cmd` in `config.yaml`.
- **Mac:** `brew install tesseract tesseract-lang`
- **Ubuntu:** `sudo apt install tesseract-ocr tesseract-ocr-hin tesseract-ocr-guj tesseract-ocr-san`

## Run

```bash
python kruti_finder.py --excel Kruti_Master.xlsx --books "D:\Books" --out output
```

`--books` takes PDF files and/or folders (sub-folders included). It writes one file: **`output/Kruti_Results.xlsx`**.

## Output: `Kruti_Results.xlsx`

One sheet, **Kruti Found**, one row per Kruti found in a book:

| Column | Meaning |
|---|---|
| Group No., Copy | The same Kruti in several books, places or scripts shares a Group No. (1, 2, 3 … in order of first appearance); Copy says which of how many ("2 of 3"). Rows of a group sit together, shaded as one block. |
| File Name, Book Name | The PDF file, and a readable book name (the PDF's title, or the file name without the library code and catalogue tags) |
| Kruti क्रमांक, Kruti Name | From the Excel when matched; for new Kruti the name is the heading read from the book |
| Aadi Vakya, Ant Vakya | The Kruti's first and last sentence, as printed in this book and in its own script (refrain cues and verse numbers are skipped) |
| PDF Start/End Page | Page numbers in the PDF file |
| Book Start/End Page | Page numbers printed in the book, read from its headers/footers (blank for front matter before page 1) |
| No. of Verses | Verses in this copy (the book's running Kruti serial number is not counted) |
| Script | Devanagari or Gujarati, as printed in this book |
| In Excel? | Matched - same script / Matched - other script / New |
| Match % | The weaker of the Aadi and Ant matches |
| Check | OK, or why a reviewer should look: no heading found, Aadi/Ant not one clear sentence, looks like an index/list, spans many pages, low OCR quality |
| Remarks | For the team (grey) |

**Kruti boundaries.** Books mark Kruti in different ways; all of these are recognised:
verse numbers between dandas (॥1॥, ।2।) or at a line end after dots (…1…, …2);
headings ending in a Kruti-type word (…लावणी, …स्तवन), matching a name in the Excel,
followed by verses restarting at 1, or followed by a bracketed serial (सुपार्श्वनाथ नु [7]).
Running page headers and page numbers are removed first.

## Tuning (`config.yaml`)

- **Too few matches on good pages:** lower `found_threshold` to 80. Wrong matches: raise it to 90.
- **Too many tiny Kruti listed:** raise `min_verses`.
- **Kruti wrongly split or fused:** add the book's Kruti-type words to `title_keywords`.
- **Copies not grouped (or different Kruti grouped):** lower (or raise) `duplicate_threshold`.
- **Machine slows down during OCR:** keep `ocr_workers: 2` on 8 GB RAM machines. Use 4–6 on a 16–32 GB desktop.
- **Poor OCR confidence across many books:** set `ocr_engine: google_vision` (see below).

## Scale and cost (estimates, verify on a pilot)

- **OCR with Tesseract** takes about 1.5–3 s per page with 4 parallel jobs on a 4-core PC. For example, 30,000 scanned pages is roughly 12–25 hours. It can run overnight and resumes from the cache if interrupted.
- **Google Cloud Vision** (`ocr_engine: google_vision`) is much better on old prints and fast. At roughly US$1.50 per 1,000 pages at time of writing, 30,000 pages is about US$45. Needs `pip install google-cloud-vision` and a service-account key in `GOOGLE_APPLICATION_CREDENTIALS`.
  > This engine has **not been tested** against real books yet. Try it on one book first.

## Known limits

- **Manuscript or old-script pages** (handwritten, padimatra, heavily damaged) are not read reliably by any off-the-shelf OCR. Rows from such pages are marked "OCR Quality: Low".
- **Splitting relies on verse numbers and headings.** Kruti printed without verse numbers or a type-word heading (e.g. a single unnumbered doha) are not detected.
- **Titles are a first draft.** They may include a raga/dhal line or miss a title placed below verse 1, and always need a reviewer's check.
- **One book = one PDF.** If a book is split across several PDFs, a Kruti crossing the split is listed in both parts.
