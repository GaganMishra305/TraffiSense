#!/usr/bin/env bash
# Assemble the narrated TraffiSense.ai demo video from scene stills + AI
# voiceover. Each scene is held for exactly the length of its narration, then
# all scenes are concatenated. Requires ffmpeg + the scene*.aiff files.
set -euo pipefail
cd "$(dirname "$0")"

SHOTS_DIR="../docs/screenshots"
BG="0x0b1220"
OUT="traffisense-demo.mp4"

# scene -> screenshot mapping
declare -a IMAGES=(
  "$SHOTS_DIR/demo-01-dashboard.png"   # 1 intro
  "$SHOTS_DIR/demo-01-dashboard.png"   # 2 build event
  "$SHOTS_DIR/demo-02-forecast.png"    # 3 forecast
  "$SHOTS_DIR/demo-03-resources.png"   # 4 resources
  "$SHOTS_DIR/demo-04-scenarios.png"   # 5 scenarios
  "$SHOTS_DIR/demo-05-assistant.png"   # 6 assistant
  "$SHOTS_DIR/demo-06-insights.png"    # 7 insights + ML + close
)

VF="scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=${BG},setsar=1,fps=30"

# Regenerate the AI voiceover from the scene scripts if missing.
for i in 1 2 3 4 5 6 7; do
  if [ ! -f "scene$i.aiff" ]; then
    echo "Generating voiceover scene$i.aiff"
    say -v Samantha -r 178 -o "scene$i.aiff" -f "scene$i.txt"
  fi
done

rm -f segment*.mp4 concat.txt
for i in 1 2 3 4 5 6 7; do
  img="${IMAGES[$((i-1))]}"
  echo "Building segment $i from $(basename "$img")"
  ffmpeg -y -loglevel error -loop 1 -i "$img" -i "scene$i.aiff" \
    -c:v libx264 -preset medium -pix_fmt yuv420p -vf "$VF" \
    -c:a aac -b:a 192k -shortest "segment$i.mp4"
  echo "file 'segment$i.mp4'" >> concat.txt
done

echo "Concatenating..."
ffmpeg -y -loglevel error -f concat -safe 0 -i concat.txt \
  -vf "fade=t=in:st=0:d=0.6" -c:v libx264 -preset medium -pix_fmt yuv420p \
  -c:a aac -b:a 192k "$OUT"

rm -f segment*.mp4 concat.txt
echo "Done -> media/$OUT"
ffprobe -v error -show_entries format=duration -of default=nokey=1:noprint_wrappers=1 "$OUT"
