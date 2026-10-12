# CCR interop: the article's setup, with mycelium as the router

The Plain English article's core insight: **Claude Code doesn't care what model
is behind the API.** It talks to whatever base URL you point it at. The article
uses `claude-code-router` (ccr), a local proxy on port 3456 that translates
Claude's requests into whatever the backend model expects:

```
you -> claude -> CCR (local proxy :3456) -> OpenRouter/Gemini/DeepSeek -> free model
```

mycelium implements the same architecture natively (`mycelium/server.py`), plus
the agent/workflow/research/content features on top. Same contract, more
capability, no extra install.

## Drop-in replacement for ccr

```bash
# 1. start the proxy (CCR's port for a true drop-in)
uv run mcy serve --ccr-port          # listens on 127.0.0.1:3456

# 2. in another terminal, point Claude Code at it
export ANTHROPIC_BASE_URL="http://127.0.0.1:3456"
export ANTHROPIC_AUTH_TOKEN="local"  # dummy; the proxy intercepts everything
claude
```

The dummy token never leaves the machine. `ccr activate` does the same two
exports; with mycelium you write them yourself or alias them.

## Endpoint parity

| ccr / Claude Code expects | mycelium provides |
|---|---|
| `POST /v1/messages` (stream + non-stream) | yes, with `message_start`/`content_block_delta`/`message_delta`/`message_stop` SSE |
| `POST /v1/messages/count_tokens` | yes (token estimate) |
| `POST /v1/chat/completions` | yes (OpenAI clients, LibreChat, etc.) |
| `GET /v1/models` | yes (bare and `backend:model` ids) |
| mid-session model switch (`/model`) | `--model backend:model`, or `/model` in the REPL |

## Backend parity

The article's config maps directly onto mycelium's `[backends]`:

```toml
# OpenRouter (the article's pick): 30+ models, free daily limits
[backends.openrouter]
kind = "openai"
base_url = "https://openrouter.ai/api/v1"
api_key_env = "OPENROUTER_API_KEY"
models = ["qwen/qwen3-coder:free", "google/gemini-2.0-flash-exp:free"]

# Gemini
[backends.gemini]
kind = "gemini"
base_url = "https://generativelanguage.googleapis.com/v1beta"
api_key_env = "GOOGLE_API_KEY"

# DeepSeek (article notes: transformer "openai" — same here)
[backends.deepseek]
kind = "openai"
base_url = "https://api.deepseek.com/v1"
api_key_env = "DEEPSEEK_API_KEY"
```

And one the article doesn't cover, because ccr can't do it: **fully local**.

```toml
[backends.local]
kind = "ollama"
base_url = "http://127.0.0.1:11434"
# no key, no network
```

## What mycelium adds on top

| | ccr | mycelium |
|---|---|---|
| translate requests for Claude Code | yes | yes (same endpoints) |
| route by task (default/think/longContext) | config `Router` | `--model`, `/model`, per-backend defaults |
| agent loop with tools | no (Claude Code drives it) | yes (`mcy run`, `mcy chat`) |
| workflows with checkpoints | no | yes (`mcy workflow run --resume`) |
| persistent memory | no | yes (`mcy learn`, distilled sessions) |
| context compaction | no | yes (logged, with tokens reclaimed) |
| local models | possible | first-class (default backend) |

So you can run the article's setup with `mcy serve --ccr-port`, and when you
outgrow chat-only driving, the same process's siblings (`run`, `workflow`,
`learn`, `report`) are one command away — against the same backends.

## Troubleshooting parity

- *Claude connects to Anthropic anyway*: `ANTHROPIC_BASE_URL` not exported in
  that shell, or the proxy isn't running. `curl 127.0.0.1:3456/healthz`.
- *"API key not found"*: set the backend's `api_key_env` var and restart the
  proxy (it reads keys at request time for the proxy path, but Claude Code's
  own env must satisfy its client checks — hence the dummy
  `ANTHROPIC_AUTH_TOKEN`).
- *Rate limits*: switch models without restarting — `--model openrouter:<other>`
  at start, or a second proxy instance on another port.
- *Config changes*: restart the proxy. Config is read at startup.
