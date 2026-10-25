# Changelog

Notable changes to Fablexis are documented here. This file does not imply a
release or publication.

## [0.3.0] - 2026-10-25

- Added deterministic local video analysis, reference-style measurements, and
  validated editing-plan timelines.
- Added FFmpeg multi-clip rendering with source trims, explicit black gaps,
  frame-rate and dimension normalization, conditional source audio, and
  verified atomic MP4 output.
- Added timeline validation and MP4 verification CLI commands, with quality
  reports for rendered outputs.
- Hardened deterministic blueprint export so failed encodes do not replace a
  prior output or report stale media as a successful export.
- Added FFmpeg-backed integration coverage and configured the CI matrix for
  Python 3.10-3.12.
- Documented unsupported timeline compositing, transitions, standalone audio,
  and hosted-provider functionality.

## Unreleased

No changes yet.
