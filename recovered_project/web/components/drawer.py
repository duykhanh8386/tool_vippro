# RECOVERED: reconstructed from CPython 3.12 bytecode
from contextlib import contextmanager
from typing import Optional
from nicegui import ui


class NavigationState:
    def __init__(self, default_route: str = "/studio"):
        self.active_route = default_route
        self._default_route = default_route
        self.locked = False
        self.lock_message = "Đang xử lý, vui lòng dừng trước khi chuyển trang."

    def lock(self, message: Optional[str] = None):
        self.locked = True
        if message:
            self.lock_message = message

    def unlock(self):
        self.locked = False

    def set_active_route(self, route: str):
        self.active_route = route
        ui.update()

    def reset_to_default(self):
        self.set_active_route(self._default_route)
        ui.navigate.to(self._default_route)


nav_state = NavigationState()


@contextmanager
def nav_item(route: str, label_text: str, icon_name: str):
    is_active = nav_state.active_route == route

    base_classes = "cursor-pointer transition-all duration-300 rounded-lg flex items-center gap-3 bg-gray-100"
    hover_classes = "hover:bg-gray-100 hover:text-gray-900"

    if is_active:
        active_classes = (
            "bg-indigo-100 border-l-4 border-indigo-500 text-indigo-700 font-semibold"
        )
        icon_color = "text-indigo-500"
    else:
        active_classes = "text-gray-600"
        icon_color = "text-gray-600"

    def handle_click():
        if nav_state.locked:
            ui.notify(nav_state.lock_message, type="warning")
            return
        nav_state.set_active_route(route)
        ui.navigate.to(route)

    with ui.item().classes(
        f"{base_classes} {hover_classes} {active_classes} py-2 px-4 mx-2"
    ).on_click(handle_click):
        ui.icon(icon_name).classes(f"text-xl {icon_color}")
        ui.label(label_text).classes("w-full")
        yield


def create_drawer():
    with ui.left_drawer(
        top_corner=True,
        fixed=True,
        bordered=False,
        elevated=True,
    ).props("width=220 persistent").classes("bg-gray-50 shadow-lg") as drawer:

        with ui.column().classes("w-full h-full flex flex-col gap-0"):

            with ui.card().classes(
                "w-full bg-gradient-to-r from-indigo-500 to-green-600 mb-6 p-5 rounded-none"
            ):

                ui.label("TV Automation").classes(
                    "text-xl font-bold text-white text-center tracking-tight"
                )

            with ui.column().classes("w-full px-4 flex-1"):
                with ui.list().classes("w-full space-y-2"):
                    with nav_item("/studio", "Tài khoản", "account_circle"):
                        pass

                    task_routes = {
                        "/audio/add",
                        "/audio/remove",
                        "/reup/delete-video",
                    }

                    with ui.expansion(
                        "Tác vụ",
                        icon="task_alt",
                        value=nav_state.active_route in task_routes,
                    ).classes("w-full text-gray-700").props("dense-toggle"):
                        with nav_item("/audio/add", "Thêm Audio", "library_add"):
                            pass
                        with nav_item(
                            "/reup/delete-video", "Xóa - Back", "delete_sweep"
                        ):
                            pass
                        with nav_item("/audio/remove", "Xóa Audio", "delete"):
                            pass

                    flow_routes = {"/audio/flow", "/reup/delete-back-flow"}
                    with ui.expansion(
                        "Flow",
                        icon="account_tree",
                        value=nav_state.active_route in flow_routes,
                    ).classes("w-full text-gray-700").props("dense-toggle"):
                        with nav_item(
                            "/audio/flow", "Thêm Audio Flow", "music_video"
                        ):
                            pass
                        with nav_item(
                            "/reup/delete-back-flow",
                            "Xóa Back Flow",
                            "delete_forever",
                        ):
                            pass

    return drawer
