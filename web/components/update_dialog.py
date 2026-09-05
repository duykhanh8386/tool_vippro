"""In-app installer update controls.

The application never runs ``git pull`` on an end-user computer: a packaged
installation has no source checkout (and must not execute arbitrary commits).
Instead, this view downloads the publisher's GitHub Release asset
through :mod:`src.updater`, then hands it to the normal Inno Setup installer.
"""

from __future__ import annotations

import asyncio

from nicegui import app, ui

from src.task_runtime import active_run_count
from src.updater import updater_service


def create_update_control() -> None:
    """Add the application-update button and its progress dialog to a drawer."""

    with ui.dialog() as dialog, ui.card().classes("w-[min(460px,calc(100vw-32px))] gap-4"):
        ui.label("Cập nhật Tuất Videos").classes("text-lg font-semibold text-gray-800")
        version_label = ui.label().classes("text-sm text-gray-500")
        status_label = ui.label().classes("min-h-[24px] text-sm text-gray-700")
        progress = ui.linear_progress(value=0).classes("w-full")
        notes_label = ui.label().classes("max-h-28 overflow-y-auto whitespace-pre-wrap text-xs text-gray-500")

        with ui.row().classes("w-full justify-end gap-2"):
            cancel_button = ui.button("Hủy tải", icon="close").classes("app-button-secondary")
            check_button = ui.button("Kiểm tra", icon="refresh").classes("app-button-secondary")
            download_button = ui.button("Tải bản mới", icon="download").classes("app-button-primary")
            install_button = ui.button("Cài đặt & khởi động lại", icon="system_update").classes("app-button-primary")
            ui.button("Đóng", on_click=dialog.close).classes("app-button-secondary")

    def refresh() -> None:
        service = updater_service
        phase = service.phase
        version_label.set_text(f"Phiên bản đang dùng: v{service.current_version}")
        status_label.set_text(service.status_text or "Nhấn Kiểm tra để tìm bản mới.")
        progress.set_value(max(0, min(100, service.progress)) / 100)

        release_info = service.release_info or {}
        notes = str(release_info.get("body") or "").strip()
        notes_label.set_text(notes)

        checking = phase == "checking"
        downloading = phase == "downloading"
        check_button.set_enabled(not checking and not downloading)
        cancel_button.set_visibility(downloading)
        download_button.set_visibility(phase == "available")
        download_button.set_enabled(phase == "available")
        install_button.set_visibility(phase == "ready")
        install_button.set_enabled(phase == "ready")

    def open_dialog() -> None:
        dialog.open()
        updater_service.check_for_updates()
        refresh()

    def check_for_updates() -> None:
        updater_service.check_for_updates()
        refresh()

    def download_update() -> None:
        updater_service.download_update()
        refresh()

    def cancel_download() -> None:
        updater_service.cancel_download()
        refresh()

    async def install_update() -> None:
        running = active_run_count()
        if running:
            ui.notify(
                f"Còn {running} tác vụ đang chạy. Hãy dừng hoặc chờ xong trước khi cập nhật.",
                type="warning",
            )
            return
        ok, message = updater_service.install_update()
        if not ok:
            ui.notify(message, type="negative")
            refresh()
            return
        ui.notify(message + " Tool sẽ đóng để cập nhật.", type="positive")
        await asyncio.sleep(0.75)
        app.shutdown()

    cancel_button.on_click(cancel_download)
    check_button.on_click(check_for_updates)
    download_button.on_click(download_update)
    install_button.on_click(install_update)
    ui.timer(0.25, refresh)
    refresh()

    ui.button("Cập nhật tool", icon="system_update", on_click=open_dialog).classes(
        "app-button-secondary w-full mb-2"
    )
