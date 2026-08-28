import asyncio
from datetime import datetime

from loguru import logger
from nicegui import ui

from src.channel_scanner import ChannelFetcher
from src.channel_store import channel_store
from src.license_manager import get_license_info
from src.state_manager import state_manager
from src.utils import get_channels_info
from src.task_runtime import TaskStopped, bind_run_context, create_run_context
from web.theme import (
    app_card,
    app_table,
    empty_state,
    page_header,
    page_shell,
    section_header,
    status_badge,
)


def create_studio_content():
    ui_refs = {"email_input": None, "password_input": None}

    def save_credentials():
        """Save login credentials to file (remember me functionality)."""
        try:
            if ui_refs["email_input"] and ui_refs["password_input"]:
                state_manager.save_state(
                    "studio_credentials",
                    {
                        "email": ui_refs["email_input"].value,
                        "password": ui_refs["password_input"].value,
                        "remember_me": True,
                    },
                )
        except Exception as exc:
            logger.error(f"Failed to save credentials: {exc}")

    def load_credentials():
        """Load saved credentials into the existing dialog inputs."""
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
                except Exception as exc:
                    logger.error(f"Failed to update UI: {exc}")

            ui.timer(0.5, update_ui, once=True)
        except Exception as exc:
            logger.error(f"Failed to load credentials: {exc}")

    async def fetch_channel_data(email, password):
        run_context = create_run_context("studio_channel_scan")
        channel_fetcher = ChannelFetcher()
        try:
            logger.info("Fetching channel data...")
            with bind_run_context(run_context):
                await asyncio.to_thread(
                    channel_fetcher.run,
                    email=email,
                    password=password,
                )
        except TaskStopped:
            logger.info("Channel scan stopped")
            ui.notify("Đã dừng quét kênh.", type="info")
        except Exception as exc:
            logger.exception(f"Error fetching channels: {exc}")
            ui.notify(f"Không thể lấy dữ liệu kênh: {exc}", type="negative")
        finally:
            run_context.cleanup()
            processing_popup.close()
            refresh_channel_list()

    def on_login():
        email = email_input.value
        password = password_input.value
        if remember_checkbox.value:
            save_credentials()
        login_dialog.close()
        processing_popup.open()
        asyncio.create_task(fetch_channel_data(email, password))

    def delete_channel_from_db(channel_id: str):
        try:
            deleted = channel_store.delete_channel(channel_id)
            if not deleted:
                ui.notify(f"Không tìm thấy kênh: {channel_id}", type="warning")
                return False
            ui.notify("Xóa kênh thành công!", type="positive")
            return True
        except Exception as exc:
            logger.exception(exc)
            ui.notify(f"Lỗi khi xóa kênh: {exc}", type="negative")
            return False

    def delete_all_channels():
        try:
            channels = get_channels_info()
            if not channels:
                ui.notify("Không có kênh nào để xóa", type="info")
                return
            count = sum(
                1 for channel in channels if channel_store.delete_channel(channel.id)
            )
            ui.notify(f"Đã xóa {count} kênh thành công!", type="positive")
            refresh_channel_list()
        except Exception as exc:
            logger.exception(exc)
            ui.notify(f"Lỗi khi xóa tất cả kênh: {exc}", type="negative")

    def create_delete_click_handler(channel_id: str, channel_name: str):
        def handler():
            def confirm_delete():
                confirm_dialog.close()
                if delete_channel_from_db(channel_id):
                    refresh_channel_list()

            with ui.dialog() as confirm_dialog:
                with ui.card().classes("app-card w-full max-w-sm"):
                    ui.label("Xác nhận xóa kênh").classes("app-section-title")
                    ui.label(
                        f"Bạn có chắc chắn muốn xóa kênh “{channel_name}”? "
                        "Dữ liệu kênh lưu trên máy sẽ bị xóa."
                    ).classes("app-section-copy")
                    with ui.row().classes("justify-end gap-2 w-full mt-3"):
                        ui.button(
                            "Hủy",
                            icon="close",
                            on_click=confirm_dialog.close,
                        ).classes("app-button-secondary")
                        ui.button(
                            "Xóa kênh",
                            icon="delete_outline",
                            on_click=confirm_delete,
                        ).classes("app-button-danger")
            confirm_dialog.open()

        return handler

    def confirm_delete_all():
        def confirm():
            dialog.close()
            delete_all_channels()

        with ui.dialog() as dialog:
            with ui.card().classes("app-card w-full max-w-sm"):
                ui.label("Xóa toàn bộ kênh?").classes("app-section-title")
                ui.label(
                    "Thao tác này xóa toàn bộ dữ liệu kênh của ứng dụng trên máy "
                    "và không thể hoàn tác."
                ).classes("app-section-copy")
                with ui.row().classes("justify-end gap-2 w-full mt-3"):
                    ui.button(
                        "Hủy",
                        icon="close",
                        on_click=dialog.close,
                    ).classes("app-button-secondary")
                    ui.button(
                        "Xóa tất cả",
                        icon="delete_sweep",
                        on_click=confirm,
                    ).classes("app-button-danger")
        dialog.open()

    def format_expiry(license_info) -> str:
        raw_expiry = license_info.get("expires_at") if license_info else None
        if not raw_expiry:
            return "Vĩnh viễn" if license_info else "Chưa xác định"
        try:
            expiry = datetime.fromisoformat(raw_expiry.replace("Z", "+00:00"))
            return expiry.strftime("%d/%m/%Y · %H:%M")
        except Exception:
            return str(raw_expiry)

    with ui.dialog().props(
        'backdrop-filter="blur(3px)" persistent'
    ) as processing_popup:
        with ui.card().classes("app-card w-full max-w-sm items-center text-center"):
            ui.spinner(size="lg", color="primary")
            ui.label("Đang lấy thông tin kênh").classes("app-section-title")
            ui.label(
                "Hãy hoàn tất đăng nhập trong cửa sổ Chrome. Dữ liệu sẽ tự động "
                "cập nhật khi quá trình kết thúc."
            ).classes("app-section-copy")

    with ui.dialog() as login_dialog:
        with ui.card().classes("app-card w-full max-w-md"):
            with ui.column().classes("gap-1 mb-2"):
                ui.label("Thêm kênh YouTube").classes(
                    "text-xl font-semibold leading-snug text-gray-900"
                )
                ui.label(
                    "Nhập tài khoản để mở phiên đăng nhập và đồng bộ danh sách kênh."
                ).classes("app-section-copy")

            email_input = ui.input("Email").props("outlined").classes("w-full")
            ui_refs["email_input"] = email_input
            password_input = (
                ui.input("Mật khẩu", password=True, password_toggle_button=True)
                .props("outlined")
                .classes("w-full")
            )
            ui_refs["password_input"] = password_input
            remember_checkbox = ui.checkbox(
                "Ghi nhớ thông tin đăng nhập",
                value=True,
            ).classes("text-sm text-gray-600")

            def clear_login_inputs():
                email_input.value = ""
                password_input.value = ""
                ui.notify("Đã xóa thông tin trong biểu mẫu", type="info")

            with ui.row().classes("w-full justify-between items-center mt-2"):
                ui.button(
                    "Xóa nội dung",
                    icon="backspace",
                    on_click=clear_login_inputs,
                ).props("flat").classes("text-gray-500")
                with ui.row().classes("gap-2"):
                    ui.button(
                        "Đóng",
                        icon="close",
                        on_click=login_dialog.close,
                    ).classes("app-button-secondary")
                    ui.button(
                        "Tiếp tục",
                        icon="arrow_forward",
                        on_click=on_login,
                    ).classes("app-button-primary")

            load_credentials()

    license_info = get_license_info()
    expiry_text = format_expiry(license_info)

    with page_shell():
        with page_header(
            "Tài khoản & kênh",
            "Quản lý các kênh YouTube được sử dụng trong tác vụ tự động hóa.",
            eyebrow="Workspace",
        ):
            ui.button(
                "Thêm kênh",
                icon="add",
                on_click=login_dialog.open,
            ).classes("app-button-primary")

        with app_card():
            with section_header(
                "Kênh YouTube",
                "Danh sách kênh được lưu riêng cho phiên bản ứng dụng này.",
            ):
                channel_count_label = ui.label("0 kênh").classes(
                    "text-xs font-medium text-gray-500"
                )
                ui.button(
                    icon="refresh",
                    on_click=lambda: refresh_channel_list(),
                ).props("flat round dense").classes("app-icon-button").tooltip(
                    "Làm mới danh sách"
                )
                with ui.button(icon="more_horiz").props(
                    "flat round dense"
                ).classes("app-icon-button") as more_actions_button:
                    with ui.menu().props("auto-close"):
                        ui.menu_item(
                            "Xóa tất cả kênh",
                            on_click=confirm_delete_all,
                        ).classes("text-red-600")

            channels_container = ui.column().classes("w-full gap-0")

        with app_card(compact=True):
            with ui.row().classes("w-full items-center gap-3"):
                with ui.element("div").classes(
                    "w-9 h-9 rounded-lg bg-emerald-50 text-emerald-600 grid place-items-center shrink-0"
                ):
                    ui.icon("o_verified_user").classes("text-xl")
                with ui.column().classes("gap-0 flex-1 min-w-0"):
                    ui.label("Giấy phép ứng dụng").classes(
                        "text-sm font-semibold text-gray-800"
                    )
                    ui.label(
                        f"{'Đang hoạt động' if license_info else 'Chưa kích hoạt'} · "
                        f"Thời hạn: {expiry_text}"
                    ).classes("text-xs text-gray-500 truncate")
                status_badge(
                    "Đã kích hoạt" if license_info else "Cần kiểm tra",
                    "success" if license_info else "warning",
                )

    def refresh_channel_list():
        channels = get_channels_info()
        channels_container.clear()
        channel_count_label.set_text(f"{len(channels)} kênh")
        more_actions_button.set_visibility(bool(channels))

        with channels_container:
            if not channels:
                empty_state(
                    "Chưa có kênh YouTube",
                    "Đăng nhập để đồng bộ kênh đầu tiên và bắt đầu chạy tác vụ.",
                    icon="o_video_library",
                    action_label="Thêm kênh",
                    on_action=login_dialog.open,
                )
                return

            with app_table(
                "minmax(240px, 1.5fr) minmax(220px, 1fr) 140px 44px"
            ):
                with ui.element("div").classes("app-table-header"):
                    ui.label("Kênh")
                    ui.label("Channel ID")
                    ui.label("Trạng thái")
                    ui.label("")
                for channel_data in channels:
                    name = channel_data.name
                    avatar = channel_data.img_src
                    channel_id = channel_data.id
                    with ui.element("div").classes("app-table-row"):
                        with ui.row().classes("items-center gap-3 min-w-0"):
                            if avatar:
                                ui.image(avatar).classes(
                                    "w-8 h-8 rounded-lg object-cover shrink-0"
                                )
                            else:
                                with ui.element("div").classes(
                                    "app-account-avatar shrink-0"
                                ):
                                    ui.icon("smart_display").classes("text-base")
                            with ui.column().classes("gap-0 min-w-0"):
                                ui.label(name).classes(
                                    "text-sm font-semibold text-gray-800 truncate"
                                )
                                ui.label("YouTube channel").classes(
                                    "text-[11px] text-gray-400"
                                )
                        ui.label(channel_id).classes(
                            "text-xs text-gray-500 truncate"
                        ).tooltip(channel_id)
                        status_badge("Đã kết nối", "success")
                        ui.button(
                            icon="delete_outline",
                            on_click=create_delete_click_handler(channel_id, name),
                        ).props("flat round dense").classes("app-icon-button")

    refresh_channel_list()
