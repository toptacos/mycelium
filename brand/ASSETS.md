# Brand Assets

Thorough reference for every mycelium brand asset. Visual identity rules live in
[BRANDING.md](BRANDING.md); this file is about the **files** — what each one is,
where it's used, and how to regenerate derived formats.

## 1. Asset inventory

### SVG masters (animate)

| File | ViewBox | What it is | Primary uses |
|---|---|---|---|
| `logo-mark.svg` | 64×64 | the animated mushroom: cap gradient, spotted with cyan pupils, skirt-ringed stem, lime threads, drifting spores, breathing glow | app icon, avatar, favicon source, any web context ≥16px |
| `logo-horizontal.svg` | 300×64 | mark + gradient wordmark lockup | README header, site nav, slides, ≥96px wide |
| `wordmark.svg` | 340×72 | "mycelium" alone, gradient with a slow 8s pan | footers, merch, text lockups |
| `favicon.svg` | 64×64 | simplified mark on a rounded void tile (bolder shapes survive 16px) | browser tabs, PWA basics |
| `social-card.svg` | 1200×630 | full card: mark, wordmark, tagline, descriptor, command chips, install line | OG image source |
| `banner.svg` | 1280×640 | repo social banner with grid texture and glow fields | GitHub social preview |

All animation is SMIL (`<animate>`, `<animateTransform>`), so they animate
anywhere SVG renders — no CSS or JS required. Everything degrades gracefully:
a renderer that ignores SMIL shows the complete static mushroom.

### Anatomy of the mark (how to describe it consistently)

```
  .-~~~~~~~-.       cap gradient: magenta #FF2E88 → violet #8B2FC9 → cyan #22D3EE
.'   o o o   '.     4-5 spots: void-purple #0B0014 with cyan #22D3EE pupils
|    *   o*   o |    gill arcs under the cap edge (ink, 45% opacity)
 \     o    *  /     stem: cream #FFF3E2 → amber #FBBF24, skirt ring at mid-stem
   '-._____.-'        ground glow: lime #A3E635 radial at 35% opacity
    |     |           threads: lime, 3 branching tapered paths with nodes
   /       \
~ ~ ~ ~ ~ ~ ~        spores: amber particles, staggered rise+fade (2.8-4.4s)
                     aura: magenta radial glow, 3.4s breathe cycle
```

## 2. PNG renders (brand/png/)

Rendered from the SVG masters with cairosvg. Static (SMIL initial state = the
full mushroom). Use PNG wherever SVG can't render — OG images, installers,
email, print.

| File | Size | Use for |
|---|---|---|
| `og-image.png` | 1200×630 | **the** social card — Twitter/LinkedIn/Facebook read PNG, not SVG |
| `banner.png` | 1280×640 | repo social preview (GitHub reads PNG for og:image) |
| `logo-1024/512/256/128/64.png` | squares | app icons, installers, docs, splash fallbacks |
| `logo-horizontal-1024.png` | 1024×218 | headers where SVG isn't allowed |
| `wordmark-1024.png` | 1024×217 | text lockups in raster contexts |
| `favicon-16/32.png` | small | legacy browsers, tabs |
| `favicon.ico` | 16+32 multi | the Windows/browser default |

Regenerate everything after editing a master:

```bash
uv run --with cairosvg --with pillow python - <<'EOF'
import cairosvg
from pathlib import Path
brand = Path("brand"); png = brand / "png"; png.mkdir(exist_ok=True)
for src, dst, w in [
    ("logo-mark.svg", "logo-1024.png", 1024), ("logo-mark.svg", "logo-512.png", 512),
    ("logo-mark.svg", "logo-256.png", 256), ("logo-mark.svg", "logo-128.png", 128),
    ("logo-mark.svg", "logo-64.png", 64), ("favicon.svg", "favicon-32.png", 32),
    ("favicon.svg", "favicon-16.png", 16), ("social-card.svg", "og-image.png", 1200),
    ("banner.svg", "banner.png", 1280), ("logo-horizontal.svg", "logo-horizontal-1024.png", 1024),
    ("wordmark.svg", "wordmark-1024.png", 1024),
]:
    cairosvg.svg2png(url=str(brand / src), write_to=str(png / dst), output_width=w)
    print("rendered", dst)
EOF
# multi-res ico (needs ImageMagick):
convert brand/png/favicon-16.png brand/png/favicon-32.png brand/png/favicon.ico
```

Then refresh the site copies:

```bash
cp brand/png/{og-image,logo-512,logo-256,logo-64,favicon-32,favicon-16,favicon.ico,banner}.png site/assets/
cp brand/*.svg site/assets/
```

## 3. Palette tokens

| Token | Hex | RGB | Role |
|---|---|---|---|
| Void | `#0B0014` | 11,0,20 | background, terminal base |
| Magenta | `#FF2E88` | 255,46,136 | gradient start, links, primary accent |
| Violet | `#8B2FC9` | 139,47,201 | gradient middle, panels, borders |
| Cyan | `#22D3EE` | 34,211,238 | gradient end, spot pupils, focus |
| Lime | `#A3E635` | 163,230,53 | threads, success states |
| Amber | `#FBBF24` | 251,191,36 | spores, emphasis, CTAs |
| Cream | `#FFF3E2` | 255,243,226 | body text on dark, stem |
| Panel | `#1E0B36` | 30,11,54 | cards, chips on dark |
| Lavender (text) | `#C4B5FD` | 196,181,253 | secondary text on dark |

CSS variables (as used on the site):

```css
:root {
  --void: #0B0014; --magenta: #FF2E88; --violet: #8B2FC9; --cyan: #22D3EE;
  --lime: #A3E635; --amber: #FBBF24; --cream: #FFF3E2; --panel: #1E0B36;
}
```

Terminal truecolor (the bloom, `mycelium/splash.py`):

| Element | RGB |
|---|---|
| cap top | 255,46,136 |
| cap mid | 139,47,201 |
| cap bottom | 34,211,238 |
| spots pupils | 34,211,238 |
| stem | 255,243,226 |
| threads | 163,230,53 |
| spores | 251,191,36 |

## 4. Typography

| Role | Family | Weights | Fallback |
|---|---|---|---|
| Display | Space Grotesk | 600 | ui-sans-serif, system-ui |
| Body | Inter | 400/600 | system sans |
| Code | JetBrains Mono | 400 | ui-monospace, SFMono-Regular |

All OFL-licensed. The site loads them via system fallbacks in the static build;
self-host woff2 subsets for production.

## 5. Motion spec

| Motion | Where | Timing | Notes |
|---|---|---|---|
| breathe | cap + spots group | 2.9s | scale 1 → 1.045 / 0.955 |
| aura pulse | glow circle | 3.4s | r 22↔27, opacity .75↔1 |
| thread ripple | main thread path | 2.6s | quadratic control-point morph |
| spore drift | 6 amber particles | 2.8–4.4s, staggered | cy + fade, different rows |
| orbit | dot ring | 24s | full rotate, subtle |
| wordmark pan | wordmark gradient | 8s | x1 0→1→0 |
| CLI bloom | `mcy` startup | 1.4s total | 15 frames @100ms; see `mycelium/splash.py` |

Respect `prefers-reduced-motion` on the site: hold the final frame for users who
ask for less motion.

## 6. Where assets are consumed

| Consumer | Files it needs |
|---|---|
| Landing page (`site/index.html`) | `assets/logo-mark.svg`, `assets/og-image.png`, favicons |
| Brand kit (`site/brand.html`) | all SVG masters + `png/*` |
| README | `brand/logo-horizontal.svg` (or its PNG) |
| GitHub repo social | `brand/banner.png` (og:image), `brand/social-card.svg` (source) |
| Installer / terminal | `mycelium/splash.py` renders its own ANSI art (no SVG at runtime) |

## 7. Non-negotiables (the wall of shame)

- No light backgrounds. Ever.
- No rotation, hue shifts, drop shadows, or bevels on the mark.
- Gradients run magenta → violet → cyan in that order.
- One glow source per composition; lime and amber stay accents.
- The metaphor appears once per section in copy — not once per sentence.
- OG images ship as **PNG** (platforms don't render SVG cards).
