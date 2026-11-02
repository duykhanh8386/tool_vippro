import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

import requests

from src.module.audio_module import (
    AudioUpdateError, UpdateAudioModule, _AudioUploadAdapter, _AudioUploadFile,
)
from test_audio_module import Response


class UploadTransportTests(unittest.TestCase):
    def test_tuned_adapter_is_limited_to_uploads_and_keeps_tls_verification(self):
        with requests.Session() as session:
            studio_adapter = session.get_adapter("https://studio.youtube.com/")
            UpdateAudioModule._configure_upload_session(session)
            upload_adapter = session.get_adapter("https://upload.youtube.com/")
            self.assertIsInstance(upload_adapter, _AudioUploadAdapter)
            self.assertIs(session.get_adapter("https://studio.youtube.com/"), studio_adapter)
            self.assertTrue(session.verify)
            request = requests.Request("POST", "https://upload.youtube.com/session").prepare()
            pool = upload_adapter.get_connection_with_tls_context(request, verify=True)
            self.assertEqual(pool.conn_kw["blocksize"], 1024 * 1024)
            self.assertEqual(pool.cert_reqs, "CERT_REQUIRED")
            self.assertIn((socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024), pool.conn_kw["socket_options"])
            proxy = upload_adapter.proxy_manager_for("http://127.0.0.1:12345")
            self.assertEqual(proxy.connection_pool_kw["blocksize"], 1024 * 1024)

    def test_real_http_upload_delivers_one_complete_body_with_large_reads_and_progress(self):
        payload = bytes(range(251)) * 13000
        received, read_sizes = [], []

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_):
                pass

            def do_POST(self):
                size = int(self.headers["Content-Length"])
                digest = hashlib.sha256()
                remaining = size
                while remaining:
                    block = self.rfile.read(min(remaining, 64 * 1024))
                    if not block:
                        break
                    digest.update(block)
                    remaining -= len(block)
                received.append((size - remaining, digest.hexdigest(), dict(self.headers)))
                self.send_response(200)
                self.send_header("X-Goog-Upload-Status", "final")
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        worker.start()
        original_read = _AudioUploadFile.read

        def read(body, size=-1):
            read_sizes.append(size)
            return original_read(body, size)

        try:
            with tempfile.TemporaryDirectory() as folder, requests.Session() as session:
                path = Path(folder) / "music.mp3"
                path.write_bytes(payload)
                url = f"http://127.0.0.1:{server.server_port}/upload"
                session.trust_env = False
                UpdateAudioModule._configure_upload_session(session)
                session.mount(url, session.get_adapter("https://upload.youtube.com/"))
                progress = {}
                with patch.object(_AudioUploadFile, "read", read):
                    result = UpdateAudioModule()._next_upload_http(
                        url, "music.mp3", "test-cookie", file_path=str(path), session=session,
                        progress=progress, single_request=True,
                    )
                self.assertEqual(result, "final")
                self.assertEqual(progress["confirmed"], len(payload))
                self.assertEqual(progress["sent"], len(payload))
                self.assertEqual(progress["status"], "complete")
        finally:
            server.shutdown()
            server.server_close()
            worker.join(2)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0][:2], (len(payload), hashlib.sha256(payload).hexdigest()))
        self.assertNotIn("Transfer-Encoding", received[0][2])
        self.assertEqual(received[0][2]["X-Goog-Upload-Command"], "upload, finalize")
        self.assertEqual(set(read_sizes), {1024 * 1024})
        self.assertLessEqual(len(read_sizes), 5)

    def test_ssl_eof_queries_same_session_then_resumes_without_resending_confirmed_bytes(self):
        module = UpdateAudioModule()
        calls, sent = [], []

        def post(url, **kwargs):
            calls.append(kwargs["headers"].copy())
            if kwargs["headers"]["X-Goog-Upload-Command"] == "query":
                return Response(headers={"X-Goog-Upload-Status": "active", "X-Goog-Upload-Size-Received": "4"})
            body = kwargs["data"]
            if len(calls) == 1:
                sent.append(body.read(4))
                raise requests.exceptions.SSLError("EOF for https://upload.youtube.com/?upload_id=private-capability")
            self.assertEqual(kwargs["headers"]["X-Goog-Upload-Offset"], "4")
            sent.append(body.read())
            return Response()

        with patch("src.module.audio_module.post_with_stop", side_effect=post), patch("src.module.audio_module.wait_interruptibly"):
            module._next_upload_http("https://upload.youtube.com/?upload_id=private-capability", "music.mp3", "cookie",
                                     data=b"abcdefghij", single_request=True)
        self.assertEqual(b"".join(sent), b"abcdefghij")
        self.assertEqual(len(calls), 3)

    def test_exhausted_ssl_failure_hides_session_url_in_logs_and_ui_error(self):
        module = UpdateAudioModule()
        module._MAX_UPLOAD_RETRIES = 1
        log = io.StringIO()
        from loguru import logger
        sink = logger.add(log, level="WARNING")
        try:
            with patch("src.module.audio_module.post_with_stop", side_effect=requests.exceptions.SSLError(
                "EOF for https://upload.youtube.com/?upload_id=private-capability"
            )), patch("src.module.audio_module.wait_interruptibly"):
                with self.assertRaises(AudioUpdateError) as raised:
                    module._next_upload_http("https://upload.youtube.com/?upload_id=private-capability", "music.mp3", "cookie", data=b"abc")
        finally:
            logger.remove(sink)
        self.assertIn("SSLError", str(raised.exception))
        self.assertNotIn("private-capability", str(raised.exception))
        self.assertNotIn("private-capability", log.getvalue())
        self.assertNotIn("upload_id", log.getvalue())


if __name__ == "__main__":
    unittest.main()
