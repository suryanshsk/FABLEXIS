# Fablexis — Open-Source, AI-Agent-Powered Video Production

<p align="center">
  <strong>Tell your AI what to create. Fablexis brings it to life.</strong>
</p>

<p align="center">
  Turn ideas, scripts, and local footage into structured video projects, motion graphics, storyboards, and verified MP4 exports — using AI agents and a deterministic local rendering engine.
</p>

<p align="center">
  <a href="https://github.com/suryanshsk/FABLEXIS">GitHub Repository</a> ·
  <a href="https://github.com/suryanshsk/FABLEXIS/releases/tag/v0.3.0">Latest Release: v0.3.0</a> ·
  <a href="https://github.com/suryanshsk/FABLEXIS/issues">Report a Bug</a> ·
  <a href="https://github.com/suryanshsk/FABLEXIS/blob/main/LICENSE">MIT License</a>
</p>

---

## What is Fablexis?

**Fablexis is an open-source, local-first video production toolkit designed to work with AI coding agents.**

Describe the video you want to make. An AI agent that can access your project and execute approved local commands can use Fablexis to plan the production, create structured project files, generate previews, run quality checks, and render an MP4 through the local engine.

Instead of treating a video as one opaque AI-generated output, Fablexis treats production as a structured, inspectable workflow.

```text
Your idea, script, or local footage
                 │
                 ▼
       AI agent + Fablexis skill
                 │
                 ▼
       Creative plan and storyboard
                 │
                 ▼
       Structured video blueprint
                 │
                 ▼
        Validation and local QA
                 │
                 ▼
       Deterministic rendering
                 │
                 ▼
           FFmpeg encoding
                 │
                 ▼
       MP4 verification and report
```

Fablexis is not a hosted video-generation SaaS, and it does not require a Fablexis account, subscription, or API key for its deterministic offline workflow.

The AI agent is the creative interface. Fablexis provides the structured production workflow and local rendering engine.

**Important:** An AI agent still needs its own usable model access, access to the repository, and permission to execute local commands. Fablexis does not bypass AI-provider authentication or subscription restrictions.

## Why does Fablexis exist?

Video production can involve much more than generating a few images or writing a script. A useful production workflow needs to coordinate narrative, timing, assets, composition, rendering, and output validation.

Common challenges include:

- **Fragmented workflows:** Ideas, scripts, storyboards, footage, timelines, and exports live in different tools.
- **Opaque outputs:** A finished video alone does not explain how it was assembled or how to reproduce it.
- **Cloud dependency:** Some workflows depend on hosted services, paid credits, or remote rendering.
- **Weak verification:** A successful command does not necessarily prove that an MP4 contains the expected streams, dimensions, duration, or decodable frames.
- **Limited reproducibility:** Recreating a result can be difficult when production decisions are not captured in structured files.
- **Agent execution gaps:** An AI can describe a video without actually creating and verifying the resulting media file.
- **Unclear editing requirements:** Local footage may need to be analyzed and organized before an editor can build a timeline.

Fablexis addresses these challenges with a local production engine, structured artifacts, validation, reproducible rendering steps, and explicit output checks.

It does not magically eliminate every editing task. Its purpose is to make the supported parts of video production more structured, automatable, and inspectable.

## What makes Fablexis different?

| Capability | Fablexis approach |
|---|---|
| Production interface | Natural-language requests through a compatible AI agent |
| Rendering | Local rendering and FFmpeg-based MP4 export |
| Project representation | Structured blueprints, timelines, and reports |
| Output validation | Metadata checks and representative frame decoding |
| Provider dependency | No AI provider required for the deterministic offline workflow |
| Ownership | Local project files and local media |
| Reproducibility | Explicit inputs, settings, structured plans, and reports |
| Agent integration | Reusable skill instructions and host-specific adapters |
| Cost model | No Fablexis subscription or mandatory hosted rendering service |
| Extensibility | Open-source code and an inspectable production workflow |

These are architectural distinctions, not a claim that Fablexis already replaces every professional editing application or supports every AI agent without configuration.

### Fablexis versus other video workflows

**Traditional video editors**

Traditional editors offer rich timelines, mature effects, and hands-on creative control. Fablexis instead focuses on an agent-operable, structured, local workflow. It can complement a conventional editor rather than replace it.

**Hosted AI video generators**

Hosted generators can create or transform media using their own models and infrastructure. Fablexis focuses on structured production and local rendering; it does not include a general-purpose text-to-video model in its default offline workflow.

**AI coding agents alone**

An AI agent can write scripts and describe production steps, but its actual capabilities depend on its tools, permissions, environment, and instructions. Fablexis provides a dedicated workflow, local CLI, schemas, renderer, and verification commands that the agent can use.

**Manual FFmpeg scripts**

FFmpeg is a powerful media-processing foundation. Fablexis adds a higher-level project workflow, blueprint and timeline validation, production artifacts, and output QA around supported rendering operations.

**Other agent skills**

A skill generally provides instructions for an agent. Fablexis combines reusable agent instructions with an actual local production engine. The skill and the engine are separate: installing the Python package does not automatically install every AI host's skill files.

## What can Fablexis do today?

### 1. Create a video project from an idea or script

Start with a concept, a written brief, or an existing script. The offline pipeline can produce structured planning and production artifacts.

```powershell
fablexis create --idea "Explain how AI agents turn goals into actions using a clear diagram and a concise visual narrative." --duration 15 --project my-video
```

Or start with a Markdown script:

```powershell
fablexis create --script script.md --duration 45 --aspect-ratio 16:9 --project my-video
```

The offline pipeline records its deterministic fallback in `production-report.json`.

### 2. Build structured production artifacts

Depending on the workflow, Fablexis can create:

- `blueprint.json` — a structured video blueprint.
- `storyboard.md` — a readable storyboard.
- `storyboard.svg` and `storyboard.html` — storyboard previews.
- `quality-report.json` — available project quality checks.
- `production-report.json` — the production run record.
- `media-report.json` — export QA details.
- Deterministically rendered frames and a verified MP4 when the required export dependencies are available.

These artifacts help separate creative planning from rendering and make the production process easier to inspect.

### 3. Render motion graphics locally

The supported rendering engine includes deterministic typography and supported graphics such as:

- Kinetic text.
- Charts and diagrams.
- Maps and structured graphic layouts.
- Scene-specific visual treatments.
- Project-local PNG, JPG/JPEG, and supported SVG assets.

Exact labels, numbers, and timing are represented as structured data rather than being entrusted to an image model to reproduce accurately.

### 4. Analyze existing footage

Fablexis can analyze local video metadata, sample representative frames, estimate visual cut boundaries, and generate contact sheets.

```powershell
fablexis analyze-video input.mp4 --output analysis/input --interval 5 --max-frames 24
```

This produces an analysis report, sampled frames, and contact sheets.

The current analysis is deterministic and heuristic. It does not claim semantic recognition of people, objects, activities, or narrative meaning.

### 5. Analyze a visual reference

Measure aspects of a reference video to help plan a new edit:

```powershell
fablexis analyze-reference reference.mp4 --output analysis/reference --interval 2 --max-frames 24
```

The resulting style report can include:

- Shot count and estimated cut frequency.
- Duration distribution.
- Brightness, contrast, and saturation.
- Framing and visual-change estimates.
- Heuristic graphic-region candidates.
- Methodology, confidence, and limitations.

These are measurable observations, not an understanding of the creator's intentions or the semantic meaning of every shot.

### 6. Prepare an explainable edit plan

Compare a reference with local footage:

```powershell
fablexis edit-plan --reference reference.mp4 --footage footage/clip-a.mp4 footage/clip-b.mp4 --duration 30 --output analysis/edit-plan
```

The output includes an `editing-plan.json` containing candidate shots, preliminary brightness-based ranking, source trim points, target timing, alternatives, unresolved requirements, and a versioned timeline contract.

**Brightness-based ranking is not semantic shot selection.** A brighter clip is not necessarily the most relevant clip for a scene.

### 7. Render and verify a timeline

```powershell
fablexis render-timeline analysis/edit-plan/editing-plan.json --project-root . --output analysis/edit-plan/rendered.mp4 --crf 18
```

The current timeline renderer supports sequential video clips, source trims, explicit black gaps, output scaling with letterboxing, H.264 encoding, and preservation of available unmuted source audio.

The renderer rejects unsupported overlaps, non-cut transitions, and unsupported non-empty tracks instead of silently pretending to process them.

### 8. Verify the actual exported media

```powershell
fablexis verify-output my-video/motionforge.mp4
```

You can independently inspect the output with FFprobe:

```powershell
ffprobe -v error -show_entries "format=duration,size:stream=codec_name,width,height,r_frame_rate,codec_type,pix_fmt" -of json my-video/motionforge.mp4
```

Fablexis uses temporary output files and validation before finalizing supported exports. A failed render should not be treated as a successful production merely because a command was started.

## Quick start

### Requirements

- Python 3.10 or newer.
- Pillow, installed with the package dependencies.
- FFmpeg and FFprobe on `PATH` for MP4 export, video analysis, and media quality checks.
- An AI agent is optional for direct CLI use and offline production.

### Step 1 — Download the repository

```powershell
git clone https://github.com/suryanshsk/FABLEXIS.git
cd FABLEXIS
```

For the published version:

```powershell
git checkout v0.3.0
```

### Step 2 — Create a Python environment

Windows PowerShell:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3 — Install Fablexis

```powershell
python -m pip install --upgrade pip setuptools
python -m pip install -e .
```

### Step 4 — Check the installation

```powershell
fablexis doctor
fablexis --help
```

If the console command is not available, use:

```powershell
python -m engine.cli doctor
python -m engine.cli --help
```

### Step 5 — Install FFmpeg for MP4 export

Download an appropriate build from [FFmpeg's official download page](https://ffmpeg.org/download.html). Add its `bin` directory to your `PATH`, open a new terminal, and verify:

```powershell
ffmpeg -version
ffprobe -version
```

Planning and previews can work without FFmpeg, but export and video-analysis commands require the relevant media tools.

### Step 6 — Create your first project

```powershell
fablexis create --idea "Explain how local-first AI tools work, using a title, a diagram, and a concise ending." --duration 15 --project first-video
```

### Step 7 — Validate, preview, run QA, and export

```powershell
fablexis validate first-video/blueprint.json
fablexis preview first-video
fablexis qa first-video
fablexis export first-video
```

The compatibility output filename is `motionforge.mp4`. It is retained for existing projects and scripts.

### Step 8 — Verify the MP4

```powershell
fablexis verify-output first-video/motionforge.mp4
```

Inspect the production report and media report as well. A trustworthy workflow checks the resulting file rather than relying only on a success message.

---

## Use Fablexis with Gemini, Claude, ChatGPT, and Codex

Fablexis is designed for agent-assisted production, but **agent skill discovery, local command execution, and a verified video render are three different capabilities**.

An AI host may read the instructions without being able to execute local commands. It may execute commands without having usable model access. It may run a pipeline without successfully producing the requested output.

The steps below explain how to set up each environment without implying that every host has already passed an independent end-to-end acceptance test.

### Before connecting any AI agent

Complete these steps first:

1. Clone the complete Fablexis repository.
2. Install the Python package in the environment where the agent can execute commands.
3. Install FFmpeg and FFprobe if you need MP4 export.
4. Run `fablexis doctor` and confirm that the CLI works manually.
5. Open the repository root as the agent's workspace.
6. Confirm that the agent can read project files and has approved local command execution.
7. Verify the resulting video with the documented QA workflow.

The complete repository matters because the Python package alone does not install the `.agents/` and `.claude/` skill files into an agent's workspace.

### Gemini CLI

**Integration status:** Fablexis skill discovery was verified with the official Gemini CLI in a trusted workspace. A successful Gemini-model-driven Fablexis video render has not been verified.

#### Step 1 — Install and configure Gemini CLI

Follow the current installation instructions in the [official Gemini CLI repository](https://github.com/google-gemini/gemini-cli).

Open a terminal in the Fablexis repository:

```powershell
cd FABLEXIS
gemini
```

Use an authentication method supported by your installed Gemini CLI and account.

#### Step 2 — Trust the workspace when appropriate

Gemini CLI may not load project skills from an untrusted workspace. Review the repository before granting trust or approving local command execution.

#### Step 3 — Check skill discovery

From the Gemini CLI interface, run:

```text
gemini skills list
```

Confirm that the Fablexis skill is listed as enabled. The skill's canonical instructions are located at:

```text
.agents/skills/fablexis/SKILL.md
```

#### Step 4 — Ask for a video

For example:

```text
Use Fablexis to create a 15-second vertical explainer about local-first AI.

Create a clear title, three visual beats, a simple diagram, and a strong
ending. Use the local Fablexis engine. Validate the project, generate
the available previews, render the MP4, and inspect the production report.
Do not claim success unless the resulting file passes output verification.
```

#### Step 5 — Confirm execution and verify the output

Check that the agent actually invokes the local Fablexis CLI, creates project artifacts, and renders the file.

If the model fails before invoking any tools, inspect the authentication and eligibility error. Skill discovery alone does not prove that the model can execute the workflow.

The Fablexis engine does not require a Gemini API key for its deterministic offline workflow. Gemini's own natural-language interface still requires a supported model-access configuration.

**Known limitation:** In the recorded acceptance test, Gemini CLI 0.65.0 discovered the enabled skill, but a natural-language request failed before tool execution because the available individual Code Assist client was rejected as unsupported. No successful Gemini-driven video render was established.

### Claude Code

**Integration status:** A Claude Code project-skill adapter is included. Host discovery and end-to-end invocation remain unverified.

#### Step 1 — Install Claude Code

Follow the [official Claude Code documentation](https://docs.anthropic.com/en/docs/claude-code/overview) for the current installation and authentication procedure.

#### Step 2 — Open the repository root

Start Claude Code in the Fablexis repository:

```powershell
cd FABLEXIS
claude
```

Use the command appropriate to your installed operating system and shell.

#### Step 3 — Check the project skill

The project adapter is located at:

```text
.claude/skills/fablexis/SKILL.md
```

The adapter points to the canonical Fablexis workflow. Use the skill-discovery interface or command supported by your installed Claude Code version to confirm that it has loaded.

If it does not appear, check that you opened the repository root and that the complete skill directory exists.

#### Step 4 — Request a production run

```text
Use the Fablexis skill to create a 20-second 16:9 explainer about
how an AI agent turns a goal into a verified result.

Plan the narrative and scenes, create the supported project files,
validate the blueprint, generate the available previews, run QA,
and export the MP4. Inspect the report and verify the output before
reporting completion. Clearly identify any unsupported visual or audio
requirements.
```

#### Step 5 — Approve and inspect local commands

Claude Code may request permission to execute commands or access files. Review the command and approve only actions you intend to allow.

If Claude can read the skill but cannot render, confirm that the Python environment, CLI installation, working directory, and local command permissions are correct.

**Important:** Installing Claude Code does not automatically establish that the Fablexis integration is working. Confirm skill discovery and actual rendering independently.

### ChatGPT

**Integration status:** ChatGPT can help plan production, explain errors, and work with project files when they are made available. Ordinary ChatGPT conversation does not automatically grant access to your local filesystem or execute arbitrary commands on your computer.

There are two distinct ways to use ChatGPT with Fablexis.

#### Option A — Use ChatGPT for planning and troubleshooting

1. Open the Fablexis repository locally.
2. Share the relevant README, skill instructions, blueprint, report, or error output with ChatGPT.
3. Ask ChatGPT to help draft a production brief, improve the storyboard, diagnose an error, or revise supported project data.
4. Save the reviewed changes into your local project.
5. Run the Fablexis CLI locally.
6. Inspect the output and verify the MP4.

Example request:

```text
Help me prepare a Fablexis production brief for a 30-second product
explainer. Produce a scene-by-scene plan with exact on-screen text,
timings, visual requirements, and a list of supported and unsupported
rendering requirements. Do not claim that a video has been rendered.
```

This workflow uses ChatGPT as a planning assistant and Fablexis as the local production engine.

#### Option B — Use a supported local coding-agent environment

If your ChatGPT plan and environment provide a coding-agent workflow with repository and command-execution access, use that environment's documented setup.

The Fablexis shared skill is located at:

```text
.agents/skills/fablexis/SKILL.md
```

1. Make the complete repository available to the coding-agent environment.
2. Confirm that it discovers the Fablexis skill.
3. Confirm that the environment can execute the installed local CLI.
4. Request a video production run.
5. Inspect the production artifacts and verify the exported MP4.

A GitHub URL or a regular chat message alone does not grant access to a computer's local files.

**Important:** The Fablexis skill has not been independently verified end to end in a Codex environment, and ordinary ChatGPT chat should not be presented as a local command-execution interface.

### OpenAI Codex

**Integration status:** The shared Agent Skills convention is documented for Codex-compatible environments, but Codex discovery and a complete video-rendering workflow have not been independently verified.

#### Step 1 — Open the full repository

Use your supported Codex environment to make the Fablexis repository available as the working project.

```text
FABLEXIS/
├── .agents/
│   └── skills/
│       └── fablexis/
│           └── SKILL.md
├── engine/
├── schemas/
├── tests/
├── examples/
├── pyproject.toml
└── README.md
```

#### Step 2 — Install the local engine

In the environment that will execute the commands:

```powershell
python -m pip install -e .
fablexis doctor
```

Ensure the required FFmpeg tools are installed for video export.

#### Step 3 — Verify skill discovery

The shared skill lives at:

```text
.agents/skills/fablexis/SKILL.md
```

Check discovery using the skill interface supported by your Codex environment. If the skill is not visible, verify the workspace root, repository contents, and current host documentation.

#### Step 4 — Request the video

```text
Use the Fablexis skill to create a 15-second vertical video about
why reproducible software builds matter.

Create the supported project artifacts, validate the blueprint,
generate previews, run QA, and export the MP4. Inspect the reports
and verify the file. If a requested effect, transition, caption,
or audio operation is unsupported, explain that limitation instead
of silently omitting it.
```

#### Step 5 — Verify the actual result

Confirm that Codex ran the local commands rather than merely writing suggested commands in its response.

Inspect the generated project, run the verification command, and check the MP4 with FFprobe.

### What if an AI agent cannot run Fablexis?

Work through this checklist:

1. **Skill missing:** Confirm that you opened the complete repository and that the relevant skill path exists.
2. **Command not found:** Activate the Python virtual environment and reinstall the package.
3. **FFmpeg unavailable:** Install FFmpeg and FFprobe and verify both are on `PATH`.
4. **Model access error:** Resolve the AI host's supported authentication or account-eligibility issue.
5. **Permission error:** Enable the required approved local command-execution capability.
6. **Render failure:** Inspect FFmpeg support, source paths, source trim bounds, dimensions, and the production logs.
7. **Missing output:** Run the pipeline and output verification again; do not assume that a generated plan is a rendered video.
8. **Unsupported feature:** Check the current renderer limitations and revise the plan to use supported operations.

Do not attempt to work around an AI provider's access restrictions by extracting browser cookies, copying private session tokens, or using undocumented authentication.

See [`docs/agent-integrations.md`](docs/agent-integrations.md) for the repository's integration documentation.

---

## What Fablexis does not do yet

Fablexis is actively evolving. The current release should be evaluated against its implemented features, not its long-term vision.

The verified offline workflow does not currently provide:

- General-purpose AI text-to-video generation.
- Guaranteed automatic semantic shot selection.
- Semantic understanding of every scene in an uploaded video.
- A fully implemented automated end-to-end integration for every AI host.
- General-purpose video overlays and caption compositing in the timeline renderer.
- Arbitrary overlaps, transitions, and compositing operations.
- Standalone audio-track mixing.
- Voiceover, music, or sound-effect generation.
- A guarantee that every creative request can be rendered exactly as described.
- A hosted collaboration platform or managed cloud rendering service.

The timeline contract includes overlay and caption track structures, but the current renderer does not composite those tracks. A contract field should not be confused with an implemented rendering feature.

Fablexis can plan more than its current renderer can execute. The workflow should identify unsupported requirements rather than silently claiming to have produced them.

## CLI reference

Run:

```powershell
fablexis --help
```

For command-specific options, use:

```powershell
fablexis create --help
fablexis render-timeline --help
fablexis analyze-video --help
```

| Command | Purpose |
|---|---|
| `init` | Create a starter project and brief |
| `doctor` | Check local rendering dependencies and readiness |
| `brief` | Build planning outputs from a brief |
| `plan` | Build a blueprint from text or Markdown |
| `storyboard` | Generate storyboard files |
| `preview` | Generate a project preview |
| `render` | Render a blueprint preview |
| `qa` | Run available project quality checks |
| `validate` | Validate a blueprint |
| `validate-timeline` | Validate a timeline contract or edit-plan wrapper |
| `export` | Export an MP4 through FFmpeg |
| `verify-output` | Verify MP4 metadata and representative decoded frames |
| `create` | Run the idea/script-to-project pipeline |
| `analyze-video` | Analyze local footage and produce contact sheets |
| `analyze-reference` | Measure reference-video characteristics |
| `edit-plan` | Compare reference footage and produce a structured edit plan |
| `render-timeline` | Render a supported sequential timeline |

The legacy `motionforge` command remains available for compatibility.

## Privacy, security, and local-first design

Fablexis is designed to keep the supported production engine and rendering workflow on your machine.

- No Fablexis account is required.
- No Fablexis subscription is required.
- The deterministic offline workflow does not require a network connection for already available local inputs.
- Local rendering uses the installed engine and media tools.
- Local project assets are validated against supported formats and path restrictions.
- Optional AI-host authentication remains separate from local rendering.

Keep credentials out of briefs, blueprints, reports, skill files, and media metadata. Use environment variables or an approved secrets manager for credentials required by other tools.

Grant agents only the filesystem and command permissions needed for the task.

The local-first architecture does not automatically guarantee that every AI host operates offline. If you use an external AI model, that provider's own data-handling and network policies apply.

## Troubleshooting

### `fablexis` is not recognized

Activate your virtual environment and reinstall:

```powershell
python -m pip install -e .
python -m engine.cli --help
```

### FFmpeg or FFprobe is missing

```powershell
ffmpeg -version
ffprobe -version
fablexis doctor
```

Check your `PATH`, install the missing tools, open a new terminal, and retry.

### Pillow cannot be imported

```powershell
python --version
python -m pip show Pillow
python -m pip check
```

Confirm that the Python environment you activated is the one where Fablexis was installed.

### The AI can read the skill but cannot render

Skill access and command execution are separate. Confirm that the host has repository access, the CLI is installed in the execution environment, and the relevant local command permissions are enabled.

### The MP4 export fails

Check that:

- Both FFmpeg and FFprobe are installed.
- FFmpeg includes `libx264` and AAC support when audio encoding is needed.
- Source files exist inside the intended project root.
- Source trim points are within the source media duration.
- The project dimensions satisfy the renderer's requirements.
- The timeline does not contain unsupported overlaps, transitions, or non-empty unsupported tracks.

### The output looks wrong

Inspect the storyboard, rendered frames, asset paths, dimensions, timing, quality report, and production report. Verify the exported media rather than assuming the requested creative intent was achieved.

## Roadmap

Potential areas for future development include:

- More robust AI-host integration tests.
- Expanded timeline compositing and transition support.
- Caption and overlay rendering.
- Standalone audio mixing and synchronization.
- Optional provider integrations with explicit configuration.
- Improved semantic shot selection.
- More extensive frame-level visual QA.
- Better cross-platform installation and acceptance testing.

Roadmap items are not current capabilities. Follow the repository's issues and release notes for implementation status.

## Contributing

Contributions are welcome.

Before opening a pull request:

1. Read the existing implementation and relevant documentation.
2. Add regression tests for behavioral changes.
3. Run the test suite and repository validation.
4. Update documentation when commands or behavior change.
5. Keep generated media, temporary reports, caches, and credentials out of source control.
6. Document the operating systems and AI hosts you actually tested.
7. Distinguish implemented functionality from planned work.

Useful starting points:

- [Issues](https://github.com/suryanshsk/FABLEXIS/issues)
- [Pull requests](https://github.com/suryanshsk/FABLEXIS/pulls)
- [Release v0.3.0](https://github.com/suryanshsk/FABLEXIS/releases/tag/v0.3.0)

## Frequently asked questions

### Is Fablexis free?

Fablexis is open source under the MIT License. Its deterministic local workflow does not require a Fablexis subscription or API key. Your operating system, hardware, and any external services you independently choose may have their own costs.

### Does Fablexis require an AI API key?

No API key is required for the deterministic offline workflow. However, using an AI agent's natural-language interface may require that provider's own supported authentication or account access.

### Can Fablexis generate MP4 videos locally?

Yes, for supported production workflows when FFmpeg and FFprobe are installed and the export succeeds. The output should be verified before it is considered complete.

### Does Fablexis generate AI video from text?

Fablexis can turn an idea or script into structured production artifacts through its offline workflow. It does not include a general-purpose AI text-to-video model in the verified default pipeline.

### Can I use Fablexis with Gemini?

The repository includes a shared skill that the official Gemini CLI discovered in the recorded acceptance environment after workspace trust. A complete Gemini-model-driven video render has not been verified; usable model access and command execution are still required.

### Can I use Fablexis with Claude Code?

A Claude Code project-skill adapter is included. Confirm that your installed version discovers it and can execute the local engine. End-to-end host verification remains outstanding.

### Can I use Fablexis with ChatGPT?

ChatGPT can help plan, review, and troubleshoot Fablexis projects. Access to local files and command execution depends on the specific ChatGPT or coding-agent environment. A normal chat message does not automatically execute commands on your computer.

### Can I use Fablexis with Codex?

The repository includes the shared Agent Skills path intended for compatible environments. Verify skill discovery and local command execution in your specific Codex environment; the complete integration has not been independently verified.

### Does Fablexis replace Premiere Pro, DaVinci Resolve, or other professional editors?

It is not currently a full replacement for a professional nonlinear editor. Fablexis focuses on agent-operable structured production and supported deterministic rendering. It may complement other editing workflows.

### Does it work offline?

The deterministic workflow can run offline when the required software and media are already installed locally. External AI models, if used, have separate connectivity and authentication requirements.

### Does Fablexis analyze what objects or people appear in footage?

Its current deterministic video analysis measures media characteristics, samples frames, and estimates cuts. It does not claim general semantic recognition of objects, people, emotions, or narrative meaning.

### How do I know the output is real?

Inspect the production report, run `fablexis verify-output`, and independently check the file with FFprobe. A storyboard, plan, or successful command invocation alone is not proof of a valid exported video.

## SEO and AI-search summary

Fablexis is an **open-source, local-first AI-agent video production toolkit**. It combines reusable AI-agent skill instructions with a deterministic local Python rendering engine for structured motion graphics, video planning, storyboard generation, local footage analysis, timeline preparation, MP4 export, and output verification. It is designed for developers who want a reproducible, inspectable video workflow without a mandatory hosted rendering service or Fablexis subscription.

Relevant topics include:

- Open-source AI video production.
- AI coding agent video workflows.
- Local-first video rendering.
- Agent skills for video production.
- Python video rendering with FFmpeg.
- Motion graphics automation.
- Structured video blueprints and storyboards.
- Local video analysis and contact sheets.
- Automated MP4 verification.
- Reproducible media production.

These terms describe the project's focus; they are not claims of compatibility with every AI agent or feature support beyond the documented implementation.

## License

Fablexis is distributed under the [MIT License](LICENSE).

Repository: https://github.com/suryanshsk/FABLEXIS

Latest release: https://github.com/suryanshsk/FABLEXIS/releases/tag/v0.3.0

**Tell your AI what to create. Fablexis brings it to life.**
