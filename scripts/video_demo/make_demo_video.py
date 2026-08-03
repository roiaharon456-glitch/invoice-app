#!/usr/bin/env python3
"""Generates an automated product-demo video for the invoice-app: a real browser
walks through the actual UI (new user -> bank details -> upload invoice -> success).
Playwright's built-in screencast video recording produces blank frames in some
sandboxed/GPU-less environments, so instead we drive the page and sample
`page.screenshot()` (which reliably forces a real paint) on a timer, then stitch
the frames into a video with ffmpeg before burning in Hebrew captions and
(optionally) a synthesized Hebrew voiceover.

Usage:
    .venv/bin/python make_demo_video.py [--no-narration] [--voice he-IL-AvriNeural]
                                         [--output output/invoice_app_demo.mp4] [--keep-tmp]
"""
import argparse
import http.client
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from fonts import font_path  # noqa: E402
from text_rtl import rtl  # noqa: E402
import narration as narration_mod  # noqa: E402
import sample_invoice  # noqa: E402

DEMO_PORT = 8765
VIEWPORT = {"width": 480, "height": 900}
END_HOLD_SECONDS = 3.0

DEMO_NAME = "ישראל ישראלי"
DEMO_BANK = {
    "account_holder": "ישראל ישראלי",
    "bank_name": "בנק הפועלים",
    "bank_number": "12",
    "branch_number": "456",
    "account_number": "123456789",
}
DEMO_REASON = "ציוד משרדי"
DEMO_AMOUNT = "245.90"

# Narration is spoken (TTS), so natural punctuation is fine there. Captions are burned
# in with ffmpeg drawtext using our bundled Hebrew-only font, which has no digit/
# punctuation glyphs and no auto-wrap - so captions avoid punctuation and are
# pre-wrapped to two short lines that fit the frame width.
SCENES = [
    {
        "narration": "מזינים שם מלא, ומתחילים תהליך מהיר ופשוט.",
        "caption": "מזינים שם מלא\nומתחילים תהליך מהיר ופשוט",
    },
    {
        "narration": "למשתמש חדש ממלאים פעם אחת את פרטי חשבון הבנק, הם יישמרו אוטומטית לפעם הבאה.",
        "caption": "למשתמש חדש ממלאים פעם אחת את פרטי הבנק\nוהם נשמרים אוטומטית לפעם הבאה",
    },
    {
        "narration": "מעלים תמונה של החשבונית, וממלאים את סיבת ההוצאה ואת הסכום.",
        "caption": "מעלים תמונה של החשבונית\nוממלאים את סיבת ההוצאה ואת הסכום",
    },
    {
        "narration": "המערכת שולחת אוטומטית מייל מסודר לאישור ההחזר, וזה הכל.",
        "caption": "המערכת שולחת אוטומטית מייל מסודר\nלאישור ההחזר וזה הכל",
    },
]


def log(msg):
    print(f"[demo-video] {msg}", flush=True)


def wait_for_server(port, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
            conn.request("GET", "/")
            resp = conn.getresponse()
            if resp.status == 200:
                return True
        except OSError:
            pass
        time.sleep(0.3)
    return False


def probe_duration(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", path,
    ])
    return float(json.loads(out)["format"]["duration"])


class Recorder:
    """Samples real page.screenshot() frames on a timer and remembers when each
    was taken, so a variable-framerate video can be reassembled with correct timing.
    """

    def __init__(self, page, frames_dir):
        self.page = page
        self.frames_dir = frames_dir
        os.makedirs(frames_dir, exist_ok=True)
        self.frames = []
        self.start = time.monotonic()

    def elapsed(self):
        return time.monotonic() - self.start

    def sample(self):
        path = os.path.join(self.frames_dir, f"frame_{len(self.frames):05d}.png")
        self.page.screenshot(path=path)
        self.frames.append((path, self.elapsed()))

    def type_with_capture(self, selector, text, char_delay=0.05):
        self.page.click(selector)
        self.sample()
        for ch in text:
            self.page.keyboard.type(ch)
            self.sample()
            time.sleep(char_delay)

    def hold(self, seconds, interval=0.15):
        deadline = self.elapsed() + seconds
        while self.elapsed() < deadline:
            self.sample()
            time.sleep(interval)


def run_scenario(recorder, sample_invoice_path):
    """Drives the UI through the full new-user flow while sampling frames. Returns
    the list of offset_seconds at which each of the SCENES narrations/captions should start.
    """
    page = recorder.page
    offsets = []

    def mark():
        offsets.append(recorder.elapsed())
        recorder.sample()

    # Scene 1: name
    mark()
    page.wait_for_selector("#name", state="visible")
    recorder.type_with_capture("#name", DEMO_NAME)
    recorder.hold(0.6)
    page.click("#step-name button.btn-primary")
    page.wait_for_selector("#step-bank.active", state="attached", timeout=5000)

    # Scene 2: bank details
    mark()
    recorder.type_with_capture("#account_holder", DEMO_BANK["account_holder"])
    recorder.type_with_capture("#bank_name", DEMO_BANK["bank_name"])
    recorder.type_with_capture("#bank_number", DEMO_BANK["bank_number"])
    recorder.type_with_capture("#branch_number", DEMO_BANK["branch_number"])
    recorder.type_with_capture("#account_number", DEMO_BANK["account_number"])
    recorder.hold(0.6)
    page.click("#step-bank button.btn-primary")
    page.wait_for_selector("#step-upload.active", state="attached", timeout=5000)

    # Scene 3: upload + expense details
    mark()
    page.set_input_files("#invoice-input", sample_invoice_path)
    page.wait_for_selector("#extra-fields", state="visible")
    recorder.sample()
    recorder.type_with_capture("#expense_reason", DEMO_REASON)
    recorder.type_with_capture("#expense_amount", DEMO_AMOUNT)
    recorder.hold(0.6)
    page.click("#submit-btn")

    # Scene 4: loading -> success
    mark()
    recorder.hold(0.5)
    page.wait_for_selector("#step-success.active", state="attached", timeout=10000)
    recorder.hold(END_HOLD_SECONDS)

    return offsets


def assemble_raw_video(frames, out_path):
    """Stitches sampled screenshots into a variable-framerate video, each frame held
    for exactly as long as it took until the next sample was captured in real time.
    """
    list_path = out_path + ".concat.txt"
    with open(list_path, "w", encoding="utf-8") as f:
        for i, (path, ts) in enumerate(frames):
            duration = (frames[i + 1][1] - ts) if i + 1 < len(frames) else 0.3
            duration = max(duration, 0.02)
            f.write(f"file '{path}'\nduration {duration:.3f}\n")
        f.write(f"file '{frames[-1][0]}'\n")

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
        "-vsync", "vfr", "-pix_fmt", "yuv420p", out_path,
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def build_captions(captions_dir, texts):
    os.makedirs(captions_dir, exist_ok=True)
    paths = []
    for i, text in enumerate(texts):
        path = os.path.join(captions_dir, f"caption_{i:02d}.txt")
        # bidi reorder each line separately - a bare newline isn't a valid paragraph
        # separator to feed through get_display() as a single unit.
        reordered = "\n".join(rtl(line) for line in text.split("\n"))
        with open(path, "w", encoding="utf-8") as f:
            f.write(reordered)
        paths.append(path)
    return paths


def mux_video(raw_video_path, caption_paths, scene_starts, video_duration,
               narration_paths, output_path):
    scene_ends = scene_starts[1:] + [video_duration]
    hebrew_font = font_path(family="hebrew")

    def quote(path):
        # Paths here are always our own tempfile-generated Linux paths (no quotes/colons),
        # so simple single-quoting is enough to protect them inside the filtergraph.
        return "'" + path.replace("'", "'\\''") + "'"

    drawtext_filters = []
    for cap_path, start, end in zip(caption_paths, scene_starts, scene_ends):
        drawtext_filters.append(
            "drawtext=fontfile={font}:textfile={text}:reload=0:"
            "fontcolor=white:fontsize=20:line_spacing=6:text_align=center:"
            "box=1:boxcolor=black@0.55:boxborderw=14:"
            "x=(w-text_w)/2:y=h-th-46:"
            "enable='between(t,{start:.2f},{end:.2f})'"
            .format(font=quote(hebrew_font), text=quote(cap_path), start=start, end=end)
        )
    video_filter = "[0:v]" + ",".join(drawtext_filters) + "[vout]"

    cmd = ["ffmpeg", "-y", "-i", raw_video_path]

    if narration_paths:
        for p in narration_paths:
            cmd += ["-i", p]
        audio_parts = []
        for i, start in enumerate(scene_starts):
            delay_ms = max(0, int(start * 1000))
            audio_parts.append(f"[{i + 1}:a]adelay={delay_ms}|{delay_ms}[a{i}]")
        mix_inputs = "".join(f"[a{i}]" for i in range(len(narration_paths)))
        audio_filter = (
            ";".join(audio_parts)
            + f";{mix_inputs}amix=inputs={len(narration_paths)}:duration=first:dropout_transition=0"
            + f",apad=whole_dur={video_duration:.2f}[aout]"
        )
        filter_complex = video_filter + ";" + audio_filter
        cmd += [
            "-filter_complex", filter_complex,
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart",
            "-t", f"{video_duration:.2f}",
            output_path,
        ]
    else:
        cmd += [
            "-filter_complex", video_filter,
            "-map", "[vout]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output_path,
        ]

    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=os.path.join(HERE, "output", "invoice_app_demo.mp4"))
    parser.add_argument("--no-narration", action="store_true")
    parser.add_argument("--voice", default=narration_mod.DEFAULT_VOICE)
    parser.add_argument("--keep-tmp", action="store_true")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    tmp_dir = tempfile.mkdtemp(prefix="invoice_demo_")
    db_path = os.path.join(tmp_dir, "demo.db")
    frames_dir = os.path.join(tmp_dir, "frames")

    log(f"working dir: {tmp_dir}")

    narration_paths = None
    if not args.no_narration:
        log("synthesizing Hebrew narration (edge-tts)...")
        narration_lines = [s["narration"] for s in SCENES]
        narration_paths = narration_mod.synthesize_all(narration_lines, os.path.join(tmp_dir, "narration"), args.voice)
        if narration_paths:
            log(f"narration ready: {len(narration_paths)} clip(s)")

    log("generating sample invoice image...")
    invoice_path = os.path.join(tmp_dir, "sample_invoice.png")
    sample_invoice.generate(invoice_path, reason=DEMO_REASON, amount=DEMO_AMOUNT)

    env = os.environ.copy()
    env["DB_PATH"] = db_path
    env["DEMO_PORT"] = str(DEMO_PORT)
    log("starting app server...")
    server = subprocess.Popen(
        [sys.executable, os.path.join(HERE, "server_entry.py")],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        if not wait_for_server(DEMO_PORT):
            raise RuntimeError("app server did not start in time")

        log("recording browser session...")
        from playwright.sync_api import sync_playwright

        chromium_exe = os.path.join(
            os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"),
            "chromium-1194", "chrome-linux", "chrome",
        )
        launch_kwargs = {"executable_path": chromium_exe} if os.path.isfile(chromium_exe) else {}

        with sync_playwright() as p:
            browser = p.chromium.launch(**launch_kwargs)
            context = browser.new_context(viewport=VIEWPORT)
            page = context.new_page()
            page.goto(f"http://127.0.0.1:{DEMO_PORT}/", wait_until="networkidle")
            recorder = Recorder(page, frames_dir)
            recorder.sample()
            scene_starts = run_scenario(recorder, invoice_path)
            context.close()
            browser.close()

        log(f"captured {len(recorder.frames)} frames, assembling raw video...")
        raw_video = os.path.join(tmp_dir, "raw.mp4")
        assemble_raw_video(recorder.frames, raw_video)
        video_duration = probe_duration(raw_video)
        log(f"recording captured: {video_duration:.1f}s")

        log("building captions...")
        caption_lines = [s["caption"] for s in SCENES]
        caption_paths = build_captions(os.path.join(tmp_dir, "captions"), caption_lines)

        log("compositing final video with ffmpeg...")
        mux_video(raw_video, caption_paths, scene_starts, video_duration, narration_paths, args.output)

    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
        if not args.keep_tmp:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        else:
            log(f"kept temp dir: {tmp_dir}")

    log(f"done -> {args.output}")


if __name__ == "__main__":
    main()
