# Gatha Lines: ground truth

Hand-labelled pages used to measure accuracy (spec section 7). The split below was fixed
on 2026-11-24, **before** any Gatha Lines output was looked at on these books. Rules are
tuned only on the `tune` books; the `unseen` books are measured once, at the end.

| Set | Book (in `kruti-samples/` or `test-results/`) | Why it is here |
|---|---|---|
| tune | B052034 kshama kalyan kruti sangrah | Hindi, verse numbers between dandas (।2।), biography prose |
| tune | B039544 Prachin Sazzaya Mahodadhi part 1 | Gujarati, bare verse numbers at the right margin, refrains (મનડું૦) |
| tune | B000505 Gitarth Ganga (test-results) | explanation (बालावबोध) printed between gathas |
| tune | S008673 parmatma bhakti prakash | Gujarati, gathas without numbers separated by gaps |
| unseen | S037822 Jay Jay Parshwa Jinanda part 1 | Hindi, tune lines (तर्ज), some unnumbered stanzas with refrains |
| unseen | B021879 sazzay sagar part 1 | Gujarati, two-column pages, ढाळ parts |
| unseen | S027836 chaityavandan parvamala | Devanagari, numbers after dots (…१…) |
| unseen | B007712 Jain-lavani | Gujarati, several gathas run together on one line (॥ 3 ॥) |

## Label format

One JSON file per book: `{"set": "tune|unseen", "file": "<pdf path>", "pages": [from, to], "krutis": [{"title": "…",
"gathas": [{"part": "", "no": "1", "first": "…", "last": "…"}]}]}`.

- `pages` is the labelled range (PDF page numbers). Only gathas that start and end inside
  it are labelled; a Kruti cut by the range keeps only its gathas inside it.
- Structure (which lines are a gatha's first and last, which text is not a Kruti, where
  a Kruti starts) is decided from the page **image**. The text of `first` / `last` is
  copied from the OCR line at that place, since the tool's output can only ever be the
  OCR text; scoring uses a fuzzy match (≥ 85) on normalised text.

## Results

Measured 2026-11-24 with `python tools/eval_gatha.py --set …` (fuzzy match ≥ 85).

| Set | Kruti | Gathas | First line | Last line | Extra rows |
|---|---|---|---|---|---|
| tune (4 books + B052034 front matter) | 100.0% | 99.4% | 97.7% | 98.3% | 3.8% |
| unseen (first and only run) | 44.8% | 75.6% | 65.1% | 63.4% | 35.6% |

The unseen books are below the 90% bar. Per book (unseen): B007712 Kruti 4/5, gathas 18/21;
B021879 6/10, 64/75; S027836 3/7, 26/48; S037822 0/7, 22/28.

### Round 2 (all sample books)

The 4 round-1 unseen books moved into tuning, and 13 more books were labelled for tuning,
21 labelled ranges in all (plus B052034's front matter). 7 fresh books were held out as
the new unseen set: B035022, S037974, B018723, B041178, S022020, B019948, B024736.
S022020 and B019948 are prose only.

| Set | Kruti | Gathas | First line | Last line | Extra rows |
|---|---|---|---|---|---|
| tune (21 books) | 75.0% | 89.3% | 83.6% | 80.7% | 8.7% |
| unseen round 2 (first and only run) | 76.7% | 77.8% | 67.0% | 57.6% | 16.4% |

Prose-only unseen books produced 0 rows. Gatha lines are still below the 90% bar on new books.
