SET = "tune"
FILE = "kruti-samples-extra/round4/R4_SHIVSTOTRA.pdf"
PAGES = (64, 67)
# Sanskrit stotras with a Hindi translation under a rule on each page: only the Sanskrit
# verses are gathas; the translation, footnotes, "॥ इति ... सम्पूर्णम् ॥" colophons, running
# headers and ornaments are left out. वेदसारशिवस्तवः starts on page 62 (verses 1-6 outside).
# Jyotirlinga verse 3 crosses from page 66 to 67.
KRUTIS = [
    ("वेदसारशिवस्तवः (continued from page 63)", [
        ("64:2", "64:5"),
        ("64:6", "64:9"),
        ("64:10", "64:13"),
        ("65:1", "65:4"),
        ("65:5", "65:8")]),
    ("द्वादशज्योतिर्लिङ्गस्मरणम्", [
        ("66:1", "66:2"),
        ("66:3", "66:4"),
        ("66:5", "67:2"),
        ("67:3", "67:4")]),
]
