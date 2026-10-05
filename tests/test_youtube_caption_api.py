import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from unittest.mock import Mock, patch

from src.youtube_caption_api import (
    CaptionQuotaExceededError,
    YouTubeCaptionClient,
    _raise_api_error,
    authorize_caption_channel,
    find_caption_oauth_client,
    publish_translated_caption,
)


class YouTubeCaptionApiTests(unittest.TestCase):
    @staticmethod
    def _write_oauth_client(path: Path, client_id: str = "client") -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "installed": {
                        "client_id": client_id,
                        "client_secret": "secret",
                    }
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_oauth_client_is_found_from_saved_path_without_customer_picker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            saved = self._write_oauth_client(root / "publisher-client.json")
            fallback = self._write_oauth_client(root / "fallback.json", "fallback")
            with (
                patch.dict(
                    os.environ,
                    {"TVAUTOMATION_GOOGLE_OAUTH_CLIENT": str(fallback)},
                ),
                patch("src.youtube_caption_api.get_data_dir", return_value=root / "data"),
            ):
                found = find_caption_oauth_client(saved)

        self.assertEqual(found, saved.resolve())

    def test_invalid_saved_oauth_client_falls_back_to_publisher_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            invalid = root / "invalid.json"
            invalid.write_text("{}", encoding="utf-8")
            fallback = self._write_oauth_client(root / "google.json")
            with (
                patch.dict(
                    os.environ,
                    {"TVAUTOMATION_GOOGLE_OAUTH_CLIENT": str(fallback)},
                ),
                patch("src.youtube_caption_api.get_data_dir", return_value=root / "data"),
            ):
                found = find_caption_oauth_client(invalid)

        self.assertEqual(found, fallback.resolve())

    def test_oauth_client_is_found_inside_packaged_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packaged = self._write_oauth_client(
                root / "assets" / "client_secret_desktop.json"
            )
            with (
                patch.dict(os.environ, {}, clear=False),
                patch("src.youtube_caption_api.get_data_dir", return_value=root / "data"),
                patch("src.youtube_caption_api.sys._MEIPASS", str(root), create=True),
            ):
                os.environ.pop("TVAUTOMATION_GOOGLE_OAUTH_CLIENT", None)
                found = find_caption_oauth_client()

        self.assertEqual(found, packaged.resolve())

    def test_authorization_uses_saved_email_without_forcing_account_picker(self):
        opened_urls = []

        class FakeServer:
            server_port = 43210

            def __init__(self, _address, handler_class):
                self.handler_class = handler_class
                self.timeout = None

            def handle_request(self):
                handler = object.__new__(self.handler_class)
                handler.path = "/?state=expected-state&code=authorization-code"
                handler.send_response = Mock()
                handler.send_header = Mock()
                handler.end_headers = Mock()
                handler.wfile = io.BytesIO()
                handler.do_GET()

            def server_close(self):
                return None

        with tempfile.TemporaryDirectory() as directory:
            client = self._write_oauth_client(Path(directory) / "client.json")
            token_response = Mock(status_code=200)
            token_response.json.return_value = {
                "access_token": "token",
                "refresh_token": "refresh",
                "expires_in": 3600,
            }
            with (
                patch("src.youtube_caption_api.HTTPServer", FakeServer),
                patch(
                    "src.youtube_caption_api.secrets.token_urlsafe",
                    side_effect=["expected-state", "verifier"],
                ),
                patch(
                    "src.youtube_caption_api.webbrowser.open",
                    side_effect=lambda url, **_kwargs: opened_urls.append(url),
                ),
                patch(
                    "src.youtube_caption_api.requests.post",
                    return_value=token_response,
                ),
                patch(
                    "src.youtube_caption_api._verify_authorized_channel",
                    return_value="channel",
                ),
                patch("src.youtube_caption_api._save_oauth_record"),
            ):
                authorize_caption_channel(
                    "channel",
                    client,
                    login_hint="owner@example.com",
                )

        query = parse_qs(urlparse(opened_urls[0]).query)
        self.assertEqual(query["login_hint"], ["owner@example.com"])
        self.assertEqual(query["prompt"], ["consent"])

    def test_quota_error_is_persisted_and_exposed_as_specific_exception(self):
        response = Mock(status_code=403)
        response.json.return_value = {
            "error": {
                "message": "quota",
                "errors": [{"reason": "quotaExceeded"}],
            }
        }

        with patch("src.youtube_caption_api._mark_quota_exhausted") as mark:
            with self.assertRaises(CaptionQuotaExceededError):
                _raise_api_error(response, "đăng phụ đề")

        mark.assert_called_once()

    def test_translation_download_uses_base_iso_language(self):
        response = Mock(status_code=200, content=b"translated srt")
        with (
            patch("src.youtube_caption_api._access_token", return_value="token"),
            patch("src.youtube_caption_api.requests.get", return_value=response) as get,
        ):
            result = YouTubeCaptionClient("channel").download_translation(
                "caption", "en-AU"
            )

        self.assertEqual(result, b"translated srt")
        self.assertEqual(get.call_args.kwargs["params"]["tlang"], "en")

    def test_serving_existing_language_is_not_reuploaded_on_manual_rerun(self):
        client = YouTubeCaptionClient("channel")
        existing = [{"id": "caption", "snippet": {"language": "fr"}}]
        with (
            patch.object(client, "insert_track") as insert,
            patch.object(client, "update_track") as update,
        ):
            caption_id, status = client.upsert_track(
                video_id="video",
                language="fr",
                srt_bytes=b"srt",
                existing_tracks=existing,
                replace_existing=False,
            )

        self.assertEqual((caption_id, status), ("caption", "already_added"))
        insert.assert_not_called()
        update.assert_not_called()

    def test_failed_existing_caption_is_updated_on_manual_rerun(self):
        client = YouTubeCaptionClient("channel")
        existing = [
            {
                "id": "caption",
                "snippet": {
                    "language": "fr",
                    "status": "failed",
                    "failureReason": "processingFailed",
                },
            }
        ]
        with patch.object(
            client,
            "update_track",
            return_value={
                "id": "caption",
                "snippet": {"language": "fr", "status": "syncing"},
            },
        ) as update:
            caption_id, status = client.upsert_track(
                video_id="video",
                language="fr",
                srt_bytes=b"srt",
                existing_tracks=existing,
                replace_existing=False,
            )

        self.assertEqual((caption_id, status), ("caption", "successful"))
        update.assert_called_once_with("caption", b"srt")

    def test_manual_rerun_does_not_translate_or_upload_serving_track(self):
        tracks = [
            {
                "id": "caption",
                "snippet": {"language": "fr", "status": "serving"},
            }
        ]
        with (
            patch(
                "src.youtube_caption_api.get_caption_quota_status",
                return_value={"blocked": False},
            ),
            patch.object(
                YouTubeCaptionClient,
                "download_translation",
            ) as download,
            patch.object(YouTubeCaptionClient, "upsert_track") as upsert,
        ):
            status = publish_translated_caption(
                channel_id="channel",
                video_id="video",
                source_track_id="source",
                source_language="en",
                source_srt_path="unused.srt",
                target_language="fr",
                existing_tracks=tracks,
                replace_existing=False,
            )

        self.assertEqual(status, "already_added")
        download.assert_not_called()
        upsert.assert_not_called()
