---
name: idea-to-video
description: Primary Fablexis workflow that turns ordinary-language creative material into a validated, renderable motion-graphics project. Use when an AI agent must create a video from an idea or script.
---

# Fablexis idea to video

Purpose: turn a natural-language idea or script into a storyboard, validated blueprint, rendered preview, QA report, and optional MP4.

Required inputs: an idea or script.
Optional inputs: duration, aspect ratio, local assets, factual sources, and brand constraints.
Expected outputs: `blueprint.json`, storyboard files, quality/production reports, and `motionforge.mp4` when FFmpeg is available.

Use the shared project manifest rather than retyping creative decisions in prose. Infer safe defaults and keep the creator moving.

## Workflow

1. Inspect the brief and available assets without uploading anything externally.
2. Separate user claims, verified facts, estimates, assumptions, and creative illustrations.
3. Build the narrative arc and scene manifest.
4. Ask the visual-direction skill to choose purposeful variety.
5. Create the asset manifest and mark provider-dependent items.
6. Render deterministic graphics locally where possible.
7. Run quality checks and produce actionable corrections.
8. Export only when the configured renderer succeeds.
9. Hand the blueprint and production report to the rendering/export or quality stage.

## Fallbacks

Missing research, image, audio, or video providers must not block a local storyboard. Missing FFmpeg blocks MP4 export and must be reported, not simulated.

Validation: every scene needs timing, purpose, visual treatment, transition, and render metadata; local assets must remain inside the project root.
