from __future__ import annotations

import re
from typing import Any

from mycelium.tools import Tool, ToolContext, resolve_in_workspace

CONTENT_KINDS = ("blog", "readme", "newsletter", "outline", "tutorial", "changelog")

_KIND_GUIDANCE = {
    "blog": "Write an engaging technical blog post with a hook, clear sections, code examples where useful, and a conclusion.",
    "readme": "Write a README.md with title, one-line pitch, install, usage, and development sections.",
    "newsletter": "Write a newsletter issue: short intro, 3-5 linked insights with commentary, one action item.",
    "outline": "Produce a hierarchical outline (H2/H3 bullets) with a one-line thesis per section. No prose paragraphs.",
    "tutorial": "Write a step-by-step tutorial with prerequisites, numbered steps, and verification commands.",
    "changelog": "Write a changelog entry grouped by Added/Changed/Fixed with user-facing phrasing.",
}


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "content"


async def create_content(args: dict[str, Any], ctx: ToolContext) -> str:
    kind = args.get("kind", "blog").strip().lower()
    if kind not in CONTENT_KINDS:
        return f"error: unknown kind {kind!r}; available: {', '.join(CONTENT_KINDS)}"
    topic: str = args["topic"].strip()
    audience = args.get("audience", "software developers").strip()
    tone = args.get("tone", "clear and practical").strip()
    max_words = int(args.get("max_words", 600))
    if not topic:
        return "error: topic is required"
    if ctx.backend is None:
        return "error: no backend configured for drafting"

    if max_words < 50:
        return "error: max_words must be at least 50"
    word_cap = min(3000, max_words)

    messages = [
        {
            "role": "system",
            "content": (
                f"You are a senior technical writer. {_KIND_GUIDANCE[kind]} "
                f"Audience: {audience}. Tone: {tone}. "
                f"Hard limit: {word_cap} words. Output markdown only, starting with an H1."
            ),
        },
        {"role": "user", "content": f"Topic: {topic}"},
    ]
    backend_name, model = ctx.settings.resolve_model(
        f"{ctx.settings.backend}:{ctx.settings.model}"
    )
    draft = await ctx.backend.chat(
        messages, model=model, temperature=0.6, max_tokens=min(4096, word_cap * 3)
    )
    body = draft.content.strip()
    if not body:
        return "error: model returned an empty draft"

    out_dir = resolve_in_workspace(ctx.workspace, "content")
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{_slugify(topic)}-{kind}.md"
    path = out_dir / filename
    header = f"---\ntitle: {topic}\nkind: {kind}\naudience: {audience}\ntone: {tone}\nmodel: {model}\nwords_cap: {word_cap}\n---\n\n"
    path.write_text(header + body + "\n", encoding="utf-8")

    rel = path.relative_to(ctx.workspace.resolve()).as_posix()
    word_count = len(body.split())
    return (
        f"created {rel} ({word_count} words, cap {word_cap})\n\npreview:\n{body[:400]}"
    )


def content_tool() -> Tool:
    return Tool(
        name="create_content",
        description=(
            "Draft a piece of content with the local model and save it to workspace content/<slug>-<kind>.md. "
            "Kinds: blog, readme, newsletter, outline, tutorial, changelog."
        ),
        parameters={
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": list(CONTENT_KINDS),
                    "default": "blog",
                },
                "topic": {"type": "string"},
                "audience": {"type": "string", "default": "software developers"},
                "tone": {"type": "string", "default": "clear and practical"},
                "max_words": {"type": "integer", "default": 600},
            },
            "required": ["topic"],
        },
        handler=create_content,
        mutating=True,
    )
