---
name: fablexis
description: "Use when turning an idea, script, facts, local assets, source footage, or a reference video into a Fablexis production plan, validated blueprint, preview, QA report, or locally rendered MP4."
---

# Fablexis shared production skill

Fablexis is a local, deterministic video-production engine with reusable
agent instructions. Use this shared skill from an agent that can read the
repository and execute approved local commands. It is not a hosted Fablexis
service and does not grant filesystem or shell permissions by itself.

## Required boundaries

- Work from the repository root containing `pyproject.toml`.
- Keep source assets and generated outputs inside the permitted project
  directory.
- Never put credentials in briefs, blueprints, reports, or skill files.
- Preserve user-supplied facts and label assumptions; offline planning is not
  live research.
- Do not claim a render succeeded until the output exists and FFprobe verifies
  it.
- Do not invent audio, narration, external-provider, reference-analysis, or
  raw-footage capabilities that the current engine has not executed.

## Production workflow

1. Read the user's idea or script and identify audience, purpose, duration,
   aspect ratio, factual claims, assumptions, and requested visual language.
2. Inspect project-local assets without leaving the project boundary.
3. Create or update a project:

   ```text
   fablexis create --idea "<idea>" --project <project>
   fablexis create --script <script> --project <project>
   ```

4. Read `<project>/production-report.json` and record each stage's status,
   provider mode, outputs, warnings, and limitations.
5. Validate the generated blueprint:

   ```text
   fablexis validate <project>/blueprint.json
   fablexis preview <project>
   fablexis qa <project>
   ```

6. If FFmpeg is available, export with `fablexis export <project>`.
7. Verify the reported output with FFprobe. Confirm file existence, nonzero
   size, codec, dimensions, frame rate, duration, pixel format, and audio
   stream presence or absence.
8. Report what was actually executed, what was skipped, and what remains
   unsupported. Preserve the editable blueprint and reports.

Use `python -m engine.cli` when the console entry point is unavailable. The
legacy `motionforge` command and `motionforge.mp4` output remain compatible
aliases.

## Current capability boundary

Implemented and tested:

- Deterministic offline idea/script planning.
- Versioned blueprint validation.
- Scene-specific graphics, typography, charts, diagrams, maps, and timing.
- Project-local PNG, JPEG, transparent PNG, and safe SVG compositing.
- Preview generation, frame QA, and FFmpeg H.264 export.
- Local video metadata, representative-frame, estimated-cut, shot-index, and
  contact-sheet analysis through `fablexis analyze-video`.
- Sequential multi-clip timeline rendering with source trims, explicit gaps,
  normalization, and verified H.264 output through `fablexis render-timeline`.

Not implemented by this shared workflow:

- Reference-video style analysis beyond deterministic media metadata and
  estimated visual cuts.
- Semantic shot selection or content recognition.
- Overlay/caption compositing and transitions beyond hard cuts.
- Audio mixing, narration, subtitles, or voice generation.
- External research, image, video, or generative-media providers.

If a user requests an unsupported capability, create the supported planning
artifacts where useful and state the exact blocker instead of simulating it.

For local video analysis:

```text
fablexis analyze-video input.mp4 --output analysis/input --interval 5 --max-frames 24
```

Read `analysis-report.json` for metadata, sampling timestamps, estimated shot
boundaries, relative thumbnail paths, contact sheets, and warnings. Review the
contact sheets before making creative claims. FFmpeg and FFprobe are required;
missing tools, corrupt media, and unreadable frames are reported as failures.

For a validated timeline, render sequential clips with:

```text
fablexis render-timeline timeline.json --project-root <project> --output output.mp4
```

The command also accepts the `editing-plan.json` wrapper written by
`edit-plan`. It sorts clips by `timeline_start_seconds`; each source trim must
match the explicit timeline duration and fit within the source. Gaps remain at
their specified positions as black video. When any unmuted source clip has
audio, clips without audio and gaps are filled with silence; otherwise the
output has no audio stream. `"mute": true` silences that clip. No narration,
music, sound effects, or standalone audio-track mixing is generated.

Only one video track is rendered. Overlaps, transitions other than hard cuts,
non-empty standalone audio tracks, overlays, and captions fail explicitly
rather than being silently dropped. Scaling letterboxes/pillarboxes the
complete source frame (no crop). Output is H.264/libx264, AAC when audio is
present, `yuv420p`, and constant-frame-rate; even project dimensions are
required. CRF defaults to 18 and accepts 0–51. FFmpeg and FFprobe are required.
The output is finalized only after FFprobe checks the MP4, streams, codecs,
dimensions, rate, pixel format, duration, and audio synchronization, and
representative frames decode successfully. If rendering fails, confirm both
tools are on PATH, the source paths remain inside the project root, trim points
fit the media, and the FFmpeg build includes libx264/AAC.

## Host integration

This file is the canonical shared workflow. Host adapters should remain thin:

- Gemini CLI and Codex: discover this `.agents/skills/fablexis/SKILL.md` file
  through their supported workspace skill mechanism, then invoke the local
  CLI only when command execution is available.
- Claude Code: use `.claude/skills/fablexis/SKILL.md`, which points back to
  this canonical file.
- VS Code-style agents: use
  `.github/agents/fablexis-video-producer.agent.md`.

Host discovery and command execution are separate capabilities. A browser chat
or an agent without local tool access can prepare files but cannot claim to
have rendered or inspected a video.
