# Troubleshooting

## MP4 export says FFmpeg is missing

On Windows, install FFmpeg from the official builds at https://ffmpeg.org/download.html, extract it, and add its `bin` directory (for example `C:\ffmpeg\bin`) to the user `PATH`. Open a new PowerShell window and run `ffmpeg -version` and `ffprobe -version` to verify both commands. Then run `python -m engine.cli export <project>`. `doctor` reports the detected executable and version. Previews remain available without FFmpeg.

## A blueprint fails validation

Run `python -m engine.cli qa <project>` and inspect `quality-report.json`. Timing overlaps, empty narration, and missing required fields are reported explicitly.

## External generation is unavailable

This is expected without provider configuration. Continue with deterministic SVG/HTML scenes and add generated media later through the asset manifest.
