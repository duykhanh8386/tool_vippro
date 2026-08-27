"""Import-only smoke test for the approved third-party dependency roots."""

from __future__ import annotations

import importlib
import importlib.metadata
import json


PACKAGES = {
    "nicegui": "nicegui",
    "fastapi": "fastapi",
    "loguru": "loguru",
    "requests": "requests",
    "getmac": "getmac",
    "psutil": "psutil",
    "selenium": "selenium",
    "webdriver-manager": "webdriver_manager",
    "certifi": "certifi",
}


results: list[dict[str, str | bool]] = []
for distribution, import_root in PACKAGES.items():
    try:
        module = importlib.import_module(import_root)
        results.append(
            {
                "distribution": distribution,
                "import_root": import_root,
                "import_ok": True,
                "resolved_version": importlib.metadata.version(distribution),
                "module_file": str(getattr(module, "__file__", "")),
            }
        )
    except Exception as exc:
        results.append(
            {
                "distribution": distribution,
                "import_root": import_root,
                "import_ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
        )

print(json.dumps(results, ensure_ascii=False, indent=2))
raise SystemExit(0 if all(item["import_ok"] for item in results) else 1)
