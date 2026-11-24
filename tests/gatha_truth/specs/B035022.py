SET = "unseen"
FILE = "kruti-samples/B035022_Ud_Jare_Panchi_Mahavirdeh_Mai_150dpi.pdf"
PAGES = (97, 100)
# Sanskrit/Apabhramsha stotras with metre headings "(अथ मालिनी)" etc. (not gatha lines).
KRUTIS = [
    ("(continued from page 96)",                 # gathas 20-24, 4 printed lines each
     [("97:0", "97:3"), ("97:5", "97:8"), ("97:9", "97:12"), ("97:14", "97:17"),
      ("97:19", "97:23")]),
    ("श्री सीमन्धरस्वामिजिन स्तवनम्‌",              # by Somasundarasuri
     regular(98, 3, 8) + [("98:19", "98:22")]),
    ("श्री सीमस्थरसामिजिन स्तवनम्",                # by Merunandan; भास heading after 5; continues past 100
     regular(99, 3, 5) + regular(99, 14, 2, per=4) + regular(100, 1, 5, per=4)),
]
