SET = "tune"
FILE = "kruti-samples-extra/round4/R4_BHAKTAMAR_GUJ.pdf"
PAGES = (9, 12)
# Commentary book: Gujarati verse rendering of Bhaktamar (4 italic lines, number at the end of
# the 4th), each followed by "ભાવાર્થ :" prose (skipped). The decorative italic verse font
# OCRs as garbage, but each printed verse line has its OCR line; labels point at those.
# Verses 1-3 are on p8 (out of range). Page borders/ornaments OCR as noise lines (not labelled).
# Verse 13 (p12): 4 printed lines but only 3 OCR lines (12:5-12:7); first line taken as 12:5.
KRUTIS = [
    ("શ્રી ભક્તામર સ્તોત્ર", [
        ("9:8", "9:11"), ("9:18", "9:21"), ("9:27", "9:30"),
        ("10:9", "10:12"), ("10:17", "10:20"), ("10:26", "10:29"),
        ("11:6", "11:9"), ("11:16", "11:19"), ("11:24", "11:27"),
        ("12:5", "12:7"), ("12:17", "12:20"), ("12:25", "12:28")]),
]
