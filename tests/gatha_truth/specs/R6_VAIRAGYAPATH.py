SET = "tune"
FILE = "kruti-samples-extra/round6/R6_VAIRAGYAPATH.pdf"
PAGES = (22, 25)
# p22:2-10: last three 3-line stanzas of "निर्ग्रन्थ भावना" (heading on p21). Each ends with the
# refrain cue "निर्ग्रन्थता..." on the same OCR line, after the verse text; per rule 10 the
# gatha ends before the cue (at the ॥). Then "अलोचना पाठ": doha ॥1॥, 2-line chaupai ॥2-33॥,
# two closing dohas ॥34-35॥ (p24). "( दोहा)"/"(चौपाई)" headings left out. p25: "भावना बत्तीसी"
# verses 1-13 (continues past p25). Header/footer (AtmaDharma) lines left out.
KRUTIS = [
    ("निर्ग्रन्थ भावना", [
        ("22:2", "22:4<जगत-फेरी॥"), ("22:5", "22:7<मेरी ॥"), ("22:8", "22:10<मेरी ॥")]),
    ("अलोचना पाठ",
        [("22:13", "22:14")] + regular(22, 16, 6) + regular(23, 2, 14) + regular(24, 2, 12)
        + [("24:27", "24:28"), ("24:29", "24:30")]),
    ("भावना बत्तीसी", regular(25, 3, 13)),
]
