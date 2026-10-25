# Quick start

This walkthrough renders two locally generated synthetic clips. It uses the
Fablexis CLI directly; it does not test natural-language agent invocation and
does not require an AI provider, API key, or external media service.

## Install

From the Fablexis repository root in Windows PowerShell:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools
python -m pip install -e .
fablexis doctor
```

Install FFmpeg and FFprobe separately if `doctor` reports either missing. See
the [README prerequisites](../README.md#ffmpeg-installation).

## Create and render a sample timeline

All fixtures, reports, and outputs stay inside ignored `out\quickstart-demo`.
The sample uses red then blue video so frame order is straightforward to check.

```powershell
$root = ".\out\quickstart-demo"
$input = Join-Path $root "input"
New-Item -ItemType Directory -Force -Path $input | Out-Null

ffmpeg -y -nostdin -hide_banner -loglevel error `
  -f lavfi -i "color=c=red:s=360x640:r=10:d=4" `
  -c:v libx264 -pix_fmt yuv420p (Join-Path $input "01-red.mp4")
ffmpeg -y -nostdin -hide_banner -loglevel error `
  -f lavfi -i "color=c=blue:s=360x640:r=10:d=4" `
  -c:v libx264 -pix_fmt yuv420p (Join-Path $input "02-blue.mp4")
ffmpeg -y -nostdin -hide_banner -loglevel error `
  -f lavfi -i "color=c=white:s=360x640:r=10:d=8" `
  -c:v libx264 -pix_fmt yuv420p (Join-Path $input "reference.mp4")

fablexis analyze-video (Join-Path $input "01-red.mp4") `
  --output (Join-Path $root "analysis\red") --interval 1 --max-frames 4
fablexis analyze-video (Join-Path $input "02-blue.mp4") `
  --output (Join-Path $root "analysis\blue") --interval 1 --max-frames 4
fablexis analyze-reference (Join-Path $input "reference.mp4") `
  --output (Join-Path $root "analysis\reference") --interval 1 --max-frames 4
fablexis edit-plan `
  --reference (Join-Path $input "reference.mp4") `
  --footage (Join-Path $input "01-red.mp4") (Join-Path $input "02-blue.mp4") `
  --duration 8 --width 360 --height 640 --output (Join-Path $root "plan")
fablexis validate-timeline (Join-Path $root "plan\editing-plan.json")
fablexis render-timeline (Join-Path $root "plan\editing-plan.json") `
  --project-root $input --output (Join-Path $root "rendered.mp4") --crf 18
fablexis verify-output (Join-Path $root "rendered.mp4")
ffprobe -v error -show_entries "format=duration,size:stream=codec_name,codec_type,width,height,avg_frame_rate,pix_fmt" `
  -of json (Join-Path $root "rendered.mp4")
```

The edit plan uses deterministic metadata and visual measurements; it does not
understand the semantic contents of real footage. For this synthetic sample,
the intended result is an 8-second, 360×640 H.264 video at 10 fps, with red
before blue and no audio stream. Inspect the generated quality report and
extract representative frames if verifying color/order:

```powershell
ffmpeg -y -nostdin -hide_banner -loglevel error -ss 1 -i (Join-Path $root "rendered.mp4") `
  -frames:v 1 (Join-Path $root "frame-red.png")
ffmpeg -y -nostdin -hide_banner -loglevel error -ss 6 -i (Join-Path $root "rendered.mp4") `
  -frames:v 1 (Join-Path $root "frame-blue.png")
```

## Agent-assisted production

Open the repository itself as a trusted workspace in a compatible agent, then
confirm that it discovers `.agents/skills/fablexis/SKILL.md` or the relevant
host adapter. Give the agent a brief naming the local source clips, intended
order, duration, aspect ratio, and any audio policy. Require it to report
whether the host actually invoked Fablexis and to include the final
`verify-output` and FFprobe evidence.

Host-specific setup and the known verification status are in
[agent integrations](./agent-integrations.md). A usable language model is
required for the agent to interpret a natural-language request, but the local
Fablexis renderer does not require one.
