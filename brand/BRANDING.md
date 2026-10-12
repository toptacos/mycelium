# Mycelium Brand Guidelines

Version 2.0 — October 2026 (psychedelic rebrand)

## 1. The name

**Mycelium** (my-SEE-lee-um) is the underground network of a fungus: the part
that grows, connects, shares nutrients, and learns from its environment. The
mushroom you see is just the fruiting body — a brief, visible surface of a much
larger living system.

That is the product. `mcy` is the mushroom you call on the command line; the
roots, threads, and memory live on your machine, where your data never leaves.

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
   ~39-second core test suite. Efficiency is a feature, not a compromise.

### Proof points (use these, in this order)

- 5 backends: local Ollama, OpenRouter, Gemini, DeepSeek, Anthropic
- 157 tests, 3-OS CI matrix, VM guides for Ubuntu/Fedora/Windows
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

## 4. Visual identity: bioluminescent psychedelia

The brand is **psychedelic meets terminal**: Fillmore poster saturation on a
near-black violet void, with bioluminescent glow. The visual says "trip"; the
docs say "measured on this machine". That tension is the identity.

### The mark: the badass mushroom

An animated spotted mushroom on the magenta→violet→cyan gradient:

- **Cap** carries the full spectrum gradient; spots are void-purple with cyan
  pupils (classic psychedelic iconography).
- **Stem** is cream fading to spore-amber, with a soft glow base.
- **Mycelium threads** in acid lime ripple at the base — the visible mushroom
  literally grows out of the network.
- **Spores** drift upward on a loop.
- **Motion**: the cap breathes (subtle scale), the glow pulses, threads
  ripple, spores rise. SMIL animations in the SVG masters; ANSI truecolor in
  the terminal.

Masters live in `brand/`:

| File | Use |
|---|---|
| `logo-mark.svg` | app icon, avatar, favicon source (animated) |
| `logo-horizontal.svg` | README header, site nav, slides |
| `social-card.svg` | OG/Twitter card (1200x630) |
| `favicon.svg` | browser tab (simplified, animated) |

Minimum size 16px (mark), 96px (horizontal lockup). Clear space equals the
height of one node on all sides. Do not rotate, recolors outside the palette,
add drop shadows, or place on busy imagery without the void backdrop.

### The terminal bloom

`mcy` opens with a ~1.4-second mushroom bloom: the cap grows in gradient rows,
the stem descends, threads spread, spores drift, and the gradient wordmark
`mycelium · plant it once, it grows` lands. It is **motion with manners**:

- TTY only — pipes, CI, and tests never see it.
- `--no-splash` flag or `MYCELIUM_NO_SPLASH=1` disables it.
- `--json` runs skip it so machine output stays clean.
- Implementation: `mycelium/splash.py` (frames are unit-tested).

### Palette

| Token | Hex | RGB | Use |
|---|---|---|---|
| Void | `#0B0014` | 11,0,20 | primary background, terminal base |
| Magenta | `#FF2E88` | 255,46,136 | gradient start, primary accent, links |
| Violet | `#8B2FC9` | 139,47,201 | gradient middle, panels |
| Cyan | `#22D3EE` | 34,211,238 | gradient end, spot pupils, focus |
| Lime | `#A3E635` | 163,230,53 | mycelium threads, success states |
| Amber | `#FBBF24` | 251,191,36 | spores, emphasis, CTAs |
| Cream | `#FFF3E2` | 255,243,226 | body text on dark, stem |

Dark-first, always. The product lives in a terminal; dark is the native
habitat. Accessibility: cream on void passes AAA; magenta on void passes AA
for large text; never use violet for body text on void (AA large only).

### Palette rules

- Gradients run **magenta → violet → cyan**, always in that order (hot to
  cold = growth direction).
- Lime and amber are **accents only** — never more than 15% of any surface.
- One glow source per composition.
- Terminal UI (rich tables, prompts) keeps its structure; do not fight rich's
  defaults, but new surfaces use the palette.

### Typography

- **Display / headings:** Space Grotesk (fallback: `ui-sans-serif, system-ui`)
- **Body:** Inter (fallback: system sans)
- **Code / terminal:** JetBrains Mono (fallback: `ui-monospace, SFMono-Regular`)

All three are open-licensed (OFL); the site self-hosts woff2 subsets. Terminal
output in marketing materials is always JetBrains Mono on Void.

## 5. Applications

- **CLI**: the bloom, then rich tables. Wordmark line under the final frame.
- **README**: horizontal lockup, max 240px wide.
- **Site**: dark hero with the animated mark, cast player, measured-numbers
  band. Never autoplay audio; casts autoplay only when in view.
- **Social cards**: `social-card.svg` template; headline in Space Grotesk,
  one metric in Fruiting Amber. Rasterize to PNG at 1200x630 for Twitter.
- **Swag / stickers**: the mark on Void; the mushroom face is the sticker.

## 6. Taglines (approved, in order)

1. Plant it once. It grows.
2. Your agent, grown local.
3. Roots in your machine. Reach into everything.
4. The network under your stack.
5. A 522MB model that scaffolds, researches, and remembers.

## 7. Brand misuses (the wall of shame)

- The mushroom in corporate blue, or on a white background without the void.
- The metaphor in every sentence — once per section, precisely.
- "Disrupting", "revolutionary", "10x", "magic".
- Cloning another project's palette while keeping our name.
- Any dark pattern in the bloom (it must be skippable, and it is).
