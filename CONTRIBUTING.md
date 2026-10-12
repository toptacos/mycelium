# Contributing

Thanks for caring about local-first agents. This repo is Apache-2.0; contributions
are welcome under the same license.

## Ground rules

1. **Local-first or nothing.** A feature that requires a cloud account to work
   is not merged. Cloud backends must be optional adapters, never the default
   path, and never the only way to reach a feature.
2. **No telemetry that leaves the machine.** The session log is a local file.
   Adding network calls to the core loop is an automatic no.
3. **Containment over trust.** Tools act inside the workspace; mutations are
   explicit; secrets come from the environment at call time and are never
   logged.
4. **Dependencies need justification.** Runtime deps are `httpx`, `pyyaml`,
   `rich` today. A new one needs a line in the PR body explaining why stdlib
   can't do it.
5. **Tests prove behavior.** Bug fixes come with a test that fails before the
   fix. New tools come with happy path + denial path.

## Workflow

1. Fork / branch: `git checkout -b feat/my-thing`.
2. Write the test first when fixing a bug.
3. `uv run pytest -q` and `scripts/release.sh check`.
4. Conventional commit message: `feat(tools): add ...`.
5. Open a PR against `main`. CI runs the suite on Ubuntu, macOS, and Windows
   across Python 3.11-3.13, plus the live Ollama tier.

## What we will not merge

- Telemetry, analytics, "anonymous" crash reporting.
- Features that phone home for licensing checks of OSS functionality.
- Auto-updating the core agent loop from a remote source.
- Anything that weakens the workspace path policy or the read-only mode.

## Good first issues

Look for the `good first issue` label. Historically: new scaffold templates,
new content kinds, new workflow step types, docs fixes, and VM guide coverage
for a new distro.

## Security reports

Do not open public issues for security problems. Email security@topta.co with
the tool version (`mcy --version`), OS, and a minimal reproduction. We
acknowledge within 3 business days.
