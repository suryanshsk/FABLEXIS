# Fablexis architecture

Fablexis has three provider-independent layers:

1. **Skills** describe creative decisions and orchestration using progressive disclosure.
2. **Engine** turns a brief into a versioned JSON blueprint, validates it, and renders deterministic SVG/HTML previews.
3. **Optional integrations** can provide research, images, video, audio, or transcription. Their absence never blocks local planning.

The blueprint is the source of truth. Scene IDs and asset metadata allow a single scene or asset to be revised without rebuilding the whole project. FFmpeg is detected at export time; no fake media is created when it is absent.
