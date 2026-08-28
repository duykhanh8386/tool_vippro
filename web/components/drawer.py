# RECOVERED: reconstructed from CPython 3.12 bytecode
from contextlib import contextmanager
from typing import Optional
from nicegui import ui
from src.updater import updater_service


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


def _goto_settings():
    if nav_state.locked:
        ui.notify(nav_state.lock_message, type="warning")
        return
    nav_state.set_active_route("/settings")
    ui.navigate.to("/settings")


def create_drawer():
    refs = {"badge": None, "hint": None, "hint_label": None}

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

                    with nav_item("/settings", "Cài đặt", "settings"):
                        refs["badge"] = (
                            ui.badge("Mới", color="red")
                            .props("floating rounded")
                            .classes("text-[10px]")
                        )
                        refs["badge"].set_visibility(False)

            with ui.column().classes("w-full px-4 pb-4 gap-2 mt-auto"):
                ui.separator().classes("opacity-50")

                hint = (
                    ui.row()
                    .classes(
                        "items-center gap-2 w-full bg-green-50 border border-green-200 rounded-lg px-2 py-1.5 cursor-pointer hover:bg-green-100 transition-colors"
                    )
                    .on("click", _goto_settings)
                )

                with hint:
                    ui.icon("system_update").classes(
                        "text-green-600 text-base shrink-0"
                    )

                    with ui.column().classes("gap-0 flex-1 min-w-0"):
                        refs["hint_label"] = ui.label(
                            "Có bản cập nhật mới"
                        ).classes("text-xs font-semibold text-green-700 truncate")

                        ui.label("Nhấn để cập nhật").classes(
                            "text-[10px] text-green-600"
                        )

                hint.set_visibility(False)
                refs["hint"] = hint

                with ui.row().classes("items-center gap-1.5"):
                    ui.icon("verified").classes(
                        "text-gray-400 text-sm shrink-0"
                    )
                    ui.label("Phiên bản").classes("text-xs text-gray-400")
                    ui.label(updater_service.current_version).classes(
                        "text-xs font-mono font-medium text-gray-600 bg-gray-200 px-1.5 py-0.5 rounded"
                    )

    def _sync_update_indicator():
        show = updater_service.update_available()
        if refs["badge"]:
            refs["badge"].set_visibility(show)
        if refs["hint"]:
            refs["hint"].set_visibility(show)
        if show and refs["hint_label"] and updater_service.release_info:
            refs["hint_label"].set_text(
                f"Đã có v{updater_service.release_info['version']}"
            )

    _sync_update_indicator()
    ui.timer(2.0, _sync_update_indicator)

    ui.timer(0.3, updater_service.auto_check_once, once=True)

    @ui.page("/")
    def index():
        nav_state.reset_to_default()

    @ui.page("/{path}")
    def on_page(path: str = ""):
        route = f"/{path}"
        if not path:
            nav_state.reset_to_default()
            return
        nav_state.set_active_route(route)

    return drawer
