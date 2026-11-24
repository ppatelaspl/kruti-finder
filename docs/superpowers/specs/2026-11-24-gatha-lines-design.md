# Gatha Lines: second option in Kruti Finder (design)

Date: 2026-11-24 · Base: v1.0.9 (the version the customer has)

## Intent

The customer wants a second option in the Kruti Finder app. It reads PDF books and lists **every
multi-gatha composition (Kruti)** with **the first and last line of each gatha**. It is a new,
separate feature. **The existing feature ("Find Kruti", Excel match) must not change at all.**
The first and last lines are the most important output.

## Goals

- Read the same books as feature 1: scanned or text-layer PDFs, files or folders.
- Find each Kruti that has **2 or more gathas**. Leave out the preface, the book's opening
  details, explanations of a Kruti (व्याख्या, अर्थ, भावार्थ, बालावबोध, टीका), indexes and
  other non-Kruti material.
- Within each Kruti, find every gatha:
  - **Numbered verses** (॥1॥, ।2।, …1…, `15.`): each numbered verse is one gatha.
  - **No numbers:** work out each gatha from how it is printed.
- Write one Excel row per gatha, with its first line and last line as printed.
- Give the reviewer enough detail on every row to decide whether to trust it.
- Same languages and scripts as feature 1: Hindi, Gujarati and Sanskrit OCR (`hin+guj+san`),
  plus Unicode text layers. Old scripts have the same limits as feature 1.
- Same ease of use as feature 1: pick books, progress bars, pause/resume/cancel, a cache that
  resumes, open the Excel when done.

## Non-goals

- No Excel input and no matching against the team's Kruti Excel. That is feature 1.
- No grouping of copies across books (no Group ID).
- No new OCR languages.

## Anti-goals (a failure even if it runs)

- Any change in feature 1's results, Excel or behaviour.
- Running online. The app must stay **completely offline**, like feature 1. No cloud OCR or
  AI service, and no book text leaves the computer.
- A local AI model. It would add GBs to the installer and is too slow on 8 GB laptops.
- Inventing text. First and last lines must be copied from what was read, never generated.
- Repeating 1.0.10: rules tuned on a few books that look fine there but lose accuracy on
  others. Accuracy must be measured on books not used for tuning.

## Constraints

- Code stays separate from feature 1: new modules, and feature 1's modules (`kruti/krutis.py`,
  `kruti/matcher.py`, `kruti/pipeline.py`, `kruti/report.py`, `kruti/extract.py`) are **not
  edited**. Feature 2 may import their functions read-only. If it needs a variant of one, it
  copies the code into its own module rather than changing the shared one.
- 1.0.10 was withdrawn and its code removed from the repo; the customer has 1.0.9 only. This
  feature ships as **v1.1.0** *(my call: a new feature, so a minor version bump)*.
- Builds and installers stay as they are (one app, three installers, PyInstaller, Python 3.12,
  PySide6 6.7.3). Feature 2 adds no new dependencies.
- Both features use the same OCR settings (Tesseract, bundled models, `ocr_workers`, DPI).

## Approaches considered

1. **Offline rules plus page layout (chosen).** Use each line's position on the page as well
   as its words. The user required offline operation, and this is the only offline option
   that fits the installer and the laptops.
2. **Claude reads the pages (rejected).** The most accurate at telling verse from prose, but
   online. The user ruled it out.
3. **A mix of rules and Claude (rejected).** Online for the unclear pages, so also ruled out.
4. **A local AI model (rejected).** Too large and too slow for the target machines.

Why the layout matters: 1.0.10 decided verse vs prose from the words alone and was not
accurate enough. The layout gives stronger signals:
- **Verse:** short lines, printed in groups, often indented or centred. A gap, an indent or
  a line ending in । ॥ , ; marks the end of a gatha.
- **Prose:** lines run to the full text width and wrap mid-sentence. Prose words (है, था,
  छे, हतो, करवामां …) only confirm it.

## Design

### 1. Reading pages with their layout

- Feature 1's reader (`extract.py`) and its cache keep text only. Feature 2 needs each line
  with its box (x0, y0, x1, y1), its words and, from OCR, its confidence.
- New module `kruti/layout.py`:
  - **Text-layer pages:** read lines and positions with PyMuPDF `page.get_text("dict")`.
  - **OCR pages:** Tesseract `image_to_data`, grouping words into lines by block, paragraph
    and line number. It also keeps Tesseract's block and paragraph numbers, which help find
    gatha breaks.
  - The decision to OCR a page uses the same rules as feature 1 (`min_text_chars`,
    `min_indic_ratio`, `max_broken_ratio`), reusing its functions read-only.
- A separate cache, `<data dir>/layout_cache/`, keyed the same way as the OCR cache.
  Feature 1's cache is not changed. Feature 2's first run on a book OCRs it again, and later
  runs reuse the layout cache. *(Builder's call: whether feature 1's cached text can be used
  to skip OCR for text-only signals. The cache format must not change.)*
- Running headers, footers and page numbers are removed using feature 1's logic, with the
  printed page number kept for each page (Book Page).

### 2. Leaving out non-Kruti material

Each line is classed as **verse**, **prose**, **heading**, **list/index** or **note** from:
- its layout: width compared with the page's text width, indent, gap above, line length,
  and whether it ends mid-word or mid-sentence;
- how it ends: । ॥ , ; or a verse number;
- its words: prose words, explanation openers (व्याख्या, अर्थ, भावार्थ …), index headings
  (अनुक्रमणिका …), Kruti-type words (feature 1's `title_keywords`);
- its neighbours, smoothed over a window so one odd line does not flip a whole block.

Runs of prose, index, list or note lines are left out. Verses quoted inside an explanation
are left out with it. The rules sit in one place with named, tunable thresholds.

### 3. Splitting into Kruti

A new Kruti starts where verse numbers restart at 1, or at a heading with a Kruti-type word.
This follows feature 1's rules, reused or copied.

**Explanations between gathas do not end a Kruti** (user decision). In a book that prints
gatha 1, then its अर्थ/भावार्थ/टीका, then gatha 2, the explanation is skipped and the Kruti
carries on with the next gatha. A real gatha is told apart from a verse quoted inside an
explanation by its number continuing the Kruti's sequence and by its layout (verse block,
not inline in a prose paragraph). Prose ends a Kruti only when a new heading or a verse
number restart follows, or when no verse continues the sequence within the next few pages. The Kruti name is its heading, or blank with a Check note when no heading is found.
Part headings (ढाल, दुहा, कलश … from `section_keys`) stay inside one Kruti, and gatha numbering
continues as printed. A Kruti with fewer than 2 gathas is not listed.

### 4. Splitting a Kruti into gathas

- **Tune, raga and metre lines are left out** (user decision): lines such as `राग …`,
  `… -ए देशी`, `( मालिनी-छन्दः )` and refrain markers (आंकणी, टेक, ध्रुवपद) under the heading
  or between gathas are never part of a gatha. Gatha 1's First Line is the real first verse
  line.
- **Numbered:** a gatha runs from the line after the previous verse number to the line that
  carries this number. Numbers garbled by OCR are inferred from the sequence, as in feature 1.
- **Not numbered:** a break comes at a clear vertical gap or indent change, or after a line
  ending in ॥. If those are missing, the Kruti's usual lines per gatha (often 2 or 4) is
  used, but only when the line endings (। , ;) agree. Every inferred break is marked in the
  "How found" column.
- A gatha that crosses a page or column is joined before taking its first and last line.
- **A "line" is one printed row** *(my call)*. When a gatha's two halves are printed side by
  side on one row, that row is one line. A half that wraps onto a second row makes two lines.
  Tesseract and PyMuPDF fragments on the same row are merged into one line by position.

### 5. Output: `Gatha_Results.xlsx`

One file per run, in the run's date-time folder. It has one sheet, "Gatha Lines", one row
per gatha, in book and page order, using feature 1's Excel styling (Outfit font, Aspire
colours). Each Kruti's rows are shaded as one block.

| Column | Meaning |
|---|---|
| File Name | PDF file |
| Book Name | Readable book name, same logic as feature 1 |
| Kruti No. | 1, 2, 3 … within the book, so the rows of one Kruti can be filtered |
| Kruti Name | Heading read from the book |
| Part | The part heading the gatha sits under (ढाल 2, दुहा, कलश …), blank if the Kruti has no parts *(my call: numbers restart per part, so Gatha No. alone is ambiguous)* |
| Gatha No. | As printed. If the gatha has no number, its position in the part or Kruti, in brackets: "(3)" |
| Total Gathas | Gathas in the whole Kruti, across all its parts *(my call)* |
| **First Line** | First printed line of the gatha, as read, in the book's script |
| **Last Line** | Last printed line of the gatha, including its verse number if printed |
| PDF Page | PDF page of the first line, or a start-end range if the gatha crosses pages |
| Book Page | Printed book page(s), blank for front matter |
| Script | Devanagari / Gujarati |
| Text Source | Text layer / OCR |
| OCR Confidence % | Tesseract's mean word confidence on the gatha's lines; 100 for a text layer |
| How found | "Numbered verse" / "Number inferred (OCR garbled)" / "No number - gap" / "No number - line count" |
| Confidence | High / Medium / Low, from the items above (see below) |
| Check | OK, or why a reviewer should look: no heading, low OCR, inferred break, one-line gatha, unusually long gatha, crosses pages, next to prose |
| Remarks | Empty, for the team (grey) |

**Confidence:**
- **High:** numbered verse, OCR at or above `low_ocr_confidence` (70), and no Check notes.
- **Medium:** an inferred number or a gap-based break, or one Check note.
- **Low:** a line-count break, low OCR, or two or more Check notes.

*(Builder's call: the exact scoring, as long as it is documented in the README and visible
in the row's Check column.)*

### 6. The app

- The main window gets two tabs: **"Find Kruti (Excel match)"** holds feature 1 unchanged,
  and **"Gatha Lines"** is new.
- The new tab has the same layout and widgets as feature 1:
  1. PDF books: add files, add a folder, drag and drop, remove, clear, with a count of books.
  2. Save results to: a folder, with one date-time sub-folder per run.
  3. Advanced settings: parallel OCR jobs (shared), "Clear saved layout results".
- Start, Pause/Resume and Cancel work the same way. Progress shows all books and this book,
  elapsed time, time left, pages OCR'd and **Kruti / gathas found**. There is a log panel.
- When done: "Open results (Excel)" and "Open output folder".
- Only one run at a time across both tabs. Start is disabled on the other tab while a run
  is going.
- Settings (books, output folder) are saved per tab.
- The header subtitle becomes neutral, covering both options.
- The command line gets a matching sub-command, `python kruti_finder.py gatha --books … --out …`,
  using the same engine.

### 7. Accuracy and validation

- **Pass bar (user decision): more than 90%** on books never used for tuning, for each of:
  correct Kruti identified, correct gathas identified, and correct First and Last Line of
  each gatha. Non-Kruti text wrongly listed must be close to none.
- **Ground truth** *(my call)*: labelled from the books in `kruti-samples/`. Pages are
  hand-labelled with the output columns, covering at least one book without verse numbers,
  one with explanations between gathas and one with multi-part Kruti. Books are split into
  a tuning set and an unseen set before tuning starts, and the unseen set is not looked at
  while tuning. If the team sends its own labelled pages, they join the unseen set.
- Measure and report per book:
  - Kruti found vs expected;
  - gathas found vs expected;
  - first and last lines correct, as a fuzzy match of at least 85 to allow for OCR;
  - non-Kruti text wrongly listed.
- Tests in `tests/test_gatha.py` use small synthetic pages (lines with boxes) for each rule:
  numbered, unnumbered by gap, prose rejection, explanation between verses, index page,
  part headings, crossing pages.
- Feature 1 regression check: on the sample books, feature 1's `Kruti_Results.xlsx` must be
  identical before and after this work.

## Left to the builder

- Module split inside `kruti/` (for example `layout.py`, `gatha.py`, `gatha_report.py`,
  `gatha_pipeline.py`) and how the shared progress and controller classes are reused.
- Threshold values, as long as they are named and kept in one place.
- Whether the layout cache can avoid a second OCR of books feature 1 has already read.

## Open items

None. Optional: the team's own labelled pages, added to the unseen set when they arrive.
