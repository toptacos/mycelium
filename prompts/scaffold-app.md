# scaffold-app

**Task:** scaffold a new application, run its tests, report results.

## Prompt

```
Scaffold a new Python CLI application called 'change-calculator' using the
python-cli template. Then run its test suite and report whether all tests pass.

Requirements:
- Use the scaffold_app tool with run_tests=true
- Report the final file tree and the test result
```

## Success criteria

- `apps/change-calculator/` exists with pyproject.toml, src/, tests/, README.md
- the scaffold's own test suite passes
- final message lists every created file and the test outcome
