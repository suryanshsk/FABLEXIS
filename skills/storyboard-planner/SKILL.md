---
name: storyboard-planner
description: Convert a Fablexis narrative into versioned, timed scenes with composition, motion, assets, transitions, and source provenance.
---

# Fablexis storyboard planner

Purpose: convert directed narrative beats into stable, independently revisable scene records.

Required inputs: narrative structure and creative direction.
Optional inputs: timestamped narration, asset manifest, source ledger, and platform constraints.
Expected outputs: timed storyboard, scene IDs, layer plan, asset references, and source provenance.
Validation: reject overlapping or non-positive scene timing and unresolved required asset paths.
Failure handling: retain stable scene IDs and report the exact invalid scene rather than rewriting unrelated scenes.
Handoff: pass the storyboard to blueprint generation and the asset planner.

Every scene needs a stable ID, duration, narration, narrative purpose, focal point, composition, animation beats, transition, text, sound cue, asset references, source references, and validation requirements. Label estimated timing. Support scene-level revision without changing unrelated scene IDs.

Reject overlapping or non-positive scene timing.
