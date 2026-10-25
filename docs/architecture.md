# Fablexis architecture

Fablexis has three provider-independent layers:

1. **Skills** describe creative decisions and orchestration using progressive disclosure.
2. **Engine** turns a brief into a versioned JSON blueprint, validates it, and renders deterministic SVG/HTML previews and MP4 files.
3. **Optional integrations** are extension points only. No hosted research, image, video, audio, or transcription provider is enabled by default.

The blueprint is the source of truth for graphics production. Scene IDs and asset metadata allow a single scene or asset to be revised without rebuilding the whole project. FFmpeg and FFprobe are required for verified MP4 exports; no fake media is created when either is absent.

The footage workflow is separate from blueprint graphics:

1. `analyze-video` and `analyze-reference` use local FFmpeg/FFprobe inspection and deterministic visual measurements.
2. `edit-plan` emits the versioned timeline contract in `schemas/timeline.schema.json`.
3. `render-timeline` validates and renders one video track to H.264. It sorts clips by timeline start, honors source trims, preserves explicit gaps as black frames, normalizes frame rate and size, and preserves unmuted source audio when available.
4. The renderer rejects overlaps, non-cut transitions, standalone audio tracks, overlays, and captions. It verifies the temporary MP4 and decodes representative frames before replacing the destination.

Blueprint MP4 export similarly renders deterministic local frames to a temporary file, verifies the result, and replaces the destination only after checks pass. Neither pipeline fabricates audio. Automated frame decoding and gap checks are useful QA, not semantic or artistic review.
