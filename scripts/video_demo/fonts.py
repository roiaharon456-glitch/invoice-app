import os

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")

_FILES = {
    ("hebrew", False): "NotoSansHebrew-Regular.ttf",
    ("hebrew", True): "NotoSansHebrew-Bold.ttf",
    ("latin", False): "DejaVuSans.ttf",
    ("latin", True): "DejaVuSans-Bold.ttf",
}


def font_path(bold=False, family="hebrew"):
    name = _FILES[(family, bold)]
    path = os.path.join(ASSETS_DIR, name)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Bundled font not found: {path}")
    return path
