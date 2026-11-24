"""Gatha Lines: Kruti and gathas from classed lines.   Run:  python -m pytest tests"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kruti.gatha import Gatha, confidence, split_gathas      # noqa: E402
from kruti.gatha_lines import TLine, gatha_config, mark_text  # noqa: E402
from kruti.krutis import verse_pattern                        # noqa: E402

CFG = gatha_config(None)
_PAT = verse_pattern("")


def L(text, kind="verse", page=1, gap=0.0, conf=90.0, indent=0.1, source="ocr"):
    from kruti.gatha_lines import _marks
    marks = _marks(_PAT, text) if kind == "verse" else []
    from kruti.normalize import light_normalize
    return TLine(page, text, light_normalize(text), kind, conf, source, gap, indent, 0.6, marks)


def gathas(lines):
    return [g for k in split_gathas(lines, CFG) for g in k.gathas]


def numbered(n, prefix="पद"):
    """n gathas of two lines each: "<prefix> i क," / "<prefix> i ख ॥i॥"."""
    out = []
    for i in range(1, n + 1):
        out += [L(f"{prefix} {i} क,"), L(f"{prefix} {i} ख ॥{i}॥")]
    return out


def test_numbered_gathas_first_and_last_line():
    ks = split_gathas([L("शांतिनाथ स्तवन", "heading")] + numbered(3), CFG)
    assert len(ks) == 1 and ks[0].title == "शांतिनाथ स्तवन"
    g = ks[0].gathas
    assert [x.no for x in g] == ["1", "2", "3"]
    assert (g[1].first, g[1].last) == ("पद 2 क,", "पद 2 ख ॥2॥")
    assert all(x.how == "Numbered verse" for x in g)


def test_tune_line_not_in_gatha_one():
    ks = split_gathas([L("शांतिनाथ स्तवन", "heading"), L("राग - आशावरी", "tune")] + numbered(2), CFG)
    assert ks[0].gathas[0].first == "पद 1 क,"


def test_explanation_between_gathas_skipped():
    prose = [L("भावार्थ- हे प्रभु आप", "prose"), L("जगत के नाथ हैं और", "prose"),
             L("सबका कल्याण करते हैं।", "prose")]
    g = numbered(3)
    ks = split_gathas([L("स्तवन", "heading")] + g[:2] + prose + g[2:4] + prose + g[4:], CFG)
    assert len(ks) == 1
    assert [x.no for x in ks[0].gathas] == ["1", "2", "3"]
    assert "next to prose" in ks[0].gathas[1].checks


def test_quoted_verse_inside_explanation_ignored():
    g = numbered(3)
    quote = [L("अर्थ: जैसे कहा है “ धर्म मंगल ॥2॥ ” ऐसा", "prose")]
    ks = split_gathas([L("स्तवन", "heading")] + g[:2] + quote + g[2:], CFG)
    assert [x.no for x in ks[0].gathas] == ["1", "2", "3"]


def test_restart_at_one_starts_new_kruti():
    ks = split_gathas(numbered(3) + numbered(2, "अन्य"), CFG)
    assert [len(k.gathas) for k in ks] == [3, 2]
    assert ks[1].gathas[0].first == "अन्य 1 क,"


def test_part_heading_keeps_kruti():
    ks = split_gathas(numbered(2) + [L("ढाल बीजी", "part")] + numbered(2, "बीजी"), CFG)
    assert len(ks) == 1
    assert [(x.part, x.no) for x in ks[0].gathas] == [("", "1"), ("", "2"), ("ढाल बीजी", "1"),
                                                      ("ढाल बीजी", "2")]


def test_garbled_number_inferred():
    lines = numbered(3)
    lines[3] = L("पद 2 ख ॥]॥")
    g = gathas(lines)
    assert g[1].no == "2" and g[1].how == "Number inferred (OCR garbled)"
    assert g[0].how == g[2].how == "Numbered verse"


def test_misread_number_fixed_by_sequence():
    lines = numbered(5)
    lines[7] = L("पद 4 ख ॥5॥")              # OCR read 4 as 5; the next one is 5 again
    g = gathas(lines)
    assert [x.no for x in g] == ["1", "2", "3", "4", "5"]
    assert g[3].how == "Number inferred (OCR garbled)"


def test_unnumbered_by_gap():
    lines = []
    for i in range(4):
        lines += [L(f"पंक्ति {i} क,", gap=1.2 if i else 0.0), L(f"पंक्ति {i} ख ।")]
    g = gathas([L("पद", "heading")] + lines)
    assert [x.no for x in g] == ["(1)", "(2)", "(3)", "(4)"]
    assert all(x.how == "No number - gap" for x in g)
    assert (g[2].first, g[2].last) == ("पंक्ति 2 क,", "पंक्ति 2 ख ।")


def test_unnumbered_by_indent():
    lines = []
    for i in range(4):
        lines += [L(f"पंक्ति {i} क,", indent=0.1), L(f"पंक्ति {i} ख ।", indent=0.25)]
    g = gathas([L("पद", "heading")] + lines)
    assert len(g) == 4 and g[1].first == "पंक्ति 1 क,"
    assert all(x.how == "No number - gap" for x in g)


def test_unnumbered_by_line_count():
    ends = [",", ";", ",", "॥"] * 2
    lines = [L(f"पंक्ति {'कखगघङचछज'[i]} {e}") for i, e in enumerate(ends)]
    g = gathas([L("पद", "heading")] + lines)
    assert len(g) == 2 and all(x.how == "No number - line count" for x in g)
    assert (g[1].first, g[1].last) == ("पंक्ति ङ ,", "पंक्ति ज ॥")


def test_unnumbered_without_agreeing_ends_not_split():
    lines = [L(f"पंक्ति {i}") for i in range(8)]
    assert split_gathas([L("पद", "heading")] + lines, CFG) == []


def test_run_on_line_splits_at_marks():
    g = gathas([L("स्तवन", "heading"), L("अ ब क ॥1॥ ड ए फ ॥2॥ ग ह इ ॥3॥")])
    assert [(x.first, x.last) for x in g] == [("अ ब क ॥1॥",) * 2, ("ड ए फ ॥2॥",) * 2,
                                              ("ग ह इ ॥3॥",) * 2]


def test_gatha_across_pages():
    lines = numbered(3)
    lines[3] = L("पद 2 ख ॥2॥", page=2)
    lines[4:] = [L(x.text, page=2) for x in lines[4:]]
    g = gathas([L("स्तवन", "heading")] + lines)
    assert g[1].pages == (1, 2) and "crosses pages" in g[1].checks
    assert g[0].pages == (1, 1)


def test_single_gatha_kruti_dropped():
    assert split_gathas([L("स्तवन", "heading")] + numbered(1), CFG) == []


def test_gujarati_numbers_and_script_kept():
    lines = [L("શ્રી મહસેન નરેશ નંદ,"), L("શશિ લાંછન ઉજ્જ્વલ વરણ ॥૧॥"),
             L("ધનુષ દોઢ સૈ માન ચારુ,"), L("આયુ બરસ દશ લાખ પૂર્વ ॥૨॥")]
    g = gathas([L("સ્તવન", "heading")] + lines)
    assert [x.no for x in g] == ["1", "2"]
    assert (g[0].first, g[0].last) == ("શ્રી મહસેન નરેશ નંદ,", "શશિ લાંછન ઉજ્જ્વલ વરણ ॥૧॥")


def test_no_heading_check_and_sources():
    g = gathas(numbered(2))
    assert "no heading" in g[0].checks
    g = gathas([L("स्तवन", "heading")] + [L(x.text, source="text", conf=100) for x in numbered(2)])
    assert g[0].source == "Text layer" and g[0].conf == 100 and g[0].checks == []


def test_confidence_levels():
    def mk(how, conf=95, checks=()):
        return Gatha("", "1", "a", "b", (1, 1), how, conf, "OCR", list(checks))
    assert confidence(mk("Numbered verse"), 70) == "High"
    assert confidence(mk("No number - gap"), 70) == "Medium"
    assert confidence(mk("Number inferred (OCR garbled)"), 70) == "Medium"
    assert confidence(mk("Numbered verse", checks=["crosses pages"]), 70) == "Medium"
    assert confidence(mk("No number - line count"), 70) == "Low"
    assert confidence(mk("Numbered verse", conf=60), 70) == "Low"
    assert confidence(mk("Numbered verse", checks=["a", "b"]), 70) == "Low"


def test_repeated_number_closing_an_explanation_is_not_a_gatha():
    lines = numbered(2)[:2] + [L("भावार्थ- आ गाथानो अर्थ", "prose"),
                               L("सिद्धांतमां कह्युं छे ए भाव ॥1॥")] + numbered(3)[2:]
    g = gathas([L("स्तवन", "heading")] + lines)
    assert [x.no for x in g] == ["1", "2", "3"]
    assert g[1].first == "पद 2 क,"


def test_first_number_of_a_part_misread():
    lines = [L("ढाल पांचमी", "part"), L("पद 1 क,"), L("पद 1 ख ॥9॥"), L("पद 2 क,"), L("पद 2 ख ॥2॥"),
             L("पद 3 क,"), L("पद 3 ख ॥3॥")]
    g = gathas([L("स्तवन", "heading")] + lines)
    assert [x.no for x in g] == ["1", "2", "3"] and g[0].how == "Number inferred (OCR garbled)"


def test_refrain_cue_read_as_a_number_is_not_a_mark():
    lines = []
    for i in range(1, 5):
        cue = L(f"પદ {i} ક, ३०")
        cue.marks = [(len(cue.text), 30)]      # a book numbering verses at the line end
        lines += [cue, L(f"પદ {i} ખ. રૂડા૦ ॥{i}॥")]
    g = gathas([L("સજ્ઝાય", "heading")] + lines)
    assert [x.no for x in g] == ["1", "2", "3", "4"]
    assert (g[1].first, g[1].last) == ("પદ 2 ક, ३०", "પદ 2 ખ. રૂડા૦ ॥2॥")


def test_recurring_cue_number_dropped_even_next_to_a_misread_number():
    lines, nums = [], [7, 8, 3, 10, 11, 12]              # 9 misread as 3
    for i, n in zip(range(7, 13), nums):
        cue = L(f"પદ {i} ક, ३०")
        cue.marks = [(len(cue.text), 30)]
        end = L(f"પદ {i} ખ. ધન્ય૦ {n}")
        end.marks = [(len(end.text), n)]
        lines += [cue, end]
    g = gathas([L("સજ્ઝાય", "heading")] + lines)
    assert len(g) == 6 and all(x.first.endswith("३०") for x in g)


def test_gatha_with_a_lost_number_is_split_by_the_usual_line_count():
    lines = numbered(5)
    lines[5] = L("पद 3 ख")                     # gatha 3's number lost in OCR
    g = gathas([L("स्तवन", "heading")] + lines)
    assert [x.no for x in g] == ["1", "2", "3", "4", "5"]
    assert (g[2].first, g[2].last) == ("पद 3 क,", "पद 3 ख")
    assert (g[3].first, g[3].last) == ("पद 4 क,", "पद 4 ख ॥4॥")
    assert g[2].how == "Number inferred (OCR garbled)"


def test_unnumbered_stanzas_end_at_their_refrain_cue():
    rows = ["વીર સંજમ લીયું રે, પંચસયા પરિવાર", "છઠ છઠ તપને પારણે રે,",
            "કરતાં ઉગ્ર વિહાર....જયંકર જીવો ગૌતમ સ્વામ.",
            "અષ્ટાપદ લબ્ધિએ ચડ્યા રે, વાંદ્યા જિન ચોવીસ", "જગ ચિંતામણી તિહાં કીયું રે",
            "સ્તવિયા શ્રી જગદીશ....જયંકર જીવો ગૌતમ સ્વામ.",
            "પનરસે તાપસ પારણે રે, ખીર ખાંડ ઘૃત ભરપુર", "અમિય જાસ અંગૂઠડો રે,",
            "ઉગ્યો કેવલસૂર....જયંકર જીવો ગૌતમ સ્વામ."]
    g = gathas([L("ગૌતમસ્વામીનું સ્તવન", "heading")] + [L(r) for r in rows])
    assert [(x.first, x.last) for x in g] == [(rows[0], rows[2]), (rows[3], rows[5]), (rows[6], rows[8])]
    assert all(x.how == "No number - gap" for x in g)


def test_restart_after_a_named_part_is_the_next_part():
    lines = [L("( દોહા )", "part")] + numbered(3) + numbered(3, "ઢાલ")
    ks = split_gathas([L("સંગ્રામ સોનીની સજઝાય", "heading")] + lines, CFG)
    assert len(ks) == 1 and len(ks[0].gathas) == 6
    assert ks[0].gathas[0].part == "( દોહા )" and ks[0].gathas[3].part != "( દોહા )"


def test_refrain_cue_ending_a_gatha_whose_number_was_lost():
    lines = []
    for i in range(1, 6):
        end = f"પદ {i} ખ રે. મનડુ'૦" + (f" ॥{i}॥" if i in (1, 5) else "")
        lines += [L(f"પદ {i} ક રે;"), L(end)]
    g = gathas([L("સજઝાય", "heading")] + lines)
    assert [x.no for x in g] == ["1", "2", "3", "4", "5"]
    assert g[2].first == "પદ 3 ક રે;"


def test_restart_inside_a_named_part_even_when_the_next_number_is_garbled():
    lines = [L("( દોહા )", "part")] + numbered(3) + numbered(4, "ઢાલ")
    lines[9] = L("ઢાલ 2 ખ ર")                      # gatha 2 of the dhal: number OCR'd as ર
    ks = split_gathas([L("સંગ્રામ સોનીની સજઝાય", "heading")] + lines, CFG)
    assert len(ks) == 1


def test_double_danda_at_every_half_line_is_not_a_verse_mark():
    rows = []
    for i in range(1, 4):
        rows += [L(f"पद {i} पहली पंक्ति लाल।।"), L(f"पद {i} दूसरी पंक्ति लाल।।"), L(f"{i}।।")]
    g = gathas([L("स्तवन", "heading")] + rows)
    assert [x.no for x in g] == ["1", "2", "3"]
    assert (g[1].first, g[1].last) == ("पद 2 पहली पंक्ति लाल।।", "पद 2 दूसरी पंक्ति लाल।। 2।।")


# ---- found on the tuning book B052034's front matter (title page, biography, editor's note)
def test_title_page_lines_are_not_unnumbered_gathas():
    rows = ["आशीर्वाद", "आचार्य भगवंत श्री जिनमणिप्रभसूरिजी म.", "संपादक", "मूल्य : 50 रुपये",
            "प्रतियाँ : 500", "प्रकाशन वर्ष : ईसवी सन्‌ 2016"]
    lines = [L(r, gap=1.2 if i % 2 == 0 and i else 0.0) for i, r in enumerate(rows)]
    assert split_gathas(lines, CFG) == []


def test_verses_quoted_inside_a_biography_are_left_out():
    prose = [L("उन्होंने इस विषय पर अनेक रचनाएँ कीं जिनमें से एक यह है", "prose")]
    quote = [L("प्रभु दर्शन थी दर्शन होय, अतिनिर्मल तिम पावन होय ।"),
             L("दर्शनथी दुःख जावे दूर, प्रगट हुवे सुख संपद पूर ।।3॥"),
             L("एहथी दूर टले कुविचार, उपजे दिल आनंद अपार ।"),
             L("उत्तम ध्यान नो कारण एह, तिम वलि सहज समाधि नो गेह।।4।")]
    after = [L("इस प्रकार उनकी भक्ति प्रकट होती है और आगे वे लिखते हैं", "prose")]
    assert split_gathas(prose + quote + after, CFG) == []


def test_several_quotes_in_one_biography_are_all_left_out():
    def prose(n):
        return [L(f"उन्होंने अनेक रचनाएँ कीं और यह पंक्ति {i} है", "prose") for i in range(n)]
    q1 = [L("प्रभु दर्शन थी दर्शन होय, पावन होय ।"), L("दर्शनथी दुःख जावे दूर, सुख पूर ।।3॥"),
          L("एहथी दूर टले कुविचार, आनंद अपार ।"), L("उत्तम ध्यान नो कारण एह, गेह।।4।")]
    q2 = [L("अनुभव दे दुय भेदनो रे, शुद्ध स्वरूप ।"), L("शुद्ध सदा मुझ दीजिये रे, विरूप ।।3॥।"),
          L("सुध अनुभव थी संपजे रे, व्यवहार ।"), L("निरविध ने तेहथी मले रे, सुखकार ।।4॥")]
    assert split_gathas(prose(3) + q1 + prose(4) + q2 + prose(2), CFG) == []


def test_prose_without_an_opener_ends_a_kruti():
    def prose(n):
        return [L(f"उन्होंने अनेक रचनाएँ कीं और यह पंक्ति {i} है", "prose") for i in range(n)]
    def quote(a):
        return [x for i in range(a, a + 3) for x in (L(f"पद {i} पहली पंक्ति ।"), L(f"पद {i} दूसरी पंक्ति ॥{i}॥"))]
    assert split_gathas(prose(3) + quote(3) + prose(4) + quote(7) + prose(3) + quote(2) + prose(2), CFG) == []


def test_refrain_cue_after_a_semicolon_does_not_end_the_gatha():
    rows = []
    for i in range(1, 4):
        rows += [L(f"पद {i} पहली पंक्ति सिरदार; ऐसें०।"), L(f"पद {i} दूसरी पंक्ति विचार।।एसें०।।{i}॥")]
    g = gathas([L("होरी", "heading")] + rows)
    assert [x.no for x in g] == ["1", "2", "3"]
    assert g[1].first == "पद 2 पहली पंक्ति सिरदार; ऐसें०।"


def test_the_same_garbled_number_on_every_stanza_is_renumbered():
    rows = []
    for i in range(1, 4):
        rows += [L(f"पद {i} पहली पंक्ति ;"), L(f"पद {i} दूसरी पंक्ति."), L("... हो साहिब ससनेहा. ॥9॥")]
    g = gathas([L("स्तवन", "heading")] + rows)
    assert [x.no for x in g] == ["1", "2", "3"]


def test_tune_line_after_a_finished_gatha_starts_a_new_kruti():
    lines = numbered(3) + [L("(राग - शत्रुंजय मंडन ऋषभ जिणंद दयाल.)", "tune")] + numbered(3, "स्तुति")
    lines[7:] = [L(x.text.replace("॥1॥", "॥9॥")) if "॥1॥" in x.text else x for x in lines[7:]]
    ks = split_gathas([L("स्तवन", "heading")] + lines, CFG)
    assert [len(k.gathas) for k in ks] == [3, 3]


def test_last_piece_of_only_a_cue_and_number_joins_the_line_before():
    rows = [L("पद एक पहली पंक्ति रे,"), L("पद एक दूसरी पंक्ति रे. आज० 1. पद दो पहली रे,"),
            L("पद दो दूसरी पंक्ति काया रे."), L("आज० 2. पद तीन पहली रे,"), L("पद तीन दूसरी रे. आज० 3.")]
    g = gathas([L("स्तवन", "heading")] + rows)
    assert g[1].last == "पद दो दूसरी पंक्ति काया रे. आज० 2."


def test_garbled_last_number_before_the_next_kruti_is_kept():
    lines = numbered(4)
    lines += [L("પદ 5 ક રે,"), L("બોલતાં બેસતા સાંભરે રે, ખિમાવિજય જિન નામ રે. પ")]
    lines += numbered(3, "બીજું")
    ks = split_gathas([L("સ્તવન", "heading")] + lines, CFG)
    assert [len(k.gathas) for k in ks] == [5, 3]


def test_garbled_marks_between_consecutive_numbers_are_still_pruned():
    rows = []
    for i in range(1, 4):
        rows += [L(f"પદ {i} ક રે; ર"), L(f"પદ {i} ખ રે. ॥{i}॥")]     # "ર" after a half-line ;
    g = gathas([L("સજઝાય", "heading")] + rows)
    assert [x.no for x in g] == ["1", "2", "3"]
