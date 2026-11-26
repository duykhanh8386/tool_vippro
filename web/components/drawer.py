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


def _recovery_channel_summary(status: dict) -> str:
    active = int(status.get("active_channel_count") or 0)
    finished = int(status.get("completed_channel_count") or 0)
    total = int(status.get("channel_total") or 0)
    if status.get("continuous"):
        waiting = int(status.get("waiting_channel_count") or 0)
        passes = int(status.get("completed_pass_count") or 0)
        summary = f"Tổng {total} kênh · Đang xử lý {active} · Đã kết thúc {passes} lượt"
    else:
        waiting = max(0, total - active - finished)
        summary = f"Đang xử lý {active} kênh · Đã kết thúc lượt {finished}/{total} kênh"
    if waiting:
        summary += f" · Còn chờ {waiting} kênh"
    return summary


def _recovery_transfer_text(job: dict) -> str:
    if job.get("phase") == "preparing":
        return (
            f"Đã tạo {_format_transfer_size(job.get('preparation_bytes', 0))} · "
            f"{job.get('preparation_elapsed_seconds', 0)} giây"
        )
    if job.get("phase") != "uploading":
        return "—"
    if job.get("upload_studio_state") == "failed":
        return "YouTube báo không xử lý được · đã dừng gửi file"
    stage = {
        "deleting": "Đang xóa track cần thay lại",
        "authenticating": "Đang xác thực",
        "starting": "Đang mở phiên tải",
        "registering": "Đang xuất bản track",
        "finalizing": "Đang hoàn tất tải file",
        "verifying": "Đang kiểm tra track trên YouTube",
        "retrying": "Đang thử tải lại",
        "complete": "Đã gửi file",
        "error": "Tải file lỗi",
    }.get(job.get("upload_status"), "Đang gửi file")
    if job.get("upload_status") == "complete":
        stage = {
            "processing": "YouTube đã nhận, đang xử lý",
            "published": "Đã xuất bản",
        }.get(job.get("upload_studio_state"), stage)
    sent = int(job.get("upload_sent") or 0)
    total = int(job.get("upload_total") or 0)
    fraction = float(job.get("upload_fraction") or 0)
    return f"{stage} · {fraction:.0%} · {_format_transfer_size(sent)} / {_format_transfer_size(total)}"


def _recovery_studio_text(job: dict) -> str:
    """Describe observed server state separately from local byte progress."""
    if job.get("phase") != "uploading":
        return "—"
    state = job.get("upload_studio_state")
    if state == "failed":
        return "Không xử lý được"
    if state == "published":
        return "Đã xuất bản"
    if state == "processing":
        return "Đang xử lý" if job.get("upload_status") == "complete" else "Đang chờ nhận đủ file"
    return "Chưa xác nhận trạng thái"


def _navigate(route: str) -> None:
    target_path = route.split("?", 1)[0]
    try:
        current_route = context.client.page.path
    except RuntimeError:
        current_route = nav_state.active_route
    message = nav_state.blocking_message(current_route, target_path)
    if message:
        ui.notify(message, type="warning")
        return
    nav_state.set_active_route(target_path)
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

            recovery_alert_container = ui.column().classes("w-full gap-1.5 mt-2")
            recovery_alert_state = {"signature": None}
            recovery_alert_channel_names: dict[str, str] = {}

            with ui.dialog() as recovery_alert_dialog, ui.card().classes(
                "gap-3"
            ).style(
                "width: min(640px, calc(100vw - 32px)); max-width: calc(100vw - 32px)"
            ):
                with ui.row().classes("w-full items-center justify-between no-wrap"):
                    with ui.row().classes("items-center gap-2 no-wrap"):
                        ui.icon("warning_amber").classes("text-bad text-2xl")
                        ui.label("Cảnh báo session token kênh").classes(
                            "text-title-xs text-ink"
                        )
                    ui.button(icon="close", on_click=recovery_alert_dialog.close).props(
                        "flat round dense"
                    )
                recovery_alert_dialog_summary = ui.label().classes(
                    "text-body-s text-subtitle"
                )
                recovery_alert_dialog_list = ui.column().classes(
                    "w-full gap-2 max-h-80 overflow-y-auto"
                )
                with ui.row().classes("w-full justify-end gap-2 mt-1"):
                    ui.button("Đóng", on_click=recovery_alert_dialog.close).classes(
                        "app-button-secondary"
                    )
                    ui.button(
                        "Load lại đúng kênh lỗi",
                        icon="refresh",
                        on_click=lambda: (
                            recovery_alert_dialog.close(),
                            _navigate("/studio?reload_alerts=1"),
                        ),
                    ).classes("app-button-primary")

            def recovery_alert_channel_name(
                channel_id: str, alert: dict
            ) -> str:
                stored_name = str(alert.get("channel_name") or "").strip()
                if stored_name:
                    return stored_name
                if channel_id not in recovery_alert_channel_names:
                    try:
                        channel = get_channels_info(channel_id)
                        recovery_alert_channel_names[channel_id] = str(
                            getattr(channel, "name", "") or channel_id
                        )
                    except Exception:
                        recovery_alert_channel_names[channel_id] = channel_id
                return recovery_alert_channel_names[channel_id]

            def recovery_alert_time(alert: dict) -> str:
                try:
                    requested_at = float(alert.get("requested_at") or 0)
                except (TypeError, ValueError):
                    requested_at = 0
                if requested_at <= 0:
                    return "Không rõ thời điểm"
                return time.strftime(
                    "%d/%m/%Y %H:%M:%S", time.localtime(requested_at)
                )

            def refresh_recovery_alert() -> None:
                alerts = get_channel_refresh_alerts()
                signature = tuple(
                    sorted(
                        (
                            channel_id,
                            alert.get("requested_at"),
                            alert.get("severity"),
                        )
                        for channel_id, alert in alerts.items()
                    )
                )
                recovery_alert_container.clear()
                if not alerts:
                    recovery_alert_state["signature"] = None
                    return
                has_validation_error = any(
                    alert.get("severity") == "error"
                    or alert.get("validation_failed")
                    for alert in alerts.values()
                )
                pill_tone = "app-sidebar-pill--bad" if has_validation_error else "app-sidebar-pill--warn"
                recovery_alert_dialog_summary.set_text(
                    f"YouTube chưa cấp session token cho {len(alerts)} kênh."
                )
                recovery_alert_dialog_list.clear()
                with recovery_alert_dialog_list:
                    for channel_id, alert in sorted(alerts.items()):
                        is_error = bool(
                            alert.get("severity") == "error"
                            or alert.get("validation_failed")
                        )
                        detail_classes = (
                            "w-full gap-1 rounded-card border border-bad-line bg-bad-soft p-3"
                            if is_error
                            else "w-full gap-1 rounded-card border border-warn-line bg-warn-soft p-3"
                        )
                        with ui.column().classes(detail_classes):
                            ui.label(
                                recovery_alert_channel_name(channel_id, alert)
                            ).classes(
                                "text-body-s font-semibold break-all "
                                + ("text-bad" if is_error else "text-warn")
                            )
                            ui.label(f"ID: {channel_id}").classes(
                                "text-label-m font-mono break-all select-text text-body"
                            )
                            ui.label(
                                f"Lỗi lúc: {recovery_alert_time(alert)}"
                            ).classes("text-label-m text-muted")
                            if is_error:
                                ui.label(
                                    "Kiểm tra session token thất bại sau khi load lại."
                                ).classes("text-label-m font-medium text-bad")

                with recovery_alert_container:
                    with ui.column().classes(
                        f"app-sidebar-pill app-sidebar-pill--clickable {pill_tone} gap-1"
                    ).on("click", recovery_alert_dialog.open):
                        with ui.row().classes("w-full items-center gap-1.5 no-wrap"):
                            ui.icon(
                                "error_outline" if has_validation_error else "warning_amber"
                            ).classes("text-base shrink-0")
                            ui.label(
                                f"Token lỗi · {len(alerts)} kênh"
                            ).classes("text-label-m font-semibold truncate")
                            ui.icon("chevron_right").classes(
                                "text-base shrink-0 ml-auto opacity-70"
                            )
                        ui.label("Nhấp xem chi tiết kênh lỗi").classes("text-2xs opacity-80")
                        ui.button(
                            "Load lại kênh lỗi",
                            icon="refresh",
                            on_click=lambda: _navigate("/studio?reload_alerts=1"),
                        ).props("flat dense no-caps size=sm").classes(
                            "self-start px-1 text-label-m font-semibold "
                            + ("text-bad" if has_validation_error else "text-warn")
                        ).on("click.stop", lambda: None)
                if recovery_alert_state["signature"] != signature:
                    ui.notify(
                        "Kiểm tra session token thất bại; xem tên và Channel ID "
                        "trong cảnh báo."
                        if has_validation_error
                        else "Tự động khôi phục audio đang tạm dừng vì YouTube không "
                        "cấp token. Vui lòng đăng nhập và tải lại đúng kênh lỗi.",
                        type="negative" if has_validation_error else "warning",
                        timeout=0,
                        close_button="Đóng",
                    )
                    recovery_alert_state["signature"] = signature

            refresh_recovery_alert()
            ui.timer(10.0, refresh_recovery_alert)

            recovery_activity_container = ui.column().classes("w-full gap-1")
            recovery_activity_state = {
                "notified_start": False,
                "was_active": False,
                "quota_signature": None,
            }
            recovery_channel_names: dict[str, str] = {}

            with ui.dialog() as recovery_detail_dialog, ui.card().classes(
                "gap-3"
            ).style(
                "width: min(1000px, calc(100vw - 32px)); max-width: calc(100vw - 32px)"
            ):
                with ui.row().classes("w-full items-center justify-between no-wrap"):
                    with ui.row().classes("items-center gap-2 no-wrap"):
                        ui.icon("manage_search").classes("text-info text-2xl")
                        ui.label("Chi tiết Auto audio").classes(
                            "text-title-xs text-ink"
                        )
                    ui.button(icon="close", on_click=recovery_detail_dialog.close).props(
                        "flat round dense"
                    )

                recovery_detail_status = ui.label().classes(
                    "text-body-s font-medium text-info"
                )
                recovery_detail_summary = ui.label().classes("text-label-m text-subtitle")
                recovery_detail_capacity = ui.label().classes("text-label-m text-muted")
                ui.label("Kênh trong lượt quét").classes("text-label-m font-medium text-subtitle")
                recovery_channel_table = ui.table(
                    columns=[
                        {"name": "name", "label": "Kênh", "field": "name", "classes": "whitespace-normal"},
                        {"name": "channel_id", "label": "Channel ID", "field": "channel_id", "classes": "font-mono select-text"},
                        {"name": "video_id", "label": "Video ID", "field": "video_id", "classes": "font-mono select-text"},
                        {"name": "language", "label": "Ngôn ngữ", "field": "language"},
                        {"name": "pass_index", "label": "Lượt quét", "field": "pass_index"},
                        {"name": "message", "label": "Tiến độ / Kết quả", "field": "message", "classes": "whitespace-normal", "style": "min-width: 200px; max-width: 350px"},
                        {"name": "transfer", "label": "Tiến độ file", "field": "transfer", "style": "min-width: 240px"},
                        {"name": "studio", "label": "Trạng thái YouTube", "field": "studio", "style": "min-width: 180px"},
                    ],
                    rows=[], row_key="channel_id",
                ).props("dense flat").classes("w-full")
                recovery_channel_table.add_slot("body-cell-transfer", '''
                    <q-td :props="props">
                        <div v-if="props.row.phase === 'uploading'" class="column q-gutter-xs">
                            <q-linear-progress rounded color="info" size="8px"
                                :value="props.row.upload_fraction || 0"
                                :indeterminate="['deleting', 'authenticating', 'starting', 'registering', 'verifying'].includes(props.row.upload_status)" />
                            <span>{{ props.row.transfer }}</span>
                        </div>
                        <span v-else>{{ props.row.transfer }}</span>
                    </q-td>
                ''')
                recovery_channel_table.add_slot("body-cell-studio", '''
                    <q-td :props="props">
                        <span :class="props.row.upload_studio_state === 'failed' ? 'text-negative' : ''">
                            {{ props.row.studio }}
                        </span>
                        <div v-if="props.row.upload_track_id" class="text-caption text-grey-7">
                            {{ props.row.upload_track_id }}
                        </div>
                    </q-td>
                ''')
                recovery_channel_table.add_slot("body-cell-message", '''
                    <q-td :props="props" style="min-width: 200px; max-width: 350px; white-space: normal">
                        <div>{{ props.row.message }}</div>
                        <div v-if="props.row.last_error" class="text-caption text-negative">
                            Lỗi gần nhất: {{ props.row.last_error }}
                        </div>
                    </q-td>
                ''')
                recovery_detail_progress = ui.linear_progress(value=0, show_value=False, size="12px").props(
                    "rounded color=info"
                ).classes("w-full")
                recovery_detail_transfer = ui.label().classes(
                    "text-label-m text-subtitle"
                )

                with ui.grid(columns=1).classes(
                    "w-full gap-2 rounded-card bg-sunken border border-line p-3"
                ):
                    ui.label("Kênh đang xử lý").classes(
                        "text-label-s uppercase tracking-wide text-muted"
                    )
                    recovery_detail_channel_name = ui.label("—").classes(
                        "text-body-s font-semibold text-ink break-all select-text"
                    )
                    ui.label("Channel ID").classes(
                        "text-label-s uppercase tracking-wide text-muted mt-1"
                    )
                    recovery_detail_channel_id = ui.label("—").classes(
                        "text-label-m font-mono text-body break-all select-text"
                    )
                    ui.label("Video ID đang add lại").classes(
                        "text-label-s uppercase tracking-wide text-muted mt-1"
                    )
                    recovery_detail_video_id = ui.label("—").classes(
                        "text-body-s font-mono font-semibold text-ink break-all select-text"
                    )
                    ui.label("Ngôn ngữ").classes(
                        "text-label-s uppercase tracking-wide text-muted mt-1"
                    )
                    recovery_detail_language = ui.label("—").classes(
                        "text-body-s font-mono text-body break-all select-text"
                    )

                ui.label(
                    "Thông tin này tự cập nhật trong khi hộp thoại đang mở."
                ).classes("text-label-m text-muted")

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
                recovery_detail_summary.set_text(_recovery_channel_summary(status))
                recovery_detail_capacity.set_text(
                    f"Tối đa {status.get('channel_concurrency', 3)} kênh cùng lúc. "
                    "Mỗi kênh có tiến độ file riêng; kết quả giữ lại cả lỗi và lý do tạm hoãn."
                )
                recovery_channel_table.update_rows([
                    {
                        **job,
                        "name": get_recovery_channel_name(job["channel_id"]),
                        "transfer": _recovery_transfer_text(job),
                        "studio": _recovery_studio_text(job),
                    }
                    for job in status.get("channels", []) if active
                ] + [
                    {
                        **result,
                        "pass_index": result.get("pass_count", 1),
                        "name": get_recovery_channel_name(result["channel_id"]),
                        "video_id": "—", "language": "—", "transfer": "—", "studio": "—",
                    }
                    for result in status.get("channel_results", [])
                ])
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

                recovery_detail_progress.props(remove="indeterminate")
                if phase == "uploading" and active:
                    fraction = float(status.get("upload_fraction") or 0)
                    repair_index = int(status.get("repair_index") or 0)
                    repair_total = int(status.get("repair_total") or 0)
                    recovery_detail_progress.set_value(fraction)
                    recovery_detail_transfer.set_text(
                        f"{get_recovery_channel_name(channel_id)} · Audio {repair_index}/{repair_total} · "
                        f"{_recovery_transfer_text(status)}"
                    )
                elif phase == "preparing" and active:
                    recovery_detail_progress.props("indeterminate")
                    recovery_detail_transfer.set_text(
                        f"{status.get('message', '')} · "
                        f"Đã tạo {_format_transfer_size(status.get('preparation_bytes', 0))} · "
                        f"{status.get('preparation_elapsed_seconds', 0)} giây"
                    )
                elif phase == "captioning" and active:
                    recovery_detail_progress.set_value(0)
                    recovery_detail_transfer.set_text(
                        "Đang kiểm tra và add lại phụ đề có trạng thái failed"
                    )
                elif active:
                    current = int(status.get("completed_channel_count") or 0)
                    total = int(status.get("channel_total") or 0)
                    recovery_detail_progress.set_value(
                        current / total if phase == "scanning" and total else 0
                    )
                    recovery_detail_transfer.set_text(
                        _recovery_channel_summary(status) if status.get("continuous") else
                        f"Đã hoàn tất {current}/{total} kênh"
                        if phase == "scanning" and total
                        else "Đang chuẩn bị audio để add lại"
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
                processing_warning_count = int(status.get("processing_warning_count") or 0)

                recovery_activity_container.clear()
                with recovery_activity_container:
                    if active:
                        title_text = (
                            "Đang tắt Auto Registry..."
                            if not status.get("enabled", True)
                            else str(status.get("message") or "Đang tự động quét audio")
                        )
                        with ui.column().classes(
                            "app-sidebar-pill app-sidebar-pill--info app-sidebar-pill--clickable gap-1.5 mt-1"
                        ).on("click", open_recovery_details).tooltip(
                            "Nhấp để xem Channel ID và Video ID"
                        ):
                            with ui.row().classes("w-full items-center gap-1.5 no-wrap"):
                                ui.icon("sync").classes("animate-spin text-base shrink-0")
                                ui.label(title_text).classes(
                                    "text-label-m font-semibold leading-tight truncate"
                                )
                                ui.icon("chevron_right").classes(
                                    "text-base shrink-0 ml-auto opacity-70"
                                )
                            if phase == "uploading":
                                fraction = float(status.get("upload_fraction") or 0)
                                ui.linear_progress(
                                    value=fraction, show_value=False, size="4px"
                                ).props("rounded color=info").classes("w-full")
                                summary_text = f"{fraction:.0%} · {status.get('video_id') or '—'}"
                            elif phase == "scanning":
                                current = int(status.get("completed_channel_count") or 0)
                                total = int(status.get("channel_total") or 0)
                                fraction = current / total if total else 0
                                ui.linear_progress(
                                    value=fraction, show_value=False, size="4px"
                                ).props("rounded color=info").classes("w-full")
                                summary_text = _recovery_channel_summary(status)
                            else:
                                ui.linear_progress(
                                    value=0, show_value=False, size="4px"
                                ).props("indeterminate rounded color=info").classes("w-full")
                                summary_text = (
                                    f"Video: {status['video_id']}"
                                    if status.get("video_id")
                                    else _recovery_channel_summary(status)
                                )
                            ui.label(summary_text).classes("text-2xs truncate w-full opacity-85")
                    elif not status.get("enabled", True):
                        with ui.row().classes(
                            "app-sidebar-pill app-sidebar-pill--neutral items-center gap-1.5 no-wrap mt-1"
                        ):
                            ui.icon("pause_circle_outline").classes("text-base shrink-0")
                            ui.label("Auto Registry đã tắt").classes(
                                "text-label-m font-medium truncate"
                            )
                    elif status.get("monitor_running"):
                        finished_at = status.get("last_cycle_finished_at")
                        if finished_at:
                            error_count = int(status.get("failed") or 0) + int(
                                status.get("captions_failed") or 0
                            )
                            idle_summary = (
                                f"Quét cuối {time.strftime('%H:%M', time.localtime(finished_at))} · "
                                f"sửa {status.get('repaired', 0)} · lỗi {error_count}"
                            )
                        else:
                            idle_summary = "Đang chờ vòng quét đầu"
                        with ui.column().classes(
                            "app-sidebar-pill app-sidebar-pill--ok app-sidebar-pill--clickable gap-0.5 mt-1"
                        ).on("click", open_recovery_details).tooltip(
                            "Nhấp để xem chi tiết Auto Registry"
                        ):
                            with ui.row().classes("w-full items-center gap-1.5 no-wrap"):
                                ui.icon("verified").classes("text-base shrink-0")
                                ui.label("Auto Registry đang chạy").classes(
                                    "text-label-m font-semibold truncate"
                                )
                                ui.icon("chevron_right").classes(
                                    "text-base shrink-0 ml-auto opacity-70"
                                )
                            ui.label(idle_summary).classes("text-2xs truncate w-full opacity-85")

                    caption_quota_message = str(
                        status.get("caption_quota_message") or ""
                    )
                    if caption_quota_message:
                        with ui.row().classes(
                            "app-sidebar-pill app-sidebar-pill--warn items-center gap-1.5 no-wrap"
                        ).tooltip(caption_quota_message):
                            ui.icon("warning_amber").classes("text-sm shrink-0")
                            ui.label(caption_quota_message).classes("text-2xs truncate")

                    if processing_warning_count:
                        with ui.row().classes(
                            "app-sidebar-pill app-sidebar-pill--warn app-sidebar-pill--clickable items-center gap-1.5 no-wrap"
                        ).on("click", open_recovery_details):
                            ui.icon("schedule").classes("text-sm shrink-0")
                            ui.label(f"{processing_warning_count} audio chờ thêm lại").classes(
                                "text-2xs font-medium truncate"
                            )
                            ui.icon("chevron_right").classes(
                                "text-base shrink-0 ml-auto opacity-70"
                            )
                    channel_errors = sum(
                        result.get("outcome") == "error"
                        for result in status.get("channel_results", [])
                    )
                    if channel_errors:
                        with ui.row().classes(
                            "app-sidebar-pill app-sidebar-pill--bad app-sidebar-pill--clickable items-center gap-1.5 no-wrap"
                        ).on("click", open_recovery_details):
                            ui.icon("error_outline").classes("text-sm shrink-0")
                            ui.label(f"{channel_errors} kênh lỗi lượt quét").classes(
                                "text-2xs font-medium truncate"
                            )
                            ui.icon("chevron_right").classes(
                                "text-base shrink-0 ml-auto opacity-70"
                            )

                refresh_recovery_details(status)

                if not status.get("monitor_running") and not active:
                    recovery_activity_state["notified_start"] = False
                if active and not recovery_activity_state["notified_start"]:
                    ui.notify(
                        "Đang quét audio liên tục và kiểm tra phụ đề vừa đăng...",
                        type="info",
                        timeout=3000,
                    )
                    recovery_activity_state["notified_start"] = True
                elif recovery_activity_state["was_active"] and not active:
                    repaired = int(status.get("repaired") or 0)
                    failed = int(status.get("failed") or 0)
                    captions_repaired = int(status.get("captions_repaired") or 0)
                    captions_failed = int(status.get("captions_failed") or 0)
                    if repaired or failed or captions_repaired or captions_failed or processing_warning_count:
                        ui.notify(
                            str(status.get("message") or "Đã hoàn tất tự động khôi phục audio"),
                            type=(
                                "positive"
                                if failed == 0 and captions_failed == 0 and processing_warning_count == 0
                                else "warning"
                            ),
                            timeout=5000,
                        )
                caption_quota_message = str(
                    status.get("caption_quota_message") or ""
                )
                if (
                    caption_quota_message
                    and recovery_activity_state["quota_signature"]
                    != caption_quota_message
                ):
                    ui.notify(
                        caption_quota_message,
                        type="warning",
                        timeout=0,
                        close_button="Đóng",
                    )
                    recovery_activity_state["quota_signature"] = (
                        caption_quota_message
                    )
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
                with nav_item("/audio/remove", "Xóa audio", "o_layers_clear"):
                    pass
                with nav_item("/audio/add-only", "Thêm audio", "o_add_circle_outline"):
                    pass
                with nav_item("/videos/titles", "Ghép & đổi tiêu đề", "o_drive_file_rename_outline"):
                    pass
                with nav_item("/videos/publishing", "SEO, thumbnail & lên lịch", "o_event_available"):
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

            ui.separator().classes("bg-line mb-2")
            create_update_control()

    return drawer
