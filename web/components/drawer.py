from contextlib import contextmanager
import time
from typing import Iterator, Optional

from nicegui import context, ui

from src.audio_recovery import (
    get_audio_recovery_runtime_status,
    get_channel_refresh_alerts,
)
from src.utils import get_channels_info
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


def _format_transfer_size(value: int) -> str:
    size = max(0.0, float(value or 0))
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


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

            recovery_alert_container = ui.column().classes("w-full gap-1")
            recovery_alert_state = {"signature": None}

            def refresh_recovery_alert() -> None:
                alerts = get_channel_refresh_alerts()
                signature = tuple(sorted(alerts))
                recovery_alert_container.clear()
                if not alerts:
                    recovery_alert_state["signature"] = None
                    return
                with recovery_alert_container:
                    with ui.card().classes(
                        "w-full p-2 bg-amber-50 border border-amber-300 shadow-none"
                    ):
                        ui.label(
                            f"YouTube thiếu token xác thực cho {len(alerts)} kênh. "
                            "Hãy đăng nhập và tải lại thông tin kênh."
                        ).classes("text-xs text-amber-900")
                        ui.button(
                            "Đăng nhập lại",
                            icon="refresh",
                            on_click=lambda: _navigate("/studio"),
                        ).props("flat dense").classes("text-amber-800")
                if recovery_alert_state["signature"] != signature:
                    ui.notify(
                        "Tự động khôi phục audio đang tạm dừng vì YouTube không "
                        "cấp token. Vui lòng đăng nhập và tải lại kênh.",
                        type="warning",
                        timeout=0,
                        close_button="Đóng",
                    )
                    recovery_alert_state["signature"] = signature

            refresh_recovery_alert()
            ui.timer(10.0, refresh_recovery_alert)

            recovery_activity_container = ui.column().classes("w-full gap-1")
            recovery_activity_state = {
                "notified_cycle": None,
                "was_active": False,
                "quota_signature": None,
            }
            recovery_channel_names: dict[str, str] = {}

            with ui.dialog() as recovery_detail_dialog, ui.card().classes(
                "w-[min(560px,calc(100vw-32px))] gap-3"
            ):
                with ui.row().classes("w-full items-center justify-between no-wrap"):
                    with ui.row().classes("items-center gap-2 no-wrap"):
                        ui.icon("manage_search").classes("text-blue-700 text-2xl")
                        ui.label("Chi tiết Auto audio").classes(
                            "text-lg font-semibold text-gray-800"
                        )
                    ui.button(icon="close", on_click=recovery_detail_dialog.close).props(
                        "flat round dense"
                    )

                recovery_detail_status = ui.label().classes(
                    "text-sm font-medium text-blue-800"
                )
                recovery_detail_progress = ui.linear_progress(value=0).props(
                    "rounded color=blue"
                ).classes("w-full")
                recovery_detail_transfer = ui.label().classes(
                    "text-xs text-gray-600"
                )

                with ui.grid(columns=1).classes(
                    "w-full gap-2 rounded-lg bg-gray-50 border border-gray-200 p-3"
                ):
                    ui.label("Kênh đang xử lý").classes(
                        "text-[11px] uppercase tracking-wide text-gray-500"
                    )
                    recovery_detail_channel_name = ui.label("—").classes(
                        "text-sm font-semibold text-gray-900 break-all select-text"
                    )
                    ui.label("Channel ID").classes(
                        "text-[11px] uppercase tracking-wide text-gray-500 mt-1"
                    )
                    recovery_detail_channel_id = ui.label("—").classes(
                        "text-xs font-mono text-gray-800 break-all select-text"
                    )
                    ui.label("Video ID đang add lại").classes(
                        "text-[11px] uppercase tracking-wide text-gray-500 mt-1"
                    )
                    recovery_detail_video_id = ui.label("—").classes(
                        "text-sm font-mono font-semibold text-gray-900 break-all select-text"
                    )
                    ui.label("Ngôn ngữ").classes(
                        "text-[11px] uppercase tracking-wide text-gray-500 mt-1"
                    )
                    recovery_detail_language = ui.label("—").classes(
                        "text-sm font-mono text-gray-800 break-all select-text"
                    )

                ui.label(
                    "Thông tin này tự cập nhật trong khi hộp thoại đang mở."
                ).classes("text-[11px] text-gray-500")

            def get_recovery_channel_name(channel_id: str) -> str:
                if not channel_id:
                    return "—"
                if channel_id not in recovery_channel_names:
                    try:
                        channel = get_channels_info(channel_id)
                        recovery_channel_names[channel_id] = str(
                            getattr(channel, "name", "") or channel_id
                        )
                    except Exception:
                        recovery_channel_names[channel_id] = channel_id
                return recovery_channel_names[channel_id]

            def refresh_recovery_details(status: dict) -> None:
                active = bool(status.get("active"))
                phase = str(status.get("phase") or "idle")
                channel_id = str(status.get("channel_id") or "") if active else ""
                video_id = str(status.get("video_id") or "") if active else ""
                language = str(status.get("language") or "") if active else ""

                recovery_detail_status.set_text(
                    str(status.get("message") or "Auto audio đang hoạt động")
                )
                recovery_detail_channel_name.set_text(
                    get_recovery_channel_name(channel_id)
                )
                recovery_detail_channel_id.set_text(channel_id or "—")
                recovery_detail_video_id.set_text(video_id or "—")
                recovery_detail_language.set_text(language or "—")

                if phase == "uploading" and active:
                    fraction = float(status.get("upload_fraction") or 0)
                    sent = int(status.get("upload_sent") or 0)
                    total = int(status.get("upload_total") or 0)
                    repair_index = int(status.get("repair_index") or 0)
                    repair_total = int(status.get("repair_total") or 0)
                    recovery_detail_progress.set_value(fraction)
                    recovery_detail_transfer.set_text(
                        f"Audio {repair_index}/{repair_total} · "
                        f"{_format_transfer_size(sent)} / {_format_transfer_size(total)}"
                    )
                elif active:
                    current = int(status.get("channel_index") or 0)
                    total = int(status.get("channel_total") or 0)
                    recovery_detail_progress.set_value(
                        current / total if phase == "scanning" and total else 0
                    )
                    recovery_detail_transfer.set_text(
                        f"Đang quét kênh {current}/{total}"
                        if phase == "scanning" and total
                        else (
                            "Đang đăng lại phụ đề còn thiếu"
                            if phase == "captioning"
                            else "Đang chuẩn bị audio để add lại"
                        )
                    )
                else:
                    recovery_detail_progress.set_value(0)
                    recovery_detail_transfer.set_text(
                        "Hiện không có video nào đang được add lại."
                    )

            def open_recovery_details() -> None:
                refresh_recovery_details(get_audio_recovery_runtime_status())
                recovery_detail_dialog.open()

            def refresh_recovery_activity() -> None:
                status = get_audio_recovery_runtime_status()
                active = bool(status.get("active"))
                phase = str(status.get("phase") or "idle")
                cycle_id = status.get("cycle_id")

                recovery_activity_container.clear()
                with recovery_activity_container:
                    if active:
                        with ui.card().classes(
                            "w-full p-2 bg-blue-50 border border-blue-200 shadow-none "
                            "cursor-pointer hover:bg-blue-100"
                        ).on("click", open_recovery_details):
                            with ui.row().classes("w-full items-center gap-2 no-wrap"):
                                ui.icon("sync").classes("text-blue-700 animate-spin")
                                ui.label(str(status.get("message") or "Đang tự động quét audio")) \
                                    .classes("text-xs font-semibold text-blue-900")

                            if phase == "uploading":
                                sent = int(status.get("upload_sent") or 0)
                                total = int(status.get("upload_total") or 0)
                                fraction = float(status.get("upload_fraction") or 0)
                                ui.linear_progress(value=fraction).props(
                                    "rounded color=blue"
                                ).classes("w-full mt-1")
                                ui.label(
                                    f"{_format_transfer_size(sent)} / {_format_transfer_size(total)}"
                                ).classes("text-[11px] text-blue-800")
                                ui.label(
                                    f"Video: {status.get('video_id') or '—'} · "
                                    f"Ngôn ngữ: {status.get('language') or '—'}"
                                ).classes("text-[10px] text-blue-700 break-all")
                            elif phase == "scanning":
                                current = int(status.get("channel_index") or 0)
                                total = int(status.get("channel_total") or 0)
                                fraction = current / total if total else 0
                                ui.linear_progress(value=fraction).props(
                                    "rounded color=blue"
                                ).classes("w-full mt-1")
                                ui.label(
                                    f"Kênh {current}/{total}" if total else "Đang đọc danh sách theo dõi..."
                                ).classes("text-[11px] text-blue-800")
                            else:
                                ui.linear_progress(value=0).props(
                                    "indeterminate rounded color=blue"
                                ).classes("w-full mt-1")
                                if status.get("video_id"):
                                    ui.label(
                                        f"Video: {status['video_id']}"
                                    ).classes("text-[10px] text-blue-700 break-all")
                            ui.label("Nhấp để xem Channel ID và Video ID").classes(
                                "text-[10px] text-blue-600 underline"
                            )
                    elif status.get("monitor_running"):
                        with ui.card().classes(
                            "w-full p-2 bg-emerald-50 border border-emerald-200 shadow-none "
                            "cursor-pointer hover:bg-emerald-100"
                        ).on("click", open_recovery_details):
                            with ui.row().classes("w-full items-center gap-2 no-wrap"):
                                ui.icon("verified").classes("text-emerald-700")
                                ui.label("Auto audio đang hoạt động").classes(
                                    "text-xs font-semibold text-emerald-900"
                                )
                            finished_at = status.get("last_cycle_finished_at")
                            if finished_at:
                                deferred_visibility = int(
                                    status.get("deferred_non_public") or 0
                                ) + int(
                                    status.get("deferred_visibility_unknown") or 0
                                )
                                ui.label(
                                    f"Lần quét cuối {time.strftime('%H:%M:%S', time.localtime(finished_at))} · "
                                    f"đã gửi lại {status.get('repaired', 0)}, "
                                    f"phụ đề {status.get('captions_repaired', 0)}, "
                                    f"hoãn {deferred_visibility} chưa công khai, "
                                    f"lỗi {int(status.get('failed', 0) or 0) + int(status.get('captions_failed', 0) or 0)}"
                                ).classes("text-[10px] text-emerald-800")
                            else:
                                ui.label("Đang chờ vòng quét đầu tiên").classes(
                                    "text-[10px] text-emerald-800"
                                )
                            ui.label("Nhấp để xem chi tiết").classes(
                                "text-[10px] text-emerald-700 underline"
                            )

                    quota_message = str(status.get("caption_quota_message") or "")
                    if quota_message:
                        with ui.card().classes(
                            "w-full p-2 bg-orange-50 border border-orange-300 shadow-none"
                        ):
                            with ui.row().classes("items-start gap-2 no-wrap"):
                                ui.icon("data_usage").classes("text-orange-700")
                                ui.label(quota_message).classes(
                                    "text-xs font-medium text-orange-900"
                                )

                refresh_recovery_details(status)

                if active and recovery_activity_state["notified_cycle"] != cycle_id:
                    ui.notify(
                        "Đang tự động quét và kiểm tra audio đã đăng ký...",
                        type="info",
                        timeout=3000,
                    )
                    recovery_activity_state["notified_cycle"] = cycle_id
                elif recovery_activity_state["was_active"] and not active:
                    repaired = int(status.get("repaired") or 0)
                    failed = int(status.get("failed") or 0)
                    captions_repaired = int(status.get("captions_repaired") or 0)
                    captions_failed = int(status.get("captions_failed") or 0)
                    if repaired or failed or captions_repaired or captions_failed:
                        ui.notify(
                            str(status.get("message") or "Đã hoàn tất tự động khôi phục audio"),
                            type=(
                                "positive"
                                if failed + captions_failed == 0
                                else "warning"
                            ),
                            timeout=5000,
                        )
                quota_message = str(status.get("caption_quota_message") or "")
                if (
                    quota_message
                    and recovery_activity_state["quota_signature"] != quota_message
                ):
                    ui.notify(
                        quota_message,
                        type="warning",
                        timeout=0,
                        close_button="Đóng",
                    )
                    recovery_activity_state["quota_signature"] = quota_message
                recovery_activity_state["was_active"] = active

            refresh_recovery_activity()
            ui.timer(1.0, refresh_recovery_activity)

            with ui.column().classes("w-full gap-0 flex-1"):
                ui.label("Tổng quan").classes("app-nav-label")
                with nav_item("/studio", "Tài khoản & kênh", "o_home"):
                    pass

                ui.label("Tác vụ").classes("app-nav-label")
                with nav_item("/audio/add", "Xóa & thêm audio", "o_library_music"):
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
