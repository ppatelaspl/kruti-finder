SET = "tune"
FILE = "kruti-samples-extra/round6/R6_BHAJANMALA.pdf"
PAGES = (4, 7)
# Hindi bhajan/ghazal booklet. Unnumbered couplets: each printed 2-line couplet is a gatha;
# a closing दोहा couplet inside a Kruti is also a gatha. Opening टेक line/couplet = gatha 1.
# Refrain cues after a gatha number (॥१॥ हमें०, ॥१॥चाचा०) are cut off; the trailing
# "जगत से न्यारा हिन्दुस्तान" cue line (4:26) and the prose bridge 7:21 are not gathas.
# भजन 10 (7:23) only has its opening refrain line inside the range; its कवित्त runs onto p8.
KRUTIS = [
    ("स्वदेश प्रेम २ (शेर)", [
        ("4:5", "4:6"), ("4:7", "4:8"), ("4:9", "4:10"), ("4:11", "4:12"),
        ("4:13", "4:14")]),
    ("भजन ३", [
        ("4:16", "4:17"), ("4:18", "4:19"), ("4:20", "4:21"), ("4:22", "4:23"),
        ("4:24", "4:25")]),
    ("गज़ल राष्ट्रीय ४", regular(5, 3, 6)),
    ("भजन ५", [
        ("5:16", "5:17"),
        ("5:18", "5:19<॥ १॥"),
        ("5:20", "5:21<॥ રા"),
        ("5:22", "5:23<॥૨॥"),
        ("5:24", "5:25<॥४॥")]),
    ("भजन ६ (आज कल की सन्तान)", [
        ("6:4", "6:4"),
        ("6:5", "6:6<॥१॥"),
        ("6:7", "6:8<॥२॥"),
        ("6:9", "6:10<॥दे॥"),
        ("6:11", "6:12<न आई")]),
    ("गजल ७", regular(6, 14, 6)),
    ("भजन ८ (पुत्र को माता का उपदेश)", regular(7, 4, 4)),
    ("ख्याल ९", [
        ("7:13", "7:14"), ("7:15", "7:16"), ("7:17", "7:18"), ("7:19", "7:20")]),
    ("भजन १०", [("7:23", "7:23")]),
]
