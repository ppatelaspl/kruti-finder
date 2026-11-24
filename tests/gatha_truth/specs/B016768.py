SET = "tune"
FILE = "kruti-samples/B016768_navpad_manjusha_022757_hr6.pdf"
PAGES = (227, 230)
# Numbered stutis (૭)…(૧૩): 4 gathas of 4 printed lines each, "॥n॥" at the right margin.
# On 229 OCR put some of the margin marks on their own lines, out of order (229:17-18 are
# the marks of (૧૦) gathas 2-3, 229:24 that of gatha 4).
KRUTIS = [
    ("(continued from page 226)", [("227:2", "227:5")]),            # gatha 4
    ("(૭)", regular(227, 7, 4, per=4)),
    ("(८)", [("227:24", "227:27"), ("228:0", "228:3"), ("228:4", "228:7"), ("228:8", "228:11")]),
    ("(૯)", regular(228, 13, 4, per=4)),
    ("(૧૦)", [("229:1", "229:4 + 229:5"), ("229:6", "229:9"), ("229:10", "229:13"),
              ("229:14", "229:19")]),
    ("(૧૧)", [("229:21", "229:25 + 229:26"), ("229:27", "229:30 + 229:31"),
              ("229:32", "229:35"), ("230:0", "230:3")]),
    ("(૧૨)", regular(230, 5, 4, per=4)),
    ("(१३)", regular(230, 22, 2, per=4)),                           # continues on 231
]
