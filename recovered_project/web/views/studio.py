# RECOVERED: reconstructed from CPython 3.12 bytecode
from src.route_manager import router
from web.components.drawer import create_drawer
from web.components.studio import create_studio_content


@router.register("/studio", "Studio")
def login_page():
    create_drawer()
    create_studio_content()
