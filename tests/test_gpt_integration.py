import importlib.util
import json
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from starlette.requests import Request

from src import gpt_service, phoma_image_generator as phoma
from src.publishing_browser import ChatGPTSessionNeedsAction
from src.route_manager import RouterManager
from src.task_runtime import TaskStopped, bind_run_context, create_run_context


ROOT = Path(__file__).resolve().parent.parent


class WorkerTests(unittest.TestCase):
    @unittest.skipUnless(
        shutil.which("node") and (ROOT / "gpt_backend" / "node_modules" / "puppeteer-core").is_dir(),
        "Node.js and GPT dependencies are required",
    )
    def test_account_operations_and_invalid_job(self):
        with tempfile.TemporaryDirectory() as temp:
            env = {**os.environ, "TVA_GPT_DATA_ROOT": temp}
            requests = [
                {"action": "add", "session": "fake-token-for-test", "name": "Test"},
                {"action": "accounts"},
                {"action": "start", "prompt": "", "size": "auto", "model": "gpt-image-2", "images": []},
            ]
            result = subprocess.run(
                ["node", str(ROOT / "gpt_backend" / "worker.js")],
                input="".join(json.dumps(item) + "\n" for item in requests),
                text=True, encoding="utf-8", capture_output=True, env=env, check=True, timeout=30,
            )
            responses = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(len(responses), 3)
            self.assertEqual(responses[1]["result"][0]["name"], "Test")
            self.assertNotIn("fake-token-for-test", result.stdout)
            self.assertIn("error", responses[2])

    def test_route_access_is_loopback_only(self):
        def request(host):
            return Request({"type": "http", "method": "GET", "path": "/", "headers": [], "client": (host, 1234)})
        self.assertTrue(RouterManager.is_local_request(request("127.0.0.1")))
        self.assertTrue(RouterManager.is_local_request(request("::1")))
        self.assertFalse(RouterManager.is_local_request(request("192.168.1.10")))
        self.assertFalse(RouterManager.is_local_request(request("invalid")))

    def test_frozen_worker_uses_bundled_node_and_backend(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(sys, "frozen", True, create=True), \
             patch.object(sys, "_MEIPASS", temp, create=True):
            namespace = runpy.run_path(str(ROOT / "src" / "gpt_service.py"))
        self.assertEqual(namespace["_worker_path"], Path(temp) / "gpt_backend" / "worker.js")
        self.assertEqual(namespace["_node"], str(Path(temp) / "tools" / "node" / "node.exe"))

    @unittest.skipUnless(
        importlib.util.find_spec("PyInstaller") and shutil.which("node")
        and (ROOT / "gpt_backend" / "node_modules" / "puppeteer-core").is_dir(),
        "PyInstaller, Node.js and GPT dependencies are required",
    )
    def test_build_spec_includes_backend_and_node(self):
        import PyInstaller.utils.hooks as hooks

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("ffmpeg.exe", "ffprobe.exe", "chromedriver.exe"):
                (root / name).touch()
            captured = {}

            def analysis(*args, **kwargs):
                captured.update(kwargs)
                return type("AnalysisResult", (), {"pure": [], "scripts": [], "binaries": [], "datas": []})()

            env = {"TVAUTOMATION_FFMPEG_DIR": temp, "TVAUTOMATION_CHROMEDRIVER": str(root / "chromedriver.exe")}
            with patch.dict(os.environ, env), \
                 patch.object(hooks, "collect_data_files", return_value=[]), \
                 patch.object(hooks, "collect_dynamic_libs", return_value=[]), \
                 patch.object(hooks, "collect_submodules", return_value=[]), \
                 patch.object(hooks, "copy_metadata", return_value=[]):
                runpy.run_path(str(ROOT / "Tuat Videos.spec"), init_globals={
                    "SPECPATH": str(ROOT), "Analysis": analysis,
                    "PYZ": lambda *args: None, "EXE": lambda *args, **kwargs: None,
                    "COLLECT": lambda *args, **kwargs: None,
                })
            data_destinations = {destination for _, destination in captured["datas"]}
            self.assertTrue({"gpt_backend", "gpt_backend/src", "gpt_backend/node_modules"} <= data_destinations)
            self.assertIn("tools/node", {destination for _, destination in captured["binaries"]})


class PhomaPublishingTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.reference = self.root / "reference.jpg"
        self.reference.write_bytes(b"reference")
        self.job_id = str(uuid.uuid4())
        self.receipt = {"provider": "phoma", "job_id": self.job_id, "video_id": "video1", "title": "Song", "status": "sent"}
        self.generator = phoma.PhomaImageGenerator()

    def generate(self, **kwargs):
        return self.generator.generate(str(self.reference), "prompt", {"title": "Song"},
                                       str(self.root / "thumb.generated"), video_id="video1", **kwargs)

    def test_session_json_is_not_a_cookie_and_errors_do_not_leak_secrets(self):
        self.assertEqual(phoma.parse_access_token('{"accessToken":"secret-token"}'), "secret-token")
        self.assertEqual(phoma.parse_access_token("Bearer secret-token"), "secret-token")
        for text in ('{"user":"secret"}', "Cookie: session=secret", "session=secret", "{secret"):
            with self.assertRaises(ValueError) as caught:
                phoma.parse_access_token(text)
            self.assertNotIn("secret", str(caught.exception))

    def test_new_job_sends_reference_model_and_saves_receipt(self):
        output = self.root / "result.png"
        output.write_bytes(b"image")
        receipts = []
        with patch.object(self.generator, "ensure_ready"), \
             patch.object(gpt_service, "call", side_effect=[{"id": self.job_id}, {"status": "success"}]) as call, \
             patch.object(phoma, "generated_image", return_value=output):
            result = self.generate(model="gpt-6-high", cleanup=True, on_request=receipts.append)
        self.assertEqual(Path(result).read_bytes(), b"image")
        self.assertEqual(call.call_args_list[0].args, ("start",))
        self.assertEqual(call.call_args_list[0].kwargs["size"], "16:9")
        self.assertEqual(call.call_args_list[0].kwargs["model"], "gpt-6-high")
        self.assertTrue(call.call_args_list[0].kwargs["cleanup"])
        self.assertEqual(receipts[0]["job_id"], self.job_id)
        self.assertEqual(receipts[-1]["status"], "success")

    def test_completed_receipt_is_reused_after_worker_restart_without_new_prompt(self):
        directory = self.root / "gpt_runtime" / "app" / "gpt" / "images"
        directory.mkdir(parents=True)
        (directory / (self.job_id + ".webp")).write_bytes(b"image")
        with patch.object(phoma, "get_data_dir", return_value=self.root), \
             patch.object(gpt_service, "call", side_effect=gpt_service.GPTServiceError("missing", "job_missing")) as call:
            result = self.generate(request=self.receipt)
        self.assertTrue(result.endswith(".webp"))
        call.assert_called_once_with("job", id=self.job_id)

    def test_missing_job_does_not_silently_submit_another_prompt(self):
        with patch.object(phoma, "generated_image", return_value=None), \
             patch.object(gpt_service, "call", side_effect=gpt_service.GPTServiceError("missing", "job_missing")) as call:
            with self.assertRaisesRegex(ValueError, "Tạo lại ảnh"):
                self.generate(request=self.receipt)
        call.assert_called_once_with("job", id=self.job_id)

    def test_running_job_does_not_read_an_image_still_being_written(self):
        source = self.root / "result.png"
        source.write_bytes(b"image")
        with patch.object(phoma, "generated_image", return_value=source) as lookup, \
             patch.object(phoma, "wait_interruptibly") as wait, \
             patch.object(gpt_service, "call", side_effect=[
                 {"status": "running", "stage": "downloading"}, {"status": "success"},
             ]):
            self.generate(request=self.receipt)
        wait.assert_called_once_with(2)
        lookup.assert_called_once_with(self.job_id)

    def test_stop_cancels_only_the_receipted_job(self):
        run = create_run_context("phoma-stop-test")
        self.addCleanup(run.cleanup)
        receipts = []

        def wait(_seconds):
            run.request_stop()
            run.checkpoint()

        with bind_run_context(run), patch.object(phoma, "generated_image", return_value=None), \
             patch.object(phoma, "wait_interruptibly", side_effect=wait), \
             patch.object(gpt_service, "call", side_effect=[
                 {"status": "running", "stage": "polling"}, {"status": "cancelled"},
             ]) as call:
            with self.assertRaises(TaskStopped):
                self.generate(request=self.receipt, on_request=receipts.append)
        self.assertEqual(call.call_args_list[-1].args, ("cancel",))
        self.assertEqual(call.call_args_list[-1].kwargs, {"id": self.job_id})
        self.assertEqual(receipts[-1]["status"], "cancelled")

    def test_auth_error_pauses_and_old_or_wrong_receipts_are_rejected(self):
        with patch.object(phoma, "generated_image", return_value=None), \
             patch.object(gpt_service, "call", return_value={"status": "error", "errorCode": "account_auth"}):
            with self.assertRaises(ChatGPTSessionNeedsAction):
                self.generate(request=self.receipt)
        for receipt in (
            {"video_id": "video2", "title": "Song"},
            {"video_id": "video1", "title": "Song", "marker": "old"},
            {"provider": "phoma", "video_id": "video1", "title": "Song", "status": "sent"},
        ):
            with patch.object(gpt_service, "call") as call, self.assertRaises(ValueError):
                self.generate(request=receipt)
            call.assert_not_called()

    def test_rate_limit_pauses_instead_of_submitting_more_videos(self):
        with patch.object(phoma, "generated_image", return_value=None), \
             patch.object(gpt_service, "call", return_value={"status": "error", "errorCode": "rate_limited"}):
            with self.assertRaises(ChatGPTSessionNeedsAction) as caught:
                self.generate(request=self.receipt)
        self.assertEqual(caught.exception.reason, "quota")


if __name__ == "__main__":
    unittest.main()
