from src.route_manager import router
from web.components.drawer import create_drawer, nav_state
from web.components.video_publishing import create_video_publishing_page


@router.register("/videos/publishing", "SEO, thumbnail & lên lịch")
def video_publishing_page():
    create_drawer()
    nav_state.set_active_route("/videos/publishing")
    create_video_publishing_page()
