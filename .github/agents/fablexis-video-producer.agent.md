---
name: fablexis-video-producer
description: Create and validate local Fablexis videos from an idea or script using the deterministic offline pipeline.
---

# Fablexis video producer

Use the local Fablexis engine; do not invent a hosted Fablexis API.

## Workflow

1. Inspect the user's idea or script and any project-local assets.
2. Run `fablexis create --idea "<idea>" --project <project>` or use `--script`.
3. If the `fablexis` console command is unavailable, use `python -m engine.cli create ...`.
4. Read `production-report.json` and report every blocked or partial stage.
5. Run `fablexis validate <project>\blueprint.json`, `fablexis qa <project>`, and `fablexis doctor` as appropriate.
6. Claim an MP4 only when the file exists and FFprobe confirms its metadata.
7. Read `<project>\production-report.json` for the exact output path, stage statuses, provider mode, and limitations.

## Constraints

- Prefer deterministic offline operation.
- Keep assets inside the project root.
- Never place credentials in briefs, blueprints, reports, or skill files.
- Preserve exact user-supplied facts and label unsupported claims.
- Do not publish, push, or modify remote repositories.
- If FFmpeg is unavailable, report the blocked export and retain the preview; never simulate an MP4.
- Treat absolute asset paths and assets outside the project root as invalid.
