"""Preview and change YouTube titles by matching local song durations."""
import csv
import io
from pathlib import Path

from nicegui import context, ui

from src.utils import get_channels_info
from src.video_scan_dates import SCAN_DATE_TYPE_OPTIONS
from src.video_title_tasks import ELIGIBLE, get_video_title_controller
from web.components.common import create_channel_selection, select_directory
from web.theme import app_card, page_header, page_shell, section_header

LABELS = {"scanned": "Chưa ghép", "ready": "Sẵn sàng đổi", "unchanged": "Đã đúng tên",
          "ambiguous": "Cần chọn file", "unmatched": "Chưa khớp", "processing": "Đang đổi",
          "successful": "Thành công", "error": "Lỗi", "stopped": "Đã dừng"}


def _duration(value):
    if value is None:
        return "—"
    value = max(0, float(value))
    hours, rest = divmod(int(value), 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def create_video_titles_page():
    ui.add_css("""
        .video-title-page, .video-title-page .app-card, .video-title-page .q-table__container {min-width:0;max-width:100%}
        .video-title-page .q-field, .video-title-page .q-btn {max-width:100%}
        .video-title-page .q-table__middle {overflow-x:auto;max-width:100%;min-width:0}
        .video-title-page .q-table__middle table {min-width:1600px}
        @media(max-width:700px){.video-title-page .title-folder-row{flex-wrap:wrap}.video-title-page .title-folder-row>.q-field{flex-basis:100%}}
    """)
    controller = get_video_title_controller()
    page_client = context.client
    settings = controller.snapshot()["settings"]
    fields, buttons = {}, {}
    syncing = {"value": False, "revision": -1}

    def notify_error(error):
        ui.notify(str(error), type="negative")

    def change(key, value):
        if syncing["value"]:
            return
        try:
            controller.change_settings(**{key: value})
        except ValueError as exc:
            notify_error(exc)
        refresh()

    def choose_channel(channel_id):
        try:
            controller.change_settings(channel_id=channel_id or "")
            refresh()
            return True
        except ValueError as exc:
            notify_error(exc)
            return False

    def start(action):
        try:
            controller.start(action)
        except ValueError as exc:
            notify_error(exc)
        refresh()

    def choose_folder():
        folder = select_directory(initial_dir=fields["folder"].value or None, title="Chọn thư mục nhạc để ghép tiêu đề")
        if folder:
            change("folder", folder)

    def select_ready():
        snapshot = controller.snapshot()
        controller.select(row["video_id"] for row in snapshot["rows"] if row["status"] in ELIGIBLE and row.get("new_title"))
        refresh()

    def selection_changed(_event):
        if syncing["value"]:
            return
        try:
            controller.select(row["video_id"] for row in table.selected)
        except ValueError as exc:
            notify_error(exc)
        refresh()

    def choose_candidate(event):
        if controller.snapshot()["busy"]:
            return
        row = next((row for row in controller.snapshot()["rows"] if row["video_id"] == event.args), None)
        if not row or not row.get("candidates"):
            return
        options = {item["path"]: f"{Path(item['path']).name} · {_duration(item['seconds'])} · lệch {item['delta']:.2f}s"
                   for item in row["candidates"]}
        with ui.dialog() as dialog, ui.card().classes("w-[760px] max-w-full"):
            ui.label(f"Chọn bài nhạc cho {row['video_id']}").classes("text-lg font-semibold")
            ui.label(row["old_title"]).classes("text-sm text-gray-500 break-all")
            choice = ui.select(options, label="File khớp thời lượng", value=row.get("audio_path") or None).props("outlined").classes("w-full")

            def apply():
                try:
                    controller.select_candidate(row["video_id"], choice.value)
                    dialog.close()
                    refresh()
                except ValueError as exc:
                    notify_error(exc)

            with ui.row().classes("w-full justify-end"):
                ui.button("Hủy", on_click=dialog.close).props("flat")
                ui.button("Dùng file này", on_click=apply)
        dialog.open()

    def export():
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(["Video ID", "Channel ID", "Tiêu đề lúc quét", "Thời lượng video", "File nhạc", "Tiêu đề mới", "Trạng thái", "Chi tiết"])
        for row in controller.snapshot()["rows"]:
            # Neutralize spreadsheet formulas in names supplied by remote metadata.
            values = [row["video_id"], row["channel_id"], row["old_title"], row["duration_seconds"],
                      row.get("audio_path", ""), row.get("new_title", ""), LABELS[row["status"]], row.get("detail", "")]
            writer.writerow(["'" + value if isinstance(value, str) and value.startswith(("=", "+", "-", "@")) else value for value in values])
        ui.download(stream.getvalue().encode("utf-8-sig"), "ket_qua_doi_tieu_de.csv", media_type="text/csv")

    def refresh():
        if getattr(page_client, "_deleted", False):
            return
        data = controller.snapshot()
        busy, config = data["busy"], data["settings"]
        syncing["value"] = True
        try:
            for key, field in fields.items():
                if field.value != config[key]:
                    field.set_value(config[key])
                field.set_enabled(not busy)
            fields["limit"].set_enabled(not busy and config["mode"] == "count")
            for key in ("start_date", "end_date", "date_type"):
                fields[key].set_enabled(not busy and config["mode"] == "dates")
            for key, button in buttons.items():
                button.set_enabled(not busy)
            buttons["stop"].set_enabled(busy)
            buttons["scan"].set_enabled(not busy and bool(config["channel_id"]))
            buttons["scan_part"].set_enabled(not busy and bool(config["channel_id"]))
            buttons["scan_manual"].set_enabled(not busy and bool(config["channel_id"]) and bool(config["manual_ids"].strip()))
            buttons["match"].set_enabled(not busy and bool(data["rows"]) and bool(config["folder"]))
            eligible = [row for row in data["rows"] if row.get("new_title") and row["status"] in ELIGIBLE]
            chosen = sum(bool(row.get("selected")) for row in eligible)
            buttons["update"].set_enabled(not busy and chosen > 0)
            message.set_text(data["message"])
            summary.set_text(f"{len(data['rows'])} video · {len(eligible)} sẵn sàng · đã chọn {chosen}")
            selection = None if busy else "multiple"
            if table.selection != selection:
                table.selection = selection
            if data["revision"] != syncing["revision"]:
                rows = [{**row, "video_length": _duration(row["duration_seconds"]), "audio_length": _duration(row.get("audio_duration")),
                         "audio_name": Path(row["audio_path"]).name if row.get("audio_path") else "—",
                         "delta_label": f"{row['delta']:.2f}s" if row.get("delta") is not None else "—",
                         "status_label": LABELS[row["status"]], "can_choose": bool(row.get("candidates")) and row["status"] != "successful" and not busy}
                        for row in data["rows"]]
                table.rows = rows
                table.selected = [row for row in rows if row.get("selected")]
                table.update()
                syncing["revision"] = data["revision"]
        finally:
            syncing["value"] = False

    with page_shell(), ui.column().classes("video-title-page w-full min-w-0 gap-6"):
        with page_header("Ghép nhạc & đổi tiêu đề", "Quét video trên YouTube, ghép theo thời lượng và đổi tiêu đề theo tên file nhạc.", eyebrow="TÁC VỤ VIDEO"):
            buttons["export"] = ui.button("Xuất kết quả CSV", icon="download", on_click=export).props("outline")
        create_channel_selection(get_channels_info() or [], choose_channel,
                                 initial_selected_ids=settings["channel_id"] or None,
                                 can_change_selection=lambda: not controller.snapshot()["busy"])
        with app_card():
            with section_header("Quét video", "Quét mọi video trong phạm vi; không lọc theo trạng thái audio."):
                buttons["scan"] = ui.button("Quét video", icon="manage_search", on_click=lambda: start("scan"))
                buttons["scan_part"] = ui.button('Quét video có chữ “part”', icon="filter_alt", on_click=lambda: start("scan_part")).props("outline")
            with ui.row().classes("w-full items-end gap-3 flex-wrap"):
                fields["mode"] = ui.select({"count": "Theo số lượng", "dates": "Theo khoảng ngày"}, label="Cách quét", value=settings["mode"],
                                           on_change=lambda e: change("mode", e.value)).props("outlined").classes("w-52")
                fields["scope"] = ui.select({"all": "Tất cả video", "public": "Chỉ công khai", "scheduled": "Đã lên lịch", "draft": "Bản nháp"},
                                            label="Phạm vi trên kênh", value=settings["scope"], on_change=lambda e: change("scope", e.value)).props("outlined").classes("w-52")
                fields["limit"] = ui.number("Số video mới nhất", value=settings["limit"], min=1, max=10000, step=1,
                                            on_change=lambda e: change("limit", e.value)).props("outlined").classes("w-44")
                fields["start_date"] = ui.input("Từ ngày", value=settings["start_date"], on_change=lambda e: change("start_date", e.value)).props("outlined type=date").classes("w-48")
                fields["end_date"] = ui.input("Đến hết ngày", value=settings["end_date"], on_change=lambda e: change("end_date", e.value)).props("outlined type=date").classes("w-48")
                fields["date_type"] = ui.select(SCAN_DATE_TYPE_OPTIONS, label="Tính theo ngày", value=settings["date_type"],
                                                on_change=lambda e: change("date_type", e.value)).props("outlined").classes("w-64")
            ui.label("Khoảng ngày tính theo giờ Việt Nam, gồm cả ngày kết thúc. Chế độ số lượng lấy video mới nhất sau khi lọc phạm vi.").classes("text-xs text-gray-500")
            ui.label('Nút quét “part” chỉ lấy tiêu đề chứa chữ part, không phân biệt hoa thường (ví dụ: _part40, PART 2). Số lượng tính sau khi lọc tiêu đề.').classes("text-xs text-gray-500")
            ui.separator()
            fields["manual_ids"] = ui.textarea("Video ID thủ công", value=settings["manual_ids"],
                                               placeholder="Mỗi dòng một Video ID hoặc link YouTube / Studio",
                                               on_change=lambda e: change("manual_ids", e.value or "")).props("outlined autogrow").classes("w-full")
            with ui.row().classes("w-full items-center gap-3"):
                buttons["scan_manual"] = ui.button("Đọc Video ID thủ công", icon="playlist_add", on_click=lambda: start("scan_manual")).props("outline")
                ui.label("Đọc đúng danh sách đã nhập và thay thế bảng bên dưới; bỏ qua bộ lọc ngày, số lượng và phạm vi. Video phải thuộc kênh đã chọn.").classes("text-xs text-gray-500 flex-1 min-w-0")
        with app_card():
            with section_header("Ghép tên bài nhạc theo thời lượng", "Tên file nhạc bỏ phần mở rộng sẽ trở thành tiêu đề video trên YouTube."):
                buttons["match"] = ui.button("Ghép theo thời lượng", icon="timer", on_click=lambda: start("match")).props("outline")
            with ui.row().classes("title-folder-row w-full items-center gap-3"):
                fields["folder"] = ui.input("Thư mục nhạc", value=settings["folder"], on_change=lambda e: change("folder", e.value)).props("outlined clearable").classes("flex-1 min-w-0")
                buttons["browse"] = ui.button("Chọn thư mục", icon="folder_open", on_click=choose_folder).props("outline")
            with ui.row().classes("w-full items-center gap-5"):
                fields["recursive"] = ui.switch("Quét cả thư mục con", value=settings["recursive"], on_change=lambda e: change("recursive", e.value))
                fields["tolerance"] = ui.number("Lệch tối đa (giây)", value=settings["tolerance"], min=0, max=60, step=.1,
                                                on_change=lambda e: change("tolerance", e.value)).props("outlined").classes("w-44")
            ui.label("Một bài nhạc có thể ghép cho nhiều video. Nếu nhiều tên khớp ngang nhau, chọn file tại từng dòng trước khi đổi. Tiêu đề được lọc ký tự và rút gọn tối đa 100 ký tự.").classes("text-xs text-gray-500")
        with app_card():
            with section_header("Xem trước tiêu đề", "Các video ghép được được chọn sẵn. Bỏ chọn những dòng chưa muốn đổi."):
                buttons["select"] = ui.button("Chọn các dòng đã ghép", icon="checklist", on_click=select_ready).props("outline")
                buttons["update"] = ui.button("Đổi tiêu đề đã chọn", icon="drive_file_rename_outline", on_click=lambda: start("update"))
                buttons["stop"] = ui.button("Dừng", icon="stop", on_click=lambda: (controller.stop(), refresh())).props("outline color=negative")
            message = ui.label().classes("text-sm text-emerald-700 break-words")
            summary = ui.label().classes("text-xs text-gray-500")
            columns = [{"name": name, "label": label, "field": name, "align": "left", "sortable": True}
                       for name, label in [("video_id", "Video ID"), ("old_title", "Tiêu đề lúc quét"), ("video_length", "Video"),
                                           ("audio_name", "File nhạc"), ("audio_length", "Nhạc"), ("delta_label", "Độ lệch"),
                                           ("new_title", "Tiêu đề mới"), ("status_label", "Trạng thái"), ("detail", "Chi tiết"), ("action", "Chọn file")]]
            table = ui.table(columns=columns, rows=[], row_key="video_id", selection="multiple", pagination=20,
                             on_select=selection_changed).classes("w-full min-w-0").props('wrap-cells no-data-label="Chưa có video. Chọn kênh và bấm Quét video."')
            for name in ("old_title", "new_title", "detail"):
                table.add_slot(f"body-cell-{name}", f'<q-td :props="props" style="min-width:180px;max-width:320px;white-space:normal;overflow-wrap:anywhere">{{{{props.row.{name}}}}}</q-td>')
            table.add_slot("body-cell-audio_name", '<q-td :props="props" style="max-width:260px;white-space:normal;overflow-wrap:anywhere">{{props.row.audio_name}}<q-tooltip>{{props.row.audio_path}}</q-tooltip></q-td>')
            table.add_slot("body-cell-action", '<q-td :props="props"><q-btn flat dense icon="folder_open" :disable="!props.row.can_choose" @click="$parent.$emit(\'choose_audio\', props.row.video_id)" aria-label="Chọn lại file nhạc" /></q-td>')
            table.on("choose_audio", choose_candidate)
        refresh()
        ui.timer(.5, refresh)
