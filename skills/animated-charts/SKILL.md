---
name: animated-charts
description: Turn supplied data into accurate, readable, deterministic Fablexis animated charts with source and unit tracking.
---

# Animated charts

Purpose: render exact, readable, deterministic data graphics.
Required inputs: values, units, labels, and source status.
Optional inputs: dates, comparison groups, brand palette, and target aspect ratio.
Expected outputs: chart type, axis/label plan, animation beats, and provenance notes.

Validate values, units, dates, currency, and source status before drawing. Use code-rendered labels and axes for exactness. Choose a chart type that answers the claim, animate one meaningful change at a time, and flag missing provenance instead of inventing it.

Validation: reject malformed or ambiguous values. Failure handling: produce a blocked data-visualization note instead of fabricated numbers. Handoff: send the chart plan to blueprint generation and rendering.
