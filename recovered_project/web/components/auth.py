import time

from nicegui import ui

from src.route_manager import router


def create_auth_page():
    with ui.element("div").classes("app-auth-page"):
        with ui.card().classes("app-auth-panel"):
            with ui.column().classes("w-full items-center text-center gap-2 mb-3"):
                ui.image("/tuat-videos-assets/logo.png").classes(
                    "w-16 h-16 rounded-xl object-cover mb-1"
                )
                ui.label("Kích hoạt Tuất Videos").classes(
                    "text-2xl font-bold leading-tight text-gray-900"
                )
                ui.label(
                    "Nhập license key để mở workspace và sử dụng các tác vụ tự động hóa."
                ).classes("app-section-copy max-w-sm")

            license_input = (
                ui.input("License key")
                .props('outlined clearable autocomplete="off"')
                .classes("w-full")
            )

            if router.is_authenticated():
                ui.notify("Ứng dụng đã được xác thực!", type="positive")
                time.sleep(2)
                ui.navigate.to(router.start_path)
            else:
                with ui.row().classes(
                    "w-full items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3"
                ):
                    ui.icon("o_info").classes("text-lg text-amber-600 shrink-0")
                    ui.label(
                        "License chưa được kích hoạt hoặc đã hết hạn."
                    ).classes("text-xs text-amber-700")

            def handle_auth():
                key = license_input.value
                is_auth, message = router.verify_activation_key(key)
                if is_auth:
                    ui.notify(message, type="positive")
                    ui.navigate.to(router.start_path)
                    return
                ui.notify(message, type="negative")

            def clear_all_inputs():
                license_input.value = ""
                ui.notify("Đã xóa license key", type="info")

            with ui.row().classes("w-full gap-2 mt-2"):
                ui.button(
                    "Xóa nội dung",
                    icon="backspace",
                    on_click=clear_all_inputs,
                ).classes("app-button-secondary flex-1")
                ui.button(
                    "Kích hoạt",
                    icon="key",
                    on_click=handle_auth,
                ).classes("app-button-primary flex-1")

            ui.label(
                "License và dữ liệu được lưu riêng trên thiết bị này."
            ).classes("text-[11px] text-gray-400 text-center mt-2")
