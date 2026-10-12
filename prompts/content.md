# content

**Task:** create a blog post draft and save it.

## Prompt

```
Create a blog post (kind=blog) about 'why local-first AI agents matter for
privacy'. Audience: backend developers. Tone: clear and practical. Max 500 words.

Requirements:
- Use create_content to draft and save it
- Then read it back with fs_read and verify it starts with an H1 heading
- Report the final word count
```

## Success criteria

- `content/why-local-first-ai-agents-matter-for-privacy-blog.md` exists
- word count under the 500 cap
- final message states path and word count
