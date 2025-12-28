import asyncio
import re
from typing import Dict, Iterable, List, Set, Tuple

import aiohttp
from bs4 import BeautifulSoup
from rich import print
from rich.progress import Progress

# ---------------------------
# Backend fingerprint patterns
# ---------------------------
BACKEND_SIGS: Dict[str, List[str]] = {
    "Django": [r"csrftoken", r"sessionid"],
    "Laravel": [r"XSRF-TOKEN", r"laravel_session"],
    "Node.js / Express": [r"X-Powered-By: Express", r"express"],
    "Rails": [r"_rails_session"],
    "Spring": [r"JSESSIONID"],
    "PHP": [r"PHPSESSID", r"X-Powered-By: PHP", r"Set-Cookie: PHP"],
    "ASP.NET": [r"ASP.NET", r"ASPNET", r"ARRAffinity"],
    "Flask": [r"session=", r"flask"],
    "FastAPI": [r"fastapi"],
    "NestJS": [r"nestjs"],
}

# ---------------------------
# Frontend/CMS fingerprints
# ---------------------------
FRONTEND_SIGS: Dict[str, List[str]] = {
    "React": [r"react", r"__REACT_DEVTOOLS_GLOBAL_HOOK__", r"data-reactroot"],
    "Next.js": [r"_next/static", r"__NEXT_DATA__"],
    "Angular": [r"ng-version", r"_ngcontent"],
    "Vue.js": [r"vue"],
    "Nuxt.js": [r"nuxt", r"__NUXT__"],
    "Svelte": [r"svelte"],
    "jQuery": [r"jquery"],
    "TailwindCSS": [r"tailwind"],
    "Bootstrap": [r"bootstrap"],
}

CMS_SIGS: Dict[str, List[str]] = {
    "WordPress": [r"wp-content", r"wp-includes", r"X-Pingback"],
    "Shopify": [r"cdn.shopify.com", r"Shopify"],
    "Wix": [r"wixstatic", r"X-Wix-Request-Id"],
    "Squarespace": [r"squarespace"],
    "Ghost": [r"ghost"],
}

# ---------------------------
# Hosting platform signatures
# ---------------------------
HOSTING_PROVIDERS: Dict[str, List[str]] = {
    "Vercel": ["vercel", "server: Vercel"],
    "Cloudflare": ["cloudflare", "__cf_bm"],
    "Netlify": ["netlify"],
    "Github Pages": ["github.io"],
    "Firebase Hosting": ["firebaseapp.com", "firebase"],
}

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=12)
CONCURRENCY_LIMIT = 20
_fetch_semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)


async def fetch(session: aiohttp.ClientSession, url: str) -> Tuple[str, int, str, Dict[str, str]]:
    try:
        async with _fetch_semaphore:
            async with session.get(url, timeout=REQUEST_TIMEOUT, ssl=False) as resp:
                body = await resp.text(errors="ignore")
                return url, resp.status, body, dict(resp.headers)
    except Exception:
        return url, None, None, None


def extract_links(html: str, base_url: str) -> Set[str]:
    if not html:
        return set()
    soup = BeautifulSoup(html, "html.parser")
    links = set()

    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if href.startswith("http"):
            links.add(href)
        elif href.startswith("/"):
            links.add(base_url.rstrip("/") + href)

    return links


def detect_backend(headers: Dict[str, str], body: str) -> List[str]:
    results: List[str] = []
    header_str = "\n".join([f"{k}: {v}" for k, v in headers.items()]) if headers else ""

    for tech, patterns in BACKEND_SIGS.items():
        for pattern in patterns:
            if re.search(pattern, header_str, re.I) or (body and re.search(pattern, body, re.I)):
                results.append(tech)
                break
    return results


def detect_frontend(headers: Dict[str, str], body: str) -> List[str]:
    results: List[str] = []
    header_str = "\n".join([f"{k}: {v}" for k, v in headers.items()]) if headers else ""
    haystack = header_str + "\n" + (body or "")

    for tech, patterns in FRONTEND_SIGS.items():
        if any(re.search(p, haystack, re.I) for p in patterns):
            results.append(tech)

    for cms, patterns in CMS_SIGS.items():
        if any(re.search(p, haystack, re.I) for p in patterns):
            results.append(cms)

    return results


def detect_hosting(url: str, headers: Dict[str, str]) -> str:
    host = url.split("//")[-1].split("/")[0]
    header_str = "\n".join([f"{k}: {v}" for k, v in headers.items()]) if headers else ""

    for provider, patterns in HOSTING_PROVIDERS.items():
        for p in patterns:
            if p.lower() in host.lower() or p.lower() in header_str.lower():
                return provider
    return "Unknown"


async def scan_domain(start_url: str, max_depth: int = 1):
    visited = set()
    to_visit = {start_url}
    results = []

    connector = aiohttp.TCPConnector(ssl=False, limit=None)
    async with aiohttp.ClientSession(
        connector=connector,
        headers={"User-Agent": USER_AGENT},
    ) as session:
        for depth in range(max_depth):
            new_links = set()

            with Progress() as progress:
                task = progress.add_task(f"[cyan]Scanning depth {depth+1}...", total=len(to_visit))

                tasks = [fetch(session, url) for url in to_visit]
                responses = await asyncio.gather(*tasks)

                for url, status, body, headers in responses:
                    progress.advance(task)

                    if not status:
                        print(f"[red]❌ Failed: {url}")
                        continue

                    print(f"[green]✔ {url}[/green]  [white]Status:[/white] {status}")

                    backend = detect_backend(headers, body)
                    frontend = detect_frontend(headers, body)
                    hosting = detect_hosting(url, headers)

                    print(
                        f"   [yellow]Backend:[/yellow] {', '.join(backend) if backend else 'Unknown'}"
                    )
                    print(
                        f"   [cyan]Frontend/CMS:[/cyan] {', '.join(frontend) if frontend else 'Unknown'}"
                    )
                    print(f"   [magenta]Hosting:[/magenta] {hosting}\n")

                    results.append((url, status, backend, frontend, hosting))

                    for link in extract_links(body, start_url):
                        if link not in visited:
                            new_links.add(link)

                visited.update(to_visit)
                to_visit = new_links

    return results


if __name__ == "__main__":
    url = input("Enter domain (e.g. https://example.com): ").strip()
    asyncio.run(scan_domain(url, max_depth=2))
