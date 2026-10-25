# Fablexis

**Tell your AI what to create. Fablexis brings it to life.**

Fablexis is an open-source, AI-agent-installable video-production skill pack
backed by a deterministic local rendering engine. It helps an AI agent turn an
idea, outline, script, facts, or references into an original motion-graphics
project that can be inspected, validated, and exported locally.

Fablexis is not a hosted SaaS product. It does not require a Fablexis account,
subscription, or API key. Creative planning can be assisted by an AI agent,
while supported graphics, typography, previews, quality checks, and MP4
encoding run on the local machine.

## What Fablexis produces

Depending on the command and available dependencies, a project can contain:

- A narrative and visual direction plan.
- Scene-by-scene timing, transitions, text, and asset requirements.
- A validated `blueprint.json`.
- `storyboard.md`, `storyboard.svg`, and `storyboard.html`.
- A `quality-report.json`.
- Deterministic rendered frames.
- A `production-report.json`.
- A real H.264 MP4 when FFmpeg is installed and export succeeds.

The renderer supports deterministic typography, charts, diagrams, maps,
kinetic text, scene-specific treatments, and project-local PNG, JPG/JPEG, and
safe SVG assets. Exact labels, numbers, and timing are kept in structured
data rather than delegated to an image model.

## Quick start

### Requirements

- Python 3.10 or newer.
- Pillow, installed automatically from `pyproject.toml`.
- FFmpeg and FFprobe on `PATH` for MP4 export, local video analysis, and
  rendered-media quality checks. They are optional for planning and previews.

### Windows PowerShell

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools
python -m pip install -e .
fablexis doctor
fablexis --help
```

If PowerShell blocks activation, use the module fallback from the activated
environment:

```powershell
python -m engine.cli doctor
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools
python -m pip install -e .
fablexis doctor
```

### Create a project from an idea

```powershell
fablexis create --idea "How AI agents turn goals into actions. A diagram shows the loop. Human judgment closes the story." --duration 15 --project my-video
```

Or use an existing script:

```powershell
fablexis create --script script.md --duration 45 --aspect-ratio 16:9 --project my-video
```

The offline pipeline does not need a network connection or paid provider. It
records its deterministic fallback in `production-report.json`.

### Review and export

```powershell
fablexis validate my-video\blueprint.json
fablexis preview my-video
fablexis qa my-video
fablexis export my-video
```

The compatibility output is named `motionforge.mp4`. This name is retained so
existing projects and scripts continue to work. Export writes to a temporary
file, verifies metadata and representative decoded frames, then replaces the
destination only on success. A previous good output is preserved if a new
export fails. The Fablexis-branded `production-report.json` is the authoritative
record of the production run; `media-report.json` contains export QA details.

Verify an exported file rather than trusting a command's exit message:

```powershell
ffprobe -v error -show_entries "format=duration,size:stream=codec_name,width,height,r_frame_rate,codec_type,pix_fmt" -of json my-video\motionforge.mp4
```

### Analyze local video footage

Fablexis can perform deterministic local media analysis without an AI provider:

```powershell
fablexis analyze-video input.mp4 --output analysis\input --interval 5 --max-frames 24
```

The command writes `analysis-report.json`, representative JPEG frames under
`frames/`, and one or more labeled contact sheets under `contact-sheets/`.
The report includes FFprobe metadata, sampling timestamps, estimated visual
cut boundaries, stable shot records, relative artifact paths, and explicit
warnings that no semantic subject recognition was performed. FFmpeg and
FFprobe are required for this command. It does not yet edit raw footage or
perform semantic content recognition.

### Analyze a reference and prepare an edit plan

Reference analysis extends the deterministic media analysis with measurable
style observations:

```powershell
fablexis analyze-reference reference.mp4 `
  --output analysis\reference `
  --interval 2 `
  --max-frames 24 `
  --scene-threshold 0.35
```

The generated `reference-style-report.json` records framing, shot count,
duration distribution, cut frequency, brightness, contrast, saturation,
visual-change estimates, heuristic graphic-region candidates, methodology,
confidence, and limitations. It does not infer narrative meaning, objects,
emotions, or creator intent.

To compare a reference with one or more local footage files and produce an
explainable, non-rendering edit plan:

```powershell
fablexis edit-plan `
  --reference reference.mp4 `
  --footage footage\clip-a.mp4 footage\clip-b.mp4 `
  --duration 30 `
  --output analysis\edit-plan
```

The output contains `editing-plan.json` with candidate shots, preliminary
brightness-based ranking, source trim points, target timing, alternatives,
unresolved requirements, and a validated version `1.0` timeline contract.
Semantic relevance is not claimed. The contract includes video, audio,
overlay, and caption tracks. A validated timeline can be rendered with:

```powershell
fablexis render-timeline analysis\edit-plan\editing-plan.json `
  --project-root . `
  --output analysis\edit-plan\rendered.mp4
```

The renderer supports sequential video clips, source trims, explicit black
gaps, output scaling with letterboxing, H.264/yuv420p encoding, and source
audio preservation when any unmuted source clip contains audio. Set
`"mute": true` on a video clip to replace its audio with silence. Overlaps and
transitions other than cuts are rejected; overlays and captions are contract
placeholders and are not composited by this renderer. The command accepts both
a timeline document and the `editing-plan.json` wrapper produced by
`edit-plan`:

```powershell
fablexis render-timeline analysis\edit-plan\editing-plan.json `
  --project-root . `
  --output analysis\edit-plan\rendered.mp4 `
  --crf 18
```

Timeline clip order is determined by `timeline_start_seconds`, not array
position. Source duration (`out_seconds - in_seconds`) must match the clip's
timeline duration. Gaps remain at their specified positions and render as
black video; when any source audio is present, those gaps and clips without
audio receive silence so the output audio stays synchronized. Audio is copied
from video clips only when present and not muted. The renderer does not mix
standalone audio tracks, compose overlays/captions, or generate voice, music,
or effects. It rejects overlapping clips, non-cut transitions, and non-empty
unsupported tracks rather than silently discarding them.

The output uses H.264 (`libx264`), AAC when audio is present, `yuv420p`, a
constant project frame rate, and `+faststart`. Project dimensions must be even
for this H.264 pixel format. Scaling preserves the full source frame and adds
black letterboxing/pillarboxing; it does not crop. `--crf` accepts 0–51
(default 18; lower values retain more quality). FFmpeg and FFprobe must both be
installed. A render is written to a unique temporary MP4, probed for stream,
codec, size, dimensions, frame rate, pixel format, duration, and audio
synchronization, and representative frames are decoded before the output is
finalized. A failed render leaves no partial file at the requested output.
If rendering fails, check that FFmpeg includes `libx264` and AAC encoder
support, both executables are on `PATH`, the source trims fit their media, and
all source paths resolve inside `--project-root`.

## FFmpeg installation

Download an FFmpeg build from [ffmpeg.org/download.html](https://ffmpeg.org/download.html),
install it, and add its `bin` directory to `PATH`. Open a new terminal and
verify both commands:

```text
ffmpeg -version
ffprobe -version
```

`fablexis doctor` reports whether FFmpeg is available. If it is missing,
preview and QA remain usable, while export fails with an actionable message
and does not create a fake MP4.

## Using Fablexis with AI agents

Fablexis provides reusable instructions, not an automatic permission grant.
An agent must be able to read the repository, access the intended project
directory, and use an approved local command-execution mechanism before it can
render a video.

The canonical shared skill is
[`.agents/skills/fablexis/SKILL.md`](./.agents/skills/fablexis/SKILL.md).
It is the primary workflow entry point for hosts that support the shared
`.agents/skills/` convention. A thin Claude Code adapter is available at
[`.claude/skills/fablexis/SKILL.md`](./.claude/skills/fablexis/SKILL.md).
These files reuse the local engine; they do not provide shell permissions or a
hosted rendering service.

### VS Code-style workspace agent — adapter present, host loading not independently tested

The repository includes
[`.github/agents/fablexis-video-producer.agent.md`](./.github/agents/fablexis-video-producer.agent.md).
Expose the repository as a workspace, select the custom agent, and ensure the
Python environment is installed. The agent should invoke:

```text
fablexis create --idea "<idea>" --project <project>
```

It must inspect `production-report.json`, validate the blueprint, run QA, and
use FFprobe before claiming that an MP4 exists.

### Claude Code — adapter present, host loading not independently tested

Expose the root [`SKILL.md`](./SKILL.md) and the relevant files under
[`skills/`](./skills/) using the skill mechanism supported by the Claude
product or environment in use. The host must also provide approved access to
the local repository and command execution. A normal chat session may be able
to plan a project without being able to run the local renderer.

### Gemini — documented, host loading not independently tested

Provide [`SKILL.md`](./SKILL.md) and relevant specialist skills through a
supported workspace, project-instruction, or file-context mechanism. A browser
chat should not be assumed to access local files or execute `fablexis`.
Configure and test an approved local command bridge before requesting an
automated render.

### ChatGPT/Codex — documented, host loading not independently tested

Use a workspace-capable Codex or editor environment that can read this
repository and execute local commands. Expose [`SKILL.md`](./SKILL.md), the
needed specialist skills, and the project directory. A GitHub URL or ordinary
chat message alone does not grant access to the local filesystem.

For every host, distinguish these states:

1. **Planning available:** the agent can read instructions and produce files.
2. **Local execution available:** the agent can invoke the CLI in the project
   environment.
3. **Verified production:** the agent has run the pipeline, inspected its
   report, and verified the MP4 with FFprobe.

Do not treat a consumer AI subscription as API access. Fablexis does not
extract browser cookies, bypass subscription restrictions, or require
undocumented authentication.

## CLI commands

Use `fablexis --help` and each command's help for the installed version.

| Command | Purpose |
| --- | --- |
| `init <project>` | Create a starter project and brief. |
| `doctor` | Check FFmpeg, FFprobe, and local preview readiness. |
| `brief <input> --project <project>` | Build planning outputs from a brief. |
| `plan <input> --output <file>` | Build a blueprint from text or Markdown. |
| `storyboard <project>` | Generate storyboard preview files. |
| `preview <project>` | Generate the storyboard preview. |
| `render <blueprint> --output <dir>` | Render a blueprint preview. |
| `qa <project>` | Run available project quality checks. |
| `validate <blueprint>` | Validate a blueprint against the schema. |
| `validate-timeline <timeline>` | Validate the timeline contract or edit-plan wrapper. |
| `export <project>` | Render and encode MP4 through FFmpeg. |
| `verify-output <file.mp4>` | Verify MP4 metadata and decode representative frames. |
| `create --idea/--script ...` | Run the offline idea-to-video pipeline. |
| `analyze-video <input>` | Analyze local metadata, frames, estimated cuts, and contact sheets. |
| `analyze-reference <input>` | Produce a measurable reference-style report. |
| `edit-plan --reference ... --footage ...` | Compare local footage with a reference and write an editable plan. |
| `render-timeline <timeline> --output <file>` | Render a validated sequential timeline through FFmpeg. |

The legacy `motionforge` console command remains available:

```powershell
motionforge --help
```

The module fallback works when console scripts are not on `PATH`:

```powershell
python -m engine.cli --help
```

## Production modes

- **Quick:** concise direction, narrative arc, and scene prompts.
- **Director:** storyboard, timing, composition, camera, transitions, sound,
  and continuity notes.
- **Production:** Director output plus evidence tracking, asset planning,
  blueprint validation, previews, QA, and render outputs.

These modes do not activate external providers, research services, image
generation, or voice generation. Those integrations are optional and are not
implemented by the default provider boundary.

## Assets and blueprints

Keep assets inside the project directory. Supported local asset layers include
PNG, JPG/JPEG, and a restricted SVG subset:

```json
{
  "type": "asset",
  "asset": "assets/diagram.svg",
  "x": 48,
  "y": 220,
  "width": 444,
  "height": 300,
  "fit": "contain",
  "opacity": 0.9,
  "z": 2
}
```

The renderer validates containment, existence, file contents, and supported
formats before rendering. Absolute paths, paths outside the project, external
SVG URLs, scripts, and network resources are rejected. The bundled demo media
is original local artwork documented in
[`examples/ASSET-PROVENANCE.md`](./examples/ASSET-PROVENANCE.md).

## Repository layout

```text
SKILL.md                         Main agent workflow
skills/                          Specialist production skills
references/                      Creative and production playbooks
examples/                        Input, blueprints, and local demo assets
engine/                          Planner, validator, renderer, and CLI
schemas/                         Blueprint schema
tests/                           Regression tests
validate.py                      Repository validation
pyproject.toml                   Package metadata and CLI entry points
```

`engine/pipeline.py` orchestrates intake, segmentation, planning, creative
direction, asset planning, validation, previews, frame QA, export, FFprobe
metadata, and production reporting. `engine/vox_motion.py` owns blueprint
generation, compositing, typography, and frame rendering.

## Privacy, credentials, and boundaries

The deterministic local workflow needs no account, API key, or network access
for already available local files. Keep credentials in environment variables
or an approved secrets manager, never in skills, blueprints, reports, briefs,
or image metadata. Do not grant an agent access to directories outside the
project that it needs to produce the requested output.

Optional providers are not implemented by default. An environment variable
does not activate a provider unless the provider exists in the installed
version and is documented.

## Troubleshooting

### `fablexis` is not recognized

Activate the virtual environment and reinstall:

```powershell
python -m pip install -e .
python -m engine.cli --help
```

### Pillow fails to import

```powershell
python --version
python -m pip show Pillow
python -m pip check
```

### FFmpeg or FFprobe is missing

Run `ffmpeg -version`, `ffprobe -version`, and `fablexis doctor`. Check
`PATH`, open a new terminal, and retry. Export remains blocked until both
executables are available.

### An agent can read the skill but cannot render

Reading a skill file does not grant filesystem or command permissions. Confirm
that the host can access the repository, the package is installed, the
working directory is correct, and an approved command tool is enabled. Run the
CLI yourself if the host only supports text generation.

### The output looks wrong

Inspect the storyboard preview, representative frames, quality report, asset
paths, dimensions, timing, and production report. Do not claim visual
inspection unless frames or playback were actually reviewed.

## Current limitations

- The deterministic offline provider is the only provider implemented and
  tested.
- MP4 export depends on FFmpeg and a successful render.
- Audio and voiceover generation are not implemented in the verified workflow.
- Research planning is not live source verification.
- The renderer supports a defined graphics and SVG subset, not every visual
  instruction an agent can describe.
- Host-specific skill loading must be verified in each Claude, Gemini,
  ChatGPT/Codex, or other environment.
- `motionforge` remains the compatibility command and output filename.

Roadmap ideas include audio support, more agent-host integration tests,
expanded compositing, optional providers with explicit credentials, and
additional frame-level QA. Roadmap items are not current capabilities.

## Contributing

Before submitting changes:

1. Keep generated media, reports, caches, and credentials out of source
   control.
2. Add regression tests for changed engine behavior.
3. Run the existing test suite and repository validation.
4. Update documentation when commands or behavior change.
5. State which platforms and agent hosts were actually tested.

## License

Fablexis is released under the MIT License. See [`LICENSE`](./LICENSE).

Repository: [github.com/suryanshsk/FABLEXIS](https://github.com/suryanshsk/FABLEXIS)

**Tell your AI what to create. Fablexis brings it to life.**
