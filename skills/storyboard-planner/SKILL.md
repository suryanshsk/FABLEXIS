---
name: storyboard-planner
description: Convert a Fablexis narrative into versioned, timed scenes with composition, motion, assets, transitions, and source provenance.
---

# Fablexis storyboard planner

Purpose: convert directed narrative beats into stable, independently revisable scene records.

Inputs: narrative structure and creative direction.
Outputs: timed storyboard, scene IDs, layer plan, asset references, and source provenance.

Every scene needs a stable ID, duration, narration, narrative purpose, focal point, composition, animation beats, transition, text, sound cue, asset references, source references, and validation requirements. Label estimated timing. Support scene-level revision without changing unrelated scene IDs.

Handoff: pass the storyboard to blueprint generation. Reject overlapping or non-positive scene timing.
