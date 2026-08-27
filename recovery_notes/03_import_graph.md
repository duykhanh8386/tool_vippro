# 03 — Import graph from recovered code

## Scope

This graph is derived only from import statements recovered from `app.pyc` and `src/route_manager.pyc`. It does not infer dependencies from filenames or from modules that were not analyzed in this step.

```text
app
├── [stdlib] sys
├── [third-party] nicegui.ui
├── [project-local] src.route_manager.router
│   └── route_manager
│       ├── [stdlib] inspect
│       ├── [stdlib] dataclasses.dataclass
│       ├── [stdlib] pathlib.Path
│       ├── [stdlib] typing.{Callable, Dict, Optional, Type, Union}
│       ├── [third-party] fastapi.Request
│       ├── [third-party] loguru.logger
│       ├── [third-party] nicegui.ui
│       └── [project-local] src.license_manager.{is_licensed, verify_license}
├── [project-local] web.nicegui_patches.apply_patches
└── [project-local] web.views.*
```

## Exact imports

### `app.py`

| Category | Import |
|---|---|
| Standard library | `import sys` |
| Third-party | `from nicegui import ui` |
| Project-local | `from src.route_manager import router` |
| Project-local | `from web.nicegui_patches import apply_patches` |
| Project-local | `from web.views import *` |

The star import is confirmed by the original constants tuple `('*',)` and Python 3.12 `CALL_INTRINSIC_1 2` (`IMPORT_STAR` behavior); it is not inferred from the module name.

### `src/route_manager.py`

| Category | Import |
|---|---|
| Standard library | `import inspect` |
| Standard library | `from dataclasses import dataclass` |
| Standard library | `from pathlib import Path` |
| Standard library | `from typing import Callable, Dict, Optional, Type, Union` |
| Third-party | `from fastapi import Request` |
| Third-party | `from loguru import logger` |
| Third-party | `from nicegui import ui` |
| Project-local | `from src.license_manager import is_licensed, verify_license` |

`license_manager.pyc` was not decompiled or otherwise analyzed in this step. Only the two imported identifiers exposed by `route_manager` are recorded.

## Runtime relationships visible in recovered code

- `app` calls `apply_patches()` and then `router.setup_routes()` before `ui.run(...)`.
- `RouterManager.is_authenticated()` delegates to project-local `is_licensed()`.
- `RouterManager.verify_activation_key()` delegates to project-local `verify_license(license_key)`.
- Route handlers use `fastapi.Request` for query parameters and NiceGUI for page registration/navigation.

These relationships are directly present in recovered bytecode/source; no additional dependency is assumed.
