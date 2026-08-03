from bidi.algorithm import get_display

from fonts import font_path

_HEBREW_RANGE = (0x0590, 0x05FF)


def rtl(text):
    """Reorders logical-order Hebrew text into visual (left-to-right drawable) order."""
    return get_display(text)


def _is_hebrew(ch):
    return _HEBREW_RANGE[0] <= ord(ch) <= _HEBREW_RANGE[1]


def _split_runs(text):
    runs = []
    cur, cur_heb = "", None
    for ch in text:
        heb = _is_hebrew(ch)
        if cur_heb is None or heb == cur_heb:
            cur += ch
            cur_heb = heb
        else:
            runs.append((cur, cur_heb))
            cur = ch
            cur_heb = heb
    if cur:
        runs.append((cur, cur_heb))
    return runs


def draw_rtl_text(draw, xy, text, size, bold=False, fill="black", align="right", font_cache=None):
    """Draws logical-order Hebrew/mixed text correctly, switching between a Hebrew font
    (for Hebrew glyphs) and a Latin font (for digits/punctuation the Hebrew subset lacks).
    `align` is 'right', 'left', or 'center'; vertical position is always centered on xy[1].
    """
    from PIL import ImageFont

    cache = font_cache if font_cache is not None else {}

    def get_font(family):
        key = (family, bold, size)
        if key not in cache:
            cache[key] = ImageFont.truetype(font_path(bold=bold, family=family), size)
        return cache[key]

    runs = _split_runs(rtl(text))
    widths = []
    for run_text, is_heb in runs:
        f = get_font("hebrew" if is_heb else "latin")
        widths.append(draw.textlength(run_text, font=f))
    total = sum(widths)

    x, y = xy
    if align == "right":
        x -= total
    elif align == "center":
        x -= total / 2

    for (run_text, is_heb), w in zip(runs, widths):
        f = get_font("hebrew" if is_heb else "latin")
        draw.text((x, y), run_text, font=f, fill=fill, anchor="lm")
        x += w

    return total
