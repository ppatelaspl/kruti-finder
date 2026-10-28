"""Kruti boundaries: a heading must start a new Kruti, never become part of the
previous Kruti's text.   Run:  python -m pytest tests"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kruti.config import merged                      # noqa: E402
from kruti.extract import PageText                   # noqa: E402
from kruti.krutis import find_krutis                 # noqa: E402
from kruti.matcher import Book                       # noqa: E402

PREVIOUS = ("शांतिनाथ स्तवन.\n"
            "शांति जिनेसर सोलमा, अचिरा सुत वंदो ॥1॥ विश्वसेन कुल नभ मणि, भविजन सुख कंदो ॥2॥ "
            "मृग लंछन जिन आउखुं, लाख वरस प्रमाण ॥3॥ ज्ञान विमल सूरि गुण गावे, पामे परम कल्याण ॥")
# the user's example, exactly as OCR produced it (one run-on line)
EXAMPLE = ("16॥ नेमनाथजीनी लावणी. । सजन समजावो आपने मनुं रे, सजन समजावो अपने दिलकुं ॥ मत नवो "
           "गिरनार नेम फिर, क्या करनां 556 ॥ मे आंकणी । सती राजील मन नंहीं माने रे ॥ सतीन ॥ बांक "
           "बिन ऊठगचे गिरवरकुं, बन बेठे ध्याने ॥ झूरती मूझी, महाराज । 20 ॥")


def _krutis(text, names=()):
    book = Book.from_pages("book.pdf", [PageText(1, "ocr", 90.0, text)])
    return find_krutis(book, {1: 90.0}, merged(None), names)


def test_heading_after_number_starts_new_kruti():
    ks = _krutis(PREVIOUS + EXAMPLE)
    assert [k.title for k in ks] == ["शांतिनाथ स्तवन", "नेमनाथजीनी लावणी"]
    prev, nem = ks
    assert "नेमनाथजीनी" not in prev.ant and "सजन" not in prev.ant
    assert prev.ant.startswith("ज्ञान विमल सूरि")
    assert nem.aadi.startswith("सजन समजावो आपने मनुं रे")
    assert "लावणी" not in nem.aadi


def test_refrain_marker_is_not_a_heading():
    # "मे आंकणी" (refrain) sits after a number and a danda too, but is not a Kruti name
    ks = _krutis(PREVIOUS + EXAMPLE)
    assert not any("आंकणी" in k.title for k in ks)


def test_heading_confirmed_by_verses_restarting():
    # no Kruti-type word and not in the Excel, but verse numbers restart at 1 after it
    text = PREVIOUS + ("16॥ श्री गौतम गणधर गुण. । गौतम स्वामी गुण गावुं, लब्धि तणा भंडार ॥1॥ "
                       "प्रह ऊठी नित प्रणमीए, पामे भवनो पार ॥2॥")
    ks = _krutis(text)
    assert [k.title for k in ks] == ["शांतिनाथ स्तवन", "श्री गौतम गणधर गुण"]
    assert ks[1].aadi.startswith("गौतम स्वामी गुण गावुं")


def test_excel_name_starts_new_kruti_even_without_restart():
    # numbering runs on (OCR/print), so only the Excel name can reveal the boundary
    text = PREVIOUS + ("16॥ श्री गौतम गणधर गुण. । गौतम स्वामी गुण गावुं, लब्धि तणा भंडार ॥17॥ "
                       "प्रह ऊठी नित प्रणमीए, पामे भवनो पार ॥18॥")
    assert [k.title for k in _krutis(text)] == ["शांतिनाथ स्तवन"]
    ks = _krutis(text, names=["श्री गौतम गणधर गुण"])
    assert [k.title for k in ks] == ["शांतिनाथ स्तवन", "श्री गौतम गणधर गुण"]
    assert "गौतम" not in ks[0].ant


def test_ocr_variant_of_excel_name_is_tolerated():
    text = PREVIOUS + ("16॥ श्री गोतम गणधर गुन. । गौतम स्वामी गुण गावुं, लब्धि तणा भंडार ॥1॥ "
                       "प्रह ऊठी नित प्रणमीए, पामे भवनो पार ॥2॥")
    ks = _krutis(text, names=["श्री गौतम गणधर गुण"])
    assert len(ks) == 2 and ks[1].aadi.startswith("गौतम स्वामी")


def test_verse_line_is_not_a_heading():
    # an ordinary verse after a number, even one containing a type word, stays content
    text = ("शांतिनाथ स्तवन.\nशांति जिनेसर सोलमा, अचिरा सुत वंदो ॥1॥ "
            "गावो प्रभुनुं स्तवन, मनमां धरी उल्लास रे ॥2॥ पामे परम कल्याण ॥3॥")
    ks = _krutis(text)
    assert len(ks) == 1 and ks[0].verses == 3


def test_aadi_has_no_leading_danda():
    text = PREVIOUS + "16॥ नेमनाथजीनी लावणी. ॥ सजन समजावो आपने मनुं रे, सजन समजावो अपने ॥1॥ बीजी कडी ॥2॥"
    assert _krutis(text)[1].aadi.startswith("सजन समजावो")


def test_ant_is_a_real_line_not_a_refrain_fragment():
    # "॥ मत । ॥" (a refrain cue between dandas) must not become the whole Ant Vakya
    text = ("नेमजीनी लावणी.\nसजन समजावो आपने मनुं रे ॥1॥ बांक बिन ऊठगचे गिरवरकुं, बन बेठे ध्याने "
            "॥2॥ झूरती मूझी राजुल नारी, नेम गया गिरनार ॥3॥ मत । ॥")
    ant = _krutis(text)[0].ant
    assert "झूरती मूझी राजुल नारी" in ant


def test_title_drops_ocr_number_prefix():
    text = PREVIOUS + "16॥ 8569 लावणी. । अगम पंथ जानां हे भाई रे, ग्यान ध्यान धरो ॥1॥ बीजी कडी रे ॥2॥"
    assert _krutis(text)[1].title == "लावणी"


def test_aadi_falls_back_to_next_verse_when_opening_is_only_numbers():
    text = PREVIOUS + "16॥ उपदेश लावणी. ॥1॥ सुरग आस मत करे कलेशी, कुमति संग छायो ॥2॥ बीजी कडी रे भाई ॥3॥"
    assert _krutis(text)[1].aadi.startswith("सुरग आस मत करे कलेशी")


# Real OCR from Jain-lavani p.25: a Kruti ends "॥ 6॥ ॥98॥" - verse 6, then the book's
# running Kruti number 98 - followed by the next Kruti's heading.
LAVANI_END = ("नेमनाथजीनी लावणी.\nकुं मै अबला हुं अजाणु लाल, तेरे दरसनकी भूखी ॥ 1 ॥ जलो जगतकी जाल, "
              "सखी संपतकुं कया करनी ॥ 2 ॥ (24 प्यार, भार मेरेरिर पर सख धरता ॥ 020 ॥ मेरो आदर नहि कोय "
              "डरता ॥ 3 ॥ दोहा ॥ आग लगो सुख सेजकुं, मालक दीनी मूक ॥ रुल परमे कायम रहि) सो रती पडी "
              "नहिं चूक ॥ भलां सो ॥ 6॥ ॥98॥\nनेमजीनी लावणी.\n॥ अने हांरे पिया बिन झुर झुर, खे झुर झुर "
              "हुई खूनी ॥ 1 ॥ पियु गिरनार गये रे ॥ 2 ॥")


def test_running_kruti_number_is_not_a_verse_count():
    ks = _krutis(LAVANI_END)
    assert [k.title for k in ks] == ["नेमनाथजीनी लावणी", "नेमजीनी लावणी"]
    assert ks[0].verses == 6


def test_ant_is_the_last_line_not_refrain_or_numbers():
    ant = _krutis(LAVANI_END)[0].ant
    assert "पडी नहिं चूक" in ant
    assert len(ant) < 120 and "डरता" not in ant


def test_ocr_variant_of_type_word():
    # OCR reads लावणी as लावणुं; no restart and no Excel name to vouch for it
    text = PREVIOUS + "16॥ नेमजीनी लावणुं. । सजन बिन सुना, मेरी जान सजन बिन सुना ॥ 17 ॥ बीजी कडी रे ॥ 18 ॥"
    assert [k.title for k in _krutis(text)] == ["शांतिनाथ स्तवन", "नेमजीनी लावणुं"]


# Real OCR, S037974_chaityavandan_chauvisi p.16-17: verses end "...1..." / "...2" / "..."
# and each heading is "<name> नु [serial]" (the bracket often OCR-garbled).
CHAITYA_P16 = """धनुष अढीसें देहमान, कोसंबीराय,
श्रीधर धरणीधर पिता, गयु सुशीमा माय...2
तीस लाख पूरव तणुं अ, भोगवी जीवित मान,
अविचल पदवी पामीओ, मान करे नितु ध्यान.
सुपाश्वेनाथ नु [छ]
सुपरि सुरजन सेविओ, सुखकारी गुवार,
स्वस्तिक लंछन मांगलिक, सघठाने उल्लास... 1...
सोवन वन तनु दोयसें, धनुमान उत्तंग,
वीश लाख पूरव तणुं, जीवित जस चंग...2...
वाणारसी नयरी वळीगे, जिनवर जगविख्यात,
पृथ्वी मात प्रतिष्ठ तात, सानविजय गुण पात...र...
चद्रप्रमु गु [8]
चंद्रपरभु जिन चंद्रसौम्य, पुरी चंद्रा राय,
कान्ति चंद्र हार्यो रहे, लंछन मसे पाय...?
लाख पूरव देश आय जास, जगमां विख्यात,
नुप महसेन ने लक्ष्मणा, केरो अंगजात...2...
दोढसो धनुष मित देहडी ए, जीवन जगदाधार,
मानविजय कवियण कहे, आवागमन निवार...3...
सुविधिनाथ नु" [6]
सुविधि सुविधिसु सेवि, जिणे सुविधि प्रकाश्यो,
आपे चारित्र आदरी, विधि योग अभ्यास्यो... 1...
काकंदी नुपति सुग्रीव, रामानो जायो,
लाख पूरव जस दोय आय, शत धनुष प्रमायो...2...
"""
CHAITYA_P17 = """मगर लंछन जस शोभतूं ए, भयभंजन भगवान,
मानविजयने गावोगे, अदुभुत अविचल थान.
शीतलनाथ नु [10]
शीतल सेजे शीतलो, शीतल जस वाणो,
समता शीतल ते हुवे, जे निसुणे पाळी...
नेवं धनुष प्रमाण प्रीत, वर्ण जस काय,
श्रीवत्स लंछन अक लाख, पूरव जस आय...
हृढरथ नंदा नंदनोअओ, भदिलपुर वर राय,
प्रभुध्याने शीतल रहे, मानविजय उवज्ज्ञाय...
श्रेयांसनाथ नु [22]
श्री श्रेयांस जिणंद देव, सेवक सुखकारी,
परम पुरुष परमेश्वरो, प्रणमो नरनारी...
सिहपुरी वर राय विष्णु, विष्णु अंगजात,
चउराणी लख वषं आय, सोवन सम गात...
वासुपुज्य नु । 12]
वासव पूजित वामुपुज्य, तनु विद्रुम वान,
राणी जया वसुपूज्यराय, कुल तिलक समान...
चंपा नयरी जनमिओ, सित्तेर धनुष देह,
वरस बहोंतेर लाख आय, कीधो भव चेह. .
"""


def _book_krutis(*pages):
    book = Book.from_pages("book.pdf", [PageText(i + 1, "ocr", 90.0, t) for i, t in enumerate(pages)])
    return find_krutis(book, {i + 1: 90.0 for i in range(len(pages))}, merged(None))


def test_ellipsis_verses_and_bracket_serial_headings():
    ks = _book_krutis(CHAITYA_P16, CHAITYA_P17)
    titles = [k.title for k in ks if k.title]
    assert titles == ["सुपाश्वेनाथ नु", "चद्रप्रमु गु", "सुविधिनाथ नु", "शीतलनाथ नु",
                      "श्रेयांसनाथ नु", "वासुपुज्य नु"]
    by_title = {k.title: k for k in ks}
    assert by_title["सुपाश्वेनाथ नु"].aadi.startswith("सुपरि सुरजन सेविओ")
    assert by_title["चद्रप्रमु गु"].verses == 3
    assert "मानविजय कवियण कहे" in by_title["चद्रप्रमु गु"].ant
    assert by_title["शीतलनाथ नु"].aadi.startswith("शीतल सेजे शीतलो")
    assert by_title["शीतलनाथ नु"].start_page == 2
    assert all(len(k.aadi) < 150 and len(k.ant) < 150 for k in ks)


def test_aadi_is_first_sentence_and_ant_is_last_sentence():
    k = {k.title: k for k in _book_krutis(CHAITYA_P16, CHAITYA_P17)}["चद्रप्रमु गु"]
    assert k.aadi == "चंद्रपरभु जिन चंद्रसौम्य, पुरी चंद्रा राय, कान्ति चंद्र हार्यो रहे, लंछन मसे पाय"
    assert k.ant == "दोढसो धनुष मित देहडी ए, जीवन जगदाधार, मानविजय कवियण कहे, आवागमन निवार"


def test_book_page_numbers_from_headers():
    # printed "[7] चैत्यवंदन" / "चोवीसी 8" in the headers: book page = PDF page - 6
    fillers = ["ऋषभ जिनेसर वंदीए", "अजित जिणंद दयाल", "संभव सुखदाता सदा", "अभिनंदन गुणखाण",
               "सुमति सुमति दातार", "पद्मप्रभ पावन करो", "सुपास जिन सेवीए", "चंद्रप्रभ मुखचंद"]
    pages = []
    for i, n in enumerate(range(12, 20)):
        body = CHAITYA_P17 if n == 13 else f"{fillers[i]}, भवि जन सेवो ...1...\n"
        head = f"[{n - 6}] चैत्यवंदन" if n % 2 == 0 else f"चोवीसी {n - 6}"
        pages.append(PageText(n, "ocr", 90.0, f"{head}\n{body}"))
    book = Book.from_pages("b.pdf", pages)
    assert book.printed_page(16) == 10 and book.printed_page(19) == 13
    k = next(k for k in find_krutis(book, {}, merged(None)) if k.title == "शीतलनाथ नु")
    assert (k.start_page, k.book_start) == (13, 7)


def test_index_page_is_left_out():
    index = ("अनुक्रमणिका\nश्री ऋषभदेव 12 ॥1॥ श्री अजितनाथ 14 ॥2॥ श्री संभवनाथ 16 ॥3॥ श्री अभिनंदन 18 ॥4॥ "
             "श्री सुमतिनाथ 20 ॥5॥ श्री पद्मप्रभ 22 ॥6॥ श्री सुपार्श्व 24 ॥7॥")
    assert _krutis(index) == []


def test_preface_prose_is_left_out():
    preface = ("विक्रम की 16वीं शताब्दी के बाद का समय भक्ति योग का प्रेरक काल रहा है, इस कालखंड में हर धर्म "
               "व क्षेत्र में विशिष्ट कवियों का आविर्भाव हुआ जिन्होंने प्रभु भक्ति के विविध आयामों पर "
               "काव्य शक्ति को प्रकट करते हुए अपनी कलम को गति दी...\nउसी श्रृंखला के एक अनूठे हस्ताक्षर हैं "
               "श्री क्षमाकल्याणजी महाराज, वे मूलतः कविचेता साधु हैं और उन्होंने अपने आराध्य को लक्ष्य "
               "बनाकर अनेक रचनाएं कीं जो आज भी गाई जाती हैं...\n")
    assert _krutis(preface) == []


def test_heading_with_stray_danda_first_verse_and_garbled_running_header():
    # real OCR, S037974 p.30: "। सुविधिनाथ गु [6]", a first verse ending "... 1...", and the
    # running header "चोवीसी [24]" read as "चोवीसी [2%]" at the top of the next page
    p1 = ("चैत्यवंदन [27]\nलखमणा सूत पूजि, कुसुम घनसार चंदन. ..2...\nचंद्रप्रभा नयरी सुणो, नरपति प्रणमे पाय,\n"
          "त्रिजगगुरू नित्ये नमो, लंछन दोपे निशि राय, ..3...\n। सुविधिनाथ गु [6]\n"
          "सुविधि नवनिधि सुविधि नवनिधि रयण भंडार... 1...\nतात\n")
    p2 = ("चोवीसी [2%]\nवंछित सुखदायक नमुं, गर्भवास नितु टाझे फे रो,\nकाकंदी नयरी हुओ, देव पुत्र सुग्रीव केरो...2...\n"
          "रामा राणी जाइओ, मंगर लंछन जे कोय,\nसुविधिनाथ सविया नमो, जिम घरे संपत्ति होय. . . 3. - -\n"
          "शीतलनाथ नु [20]\nस्वामी शीतल स्वामी शीतल भद्दिलपुर माम ...1...\n")
    others = [f"{h} [{n}]\n{v} जिनवर वंदीए, भवि जन सेवो ...1...\n"
              for h, n, v in (("चैत्यवंदन", 29, "ऋषभ"), ("चोवीसी", 30, "अजित"), ("चैत्यवंदन", 31, "संभव"),
                              ("चोवीसी", 32, "अभिनंदन"))]
    book = Book.from_pages("b.pdf", [PageText(i + 1, "ocr", 90.0, t)
                                     for i, t in enumerate([p1, p2] + others)])
    ks = find_krutis(book, {}, merged(None))
    titles = [k.title for k in ks if k.title]
    assert "सुविधिनाथ गु" in titles and "शीतलनाथ नु" in titles
    assert not any(t.startswith(("सुविधि नवनिधि", "चोवीसी", "चैत्यवंदन")) for t in titles)
    k = next(k for k in ks if k.title == "सुविधिनाथ गु")
    assert k.aadi == "सुविधि नवनिधि सुविधि नवनिधि रयण भंडार"


def test_rows_without_text_are_not_grouped_together():
    from kruti.krutis import Kruti, assign_groups
    a = Kruti("a.pdf", 1, 1, 1, "x", "", "", [], (0, 1))
    b = Kruti("b.pdf", 2, 2, 1, "y", "", "", [], (0, 1))
    assign_groups([a, b])
    assert a.group_no != b.group_no


# Other books' layouts, from real OCR of the samples
def test_type_word_first_heading():
    # S002803 stavanavali: "पद अगीयारमु ॥", "पद बारमुं ॥ राग ..."
    text = ("पद दशमुं ॥ श्री चिंतामणि प्रभु पूजा करतां, माया मुकत अब वामी ॥ 1 ॥ "
            "लागी लगन प्रभु चरणनी, भव भय सघलो वामी ॥ 2 ॥\n"
            "पद अगीयारमु॥ में तो तोरी आजही महीमा\nजाणी ॥ टेक ॥ कायकुं नव विच चरी जील नमता,\n"
            "कायकुं बोत दुःख दानी ॥ मेतो0 ॥ 1॥ एसी शाखा\nमें बोत सुनी दे, जेन पुरान बिखानी ॥ मेतो0 ॥ 2 ॥\n"
            "पद बारमुं ॥ राग विर्य ॥ शीयल नित पालो\nप्रानी, शीयल धरमको मूल रे ॥ सीचणळ ॥ टेक ॥\n"
            "सीयत सती सीतायें पाद्यं, अग्नि कुंड जयो पानी रे\n॥ चीयलण्॥ 1 ॥ झीयल सती सुनझायें वाव्युं, चा\n"
            "लणी स जर लीयो पानी रे ॥दीयलण्॥ 2 ॥")
    titles = [k.title for k in _krutis(text)]
    assert titles == ["पद दशमुं", "पद अगीयारमु", "पद बारमुं"]


def test_line_end_verse_numbers_when_the_book_uses_them():
    # B039544 prachin sazzaya: "...रूडा0 धन्य0 11" - the number closes the verse line
    verses = ["त्राजवुं मंगावी मेघरथ रायजी, कापी कापी मूके छे मांस", "देव माया धारणु समी, ने आवे एकणु गश",
              "भाई सुत राणी वळवळे, हाथ झाली कहे तेह", "एक पारेवा ने कारणे, शुं कापो छे देह",
              "महाजन लोक वारे सहु, म करो एवडी वात", "मेघरथ कहे धर्म भलो, जीवदया सुज घात",
              "त्राजवे बेठा मेघरथ राजवी, जे भावे ते खाजो", "जीवथी पारेवा अधिक गह्यो, धन्य पिता तुज माय",
              "चढते परिणामे राजवी, सुर प्रगट्यो तिहां आय"]
    lines = ["मेघरथ राजानी सज्झाय."]
    for i, v in enumerate(verses, 1):
        lines += [v + ",", f"रूडा0 धन्य0 {i}"]
    ks = _krutis("\n".join(lines))
    assert len(ks) == 1 and ks[0].title == "मेघरथ राजानी सज्झाय" and ks[0].verses == 9
    assert ks[0].aadi.startswith("त्राजवुं मंगावी मेघरथ रायजी")


def test_stray_line_end_numbers_do_not_split_a_normal_book():
    # a ॥n॥ book with a few numbers at line ends (years, counts) keeps ॥n॥ verses only
    text = PREVIOUS + "\nसंवत 1686\nमागशर मास 12\n"
    assert [k.title for k in _krutis(text)] == ["शांतिनाथ स्तवन"]


def test_long_verse_is_taken_whole():
    # verses punctuated only at the verse end: Aadi/Ant are still the whole first/last
    # verse, as the team's Excel writes them
    text = ("आदिनाथ स्तवन.\n"
            "प्रथम जिनेश्वर प्रणमीए, जास सुगंधी रे काय, कल्पवेली परे विस्तरी,\n"
            "नाभिराया कुल मंडणो, मरुदेवी माता मल्हार, वंछित फल दातार जिणंदा,\n"
            "भविजन कमल दिवाकरु, सेवक जन आधार, त्रिभुवन तारण देव दयाल,\n"
            "केवल ज्ञान दिवाकर स्वामी, शिवसुख संपत्ति दाय ॥1॥\n"
            "मोहन कहे प्रभु सेवतां, लहीए सुख अपार अनंत, भव भय भंजन देव,\n"
            "सुरनर सेवे जेहने, पामे भवजल पार, जिनवर नमीए नित्य,\n"
            "समकित दायक साहिबा, मुज मन मंदिर वास,\n"
            "कीर्ति सदा जग विस्तरी, गावे मुनि गुणवंत ॥2॥")
    k = _krutis(text)[0]
    assert k.aadi.startswith("प्रथम जिनेश्वर प्रणमीए, जास सुगंधी रे काय, कल्पवेली परे विस्तरी, ")
    assert k.aadi.endswith("केवल ज्ञान दिवाकर स्वामी, शिवसुख संपत्ति दाय")
    assert k.ant.startswith("मोहन कहे प्रभु सेवतां")
    assert k.ant.endswith("कीर्ति सदा जग विस्तरी, गावे मुनि गुणवंत")
    assert not k.checks


# Real OCR, B018723 sazzay sarita p.345-348 (Gujarati): a multi-part sajjhay. Its dhals
# (ઢાળ ૪), dohas (દુહા) and kalash restart verse numbers but are parts of ONE Kruti.
SAJJHAY = """172. સુદર્શન શેઠની સજઝાય
શેઠ સુદર્શન પ્રિયા નામે મનોરમા જેહ લલના;
રૂપે રતિ સમ સુંદરી શીલવતી ગુણ ગેહ લલના; શીલ૦ ૧
કહે કપિલા તે કિલબ છે જૂઠ ધરે નર વેશ લલના;
કિમ જાણ્યુ રાણી કહે કહે વૃત્તાત અશેષ લલના; શીલ૦ ૨
ઢાળ ૪
હવે અભયા થઈ આકરી રે લાલ ચૂકવવા તસ શીલ રાયજાદી;
ધાવ માતા તસ પંડિતા રે લાલ તેડી કહે નિજ ચિત્ત રાયજાદી; ખલ૦ ૧
સુણ પુત્રી કહે પંડિતા રે લાલ તુજ હઠ ખોટી અત્યંત રાયજાદી;
એક દોય ત્રણ ઈમ કામની રે લાલ મૂરતિ આણી તામ રાયજાદી; ખલ૦ ૨
દુહા
બીજે દિવસે ગવેષવા, વસુદત્તના સુત ચાર;
ભીંત પડી ઉપડાવતાં, મળી સોવન શ્રીકાર. ૧
કલશ
ઈમ શેઠ સુદર્શન શીલ પાળી પામ્યા ભવનો પાર;
શ્રી શુભવીર વચન રસ પીતાં લહીએ સુખ અપાર. ૧
173. સુનંદા રૂપસેનની સજઝાય
ખેટમુની કહે ધન્ય તુમે સાતે જણાં એક વયણે પ્રતિબોધ લહ્યો;
ન રહી શકે મન ધર્મ વિના સુખ પામે તે જિન વચન કહ્યો. ૧
ત્રીજે ખંડે ઢાળ એ છઠ્ઠી મન ધરો શ્રી શુભવીર વચન રસે;
રૂપસેન સુનંદા ગુણ ગાતાં પાપ પડલ સવિ દૂર ખસે. ૨
"""


def test_dhal_doha_kalash_are_parts_of_one_kruti():
    from kruti.normalize import devanagari_to_gujarati as guj
    ks = _krutis(SAJJHAY)
    for k in ks:                       # the pipeline shows Gujarati books in Gujarati
        k.title, k.aadi, k.ant = guj(k.title), guj(k.aadi), guj(k.ant)
    titles = [k.title for k in ks]
    assert titles == ["સુદર્શન શેઠની સજઝાય", "સુનંદા રૂપસેનની સજઝાય"], titles
    first = ks[0]
    assert first.aadi.startswith("શેઠ સુદર્શન પ્રિયા નામે મનોરમા")
    assert "ભવનો પાર" in first.ant or "સુખ અપાર" in first.ant    # its kalash, not dhal 1
    assert first.verses == 6                                     # 2 + 2 + 1 + 1 across parts


def test_repeated_part_headings_are_not_taken_for_page_headers():
    # "ઢાળ ૩", "ઢાળ ૪" ... repeat on many pages (as "ढाळ" without the number) but sit
    # mid-page; only lines at a page's top/bottom are running headers
    pages = []
    for i in range(1, 6):
        pages.append(PageText(i, "ocr", 90.0,
                              f"સજ્ઝાય સરિતા\nએક દિન ઈન્દ્ર મહોત્સવે રાજાદિક સવિ લોક લલના ... {i}\n"
                              f"ઢાળ {i + 1}\nકીડા કારા આવીયા સજ્જ કરી સઘળા થોક લલના;\n"
                              f"શીલ ભલી પેરે પાળીએ... ૧\nસજ્ઝાય સરિતા {i + 100}"))
    book = Book.from_pages("b.pdf", pages)
    assert book.light.count("ढाळ") == 5            # part headings kept
    assert "सरिता" not in book.light               # the running header removed


# Real OCR, B018723 p.346-348 (Gujarati, shown here after conversion to Devanagari)
PARTS_AND_NEXT = """धाव माता तस पंडिता रे लाल कहे सवि वात सलील रायजादी... खल0 9
एक दोय त्रण ईम कामनी रे लाल मूरति आणी ताम रायग्नद्दी,
प्रतिमाधर ईम रोठने रे लाल कपटे आण्यो धाम रायजादी... खल0 10
ढाळ प
अभया काम विकार करी आलिगती हो लाल-डरी0
कोमल कमल मृणाल भुजारयुं विटती हो लाल-भूजाट...
निज थण मंडल पीडे तस करशुं गृही हो लाल-तस0
अंगो पांगे सर्व के फरसे ते सही हो लो-के0... 2
सहज सोभागी समकित उजळुं रे गुणीनां गुणगातां आनंद थाय रे
ज्ञानविमल गुर वाधे अतिघणा रे अधिक उदय होवे सवाय रे
मोटो0 3
172. सुनंदा रूपसेननी सजझाय (ढाळ-2)
ढाळ 1:
खेटमुनी कहे धन्य तुमे साते जणां एक वयणे प्रतिबोध लह्यो न रही मणां;
रात उपदेशे पण राय न बूझीयो पापी प्राणी... 1
त्रीजे खंडे ढाळ ए छठ्ठी मन धरो श्री शुभवीर वचन रसे... 2
"""


def test_unreadable_part_number_and_parenthetical_heading():
    ks = _krutis(PARTS_AND_NEXT)
    titles = [k.title for k in ks]
    assert len(ks) == 2, titles                       # the dhals of one Kruti, then the next
    assert not any("निज थण" in t for t in titles)      # a verse line is never a title
    assert ks[1].title.startswith("सुनंदा रूपसेननी सजझाय")
    assert ks[1].aadi.startswith("खेटमुनी कहे धन्य")


def test_part_heading_with_tune_note_stays_in_the_kruti():
    # B016768 navpad manjusha: "ढाल तेरहवीं -नारायणकी देशी …" and "दुहो" are parts
    text = ("नवपद पूजा.\nअरिहंत पद पूजीए, भवि भावे मन उल्लास ॥1॥ सिद्ध पद सेवीए, पामो शिव वास ॥2॥\n"
            "ढाल तेरहवीं -नारायणकी देशी जिम मधुकर मन मालती\nजिनवर नमीए भाव थी, वीर जिणंद उपदेश ॥1॥ "
            "गुरु गौतम गुण गाईए, पामो सुख विशेष ॥2॥\nदुहो\nअनंत चतुष्टय पामवा, सज्ज द्रव्य गुण पर्याय ॥1॥")
    ks = _krutis(text)
    assert [k.title for k in ks] == ["नवपद पूजा"] and ks[0].verses == 5


# Missed headings seen in the samples (real OCR lines)
def test_serial_numbered_heading_with_garbled_type_word():
    # B018723: "294. वैराग्यनी साय" (सज्झाय garbled); B018952: "(।) अभिनंदन जिन सवत."
    text = ("गुरु गुण गावो भाव धरीने, पामो सुख अपार रे ॥1॥ समकित निरमल धारीए, टाळो भव नो भार रे ॥2॥\n"
            "294. वैराग्यनी साय\nसार नहि रे संसारमां, करो मनमां विचार जी ॥1॥\n"
            "नेत्र उघाडीने जोईए, करीए दृष्टि पसार जी ॥2॥\n"
            "(।) अभिनंदन जिन सवत. (राग : समताथी)\nअभिनंदन स्वामी हमारा, प्रभु भव दुःख भंजनहारा ॥1॥ "
            "ये दुनियां दुखोकी धारा, प्रभु इनसे करो निस्तारा ॥2॥")
    titles = [k.title for k in _krutis(text)]
    assert titles[1:] == ["वैराग्यनी साय", "अभिनंदन जिन सवत"], titles


def test_more_kruti_type_words():
    text = ("श्री धर्मनाथ भगवान\nभानुनंदन धर्मनाथ, सुव्रता भली मात ॥1॥ वज्र लंछन वजी नमे, त्रण भुवन विख्यात ॥2॥\n"
            "जय वीयराय सूत्र\nजय वीयराय जगगुरु, होउ ममं तुह पभावओ भयवं ॥1॥ भव निव्वेओ मग्गाणुसारिया, इट्ठफलसिद्धी ॥2॥\n"
            "गुणस्थानक स्वाध्याय\nअपूर्व अवसर एवो क्यारे आवशे, क्यारे थइशुं बाह्यांतर निर्ग्रंथ जो ॥1॥ "
            "सर्व संबंधनुं बंधन तीक्ष्ण छेदीने, विचरशुं कव महत्पुरुषने पंथ जो ॥2॥")
    assert [k.title for k in _krutis(text)] == ["श्री धर्मनाथ भगवान", "जय वीयराय सूत्र",
                                               "गुणस्थानक स्वाध्याय"]


def test_ocr_variants_of_dhal_and_doha_are_parts():
    # B002198 "हाल 3 :-", B017945 "॥ हाल त्रीनी ॥" / "॥ टाई बीजी ॥", "डुहाः-"
    text = ("सीमंधर स्वामीनुं स्तवन.\nश्री सीमंधर साहिबा, विनतडी अवधार ॥1॥ सुण सुण स्वामी सीमंधरा, धरा भूषण इंश ॥2॥\n"
            "॥ हाल त्रीनी ॥ श्रेणिक मन अचरिज हज ॥ ए देशी ॥\nतपजप करीये रातथी, तेहतणो छे भेद रे ॥1॥ "
            "शिव सुख पामे जीवडो, टाळे भव नो खेद रे ॥2॥\nडुहाः-इयादिक अनेक छे, अनंतकायना भेद ॥1॥\n"
            "हाल बेहाल थयो जीवडो, भमतो चार गति मांहि ॥2॥")
    ks = _krutis(text)
    assert [k.title for k in ks] == ["सीमंधर स्वामीनुं स्तवन"], [k.title for k in ks]
    assert "हाल बेहाल थयो जीवडो" in ks[0].ant            # a verse starting with "हाल" stays a verse


def test_decorative_rule_is_not_a_sentence():
    text = ("श्री पाक्षिक खामणा.\n~-~--~---~-~~~~---~~~~-----~-~~-~~~\n"
            "इच्छामि खमासमणो वंदिउं जावणिज्जाए निसीहिआए ॥1॥ पियं च मे जं भे हट्ठाणं तुट्ठाणं ॥2॥")
    k = _krutis(text)[0]
    assert k.aadi.startswith("इच्छामि खमासमणो")


# Second, unseen sample (real OCR lines)
def test_part_heading_recognised_by_its_ordinal():
    # B002198: "हाश खीजीः-" / "हार त्रीजी ड--" (ढाल बीजी / त्रीजी garbled), "ढाल चोथी"
    text = ("समकितनी सज्झाय.\nसमकित दायक गुरु तणो, पच्चुवयार न थाय ॥1॥ भव कोडा कोडी लगे, करतां सर्व उपाय ॥2॥\n"
            "हाश खीजीः-शय हुं तुज विनवुं\nदोय बेरखा सेती भली, तुजने दीधी रे ॥1॥ सुणी पामी परम उत्साह हो ॥2॥\n"
            "हार त्रीजी ड--कळावती\nलोक मळी वारे घणुंजी, वचन न माने राय ॥1॥ नगर मझार उत्सव घणो रंग ॥2॥")
    ks = _krutis(text)
    assert [k.title for k in ks] == ["समकितनी सज्झाय"] and ks[0].verses == 6


def test_serial_without_full_stop():
    # B002198: "68 समकितनी सजय" (सज्झाय garbled), after the previous Kruti's last verse
    text = ("गुरु गुण गावो भाव धरीने, पामो सुख अपार रे ॥1॥ समकित निरमल धारीए, टाळो भव भार रे ॥2॥\n"
            "68 समकितनी सजय\nसमकित दायक गुरु तणो, पच्चुवयार न थाय ॥1॥ भव कोडा कोडी लगे, करतां सर्व उपाय ॥2॥")
    assert [k.title for k in _krutis(text)][1:] == ["समकितनी सजय"]


def test_letter_serial_and_raga_line_start_a_kruti():
    # B020983: "(च)" / "(£)" and "(राग - वीर जिनेश्वर…)" on their own line, no title printed
    text = ("वल्लभसूरि कहे ए करणी, श्रीपद महेल चढण नीसरणी ॥3॥ सिद्धायिका दुःख हरणी ॥4॥\n"
            "(राग - वीर जिनेश्वर अति अलवेसर)\nपामी पुण्य संयोग सुहावो, जिन दरिसण मन भावो ॥1॥ "
            "सेवो भवियण भाव धरीने, पामो शिवपुर ठावो ॥2॥\n(च)\nवीर जिनेश्वर वंदीए, शासन नायक देव ॥1॥ "
            "मेघविजय कवियणनो शिष्य, विनय वंदे निशदिश ॥2॥")
    ks = _krutis(text)
    assert len(ks) == 3
    assert ks[1].aadi.startswith("पामी पुण्य संयोग") and ks[2].aadi.startswith("वीर जिनेश्वर वंदीए")


# Sanskrit / old-text markers (real OCR lines from the samples)
def test_atha_opens_and_iti_closes_a_kruti():
    text = ("नमिऊण पणय सुरगण चूडामणि किरण रंजियं मुणिणो ॥1॥ चलण जुयलं महाभय पणासणं संथवं वोच्छं ॥2॥\n"
            "इति श्रीलघुअजितशांतिस्तवनं द्वितीयं स्मरणं ॥\n"
            "॥ अथ गुण विषे दोहा ॥\nगुण विना नर शोभे नहि, जिम फूल विना वन वेल ॥1॥ गुणीजन संगत कीजीए, टाळे भवनो खेल ॥2॥")
    ks = _krutis(text)
    assert [k.title for k in ks][1:] == ["गुण विषे दोहा"], [k.title for k in ks]
    assert "इति" not in ks[0].ant and "इति" not in ks[1].aadi
    assert ks[1].aadi.startswith("गुण विना नर शोभे नहि")


def test_bracketed_number_alone_on_a_line():
    # S027836: "। [2]" between two chaityavandans
    text = ("अढाइधर आराधीएं, आगम वाणी विनीत...1...\nसंघ सकल शुभ रीत, पामो भवनो पार...2...\n"
            "। [2]\nप्रणमुं श्री देवाधिदेव, जिनवर महावीर...1...\nशासन नायक जग जयो, वरते जय जयकार...2...")
    ks = _krutis(text)
    assert len(ks) == 2 and ks[1].aadi.startswith("प्रणमुं श्री देवाधिदेव")


def test_lone_short_line_before_restarted_verses_is_the_title():
    # B018723: "…सगुढ 6⏎294. वैराग्यनी साय⏎सार नहि रे संसारमां…" in a book numbering
    # verses "N." - the serial 294 is read as a verse number, the title stands alone
    prev = "".join(f"गुरु गुण गावो भाव धरीने पामो सुख अपार रे {i}.\n" for i in range(1, 9))
    text = (prev + "294. वैराग्यनी साय\n"
            "सार नहि रे संसारमां करो मनमां विचार जी 1.\nनेत्र उघाडीने जोईए करीए दृष्टि पसार जी 2.\n")
    ks = _krutis(text)
    assert [k.title for k in ks][-1:] == ["वैराग्यनी साय"], [k.title for k in ks]
    assert ks[-1].aadi.startswith("सार नहि रे संसारमां")


def test_first_verse_line_is_not_taken_for_a_title():
    # a new Kruti with no title printed: its first line is long / has a comma -> no title
    text = ("गुरु गुण गावो भाव धरीने, पामो सुख अपार रे ॥1॥ समकित निरमल धारीए, टाळो भव भार रे ॥2॥\n"
            "सार नहि रे संसारमां, करो मनमां विचार जी ॥1॥ नेत्र उघाडीने जोईए, करीए दृष्टि पसार जी ॥2॥")
    assert [k.title for k in _krutis(text)] == ["", ""]


def test_junk_line_is_not_a_title():
    text = ("गुरु गुण गावो भाव धरीने, पामो सुख अपार रे ॥1॥ समकित निरमल धारीए, टाळो भव भार रे ॥2॥\n"
            "द्वरिझे 939 ल्दिझे 9798\nसार नहि रे संसारमां, करो मनमां विचार जी ॥1॥ नेत्र उघाडीने जोईए ॥2॥")
    assert [k.title for k in _krutis(text)] == ["", ""]


def test_type_word_alone_with_comma():
    # B007712 held-out: "॥ 5॥⏎लावणी,⏎॥ करूं अरज एक …"
    text = ("भवि जन वंदो भावसुं, टालणुहार ॥ 4॥ सोहग टालणुहार ॥ 5॥\nलावणी,\n"
            "॥ करूं अरज एक जिनपति, कंत नहीं डरते ॥ 1 ॥ गाम धुलेवे वंश जालमे, प्रभु धरती ॥ 2 ॥")
    assert [k.title for k in _krutis(text)][-1] == "लावणी"


# ---- text that is not a Kruti: explanations, headers, footnotes, notes, preface, index
# (real OCR from the first test round: B000505, B002637, B052034)

def test_explanation_after_each_verse_is_left_out():
    # B000505 p.19: every verse is followed by its "व्याख्या-" paragraph, numbered like it
    text = ("॥ श्री सीमंधर स्वामिनी विनतिरुप स्तवन ॥\n"
            "स्वामी सीमंधर विनति, सांभळो माहरी देवरे ।\nताहरी आण हुं शिर धरुं, आदरुं ताहरी सेवरे ॥ १॥\n"
            "व्याख्या-हे श्री सीमंधर स्वामी, तमे माहरी विनति सांभळो, देव के० हे देवाधिदेव\n"
            "हुं ताहरी आज्ञा शिर धरुं छुं, तथा ताहरी सेवाने आदरुं छुं. सेवकनी\n"
            "विनति स्वामीए सांभळवीज. ॥१॥\n"
            "कुगुरुनी वासना पासमां, हरिण परे जे पड्या लोकरे ।\nतेहने शरण तुज विण नहीं, टळवळे बापडा फोकरे ॥२॥\n"
            "व्याख्या-कुगुरुनी वासना के० जूठा उपदेशनी धारणा ते रूपी पाशमां हरिणनी\n"
            "पेरे जे लोक पड्या छे, पोते मोह मूके नहीं एम सर्व मोहे मुंझाइ रह्या छे, ते\n"
            "दृष्टिरागी लोकने तुज विना शरण नथी. ॥ २ ॥\n"
            "ज्ञान दर्शन चरण गुण विना, जे करावे कुलाचाररे ।\nलूटे तेणे जन देखतां, क्यां करे लोक पोकाररे ॥३॥\n")
    ks = _krutis(text)
    assert len(ks) == 1
    k = ks[0]
    assert k.aadi.startswith("स्वामी सीमंधर विनति, सांभळो माहरी देवरे")
    assert k.ant.startswith("ज्ञान दर्शन चरण गुण विना") and k.ant.endswith("लोक पोकाररे")
    assert "व्याख्या" not in k.aadi + k.ant and "के०" not in k.aadi + k.ant


def test_running_header_with_page_number_is_not_a_title():
    # B002637 p.42-43: "यवीयराय सूत्र । 11" / "12 अभय रत्नसार ।" head the pages; the header
    # names the Kruti on the page but is not where it starts
    pages = []
    for n in range(40, 46):
        head = f"{n - 31} अभय रत्नसार ।" if n % 2 == 0 else f"जयवीयराय सूत्र । {n - 31}"
        pages.append(PageText(n, "ocr", 90.0, f"{head}\nजय वीयराय जगगुरु, होउ ममं तुह पभावओ भयवं ॥ 1 ॥\n"
                                               f"भव-निव्वेओ मग्गा-णुसारिया इट्ठफल-सिद्धी ॥ 2 ॥\n"))
    book = Book.from_pages("b.pdf", pages)
    titles = [k.title for k in find_krutis(book, {}, merged(None))]
    assert not any("रत्नसार" in t or "सूत्र" in t for t in titles), titles


def test_footnote_is_not_a_title():
    # B002637 p.39: "# पाठान्तर "संपद्"" under the last verse became a Kruti name
    text = ("जं किंचि सूत्र ।\nजं किंचि नाम तित्थं, सग्गे पायालि माणुसे लोए ।\n"
            "जाई जिण-बिंबाइं, ताईं सव्वाइं वंदामि ॥ 1 ॥\nसव्वाइं वंदामि पुनः, भवे भवे तुह चलणाणं ॥ 2 ॥\n"
            "# पाठान्तर \"संपद्\" ।")
    ks = _krutis(text)
    assert [k.title for k in ks] == ["जं किंचि सूत्र"]
    assert "पाठान्तर" not in ks[0].ant


def test_metre_note_and_source_note_are_not_aadi_or_ant():
    # B052034 p.32, 50: "( मालिनी-छन्दः )" above the first verse, "(खरतरगच्छ साहित्य कोश
    # क्रमांक- 3553.)" under the last one
    text = ("2. श्रीअजितनाथजिनेन्द्र-चैत्यवन्दनम्\n( मालिनी-छन्दः )\n"
            "सकलसुखसमृद्धिर्यस्य पादारविन्दे,\nविलसति गुणरक्ता भक्तराजीव नित्यम्।\n"
            "त्रिभुवनजनमान्यः शान्तमुद्राऽभिरामः,\nस जयति जिनराजस्तुङ्ग तारङ्गतीर्थे॥1॥\n"
            "नरपतिजितशत्रुर्वंशरत्नाकरेन्दुः,\nसुरपति-यतिमुख्यैर्भक्तिदक्षैः समर्च्यः।\n"
            "दिनपतिरिव लोकेऽपास्तमोहान्धकारो,\nजिनपतिरजितेशः पातु मां पुण्यमूर्तिः ॥2॥\n"
            "(खरतरगच्छ साहित्य कोश क्रमांक- 3553.)\n")
    k = _krutis(text)[0]
    assert k.aadi.startswith("सकलसुखसमृद्धिर्यस्य पादारविन्दे")
    assert k.aadi.endswith("तारङ्गतीर्थे")
    assert k.ant.startswith("नरपतिजितशत्रुर्वंशरत्नाकरेन्दुः") and "कोश" not in k.ant


def test_tune_note_in_front_of_first_verse_is_dropped():
    # B052034 p.88: "(सिंहल नृप कहे चंदने-ए देशी) श्री संभव जिनरायजी, …"
    text = ("श्री संभवनाथ जिनेश्वर स्तवन\n(सिंहल नृप कहे चंदने-ए देशी) श्री संभव जिनरायजी, साहिब मारा\n"
            "सेना नंद सुजाण हो ॥1॥\nराज जितारि कुल दिनमणि, साहिब मारा सोहे सुर नर भाण हो ॥2॥")
    assert _krutis(text)[0].aadi.startswith("श्री संभव जिनरायजी, साहिब मारा")


def test_preface_pages_quoting_verses_are_left_out():
    # B052034 p.15-16: the preface quotes a numbered line of a stavan; no Kruti from it
    prose = ("वे भक्त हैं तो कवि की रसिकता भी उनमें भरपूर है। अपने रसिक अनुभव को मर्यादा के साथ\n"
             "प्रकृति-वर्णन द्वारा अभिव्यक्त करते हैं। नेमिनाथ परमात्मा के एक स्तवन में प्रकृति\n"
             "की लीला इस प्रकार प्रकट हुई है। उनके इन गीतों में हृदय में कल-कल उमड़ते भावों की\n"
             "सहज प्रस्तुति है। इन गीतों में इतिहास का समावेश भी उन्होंने बखूबी किया है और\n"
             "इन स्तवनों से उनकी विहार-यात्रा का वृत्तान्त भी सहज उपलब्ध हो जाता है। गच्छ में\n"
             "व्याप्त मतभेदों के कारण विधि-विधानों में मतभेद चल रहा था, उन्होंने उसे दूर किया।\n")
    quote = "समय वसंत प्रगट भयो सुन्दर, विकसित कुसुम अपार ॥ 1 ॥\nकोयल कलरव करत मधुर धुनि, भमर करत झंकार ॥ 2 ॥\n"
    kruti = ("1.\nश्री सिद्धाचलजी तीर्थ का चैत्यवंदन\n"
             "जय जय नाभि नरिन्द नन्द, सिद्धाचल मंडण,\nजय जय प्रथम जिणंद चन्द, भव दुःख विहण्डण॥1॥\n"
             "जय जय साधु सुरिंद वृन्द, वंदिय परमेसर,\nजय जय जगदानन्द कन्द, श्री रिषभ जिणेसर॥2॥\n"
             "अमृतसम जिन धर्मनों ए, दायक जगमें गाळ,\nतुझ पद पंकज प्रीतिधर, निशदिन नमत कल्याण॥3॥\n")
    ks = _book_krutis(prose * 2, prose + quote + prose, prose * 2, kruti, kruti)
    assert ks and all(k.start_page >= 4 for k in ks), [(k.start_page, k.aadi[:30]) for k in ks]


def test_index_page_with_ocr_garbled_heading_is_left_out():
    # B000505 p.18: "विषयाहुक्रमणिका" (OCR of विषयानुक्रमणिका) over a publisher's book list
    index = ("(60) 'विषयाहुक्रमणिका.\nमहावीर जैनसभा तरफथी प्रसिद्ध थयेला ग्रंथो लीस्ट,\n"
             "1 बारव्रतनी टीप (गुजराती) रु. 0-1-0\n2 जैननुं स्तवन (गुजराती) रु. 0-2-0\n"
             "3 बृहत्शान्ति स्तव वृत्ति सहित रु. 0-1-0\n4 अंगुलसत्तरी भाषांतर रु. 0-2-0\n"
             "5 बार व्रतनी टीप (हिंदी) भेट\n6 षन्नरेन्द्र कथा संस्कृत रु. 0-8-0 ॥ 1 ॥\n")
    assert _krutis(index) == []


def test_verse_line_ending_like_a_type_word_is_not_a_title():
    # B052034 p.56: "…गतिर्भाविनीति॥2॥" ends like "विनती" and "…पुण्यमूर्तिः" like "आरती";
    # a line closed by a verse number is the end of a verse, and the Kruti runs on
    text = ("3. श्रीविमलनाथजिनेन्द्र-चैत्यवन्दनम्\n( मन्दाक्रान्ता-छन्दः )\n"
            "संसारेऽस्मिन् महति महिमाऽमेयमानन्दिरूपं,\nत्वां सर्वज्ञं सकलसुकृतिश्रेणिसंसेव्यमानम्॥1॥\n"
            "ये तु स्वामिन! कुमतिपिहितस्फारसद्बोधमूढाः,\nमन्ये तेषां गतशुभदुशां का गतिर्भाविनीति॥2॥\n"
            "दिनपतिरिव लोकेऽपास्तमोहान्धकारो,\nजिनपतिरजितेशः पातु मां पुण्यमूर्तिः ॥3॥\n")
    ks = _krutis(text)
    assert [k.title for k in ks] == ["श्रीविमलनाथजिनेन्द्र-चैत्यवन्दनम्"]
    assert ks[0].verses == 3 and ks[0].ant.startswith("दिनपतिरिव")


def test_section_heading_and_invocation_before_the_first_kruti():
    # B052034 p.30-32: a section heading, the book's invocation lines, then the Kruti; the
    # second Kruti's "श्री शान्ति …" is a title, not a garbled "ढाल सातमी"
    text = ("चेत्यवंदन संग्रह\n॥ ऊँ नमोऽर्हद्भ्यः। ऐँ नमः॥\nश्रीमहावीरस्वामिने नमः\nश्रीवादागुरुदेवाय नमः\n"
            "1.\nश्री सिद्धाचलजी तीर्थ का चैत्यवंदन\n"
            "जय जय नाभि नरिन्द नन्द, सिद्धाचल मंडण,\nजय जय प्रथम जिणंद चन्द, भव दुःख विहण्डण॥1॥\n"
            "अमृतसम जिन धर्मनों ए, दायक जगमें गाळ,\nतुझ पद पंकज प्रीतिधर, निशदिन नमत कल्याण॥2॥\n"
            "2.\nश्री शान्ति जिन चेत्यवंदन\nसोलमा जिनवर शान्तिनाथ, सेवो शिरनामी,\n"
            "कंचन वरण शरीर कांति, अतिशय अभिरामी॥1॥\nजगमां अमृत जेहवी ए, जास अखंडित आण,\n"
            "एक मने आराधतां, लिए जोडी कल्याण॥2॥\n")
    ks = _krutis(text)
    assert [k.title for k in ks] == ["श्री सिद्धाचलजी तीर्थ का चैत्यवंदन", "श्री शान्ति जिन चेत्यवंदन"]
    assert ks[0].aadi.startswith("जय जय नाभि नरिन्द नन्द") and "नमः" not in ks[0].aadi
    assert ks[0].ant.startswith("अमृतसम जिन धर्मनों ए")


# ---- learned from books the rules were not tuned on (B007712, B018723, B021879, B035022)

def test_lavani_set_as_running_text_is_not_an_explanation():
    # B007712 p.27: verse printed as running lines, words hyphenated across lines, Hindi
    # words (मेरी, मुझे, नहीं) and refrain cues; its verse numbers sit inside the run
    text = ("सती राजुलनी लावणी.\n"
            "पिया परबतमें दुःख ममता, महेल मंदिर मुझे नहीं गमता ॥ श्याम खडी, मेरी जान श्याम\n"
            "खडी, श्याम खडी खाय गमक ॥ सतीन ॥1॥ सती रथ संजम, मेरी जान सती रथ संजम, सती रथ\n"
            "संजममे बेडी ॥ भ्रमना अंतरका मेटी ॥ सती सब सेन, मेरी जान सती सब सेना, सती सब\n"
            "सोना तज देती ॥ जगतमें राखी नहिं रेती ॥ करी जुग बीच, मेरी जान करी जुग बीच, क्षमा\n"
            "खेती ॥ सती बस किया अपने मनकुं ॥ सतीन ॥ 2 ॥ साज शिवपुरका, मेरी जान साज शिवपुरका ॥ 3 ॥\n")
    ks = _krutis(text)
    assert len(ks) == 1 and ks[0].verses == 3
    assert ks[0].aadi.startswith("पिया परबतमें दुःख ममता")


def test_verse_lines_ending_in_dots_are_not_prose():
    # B018723 p.66: a sajjhay whose lines end "…" and "… हो राज." (no dandas)
    lines = ["गर्भ रह्यो ते दिवसथी तेने, चिंता थई चारे कोर. हो राज.",
             "माता-पिताए पण तेने कढी, प्रीती हती जेनी गाढी...",
             "करम तणी गति न्यारी जाणो, ते तो छे सहुने भारी...",
             "शीयल पाळी सुख पामी ते, जगमां कीर्ति वधारी...",
             "जे नर नारी भावे गाशे, ते पामे भवपार. हो राज.",
             "पुण्य उदये सुख संपत्ति, रूप कळा भंडार...",
             "कहे मुनि गुण गावो एहना, थाशे जय जयकार. हो राज."]
    page = "\n".join(lines * 3)
    from kruti.content import page_kind
    assert page_kind(page) is None


def test_short_verse_lines_without_dandas_are_not_an_index():
    # B021879 p.409, B035022 p.193: short verse lines whose dandas OCR lost, ending "रे",
    # "हु०" (OCR'd "हु 0")
    page = "\n".join(["तजी रमणी गढ राज्यनी हु 0", "पुर अंतेउर तेम रे हु°", "मोह कुंभी मद गालवा, हु 0",
                      "प्रगटयो मृगपति जग रे हु0", "देई दान संवत्सरी हु 0", "ओच्छव कर्यो इंद्र रे हु0",
                      "मुनिसुव्रत-नमि अंतरे हु 0", "दीक्षा लीधी जिणंद रे हु0", "विनयथी गुण वाधे घणा रे",
                      "धर्मनुं मूल विनय कह्यो रे", "विनयथी रीझे देवता रे", "वाचक शमविजय कही रे"])
    from kruti.content import page_kind
    assert page_kind(page) is None


def test_list_of_first_lines_is_an_index():
    # B007712 p.4: "प्रत्येक लावणीनुं प्रथमपद" over a list of each लावणीनी first line
    page = ("आंक.\nर4\nर्\nप\n। प्रत्येक लावणीनुं प्रथमपद.\nतजो काम मद भून् लाल जिनवर गुणमातां....\n"
            "अगम पंथ जानां इ नडे अगम ...\nसुगुण आस मत करे कलेसी कुमति संग छायो...\n"
            "सजन समजावो अपने मनकुं रे, सज0...\nमें अबला हुं अजाण लाल तेरे दरसनकी भूखी0.\n"
            "श्री आदिनाथ निर्वाणी नमुं एसे ध्यानी. ...\nश्री शंखेश्वर पास जिनेसर अरज करुं. ...\n")
    from kruti.content import INDEX, page_kind
    assert page_kind(page) == INDEX


def test_explanation_word_after_the_verse_number_it_explains():
    # B000505 p.25: "॥ 1 ॥ ” अर्थृ-अथवा यतिनो आत्मा …" - the explanation (OCR'd "अर्थ")
    # starts on the line of the verse number it explains
    from kruti.content import _explanation_start
    assert _explanation_start("॥ 1 ॥ ” अर्थृ-अथवा यतिनो आत्मान सम्यक्त्व दशन निमे ज्ञान")
    assert _explanation_start("व्याख्या-हे श्री सीमंधर स्वामी, तमे माहरी विनति सांभळो")
    assert not _explanation_start("॥ 2 ॥ सेत्रुंजा गिरनार जीव तुम, अष्टापद जातां")
    assert not _explanation_start("समुद्यताभिः श्रीवर्द्धमानजिनदत्तमतप्रवृत्तान्")
