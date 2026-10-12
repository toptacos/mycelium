# The Branding Site

Source for **mycelium.topta.co** and its brand kit. Two static pages, no build
step, no framework, no JavaScript dependency for the core experience.

## Files

```
site/
├── index.html      the product landing page (hero, features, casts, numbers)
├── brand.html      the brand kit (logos, palette, typography, motion, rules)
├── assets/
│   ├── *.svg       animated logo masters (copied from ../brand/)
│   ├── png/...     rendered assets (og-image, banner, logo sizes, favicons)
│   ├── favicon.ico multi-res icon
│   └── casts/      asciinema v2 screencasts (.cast)
└── README.md       this file
```

## Deploy

Any static host works. The pages reference assets relatively, so deploying the
directory as-is is enough.

**Netlify / Vercel / Cloudflare Pages** — point at `site/` as the publish
directory, done.

**GitHub Pages** (branch `gh-pages`, or Actions):

```bash
# quick manual push
git subtree push --prefix site origin gh-pages
```

**DNS** — point `mycelium.topta.co` at the host (CNAME for Pages/Netlify).

**Cloudflare** (the org already uses it): Pages project → this repo, build
command empty, output directory `site/`.

## Local preview

```bash
cd site && python3 -m http.server 8080
# http://localhost:8080        — landing page
# http://localhost:8080/brand.html — brand kit
```

## Keeping assets in sync

`site/assets/` is a **copy** of `brand/`. After changing anything in `brand/`:

```bash
cp brand/*.svg site/assets/
cp brand/png/*.png site/assets/
```

Or re-render from scratch using the commands in `brand/ASSETS.md` §2.

## The casts

`site/casts/*.cast` are asciinema v2 files, played with the asciinema-player
(CDN in `index.html`). Re-record with:

```bash
bash scripts/record-all-casts.sh
```

The player script tag and theme are inline in `index.html`; if you self-host,
vendor `asciinema-player`'s CSS/JS into `assets/` and swap the URLs.

## Accessibility & performance notes

- Dark-only by design (brand guidelines forbid light backgrounds).
- Cream-on-void is the only body-text pairing (AAA); Magenta is for large text
  and accents (AA-large).
- Casts do not autoplay; only text plays by default.
- No fonts are downloaded from third-party CDNs in the static build — families
  are system fallbacks, self-host subsets for production.
- Everything is one HTML file per page; the largest asset is `og-image.png`
  (~130KB).

## Known gaps (launch checklist)

- [ ] Self-host woff2 subsets (Space Grotesk, Inter, JetBrains Mono)
- [ ] Vendor the asciinema-player locally (drop the jsdelivr CDN)
- [ ] `prefers-reduced-motion` handling for the bloom cast (cast 00)
- [ ] RSS/JSON-LD for SEO once the domain is live
