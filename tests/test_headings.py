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
