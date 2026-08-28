# RECOVERED: reconstructed from CPython 3.12 bytecode
from src.route_manager import router
from web.components.drawer import create_drawer, nav_state
from web.components.settings import create_settings_page


@router.register("/settings", "Cài đặt")
def settings_page():
    create_drawer()
    nav_state.set_active_route("/settings")
    create_settings_page()
