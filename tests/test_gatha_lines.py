"""Gatha Lines: what kind of line each one is.   Run:  python -m pytest tests"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kruti.gatha_lines import classify_book, gatha_config  # noqa: E402
from kruti.layout import Line, PageLayout                  # noqa: E402

CFG = gatha_config(None)
LEFT, RIGHT = 60, 360          # text box of the synthetic page (width 300)


def page(no, rows, source="ocr"):
    """rows: (text, x0, x1) or (text, x0, x1, gap) - gap in line heights above the line."""
    lines, y = [], 40
    for r in rows:
        text, x0, x1 = r[:3]
        y += 18 * (r[3] if len(r) > 3 else 0)
        lines.append(Line(text, x0, y, x1, y + 14, 90))
        y += 18
    return PageLayout(no, source, 90, 420, 600, lines)


PROSE = [("यह स्तवन श्री जिनराजसूरि ने रचा है और इसमें प्रभु के गुणों का", LEFT, RIGHT),
         ("वर्णन किया गया है। इस संग्रह में ऐसी अनेक रचनाएँ दी गई हैं जो", LEFT, RIGHT),
         ("प्राचीन भंडारों से प्राप्त हुई थीं और पहले कभी छपी नहीं थीं।", LEFT, RIGHT),
         ("इनका संपादन बहुत सावधानी से किया गया है ताकि पाठ शुद्ध रहे", LEFT, RIGHT),
         ("और पाठकों को लाभ हो।", LEFT, 160)]
VERSES = [("श्री महसेन नरेश नंद, चंद्रप्रभ स्वामी,", 100, 260),
          ("शशि लांछन उज्ज्वल वरण, सेवुं सिरनामी ॥1॥", 135, 330),
          ("धनुष दोढ सै मान चारु, जसु उन्नत काय,", 100, 285),
          ("आयु बरस दश लाख पूर्व, चंद्रपुरी राय ॥2॥", 135, 325)]


def kinds(pages):
    lines, _ = classify_book(pages, CFG)
    return [(ln.text, ln.kind) for ln in lines]


def kind_of(pages, text):
    return dict(kinds(pages))[text]


def test_header_and_page_number_removed():
    pages = [page(n, [("क्षमाकल्याण कृति संग्रह", 150, 280)] + VERSES + [(str(n + 10), 200, 215)])
             for n in range(1, 6)]
    lines, printed = classify_book(pages, CFG)
    assert all(ln.kind == "furniture" for ln in lines if ln.text == "क्षमाकल्याण कृति संग्रह")
    assert all(ln.kind == "furniture" for ln in lines if ln.text.isdigit())
    assert printed[3] == 13


def test_short_lines_ending_in_danda_are_verse():
    ks = kinds([page(1, VERSES)])
    assert [k for _, k in ks] == ["verse"] * 4


def test_full_width_wrapped_prose_is_prose():
    ks = kinds([page(1, PROSE)])
    assert [k for _, k in ks] == ["prose"] * 5


def test_explanation_opener_is_prose():
    rows = VERSES + [("भावार्थ- चंद्रप्रभ स्वामी महसेन राजा के पुत्र", 60, 300),
                     ("हैं, उनका लांछन चंद्र है।", 60, 200),
                     ("अर्थ: हे प्रभु!", 60, 140)]
    ks = kinds([page(1, rows)])
    assert [k for _, k in ks][4:] == ["prose", "prose", "prose"]


def test_tune_line_is_tune():
    for t in ("राग - आशावरी", "( मालिनी-छन्दः )", "नणदल बिंदली -ए देशी", "आंकणी", "॥ टेक ॥",
              "ध्रुवपद", "(तर्ज: मेरे मौला बुला लो)"):
        pages = [page(1, [("चंद्रप्रभ जिन स्तवन", 150, 280), (t, 140, 290)] + VERSES)]
        assert kind_of(pages, t) == "tune", t


def test_part_heading_is_part():
    for t in ("ढाल बीजी", "॥ दुहा ॥", "कलश"):
        pages = [page(1, VERSES[:2] + [(t, 180, 240)] + VERSES[2:])]
        assert kind_of(pages, t) == "part", t


def test_kruti_heading_is_heading():
    for t in ("शांतिनाथ स्तवन", "8. श्री चन्द्रप्रभ जिन चैत्यवंदन"):
        pages = [page(1, [(t, 150, 290)] + VERSES)]
        assert kind_of(pages, t) == "heading", t


def test_index_page_is_list():
    rows = [("अनुक्रमणिका", 170, 250)] + [
        (f"{n}. {name} ........ {10 + 3 * n}", LEFT, RIGHT)
        for n, name in enumerate(["शांतिनाथ स्तवन", "नेमिनाथ स्तवन", "पार्श्वनाथ स्तवन",
                                  "महावीर स्तवन", "गौतम स्वामी सज्झाय", "नवपद पूजा"], 1)]
    ks = kinds([page(1, rows)])
    assert {k for _, k in ks} == {"list"}


def test_source_note_is_note():
    pages = [page(1, VERSES + [("(खरतरगच्छ साहित्य कोश क्रमांक- 2592.)", 120, 330)])]
    assert kind_of(pages, "(खरतरगच्छ साहित्य कोश क्रमांक- 2592.)") == "note"


def test_one_odd_line_smoothed():
    odd = ("गुण गावे भविजन प्रेमे प्रभु तणा जे नर नारी सुणे ते पामे", LEFT, RIGHT)
    rows = VERSES + [odd] + VERSES
    ks = kinds([page(1, rows)])
    assert ks[4] == (odd[0], "verse")


def test_last_line_of_prose_paragraph_is_prose():
    ks = kinds([page(1, VERSES + PROSE)])
    assert ks[-1] == ("और पाठकों को लाभ हो।", "prose")


def test_gujarati_numbers_and_script_kept():
    rows = [("શ્રી મહસેન નરેશ નંદ, ચંદ્રપ્રભ સ્વામી,", 100, 260),
            ("શશિ લાંછન ઉજ્જ્વલ વરણ, સેવું સિરનામી ॥૧॥", 135, 330),
            ("ધનુષ દોઢ સૈ માન ચારુ, જસુ ઉન્નત કાય,", 100, 285),
            ("આયુ બરસ દશ લાખ પૂર્વ, ચંદ્રપુરી રાય ॥૨॥", 135, 325)]
    lines, _ = classify_book([page(1, rows)], CFG)
    assert [ln.kind for ln in lines] == ["verse"] * 4
    assert lines[1].text == rows[1][0]
    assert [n for _, n in lines[1].marks] == [1] and [n for _, n in lines[3].marks] == [2]
    assert lines[1].text[:lines[1].marks[0][0]].endswith("॥૧॥")


def test_layout_measures():
    """Fill and indent are measured against the book's text width (set by its prose)."""
    lines, _ = classify_book([page(1, PROSE), page(2, [VERSES[0], VERSES[1] + (2,)] + VERSES[2:])],
                             CFG)
    lines = [ln for ln in lines if ln.page == 2]
    assert abs(lines[0].fill - (260 - 100) / 300) < 0.01
    assert abs(lines[1].indent - (135 - 60) / 300) < 0.15
    assert lines[1].gap_above > 1.5 and lines[2].gap_above < 0.2
