---
name: fablexis
description: "Use the canonical Fablexis shared skill for local video production."
---

# Fablexis Claude Code adapter

This is a thin Claude Code entry point. From the repository root, read and
follow the canonical shared skill at
`.agents/skills/fablexis/SKILL.md`.
Do not maintain a separate production workflow here.

The host must provide access to the repository and an approved local command
execution mechanism. Use `fablexis` or `python -m engine.cli`, inspect the
production report, and verify any MP4 with FFprobe before reporting success.
