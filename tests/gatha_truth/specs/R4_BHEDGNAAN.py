SET = "tune"
FILE = "kruti-samples-extra/round4/R4_BHEDGNAAN.pdf"
PAGES = (50, 53)
# Bhajan book, one bhajan per page. The opening ટેક block is labelled as a gatha.
# p50: 3-line stanzas, numbers 1-5 printed at stanza end, last two stanzas unnumbered.
# p51: number is printed after each stanza's FIRST line; stanza ends at the "સુખ શાંતિ......." cue.
# p52: unnumbered couplets (printed order kept as-is).
# p53: after the 2-line ટેક, every line ends with the "।। આજ ।।" refrain cue = one stanza each.
KRUTIS = [
    ("દેવ સ્તુતિ-૩૦", [("50:2", "50:3"), ("50:4", "50:6"), ("50:7", "50:9"), ("50:10", "50:12"),
                      ("50:13", "50:15"), ("50:16", "50:18"), ("50:19", "50:21"), ("50:22", "50:24")]),
    ("જિનેન્દ્ર ભક્તિ-૩૧", [("51:2", "51:3"), ("51:4", "51:7"), ("51:8", "51:11"),
                           ("51:12", "51:15"), ("51:16", "51:19"), ("51:20", "51:23")]),
    ("પંચ પરમેષ્ઠી સ્તુતિ-૩૨", regular(52, 2, 9, per=2)),
    ("જિનેન્દ્ર ભક્તિ-૩૩", [("53:2", "53:3")] + [(f"53:{i}", f"53:{i}") for i in range(4, 19)]),
]
