SET = "tune"
FILE = "kruti-samples-extra/round6/R6_DASHLAKSHAN.pdf"
PAGES = (24, 27)
# Dashlakshan mandal vidhan. End of the आर्जव puja: 2-line chaupai arghya stanzas (each
# followed by a mantra line), the jaymala doha, and the 2-line बेसरी stanzas ending in the
# refrain "आरजव भाव धरै जे जीवा" (the first stanza 24:21-22 crosses no page). Closing doha.
# Then the सत्य puja: 4-line adilla sthapana and 4-line त्रिभंगी ashtak stanzas (printed as
# two couplets with a gap, but one stanza per offering, refrain "…परमा जजि जानौ");
# the 7th stanza (27:22) runs onto p28. Mantra lines and headings are left out.
KRUTIS = [
    ("उत्तम आर्जव धर्मपूजा", [
        ("24:2", "24:3"), ("24:5", "24:6"), ("24:8", "24:9"), ("24:11", "24:12"),
        ("24:14", "24:15"),
        ("24:18", "24:19"),
        ("24:21", "24:22")] + regular(25, 2, 7) + [
        ("25:17", "25:18")]),
    ("उत्तम सत्य धर्म पूजा", [
        ("26:3", "26:6"),
        ("26:10", "26:13"), ("26:15", "26:18"),
        ("27:2", "27:5"), ("27:7", "27:10"), ("27:12", "27:15"), ("27:17", "27:20")]),
]
