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

One JSON file per book: `{"file": "<pdf path>", "pages": [from, to], "krutis": [{"title": "…",
"gathas": [{"part": "", "no": "1", "first": "…", "last": "…"}]}]}`.

- `pages` is the labelled range (PDF page numbers). Only gathas that start and end inside
  it are labelled; a Kruti cut by the range keeps only its gathas inside it.
- Structure (which lines are a gatha's first and last, which text is not a Kruti, where
  a Kruti starts) is decided from the page **image**. The text of `first` / `last` is
  copied from the OCR line at that place, since the tool's output can only ever be the
  OCR text; scoring uses a fuzzy match (≥ 85) on normalised text.
