#!/usr/bin/env bash
# Stitch frames + narration into an MP4.  usage: assemble.sh <workdir from record.mjs> <output.mp4>
set -euo pipefail
W="$1"; OUT="$2"
command -v ffmpeg >/dev/null || { echo "ffmpeg not found (brew install ffmpeg)"; exit 1; }
FPS=$(python3 -c "import json;print(json.load(open('$W/timeline.json'))['fps'])")
rm -f "$W/audio/"*.wav "$W/audio/list.txt"
python3 - "$W" <<'EOF' | while read -r src frames lead idx; do
import json,sys
t=json.load(open(sys.argv[1]+'/timeline.json'))
for i,s in enumerate(t['scenes']): print(s['audio'], s['frames'], s['lead'], f"{i:02d}")
EOF
  dur=$(python3 -c "print($frames/$FPS)"); ms=$(python3 -c "print(int($lead*1000))")
  # pad each scene's narration to exactly its video length so audio never drifts
  ffmpeg -nostdin -loglevel error -y -i "$src" -af "aresample=48000,adelay=${ms}:all=1,apad" -t "$dur" -ac 2 "$W/audio/$idx.wav"
  echo "file '$W/audio/$idx.wav'" >> "$W/audio/list.txt"
done
ffmpeg -nostdin -loglevel error -y -f concat -safe 0 -i "$W/audio/list.txt" -c copy "$W/narration.wav"
ffmpeg -nostdin -loglevel error -y -framerate "$FPS" -i "$W/frames/%06d.jpg" -i "$W/narration.wav" \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -vf "scale=1920:-2:flags=lanczos" -r "$FPS" \
  -c:a aac -b:a 160k -af "loudnorm=I=-16:TP=-1.5" -shortest -movflags +faststart "$OUT"
ffprobe -v error -show_entries format=duration,size -of default=nw=1 "$OUT"
