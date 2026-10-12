from __future__ import annotations

from html.parser import HTMLParser
from typing import Any

from mycelium.tools import Tool, ToolContext

MAX_FETCH_BYTES = 5 * 1024 * 1024
MAX_PAGE_CHARS = 24000
USER_AGENT = "mycelium/0.1 (+local-first research agent)"


class _TextExtractor(HTMLParser):
    _SKIP = {"script", "style", "noscript", "template", "svg", "head"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._SKIP:
            self._skip_depth += 1
        if tag in (
            "p",
            "br",
            "li",
            "h1",
            "h2",
            "h3",
            "h4",
            "tr",
            "div",
            "section",
            "article",
        ):
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data.strip():
            self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    text = "".join(parser.parts)
    lines = [line.strip() for line in text.splitlines()]
    out: list[str] = []
    blank = False
    for line in lines:
        if line:
            out.append(line)
            blank = False
        elif not blank and out:
            out.append("")
            blank = True
    return "\n".join(out).strip()


async def research_web(args: dict[str, Any], ctx: ToolContext) -> str:
    import httpx

    url: str = args["url"]
    question: str = args.get("question") or "Summarize the key points of this page."
    if not url.startswith(("http://", "https://")):
        return f"error: url must start with http:// or https://, got {url!r}"

    async with httpx.AsyncClient(
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/json,text/plain,*/*",
        },
        follow_redirects=True,
        timeout=20.0,
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "json" in content_type:
            page_text = resp.text[:MAX_PAGE_CHARS]
        else:
            page_text = html_to_text(resp.text)[:MAX_PAGE_CHARS]

    if not page_text.strip():
        return f"error: no readable text content at {url}"

    if ctx.backend is None:
        return f"error: no backend configured for summarization"

    summary_messages = [
        {
            "role": "system",
            "content": "You are a precise research assistant. Answer strictly from the provided page text. If the page does not contain the answer, say so.",
        },
        {
            "role": "user",
            "content": f"Page URL: {url}\n\nPage text:\n{page_text}\n\nQuestion: {question}",
        },
    ]
    backend_name, model = ctx.settings.resolve_model(
        ctx.settings.strong_model
        and f"{ctx.settings.strong_backend}:{ctx.settings.strong_model}"
    )
    answer = await ctx.backend.chat(
        summary_messages, model=model or "qwen2.5-coder:latest"
    )

    return f"research: {url}\nquestion: {question}\npage_chars: {len(page_text)}\n\nanswer:\n{answer.content.strip()}"


def research_tool() -> Tool:
    return Tool(
        name="research_web",
        description=(
            "Fetch a web page (or JSON API endpoint) and answer a question about it using the local model. "
            "Returns a grounded answer plus page size stats. Requires network access."
        ),
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "http(s) URL to fetch"},
                "question": {
                    "type": "string",
                    "description": "What to answer from the page (default: summarize)",
                },
            },
            "required": ["url"],
        },
        handler=research_web,
        requires_net=True,
    )
