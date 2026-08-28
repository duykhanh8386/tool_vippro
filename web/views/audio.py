# RECOVERED: reconstructed from CPython 3.12 bytecode
from src.route_manager import router
from web.components.add_audio_flow import create_add_audio_flow_page
from web.components.audio import create_add_audio_page
from web.components.drawer import create_drawer, nav_state
from web.components.remove_audio import create_remove_audio_page


@router.register("/audio/add", "Add Audio")
def add_audio_page():
    create_drawer()
    nav_state.set_active_route("/audio/add")
    create_add_audio_page()


@router.register("/audio/flow", "Add Audio Flow")
def add_audio_flow_page():
    create_drawer()
    nav_state.set_active_route("/audio/flow")
    create_add_audio_flow_page()


@router.register("/audio/remove", "Remove Audio")
def remove_audio_page():
    create_drawer()
    nav_state.set_active_route("/audio/remove")
    create_remove_audio_page()
