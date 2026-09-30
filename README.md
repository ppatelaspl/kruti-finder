# Kruti Finder

The team's Excel covers only part of the books. Kruti Finder does two jobs:

1. **New Kruti.** It finds every Kruti in the books that is **not in the team's Excel**, and writes them in the team's own Excel format: title, Aadi Vakya, Ant Vakya, book and start/end page. The team then only reviews and approves, instead of reading every book manually.
2. **Excel Kruti in other books.** For every Kruti already in the Excel, it lists **all books** it appears in, with page ranges. The Excel does not record which book the team worked from, so every copy is listed.

## Desktop app

Kruti Finder is a desktop app for **Windows 10/11, macOS (Apple silicon) and Ubuntu / Linux Mint / Debian**, with OCR built in.

- **Installing:** see [INSTALL.md](INSTALL.md).
- **Building the installers:** see [BUILD.md](BUILD.md). GitHub builds all three automatically.

The command-line version described below uses the same engine and gives identical results.

## How it works

1. **Read each page.** If the PDF has a proper Unicode text layer it is used directly. If the page is a scan, or the text layer is garbage (old legacy Gujarati/Hindi fonts, broken conjuncts), the page is OCR'd. OCR results are cached in `.kruti_cache/`, so a stopped or repeated run never OCRs the same page twice.
2. **Normalise.** Gujarati script is converted to Devanagari. The Excel's `#…#` markers and `{variant}` readings are removed. Common spelling variants are treated as equal (ण/न, श/ष/स, ब/व, ी/ि, ू/ु, ै/े …), and digits, punctuation and spaces are ignored while matching.
3. **Find start and end.** Aadi Vakya is searched with its first part, and Ant Vakya with its last part (text after `...`). The search works like finding a house by first going to the right pincode and then checking door-to-door. A quick index shortlists a few likely spots in the book, and only those are compared carefully (fuzzy match, so OCR mistakes are tolerated).
4. **Classify each Kruti.**
   - **Found**: start and end both match ≥ 85%, in order, within 40 pages.
   - **Partially Found**: only the start or only the end matches, or one end is a weak match. The Note column says which.
   - **Not Found**: nothing in any book.

   Lines in a book's index page (`first line ....... 12`) are ignored.
5. **Find missing Kruti.** A new Kruti starts wherever verse numbers restart at ॥1॥, or at a heading ending in a Kruti-type word (स्तवन, सज्झाय, गीत, पद …; configurable in `title_keywords`). Numbers garbled by OCR (॥[॥) are inferred from the sequence.

   For every block not already in the Excel, the tool records:
   - **Title:** the heading lines above verse 1;
   - **Aadi Vakya:** the first verse;
   - **Ant Vakya:** the last verse;
   - **pages.**

   The same Kruti found in several books or editions, even one in Gujarati script and one in Devanagari, becomes **one row**, with the other copies listed in "Also Found In".

   Running headers, footers and page numbers are removed first, so they never leak into the Vakya text or break a Kruti that crosses a page.

## Command line: setup (one time)

Python 3.10+ is required.

```bash
pip install -r requirements.txt
```

Install Tesseract OCR with the Hindi, Gujarati and Sanskrit languages:

- **Windows:** use the UB-Mannheim installer (github.com/UB-Mannheim/tesseract/wiki). Tick *Hindi, Gujarati, Sanskrit* under "Additional language data". If `tesseract` is not on PATH, set `tesseract_cmd` in `config.yaml`.
- **Mac:** `brew install tesseract tesseract-lang`
- **Ubuntu:** `sudo apt install tesseract-ocr tesseract-ocr-hin tesseract-ocr-guj tesseract-ocr-san`

For old printed books, replace `hin/guj/san.traineddata` with the **tessdata_best** models (github.com/tesseract-ocr/tessdata_best). They are slower but noticeably more accurate.

## Run

```bash
python kruti_finder.py run --excel Kruti_Master.xlsx --books "D:\Books" --out output
```

It writes two files to `output/`: **`Missing_Kruti.xlsx`** (the main deliverable for the team) and **`Kruti_Report.xlsx`** (status of the Kruti already in the Excel). The books folder may contain sub-folders. The book name in the report is the PDF file name, so name files meaningfully (e.g. `Kshamakalyan_Kruti_Sangrah_Vol2.pdf`).

## Output 1: `Missing_Kruti.xlsx` (the main deliverable)

Both sheets start with the same four columns as the team's Excel (कृति क्र., नाम, आदिवाक्य, अंत वा.) and are grouped one row per Kruti.

| Sheet | Use |
|---|---|
| New Kruti | Kruti not in the Excel. After the four columns come Temp ID, Book, Start/End Page, No. of Verses, No. of Books, Also Found In (other books with pages), OCR Quality, Approve (Y/N) and Reviewer Remarks. Grey columns are for the team. |
| Excel Kruti - Books Found | Kruti already in the Excel, with No. of Books, first Book and pages, and every other book in "Also Found In". Reviewer Remarks lets the team note which copies are new for them. |
| How to Review | Short instructions for reviewers |

## Output 2: `Kruti_Report.xlsx` (the Kruti already in the Excel)

| Sheet | Use |
|---|---|
| Dashboard | Counts: found / partial / not found, missing Kruti, pages OCR'd, pages flagged |
| Kruti Summary | One row per Kruti: status, first book, pages, other books. Kruti **not found in any book** are here. |
| Kruti Locations | One row per occurrence (a Kruti in 3 books = 3 rows), with match % |
| Page Log | How every page was read (text/OCR), OCR confidence, low-quality flags |
| Updated Master | The original Excel plus Status, Book and Page columns |

## Team review loop

1. Reviewers work through the **New Kruti** sheet of `Missing_Kruti.xlsx`.
   - Assign the real Kruti No. (left blank, the Temp ID is used).
   - Check the title.
   - Correct Aadi/Ant text on rows marked "OCR Quality: Low".
   - Set Approve = `Y` for real Kruti.
2. Reviewers check the **Excel Kruti - Books Found** sheet for copies in books the team has not used, and **Partially Found** rows. Usually the book text differs from the Excel, or OCR on that page was poor (see Page Log).
3. Merge the approved rows into a new master:

   ```bash
   python kruti_finder.py merge --report output/Kruti_Report.xlsx --missing output/Missing_Kruti.xlsx --out Kruti_Master_v2.xlsx
   ```

4. Use the new master for the next run. Coverage improves with every cycle.

## Tuning (`config.yaml`)

- **Too many Partially Found on good pages:** lower `found_threshold` to 80. Too many wrong Found: raise it to 90.
- **Missing list too long:** raise `gap_min_verses`.
- **Kruti wrongly split or fused:** add the book's Kruti-type words to `title_keywords`.
- **Machine slows down during OCR:** keep `ocr_workers: 2` on 8 GB RAM machines. Each worker uses about 1 GB. Use 4–6 on a 16–32 GB desktop.
- **Poor OCR confidence across many books:** set `ocr_engine: google_vision` (see below).

## Scale and cost (estimates, verify on a pilot)

- **Matching** takes about 2 ms per Kruti per book. 40,000 Kruti × 200 books is roughly 4–5 hours; 114 Kruti is minutes.
- **OCR with Tesseract** takes about 3–6 s per page per worker. For example, 30,000 scanned pages with 2 workers is roughly 15–25 hours. It can run overnight and resumes from the cache if interrupted.
- **Google Cloud Vision** (`ocr_engine: google_vision`) is much better on old prints and fast. At roughly US$1.50 per 1,000 pages at time of writing, 30,000 pages is about US$45. Needs `pip install google-cloud-vision` and a service-account key in `GOOGLE_APPLICATION_CREDENTIALS`.
  > This engine has **not been tested** against real books yet. Try it on one book first.

## Known limits

- **Manuscript or old-script pages** (handwritten, padimatra, heavily damaged) are not read reliably by any off-the-shelf OCR. They show up in the Page Log as low confidence; treat Not Found there as "unchecked".
- **Splitting relies on verse numbers and headings.** Kruti printed without verse numbers or a type-word heading (e.g. a single unnumbered doha) are not detected as new Kruti.
- **Titles are a first draft.** They may include a raga/dhal line or miss a title placed below verse 1, and always need a reviewer's check.
- **One book = one PDF.** If a book is split across several PDFs, a Kruti crossing the split will show as Partially Found in both parts.
- **Missing Kruti depend on the Excel.** Every Kruti in the books, by any author, is compared with the Excel entries; whatever is not in the Excel is listed as missing.
- **Excel entries with typos** may show as Partially Found. The tool does not list their block as missing, so the Kruti is never entered twice.
