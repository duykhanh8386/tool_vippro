"""UI for copying reference metadata, generating thumbnails and daily scheduling."""
import csv
import io
import asyncio
from collections import Counter

from nicegui import context, ui

from src.utils import get_channels_info
from src.video_publishing import (
    COPYRIGHT_LABELS, VIDEO_SCOPE_LABELS, publishing_row_disabled_reason,
    publishing_row_matches, publishing_row_selectable,
)
from src.video_publishing_tasks import STATUS_LABELS, get_video_publishing_controller
from web.components.common import create_channel_selection, select_directory
from web.theme import app_card, page_header, page_shell, section_header


def create_video_publishing_page():
    controller = get_video_publishing_controller()
    client = context.client
    settings = controller.snapshot()["settings"]
    fields, buttons = {}, {}
    syncing = {"active": False, "revision": -1}
    visible = {"ids": []}

    def invoke(callback):
        try:
            callback()
            return True
        except ValueError as exc:
            ui.notify(str(exc), type="negative")
            return False
        finally:
            refresh()

    def change(key, value):
        if not syncing["active"]:
            return invoke(lambda: controller.change_settings(**{key: value}))

    def choose_channels(identifiers):
        return change("channel_ids", list(identifiers or []))

    def set_cookie():
        if invoke(lambda: controller.set_cookie(cookie_field.value or "")):
            cookie_field.set_value("")
            ui.notify("Đã nhận cookie. Bấm Mở / kiểm tra phiên để xác nhận đăng nhập ChatGPT.", type="positive")

    async def session_action(action):
        try:
            await asyncio.to_thread(action)
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
        finally:
            refresh()

    async def prepare_session():
        await session_action(controller.prepare_chatgpt_session)

    async def close_session():
        await session_action(controller.close_chatgpt_session)

    def choose_folder():
        folder = select_directory(initial_dir=fields["output_folder"].value or None, title="Chọn thư mục lưu thumbnail")
        if folder:
            change("output_folder", folder)

    def select_rows(event):
        if not syncing["active"]:
            invoke(lambda: controller.select((row["video_id"] for row in event.selection), within_ids=visible["ids"]))

    def select_all():
        invoke(controller.select_filtered)

    def export():
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(["Channel ID", "Video ID", "Loại video", "Bản quyền", "Bài nhạc", "Video tham chiếu", "Cách chọn tham chiếu", "Độ lệch giây", "Title mới", "Description mới", "Thumbnail", "Lịch UTC+7", "Trạng thái", "Chi tiết"])
        for row in controller.snapshot()["rows"]:
            reference = row.get("reference") or {}
            values = [row["channel_id"], row["video_id"], row.get("visibility_label", "Cần quét lại loại video"), row["copyright_label"], row["song"], reference.get("url", ""),
                      reference.get("selection_label", ""), reference.get("duration_delta_seconds", ""),
                      reference.get("title", ""), reference.get("description", ""), row.get("thumbnail_path", ""),
                      row.get("publish_label", ""), STATUS_LABELS[row["status"]], row.get("detail", "")]
            writer.writerow(["'" + value if isinstance(value, str) and value.startswith(("=", "+", "-", "@")) else value for value in values])
        ui.download(stream.getvalue().encode("utf-8-sig"), "seo_thumbnail_lich_dang.csv", media_type="text/csv")

    def details(event):
        row = next((item for item in controller.snapshot()["rows"] if item["video_id"] == event.args), None)
        if not row:
            return
        with ui.dialog() as dialog, ui.card().classes("w-[900px] max-w-full"):
            ui.label(row["old_title"]).classes("text-lg font-semibold break-words")
            ui.label(f"{row['channel_id']} · {row['video_id']}").classes("text-xs text-gray-500")
            ui.label(f"Loại video: {row.get('visibility_label', 'Cần quét lại')} · {row['copyright_label']}").classes("text-sm")
            reference = row.get("reference") or {}
            if reference:
                ui.link("Mở video tham chiếu", reference["url"], new_tab=True)
                ui.label(reference.get("selection_label", "Đã chọn từ phiên trước")).classes("text-sm text-emerald-700")
                if row.get("duration_seconds"):
                    ui.label(f"Thời lượng video hiện tại: {row['duration_seconds']:g} giây").classes("text-xs text-gray-500")
                ui.input("Title sẽ chép nguyên văn", value=reference["title"]).props("outlined readonly").classes("w-full")
                ui.textarea("Description sẽ chép nguyên văn", value=reference["description"]).props("outlined readonly autogrow").classes("w-full")
                ui.image(reference["thumbnail"]).classes("w-96 max-w-full")
            query = ui.input("Bài nhạc dùng tìm kiếm", value=row["song"]).props("outlined").classes("w-full")
            if not controller.snapshot()["busy"] and row["status"] not in {"skipped", "successful"} and not row.get("metadata_copied"):
                def update_query():
                    if invoke(lambda: controller.set_song(row["video_id"], query.value)):
                        dialog.close()

                ui.button("Lưu bài nhạc và tìm lại tham chiếu khi chạy", icon="search", on_click=update_query).props("outline")
            else:
                query.props("readonly")
            ui.label("Thumbnail lưu tại: " + row.get("thumbnail_path", "Chưa tạo")).classes("text-sm break-all")
            if row.get("conversation_url"):
                ui.link("Mở hội thoại tạo thumbnail", row["conversation_url"], new_tab=True)
            ui.label(row.get("detail", "")).classes("text-sm break-words")
            ui.button("Đóng", on_click=dialog.close).props("flat")
        dialog.open()

    def refresh():
        if getattr(client, "_deleted", False):
            return
        data = controller.snapshot()
        syncing["active"] = True
        try:
            job_busy = data["busy"]
            busy = job_busy or data["session_busy"]
            config = data["settings"]
            copyright_counts = Counter(row["copyright"] for row in data["rows"] if publishing_row_matches(row, scope=config["scope"]))
            type_counts = Counter(row.get("visibility_type", "unknown") for row in data["rows"])
            scope_counts = {**type_counts, "all": len(data["rows"]),
                            "unpublished": sum(type_counts[key] for key in ("draft", "private", "unlisted"))}
            for key, options in (
                ("categories", {kind: f"{label} ({copyright_counts[kind]})" for kind, label in COPYRIGHT_LABELS.items()}),
                ("scope", {kind: f"{label} ({scope_counts.get(kind, 0)})" for kind, label in VIDEO_SCOPE_LABELS.items()}),
            ):
                if fields[key].options != options:
                    fields[key].set_options(options)
            for key, field in fields.items():
                if field.value != config[key]:
                    field.set_value(config[key])
                field.set_enabled(not busy)
            fields["limit"].set_enabled(not busy and not config["scan_all"])
            from_links = config["channel_source"] == "links"
            fields["channel_links"].set_visibility(from_links)
            channel_picker.set_visibility(not from_links)
            source_status.set_text("Nguồn quét: các link kênh đã dán." if from_links else f"Nguồn quét: {len(config['channel_ids'])} thẻ kênh đã chọn.")
            cookie_field.set_enabled(not busy)
            for key, button in buttons.items():
                button.set_enabled(not busy)
            buttons["stop"].set_enabled(job_busy)
            chosen = sum(bool(row.get("selected")) and publishing_row_selectable(row) for row in data["rows"])
            filtered = [row for row in data["rows"] if publishing_row_matches(row, scope=config["scope"], categories=config["categories"])]
            selectable_count = sum(publishing_row_selectable(row) for row in filtered)
            shown_selected = sum(bool(row.get("selected")) for row in filtered)
            buttons["scan"].set_enabled(not busy and bool(config["channel_links"].strip() if from_links else config["channel_ids"]))
            buttons["select"].set_enabled(not busy and selectable_count > 0)
            buttons["deselect"].set_enabled(not busy and shown_selected > 0)
            buttons["clear_selection"].set_enabled(not busy and chosen > 0)
            for key in ("plan", "run"):
                buttons[key].set_enabled(not busy and chosen > 0)
            message.set_text(data["message"])
            scheduled_count=sum(row.get("visibility_type")=="scheduled" or row["status"]=="successful" for row in data["rows"])
            summary.set_text(f"{len(data['rows'])} đã quét · {len(filtered)} trong bộ lọc · {selectable_count} có thể tích chọn · {chosen} đã chọn toàn bộ ({chosen - shown_selected} ngoài bộ lọc) · {scheduled_count} video có lịch · {sum(row['status'] == 'successful' for row in data['rows'])} hoàn tất tác vụ")
            rescan_hint.set_visibility(data["needs_rescan"])
            cookie_status.set_text("Đã nhận cookie nhập tay." if data["has_cookie"] else "Có thể dùng phiên Chrome đã lưu hoặc đăng nhập trực tiếp.")
            session_status.set_text(data["chatgpt_status"])
            selection = None if busy else "multiple"
            if table.selection != selection:
                table.selection = selection
            visible["ids"] = [row["video_id"] for row in filtered]
            if data["revision"] != syncing["revision"]:
                rows = [{**row, "status_label": STATUS_LABELS[row["status"]],
                         "visibility_label": row.get("visibility_label", "Cần quét lại loại video"),
                         "can_select": not busy and publishing_row_selectable(row),
                         "disabled_reason": "Tác vụ đang chạy." if busy else publishing_row_disabled_reason(row),
                         "reference_title": (row.get("reference") or {}).get("title", ""),
                         "reference_method": (row.get("reference") or {}).get("selection_label", ""),
                         "reference_url": (row.get("reference") or {}).get("url", ""),
                         "publish_label": row.get("publish_label", "")} for row in filtered]
                table.rows = rows
                table.selected = [row for row in rows if row.get("selected")]
                table.update()
                syncing["revision"] = data["revision"]
        finally:
            syncing["active"] = False

    with page_shell(), ui.column().classes("w-full min-w-0 gap-6"):
        with page_header("SEO, thumbnail & lên lịch", "Chép nguyên title/description từ video tìm kiếm, vẽ lại thumbnail bằng ChatGPT và đăng mỗi ngày một video trên từng kênh.", eyebrow="TÁC VỤ VIDEO"):
            buttons["export"] = ui.button("Xuất CSV", icon="download", on_click=export).props("outline")
        with app_card():
            with section_header("Nguồn kênh để quét", "Chọn rõ một nguồn trước khi quét."):
                pass
            fields["channel_source"] = ui.toggle({"selected": "Kênh đã chọn", "links": "Link kênh"}, value=settings["channel_source"],
                                                  on_change=lambda e: change("channel_source", e.value))
            source_status = ui.label().classes("text-sm text-emerald-700")
        with ui.column().classes("w-full") as channel_picker:
            create_channel_selection(get_channels_info() or [], choose_channels, multi_select=True,
                                     initial_selected_ids=settings["channel_ids"],
                                     can_change_selection=lambda: not (controller.snapshot()["busy"] or controller.snapshot()["session_busy"]) and controller.snapshot()["settings"]["channel_source"] == "selected")
        with app_card():
            with section_header("Quét video trong Studio", "Chỉ xử lý video chưa công khai; giữ các lịch đã đặt trên kênh."):
                buttons["scan"] = ui.button("Quét video", icon="manage_search", on_click=lambda: invoke(lambda: controller.start("scan")))
            fields["channel_links"] = ui.textarea("Link kênh YouTube", value=settings["channel_links"],
                                                  placeholder="Mỗi dòng một link /channel/UC… hoặc /@tenkenh. Dùng khi Nguồn kênh được đặt là Link kênh.",
                                                  on_change=lambda e: change("channel_links", e.value or "")).props("outlined autogrow").classes("w-full")
            fields["manual_ids"] = ui.textarea("Link video / Video ID (tùy chọn)", value=settings["manual_ids"],
                                               placeholder="Mỗi dòng một link hoặc ID của video đã có trong Studio. Để trống để quét cả kênh.",
                                               on_change=lambda e: change("manual_ids", e.value or "")).props("outlined autogrow").classes("w-full")
            with ui.row().classes("w-full gap-3 items-center flex-wrap"):
                fields["order"] = ui.select({"oldest": "Cũ trước", "newest": "Mới trước"}, label="Thứ tự đăng", value=settings["order"],
                                            on_change=lambda e: change("order", e.value)).props("outlined").classes("w-44")
                fields["scan_all"] = ui.switch("Quét hết video", value=settings["scan_all"], on_change=lambda e: change("scan_all", e.value))
                fields["limit"] = ui.number("Số video mỗi kênh", value=settings["limit"], min=1, max=10000, step=1,
                                            on_change=lambda e: change("limit", e.value)).props("outlined").classes("w-44")
            ui.label("Sau khi quét, lọc theo loại video và trạng thái bản quyền trong Danh sách xử lý để chọn video lên lịch.").classes("text-xs text-gray-500")
        with app_card():
            with section_header("ChatGPT vẽ thumbnail", "Dùng lại một phiên Chrome riêng của tool cho các lượt chạy."):
                buttons["session"] = ui.button("Mở / kiểm tra phiên", icon="open_in_browser", on_click=prepare_session).props("outline")
                buttons["close_session"] = ui.button("Đóng cửa sổ phiên", icon="close", on_click=close_session).props("flat")
            with ui.row().classes("w-full gap-3 items-end"):
                cookie_field = ui.input("Cookie ChatGPT tùy chọn (JSON hoặc Cookie header)", password=True, password_toggle_button=True).props("outlined autocomplete=off").classes("flex-1 min-w-0")
                buttons["cookie"] = ui.button("Nạp cookie", icon="key", on_click=set_cookie).props("outline")
                buttons["clear_cookie"] = ui.button("Bỏ cookie nhập tay", icon="clear", on_click=lambda: invoke(lambda: controller.set_cookie(""))).props("flat")
            cookie_status = ui.label().classes("text-xs text-gray-500")
            session_status = ui.label().classes("text-sm text-emerald-700 break-words")
            ui.label("Chrome lưu phiên riêng trên máy để dùng lại. Bạn có thể nạp cookie hoặc đăng nhập trong phiên này. Khi tác vụ đang chạy, tool chờ tối đa 10 phút để bạn đăng nhập/xác minh thủ công và tự tiếp tục gửi prompt khi sẵn sàng; bấm Dừng để hủy chờ. Ô cookie không được lưu vào cấu hình; Bỏ cookie nhập tay không đăng xuất phiên Chrome đã lưu.").classes("text-xs text-gray-500")
            fields["image_prompt"] = ui.textarea("Prompt chung vẽ lại thumbnail", value=settings["image_prompt"],
                                                 on_change=lambda e: change("image_prompt", e.value or "")).props("outlined autogrow").classes("w-full")
            with ui.row().classes("w-full gap-3 items-end"):
                fields["output_folder"] = ui.input("Thư mục lưu thumbnail (để trống dùng thư mục dữ liệu tool)", value=settings["output_folder"],
                                                    on_change=lambda e: change("output_folder", e.value or "")).props("outlined").classes("flex-1 min-w-0")
                buttons["folder"] = ui.button("Chọn thư mục", icon="folder_open", on_click=choose_folder).props("outline")
        with app_card():
            with section_header("Lịch đăng hằng ngày", "Mỗi kênh dùng cùng giờ cố định; tự bỏ qua ngày đã có video được lên lịch."):
                pass
            with ui.row().classes("w-full gap-3 items-end flex-wrap"):
                fields["start_date"] = ui.input("Ngày bắt đầu", value=settings["start_date"], on_change=lambda e: change("start_date", e.value or "")).props("outlined type=date").classes("w-56")
                fields["hour"] = ui.input("Giờ đăng (Việt Nam, UTC+7)", value=settings["hour"], on_change=lambda e: change("hour", e.value or "")).props("outlined type=time").classes("w-64")
                buttons["plan"] = ui.button("Xem lịch dự kiến", icon="event", on_click=lambda: invoke(controller.plan)).props("outline")
        with app_card():
            with section_header("Danh sách xử lý", "Ưu tiên ID ở cuối tên MP4/title → video tìm kiếm lệch thời lượng dưới 2 giây → kết quả tìm kiếm đầu tiên. Từ khóa lấy từ bài nhạc đầu tiên trong description, hoặc title nếu không có tracklist."):
                buttons["select"] = ui.button("Chọn tất cả trong bộ lọc", icon="checklist", on_click=select_all).props("outline")
                buttons["deselect"] = ui.button("Bỏ chọn trong bộ lọc", icon="remove_done", on_click=lambda: invoke(lambda: controller.select_filtered(selected=False))).props("outline")
                buttons["clear_selection"] = ui.button("Bỏ chọn tất cả", icon="clear_all", on_click=lambda: invoke(lambda: controller.select([]))).props("flat")
                buttons["run"] = ui.button("Tự động SEO, tạo thumbnail & lên lịch", icon="play_arrow", on_click=lambda: invoke(lambda: controller.start("run")))
                buttons["stop"] = ui.button("Dừng", icon="stop", on_click=lambda: invoke(controller.stop)).props("outline color=negative")
            with ui.row().classes("w-full gap-3 items-end flex-wrap"):
                fields["scope"] = ui.select(VIDEO_SCOPE_LABELS, label="Lọc loại video đã quét", value=settings["scope"],
                                            on_change=lambda e: change("scope", e.value)).props("outlined").classes("w-96 max-w-full")
                fields["categories"] = ui.select(COPYRIGHT_LABELS, multiple=True, clearable=True, label="Lọc trạng thái bản quyền (trống = tất cả)",
                                                 value=settings["categories"], on_change=lambda e: change("categories", list(e.value or []))).props("outlined use-chips").classes("flex-1 min-w-64")
            ui.label("Bảng áp dụng đồng thời loại video và bản quyền. Xóa bộ lọc bản quyền để thấy đủ video thuộc loại đã chọn. Đổi bộ lọc vẫn giữ các video đã chọn; video bị khóa checkbox có lý do tại từng dòng.").classes("text-xs text-gray-500")
            rescan_hint = ui.label("Danh sách cũ chưa được kiểm tra bằng cách nhận diện bản nháp mới. Bấm Quét video lại một lần để cập nhật đúng loại video.").classes("text-sm text-amber-700")
            message = ui.label().classes("text-sm text-emerald-700 break-words")
            summary = ui.label().classes("text-xs text-gray-500")
            columns = [{"name": key, "label": label, "field": key, "align": "left"} for key, label in (
                ("channel_id", "Kênh"), ("video_id", "Video ID"), ("old_title", "Title hiện tại"), ("visibility_label", "Loại video"), ("copyright_label", "Bản quyền"),
                ("song", "Bài nhạc tìm kiếm"), ("reference_title", "Title sẽ chép nguyên văn"), ("publish_label", "Ngày giờ UTC+7"),
                ("reference_method", "Cách chọn tham chiếu"),
                ("status_label", "Trạng thái"), ("detail", "Chi tiết"), ("action", "Xem tham chiếu"))]
            table = ui.table(columns=columns, rows=[], row_key="video_id", selection="multiple", on_select=select_rows, pagination=20).classes("w-full min-w-0").props('wrap-cells no-data-label="Chưa có video. Chọn kênh và bấm Quét video."')
            table.props('no-data-label="Không có video trong bộ lọc này. Đổi loại video / trạng thái bản quyền hoặc quét lại."')
            table.add_slot("body-selection", '<q-checkbox v-model="props.selected" :disable="!props.row.can_select" dense><q-tooltip v-if="props.row.disabled_reason">{{props.row.disabled_reason}}</q-tooltip></q-checkbox>')
            table.add_slot("header-selection", '<q-btn flat dense icon="done_all" @click="$parent.$emit(\'select_visible\')" aria-label="Chọn tất cả trong bộ lọc"><q-tooltip>Chọn video có thể lên lịch trong bộ lọc này</q-tooltip></q-btn>')
            table.on("select_visible", select_all)
            for key in ("old_title", "song", "reference_title", "detail"):
                table.add_slot(f"body-cell-{key}", f'<q-td :props="props" style="min-width:180px;max-width:300px;white-space:normal;overflow-wrap:anywhere">{{{{props.row.{key}}}}}</q-td>')
            table.add_slot("body-cell-action", '<q-td :props="props"><q-btn flat dense icon="visibility" @click="$parent.$emit(\'view_reference\', props.row.video_id)" aria-label="Xem dữ liệu tham chiếu" /></q-td>')
            table.on("view_reference", details)
        refresh()
        ui.timer(1.0, refresh)
