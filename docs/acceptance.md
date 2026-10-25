# Reproducible acceptance procedure

This procedure separates local engine checks from agent-host checks. Never
combine their results into a single claim.

## Local engine acceptance

Requirements: Python 3.10+, this repository, FFmpeg, and FFprobe. No AI
provider or network service is needed once the Python dependency is installed.

```powershell
python -m pip install --upgrade pip setuptools
python -m pip install -e .
python -m pip check
python -m unittest discover -s tests -v
python validate.py
python -m compileall -q engine tests
python -m engine.cli --help
python -m engine.cli doctor
git diff --check
```

Then run the [two-clip quick start](./quickstart.md). Require:

- Timeline schema validation succeeds and reports the expected clip count.
- The output file exists and is nonempty.
- `verify-output` reports a passed quality status.
- FFprobe confirms video codec, dimensions, frame rate, duration, pixel format,
  and audio stream policy.
- Representative frames decode and visibly match the requested clip order.
- Warnings and unsupported features are included in the report.

## Agent-host acceptance

For each host independently:

1. Record executable path and version.
2. Confirm the host itself discovers the Fablexis skill using its documented
   mechanism.
3. Submit an ordinary natural-language request against local synthetic clips.
4. Record whether the host activated/read the skill and requested command
   approvals.
5. Capture the actual Fablexis CLI commands the host invoked.
6. Validate the resulting timeline, render, and run `verify-output`.
7. Confirm FFprobe metadata and inspect representative frames.
8. Record manual steps, errors, and whether the host completed the entire task.

Classification:

- **PASS:** all steps including host invocation and media verification passed.
- **FAIL:** host invocation occurred but the workflow or output did not meet
  acceptance.
- **BLOCKED:** an external requirement such as account eligibility prevented
  the test from reaching host invocation.
- **NOT VERIFIED:** the host was unavailable or there is insufficient evidence.

## Recorded environment result

On 2026-10-26, the local workflow rendered two synthetic silent clips in red,
then blue order. The 12-second output was 360×640, 10 fps, H.264/yuv420p, and
had no audio stream. FFprobe and decoded pixel samples confirmed these
properties. The full 37-test suite, `validate.py`, Python compilation, CLI
help/doctor, and `git diff --check` passed on Python 3.10 and 3.12.

The clean Python 3.10 virtual environment passed `pip check`, CLI doctor, all
37 tests, and `validate.py` after upgrading its bundled pip/setuptools. The
shared pre-existing environment's `pip check` reports conflicts in
google-genai, grpcio-status, litellm, and tensorflow-intel; these packages are
not Fablexis dependencies. See
[`out/gemini-cli-acceptance-20261026/acceptance-summary.md`](../out/gemini-cli-acceptance-20261026/acceptance-summary.md)
for detailed local render evidence and command records.

Gemini CLI 0.65.0 discovered the skill only when workspace trust was granted.
Its language-model request was blocked before skill activation/tool execution
by an `UNSUPPORTED_CLIENT` Code Assist eligibility error. Codex and Claude
Code were unavailable in that environment. See
[agent integration status](./agent-integrations.md).
