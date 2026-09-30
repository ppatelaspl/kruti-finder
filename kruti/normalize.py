"""Text normalisation for matching Kruti text across scripts, spellings and OCR noise.

Two representations are used:
  * "light" text  - readable Devanagari with digits, dandas and spaces kept
                    (used for verse-number detection and for showing text to reviewers)
  * "key" text    - letters only, spelling variants folded
                    (used for fuzzy matching). Every key character remembers its
                    position in the light text so matches can be mapped back to pages.
"""
import re
import unicodedata

# The Gujarati Unicode block (U+0A80-U+0AFF) is laid out in parallel with Devanagari
# (U+0900-U+097F), so a fixed offset converts one script to the other.
_GUJ_START, _GUJ_END = 0x0A80, 0x0AFF
_GUJ_TO_DEV_OFFSET = 0x0A80 - 0x0900

_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\ufeff"), None)
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ufffd]")

_ELLIPSIS = re.compile(r"\.{3,}|…")
_VARIANT = re.compile(r"\{[^}]*\}")

# Spelling variants common in old Maru-Gurjar / Rajasthani texts and in OCR output.
_FOLDS = str.maketrans({
    "ण": "न", "ष": "स", "श": "स", "ब": "व", "ळ": "ल",
    "ी": "ि", "ू": "ु", "ई": "इ", "ऊ": "उ",
    "ै": "े", "ौ": "ो", "ऐ": "ए", "औ": "ओ",
    "ँ": "ं",
})
_DROP_WHEN_FOLDING = {"\u094d", "\u093c"}  # halant, nukta: OCR drops these often


def gujarati_to_devanagari(text: str) -> str:
    return "".join(
        chr(ord(c) - _GUJ_TO_DEV_OFFSET) if _GUJ_START <= ord(c) <= _GUJ_END else c
        for c in text
    )


def devanagari_to_gujarati(text: str) -> str:
    """For showing a Gujarati book's text in its own script (dandas stay as they are)."""
    return "".join(
        chr(ord(c) + _GUJ_TO_DEV_OFFSET) if 0x0900 <= ord(c) <= 0x097F and c not in "।॥" else c
        for c in text
    )


def script_of(text: str) -> str:
    """'Gujarati' or 'Devanagari' by majority of letters; '' when neither is present."""
    guj = sum(1 for c in text or "" if _GUJ_START <= ord(c) <= _GUJ_END)
    dev = sum(1 for c in text or "" if 0x0900 <= ord(c) <= 0x097F and c not in "।॥")
    if not guj and not dev:
        return ""
    return "Gujarati" if guj > dev else "Devanagari"


def light_normalize(text: str) -> str:
    """Readable, script-unified text. Keeps digits, dandas and single spaces."""
    text = unicodedata.normalize("NFC", text or "").translate(_ZERO_WIDTH)
    text = _CONTROL.sub(" ", text)
    text = gujarati_to_devanagari(text).translate(_DEV_DIGITS)
    text = text.replace("।।", "॥").replace("||", "॥").replace("|", "।")
    return re.sub(r"[ \t\r\f\v]+", " ", text)


def clean_reference(text: str) -> str:
    """Remove the Excel's editorial markup: #...# markers and {variant} readings."""
    text = _VARIANT.sub("", str(text or ""))
    return text.replace("#", "")


def split_segments(text: str) -> list:
    """An Aadi/Ant Vakya may skip verses with '...'; each piece is searched separately."""
    return [s.strip() for s in _ELLIPSIS.split(text) if s.strip()]


def _is_key_char(c: str) -> bool:
    cp = ord(c)
    if 0x0964 <= cp <= 0x096F:          # dandas and digits
        return False
    return 0x0900 <= cp <= 0x0963 or 0x0971 <= cp <= 0x097F


def make_key(text: str, fold: bool = True):
    """Return (key, index_map). index_map[i] = position in light text of key char i."""
    light = light_normalize(text)
    chars, index_map = [], []
    for i, c in enumerate(light):
        if not _is_key_char(c):
            continue
        if fold:
            if c in _DROP_WHEN_FOLDING:
                continue
            c = c.translate(_FOLDS)
        chars.append(c)
        index_map.append(i)
    return "".join(chars), index_map


def key_only(text: str, fold: bool = True) -> str:
    return make_key(text, fold)[0]
