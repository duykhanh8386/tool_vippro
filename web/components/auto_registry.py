"""Bulk controls for the persistent automatic recovery registry."""

from typing import Callable

from loguru import logger
from nicegui import ui

from src.audio_recovery import (
    get_audio_recovery_registry_items,
    remove_audio_recovery_items,
    set_audio_recovery_items_enabled,
)
from src.utils import get_channels_info
from web.theme import app_card, section_header


def create_auto_registry_content(*, on_change: Callable[[], None] | None = None):
    tables = {}

    def refresh() -> None:
        try:
            channel_items, video_items = get_audio_recovery_registry_items()
            names = {
                channel.id: channel.name for channel in (get_channels_info() or [])
            }
        except Exception as exc:
            logger.error("Could not read Auto Registry: {}", exc)
            ui.notify("Không thể tải danh sách Auto Registry.", type="negative")
            return

        channel_rows = [
            {
                **item,
                "id": item["channel_id"],
                "name": names.get(item["channel_id"], item["channel_id"]),
                "status": "Active" if item["enabled"] else "Deactive",
            }
            for item in channel_items
        ]
        video_rows = [
            {
                **item,
                "id": f'{item["channel_id"]}:{item["video_id"]}',
                "name": names.get(item["channel_id"], item["channel_id"]),
                "languages": ", ".join(item["languages"]),
                "status": "Active" if item["enabled"] else "Deactive",
                "inactive_reason": (
                    "" if item["enabled"]
                    else "Video đã Deactive" if not item["video_enabled"]
                    else "Kênh chưa được phép tự động quét" if not item["channel_enabled"]
                    else "Auto Registry đang tắt"
                ),
            }
            for item in video_items
        ]
        for scope, rows in (("channels", channel_rows), ("videos", video_rows)):
            table = tables[scope]
            if table.rows != rows:
                selected_ids = {row["id"] for row in table.selected}
                table.selected = [row for row in rows if row["id"] in selected_ids]
                table.update_rows(rows, clear_selection=False)
        active_channels = sum(item["enabled"] for item in channel_items)
        summary.set_text(
            f"{len(channel_rows)} kênh "
            f"({active_channels} Active · {len(channel_rows) - active_channels} Deactive) · "
            f"{len(video_rows)} video · "
            f'{sum(item["enabled"] for item in video_items)} video được phép tự động quét'
        )

    def set_items_enabled(
        scope: str, enabled: bool, items: list[dict] | None = None
    ) -> None:
        table = tables[scope]
        selected = list(table.selected if items is None else items)
        if not selected:
            ui.notify("Hãy tick chọn kênh hoặc video cần thay đổi.", type="info")
            return
        channel_ids = []
        video_ids_by_channel = {}
        if scope == "channels":
            channel_ids = [row["channel_id"] for row in selected]
        else:
            for row in selected:
                video_ids_by_channel.setdefault(row["channel_id"], []).append(
                    row["video_id"]
                )
        if not set_audio_recovery_items_enabled(
            enabled=enabled,
            channel_ids=channel_ids,
            video_ids_by_channel=video_ids_by_channel,
        ):
            ui.notify("Không thể lưu trạng thái tự động quét.", type="negative")
            return
        if items is None:
            table.selected = []
            table.update()
        refresh()
        if on_change is not None:
            on_change()
        item_type = "kênh" if scope == "channels" else "video"
        action = "Active" if enabled else "Deactive"
        ui.notify(
            f"Đã {action} {len(selected)} {item_type}.",
            type="positive",
        )

    def toggle_channel(event) -> None:
        row_id = str(event.args.get("id") or "")
        row = next(
            (item for item in tables["channels"].rows if item["id"] == row_id),
            None,
        )
        if row is not None:
            set_items_enabled("channels", not row["enabled"], [row])

    def confirm_remove(scope: str, items: list[dict] | None = None) -> None:
        table = tables[scope]
        selected = list(table.selected if items is None else items)
        if not selected:
            ui.notify("Hãy tick chọn kênh hoặc video cần xóa.", type="info")
            return
        item_type = "kênh" if scope == "channels" else "video"
        channel_ids = []
        video_ids_by_channel = {}
        if scope == "channels":
            channel_ids = [row["channel_id"] for row in selected]
        else:
            for row in selected:
                video_ids_by_channel.setdefault(row["channel_id"], []).append(
                    row["video_id"]
                )

        def remove() -> None:
            if not remove_audio_recovery_items(
                channel_ids=channel_ids, video_ids_by_channel=video_ids_by_channel
            ):
                ui.notify("Không thể xóa các mục khỏi Auto Registry.", type="negative")
                return
            dialog.close()
            refresh()
            if on_change is not None:
                on_change()
            ui.notify(
                f"Đã xóa {len(selected)} {item_type} khỏi Auto Registry.",
                type="positive",
            )

        with ui.dialog() as dialog:
            with ui.card().classes("app-card w-full max-w-lg"):
                ui.label("Xóa khỏi Auto Registry").classes("app-section-title")
                message = (
                    f"Xóa {len(selected)} {item_type} khỏi danh sách "
                    "và ngừng tự động quét."
                )
                if scope == "channels":
                    video_count = sum(row["video_count"] for row in selected)
                    message += (
                        f" Toàn bộ {video_count} video của các kênh này "
                        "cũng sẽ được gỡ khỏi Registry."
                    )
                ui.label(message).classes("app-section-copy")
                with ui.column().classes(
                    "w-full max-h-48 overflow-auto gap-1 rounded border border-gray-200 p-2"
                ):
                    for row in selected:
                        description = row["channel_id"]
                        if scope == "videos":
                            description += f' / {row["video_id"]}'
                        ui.label(description).classes("text-xs font-mono break-all")
                with ui.row().classes("w-full justify-end gap-2"):
                    ui.button("Hủy", on_click=dialog.close).classes("app-button-secondary")
                    ui.button("Xóa", icon="delete_outline", on_click=remove).classes(
                        "app-button-danger"
                    )
        dialog.open()

    def remove_row(scope: str, event) -> None:
        row_id = str(event.args.get("id") or "")
        row = next(
            (item for item in tables[scope].rows if item["id"] == row_id), None
        )
        if row is not None:
            confirm_remove(scope, [row])

    def create_table(scope: str, columns: list[dict]) -> None:
        with ui.row().classes("w-full items-center gap-2 flex-wrap"):
            search = ui.input("Tìm theo ID hoặc tên kênh").props(
                "outlined dense clearable"
            ).classes("w-full sm:w-80")
            deactivate = ui.button(
                "Deactive",
                icon="pause_circle_outline",
                on_click=lambda: set_items_enabled(scope, False),
            ).classes("app-button-danger").props("no-caps").tooltip(
                "Tắt tự động quét các mục đã tick chọn"
            )
            activate = ui.button(
                "Active",
                icon="play_circle_outline",
                on_click=lambda: set_items_enabled(scope, True),
            ).classes("app-button-secondary").props("no-caps").tooltip(
                "Bật lại tự động quét các mục đã tick chọn"
            )
            remove_selected = ui.button(
                "Xóa khỏi danh sách",
                icon="delete_outline",
                on_click=lambda: confirm_remove(scope),
            ).classes("app-button-danger").props("no-caps")
        table = ui.table(
            columns=columns,
            rows=[],
            row_key="id",
            selection="multiple",
            pagination=20,
            column_defaults={"align": "left", "sortable": True},
        ).classes("w-full").props("flat bordered wrap-cells")
        table.add_slot(
            "body-cell-status",
            '<q-td :props="props"><q-badge '
            ':color="props.row.enabled ? \'positive\' : \'grey\'">'
            '{{ props.value }}'
            '<q-tooltip v-if="props.row.inactive_reason">'
            '{{ props.row.inactive_reason }}</q-tooltip>'
            '</q-badge></q-td>',
        )
        channel_action = (
            '<q-btn flat dense no-caps '
            ':label="props.row.enabled ? \'Deactive\' : \'Active\'" '
            ':color="props.row.enabled ? \'negative\' : \'positive\'" '
            ':icon="props.row.enabled ? \'pause_circle_outline\' : \'play_circle_outline\'" '
            '@click="$parent.$emit(\'toggle-active\', {id: props.row.id})" />'
            if scope == "channels" else ""
        )
        table.add_slot(
            "body-cell-actions",
            '<q-td :props="props"><div class="row no-wrap items-center q-gutter-xs">'
            + channel_action
            + '<q-btn flat dense no-caps label="Xóa" icon="delete_outline" color="negative" '
            '@click="$parent.$emit(\'remove-item\', {id: props.row.id})" />'
            '</div></q-td>',
        )
        if scope == "channels":
            table.on("toggle-active", toggle_channel)
        table.on("remove-item", lambda event: remove_row(scope, event))
        table.add_slot(
            "no-data",
            '<div class="w-full text-center text-grey q-pa-md">'
            'Chưa có mục nào trong Auto Registry hoặc không có kết quả phù hợp.'
            '</div>',
        )
        search.bind_value_to(table, "filter", forward=lambda value: value or "")
        deactivate.bind_enabled_from(table, "selected", backward=bool)
        activate.bind_enabled_from(table, "selected", backward=bool)
        remove_selected.bind_enabled_from(table, "selected", backward=bool)
        ui.label().bind_text_from(
            table, "selected", backward=lambda rows: f"Đã chọn {len(rows)} mục"
        ).classes("text-xs text-gray-500")
        tables[scope] = table

    with app_card():
        with section_header(
            "Auto Registry",
            "Tick chọn các mục để Active, Deactive hoặc xóa khỏi danh sách; có thể dùng nút trên từng dòng.",
        ):
            ui.button(icon="refresh", on_click=refresh).props(
                "flat round dense"
            ).tooltip("Làm mới Auto Registry")
        summary = ui.label("").classes("text-xs text-gray-500")
        ui.label(
            "Mặc định tự động quét tất cả các kênh Active. Kênh Deactive vẫn ở trong "
            "danh sách và có thể Active lại bằng nút; toàn bộ video của kênh Deactive "
            "được bỏ qua. Deactive video chỉ áp dụng cho ID đó. Trạng thái được lưu "
            "khi đóng và mở lại ứng dụng."
        ).classes("text-xs text-gray-500")
        with ui.tabs().classes("w-full") as tabs:
            channel_tab = ui.tab("Theo ID kênh", icon="subscriptions")
            video_tab = ui.tab("Theo ID video", icon="smart_display")
        with ui.tab_panels(tabs, value=channel_tab).classes("w-full"):
            with ui.tab_panel(channel_tab).classes("p-0 pt-3"):
                create_table("channels", [
                    {"name": "name", "label": "Kênh", "field": "name"},
                    {"name": "channel_id", "label": "Channel ID", "field": "channel_id", "classes": "font-mono select-text"},
                    {"name": "video_count", "label": "Tổng video", "field": "video_count"},
                    {"name": "active_video_count", "label": "Video được quét", "field": "active_video_count"},
                    {"name": "status", "label": "Trạng thái", "field": "status"},
                    {"name": "actions", "label": "Thao tác", "field": "id", "sortable": False},
                ])
            with ui.tab_panel(video_tab).classes("p-0 pt-3"):
                create_table("videos", [
                    {"name": "video_id", "label": "Video ID", "field": "video_id", "classes": "font-mono select-text"},
                    {"name": "channel_id", "label": "Channel ID", "field": "channel_id", "classes": "font-mono select-text"},
                    {"name": "name", "label": "Kênh", "field": "name"},
                    {"name": "languages", "label": "Ngôn ngữ audio", "field": "languages"},
                    {"name": "status", "label": "Trạng thái", "field": "status"},
                    {"name": "actions", "label": "Thao tác", "field": "id", "sortable": False},
                ])
    refresh()
    ui.timer(5.0, refresh)
    return refresh
