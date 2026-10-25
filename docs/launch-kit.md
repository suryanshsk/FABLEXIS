# Fablexis launch kit — draft, not approved for publication

All copy below describes the verified local engine and explicitly marks host
integration as incomplete. Do not post under a user's identity without their
approval.

## Repository description

> Open-source, local-first video production engine: turn a brief and local
> footage into validated plans, deterministic graphics, and verified MP4s.
> Agent skill integrations are experimental and host-dependent.

## Suggested GitHub topics

`video-editing`, `ffmpeg`, `python`, `ai-agents`, `agent-skills`,
`local-first`, `motion-graphics`, `video-production`, `open-source`

## X draft

> Meet Fablexis: an open-source, local-first video production engine.
>
> It turns a validated timeline into an MP4 with FFmpeg, checks the result
> with FFprobe, and keeps rendering independent of hosted AI providers.
>
> Multi-clip cuts, trims, gaps, and technical verification work today. Audio
> mixing, captions, overlays, and transitions are still on the roadmap.
>
> Agent skill discovery has been verified for Gemini CLI in a trusted
> workspace; model-driven execution remains blocked/unverified in our current
> environment. Try the local CLI and help us test more hosts: [repository URL]

## LinkedIn draft

> We are building Fablexis, an open-source, local-first video production
> engine designed to connect natural-language AI agents with real, verifiable
> video workflows.
>
> Today the local engine supports deterministic motion-graphics projects,
> footage/reference measurements, validated sequential multi-clip timelines,
> FFmpeg rendering, and FFprobe-based output checks. A reproducible demo uses
> two local clips and verifies their order in the exported MP4.
>
> We are careful not to overstate agent compatibility: Gemini CLI discovered
> the project skill in a trusted workspace, but model execution was blocked
> by the available account/client. Codex and Claude Code still need separate
> acceptance tests. Audio mixing, captions, overlays, and non-cut transitions
> are not yet implemented in the multi-clip renderer.
>
> If you build with local media tools or agent skills, we would value
> installation feedback, issue reports, and contributions: [repository URL]

## Reddit / developer community draft

> **Show-and-tell: Fablexis, a local-first FFmpeg video workflow with an
> agent-skill interface**
>
> I am working on Fablexis, an MIT-licensed Python project that validates
> editing plans and renders local footage with FFmpeg. The current supported
> timeline is intentionally narrow: sequential clips, trims, explicit black
> gaps, source audio when present, and H.264 output checked with FFprobe.
>
> It does not yet mix music/voiceover, render captions/overlays, support
> transitions beyond cuts, or semantically understand footage. Gemini CLI
> skill discovery passed with workspace trust, but its model request could
> not run in my current account environment; other agent hosts are unverified.
>
> Reproducible local demo and limitations: [repository URL]. I would especially
> appreciate feedback on installation and what to prioritize next.

Before posting, read the selected community's self-promotion, project
announcement, and AI-content rules. Adapt the post to the community and disclose
your relationship to the project.

## AI developer community draft

> Fablexis explores a practical boundary between agent reasoning and local
> media execution: an agent can produce a validated editing plan, while the
> local Python/FFmpeg engine handles deterministic rendering and output QA.
>
> The renderer is usable without a hosted AI provider. We have verified a
> two-clip synthetic render, timeline validation, FFprobe metadata, and
> representative frame order. Skill discovery is host-dependent: Gemini CLI
> discovery passed in a trusted workspace, but model invocation was blocked
> by account eligibility. Codex and Claude Code are not yet verified.
>
> We welcome reproducible bug reports and contributions, especially clean
> installs, host-invocation tests, and carefully specified caption/audio
> workflows: [repository URL]

## 45-second demo video script and storyboard

| Time | Picture / screen action | Voiceover / on-screen text |
|---|---|---|
| 0–5s | Show two labeled local clips and the Fablexis repository. | “What if an AI agent could hand off a video edit to a local, verifiable renderer?” |
| 5–12s | Show install commands and `fablexis doctor`. | “Fablexis is an open-source Python and FFmpeg workflow. The renderer needs no AI API key.” |
| 12–22s | Show the red/blue two-clip timeline plan and validation output. | “Today it validates sequential cuts, trims, and explicit gaps. It rejects unsupported operations.” |
| 22–32s | Run render and `verify-output`; show FFprobe metadata. | “The MP4 is checked for codec, dimensions, frame rate, duration, audio policy, and decodable frames.” |
| 32–40s | Play red then blue sample; show limitations card. | “This is technical verification, not semantic visual review. Mixing, captions, overlays, and transitions remain future work.” |
| 40–45s | Show repository URL and contribution prompt. | “Try the reproducible demo, report what breaks, and help us test agent hosts.” |

Use only generated synthetic color clips in this screen recording unless
separate source-media rights are confirmed. Do not stage a false Gemini
invocation; label any direct CLI steps as direct CLI.

## Screen-recording and screenshot plan

1. Record the exact tested Python/FFmpeg versions and repository commit.
2. Show the README prerequisites and quick-start commands.
3. Show real Gemini skill discovery only if rerunning it live; visibly note
   workspace trust and that discovery is not model-driven rendering.
4. Show the local CLI workflow separately from any agent-host demonstration.
5. Keep the terminal readable; show timeline validation and the output path.
6. Show `verify-output`, FFprobe JSON, and red/blue representative frames.
7. End with a limitations card and repository URL.

Suggested screenshots: `doctor` output, timeline validation, a contact sheet
of synthetic source clips, the FFprobe summary, and red/blue output frames.
Suggested GIF: a short, silent loop switching between the validated timeline,
rendered red frame, and rendered blue frame. Ensure the GIF is generated from
the ignored acceptance output and does not imply untested agent execution.

## Call to action

> Try the reproducible local demo, open an issue with your OS/Python/FFmpeg
> versions and exact command output, and contribute a test before expanding
> renderer behavior. Agent-host reports should state discovery and invocation
> separately.

## Launch-day checklist

- [ ] Merge only after the reviewed PR's current CI is green.
- [ ] Confirm the released version and changelog agree.
- [ ] Build and install wheel and source distribution in clean environments.
- [ ] Re-run local render acceptance and inspect output frames.
- [ ] Confirm the release contains no generated media, credentials, caches, or
  local configuration.
- [ ] Review this copy for current facts and community policies.
- [ ] Obtain explicit approval before creating the GitHub release or posting.
