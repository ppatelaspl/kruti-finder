SET = "tune"
FILE = "kruti-samples/S027836_chaityavandan_parvamala_003634_h_r.pdf"
PAGES = (27, 31)
# Numbers after dots (…५…); OCR drops several of them (page 31).
KRUTIS = [
    ("(continued from page 26)", regular(27, 1, 11) + [("27:23", "28:3")]),
    ("[२३] मौन एकादशी स्तवन", regular(28, 5, 1, per=4) + regular(28, 9, 5, per=3)
     + regular(29, 1, 7, per=3)),
    ("[४] मल्लि जिन", [("29:23", "29:24"), ("30:1", "30:2"), ("30:3", "30:4")]),
    ("[५] उत्तम तिथि अकादशी", regular(30, 6, 5)),
    ("एकादशी सामान्य", [("30:17", "30:19"), ("30:20", "30:21"), ("30:22", "30:23"),
                        ("30:25", "30:26")] + regular(31, 1, 5)),
    ("[२]", regular(31, 12, 3)),
    ("[३]", regular(31, 19, 3)),
]
