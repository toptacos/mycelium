from __future__ import annotations

PROMPT_LIBRARY: dict[str, dict[str, str]] = {
    "scaffold-app": {
        "summary": "Scaffold a new application, run its tests, report results",
        "text": """# Sample prompt: scaffold an application

Scaffold a new Python CLI application called 'change-calculator' using the python-cli
template. Then run its test suite and report whether all tests pass.

Requirements:
- Use the scaffold_app tool with run_tests=true
- The app should parse CLI args (implement a --version flag in the template)
- Report the final file tree and the test result

Success criteria:
- apps/change-calculator/ exists with pyproject.toml, src/, tests/, README.md
- the scaffold's own test suite passes
- your final message lists every created file and the test outcome
""",
    },
    "research": {
        "summary": "Fetch a web page, answer a question, save research notes",
        "text": """# Sample prompt: research

Research the page at https://example.com and answer: what is this page for?

Steps:
- Use research_web to fetch and analyze the page
- Save your findings to research/example-com.md using fs_write
- Include the source URL and today's date in the notes

Success criteria:
- research/example-com.md exists and contains: source URL, the answer, and 3-5 key facts
- your final message summarizes the answer in two sentences
""",
    },
    "content": {
        "summary": "Create a blog post draft, save to content/",
        "text": """# Sample prompt: content creation

Create a blog post (kind=blog) about 'why local-first AI agents matter for privacy'.
Audience: backend developers. Tone: clear and practical. Max 500 words.

Requirements:
- Use create_content to draft and save it
- Then read it back with fs_read and verify it starts with an H1 heading
- Report the final word count

Success criteria:
- content/why-local-first-ai-agents-matter-for-privacy-blog.md exists
- word count is under the 500 cap
- final message states the path and word count
""",
    },
    "integration": {
        "summary": "Call a third-party API connection and summarize the response",
        "text": """# Sample prompt: third-party integration

Use call_api against the 'example' connection with method GET and path '/status'.
Summarize the response for me.

Requirements:
- The connection is already configured in mycelium.toml (do not hardcode any URL or token)
- Report the HTTP status and a one-paragraph interpretation of the payload

Success criteria:
- the call was made through the call_api tool
- final message contains the status code and interpretation
""",
    },
    "workflow": {
        "summary": "Execute a multi-step YAML workflow end to end",
        "text": """# Sample prompt: workflow execution

Run the 'release-notes' workflow (use run_workflow) with input repo_path='.'.

Requirements:
- Report which steps ran and their outputs
- The final markdown should be written to RELEASE_NOTES.md in the workspace

Success criteria:
- workflow completed ok
- RELEASE_NOTES.md exists
- final message lists each step id with its outcome
""",
    },
}
