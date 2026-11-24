SET = "unseen"
FILE = "kruti-samples-extra/anandghan_stavanavali_guj.pdf"
PAGES = (8, 11)
# Anandghan stavans, 2 printed lines per gatha with the number at the end of the 2nd.
# Stavana 8 and 13: the opening refrain line(s) belong to gatha 1; in 13 every gatha ends
# in a refrain line holding the number.
KRUTIS = [
    ("(continued from page 7) સુપાસ", regular(8, 1, 7)),
    ("સ્તવના ૮ મી", [("8:17", "8:19")] + regular(8, 20, 3) + regular(9, 1, 3)),
    ("સ્તવના ૯ મી", regular(9, 9, 8)),
    ("સ્તવના ૧૦ મી", [("9:27", "10:1")] + regular(10, 2, 5)),
    ("સ્તવના ૧૧ મી", regular(10, 14, 6)),
    ("સ્તવના ૧૨ મી", regular(11, 3, 6)),
    ("સ્તવના ૧૩ મી", [("11:17", "11:20"), ("11:21", "11:23"), ("11:24", "11:26")]),
]
