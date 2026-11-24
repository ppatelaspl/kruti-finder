SET = "tune"
FILE = "kruti-samples-extra/round6/R6_PUJANJALI.pdf"
PAGES = (81, 84)
# Puja book. Each stanza is a gatha; the "ॐ ह्रीं … स्वाहा ॥n॥" mantra line after it (which
# carries the running arghya number) is left out, as are the metre headings "( झूलना )" etc.
# Kruti 1 (heading on p79, "पाँच परमेष्ठी … १७ अर्घ्य") has stanzas 1-9 before the range; stanza 14
# crosses p81->p82 (p82:1 is OCR of the bracketed first line, text doubled); the closing
# पूर्णार्घ्य doha (82:21-22) is a gatha. Kruti 2: 2-line paddhari/trotak stanzas numbered ।।1।।…
# ।।17।; p84:1 is the stanza 9 first line (text doubled by OCR). Kruti 2 continues past p84.
KRUTIS = [
    ("पाँच परमेष्ठी, चार मंगल, चार उत्तम व चार शरण के लिए १७ अर्घ्य", [
        ("81:2", "81:5"), ("81:8", "81:11"), ("81:14", "81:17"), ("81:20", "81:23"),
        ("81:26", "82:2"), ("82:5", "82:8"), ("82:11", "82:12"), ("82:15", "82:18"),
        ("82:21", "82:22")]),
    ("भूतकाल में हुए २४ तीर्थकरों के लिए अर्घ्य", [
        ("83:4", "83:5"), ("83:7", "83:8"), ("83:10", "83:11"), ("83:13", "83:14"),
        ("83:16", "83:17"), ("83:19", "83:20"), ("83:22", "83:23"), ("83:25", "83:26"),
        ("84:1", "84:2"), ("84:4", "84:5"), ("84:7", "84:8"), ("84:10", "84:11"),
        ("84:13", "84:14"), ("84:16", "84:17"), ("84:19", "84:20"), ("84:22", "84:23"),
        ("84:25", "84:26")]),
]
