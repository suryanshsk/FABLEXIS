# Agent integration and verification

Fablexis has two separate interfaces:

1. An agent skill gives a host instructions for interpreting a video request.
2. The local `fablexis` CLI performs only the implemented deterministic work.

Finding a skill does not prove that the host can invoke local commands, and a
successful direct CLI run is not proof of agent invocation. Do not report an
agent-host acceptance pass until the host itself has interpreted a natural
language request, invoked the workflow, and produced an MP4 that passes
`fablexis verify-output` and FFprobe checks.

## Host status

| Host | Skill location / convention | Discovery evidence | Invocation evidence |
|---|---|---|---|
| Gemini CLI | `.agents/skills/fablexis/SKILL.md` | **PASS with trusted workspace.** Official `@google/gemini-cli` 0.65.0 listed `fablexis [Enabled]`. Untrusted workspaces skipped project skills. | **BLOCKED.** The prompt failed before tool execution with `IneligibleTierError` / `UNSUPPORTED_CLIENT` for Gemini Code Assist for individuals. No model-driven render was performed. |
| Codex / Codex CLI | Shared `.agents/skills/` Agent Skills directory | Not tested; no `codex` executable was found in PATH or common local program locations. | **NOT VERIFIED.** |
| Claude Code | `.claude/skills/fablexis/SKILL.md` | Adapter exists and points to the canonical shared skill. No `claude` executable was found. | **NOT VERIFIED.** |
| VS Code-style agent | `.github/agents/fablexis-video-producer.agent.md` | Adapter exists; host loading was not independently tested. | **NOT VERIFIED.** |
| Local Fablexis CLI | Installed `fablexis` console entry point or `python -m engine.cli` | **PASS** in the repository and a clean Python 3.10 virtual environment. | **PASS for direct CLI use only.** Not an agent-host test. |

This matrix records tested facts for the acceptance environment, not a
guarantee for every version or account tier. Gemini documentation describes
workspace skills under `.agents/skills/` and requires explicit consent when a
skill is activated. See the [Gemini CLI skills
documentation](https://geminicli.com/docs/cli/skills/). Claude Code documents
project skills in its [skills
guide](https://code.claude.com/docs/en/skills). Codex setup should follow the
[official Codex documentation](https://developers.openai.com/codex/skills/);
this repository's Codex adapter path has not been tested in Codex itself.

## Open this repository with a host

1. Clone or open the complete repository as the host's workspace. Do not copy
   only the skill file if the agent is expected to use the checked-out local
   engine.
2. Install Python 3.10 or newer and run the
   [repository quick start](./quickstart.md) to install Fablexis and check
   FFmpeg/FFprobe.
3. Let the host apply its normal workspace trust, skill activation, and local
   command-consent controls. Never bypass them.
4. Ask the host to list or otherwise confirm the discovered `fablexis` skill.
   If it cannot show discovery, classify the result as **NOT VERIFIED**.
5. Use a small request referencing local footage and ask it to report each
   command and output path. Approve commands through the host's normal
   permission UI.
6. Require the agent to validate the timeline, render with the existing CLI,
   run `verify-output`, and report FFprobe's stream metadata.
7. Confirm the clips visually by reviewing representative decoded frames.
   FFprobe metadata alone is not semantic visual review.

The Python wheel and source distribution currently package the `engine` module
and CLI, not the `.agents/` or `.claude/` skill directories. Installing a wheel
alone therefore does not install or expose a host skill. Use the complete
repository checkout as the workspace for skill discovery; the separately
installed CLI can be useful for engine-only automation.

### Claude Code

From the repository root, run `claude` using the installation method in the
[Claude Code setup guide](https://code.claude.com/docs/en/setup). When the
workspace opens, the project skill should be available as `/fablexis`; verify
that in the host before requesting a render. This documented setup was not
executed here because Claude Code was unavailable.

### Codex

From the repository root, start the installed Codex CLI using its official
[installation instructions](https://developers.openai.com/codex/cli/). Confirm
that the workspace skill is listed by the current host, then request a render.
This setup was not executed here because Codex CLI was unavailable.

## Gemini CLI verification

From the trusted repository root:

```powershell
gemini skills list --all
```

The expected discovery entry is `fablexis [Enabled]` and its path should point
to `.agents/skills/fablexis/SKILL.md`. If the workspace is not trusted, Gemini
CLI may omit project skills. Trust it only through the CLI's normal prompt or
documented settings; this repository does not modify global trust settings.
Skill activation may itself request consent.

On the acceptance machine, `gemini` on PATH was an unrelated broken Python
launcher (`ModuleNotFoundError: No module named 'gemini.cli'`). The official
Node CLI package was available through the local npm cache at version 0.65.0.
Its skill discovery succeeded with temporary workspace trust, but its natural
language request failed before activation or command execution because the
account's Gemini Code Assist client was reported unsupported. No API key was
used, no model was installed, and no global Gemini configuration was changed.
The local renderer does not need Gemini or any other model; a natural-language
agent front end does need a usable host model/backend.

## Boundaries and common failures

- A direct `python -m engine.cli ...` run is a local-engine acceptance test, not
  proof that an AI host invoked the skill.
- A skill file's presence is not proof of host discovery.
- Workspace trust and command permissions are host security controls. Follow
  the host's documented prompts; do not attempt to bypass them.
- If a host cannot authenticate or use its model, report the host as blocked
  or not verified. Do not install a local model or change global auth settings
  without the user's explicit approval.
- The deterministic planner does not perform semantic shot selection. Read
  analysis reports and inspect contact sheets before making content claims.
- Unsupported timeline operations fail explicitly. See
  [roadmap and limitations](./roadmap.md).
