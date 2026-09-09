from src.route_manager import router
from web.components.drawer import create_drawer, nav_state
from web.components.youtube_mp3 import create_youtube_mp3_page


@router.register("/tools/youtube-mp3", "Download MP3 from YouTube")
def youtube_mp3_page():
    create_drawer()
    nav_state.set_active_route("/tools/youtube-mp3")
    create_youtube_mp3_page()
