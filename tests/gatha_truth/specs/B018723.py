SET = "tune"
FILE = "kruti-samples/B018723_sazzay_sarita_023239_std.pdf"
PAGES = (283, 286)
# Gujarati sajjhays; each gatha ends in a right-aligned refrain-cue line holding its number.
KRUTIS = [
    ("૧૩૨. રહનેમિને રાજીમતીની સજઝાયો (प)",          # 3 printed lines per gatha (2 + cue)
     regular(283, 1, 8, per=3) + [("283:25", "284:0")] + regular(284, 1, 9, per=3)),
    ("૧૩૩. રાજીમતીની સજઝાય", [("285:1", "285:2")] + regular(285, 3, 12)),
    ("૧૩૪. રાવણ મંદોદરીની સજ્ઝાયો (૧)", regular(286, 1, 5)),
    ("૧૩૫. રાવણ મંદોદરીની સજ્ઝાયો (૨) (ઢાળ-૪)",       # ઢાળ ૧ gathas 1-3, ઢાળ ૨ gathas 1-2; continues
     [("286:13", "286:16"), ("286:17", "286:18"), ("286:19", "286:20"),
      ("286:22", "286:25"), ("286:26", "286:27")]),
]
