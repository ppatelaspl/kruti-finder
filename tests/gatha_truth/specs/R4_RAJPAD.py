SET = "tune"
FILE = "kruti-samples-extra/round4/R4_RAJPAD.pdf"
PAGES = (24, 27)
# Shrimad Rajchandra poems, numbered gathas ("... n" at line end). Headings "(૧૨)", titles,
# metre lines "(સવૈયા)", "(મનહર છંદ)", the subtitle "(એક ગરીબની વધતી ગયેલી તૃષ્ણા)" and the
# "-વિ. સં. ૧૯૪૧" date lines are not gatha lines. Brahmacharya doha starts on p23 (gathas 4-7 here).
KRUTIS = [
    ("બ્રહ્મચર્ય વિષે સુભાષિત", regular(24, 2, 4, per=2)),
    ("સામાન્ય મનોરથ", [("24:14", "24:17"), ("24:18", "25:3"), ("25:4", "25:7"), ("25:8", "25:11")]),
    ("તૃષ્ણાની વિચિત્રતા", [("25:17", "26:7"), ("26:8", "26:15"), ("26:16", "27:7"), ("27:8", "27:15")]),
]
