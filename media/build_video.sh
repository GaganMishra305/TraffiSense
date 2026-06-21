#!/usr/bin/env bash
# Build the narrated, captioned TraffiSense.ai demo video.
# Captions are rendered with Pillow (this ffmpeg bottle lacks libass/drawtext),
# then ffmpeg stitches stills + AI voiceover. Emits MP4 + sidecar SRT.
set -euo pipefail
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:$PATH"

# Use the project venv (Pillow lives there); fall back to system python3.
PY="../.venv/bin/python"
[ -x "$PY" ] || PY="python3"
exec "$PY" build_video.py
