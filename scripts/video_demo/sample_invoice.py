"""Generates a placeholder invoice/receipt image used as the upload sample in the demo recording."""
from PIL import Image, ImageDraw

from text_rtl import draw_rtl_text


def generate(out_path, reason="ציוד משרדי", amount="245.90"):
    width, height = 720, 960
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    cache = {}

    def text(x, y, s, size, bold=False, fill=(20, 20, 20), align="right"):
        draw_rtl_text(draw, (x, y), s, size, bold=bold, fill=fill, align=align, font_cache=cache)

    draw.rectangle([0, 0, width, 130], fill=(37, 99, 138))
    text(width / 2, 65, "חשבונית מס", 40, bold=True, fill="white", align="center")

    text(width - 40, 190, "משק הבית הכחול בע\"מ", 30, bold=True, align="right")
    text(width - 40, 225, "ח.פ. 514123456", 20, fill=(100, 100, 100), align="right")
    text(width - 40, 255, "רחוב הרצל 12, תל אביב", 20, fill=(100, 100, 100), align="right")

    y = 340
    rows = [
        ("תאריך:", "03/08/2026"),
        ("מס' חשבונית:", "INV-20260803"),
        ("תיאור:", reason),
    ]
    for label, value in rows:
        text(width - 40, y, label, 26, fill=(90, 90, 90), align="right")
        text(width - 260, y, value, 30, bold=True, align="right")
        y += 60

    draw.line([(40, y + 20), (width - 40, y + 20)], fill=(210, 210, 210), width=2)
    y += 60
    text(width - 40, y, "סה\"כ לתשלום:", 26, fill=(90, 90, 90), align="right")
    text(width - 260, y, f"{amount} ₪", 40, bold=True, fill=(37, 99, 138), align="right")

    draw.rectangle([0, height - 60, width, height], fill=(245, 247, 250))
    text(width / 2, height - 30, "תודה על הרכישה", 20, fill=(150, 150, 150), align="center")

    img.save(out_path)
    return out_path


if __name__ == "__main__":
    import sys
    generate(sys.argv[1] if len(sys.argv) > 1 else "sample_invoice.png")
