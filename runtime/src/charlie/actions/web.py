from __future__ import annotations

import re
from html import unescape
from urllib.parse import parse_qs, unquote, urlparse

import httpx

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
}


def _clean(text: str) -> str:
    text = unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text).strip()


def _unwrap(url: str) -> str:
    parsed = urlparse(url)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        uddg = parse_qs(parsed.query).get("uddg", [""])[0]
        if uddg:
            return unquote(uddg)
    return url


def search(query: str, limit: int = 5) -> str:
    if not query:
        raise RuntimeError("Missing search query.")
    response = httpx.post(
        "https://html.duckduckgo.com/html/",
        data={"q": query},
        headers=HEADERS,
        timeout=20.0,
        follow_redirects=True,
    )
    response.raise_for_status()
    hits = re.findall(
        r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        response.text,
        flags=re.I | re.S,
    )
    if not hits:
        hits = re.findall(r'href="(https?://[^"]+)"[^>]*class="result__a"[^>]*>(.*?)</a>', response.text, flags=re.I | re.S)
    lines: list[str] = []
    seen: set[str] = set()
    for href, title in hits:
        url = _unwrap(unescape(href))
        if url in seen or url.startswith("https://duckduckgo.com"):
            continue
        seen.add(url)
        lines.append(f"- {_clean(title)[:120]}\n  {url}")
        if len(lines) >= max(1, min(int(limit or 5), 8)):
            break
    return "\n".join(lines) or f"No web results for {query}."


def fetch(url: str) -> str:
    if not url:
        raise RuntimeError("Missing url.")
    if not str(url).lower().startswith(("http://", "https://")):
        raise RuntimeError("url must start with http:// or https://")
    response = httpx.get(url, headers=HEADERS, timeout=20.0, follow_redirects=True)
    response.raise_for_status()
    ctype = (response.headers.get("content-type") or "").lower()
    if "html" in ctype:
        text = _clean(re.sub(r"(?is)<script.*?>.*?</script>", " ", response.text))
        text = _clean(re.sub(r"(?is)<style.*?>.*?</style>", " ", text))
    else:
        text = response.text
    text = text.strip()
    if len(text) > 4000:
        text = text[:4000] + "\n[truncated]"
    return text or "(empty)"
