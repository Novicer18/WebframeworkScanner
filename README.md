# FrameworkScanner

Lightweight async web stack fingerprinting script that discovers backend, frontend/CMS, and hosting clues by crawling a domain to a small depth.

## Features
- Async HTTP fetching with bounded concurrency for speed without overwhelming targets.
- Backend detection: Django, Laravel, Express, Rails, Spring, PHP, ASP.NET, Flask, FastAPI, NestJS.
- Frontend/CMS detection: React, Next.js, Angular, Vue/Nuxt, Svelte, jQuery, Tailwind, Bootstrap, WordPress, Shopify, Wix, Squarespace, Ghost.
- Hosting hints: Vercel, Cloudflare, Netlify, GitHub Pages, Firebase Hosting.
- Simple crawler that follows same-site links up to a chosen depth and reports per-URL findings.

## Requirements
- Python 3.9+
- Packages: `aiohttp`, `beautifulsoup4`, `rich`

Install deps:
```bash
pip install aiohttp beautifulsoup4 rich
```

## Usage
From the repository root:
```bash
python FrameworkScanner.py
```
Enter a starting URL (e.g., `https://example.com`). The script crawls to depth 2 by default.

### Adjustments
- Depth: change `max_depth` in the `scan_domain` call at the bottom of the script.
- Concurrency: tweak `CONCURRENCY_LIMIT` near the top to balance speed vs. server load.
- Timeouts: `REQUEST_TIMEOUT` controls per-request timeout.

## Output
For each fetched URL, the script prints status, detected backend, frontend/CMS, and hosting provider, e.g.:
```
✔ https://example.com  Status: 200
   Backend: Django
   Frontend/CMS: React
   Hosting: Cloudflare
```

## Notes
- Signatures are regex- and header-based heuristics; results are best-effort and may be incomplete or noisy.
- Crawler only follows links discovered in HTML `<a>` tags on the same origin pattern (absolute or root-relative).
- TLS verification is disabled for flexibility; enable SSL verification if you need stricter security.
