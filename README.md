# Fablexis

**Tell your AI what to create. Fablexis brings it to life.**

Fablexis is an open-source, AI-agent-installable video-production skill pack backed by a local rendering engine. It turns a rough idea, outline, script, facts, or references into an original editorial motion-graphics project. It combines autonomous creative direction, a versioned project manifest, deterministic storyboard rendering, quality checks, and an optional FFmpeg export path.

It is inspired by the broad conventions of premium documentary explainers, paper-cut collage, kinetic typography, data visualization, and cinematic 2.5D motion. It does not copy any publisher's branding, assets, layouts, or distinctive frames.

## What it produces

- A fact-aware story analysis with explicit assumptions and evidence status.
- A global visual system with palette, typography, texture, and motion rules.
- Purposeful scenes with narration, timing, composition, animation, camera, transition, sound, and continuity notes.
- Self-contained Gemini-ready prompts for each scene.
- An editing and asset blueprint.
- A quality-control report.
- A validated `blueprint.json` and a dependency-free storyboard preview (`storyboard.svg` and `storyboard.html`).
- A project workflow with `init`, `doctor`, `brief`, `storyboard`, `preview`, `render`, `qa`, and `export` commands.
- A complete offline-first `create` pipeline with staged production reporting.

The local toolkit generates deterministic graphics and, when FFmpeg is available, a real H.264 MP4. External image/video generation and final editing remain optional production steps. Exact text, numbers, charts, and timestamps are rendered in code rather than trusted to an image model.

## Quick start

### Use as a Claude Skill

1. Download or clone this repository.
2. Install the repository's root [`SKILL.md`](./SKILL.md) and the `skills/` directory into the compatible agent environment's skill directory.
3. Give Claude a rough idea and any information you have. You do not need to complete a creative brief.
4. Choose `Quick Mode`, `Director Mode`, or `Production Mode` when you want a different level of detail.

Example:

> Why are Indian IPO investors obsessed with allotment? I have these facts: ...

Claude should preserve supplied wording, distinguish facts from assumptions, and ask only questions that materially change the result.

### Install the local engine

Requires Python 3.10 or newer and Pillow for raster compositing and anti-aliased typography.

```powershell
python -m pip install --upgrade pip setuptools
python -m pip install -e .
```

This installs the `fablexis` command. The legacy `motionforge` command remains available for existing scripts.

```powershell
fablexis init my-video
fablexis brief my-video\brief.md --project my-video
fablexis preview my-video
fablexis qa my-video
fablexis export my-video
```

Run the complete deterministic pipeline from an idea:

```powershell
fablexis create --idea "How AI agents turn goals into actions. Data reveals the loop. A diagram shows the system. Human judgment closes the story." --duration 15 --project my-video
```

Or start from a script:

```powershell
fablexis create --script script.md --duration 45 --aspect-ratio 16:9 --project my-video
```

The command produces `blueprint.json`, `storyboard.md`, `storyboard.svg`, `storyboard.html`,
`quality-report.json`, `production-report.json`, and (when FFmpeg is on `PATH`) `motionforge.mp4`.
The report records every stage, output path, provider mode, and unresolved limitation. Without a configured
provider, the report explicitly records the deterministic offline fallback; no API key or network access is needed.

`brief` writes `blueprint.json`, `storyboard.md`, and `quality-report.json`. `preview` and `render` write a storyboard preview. `export` uses FFmpeg when installed and reports the exact missing dependency otherwise. No paid AI provider is required for the local workflow.

### Install into an AI-agent workspace

Fablexis is a local skill pack, not a hosted service. In an agent environment that supports workspace skills, add this repository as a workspace skill source. Keep the repository available on the local filesystem so the agent can invoke:

```text
python -m engine.cli create --idea "<idea>" --project <project>
```

The agent should use the deterministic offline path unless the user explicitly configures an optional provider. API keys belong in environment variables, never in skill files, blueprints, or reports. The included `.github/agents/fablexis-video-producer.agent.md` provides a compatible custom-agent entry point for VS Code-style hosts.

Scene layers may reference project-local PNG, JPG/JPEG, or SVG files:

```json
{"type":"asset","asset":"assets/diagram.svg","x":48,"y":220,"width":444,"height":300,"fit":"contain","opacity":0.9,"z":2}
```

Assets are kept inside the project directory, validated before rendering, and rendered without network access. SVG support intentionally covers safe local vector shapes rather than external fonts, images, scripts, or URLs.

## Repository layout

```text
SKILL.md                         Claude skill entry point
skills/idea-to-video/            primary orchestration skill
skills/*/SKILL.md                focused specialist skills
references/                      Creative and production playbooks
examples/                        Input and complete output examples
engine/                          Dependency-free planner, validator, renderer, and CLI
tests/                           Unit tests for the local engine
validate.py                      Repository and blueprint validation
pyproject.toml                   Python package metadata and CLI entry point
```

## Pipeline architecture

The Fablexis local pipeline is composed of brief intake, script segmentation, research planning, narrative structure,
creative direction, asset planning, blueprint validation, storyboard generation, deterministic rendering, QA,
FFmpeg export, and production reporting. `engine/pipeline.py` owns orchestration; `engine/vox_motion.py`
owns blueprint and frame generation; `engine/providers.py` defines the provider boundary. The offline provider
is the only provider currently implemented and tested.

## Primary workflow

The `idea-to-video` skill orchestrates brief analysis, evidence tracking, story planning, visual direction, asset planning, animation, rendering, and quality checks. Stages report real progress and real failures. Optional providers are never required for deterministic graphics.

## Three operating modes

- **Quick Mode**: concise creative direction and one copy-ready prompt per scene.
- **Director Mode**: storyboard, timing, transitions, camera, sound, and continuity.
- **Production Mode**: all of the above plus asset manifest, compositing plan, research ledger, validation, and renderable local preview.

## Responsible use

Do not present invented statistics, citations, historical details, or generated visuals as verified fact. Add sources for consequential factual claims. When a tool cannot reliably render exact labels or numbers, create the visual without them and add precise overlays during compositing.

## Rendering limitations

The local renderer creates deterministic SVG/HTML previews and procedural frames with scene-specific kinetic type, editorial collage, paper-cut, chart, diagram, and map treatments. MP4 export uses the same deterministic frame path plus FFmpeg when it is on `PATH`; Fablexis never creates a fake success file when FFmpeg is missing. Image/video generation, voice generation, transcription, and research providers are intentionally optional and are not configured by default. Explicit local PNG, JPEG, and SVG asset paths are validated before export.

Check dependencies before rendering:

```powershell
python -m engine.cli doctor
```

On Windows, install FFmpeg from [ffmpeg.org/download.html](https://ffmpeg.org/download.html), add its `bin` directory to `PATH`, open a new PowerShell window, and verify `ffmpeg -version` plus `ffprobe -version`.

## License

MIT. See [`LICENSE`](./LICENSE).
