"""Generate the app icon in Aspire brand colours (png, ico, icns)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

NAVY, GOLD, ORANGE = "#011d45", "#f8bb13", "#ee7532"
OUT = Path(__file__).resolve().parent.parent / "app" / "assets"
FONT = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"   # has Devanagari glyphs


def draw(size=1024):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pad = size // 16
    d.rounded_rectangle([pad, pad, size - pad, size - pad], radius=size // 5, fill=NAVY)
    # an open book: two gold pages
    cx, top, bot = size // 2, int(size * 0.60), int(size * 0.80)
    d.polygon([(int(size * .20), top), (cx, top + size // 20), (cx, bot), (int(size * .20), bot - size // 20)], fill=GOLD)
    d.polygon([(int(size * .80), top), (cx, top + size // 20), (cx, bot), (int(size * .80), bot - size // 20)], fill=ORANGE)
    f = ImageFont.truetype(FONT, int(size * 0.36), layout_engine=ImageFont.Layout.RAQM)
    d.text((cx, int(size * 0.36)), "कृ", font=f, fill=GOLD, anchor="mm")
    return im


img = draw()
img.save(OUT / "icon.png")
img.save(OUT / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
img.save(OUT / "icon.icns")
print("icons written to", OUT)
