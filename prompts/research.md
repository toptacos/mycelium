# research

**Task:** fetch a web page, answer a question, save research notes.

## Prompt

```
Research the page at https://example.com and answer: what is this page for?

Steps:
- Use research_web to fetch and analyze the page
- Save your findings to research/example-com.md using fs_write
- Include the source URL in the notes
```

## Success criteria

- `research/example-com.md` exists with source URL, the answer, and key facts
- final message summarizes the answer in two sentences
