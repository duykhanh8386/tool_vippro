import asyncio
import time
from datetime import datetime

from loguru import logger
from nicegui import context, ui

from src.audio_recovery import (
    RECOVERY_SCAN_MODE_ALL,
    RECOVERY_SCAN_MODE_SELECTED,
    acknowledge_channel_refresh,
    get_audio_recovery_scan_preferences,
    get_audio_recovery_state,
    run_audio_recovery_cycle,
    set_audio_recovery_scan_preferences,
)
from src.channel_scanner import (
    AUTHENTICATION_TIMEOUT_SECONDS,
    ChannelFetcher,
    ChannelScanError,
)
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
    ui_refs = {
        "email_input": None,
        "password_input": None,
        "login_title": None,
        "login_copy": None,
        "login_submit": None,
    }
    try:
        page_client = context.client
    except RuntimeError:
        page_client = None
    scan_state = {
        "run_context": None,
        "deadline": None,
        "cancel_requested": False,
        "authenticated": False,
        "operation": "add_new",
        "include_channel_ids": set(),
        "exclude_channel_ids": set(),
    }
    recovery_scope_refs = {
        "toggle": None,
        "summary": None,
        "selection_actions": None,
    }

    def client_is_alive() -> bool:
        return page_client is not None and not getattr(page_client, "_deleted", False)

    def best_effort_ui(action: str, callback) -> bool:
        if not client_is_alive():
            return False
        try:
            # fetch_channel_data runs as a background task, which has no active
            # NiceGUI slot. Re-enter the page client before creating/updating UI.
            with page_client:
                callback()
            return True
        except Exception as exc:
            logger.warning("Studio UI action '{}' was skipped: {}", action, exc)
            return False

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

    async def fetch_channel_data(
        email,
        password,
        *,
        operation: str,
        include_channel_ids: set[str],
        exclude_channel_ids: set[str],
    ):
        run_context = create_run_context("studio_channel_scan")
        scan_state["run_context"] = run_context
        channel_fetcher = ChannelFetcher()
        try:
            logger.info("Fetching channel data...")
            with bind_run_context(run_context):
                report = await asyncio.to_thread(
                    channel_fetcher.run,
                    email=email,
                    password=password,
                    on_authenticated=lambda: scan_state.update(authenticated=True),
                    include_channel_ids=(
                        include_channel_ids
                        if operation == "reload_selected"
                        else None
                    ),
                    exclude_channel_ids=(
                        exclude_channel_ids
                        if operation == "add_new"
                        else None
                    ),
                )
            refreshed_channel_ids = [
                str(channel.get("id") or "")
                for channel in report.channels
                if isinstance(channel, dict) and channel.get("id")
            ]
            if acknowledge_channel_refresh(refreshed_channel_ids):
                asyncio.create_task(run_audio_recovery_cycle())
            if operation == "reload_selected":
                requested_count = len(include_channel_ids)
                missing_count = len(report.missing_channel_ids)
                message = (
                    f"Đã load lại {len(report.channels)}/{requested_count} kênh đã chọn."
                )
                if missing_count:
                    missing_preview = ", ".join(report.missing_channel_ids[:5])
                    if missing_count > 5:
                        missing_preview += ", ..."
                    message += (
                        f" Không tìm thấy {missing_count} kênh trong tài khoản; "
                        f"dữ liệu cũ vẫn được giữ nguyên: {missing_preview}."
                    )
                if report.failures:
                    message += f" Có {len(report.failures)} kênh load lại bị lỗi."
                if report.unidentified_channel_count:
                    message += (
                        f" Bỏ qua an toàn {report.unidentified_channel_count} hồ sơ "
                        "không đọc được Channel ID."
                    )
                result_type = (
                    "warning"
                    if report.failures
                    or missing_count
                    or report.unidentified_channel_count
                    else "positive"
                )
                best_effort_ui(
                    "notify selected channel reload",
                    lambda: ui.notify(message, type=result_type),
                )
            else:
                message = f"Đã thêm {len(report.channels)} kênh mới."
                if not report.channels and not report.failures:
                    message = "Không có kênh mới trong tài khoản này."
                if report.failures:
                    message += f" Có {len(report.failures)} kênh mới bị lỗi."
                if report.unidentified_channel_count:
                    message += (
                        f" Bỏ qua an toàn {report.unidentified_channel_count} hồ sơ "
                        "không đọc được Channel ID."
                    )
                result_type = (
                    "warning"
                    if report.failures or report.unidentified_channel_count
                    else ("positive" if report.channels else "info")
                )
                best_effort_ui(
                    "notify add new channel scan",
                    lambda: ui.notify(message, type=result_type),
                )
        except TaskStopped:
            logger.info("Channel scan stopped")
            best_effort_ui(
                "notify channel scan stopped",
                lambda: ui.notify("Đã dừng quét kênh.", type="info"),
            )
        except ChannelScanError as exc:
            logger.error("Channel scan failed: {}", exc)
            best_effort_ui(
                "notify classified channel scan error",
                lambda: ui.notify(
                    f"Không thể lấy dữ liệu kênh: {exc}", type="negative"
                ),
            )
        except Exception as exc:
            logger.exception(f"Error fetching channels: {exc}")
            best_effort_ui(
                "notify unexpected channel scan error",
                lambda: ui.notify(
                    "Không thể lấy dữ liệu kênh do lỗi không xác định.",
                    type="negative",
                ),
            )
        finally:
            run_context.cleanup()
            if scan_state["run_context"] is run_context:
                scan_state["run_context"] = None
                scan_state["deadline"] = None
            best_effort_ui("close channel scan popup", processing_popup.close)
            best_effort_ui("refresh channel list", refresh_channel_list)

    def open_channel_login(operation: str) -> None:
        if scan_state["run_context"] is not None:
            ui.notify("Đang quét kênh, vui lòng chờ hoặc bấm Hủy.", type="warning")
            return
        if operation == "reload_selected":
            preferences = recovery_scope_snapshot()
            if preferences["scan_mode"] != RECOVERY_SCAN_MODE_SELECTED:
                ui.notify(
                    "Hãy chuyển sang chế độ Danh sách kênh rồi chọn các kênh cần load lại.",
                    type="warning",
                )
                return
            selected_ids = {
                str(channel_id).strip()
                for channel_id in preferences["selected_channel_ids"]
                if str(channel_id).strip()
            }
            if not selected_ids:
                ui.notify("Chưa chọn kênh nào để load lại.", type="warning")
                return
            scan_state["operation"] = operation
            scan_state["include_channel_ids"] = selected_ids
            scan_state["exclude_channel_ids"] = set()
            ui_refs["login_title"].set_text("Load lại kênh đã chọn")
            ui_refs["login_copy"].set_text(
                f"Đăng nhập tài khoản chứa {len(selected_ids)} kênh đã chọn. "
                "Tool chỉ click đúng Channel ID trùng khớp."
            )
            ui_refs["login_submit"].set_text("Load lại")
        else:
            existing_ids = {
                str(channel.id).strip()
                for channel in (get_channels_info() or [])
                if str(channel.id).strip()
            }
            scan_state["operation"] = "add_new"
            scan_state["include_channel_ids"] = set()
            scan_state["exclude_channel_ids"] = existing_ids
            ui_refs["login_title"].set_text("Thêm kênh YouTube mới")
            ui_refs["login_copy"].set_text(
                "Đăng nhập tài khoản YouTube. Tool chỉ click các Channel ID chưa có "
                "trong danh sách hiện tại."
            )
            ui_refs["login_submit"].set_text("Tìm kênh mới")
        login_dialog.open()

    def on_login():
        if scan_state["run_context"] is not None:
            ui.notify("Đang quét kênh, vui lòng chờ hoặc bấm Hủy.", type="warning")
            return
        email = str(email_input.value or "").strip()
        password = str(password_input.value or "")
        if not email or not password:
            ui.notify("Vui lòng nhập đầy đủ email và mật khẩu.", type="warning")
            return
        if remember_checkbox.value:
            save_credentials()
        else:
            state_manager.clear_state("studio_credentials")
        login_dialog.close()
        scan_state["deadline"] = time.monotonic() + AUTHENTICATION_TIMEOUT_SECONDS
        scan_state["cancel_requested"] = False
        scan_state["authenticated"] = False
        processing_status.set_text(
            "Bạn có tối đa 10 phút để hoàn tất xác thực Google."
        )
        auth_countdown.set_text("Thời gian xác thực còn lại: 10:00")
        cancel_scan_button.set_enabled(True)
        processing_popup.open()
        asyncio.create_task(
            fetch_channel_data(
                email,
                password,
                operation=str(scan_state["operation"]),
                include_channel_ids=set(scan_state["include_channel_ids"]),
                exclude_channel_ids=set(scan_state["exclude_channel_ids"]),
            )
        )

    async def cancel_channel_scan():
        run_context = scan_state["run_context"]
        if run_context is None or scan_state["cancel_requested"]:
            return
        scan_state["cancel_requested"] = True
        best_effort_ui(
            "disable channel scan cancel button",
            lambda: cancel_scan_button.set_enabled(False),
        )
        best_effort_ui(
            "show channel scan cancellation",
            lambda: processing_status.set_text("Đang hủy và đóng cửa sổ Chrome..."),
        )
        await asyncio.to_thread(run_context.request_stop)

    async def stop_scan_when_client_disconnects():
        """Stop the owned Selenium session when this page is closed/reloaded."""
        run_context = scan_state["run_context"]
        if run_context is None:
            return
        scan_state["cancel_requested"] = True
        logger.info("Studio page disconnected; stopping channel scan")
        await asyncio.to_thread(run_context.request_stop)

    if page_client is not None:
        page_client.on_disconnect(stop_scan_when_client_disconnects)

    def update_auth_countdown():
        deadline = scan_state["deadline"]
        if deadline is None or not client_is_alive():
            return
        if scan_state["authenticated"]:
            scan_state["deadline"] = None
            best_effort_ui(
                "show channel scan authenticated state",
                lambda: (
                    processing_status.set_text(
                        "Xác thực hoàn tất, đang đồng bộ các kênh..."
                    ),
                    auth_countdown.set_text("Đã xác thực"),
                ),
            )
            return
        remaining = max(0, int(deadline - time.monotonic() + 0.999))
        minutes, seconds = divmod(remaining, 60)
        best_effort_ui(
            "update channel scan authentication countdown",
            lambda: auth_countdown.set_text(
                f"Thời gian xác thực còn lại: {minutes:02d}:{seconds:02d}"
            ),
        )

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

    def recovery_scope_snapshot() -> dict:
        try:
            return get_audio_recovery_scan_preferences()
        except Exception as exc:
            logger.error("Could not read Auto Registry channel scope: {}", exc)
            return {
                "scan_mode": RECOVERY_SCAN_MODE_ALL,
                "selected_channel_ids": [],
            }

    def update_recovery_scope_summary(channels=None) -> None:
        summary = recovery_scope_refs.get("summary")
        if summary is None:
            return
        channels = list(channels if channels is not None else (get_channels_info() or []))
        preferences = recovery_scope_snapshot()
        mode = preferences["scan_mode"]
        selected = set(preferences["selected_channel_ids"])
        try:
            registry_channel_ids = set(
                (get_audio_recovery_state().get("entries") or {}).keys()
            )
        except Exception:
            registry_channel_ids = set()

        if mode == RECOVERY_SCAN_MODE_ALL:
            summary.set_text(
                "Mặc định: quét video công khai của toàn bộ "
                f"{len(registry_channel_ids)} kênh đang có trong Auto Registry."
            )
        else:
            visible_ids = {channel.id for channel in channels}
            visible_selected = len(selected & visible_ids)
            summary.set_text(
                f"Đã chọn {visible_selected}/{len(channels)} kênh trong danh sách. "
                "Kênh bỏ chọn vẫn được giữ nguyên Registry và lịch sử."
            )

        actions = recovery_scope_refs.get("selection_actions")
        if actions is not None:
            actions.set_visibility(mode == RECOVERY_SCAN_MODE_SELECTED)

    def on_recovery_scope_change(event) -> None:
        requested_mode = str(event.value or "").strip()
        previous = recovery_scope_snapshot()
        if requested_mode not in {
            RECOVERY_SCAN_MODE_ALL,
            RECOVERY_SCAN_MODE_SELECTED,
        }:
            requested_mode = RECOVERY_SCAN_MODE_ALL
        if not set_audio_recovery_scan_preferences(scan_mode=requested_mode):
            toggle = recovery_scope_refs.get("toggle")
            if toggle is not None:
                toggle.value = previous["scan_mode"]
            ui.notify("Không thể lưu chế độ quét Auto Registry.", type="negative")
            return
        refresh_channel_list()
        if requested_mode == RECOVERY_SCAN_MODE_ALL:
            ui.notify(
                "Auto Registry sẽ quét tất cả kênh trong lịch sử.",
                type="positive",
            )
        else:
            ui.notify(
                "Auto Registry chỉ quét các kênh được chọn trong danh sách.",
                type="positive",
            )

    def create_recovery_channel_toggle_handler(channel_id: str):
        def handler(event) -> None:
            preferences = recovery_scope_snapshot()
            if preferences["scan_mode"] != RECOVERY_SCAN_MODE_SELECTED:
                return
            selected = set(preferences["selected_channel_ids"])
            if bool(event.value):
                selected.add(channel_id)
            else:
                selected.discard(channel_id)
            if not set_audio_recovery_scan_preferences(
                scan_mode=RECOVERY_SCAN_MODE_SELECTED,
                selected_channel_ids=sorted(selected),
            ):
                ui.notify("Không thể lưu danh sách kênh tự động quét.", type="negative")
                refresh_channel_list()
                return
            update_recovery_scope_summary()

        return handler

    def select_all_recovery_channels() -> None:
        channel_ids = [channel.id for channel in (get_channels_info() or [])]
        if set_audio_recovery_scan_preferences(
            scan_mode=RECOVERY_SCAN_MODE_SELECTED,
            selected_channel_ids=channel_ids,
        ):
            refresh_channel_list()
            ui.notify(f"Đã chọn {len(channel_ids)} kênh để tự động quét.", type="positive")
        else:
            ui.notify("Không thể lưu danh sách kênh tự động quét.", type="negative")

    def deselect_all_recovery_channels() -> None:
        if set_audio_recovery_scan_preferences(
            scan_mode=RECOVERY_SCAN_MODE_SELECTED,
            selected_channel_ids=[],
        ):
            refresh_channel_list()
            ui.notify("Đã bỏ chọn tất cả kênh; Registry và lịch sử vẫn được giữ.", type="info")
        else:
            ui.notify("Không thể lưu danh sách kênh tự động quét.", type="negative")

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
            processing_status = ui.label(
                "Bạn có tối đa 10 phút để hoàn tất xác thực Google."
            ).classes("text-sm text-gray-600")
            auth_countdown = ui.label(
                "Thời gian xác thực còn lại: 10:00"
            ).classes("text-lg font-semibold text-primary")
            cancel_scan_button = ui.button(
                "Hủy",
                icon="close",
                on_click=cancel_channel_scan,
            ).classes("app-button-secondary mt-2")

    ui.timer(1.0, update_auth_countdown)

    with ui.dialog() as login_dialog:
        with ui.card().classes("app-card w-full max-w-md"):
            with ui.column().classes("gap-1 mb-2"):
                login_title = ui.label("Thêm kênh YouTube mới").classes(
                    "text-xl font-semibold leading-snug text-gray-900"
                )
                ui_refs["login_title"] = login_title
                login_copy = ui.label(
                    "Đăng nhập tài khoản YouTube. Tool chỉ click các Channel ID chưa có "
                    "trong danh sách hiện tại."
                ).classes("app-section-copy")
                ui_refs["login_copy"] = login_copy

            email_input = ui.input("Email").props("outlined").classes("w-full")
            ui_refs["email_input"] = email_input
            password_input = (
                ui.input("Mật khẩu", password=True, password_toggle_button=True)
                .props("outlined")
                .classes("w-full")
            )
            ui_refs["password_input"] = password_input
            def on_remember_change(event):
                if not event.value:
                    state_manager.clear_state("studio_credentials")

            remember_checkbox = ui.checkbox(
                "Ghi nhớ thông tin đăng nhập",
                value=True,
                on_change=on_remember_change,
            ).classes("text-sm text-gray-600")

            def clear_login_inputs():
                email_input.value = ""
                password_input.value = ""
                remember_checkbox.value = False
                if state_manager.clear_state("studio_credentials"):
                    ui.notify(
                        "Đã xóa thông tin đăng nhập khỏi biểu mẫu và dữ liệu đã lưu.",
                        type="positive",
                    )
                else:
                    ui.notify(
                        "Đã xóa biểu mẫu nhưng không thể xóa dữ liệu đã lưu.",
                        type="warning",
                    )

            with ui.row().classes("w-full justify-between items-center mt-2"):
                ui.button(
                    "Xóa thông tin",
                    icon="backspace",
                    on_click=clear_login_inputs,
                ).props("flat").classes("text-gray-500")
                with ui.row().classes("gap-2"):
                    ui.button(
                        "Đóng",
                        icon="close",
                        on_click=login_dialog.close,
                    ).classes("app-button-secondary")
                    login_submit = ui.button(
                        "Tìm kênh mới",
                        icon="arrow_forward",
                        on_click=on_login,
                    ).classes("app-button-primary")
                    ui_refs["login_submit"] = login_submit

            load_credentials()

    license_info = get_license_info()
    expiry_text = format_expiry(license_info)

    with page_shell():
        with page_header(
            "Tài khoản & kênh",
            "Quản lý các kênh YouTube được sử dụng trong tác vụ tự động hóa.",
            eyebrow="Workspace",
        ):
            with ui.row().classes("items-center gap-2"):
                ui.button(
                    "Load lại kênh",
                    icon="refresh",
                    on_click=lambda: open_channel_login("reload_selected"),
                ).classes("app-button-secondary")
                ui.button(
                    "Thêm kênh",
                    icon="add",
                    on_click=lambda: open_channel_login("add_new"),
                ).classes("app-button-primary")

        with app_card():
            initial_recovery_scope = recovery_scope_snapshot()
            with section_header(
                "Phạm vi Auto Registry",
                "Chọn quét toàn bộ kênh trong lịch sử hoặc chỉ các kênh đánh dấu bên dưới.",
            ):
                pass
            with ui.row().classes("w-full items-center gap-3 flex-wrap"):
                recovery_scope_toggle = ui.toggle(
                    {
                        RECOVERY_SCAN_MODE_ALL: "Tất cả các kênh",
                        RECOVERY_SCAN_MODE_SELECTED: "Danh sách kênh",
                    },
                    value=initial_recovery_scope["scan_mode"],
                    on_change=on_recovery_scope_change,
                ).props("no-caps")
                recovery_scope_refs["toggle"] = recovery_scope_toggle
                with ui.row().classes(
                    "items-center gap-1"
                ) as recovery_selection_actions:
                    ui.button(
                        "Chọn tất cả",
                        icon="done_all",
                        on_click=select_all_recovery_channels,
                    ).props("flat dense no-caps").classes("text-emerald-700")
                    ui.button(
                        "Bỏ chọn tất cả",
                        icon="remove_done",
                        on_click=deselect_all_recovery_channels,
                    ).props("flat dense no-caps").classes("text-gray-600")
                recovery_scope_refs["selection_actions"] = (
                    recovery_selection_actions
                )
                recovery_selection_actions.set_visibility(
                    initial_recovery_scope["scan_mode"]
                    == RECOVERY_SCAN_MODE_SELECTED
                )
            recovery_scope_summary = ui.label("").classes(
                "text-xs text-gray-500 mb-2"
            )
            recovery_scope_refs["summary"] = recovery_scope_summary

            ui.separator().classes("my-2")
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
        channels = get_channels_info() or []
        preferences = recovery_scope_snapshot()
        recovery_scan_mode = preferences["scan_mode"]
        recovery_selected_ids = set(preferences["selected_channel_ids"])
        channels_container.clear()
        channel_count_label.set_text(f"{len(channels)} kênh")
        more_actions_button.set_visibility(bool(channels))
        toggle = recovery_scope_refs.get("toggle")
        if toggle is not None and toggle.value != recovery_scan_mode:
            toggle.value = recovery_scan_mode
        update_recovery_scope_summary(channels)

        with channels_container:
            if not channels:
                empty_state(
                    "Chưa có kênh YouTube",
                    "Đăng nhập để đồng bộ kênh đầu tiên và bắt đầu chạy tác vụ.",
                    icon="o_video_library",
                    action_label="Thêm kênh",
                    on_action=lambda: open_channel_login("add_new"),
                )
                return

            with app_table(
                "52px minmax(240px, 1.5fr) minmax(220px, 1fr) 140px 44px"
            ):
                with ui.element("div").classes("app-table-header"):
                    ui.label("Quét")
                    ui.label("Kênh")
                    ui.label("Channel ID")
                    ui.label("Trạng thái")
                    ui.label("")
                for channel_data in channels:
                    name = channel_data.name
                    avatar = channel_data.img_src
                    channel_id = channel_data.id
                    with ui.element("div").classes("app-table-row"):
                        recovery_checkbox = ui.checkbox(
                            value=(
                                recovery_scan_mode == RECOVERY_SCAN_MODE_ALL
                                or channel_id in recovery_selected_ids
                            ),
                            on_change=create_recovery_channel_toggle_handler(
                                channel_id
                            ),
                        ).props("dense")
                        if recovery_scan_mode == RECOVERY_SCAN_MODE_ALL:
                            recovery_checkbox.props("disable")
                            recovery_checkbox.tooltip(
                                "Chế độ Tất cả các kênh đang bật"
                            )
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
