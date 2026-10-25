# Capability boundaries and roadmap

Fablexis should report what the current local implementation actually did.
An agent may plan unsupported creative requests, but must mark unsupported
operations instead of implying that they were rendered.

## Implemented

- Deterministic offline idea/script-to-motion-graphics planning.
- Versioned blueprint and timeline validation.
- Local SVG/HTML previews, deterministic graphics and asset compositing for
  the documented PNG/JPEG/safe-SVG subset.
- FFmpeg H.264 export and post-export metadata/frame-decode checks.
- Local video metadata, sampled frames, estimated cuts, and contact sheets.
- Deterministic reference measurements and non-semantic edit-plan generation.
- One-track sequential video rendering with source trims, explicit black gaps,
  normalization, optional source audio attached to video clips, and output
  verification.

## Not implemented or not verified

- Semantic object/person/action recognition or semantic shot selection.
- Automatic natural-language editing through a verified Gemini, Codex, or
  Claude host in the recorded acceptance environment.
- Overlapping clips, transitions other than hard cuts, or multi-track video.
- Standalone audio tracks, audio mixing, gain automation, narration, music, or
  sound-effect generation.
- Overlay compositing and caption/subtitle rendering in the multi-clip
  timeline renderer.
- Automated semantic or artistic review of the exported video.
- Hosted research or image/video/audio generation providers.
- Tested cross-platform packaging/install behavior beyond the checks listed in
  the acceptance report.
- A wheel-based or source-distribution installation that also places the
  Gemini/Codex/Claude skill files into an agent workspace. Current package
  artifacts contain the Python engine and CLI only; use a repository checkout
  for agent skill discovery.

## Prioritized follow-up

1. **Host-level invocation tests:** obtain approved, supported model access or
   install each host independently; prove discovery and invocation separately.
2. **Release packaging:** clean wheel and source-distribution CLI installs
   pass, but decide how host skill files should be distributed outside a
   repository checkout.
3. **Audio controls:** add an explicit schema-level audio-track contract and
   tested mixing behavior before exposing standalone audio or volume options.
4. **Overlays and captions:** define timing, asset, font, and layout semantics
   in the schema, then implement deterministic compositing and regression
   fixtures.
5. **Transitions and overlaps:** define overlap semantics and audio/video
   synchronization before supporting them; do not silently reinterpret cuts.
6. **Visual review:** provide a human review flow or separately validated
   visual evaluator; current technical frame decoding is not semantic QA.
7. **Platform matrix:** add clean install/render checks on Windows and macOS
   alongside the existing Linux Python 3.10–3.12 CI.

This list is a roadmap, not a claim that the listed work is in progress.
