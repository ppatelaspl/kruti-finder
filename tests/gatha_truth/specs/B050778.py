SET = "tune"
FILE = "kruti-samples/B050778_sazzay_sagar_part_02_034188_hr6.pdf"
PAGES = (253, 256)
# Two-column couplets, number at the end of the second line. [૭૦૦] opens with five
# unnumbered દુહા printed one per full-width line (each line a whole દુહો), then ઢાળ 1-22;
# its gatha 1 has no number and ends with the full-width refrain line 253:21.
KRUTIS = [
    ("(continued from page 252)", regular(253, 1, 6)),
    ("[૭૦૦] ચંદ્રગુપ્તરાજાનાં ૧૬ સ્વપ્નની સજ્ઝાય",
     [("253:14", "253:14"), ("253:15", "253:15"), ("253:16", "253:16"),
      ("253:17", "253:17"), ("253:18", "253:18"),
      ("253:19", "253:21")] + regular(253, 22, 6) + regular(254, 1, 15)),
    ("[૭૦૧] ચંદ્રગુપ્તરાજાનાં ૧૬ સ્વપ્નની સજ્ઝાય", regular(255, 3, 17)),
    ("[૭૦૨] ચંદ્રગુપ્તનાં ૧૬ સ્વપ્નની સજ્ઝાય", [("256:2", "256:3")] + regular(256, 4, 7, per=4)),
]
