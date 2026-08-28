# RECOVERED: reconstructed from CPython 3.12 bytecode
import asyncio

from loguru import logger
from nicegui import ui

from src.channel_scanner import channel_fetcher
from src.channel_store import channel_store
from src.license_manager import get_license_info
from src.state_manager import state_manager
from src.utils import get_channels_info


def create_studio_content():
    ui_refs = {"email_input": None, "password_input": None}

    def save_credentials():
        """Save login credentials to file (remember me functionality)"""
        try:
            if ui_refs["email_input"] and ui_refs["password_input"]:
                state = {
                    "email": ui_refs["email_input"].value,
                    "password": ui_refs["password_input"].value,
                    "remember_me": True,
                }
                state_manager.save_state("studio_credentials", state)
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")

    def load_credentials():
        """Load saved credentials from file"""
        try:
            state = state_manager.load_state("studio_credentials")
            if not state or not state.get("remember_me"):
                return

            def update_ui():
                try:
                    if ui_refs["email_input"] and "email" in state:
                        ui_refs["email_input"].value = state["email"]
                    if ui_refs["password_input"] and "password" in state:
                        ui_refs["password_input"].value = state["password"]
                    logger.info("Credentials loaded")
                except Exception as e:
                    logger.error(f"Failed to update UI: {e}")

            ui.timer(0.5, update_ui, once=True)
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")

    async def fetch_channel_data(email, password):
        """Asynchronous function to fetch channel data."""
        try:
            logger.info("Fetching channel data...")
            await asyncio.to_thread(
                channel_fetcher.run, email=email, password=password
            )
        except Exception as e:
            logger.exception(f"Error fetching channels: {e}")
            ui.notify(f"Không thể lấy dữ liệu kênh: {e}", type="negative")
        finally:
            processing_popup.close()
            refresh_channel_list()

    def on_login():
        """Handler for login button click."""
        email = email_input.value
        password = password_input.value
        if remember_checkbox.value:
            save_credentials()
        login_dialog.close()
        processing_popup.open()
        asyncio.create_task(fetch_channel_data(email, password))

    def delete_channel_from_db(channel_id: str):
        """Delete a channel from the SQLite database."""
        try:
            deleted = channel_store.delete_channel(channel_id)
            if not deleted:
                ui.notify(f"Không tìm thấy kênh: {channel_id}", type="warning")
                return False

            ui.notify("Xóa kênh thành công!", type="positive")
            return True
        except Exception as e:
            logger.exception(e)
            ui.notify(f"Lỗi khi xóa kênh: {e}", type="negative")
            return False

    def delete_all_channels():
        """Delete all channels from the SQLite database."""
        try:
            channels = get_channels_info()
            if not channels:
                ui.notify("Không có kênh nào để xóa", type="info")
                return

            count = 0
            for ch in channels:
                if channel_store.delete_channel(ch.id):
                    count += 1

            ui.notify(f"Đã xóa {count} kênh thành công!", type="positive")
            refresh_channel_list()
        except Exception as e:
            logger.exception(e)
            ui.notify(f"Lỗi khi xóa tất cả kênh: {e}", type="negative")

    def create_delete_click_handler(channel_id: str, channel_name: str):
        """Create a delete click handler that opens a confirm dialog and deletes the channel."""

        def handler():
            def confirm_delete():
                confirm_dialog.close()
                if delete_channel_from_db(channel_id):
                    refresh_channel_list()

            def cancel_delete():
                confirm_dialog.close()

            with ui.dialog() as confirm_dialog:
                with ui.card().classes("w-full max-w-sm p-4"):
                    ui.label("Xác nhận xóa kênh").classes(
                        "text-h6 mb-2 text-gray-800"
                    )
                    ui.label(
                        f"Bạn có chắc chắn muốn xóa kênh '{channel_name}'? Thao tác này sẽ xóa toàn bộ dữ liệu kênh trên máy."
                    ).classes("text-sm text-gray-600")
                    with ui.row().classes("justify-end gap-2 w-full mt-4"):
                        ui.button("Hủy", on_click=cancel_delete).classes(
                            "bg-gray-200 text-gray-800"
                        )
                        ui.button("Xóa", on_click=confirm_delete).classes(
                            "bg-red-600 text-white"
                        )
            confirm_dialog.open()

        return handler

    with ui.dialog().props(
        'backdrop-filter="blur(4px) saturate(150%)" persistent'
    ) as processing_popup:
        with ui.card().classes(
            "p-8 rounded-lg shadow-lg bg-white flex flex-col items-center justify-center space-y-4"
        ):
            ui.spinner(size="lg", color="primary").classes("mb-4")
            ui.label("Đang xử lý...").classes(
                "text-lg font-semibold text-center text-gray-700"
            )
            ui.label("Vui lòng theo dõi quá trình ở cửa sổ chrome.").classes(
                "text-sm text-gray-500 text-center"
            )

    with ui.column().style("min-height: 95vh;").classes(
        "w-full h-full bg-[#fcf7ff]"
    ):
        with ui.dialog() as login_dialog:
            with ui.card().classes("w-full max-w-sm p-4"):
                ui.label("Đăng nhập").classes(
                    "text-h4 mb-4 text-gray-800 text-center"
                )
                email_input = (
                    ui.input("Email")
                    .props("outlined")
                    .classes("w-full mb-3 p-2 text-black rounded")
                )
                ui_refs["email_input"] = email_input

                password_input = (
                    ui.input("Password", password=True)
                    .props("outlined")
                    .classes("w-full mb-3 p-2 text-black rounded")
                )
                ui_refs["password_input"] = password_input

                remember_checkbox = ui.checkbox(
                    "Nhớ thông tin đăng nhập", value=True
                ).classes("mb-3")

                def clear_login_inputs():
                    email_input.value = ""
                    password_input.value = ""
                    ui.notify("Đã xóa tất cả input", type="info")

                with ui.row().classes("w-full gap-2"):
                    ui.button(
                        "Xác nhận", on_click=on_login, color="#f8edff"
                    ).classes(
                        "flex-1 bg-blue-600 text-gray-900 px-4 py-2 rounded hover:bg-blue-700 transition"
                    )
                    ui.button(
                        "Xóa tất cả", on_click=clear_login_inputs
                    ).props("color=red").classes("flex-1")

                load_credentials()

        with ui.card().classes("w-full p-4 text-black"):
            with ui.row().classes("w-full justify-between items-center"):
                ui.label("Tài khoản").classes("text-h6 text-gray-900")
                _lic = get_license_info()
                _raw = _lic.get("expires_at") if _lic else None
                if _raw:
                    try:
                        from datetime import datetime

                        _dt = datetime.fromisoformat(
                            _raw.replace("Z", "+00:00")
                        )
                        _expires = _dt.strftime("%d/%m/%Y %H:%M")
                    except Exception:
                        _expires = _raw
                else:
                    _expires = "Vinh vien" if _lic else "N/A"
                ui.label(f"Hết hạn: {_expires}").classes(
                    "text-base font-semibold text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-md px-3 py-1.5 border border-red-200 dark:border-red-800"
                )

                ui.button(
                    "Lấy thông tin kênh",
                    on_click=login_dialog.open,
                    color="#F2DDDC",
                ).classes("bg-[#F2DDDC] text-gray-900 transition")

        with ui.card().props("square").style("min-height: 85vh;").classes(
            "w-full mx-auto mt-4 p-4"
        ):
            with ui.row().classes("items-center justify-between w-full mb-3"):
                ui.label("YouTube Channels").classes("text-h6 text-black")

                def handle_refresh_click():
                    refresh_channel_list()

                def handle_delete_all_click():
                    def confirm():
                        dlg.close()
                        delete_all_channels()

                    with ui.dialog() as dlg:
                        with ui.card().classes("w-full max-w-sm p-4"):
                            ui.label("Xác nhận xóa tất cả").classes(
                                "text-h6 mb-2 text-gray-800"
                            )
                            ui.label(
                                "Bạn có chắc chắn muốn xóa toàn bộ kênh? Thao tác này không thể hoàn tác."
                            ).classes("text-sm text-gray-600")
                            with ui.row().classes(
                                "justify-end gap-2 w-full mt-4"
                            ):
                                ui.button("Hủy", on_click=dlg.close).classes(
                                    "bg-gray-200 text-gray-800"
                                )
                                ui.button(
                                    "Xóa tất cả", on_click=confirm
                                ).classes("bg-red-600 text-white")
                    dlg.open()

                with ui.row().classes("gap-2"):
                    ui.button(
                        "Làm mới", on_click=handle_refresh_click
                    ).classes("bg-gray-200 text-gray-800")
                    ui.button(
                        "Xóa tất cả kênh",
                        icon="delete_sweep",
                        on_click=handle_delete_all_click,
                    ).props("outline").classes(
                        "text-red-600 border-red-400 hover:bg-red-50 transition"
                    )

            channels_container = ui.row().classes("gap-2 flex-wrap")

            def refresh_channel_list():
                channels = get_channels_info()
                channels_container.clear()
                if not channels:
                    with channels_container:
                        ui.label(
                            "Chưa có kênh nào. Vui lòng đăng nhập để thêm kênh."
                        ).classes("text-gray-500 italic")
                    return

                with channels_container:
                    for channel_data in channels:
                        name = channel_data.name
                        avatar = channel_data.img_src
                        cid = channel_data.id

                        with ui.card().classes(
                            "w-56 p-3 bg-[#e5d8ed] hover:bg-[#cca6e3] transition rounded-md shadow-md"
                        ):
                            with ui.row().classes(
                                "items-center justify-between w-full"
                            ):
                                with ui.row().classes("items-center gap-2"):
                                    if avatar:
                                        ui.image(avatar).classes(
                                            "w-8 h-8 rounded-full"
                                        )
                                    else:
                                        ui.icon("account_circle").classes(
                                            "text-2xl text-gray-500"
                                        )
                                    ui.label(name[:15]).classes(
                                        "text-xs font-bold text-gray-900 truncate"
                                    )

                                ui.button(
                                    icon="delete",
                                    on_click=create_delete_click_handler(cid, name),
                                ).props("flat round dense").classes("text-red-600")

            refresh_channel_list()
