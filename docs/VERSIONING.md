# Versioning

mycelium follows **Semantic Versioning 2.0.0** and
[Conventional Commits](https://www.conventionalcommits.org/).

## Version format

`MAJOR.MINOR.PATCH`

- **MAJOR**: breaking changes to the CLI surface, config schema, tool schemas,
  or workflow YAML contract.
- **MINOR**: new backends, tools, commands, workflow features. Fully backward
  compatible.
- **PATCH**: fixes, docs, dependency bumps.

Pre-1.0 reality check: while `0.x`, MINOR bumps may include breaking changes to
newer surfaces. The five documented commands (`doctor`, `chat`, `run`,
`workflow`, `report`) and the config precedence rules are stable as of 0.1.0
and will not break within 0.x.

## What counts as the public API

Changing any of these requires a MAJOR bump (post-1.0) or an explicit note in
the changelog (0.x):

1. CLI commands and their flags
2. `mycelium.toml` keys and precedence
3. Tool names and parameter schemas (models are prompted with these)
4. Workflow YAML step schema
5. Proxy HTTP endpoints (`/v1/chat/completions`, `/v1/messages`)
6. Session log event names (consumed by `mcy report`)

Internal modules (agent loop internals, context heuristics) may change in any
PATCH.

## Commit convention

```
<type>(<scope>): <subject>

[optional body]

Refs: #123
```

Types: `feat`, `fix`, `perf`, `refactor`, `docs`, `test`, `build`, `ci`,
`chore`, `revert`. Breaking changes use `!` after the type and a
`BREAKING CHANGE:` footer.

Examples:

```
feat(tools): add fs_grep tool with glob filter
fix(backends): treat unknown model-prefix as part of the model name
feat(proxy)!: rename --ccr-port to --port-3456
```

Commit messages are validated in CI (` scripts/check-commits.sh` against
`git log` since the last tag) and by `scripts/release.sh check`.

## Release process

1. Update `CHANGELOG.md` (keep a `## [Unreleased]` section at all times).
2. `scripts/release.sh check` — tests, changelog, conventional-commit scan.
3. `scripts/release.sh tag 0.2.0` — updates `__init__.__version__`, commits,
   tags, pushes the tag.
4. GitHub Actions builds wheels/sdist and drafts a GitHub Release from the tag.

The version lives in exactly one place: `mycelium/__init__.py::__version__`.
`scripts/release.sh` rewrites it; nothing reads it at runtime.
