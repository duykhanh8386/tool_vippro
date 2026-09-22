from contextlib import contextmanager
from typing import Iterator, Optional

from nicegui import context, ui

from web.components.update_dialog import create_update_control


class NavigationState:
    def __init__(self, default_route: str = "/studio"):
        self.active_route = default_route
        self._default_route = default_route
        self._locks: dict[str, str] = {}
        self._default_lock_message = "Đang xử lý, vui lòng dừng trước khi chuyển trang."

    def lock(self, route: str, message: Optional[str] = None):
        self._locks[route] = message or self._default_lock_message

    def unlock(self, route: str):
        self._locks.pop(route, None)

    def blocking_message(self, current_route: str, target_route: str) -> Optional[str]:
        if current_route == target_route:
            return None
        return self._locks.get(current_route)

    def set_active_route(self, route: str):
        self.active_route = route
        ui.update()

    def reset_to_default(self):
        self.set_active_route(self._default_route)
        ui.navigate.to(self._default_route)


nav_state = NavigationState()


def _navigate(route: str) -> None:
    try:
        current_route = context.client.page.path
    except RuntimeError:
        current_route = nav_state.active_route
    message = nav_state.blocking_message(current_route, route)
    if message:
        ui.notify(message, type="warning")
        return
    nav_state.set_active_route(route)
    ui.navigate.to(route)


@contextmanager
def nav_item(route: str, label_text: str, icon_name: str) -> Iterator[None]:
    try:
        current_route = context.client.page.path
    except RuntimeError:
        current_route = nav_state.active_route
    active_class = (
        " app-nav-item--active" if current_route == route else ""
    )
    with ui.item().classes(f"app-nav-item{active_class}").on_click(
        lambda: _navigate(route)
    ):
        ui.icon(icon_name).classes("text-[19px]")
        ui.label(label_text).classes("w-full text-[13px]")
        yield


def create_drawer():
    with (
        ui.left_drawer(
            top_corner=True,
            fixed=True,
            bordered=False,
            elevated=False,
        )
        .props("width=220 persistent breakpoint=760")
        .classes("app-sidebar")
    ) as drawer:
        with ui.column().classes("app-sidebar-shell w-full h-full gap-0"):
            with ui.row().classes("app-brand w-full items-center gap-3"):
                with ui.element("div").classes("app-brand-mark"):
                    ui.image("/tuat-videos-assets/logo.png").classes(
                        "w-full h-full object-cover"
                    )
                with ui.column().classes("gap-0 min-w-0"):
                    ui.label("Tuất Videos").classes("app-brand-title")
                    ui.label("Operations workspace").classes("app-brand-copy")

            with ui.column().classes("w-full gap-0 flex-1"):
                ui.label("Tổng quan").classes("app-nav-label")
                with nav_item("/studio", "Tài khoản & kênh", "o_home"):
                    pass

                ui.label("Tác vụ").classes("app-nav-label")
                with nav_item("/audio/add", "Thêm audio", "o_library_music"):
                    pass
                with nav_item("/audio/remove", "Xóa audio", "o_layers_clear"):
                    pass
                with nav_item("/reup/delete-video", "Xóa - Back", "o_delete_sweep"):
                    pass

                ui.label("Quy trình").classes("app-nav-label")
                with nav_item("/audio/flow", "Thêm audio flow", "o_account_tree"):
                    pass
                with nav_item(
                    "/reup/delete-back-flow",
                    "Xóa Back flow",
                    "o_video_settings",
                ):
                    pass

            ui.separator().classes("bg-gray-200 mb-2")
            create_update_control()
            with (
                ui.row()
                .classes("app-account w-full items-center gap-2 cursor-pointer")
                .on("click", lambda: _navigate("/studio"))
            ):
                pass

    return drawer
