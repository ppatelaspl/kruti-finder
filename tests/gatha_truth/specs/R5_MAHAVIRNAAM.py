SET = "tune"
FILE = "kruti-samples-extra/round5/R5_MAHAVIRNAAM.pdf"
PAGES = (88, 91)
# Modern Hindi bhajans, unnumbered stanzas (one gatha per printed block); the opening
# refrain block counts as a gatha. Tune lines (तर्ज - …) and titles are never part of a gatha.
# p88: the "आ-आ ऽ शरण में आ ऽऽऽ-2" line closes each printed block, so it is the last line.
# p90: lines 20-22 are OCR debris from the bell ornament / page number.
# p91: OCR lost every "सहारे……………" refrain-cue line that closes each stanza, so each
#      gatha ends on the line before it (the line ending in ।।).
KRUTIS = [
    ("चन्दन बन जायेगा", [
        ("88:3", "88:7"),
        ("88:8", "88:14"),
        ("88:15", "88:21")]),
    ("साधु निर्ग्रन्थ को है नमन", [
        ("89:3", "89:4"),
        ("89:5", "89:9"),
        ("89:10", "89:14")]),
    ("गुरुवर प्यारा प्यारा लगे", [
        ("90:3", "90:4"),
        ("90:5", "90:7"),
        ("90:8", "90:10"),
        ("90:11", "90:13"),
        ("90:14", "90:16"),
        ("90:17", "90:19")]),
    ("हम तो गुरुवर के सहारे", [
        ("91:3", "91:4"),
        ("91:5", "91:6"),
        ("91:7", "91:8"),
        ("91:9", "91:10"),
        ("91:11", "91:12"),
        ("91:13", "91:14")]),
]
