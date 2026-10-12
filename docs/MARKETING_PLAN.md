# Marketing Plan — mycelium v0.1 launch

Owner: marketing, toptacos · Window: 6 weeks from GitHub public launch · Budget: $0

## 1. Goal

Make "local-first agent workstation" a category people associate with mycelium.
Primary metric: 1,000 GitHub stars in 90 days. Secondary: 25 external mentions
(blogs, newsletters, podcasts), 500 casts played, 100 weekly `mcy doctor`
telemetry-free installs (proxy from the site is untracked; we measure via
release download counts + stars + referral links).

## 2. Audience (in priority order)

| Persona | Where they are | Hook |
|---|---|---|
| **The Tinkerer** — runs Ollama on a gaming PC or Mac, follows LocalLLaMA | r/LocalLLaMA, HN, Discord | "522MB model, 3 deps, your data" |
| **The Free-Setup Claude Code user** — read the ccr article, wants free agentic coding | Medium, X, dev.to | "mycelium replaces the router AND adds the loop" |
| **The Privacy-Minded Lead** — evaluated Copilot/Cursor, worried about code leaving | LinkedIn, security Slack groups | "containment over trust: no telemetry, workspace-scoped tools" |
| **The Automator** — n8n/Zapier user who wants programmable steps | n8n forum, indie hackers | "YAML workflows with checkpoints and resume" |

## 3. Positioning statement

For developers who want an agent that works *on their machine*, mycelium is a
local-first agent workstation that scaffolds, researches, writes, connects, and
remembers — because the visible command is a fruiting body; the network runs
under your stack.

## 4. Channel plan

### Owned (free)
- **mycelium.topta.co** — landing page, casts, docs. Deploy the `site/` directory
  to any static host (Netlify/Vercel/Pages). DNS: CNAME `mycelium.topta.co`.
- **GitHub** — repo is the product's home. Topics: `local-first`, `ai-agent`,
  `ollama`, `openrouter`, `workflow`, `llm-tools`, `typescript-free`.
  Good-first-issues labeled for contribution funnel.
- **README casts** — embedded asciinema players (already in `docs/SCREENCASTS.md`).

### Earned
- **Show HN** — post Tuesday 9am ET: "Show HN: Mycelium — a local-first agent
  workstation on a 522MB model". Lead with the honest latency number; HN rewards
  candor and punishes hype.
- **r/LocalLLaMA** — "I benchmarked a 522MB model doing real tool-calling work"
  (the benchmark table is the post, not an ad).
- **dev.to / Medium cross-post** — the five launch posts in `content/`
  (dogfooded: the tool wrote them).
- **Newsletters** — pitch TLDR AI, The Rundown AI, Ben's Bites with the
  "local-first vs subscription" angle.

### Paid (deferred)
No paid spend before 500 stars. If it happens: $300 X/Linkedwire test driving to
the landing page, not the repo.

## 5. Content calendar (weeks 1-6)

| Week | Asset | Channel |
|---|---|---|
| 1 | Launch post + Show HN + r/LocalLLaMA | HN, Reddit |
| 2 | "Mycelium vs Claude Code + ccr" (dogfooded) | dev.to, Medium |
| 3 | Cast playlist: 5 workflows in 5 minutes | site, X thread |
| 4 | "We tested 3 OSes in VMs" + CI matrix blog | LinkedIn |
| 5 | Competitor comparison page + benchmark thread | X, HN comments |
| 6 | v0.2.0 release notes + roadmap review | all |

## 6. Launch checklist

- [x] Repo private → flip public (after this document's owner signs off)
- [x] Casts recorded (site/casts/)
- [x] Landing page ready (site/)
- [x] LICENSE Apache-2.0
- [x] CONTRIBUTING + security contact
- [ ] DNS: mycelium.topta.co → static host
- [ ] og:image = brand/social-card.svg (rasterize to PNG for Twitter: 1200x630)
- [ ] GitHub repo description + topics
- [ ] 5 launch posts scheduled (content/)

## 7. Messaging do / don't

Do: measured numbers, "on this machine", explicit limits, the mycelium metaphor
used sparingly and precisely.
Don't: "10x faster than X" without a methodology link; "AGI-adjacent";
engaging in benchmark wars; the metaphor on every sentence — once per section.

## 8. Success review

Weekly: stars, forks, release downloads, referral clicks (utm on the install
one-liner), cast plays. Monthly: mentions audit, persona mix from issues/PRs.
