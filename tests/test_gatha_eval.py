"""Gatha Lines: the accuracy tool's scoring.   Run:  python -m pytest tests"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from eval_gatha import score                       # noqa: E402

TRUTH = [{"title": "शांतिनाथ स्तवन", "gathas": [
             {"no": "1", "first": "शांति जिनेसर सोलमा,", "last": "अचिरा सुत वंदो ॥1॥"},
             {"no": "2", "first": "विश्वसेन कुल नभ मणि,", "last": "भविजन सुख कंदो ॥2॥"}]},
         {"title": "नेमिनाथ स्तवन", "gathas": [
             {"no": "1", "first": "नेम जिनेसर वंदिये,", "last": "राजुल नार ॥1॥"},
             {"no": "2", "first": "तोरण आवी पाछा वळ्या,", "last": "गिरनार ॥2॥"}]}]


def pred(*krutis):
    """krutis: lists of (first, last); each list is one predicted Kruti."""
    return [(i, f, l) for i, k in enumerate(krutis) for f, l in k]


def test_perfect():
    p = pred([("शांति जिनेसर सोलमा,", "अचिरा सुत वंदो ॥1॥"), ("विश्वसेन कुल नभ मणि,", "भविजन सुख कंदो ॥2॥")],
             [("नेम जिनेसर वंदिये,", "राजुल नार ॥1॥"), ("तोरण आवी पाछा वळ्या,", "गिरनार ॥2॥")])
    s = score(TRUTH, p)
    assert (s["kruti_ok"], s["kruti"], s["gatha_ok"], s["gatha"]) == (2, 2, 4, 4)
    assert (s["first_ok"], s["last_ok"], s["extra"], s["pred"]) == (4, 4, 0, 4)


def test_merged_kruti_and_wrong_last_line_and_extra_row():
    p = pred([("शांति जिनेसर सोलमा,", "अचिरा सुत वंदो ॥1॥"), ("विश्वसेन कुल नभ मणि,", "कुछ और ही ॥2॥"),
              ("नेम जिनेसर वंदिये,", "राजुल नार ॥1॥"), ("तोरण आवी पाछा वळ्या,", "गिरनार ॥2॥"),
              ("यह प्रस्तावना है जो", "गलत पंक्ति है")])
    s = score(TRUTH, p)
    assert s["kruti_ok"] == 0                      # both Kruti merged into one
    assert (s["gatha_ok"], s["first_ok"], s["last_ok"]) == (4, 4, 3)
    assert (s["extra"], s["pred"]) == (1, 5)


def test_ocr_slip_still_matches():
    p = pred([("शांति जिनेसर सोलमा", "अचिरा सुत वंदो ॥१॥"), ("विश्वसेन कुळ नभ मणि,", "भविजन सुख कंदो ॥2॥")],
             [("नेम जिनेसर वंदिये,", "राजुल नार ॥1॥"), ("तोरण आवी पाछा वळ्या,", "गिरनार ॥2॥")])
    s = score(TRUTH, p)
    assert (s["gatha_ok"], s["first_ok"], s["last_ok"], s["kruti_ok"]) == (4, 4, 4, 2)
