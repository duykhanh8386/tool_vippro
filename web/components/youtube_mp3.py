"""NiceGUI page for the durable YouTube-to-MP3 queue."""

from __future__ import annotations

import os
from pathlib import Path

from nicegui import ui

from src.youtube_mp3_download import (
    parse_youtube_urls,
    youtube_mp3_controller,
)
from web.components.common import select_directory
from web.theme import app_card, empty_state, page_header, page_shell, section_header


STATUS_META = {
    "pending": ("schedule", "warning", "Chờ tải"),
    "downloading": ("downloading", "info", "Đang tải"),
    "successful": ("check_circle", "success", "Hoàn tất"),
    "stopped": ("stop_circle", "warning", "Đã dừng"),
    "error": ("error", "danger", "Lỗi"),
}


def create_youtube_mp3_page() -> None:
    controller = youtube_mp3_controller
    refs = {
        "urls": None,
        "output_dir": None,
        "start": None,
        "stop": None,
        "status": None,
        "table": None,
    }
    last_version = {"value": -1}

    def render_table() -> None:
        table = refs["table"]
        if table is None:
            return
        table.clear()
        with table:
            if not controller.urls:
                empty_state(
                    "Chưa có link YouTube",
                    "Dán mỗi link video vào một dòng rồi bấm Lưu danh sách.",
                    icon="o_music_note",
                )
                return

            with ui.element("div").classes("app-table").style(
                "--app-table-columns: minmax(220px, 2.4fr) 110px 100px minmax(180px, 1.4fr)"
            ):
                with ui.element("div").classes("app-table-header"):
                    ui.label("Link / tiêu đề")
                    ui.label("Trạng thái")
                    ui.label("Tiến độ")
                    ui.label("File MP3")

                for url in controller.urls:
                    item = controller.items.get(url, {})
                    status = item.get("status", "pending")
                    icon, tone, label = STATUS_META.get(
                        status, ("help", "neutral", status)
                    )
                    with ui.element("div").classes("app-table-row"):
                        with ui.column().classes("gap-0 min-w-0"):
                            ui.label(item.get("title") or url).classes(
                                "text-sm font-medium text-gray-800 truncate"
                            )
                            if item.get("title"):
                                ui.label(url).classes("text-xs text-gray-500 truncate")
                            if item.get("error"):
                                ui.label(item["error"]).classes(
                                    "text-xs text-red-600 line-clamp-2"
                                )
                        with ui.row().classes(
                            f"app-status app-status--{tone} gap-1 justify-self-start"
                        ):
                            ui.icon(icon).classes("text-sm")
                            ui.label(label).classes("text-xs")
                        progress = int(item.get("progress") or 0)
                        with ui.column().classes("gap-1"):
                            ui.linear_progress(value=progress / 100).classes("w-full")
                            ui.label(f"{progress}%").classes("text-xs text-gray-500")
                        output_path = item.get("output_path") or ""
                        ui.label(
                            Path(output_path).name if output_path else "—"
                        ).classes("text-xs text-gray-600 truncate")

    def sync_ui() -> None:
        if last_version["value"] == controller.version:
            return
        last_version["value"] = controller.version
        render_table()
        if refs["status"]:
            refs["status"].set_text(controller.status_text)
        if refs["output_dir"]:
            refs["output_dir"].set_text(str(controller.output_dir))
        if refs["start"]:
            refs["start"].set_enabled(not controller.is_running())
        if refs["stop"]:
            refs["stop"].set_enabled(controller.is_running())

    def save_links(*, quiet: bool = False) -> bool:
        if controller.is_running():
            ui.notify("Đang tải MP3; hãy bấm Dừng trước khi đổi danh sách.", type="warning")
            return False
        urls, invalid = parse_youtube_urls(refs["urls"].value)
        controller.update_urls(urls)
        if invalid:
            preview = ", ".join(invalid[:2])
            suffix = "…" if len(invalid) > 2 else ""
            ui.notify(
                f"Bỏ qua {len(invalid)} link không phải YouTube: {preview}{suffix}",
                type="warning",
            )
        elif not quiet:
            ui.notify(f"Đã lưu {len(urls)} link YouTube.", type="positive")
        sync_ui()
        return bool(urls)

    async def handle_start() -> None:
        if not save_links(quiet=True):
            if not controller.urls:
                ui.notify("Hãy dán ít nhất một link YouTube hợp lệ.", type="warning")
            return
        try:
            controller.start()
            sync_ui()
        except Exception as exc:
            ui.notify(str(exc), type="negative")

    async def handle_stop() -> None:
        try:
            await controller.stop()
            sync_ui()
        except Exception as exc:
            ui.notify(f"Không thể dừng tải: {exc}", type="negative")

    def choose_output_dir() -> None:
        chosen = select_directory(
            initial_dir=str(controller.output_dir),
            title="Chọn thư mục lưu MP3",
        )
        if not chosen:
            return
        try:
            controller.set_output_dir(chosen)
            sync_ui()
            ui.notify("Đã đổi thư mục lưu MP3.", type="positive")
        except Exception as exc:
            ui.notify(str(exc), type="negative")

    def open_output_dir() -> None:
        try:
            controller.output_dir.mkdir(parents=True, exist_ok=True)
            os.startfile(str(controller.output_dir))
        except Exception as exc:
            ui.notify(f"Không thể mở thư mục MP3: {exc}", type="negative")

    with page_shell():
        with page_header(
            "Download MP3 from YouTube",
            "Tải audio của video YouTube công khai sang MP3. Danh sách và tiến độ được lưu theo máy để có thể tiếp tục sau khi mở lại tool.",
            eyebrow="Tác vụ",
        ):
            pass

        with app_card():
            with section_header(
                "Link YouTube",
                "Dán một link video hoặc Shorts mỗi dòng. Playlist được xử lý theo từng link video riêng.",
            ):
                pass
            refs["urls"] = ui.textarea(
                value="\n".join(controller.urls),
                label="YouTube URL",
            ).props(
                'outlined autogrow rows=7 autocomplete=off placeholder="https://www.youtube.com/watch?v=..."'
            ).classes("w-full")
            with ui.row().classes("w-full justify-end mt-2"):
                ui.button(
                    "Lưu danh sách",
                    icon="save",
                    on_click=save_links,
                ).classes("app-button-secondary")

        with app_card(compact=True):
            with ui.row().classes("w-full items-center gap-2 flex-wrap"):
                ui.icon("o_folder").classes("text-emerald-600")
                ui.label("Thư mục lưu MP3:").classes("text-sm text-gray-600")
                refs["output_dir"] = ui.label(str(controller.output_dir)).classes(
                    "text-sm font-mono text-gray-800 truncate flex-1 min-w-48"
                )
                ui.button(
                    "Chọn thư mục", icon="folder_open", on_click=choose_output_dir
                ).props("dense").classes("app-button-secondary text-xs")
                ui.button(
                    "Mở thư mục", icon="open_in_new", on_click=open_output_dir
                ).props("dense").classes("app-button-secondary text-xs")

        with app_card():
            with section_header(
                "Điều khiển tải",
                "File MP3 đã hoàn tất sẽ được giữ nguyên; chỉ các link chưa xong hoặc lỗi mới được tải lại.",
            ):
                pass
            with ui.row().classes("items-center gap-3 flex-wrap"):
                refs["start"] = ui.button(
                    "Tải MP3", icon="download", on_click=handle_start
                ).classes("app-button-primary")
                refs["stop"] = ui.button(
                    "Dừng", icon="stop", on_click=handle_stop
                ).classes("app-button-secondary")
                refs["stop"].set_enabled(controller.is_running())
            refs["status"] = ui.label(controller.status_text).classes(
                "text-sm text-gray-600 italic mt-3"
            )

        with app_card():
            with section_header(
                "Danh sách tải",
                "Tiến độ được đồng bộ tự động; nếu mất điện, trạng thái đang tải sẽ sẵn sàng để tiếp tục ở lần mở sau.",
            ):
                pass
            refs["table"] = ui.column().classes("w-full")

    sync_ui()
    ui.timer(0.5, sync_ui)
