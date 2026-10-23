# Optional providers

Fablexis does not require an AI provider. Configure provider adapters through environment variables or a future adapter implementation; never place keys in a brief or commit them.

Provider-dependent work must record:

- provider and model
- request status
- source or generation metadata
- license/provenance where known
- local fallback

When a provider is not configured, use supplied assets and deterministic graphics. Do not send assets over the network implicitly.
