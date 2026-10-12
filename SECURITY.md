# Security Policy

## Supported versions

The latest minor release receives security fixes. 0.x is beta; expect breaking
changes in minors.

## Reporting a vulnerability

Email **security@topta.co** with:

- `mcy --version` output
- OS and Python version
- A minimal reproduction (prompt + config, with tokens redacted)

We acknowledge within 3 business days. Please do not open public issues for
security problems.

## Threat model summary

mycelium is a single-user local workstation. Controls are containment, not
multi-tenant isolation:

- Tools are workspace-scoped; path traversal and absolute escapes raise
  `PolicyViolation` before any write
- `read_only` removes mutating tools from the registry for the session
- `call_api` tokens are read from env vars at call time and never logged
- No shell execution except the scaffold's own test runner (180s timeout)
- No telemetry: the session log is a local JSONL file

Known gaps (documented in docs/ARCHITECTURE.md): model injection compliance is
untested at scale — the sandboxing controls do not depend on model behavior,
but a compromised model can still lie to you. MCP is not implemented.
