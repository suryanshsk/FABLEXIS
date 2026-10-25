# Release checklist

This checklist is for review and publication preparation. It does not itself
authorize a commit, push, merge, tag, GitHub release, or public announcement.

## Repository and validation

- [x] Version metadata is `0.3.0`; changelog has a `0.3.0` entry.
- [x] Latest existing tag is `v0.2.0`; no `v0.3.0` tag was created.
- [x] PR #2 (`release/v0.3.0` → `main`) is open; its Python 3.10, 3.11, and
  3.12 checks were observed successful on 2026-10-26.
- [x] Local Python 3.10 and 3.12 test suite, validator, and compile checks pass.
- [x] Clean Python 3.10 editable install, `pip check`, console script, tests,
  and validator pass after the documented pip/setuptools upgrade.
- [x] Local wheel build succeeded.
- [x] FFmpeg/FFprobe synthetic multi-clip render and frame-order verification
  passed; detailed evidence is in the ignored acceptance output.
- [ ] Build and install a source distribution in a clean environment.
- [ ] Review latest branch diff and intended files before committing.
- [ ] Confirm PR checks apply to the final candidate commit and merge PR #2.
- [ ] After merge, verify version/changelog on `main`, then create a new
  `v0.3.0` tag/release only with explicit authorization.

## Product, security, and docs

- [x] MIT license and security-reporting policy are present.
- [x] Known unsupported timeline/audio/visual-review capabilities are
  documented.
- [ ] Reproduce host-level agent invocation for Gemini, Codex, and Claude Code
  before claiming any host as fully integrated.
- [ ] Review package contents and a non-editable wheel/sdist install outside
  the checkout; decide how skills/docs ship to agent workspaces.
- [ ] Confirm no credentials or generated video/cache artifacts enter the
  release diff.
- [ ] Confirm tested platform claims are limited to available CI and local
  environments.

## Publication gates

- [ ] Review final release notes, README claims, feature matrix, and launch kit.
- [ ] Obtain explicit approval before merge, tagging, release publication, or
  social posting.
- [ ] Publish only after the exact release commit and CI results are verified.
