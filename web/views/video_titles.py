from src.route_manager import router
from web.components.drawer import create_drawer, nav_state
from web.components.video_titles import create_video_titles_page


@router.register("/videos/titles", "Ghép nhạc & đổi tiêu đề")
def video_titles_page():
    create_drawer()
    nav_state.set_active_route("/videos/titles")
    create_video_titles_page()
