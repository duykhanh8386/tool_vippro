# RECOVERED: reconstructed from CPython 3.12 bytecode
from src.route_manager import router
from web.components.drawer import create_drawer, nav_state
from web.components.delete_video import create_delete_video_page


@router.register("/reup/delete-video", "Xóa - Back")
def delete_video_page():
    create_drawer()
    nav_state.set_active_route("/reup/delete-video")
    create_delete_video_page()
