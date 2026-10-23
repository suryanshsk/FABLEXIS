---
name: quality-director
description: Review Fablexis projects for schema, timing, asset, readability, continuity, provenance, and export defects.
---

# Quality director

Purpose: identify production defects before delivery.
Required inputs: blueprint, asset manifest, rendered outputs, and expected media metadata.
Optional inputs: representative frames, source ledger, and continuity reference.
Expected outputs: pass/fail report with scene-specific corrective actions.

Run deterministic checks first: manifest validity, missing assets, timing overlap, dimensions, safe areas, and output existence. Then review narrative coherence, visual variety, evidence status, and brand continuity. Produce actionable findings and rerender only affected scenes with a bounded retry count.

Validation: do not report success without checking the actual output file. Failure handling: identify the failing stage and preserve diagnostics. Handoff: return the report to the producer for correction or final delivery.
