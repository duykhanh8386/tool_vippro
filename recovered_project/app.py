# RECOVERED: reconstructed from CPython 3.12 bytecode
import sys

from nicegui import ui

from src.route_manager import router
from web.nicegui_patches import apply_patches
from web.views import *

apply_patches()
router.setup_routes()

_is_frozen = getattr(sys, "frozen", False)

ui.run(
    title="TV Automation",
    favicon="https://github.com/bmtuan/UPLOADS/blob/main/TVAutomation.png?raw=true",
    port=8081,
    reconnect_timeout=120,
    reload=not _is_frozen,
)
