# Mycelium Brand Guidelines

Version 1.0 — October 2026

## 1. The name

**Mycelium** (my-SEE-lee-um) is the underground network of a fungus: the part
that grows, connects, shares nutrients, and learns from its environment. The
mushroom you see is just the fruiting body — a brief, visible surface of a much
larger living system.

That is the product. `mcy` is the fruiting body you call on the command line;
the work happens underneath, on your machine, where your data never leaves.

### Why it fits (the canonical rationale)

| Product truth | Biological truth |
|---|---|
| Runs and learns locally | the network lives in the substrate; no central brain |
| Cross-system compatible | one network links different species across a forest |
| Connects third-party systems | mycorrhizal networks are literally connectors between organisms |
| Constantly learning | nutrients (information) flow across the network |
| Context-length conscious | the network recycles what it no longer needs — growth without choking the host |
| Lightweight (522MB model) | the largest organisms on Earth are built from threads |

### Usage

- First mention: **mycelium** (lowercase, even at sentence start in body copy;
  capitalize only in titles and the logo lockup).
- The command: `mcy` — always lowercase, always code-formatted.
- Domain: `mycelium.topta.co`
- Repo: `github.com/toptacos/mycelium`
- Never: "Mycelium.ai", "MyceliumAI", "the Mycelium platform". It is a tool,
  not a platform.

## 2. Positioning

**Category:** local-first agent workstation.
**One-liner:** A local-first agent workstation that scaffolds, researches,
writes, connects, and remembers — on your machine.
**Elevator:** Claude Code needs a router to reach a free model. Mycelium *is*
the router, the agent, the memory, and the workflow engine — running on your
hardware with a 522MB model.

### Messaging pillars (in priority order)

1. **Roots, not rentals.** Your agent lives on your machine. No subscription
   required to work; cloud backends are optional adapters, never the default.
2. **The network under your stack.** It connects to your APIs, your files, your
   workflows — the visible part is small; the working part is underneath.
3. **It remembers.** Memory, distilled sessions, and context budgeting mean the
   tenth run is better than the first.
4. **Small enough to actually run.** 522MB model, three runtime dependencies,
   ~26-second test suite. Efficiency is a feature, not a compromise.

### Proof points (use these, in this order)

- 5 backends: local Ollama, OpenRouter, Gemini, DeepSeek, Anthropic
- 139 tests, 3 OS matrix in CI, VM guides for Ubuntu/Fedora/Windows
- 5 sample-prompt scenarios with asserted artifacts
- Scaffolded app tests actually run and pass
- Proxy round-trip measured at 1.6s on CPU

## 3. Voice

- **Grounded, not hyped.** We say what a thing does. We never say
  "revolutionary", "magical", "10x", or "AI-powered" as a standalone claim.
- **A gardener's pragmatism.** Short sentences. Concrete nouns. Verbs that
  describe actual work: plant, grow, connect, recall, scaffold, run.
- **Honest about limits.** Small models need explicit tool naming. We say so.
  Measured numbers say "measured on this machine." Credibility is the brand.
- **First person plural, second person singular.** "We built" / "your machine".
  Never "the user" in marketing copy.

| Don't write | Write |
|---|---|
| "Leverage cutting-edge AI to supercharge your workflow" | "It runs on your laptop and remembers your project" |
| "The future of development is here" | "Plant it once. It grows." |
| "Seamlessly integrate with 3rd-party APIs" | "Point it at an API you already use" |

## 4. Logo

Masters live in `brand/`:

| File | Use |
|---|---|
| `logo-mark.svg` | app icon, avatar, favicon source |
| `logo-horizontal.svg` | README header, site nav, slides |
| `social-card.svg` | OG/Twitter card (1200x630) |
| `favicon.svg` | browser tab |

### Construction

An asymmetric node network (5 nodes, 6 curved edges) on a 64x64 grid. One
node — the *fruiting body* — is amber; the rest are hypha-green. Primary path
carries 3px weight; secondary hyphae 1.5px. Minimum size 16px (mark),
96px (horizontal lockup). Clear space equals the height of one node on all
sides. Do not rotate, recolor outside the palette, add effects, or place on
busy imagery without the ink backdrop.

## 5. Color

| Token | Hex | Use |
|---|---|---|
| Substrate Ink | `#0E1512` | primary dark background, terminal default |
| Deep Moss | `#1E3A2F` | cards, panels on dark |
| Hypha Green | `#58B368` | primary accent, links, focus rings |
| Spore White | `#F5F2E8` | primary light background, body text on dark |
| Fruiting Amber | `#E8B44A` | the highlighted node; emphasis; CTAs |
| Slate | `#5A6B62` | secondary text, captions |

Dark-first. The product lives in a terminal; dark is the native habitat.

## 6. Typography

- **Display / headings:** Space Grotesk (fallback: `ui-sans-serif, system-ui`)
- **Body:** Inter (fallback: system sans)
- **Code / terminal:** JetBrains Mono (fallback: `ui-monospace, SFMono-Regular`)

All three are open-licensed (OFL); the site self-hosts woff2 subsets. Terminal
output in marketing materials is always JetBrains Mono on Substrate Ink.

## 7. Applications

- **Terminal UI** (already shipped): rich tables, `mcy` prompt, event lines.
  Colors drift from the palette; do not fight it.
- **README header:** horizontal lockup, max 240px wide.
- **Site:** dark hero with the mark animating (nodes pulse along edges), then
  the cast player. Never autoplay audio; casts autoplay only when in view.
- **Social cards:** social-card.svg template; headline in Space Grotesk,
  one metric in Fruiting Amber.

## 8. Taglines (approved, in order)

1. Plant it once. It grows.
2. Your agent, grown local.
3. Roots in your machine. Reach into everything.
4. The network under your stack.
5. A 522MB model that scaffolds, researches, and remembers.
