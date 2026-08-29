# RECOVERED: reconstructed from CPython 3.12 bytecode
from src.route_manager import router
from web.components.delete_back_flow import create_delete_back_flow_page
from web.components.drawer import create_drawer, nav_state


@router.register("/reup/delete-back-flow", "Xóa Back Flow")
def delete_back_flow_page():
    create_drawer()
    nav_state.set_active_route("/reup/delete-back-flow")
    create_delete_back_flow_page()
