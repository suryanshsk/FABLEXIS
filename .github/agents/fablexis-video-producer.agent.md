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
5. Run `fablexis validate`, `fablexis qa`, and `fablexis doctor` as appropriate.
6. Claim an MP4 only when the file exists and FFprobe confirms its metadata.

## Constraints

- Prefer deterministic offline operation.
- Keep assets inside the project root.
- Never place credentials in briefs, blueprints, reports, or skill files.
- Preserve exact user-supplied facts and label unsupported claims.
- Do not publish, push, or modify remote repositories.
