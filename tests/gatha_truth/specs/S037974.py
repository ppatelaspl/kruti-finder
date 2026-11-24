SET = "unseen"
FILE = "kruti-samples/S037974_chaityavandan_chauvisi_003635_hr.pdf"
PAGES = (40, 43)
# Chauvisi chaityavandans: 3 gathas of 2 lines each, ending "...n...".
KRUTIS = [
    ("(continued from page 39)", regular(40, 1, 2)),          # gathas 2-3
    ("अरनाथनु [૨૦]", regular(40, 6, 3)),
    ("मल्लिनाथ નુ [૨૬]", regular(40, 13, 3)),
    ("मुनिसुव्रत स्वामी चु [૨૦]", regular(40, 20, 2) + [("41:1", "41:2")]),
    ("नमिनाथ ગું [२१]", regular(41, 4, 3)),
    ("नेमिनाथनु [૨૨]", regular(41, 11, 3)),
    ("पाश्वनाथ नु [२३]", regular(41, 18, 3)),
    ("महावीर 'स्वामी नु [૨૪]", regular(42, 2, 3)),
    ("भी ऋषभदेव नु [९]", regular(42, 10, 3)),
    ("अजितनाथनु [૨]", regular(42, 17, 2) + [("42:22", "42:23")]),   # 42:21 is OCR noise
    ("संभवनाथ તુ [૨]", regular(43, 2, 3)),
    ("अभिनंदन नं [૪]", regular(43, 9, 3)),
    ("समतिनाथ તુ |]", regular(43, 16, 3)),
    ("प्रभु ગુ [૬]", regular(43, 23, 1)),                     # continues on page 44
]
