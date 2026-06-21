#!/usr/bin/env python3
"""Build the narrated, captioned TraffiSense.ai demo video.

This local ffmpeg bottle ships without libass/drawtext, so we render the
on-screen captions ourselves with Pillow (a WCAG-contrast caption bar) and let
ffmpeg only stitch stills + audio. Also emits a sidecar .srt for players that
prefer soft subtitles / screen readers.

Timing uses the *decoded* per-scene audio length (probed from the AAC), so the
captions stay perfectly in sync with the voiceover.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
SHOTS = HERE.parent / "docs" / "screenshots"
CAP_DIR = HERE / "captions"
OUT = HERE / "traffisense-demo.mp4"
SRT = HERE / "traffisense-demo.srt"
FONT_PATH = "/System/Library/Fonts/Helvetica.ttc"

W, H = 1920, 1080
BG = (11, 18, 32)  # 0x0b1220
N = 7
IMAGES = [
    "demo-01-dashboard.png", "demo-01-dashboard.png", "demo-02-forecast.png",
    "demo-03-resources.png", "demo-04-scenarios.png", "demo-05-assistant.png",
    "demo-06-insights.png",
]


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def probe(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nokey=1:noprint_wrappers=1", str(path)])
    return float(out.strip())


def ts(sec):
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_frame(base_img, text, font, out_path):
    """Scene screenshot scaled into 1920x1080 + a captioned bar at the bottom."""
    canvas = Image.new("RGB", (W, H), BG)
    img = Image.open(base_img).convert("RGB")
    scale = min(W / img.width, H / img.height)
    nw, nh = int(img.width * scale), int(img.height * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    canvas.paste(img, ((W - nw) // 2, (H - nh) // 2))

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    lines = wrap(od, text, font, max_w=W - 240)
    line_h = font.size + 12
    block_h = line_h * len(lines)
    pad = 26
    bar_top = H - block_h - pad * 2 - 48
    # Semi-opaque bar for contrast (WCAG: white on near-black ~ 17:1).
    od.rectangle([0, bar_top, W, bar_top + block_h + pad * 2],
                 fill=(8, 12, 20, 205))
    od.rectangle([0, bar_top, W, bar_top + 4], fill=(34, 211, 238, 255))  # accent
    y = bar_top + pad
    for ln in lines:
        tw = od.textlength(ln, font=font)
        x = (W - tw) / 2
        # subtle shadow then white text
        od.text((x + 2, y + 2), ln, font=font, fill=(0, 0, 0, 220))
        od.text((x, y), ln, font=font, fill=(255, 255, 255, 255))
        y += line_h
    Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB").save(out_path)


def main():
    font = ImageFont.truetype(FONT_PATH, 34)
    tmp = Path(tempfile.mkdtemp(prefix="ts_video_"))
    try:
        # 1) Voiceover -> accurate-duration AAC, per scene.
        durations, audio_parts = [], []
        for i in range(1, N + 1):
            aiff = HERE / f"scene{i}.aiff"
            if not aiff.exists():
                run(["say", "-v", "Samantha", "-r", "178", "-o", str(aiff),
                     "-f", str(HERE / f"scene{i}.txt")])
            m4a = tmp / f"a{i}.m4a"
            run(["ffmpeg", "-y", "-i", str(aiff), "-c:a", "aac", "-b:a", "192k", str(m4a)])
            durations.append(probe(m4a))
            audio_parts.append(m4a)

        # 2) Build the cue list with synced timings.
        cues, clock = [], 0.0
        for i in range(1, N + 1):
            lines = [l.strip() for l in
                     (CAP_DIR / f"scene{i}.txt").read_text().splitlines() if l.strip()]
            weights = [max(len(l), 1) for l in lines]
            tot = sum(weights)
            t = clock
            for l, w in zip(lines, weights):
                span = durations[i - 1] * w / tot
                cues.append({"scene": i, "text": l, "start": t, "dur": span})
                t += span
            clock += durations[i - 1]

        # 3) Render captioned frames + silent video segments.
        concat = tmp / "concat.txt"
        with concat.open("w") as cf:
            for idx, c in enumerate(cues):
                frame = tmp / f"f{idx:02d}.png"
                render_frame(SHOTS / IMAGES[c["scene"] - 1], c["text"], font, frame)
                seg = tmp / f"v{idx:02d}.mp4"
                run(["ffmpeg", "-y", "-loop", "1", "-i", str(frame), "-t",
                     f"{c['dur']:.3f}", "-r", "30", "-pix_fmt", "yuv420p",
                     "-c:v", "libx264", "-preset", "medium", str(seg)])
                cf.write(f"file '{seg}'\n")

        # 4) Concat video, concat audio, mux.
        visual = tmp / "visual.mp4"
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
             "-vf", "fade=t=in:st=0:d=0.6", "-c:v", "libx264", "-preset",
             "medium", "-pix_fmt", "yuv420p", str(visual)])
        aconcat = tmp / "aconcat.txt"
        aconcat.write_text("".join(f"file '{p}'\n" for p in audio_parts))
        full_audio = tmp / "audio.m4a"
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(aconcat),
             "-c:a", "aac", "-b:a", "192k", str(full_audio)])
        run(["ffmpeg", "-y", "-i", str(visual), "-i", str(full_audio),
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(OUT)])

        # 5) Sidecar SRT.
        srt = []
        for n, c in enumerate(cues, 1):
            srt.append(f"{n}\n{ts(c['start'])} --> "
                       f"{ts(c['start'] + c['dur'] - 0.05)}\n{c['text']}\n")
        SRT.write_text("\n".join(srt))

        print(f"Done -> {OUT.name} ({clock:.1f}s, {len(cues)} captions) + {SRT.name}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())