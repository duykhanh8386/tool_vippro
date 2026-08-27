"""HTTP-only probe for the controlled UI smoke test."""

from __future__ import annotations

import json
import re

import requests


session = requests.Session()
session.trust_env = False
base_url = "http://127.0.0.2:8081"
pages = {}
local_assets = set()

for path in ("/", "/auth"):
    response = session.get(base_url + path, timeout=10, allow_redirects=False)
    title_match = re.search(r"<title>(.*?)</title>", response.text, re.I | re.S)
    references = sorted(
        set(re.findall(r'''(?:src|href)=["']([^"']+)["']''', response.text))
    )
    pages[path] = {
        "status": response.status_code,
        "content_type": response.headers.get("content-type"),
        "length": len(response.content),
        "title": title_match.group(1) if title_match else None,
        "references": references,
    }
    local_assets.update(ref for ref in references if ref.startswith("/"))

assets = []
for path in sorted(local_assets):
    response = session.get(base_url + path, timeout=10, allow_redirects=False)
    assets.append(
        {
            "url": path,
            "status": response.status_code,
            "content_type": response.headers.get("content-type"),
            "length": len(response.content),
        }
    )

print(json.dumps({"pages": pages, "assets": assets}, ensure_ascii=False, indent=2))
