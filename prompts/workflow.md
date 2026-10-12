# workflow

**Task:** execute a multi-step YAML workflow end to end.

## Prompt

```
Run the 'release-notes' workflow (use run_workflow) with input repo_path='.'.

Requirements:
- Report which steps ran and their outputs
- The final markdown should be written to RELEASE_NOTES.md
```

## Success criteria

- workflow completed ok
- RELEASE_NOTES.md exists
- final message lists each step id with its outcome
