"""Best-effort Hebrew narration via edge-tts. Synthesis needs outbound network access
(a WebSocket connection to Microsoft's TTS service) - if that's unavailable or blocked
by a network policy, callers should fall back to a silent, caption-only video.
"""
import asyncio
import os

DEFAULT_VOICE = "he-IL-AvriNeural"


async def _synth_one(text, out_path, voice):
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)


def synthesize_all(lines, out_dir, voice=DEFAULT_VOICE):
    """Synthesizes each line to its own mp3 in out_dir. Returns a list of file paths in
    the same order as `lines`, or None if narration synthesis isn't available right now.
    """
    os.makedirs(out_dir, exist_ok=True)
    paths = [os.path.join(out_dir, f"line_{i:02d}.mp3") for i in range(len(lines))]

    async def _run():
        for text, path in zip(lines, paths):
            await _synth_one(text, path, voice)

    try:
        asyncio.run(_run())
    except Exception as exc:
        print(f"[narration] TTS synthesis unavailable ({exc.__class__.__name__}: {exc}); "
              f"continuing with captions only, no voiceover.")
        return None

    for p in paths:
        if not os.path.isfile(p) or os.path.getsize(p) == 0:
            print("[narration] TTS produced an empty file; continuing without voiceover.")
            return None
    return paths
