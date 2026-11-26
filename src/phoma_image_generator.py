"""Adapt phoma image jobs to the resumable publishing workflow."""
import base64
import json
import shutil
import uuid
from pathlib import Path

from loguru import logger

from src import gpt_service
from src.paths import get_data_dir
from src.publishing_browser import ChatGPTSessionNeedsAction
from src.task_runtime import TaskStopped, check_stopped, wait_interruptibly


IMAGE_MODELS = ("gpt-image-2", "gpt-6", "gpt-6-medium", "gpt-6-high")
_ERRORS = {
    "account_auth": "Session ChatGPT không hợp lệ hoặc đã hết hạn. Hãy thay session.",
    "account_challenge": "ChatGPT yêu cầu xác minh. Hãy kiểm tra tài khoản và thử lại sau.",
    "app_access": "ChatGPT từ chối truy cập. Hãy kiểm tra tài khoản và thử lại sau.",
    "chrome_missing": "Không tìm thấy Google Chrome.",
    "network": "Không kết nối được tới ChatGPT.",
    "prompt_rejected": "ChatGPT từ chối nội dung tạo ảnh.",
    "rate_limited": "Tài khoản đã đạt giới hạn tạo ảnh.",
    "reference_image": "Không tải được ảnh tham chiếu.",
    "timeout": "Hết thời gian chờ ảnh ChatGPT.",
    "invalid_output": "ChatGPT không trả ảnh hợp lệ.",
    "upstream_unavailable": "Dịch vụ ChatGPT đang không khả dụng.",
    "unknown": "Không tạo được ảnh. Kiểm tra log ứng dụng để biết thêm.",
}


def parse_access_token(text):
    token = text.strip()
    if token.startswith("{"):
        try:
            session = json.loads(token)
        except json.JSONDecodeError:
            raise ValueError("Session JSON không hợp lệ.") from None
        if not isinstance(session, dict):
            raise ValueError("Session JSON không hợp lệ.")
        token = session.get("accessToken") or session.get("access_token")
    elif token.lower().startswith("bearer "):
        token = token[7:].strip()
    if not isinstance(token, str) or not token.strip() or any(char.isspace() for char in token.strip()):
        raise ValueError("Hãy nhập Session JSON có accessToken hoặc access token, không phải cookie.")
    if "=" in token or len(token) > 100000:
        raise ValueError("Access token không hợp lệ; không dùng Cookie header.")
    return token.strip()


def generated_image(job_id):
    identifier = str(uuid.UUID(job_id))
    root = get_data_dir() / "gpt_runtime" / "app" / "gpt" / "images"
    for suffix in (".png", ".jpg", ".webp"):
        path = root / (identifier + suffix)
        if path.is_file():
            return path
    return None


class PhomaImageGenerator:
    def __init__(self, session_text=""):
        self.session_text = session_text
        self.account_id = None

    def update_session(self, text):
        if text.strip():
            parse_access_token(text)
        self.session_text = text
        self.account_id = None

    def close(self):
        self.account_id = None

    def ensure_ready(self, *, on_status=lambda message: None, on_state=lambda state, message: None,
                     wait_for_user=False, allow_image_result=False):
        check_stopped()
        try:
            if self.session_text:
                account = gpt_service.call("add", session=self.session_text)
                gpt_service.call("select", id=account["id"])
                self.account_id = account["id"]
                self.session_text = ""
            accounts = gpt_service.call("accounts")
            if self.account_id is None:
                self.account_id = next((account["id"] for account in accounts if account.get("active")), None)
            if not any(account["id"] == self.account_id for account in accounts):
                raise ChatGPTSessionNeedsAction("Hãy thêm và chọn tài khoản GPT bằng Session JSON hoặc access token.", reason="login")
            if not wait_for_user:
                on_status("Đang kiểm tra tài khoản GPT bằng backend phoma…")
                gpt_service.call("check", id=self.account_id)
        except gpt_service.GPTServiceError as error:
            if error.code in ("account_auth", "account_challenge", "app_access"):
                raise ChatGPTSessionNeedsAction(str(error), reason="verification") from None
            raise
        check_stopped()
        on_state("ready", "Tài khoản GPT đã chọn; dùng backend phoma để tạo thumbnail.")

    def generate(self, reference_image, prompt, reference, destination, *, video_id="", request=None,
                 conversation_url="", on_request=lambda request: None, on_conversation=lambda url: None,
                 on_state=lambda state, message: None, on_progress=lambda message: None,
                 model="gpt-image-2", cleanup=False):
        check_stopped()
        receipt = dict(request or {})
        if receipt and (receipt.get("video_id") != video_id or receipt.get("title") != reference["title"]):
            raise ValueError("Mã yêu cầu ảnh không thuộc đúng video và nguồn tham chiếu.")
        if (receipt and receipt.get("provider") != "phoma") or (conversation_url and not receipt):
            raise ValueError("Yêu cầu ảnh cũ dùng Selenium. Bấm Tạo lại ảnh chưa tải để chuyển sang phoma.")
        if receipt.get("status") in ("error", "cancelled", "not_sent"):
            receipt = {}
        job_id = receipt.get("job_id")
        if receipt and not job_id:
            raise ValueError("Yêu cầu phoma đã lưu thiếu mã tác vụ. Bấm Tạo lại ảnh chưa tải nếu muốn gửi yêu cầu mới.")
        if not job_id:
            self.ensure_ready(wait_for_user=True, on_state=on_state)
            path = Path(reference_image)
            if path.stat().st_size > 15000000:
                raise ValueError("Ảnh tham chiếu vượt giới hạn 15 MB.")
            content = base64.b64encode(path.read_bytes()).decode("ascii")
            on_progress("Đang gửi ảnh tham chiếu và prompt tới backend phoma…")
            job = gpt_service.call(
                "start", id=self.account_id, prompt=prompt.strip() + "\n\nTitle video: " + reference["title"],
                model=model, size="16:9", cleanup=cleanup,
                images=[{"name": path.name, "content": content}],
            )
            job_id = job["id"]
            receipt = {"provider": "phoma", "job_id": job_id, "video_id": video_id,
                       "title": reference["title"], "status": "sent"}
            try:
                on_request(dict(receipt))
            except Exception:
                self._cancel(job_id)
                raise
        try:
            while True:
                check_stopped()
                try:
                    job = gpt_service.call("job", id=job_id)
                except gpt_service.GPTServiceError as error:
                    if error.code == "job_missing":
                        if generated_image(job_id) is None:
                            raise ValueError("Backend đã khởi động lại và chưa có ảnh của yêu cầu đã lưu. Bấm Tạo lại ảnh chưa tải nếu muốn gửi yêu cầu mới.") from None
                        job = {"status": "success"}
                    else:
                        raise
                if job["status"] == "success":
                    source = generated_image(job_id)
                    if source is None:
                        raise ValueError("Tác vụ GPT báo hoàn thành nhưng không tìm thấy tệp ảnh.")
                    output = Path(destination).with_suffix(source.suffix)
                    shutil.copyfile(source, output)
                    check_stopped()
                    on_request({**receipt, "status": "success"})
                    on_progress("Đã tải ảnh GPT bằng backend phoma.")
                    return str(output)
                if job["status"] in ("error", "cancelled"):
                    on_request({**receipt, "status": job["status"]})
                    code = job.get("errorCode", "unknown")
                    message = _ERRORS.get(code, f"Lỗi GPT: {code}")
                    if code in ("account_auth", "account_challenge", "app_access"):
                        raise ChatGPTSessionNeedsAction(message, reason="verification")
                    if code == "rate_limited":
                        raise ChatGPTSessionNeedsAction(message, reason="quota")
                    raise ValueError("Tác vụ GPT đã bị hủy." if job["status"] == "cancelled" else message)
                on_progress("GPT đang tạo thumbnail: " + job["stage"])
                wait_interruptibly(2)
        except TaskStopped:
            job = self._cancel(job_id)
            on_request({**receipt, "status": job["status"]})
            raise

    @staticmethod
    def _cancel(job_id):
        try:
            return gpt_service.call("cancel", id=job_id)
        except gpt_service.GPTServiceError:
            logger.exception("Không hủy được tác vụ GPT {}", job_id)
            raise
