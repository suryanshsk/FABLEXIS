# Troubleshooting

## MP4 export says FFmpeg is missing

On Windows, install FFmpeg from the official builds at https://ffmpeg.org/download.html, extract it, and add its `bin` directory (for example `C:\ffmpeg\bin`) to the user `PATH`. Open a new PowerShell window and run `ffmpeg -version` and `ffprobe -version` to verify both commands. Then run `python -m engine.cli export <project>`. `doctor` reports the detected executable and version. Previews remain available without FFmpeg or FFprobe.

## Timeline render fails

Run `fablexis validate-timeline <timeline.json>` first. Then check that every
source path resolves inside `--project-root`, source trim points fit the file,
and source duration matches the clip's explicit timeline duration. Only one
video track, hard cuts, and source audio attached to video clips are rendered.
Overlaps, standalone audio tracks, overlays, and captions are rejected.
Explicit gaps remain black rather than moving later clips earlier.

The FFmpeg build must include `libx264` and, when the timeline has audio, AAC.
Check the generated adjacent `.quality-report.json`; it includes stream
metadata, decoded representative-frame results, and black-gap checks. These
automated checks do not establish semantic or artistic correctness.

## An MP4 exists but quality assurance is partial

Run `fablexis verify-output <file.mp4>` with both FFmpeg and FFprobe installed.
The command checks media metadata and decodes representative frames. If the
export command failed, it will preserve an earlier output file; inspect the
production report and timestamps rather than assuming that an existing MP4 is
the result of the latest run.

## A blueprint fails validation

Run `python -m engine.cli qa <project>` and inspect `quality-report.json`. Timing overlaps, empty narration, and missing required fields are reported explicitly.

## External generation is unavailable

This is expected without provider configuration. Continue with deterministic SVG/HTML scenes and add generated media later through the asset manifest.
