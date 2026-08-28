# RECOVERED: reconstructed from CPython 3.12 bytecode
"""Settings page — app info & GitHub auto-updater UI."""

import asyncio
from datetime import datetime, timezone

from nicegui import app, ui

from src.license_manager import deactivate, get_license_info
from src.route_manager import router
from src.updater import updater_service


SYNC_INTERVAL = 0.4


def create_settings_page():
    last_version = {"v": -1}
    ui_refs = {
        "check_btn": None,
        "action_btn": None,
        "status_label": None,
        "progress_bar": None,
        "release_card": None,
    }

    def _mask_key(key: str) -> str:
        """Che bớt key, chỉ giữ đầu/cuối: LIC-ABCD…WXYZ."""
        if not key:
            return "—"
        if len(key) <= 12:
            return key
        return f"{key[:8]}…{key[-4:]}"

    def _format_expiry(expires_at) -> str:
        """ISO datetime -> 'dd/mm/yyyy (còn N ngày)'. None -> 'Vĩnh viễn'."""
        if not expires_at:
            return "Vĩnh viễn"
        try:
            dt = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        except ValueError:
            return str(expires_at)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        date_str = dt.strftime("%d/%m/%Y")
        days = (dt - datetime.now(timezone.utc)).days
        if days < 0:
            return f"{date_str} (đã hết hạn)"
        if days == 0:
            return f"{date_str} (hết hạn hôm nay)"
        return f"{date_str} (còn {days} ngày)"

    def handle_deactivate():
        deactivate()
        ui.notify("Đã hủy kích hoạt trên thiết bị này.", type="warning")
        ui.navigate.to(router.login_path)

    def handle_check():
        updater_service.check_for_updates()
        last_version["v"] = -1

    def handle_download():
        updater_service.download_update()
        last_version["v"] = -1

    async def handle_install():
        ok, msg = updater_service.install_update()
        ui.notify(msg, type="positive" if ok else "negative")
        if ok:

            ui.notify(
                "Ứng dụng sẽ đóng để hoàn tất cài đặt...", type="warning"
            )
            await asyncio.sleep(1.5)
            try:
                app.shutdown()
            except Exception:
                import os

                os._exit(0)

    def _render_release(info: dict):
        card = ui_refs["release_card"]
        if card is None:
            return
        card.clear()
        with card:
            with ui.row().classes("items-center gap-2"):
                ui.icon("new_releases").classes("text-green-600")
                ui.label(
                    f"Phiên bản mới: {info.get('name') or info.get('tag_name')}"
                ).classes("text-base font-semibold text-gray-800")
            published = info.get("published_at", "")
            if published:
                ui.label(f"Phát hành: {published[:10]}").classes(
                    "text-xs text-gray-500"
                )
            body = (info.get("body") or "").strip()
            if body:
                with ui.scroll_area().classes(
                    "w-full max-h-48 bg-gray-50 rounded p-2 mt-1"
                ):
                    ui.markdown(body).classes("text-sm text-gray-700")
            html_url = info.get("html_url")
            if html_url:
                ui.link("Xem trên GitHub", html_url, new_tab=True).classes(
                    "text-xs text-indigo-600"
                )

    def _sync_tick():
        svc = updater_service

        pb = ui_refs["progress_bar"]
        if pb:
            if svc.phase == "downloading":
                pb.set_visibility(True)
                pb.set_value(svc.progress / 100)
            elif svc.phase == "ready":
                pb.set_visibility(True)
                pb.set_value(1.0)
            else:
                pb.set_visibility(False)
        if last_version["v"] == svc.version:
            return
        last_version["v"] = svc.version

        status = ui_refs["status_label"]
        if status:
            status.set_text(svc.status_text or "")
            color = {
                "error": "text-red-500",
                "available": "text-green-600",
                "up_to_date": "text-gray-500",
                "ready": "text-green-600",
            }.get(svc.phase, "text-gray-500")
            status.classes(replace=f"text-sm italic {color}")

        cb = ui_refs["check_btn"]
        if cb:
            cb.set_enabled(not svc.is_busy())

        ab = ui_refs["action_btn"]
        if ab:
            ab.clear()
            with ab:
                if svc.phase == "available":
                    ui.button(
                        "Tải bản cập nhật",
                        icon="download",
                        on_click=handle_download,
                    ).props("unelevated color=green")
                elif svc.phase == "downloading":
                    ui.button("Đang tải...", icon="hourglass_top").props(
                        "unelevated color=grey"
                    ).set_enabled(False)
                elif svc.phase == "ready":
                    ui.button(
                        "Cài đặt & Khởi động lại",
                        icon="system_update_alt",
                        on_click=handle_install,
                    ).props("unelevated color=green")

        if svc.phase in ("available", "downloading", "ready") and svc.release_info:
            _render_release(svc.release_info)
            return
        card = ui_refs["release_card"]
        if card:
            card.clear()

    with ui.column().classes("w-full max-w-3xl mx-auto p-4 gap-4"):
        with ui.row().classes("items-center gap-3 mb-2"):
            ui.icon("settings").classes("text-3xl text-indigo-500")
            ui.label("Cài đặt").classes("text-2xl font-bold text-gray-800")

        info = get_license_info() or {}
        with ui.card().classes("w-full p-4 gap-3"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("vpn_key").classes("text-amber-500")
                ui.label("Thông tin kích hoạt").classes(
                    "text-lg font-semibold text-gray-800"
                )

            def _info_row(label: str, value: str, *, mono: bool = False):
                with ui.row().classes("items-center gap-2"):
                    ui.label(label).classes("text-sm text-gray-600")
                    cls = "text-sm text-gray-800 px-2 py-0.5 rounded bg-gray-100"
                    if mono:
                        cls += " font-mono"
                    ui.label(value).classes(cls)

            _info_row("Key:", _mask_key(info.get("license_key", "")), mono=True)
            _info_row("Hạn dùng:", _format_expiry(info.get("expires_at")))

            used = info.get("devices_used")
            mx = info.get("max_devices")
            if used is not None or mx is not None:
                _info_row(
                    "Thiết bị:",
                    f"{used if used is not None else '?'}/{mx if mx is not None else '?'}",
                )

            ui.button(
                "Hủy kích hoạt thiết bị này",
                icon="logout",
                on_click=handle_deactivate,
            ).props("outline color=red").classes("mt-1")

        with ui.card().classes("w-full p-4 gap-3"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("system_update").classes("text-indigo-500")
                ui.label("Cập nhật phần mềm").classes(
                    "text-lg font-semibold text-gray-800"
                )

            with ui.row().classes("items-center gap-2"):
                ui.label("Phiên bản hiện tại:").classes("text-sm text-gray-600")
                ui.label(updater_service.current_version).classes(
                    "text-sm font-mono bg-gray-100 text-gray-800 px-2 py-0.5 rounded"
                )

            with ui.row().classes("items-center gap-3 flex-wrap"):
                ui_refs["check_btn"] = (
                    ui.button(
                        "Kiểm tra cập nhật", icon="refresh", on_click=handle_check
                    )
                    .props("outline")
                    .classes("text-indigo-700")
                )
                ui_refs["action_btn"] = ui.row().classes("items-center gap-2")

            pb = ui.linear_progress(value=0, show_value=False).classes("w-full")
            pb.set_visibility(False)
            ui_refs["progress_bar"] = pb

            ui_refs["status_label"] = ui.label("").classes(
                "text-sm italic text-gray-500"
            )

            ui_refs["release_card"] = ui.column().classes("w-full gap-1")

        ui_refs["status_label"].set_text(updater_service.status_text or "")
        last_version["v"] = updater_service.version
        _sync_tick()

        ui.timer(SYNC_INTERVAL, _sync_tick, active=True)
