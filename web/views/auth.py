# RECOVERED: reconstructed from CPython 3.12 bytecode
from src.route_manager import router
from web.components.auth import create_auth_page


@router.register("/auth", "Auth")
def auth_page():
    create_auth_page()
