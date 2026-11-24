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


# ---- found on the tuning book B000505 (verse, then its explanation, then the next verse)
COMMENTARY = [("कहे कोई भवी सि जोडी, श्रुतमां नहीं खोडी |", 90, 300),
              ("ते मिथ्या उद्धत भाव, श्रुत जलधि भवे नावा ॥ ११ ॥", 90, 320),
              ("अर्थ--वरी केटलाक एम बोले छे जे नवी जोडी करवी ते सिद्धांतमां तो काइ", LEFT, RIGHT),
              ("स्तवन सज्झाय जोडवानुं शुं काम छे केमके श्रुत के० सिद्धांतमां तो काइ", LEFT, RIGHT),
              ("सिद्धातरूप समुद्रमां पण नावा होय तो प्रवेश थाय ए भाव ॥ ११ ॥", LEFT, 330),
              ("पूरव सूरियें कीधी, तेणे जो नवि करवी सिद्धि ।", 90, 290),
              ("तो सर्वे कीधो धर्म, नवी जोयो मर्म ॥ १२ ॥", 90, 300),
              ("अये--एवं वली प्रतिवादी बोल्या के तो पूर्वाचार्ये जोडी छे तेने भणो रे", LEFT, RIGHT),
              ("यतः-“इको य दोसो, जे भाचर खलजणस्स पीडत्ति । तदवि पयट्टो इत्थं, सुय-", LEFT, RIGHT),
              ("णाण गरो ॥ १ ॥ तत्तो चिय जं कुसल, तत्तो तेसिपि नहु पीडा । अद्धासया", LEFT, RIGHT),
              ("पवित्ति, सव्वे निद्दोसिया भणिया ॥ २ ॥” ॥ १२ ॥", LEFT, 250),
              ("ते मनमां भावीने कहे छे. यतः-“अइपरिणई अपरिणई, दोवि जणो पणासेति ।", LEFT, RIGHT),
              ("तम्हा देसणमाइक्खई, मग्गरक्खहा ॥ १ ॥” १२ ॥", LEFT, 240),
              ("एम श्रुतनो नहीं उच्छेद, ए तो एक देशनो भेद |", 90, 290),
              ("ए अर्थ सुणि उल्लासें भवी वरते श्रुत अभ्यासे ॥ १३ ॥", 90, 320)]


def test_explanation_closing_with_the_gatha_number_is_prose():
    ks = kinds([page(1, COMMENTARY)])
    assert ks[4][1] == "prose"


def test_verse_after_explanation_is_verse():
    ks = kinds([page(1, COMMENTARY)])
    assert [k for _, k in ks[5:7]] == ["verse", "verse"]
    assert [k for _, k in ks[13:15]] == ["verse", "verse"]


def test_garbled_explanation_opener_is_prose():
    assert kinds([page(1, COMMENTARY)])[7][1] == "prose"


def test_verse_quoted_in_explanation_is_prose():
    ks = kinds([page(1, COMMENTARY)])
    assert ks[10][1] == "prose" and ks[12][1] == "prose"


def test_stray_letter_line_is_furniture():
    pages = [page(1, VERSES + [("ર", 200, 205), ("क", 210, 216)])]
    assert kind_of(pages, "ર") == "furniture" and kind_of(pages, "क") == "furniture"


def test_wide_verse_after_explanation_is_verse():
    rows = COMMENTARY[:4] + [("ए भाव जाणवो ॥ ११ ॥", LEFT, 200),
                             ("कहे कोईक भवी रीते, मुनि भिक्षा भांजे भीते ।", 90, 330),
                             ("ते जुडुं शुभ मति ईहे, मुनि अंतरायथी बीहे ॥ १२ ॥", 90, 352)]
    ks = kinds([page(1, rows)])
    assert [k for _, k in ks[5:7]] == ["verse", "verse"]


def test_refrain_abbreviation_before_number_is_a_mark():
    rows = [("गीतारथ विण भूला भमता, कष्ट करे अभिमानेरे ।", 90, 300),
            ("पराये गंठी लगे नवी आव्या, ते सूता अज्ञानेरे ॥श्रीजिन०३॥", 90, 330),
            ("तेह कहे गुरु गच्छ गीतारथ, प्रतिबंधे शुं कीजेरे ।", 90, 300),
            ("दर्शन ज्ञान चरित आदरियें, आप आप तरीजेरे ।श्रीजिन० ४॥", 90, 330)]
    lines, _ = classify_book([page(1, rows)], CFG)
    assert [[n for _, n in t.marks] for t in lines] == [[], [3], [], [4]]


# ---- found on the tuning book B039544 (Gujarati, bare verse numbers at the right margin)
def gpage(no, rows):
    """rows: (text, x0, x1, conf) on a page whose text box is set by full-width lines."""
    lines, y = [], 40
    for text, x0, x1, conf in rows:
        lines.append(Line(text, x0, y, x1, y + 14, conf))
        y += 18
    return PageLayout(no, "ocr", 80, 420, 600, lines)


SAJ = [("એક મ્હેલી ખીજે મળે, વ્હાલા મતમાં નાહિ તસ નેહ;", 60, 270, 86),
       ("લીધા મૂકી જે કરે, તતે તો આખર આવે છેહ. વ૦ ૧૩", 60, 330, 91),
       ("હુકમ લેઈને ત્યાં ગયે।, દીયે આંખા શુ કાન; ~ \"5", 60, 325, 80),
       ("માંડી વાત છાની કહી, આવ્યે! તે બુદ્ધિ નિધાન. મારગ૦ ૪.", 60, 330, 85),
       ("“યેળતુ' સોની ઉચરે, ન શે જો એહ; `", 60, 310, 83),
       ("એને કરતાં તે તમે, સુજને કરજો તેહ. મારગ૦ છ", 60, 325, 88),
       ("ત્રીજી તે વાર આવ્યા તુમે રે, મારો અક્લ અવતાર રે. મનડુ'૦", 60, 335, 85),
       ("વિ તા હોતા તી તતો તીતી તી તી તીતીતીતી તો + તો તી તી તી", 100, 250, 49),
       ("से વારારા ગરાસ", 120, 200, 31)]


def test_gujarati_verse_with_margin_numbers_is_verse():
    ks = kinds([gpage(1, SAJ)])
    assert [k for _, k in ks[:7]] == ["verse"] * 7


def test_low_confidence_junk_is_furniture():
    ks = kinds([gpage(1, SAJ)])
    assert [k for _, k in ks[7:]] == ["furniture", "furniture"]


def test_bare_number_with_full_stop_and_garbled_digit_are_marks():
    rows = SAJ[:7] + [(f"પંક્તિ {i} આ રીતે ચાલે છે, ગાથા. વ૦ {i}", 60, 330, 85) for i in range(5, 13)]
    lines, _ = classify_book([gpage(1, rows)], CFG)
    by_text = {t.text: [n for _, n in t.marks] for t in lines}
    assert by_text[SAJ[3][0]] == [4]
    assert by_text[SAJ[5][0]] == [None]


def test_running_header_read_differently_is_furniture():
    heads = ["३०९ ] પ્રાચીન સજ્ઝાય મહેદધિ ભાગ- १", "પ્રાચીન સજય મહેદધિ ભાગ-૨ | ૨૦૭",
             "પ્રાચીન સજ્ઝાય મહોદધિ ભાગ-૧ | [ २०४", "૨૧૦] પ્રાચીન સન્‍્ઝાચ મહોદધિ ભાગ-૧"]
    pages = [gpage(n, [(h, 50, 380, 80)] + SAJ[:2]) for n, h in enumerate(heads, 1)]
    lines, _ = classify_book(pages, CFG)
    assert all(t.kind == "furniture" for t in lines if t.text in heads)


def test_part_heading_with_stray_bar_is_part():
    pages = [gpage(1, SAJ[:2] + [("| ( દોહા )", 150, 230, 84)] + SAJ[:2])]
    assert kind_of(pages, "| ( દોહા )") == "part"


def test_heading_with_type_word_inside_and_ocr_debris():
    for t in ("દેવકીના છ પુત્રની સજઝાય અથવા છ સાધુની", "अ સંગ્રામ સોનીની સજઝાય, રર"):
        pages = [gpage(1, [(t, 100, 300, 70)] + SAJ[:2] + SAJ[:2])]
        assert kind_of(pages, t) == "heading", t


def test_similar_kruti_headings_on_every_page_are_not_running_headers():
    heads = ["2. श्री अजित जिन चैत्यवन्दन", "3. श्री सम्भव जिन चैत्यवन्दन",
             "4. श्री अभिनन्दन जिन चैत्यवन्दन", "6. श्री पदाप्रभ जिन चैत्यवन्दन"]
    pages = [page(n, [(h, 140, 290)] + VERSES) for n, h in enumerate(heads, 1)]
    lines, _ = classify_book(pages, CFG)
    assert [t.kind for t in lines if t.text in heads] == ["heading"] * 4


def test_frame_serial_and_debris_lines_are_furniture():
    debris = [("त्‌ ૧૩૦ ત", 150, 250, 62), ("आ | ૧૩૧ मित्रदार के | के, के की |", 100, 330, 62),
              ("6. ते ', उ ६. 3 ६, 2 घ सं. 2 ક. કફ ६. છે. ક 3 5, 35. ક હ. ક.", 60, 330, 51)]
    ks = kinds([gpage(1, SAJ[:2] + debris + SAJ[:2])])
    assert all(k in ("furniture", "note") for _, k in ks[2:5])


def test_kruti_heading_at_a_gatha_boundary():
    t = "દેવકીના છ પુત્રની સજઝાય અથવા છ સાધુની"
    pages = [gpage(1, SAJ[:2] + [(t, 70, 260, 88)] + SAJ[:2])]
    assert kind_of(pages, t) == "heading"


def test_full_width_line_ending_in_full_stop_is_verse():
    rows = [("જે મત તે તેહ મિલી રહ્યા, વહાલા ઉત્તસ ઉપમ તાસ; , .", 60, 280, 88),
            ("જે જો તિલ કુલની પ્રીતડી, તેહની જગમાં રહી સુવાસ. ५० ૧૪", 60, 335, 87)]
    ks = kinds([gpage(1, SAJ[:2] + rows + SAJ[:2])])
    assert ks[3][1] == "verse"


# ---- found on the tuning book S008673 (Gujarati stavans, refrain cues after dots)
PAJ = [("પ્રભુ વીર જિણુ'દદ વિચારી, ભા'ખ્યા પવ? પજુસણુ ભારી", 60, 362, 85),
       ("આખા વષમાં તે દિન સોટા, આઠે નહી' તેમાં છોટા રે", 60, 360, 85),
       ("એ ઉત્તમને ઉપકારી....ભાખ્યા. ૧", 177, 360, 85),
       ("જેમ ઔષધમાંહિ કહીએ, અમતને સારુ લહીએ रे", 60, 337, 85),
       ("મહામ'ત્રમાં નવકાર ભારી....ભા'ખ્યા. ૨", 153, 360, 85)]


def test_wide_lines_ending_in_a_verse_particle_are_verse():
    ks = kinds([gpage(1, PAJ)])
    assert [k for _, k in ks] == ["verse"] * 5


def test_verse_line_starting_with_raag_is_not_a_tune_line():
    t = "રાગ હોત ન કેવળજ્ઞાન રે....મ્હાશ."
    assert kind_of([gpage(1, PAJ[:2] + [(t, 160, 330, 85)])], t) == "verse"


def test_short_centred_verse_line_is_not_a_heading():
    rows = [("“પહેલો ગણુધર पीरने। રે", 60, 190, 85), ("શાસનને શણુગાર", 60, 150, 85),
            ("ગૌતમ ગોત્ર તણ્‌। ધણી રે", 170, 295, 85), ("ગુણુમણી રયછે ભડાર", 170, 270, 85)]
    pages = [gpage(1, [("શ્રી ગૌતમસ્વામીનુ' સ્તવન", 150, 280, 85)] + rows + PAJ)]
    assert kind_of(pages, "ગૌતમ ગોત્ર તણ્‌। ધણી રે") == "verse"


def test_bracketed_serial_alone_starts_a_kruti():
    pages = [gpage(1, PAJ[:3] + [("॥ (२)", 180, 220, 85)] + PAJ[3:])]
    assert kind_of(pages, "॥ (२)") == "heading"


def test_heading_after_a_gatha_whose_number_has_a_dot():
    t = "દેવકીના છ પુત્રની સજઝાય અથવા છ સાધુની"
    rows = [("સકલ.” વાચક . શિરોમણી, ભાનુચ'દ્ર કહાવે; ` „~:", 60, 310, 84),
            ("તસ શિષ્ય ભાણુચ'દ્ર ભણે, ભણે દોલત પાવે. प्ये .૧૯", 60, 330, 87)]
    assert kind_of([gpage(1, rows + [(t, 70, 260, 88)] + SAJ[:2])], t) == "heading"


def test_number_before_double_danda_is_a_mark():
    lines, _ = classify_book([page(1, [("कहे शिवकीर्ति लाल।।", 100, 260), ("४।।", 100, 120)] + VERSES)], CFG)
    assert [n for _, n in lines[1].marks] == [4]


def test_number_between_doubled_dandas_is_a_mark():
    t = "उपज्यो आनंद सवायो लाल।। अतिरूडु।।३॥"
    lines, _ = classify_book([page(1, [("दुर्लभ प्रभु दरसण पायो,", 100, 260), (t, 100, 300)] + VERSES)], CFG)
    assert lines[1].marks[-1] == (len(t), 3)       # the "।।" after लाल is pruned when splitting


def test_wide_heading_ending_in_a_type_word():
    t = "जिनदत्त-जिनकुशल-जिनभद्रसूरि स्तवन"
    pages = [page(1, VERSES + [(t, 70, 330), ("(देशी- धीज धरे सीता सती रे लाल)", 90, 300)] + VERSES)]
    assert kind_of(pages, t) == "heading"


def test_unbracketed_source_note_is_note():
    t = "खरतरगच्छ साहित्य कोश क्रमाक--2542"
    assert kind_of([page(1, VERSES + [(t, 100, 300)] + VERSES)], t) == "note"


def test_refrain_cue_with_full_stop_before_the_number_is_a_mark():
    lines, _ = classify_book([page(1, [("राज आज मनोरथ सब फल्या, आज फली सहु आस ।हो.2।", 100, 330)])], CFG)
    assert [n for _, n in lines[0].marks] == [2]


def test_hindi_editorial_prose_is_prose():
    rows = [("कोई साधु-साध्वी अपरिचित नहीं हो सकता। क्योकि गच्छ में दीक्षा", LEFT, RIGHT),
            ("लेने वाले हर व्यक्ति को उनकी रचनाओं का परिचय दिया जाता", LEFT, RIGHT),
            ("मेरी रुचि के कारण जब भी मुझे आपश्री की कोई रचना मिली", LEFT, RIGHT),
            ("तो मैंने उसे लिख लिया था।", LEFT, 180)]
    assert [k for _, k in kinds([page(1, rows)])] == ["prose"] * 4


def test_short_hindi_prose_sentence_is_prose():
    t = "इस उपासरे में आपकी प्रतिमा भी बिराजित है।"
    assert kind_of([page(1, PROSE[:3] + [(t, LEFT, 280)] + PROSE[:2])], t) == "prose"


def test_hyphenated_compound_is_not_an_explanation_opener():
    from kruti.gatha_lines import explanation_opener
    op = explanation_opener(CFG)
    assert not op.match("अर्थ-बोध के लिये बुद्धि दौड़ाने का अवसर")
    assert op.match("अर्थ--वरी केटलाक एम बोले छे") and op.match("भावार्थ- हे प्रभु") and op.match("अर्थ: हे")


# ---- round 2, S037822 (modern print: numbers after a full stop, footnotes)
def test_number_after_a_full_stop_at_line_end_is_a_mark():
    rows = [("जय मंगलकारण, तारण त्रिभुवन रंग,", 90, 280), ("जिनवंदन भंजन, कर्मतरु डांग. २", 90, 290),
            ("सुखदायक नायक, विजयसिह गुरु जेह,", 90, 280), ("तेहना शिष्य बोले गजविजय वर देह. ४", 90, 290),
            ("... हो साहिब ससनेहा. 9", 230, 330)]
    lines, _ = classify_book([page(1, rows)], CFG)
    assert [[n for _, n in t.marks] for t in lines] == [[], [2], [], [4], [9]]


def test_footnote_line_is_a_note():
    for t in ("१. विनति. २. कामदेव ર. चन्द्र. ૪. उल्लसे ५. कमल की पांखडी", "पाठभेद 9. ઝગ. २. ઝચ્છાર"):
        assert kind_of([page(1, VERSES + [(t, 60, 340)])], t) == "note", t


def test_ornament_framed_centred_line_is_a_heading():
    t = "€ आंख मारी उघडे त्यां ॐ"
    rows = [(t, 140, 290), ("आंख मारी उघड त्यां शंखेश्वर देखुं,", 140, 300),
            ("मंदिरमां वेठा मारा पारसनाथ देखुं,", 140, 300), ("धन्य धन्य जीवन मारु कृपा अनी वेच्युं... १", 120, 330)]
    assert kind_of([page(1, PROSE + rows)], t) == "heading"


# ---- round 2, B007712 (run-on lavani: refrains between dandas inside the lines)
def test_adjacent_marks_keep_the_last_number():
    t = "એટ દિયા હે, ભક્તિસે નાહાયા ॥ ३१० ॥ ૧ ॥ સુરતરકી"
    lines, _ = classify_book([page(1, [(t, 60, 360)])], CFG)
    assert [n for _, n in lines[0].marks] == [1]


def test_zero_is_not_a_verse_number():
    t = "જાણુ, જપો! જિનવરરે | ०० ॥ એ અચલ બિરાજે દેવ, દરસ"
    lines, _ = classify_book([page(1, [(t, 60, 360)])], CFG)
    assert all(n not in (0,) for _, n in lines[0].marks)


def test_full_width_line_with_inner_double_dandas_is_verse():
    rows = [("મૈ રહ્યો વિષય ભર પૂર, ગરવર્મે गधा ॥ ગર” ॥ મેં બાત હુઓ હે-", 60, 360),
            ("રાન, ०८०२ જીગ ધંધા ॥ મેં રુચુર્‌ मेया જેર, જોગી ઓર જંદા |", 60, 360)]
    assert [k for _, k in kinds([page(1, rows + rows)])] == ["verse"] * 4


# ---- round 2, S027836 (numbers after dots, refrain cue glued to the number)
def test_dots_number_with_a_glued_refrain_cue_is_a_mark():
    for t, n in (("स्वयंप्रभ देवश्रुत वली, उदयनाथ जिनेश्वरं...२नेव्‌", 2),
                 ("योग अयोगश्री परम प्रभुजी जात नीकेशरं. . .४नेवु", 4),
                 ("मन वच काया स्थिर करी, कीत्तिचंद्र गुण गेह. . . ५. . .", 5)):
        lines, _ = classify_book([page(1, [(t, 60, 350)])], CFG)
        assert [m for _, m in lines[0].marks] == [n], t


def test_long_last_line_of_each_page_is_not_a_running_footer():
    ends = ["अघटित भ्रमणेन्द्र प्रभु ऋषभवचंद्रजी अघहरं . .. ६नेवू",
            "अश्ववृन्द कुटिलक वर्धेमान नन्दिकेशना जिन धर्मचन्द्र अघहरं . . ७नेवू",
            "गुरु रूपकीर्ति हृदय धरी ने माणेक मुनि सुखकरं... १३नेवु"]
    pages = [page(n, VERSES + [(e, 60, 350)]) for n, e in enumerate(ends, 1)]
    lines, _ = classify_book(pages, CFG)
    assert all(t.kind == "verse" for t in lines if t.text in ends)


def test_short_centred_title_between_krutis():
    t = "एकादशी सामान्य"
    rows = VERSES + [(t, 160, 250), ("शासन नायक वीरजी, केवल पायो,", 60, 280),
                     ("संघ चतुविध स्थापवा, महसेन वन आयो...१...", 60, 340)]
    assert kind_of([page(1, PROSE + rows)], t) == "heading"


def test_gujarati_letter_read_for_a_digit_after_a_stop_is_a_mark():
    lines, _ = classify_book([page(1, [("अओहवी जिनवाणी, विजयदेव 'गणधार. રૂ", 60, 300)])], CFG)
    assert [n for _, n in lines[0].marks] == [None]


def test_bracketed_line_with_a_dash_after_a_short_word_is_a_tune_line():
    t = "(રાઝ - शत्रुंजय मंडन ऋषभ जिणंद दयाल.)"
    assert kind_of([page(1, VERSES + [(t, 100, 300)] + VERSES)], t) == "tune"


def test_zero_cue_alone_is_no_mark():
    lines, _ = classify_book([page(1, [("नन) \"(न्न 0", 100, 200)])], CFG)
    assert lines[0].marks == []


# ---- round 2, B021879
def test_heading_with_trailing_bracketed_serial():
    t = "3૩ કમ પયહી અધ્યયન [४३९] ।"
    rows = SAJ[:2] + [(t, 150, 300, 85)] + SAJ[:2]
    assert kind_of([gpage(1, rows)], t) == "heading"


def test_running_header_that_names_a_kruti_type():
    heads = ["'છત્તરાષ્યયનની સજ્ઝાયો ૩૫૬.", "ઉત્તરાષ્યયનની સજ્ઝાયો ૩૫૩", "ઉત્તરાધ્યયનની સજ્ઝાયો ૩૫૧",
             "ઉત્તરાધ્યયનની સજ્ઝાયો ૩૫૫"]
    pages = [gpage(n, [(h, 60, 340, 80)] + SAJ[:2] + SAJ[:2]) for n, h in enumerate(heads, 1)]
    lines, _ = classify_book(pages, CFG)
    assert all(t.kind == "furniture" for t in lines if t.text in heads)


# ---- round 2, B019985 (pujan ritual: numbered mantras)
def test_numbered_mantra_lines_are_invocations_not_verse():
    for t in ("चढ़ावे ॥४॥ ॐ हीं णमो अरिहंताणं मिश्री छवंग चढ़ावे ॥५॥ च छ ज",
              "स ह ॐ हीं रावगाय नमः । ३२ दक्षा चढ़ावे ॥१६॥ सब ९६ द्राक्षा"):
        assert kind_of([page(1, VERSES + [(t, 60, 350)] + VERSES)], t) == "note", t


# ---- round 2, B018952 (run-on stavans numbered "आज० २." inside the line)
def test_number_after_a_refrain_cue_inside_the_line_is_a_mark():
    cases = [("जईजे रे, बेनी शाश्वत गिरिवर जईओ रे, आज० 9. सुणबेनी अ गिरि नो", [9]),
             ("सीत्तेर जोजन जाणीए, त्रीजे साठ जोजननुं मान । प्रभु० २ चोधे आरि", [2]),
             ("सुंधी गुंथी रे, पहेरावी प्रभु कंठे तेर, शत्र मारगनी सिद्धि रे. आज० છ.", [None]),
             ("संवत पंदर सत्याशी वर्षे, बादशाह १० वरस रहे", [])]
    for t, want in cases:
        lines, _ = classify_book([page(1, [(t, 60, 350)])], CFG)
        assert [n for _, n in lines[0].marks] == want, t


def test_number_with_a_missing_closing_danda_is_a_mark():
    for t, n in (("शांति चौमासुं रहीया, सुरनर पति मन भाव्यां ॥ भवि०॥१", 1),
                 ("जयराम मुनिश्र, सिद्ध थया नही होय ॥ भवि० ॥११)।", 11)):
        lines, _ = classify_book([page(1, [(t, 60, 350)])], CFG)
        assert [m for _, m in lines[0].marks] == [n], t


def test_dash_style_footnotes_are_notes():
    t = "૧-વૃક્ષ, ૨-સુંદર 3-ચાલ્યો ગયો છે વિકાર જેનો."
    assert kind_of([gpage(1, SAJ[:2] + [(t, 60, 250, 85)] + SAJ[:2])], t) == "note"


# ---- round 2, S002803 (pad heading printed on the same line as the first verse)
def test_inline_pad_heading_is_split_from_the_first_verse():
    t = "पद्‌ त्रीजुं ॥ राग केरबो ॥ प्रभु मेरे तुम बिन कौन सहाय, मोरे"
    lines, _ = classify_book([page(1, VERSES + [(t, 60, 350)] + VERSES)], CFG)
    got = [(ln.kind, ln.text) for ln in lines if ln.text in t]
    assert [x[1] for x in got] == ["पद्‌ त्रीजुं ॥ राग केरबो ॥", "प्रभु मेरे तुम बिन कौन सहाय, मोरे"]
    assert got[0][0] == "heading"


# ---- round 2, B002198 (run-on stavans numbered "cue n." with the cue's ० misread)
def test_number_with_a_full_stop_after_a_short_cue_word_is_a_mark():
    for t, want in (("સ્મરણુ કરવા લાગીરે. સ્હાવ ૧૩. સહુ મુખ", [13]),
                    ("તે ભવમાં અટે રે લો માટ ૪. જિ૦ સાંભળો", [4]),
                    ("ભયસાયર તરે રે લો. સા પ. જિન ગુણ", [None])):
        lines, _ = classify_book([page(1, [(t, 60, 350)])], CFG)
        assert [n for _, n in lines[0].marks] == want, t


# ---- round 2, B004897 (each verse followed by a numbered explanation paragraph)
def test_numbered_explanation_paragraph_is_prose():
    rows = [("બેસતા વર્ષ પરોઢિયે, પામ્યા કેવલનાણે;", 100, 300, 85),
            ("સુણતાં ભણતાં સંપજે, દિન દિન મંગલમાલ. ૩", 100, 310, 85),
            ("૩. કાર્તિક સુદિ એકમે બેસતું વર્ષ ઊજવાય છે. તે દિવસે વહેલી સવારે", 60, 340, 85),
            ("ગૌતમસ્વામીને કેવળજ્ઞાન થયું હતું તેથી આ દિવસ મંગલ ગણાય", 60, 340, 85),
            ("છે અને સૌ તેમનું સ્મરણ કરે છે.", 60, 200, 85),
            ("વિશાખાનંદી સિંહ થયો, વાસુદેવના હાથ;", 100, 300, 85),
            ("સત્યાવીશમા ભવ વિશે, તે ત્રિપૃષ્ઠ વીર યાય. ૪", 100, 310, 85)]
    ks = kinds([gpage(1, rows)])
    assert [k for _, k in ks] == ["verse", "verse", "prose", "prose", "prose", "verse", "verse"]


# ---- round 3, B018723 (each gatha closes with a short right-aligned refrain line + number)
def test_short_refrain_line_ending_in_a_letter_digit_is_a_mark():
    rows = [("મેવા ફળ-ફુલ લાવતો હું તમારા આવાસજી", 60, 260, 85),
            ("પ્રીતિ ઘરો પ્રેમદા મુજથી उ", 230, 330, 85)]
    lines, _ = classify_book([gpage(1, SAJ[:2] + rows)], CFG)
    assert [n for _, n in lines[3].marks] == [None]


def test_of_two_adjacent_numbers_the_cue_is_the_one_ending_in_zero():
    lines, _ = classify_book([page(1, [("अरबुदथी पेसी वधै। घनमांस कहात ॥ २१॥ ૭૦ ॥ मांसतणी", 60, 350)])], CFG)
    assert [n for _, n in lines[0].marks] == [21]


def test_centred_serial_missing_its_opening_bracket_is_a_heading():
    for t in ("6)", "ઉ)"):
        pages = [gpage(1, SAJ[:2] + [(t, 200, 215, 80)] + SAJ[:2])]
        assert kind_of(pages, t) == "heading", t


# --- Kruti headings by the books' common conventions (round 4) ---
PREV_END = [("एक गाथानी पहेली लीटी लखेली छे,", LEFT, 330), ("एनी बीजी लीटी अहीं पूरी थाय छे ॥4॥", LEFT, 330)]
NEXT = [("पहेली नवी गाथा अहीं शरु थाय, हवे आगळ", 90, 330), ("बीजी लीटी अहीं पूरी थाय छे भाई ॥1॥", 90, 330)]


def test_serial_type_word_heading():
    """"ગાયન ૨૨ મું. રાગ …": a type word with its serial number heads a Kruti, even flush left."""
    pages = [page(1, PREV_END + [("ગાયન ૨૨ મું. રાગ કેદારો,", LEFT, 250)] + NEXT)]
    assert kind_of(pages, "ગાયન ૨૨ મું. રાગ કેદારો,") == "heading"


def test_garbled_type_word_with_serial_is_heading():
    pages = [page(1, PREV_END + [("સ્તવના ૮ મી,-રાગ કેદારો તથા ગોડી,", 120, 300)] + NEXT)]
    assert kind_of(pages, "સ્તવના ૮ મી,-રાગ કેદારો તથા ગોડી,") == "heading"


def test_atha_opener_is_heading():
    """"॥ अथ काया उपर लावणी चोपनमी ॥" and "… स्तवन लिख्यते": the old opener of a Kruti."""
    for title in ("॥ अथ काया उपर लावणी चोपनमी ॥", "॥ श्रीमंदीर बहरमानरो स्तवन लीख्यंते ॥"):
        pages = [page(1, PREV_END + [(title, 90, 320)] + NEXT)]
        assert kind_of(pages, title) == "heading", title


def test_line_above_tune_line_is_heading():
    """The short line just above a tune line ("… --એ દેશી") names the Kruti."""
    pages = [page(1, PREV_END + [("શ્રી સુવિધિ જિનરાજ નવમા", 130, 280),
                                  ("એંમ ધના ધણને પરણાવે.--એ દેશી,", 130, 290)] + NEXT)]
    assert kind_of(pages, "શ્રી સુવિધિ જિનરાજ નવમા") == "heading"


def test_verse_with_number_inside_stays_verse():
    """A verse line that merely contains a type word and a number is not a heading."""
    line = ("पद ४ सुणीने भवि प्राणी, समकित गुण पामे रे,", 90, 330)
    pages = [page(1, PREV_END + NEXT[:1] + [line] + NEXT[1:])]
    assert kind_of(pages, line[0]) == "verse"


def test_line_end_numbers_in_sequence_are_gatha_marks():
    """"… સખિ ૭,": a bare number ending a line is a gatha number when it continues the count."""
    rows = [("ગાયન ૮ મું", 150, 260)]
    for n in (1, 2, 3):
        rows += [(f"પહેલી લીટી અહીં ચાલે ને આગળ વધે ગાથા {'એક બે ત્રણ'.split()[n-1]}; સખિ", 60, 330),
                 (f"બીજી લીટી અહીં પૂરી થાય છે વળી, સખિ {'૧૨૩'[n-1]},", 60, 340)]
    lines, _ = classify_book([page(1, rows)], CFG)
    ends = [ln.marks[-1][1] for ln in lines if ln.marks]
    assert ends == [1, 2, 3]


def test_line_end_number_out_of_sequence_is_not_a_mark():
    rows = [("ગાયન ૮ મું", 150, 260),
            ("પહેલી લીટી અહીં ચાલે ને આગળ વધે ભાઈ; સખિ", 60, 330),
            ("બીજી લીટી અહીં પૂરી થાય છે વળી, વરસ ૪૫,", 60, 340)]
    lines, _ = classify_book([page(1, rows)], CFG)
    assert not any(ln.marks for ln in lines)


def test_modern_likhte_in_prose_is_not_a_heading():
    line = ("अनुभव को अभिव्यक्त करते हुए आप लिखते हैं-", LEFT, 280)
    pages = [page(1, PROSE[:3] + [line] + [("धन धन दिन मुझ आज नो रे", 90, 250),
                                            ("दोष सकल दूरे गया रे ॥5॥", 90, 250)] + PROSE[:3])]
    assert kind_of(pages, line[0]) != "heading"


def test_centred_bare_number_between_kruti_is_a_serial_heading():
    """"१२" centred between two Kruti, not at the page's top or bottom: a Kruti serial."""
    rows = [("मथाळुं", 180, 240)] + PREV_END + [("१२", 205, 215, 1.5)] + NEXT + PREV_END[:1] + [("४३", 205, 215)]
    lines, _ = classify_book([page(1, rows)], CFG)
    kinds_ = {ln.text: ln.kind for ln in lines}
    assert kinds_["१२"] == "heading"
    assert kinds_["४३"] != "heading"            # the page number at the bottom


def test_centred_number_inside_an_open_gatha_is_not_a_serial():
    rows = [("मथाळुं", 180, 240)] + PREV_END + [("शासन नायक वीरजी, पन केवल पायो,", LEFT, 300),
                                               ("१", 205, 215), ("संघ चतुविध स्थापवा, महसेन वन आयो ॥1॥", LEFT, 330)] + NEXT
    lines, _ = classify_book([page(1, rows)], CFG)
    assert {ln.text: ln.kind for ln in lines}["१"] != "heading"
