# Optional providers

Fablexis does not require an AI provider. The current engine ships with a deterministic offline creative provider and does not implement hosted provider adapters. Environment variables do not activate providers.

Provider-dependent work must record:

- provider and model
- request status
- source or generation metadata
- license/provenance where known
- local fallback

Use supplied local assets and deterministic graphics. Do not send assets over the network implicitly. Local video analysis, reference measurements, timeline planning, and FFmpeg rendering do not require an AI provider.
