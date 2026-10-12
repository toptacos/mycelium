# CI: Alternatives & Local-First CI

Why this document exists: GitHub Actions bills per-minute and can be blocked by
account billing. mycelium can run the same pipeline locally, and there are
self-hosted alternatives. Here is the honest mapping.

## 1. What our Actions pipeline does vs what mycelium can do

| Actions capability | mycelium equivalent | Status |
|---|---|---|
| Run shell commands in a checkout | `run_command` tool (allowlisted executables, no shell, cwd-scoped, output+exit captured) | ✅ built |
| Matrix (os × python) | `matrix:` axes in workflow YAML; combos iterate, step ids suffixed `[combo]` | ✅ built |
| Conditionals (`if:`) | `when:` on steps (truthy templated string) | ✅ built |
| Failure gates the build | nonzero exit fails the step → workflow fails → `mcy workflow run` exits 3, with the failing command's output preserved and a checkpoint written | ✅ built |
| Env/secrets | inherited env; connection profiles read tokens at call time | ✅ same |
| Artifacts | files on disk; `uv build` writes `dist/` | ✅ same |
| Pass/fail summary | `mcy report` on the session log; the `report` step writes `CI_LOCAL_RESULT.md` | ✅ built |
| Parallel jobs | sequential (local CPU inference is the bottleneck anyway) | by design |
| PR annotations, required checks, branch protection | none — these are GitHub's servers; use a self-hosted runner if you need them | ❌ N/A |

Verdict: **every build-and-test capability in our `ci.yml` is reproducible
locally.** What is not reproducible is the GitHub *workflow* (PR decorrelation,
status checks, merging gates) — that belongs to the host.

## 2. Run the local CI

```bash
# full pipeline: commit scan, sync, core tests, e2e tests, wheel build
mcy --workspace . workflow run ci-local

# include the live model tier (needs `ollama serve` + qwen3:0.6b)
mcy --workspace . workflow run ci-local --input live=1

# matrix over what you have installed (e.g. pyenv interpreters)
mcy --workspace . workflow run ci-local --input python=3.11
```

Each step is a real `run_command` (uv, pytest, python3) executed inside the
workspace, with the output and exit code captured in the session log. A red
local CI prints the failing command's tail — the receipt, not just a checkmark.

Note on workspace: the commands run in the workspace, so point `--workspace` at
the repo root (`.`). Demo artifacts (`CI_LOCAL_RESULT.md`) land there.

## 3. Alternatives to GitHub Actions

If you want CI *hosting* without GH's billing model, ranked by fit for this
project:

| Option | Cost | Why consider it | Catch |
|---|---|---|---|
| **Woodpecker CI** | free, self-hosted | 3.7k stars, Apache-2.0, almost drop-in for GH Actions YAML syntax, matrix support, runs anywhere Docker runs | you operate it |
| **Forgejo Actions** | free, self-hosted | native to Forgejo (the Gitea community fork); same workflow syntax, no external service | needs a Forgejo instance |
| **Gitea Actions** | free, self-hosted | simplest path if already on Gitea | less active than the fork |
| **Self-hosted GH runner** | free minutes, your hardware | keeps the Actions YAML, your machine runs it | you still need a runner host |
| **Drone** | free, self-hosted | extremely light, container-native | smaller ecosystem |
| **Buildkite** | free tier, then per-seat | great UX, your compute | not free forever |
| **CircleCI** | free tier | mature | credit-based |

For a toptacos org already running servers (the pi/ and Kraken hosts in this
workspace), **Woodpecker or a self-hosted runner on the existing infra** is the
cheapest credible answer: same YAML, no minute-billing, no vendor lock.

## 4. Recommended hybrid

1. **Local-first** — developers run `mcy --workspace . workflow run ci-local`
   before pushing; it is the same checks in ~2 minutes on one machine.
2. **Self-hosted runner** (Woodpecker, or GH runner on the pi) for PR
   automation, using the same `ci.yml` shape or the mycelium workflow invoked
   via `scripts/vm-inside-smoke.sh`.
3. **GitHub Actions as mirror only** — keep it for public signal (badge) once
   billing is healthy.

The point: the repo is never *blocked* on a paid CI again. The pipeline lives
in `workflows/ci-local.yaml` and runs with `mcy`.

## 5. Security notes for `run_command`

- **No shell.** Commands are `shlex.split` and executed as argv — shell
  metacharacters are inert (there's a test).
- **Allowlist.** Only executables in `[commands] allow` (default: uv, pytest,
  git, python, python3, node, npm, ollama, ruff, mypy) can run. Denials raise
  `PolicyViolation` and fail the workflow.
- **Workspace-scoped cwd.** `cwd` outside the workspace is denied.
- **Timeout.** 600s default, per-step override.
- **It is still `mutating=True`.** Read-only sessions and the agent tool list
  respect that: don't grant `run_command` to prompts you don't trust.
