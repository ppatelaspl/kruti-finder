SET = "tune"
FILE = "kruti-samples/B039544_Prachin_Sazzaya_Mahodadhi_Part_1_004614_प्राचीन सज्झाय महोदधि भाग-1 सचित्र.pdf"
PAGES = (263, 267)
KRUTIS = [
    ("(continued from page 262)", regular(263, 2, 7)),
    ("સંગ્રામ સોનીની સજઝાય",                       # ( દોહા ) 1-3, then ઢાલ 1-19
     regular(263, 25, 3) + regular(263, 31, 3) + regular(264, 1, 16)),
    ("દેવકીના છ પુત્રની સજઝાય અથવા છ સાધુની",
     [("265:6", "265:7"), ("265:8", "265:10")] + regular(265, 12, 12) + regular(266, 2, 5)),
    ("મેઘરથ રાજાની સજઝાય",
     [("266:19", "266:21")] + regular(266, 22, 6) + regular(267, 2, 14)),
]
