SET = "unseen"
FILE = "kruti-samples-extra/round4/R4_STOTRATRAIEE.pdf"
PAGES = (31, 34)
# Commentary book (Svayambhu stotra): each number has a 2-line Sanskrit verse (॥n॥) followed
# by a 4-line Hindi verse rendering ending "n." - both printed as verse, both labelled as
# gathas (in printed order); the Gujarati "અર્થ :-" meaning is skipped, as are the
# metre lines "( વંશસ્થ છંદ )", "( સ્ત્રગ્વિણી છંદ )", "( ઉપજાતિ છંદ )" and stray OCR noise lines.
# Suvidhinath stuti starts on p30 (its verses 43-45 are in range); Shreyansnath stuti continues
# onto p35 (only Sanskrit verse 51 is in range).
KRUTIS = [
    ("૯. શ્રી પુષ્પદંત ( સુવિધિનાથ ) જિન સ્તુતિ", [
        ("31:2", "31:3"), ("31:4", "31:7"), ("31:13", "31:15"), ("31:16", "31:19"),
        ("31:26", "31:27"), ("32:2", "32:5")]),
    ("૧૦. શ્રી શીતલનાથ જિન સ્તુતિ", [
        ("32:13", "32:14"), ("32:16", "32:19"), ("33:2", "33:3"), ("33:4", "33:8"),
        ("33:14", "33:16"), ("33:17", "33:20"), ("33:27", "33:29"), ("34:2", "34:5"),
        ("34:12", "34:13"), ("34:14", "34:17")]),
    ("૧૧. શ્રી શ્રેયાંસનાથ જિન સ્તુતિ", [("34:26", "34:27")]),
]
