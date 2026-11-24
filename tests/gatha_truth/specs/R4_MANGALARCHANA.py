SET = "tune"
FILE = "kruti-samples-extra/round4/R4_MANGALARCHANA.pdf"
PAGES = (67, 70)
# A puja ("श्रीसिद्ध पूजन") with no gatha numbers: each printed stanza is a gatha - the
# sthapana doha, eight 4-line ashtak stanzas and the 8-line arghya stanza, then (after the
# जयमाला / (दोहा) / (पद्धरि) part headings) the doha and the 2-line paddhari couplets.
# The "ॐ ह्रीं … स्वाहा" mantra lines and the invocation prose are not gathas. The closing
# doha is on page 71, outside the range.
KRUTIS = [
    ("श्रीसिद्ध पूजन", [
        ("67:3", "67:4"),
        ("67:9", "67:12"), ("67:15", "67:18"), ("67:21", "67:24"),
        ("68:1", "68:4"), ("68:7", "68:10"), ("68:13", "68:16"), ("68:19", "68:22"),
        ("68:24", "69:2"),
        ("69:4", "69:11"),
        ("69:15", "69:16"),
        ("69:18", "69:19"), ("69:20", "69:21"), ("69:22", "69:23"),
    ] + regular(70, 1, 11, per=2)),
]
