import unittest
from unittest.mock import Mock, patch

from src.youtube_caption_api import (
    CaptionQuotaExceededError,
    YouTubeCaptionClient,
    _raise_api_error,
    publish_translated_caption,
)


class YouTubeCaptionApiTests(unittest.TestCase):
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
