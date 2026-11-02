import copy
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch

from src.module.audio_module import AudioUpdateError, UpdateAudioModule
from test_audio_module import Response


def track(kind="descriptive", status="PENDING", track_id="new", language="en", video="video"):
    return {"videoId": video, "audioTrackId": track_id, "language": language,
            "audioContentTypeString": kind, "source": "AUDIO_TRACK_SOURCE_CREATOR",
            "status": "AUDIO_TRACK_STATUS_" + status,
            "failureReason": "AUDIO_TRACK_FAILURE_REASON_UNSPECIFIED"}


class AudioUploadConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.module = UpdateAudioModule()
        self.events = []
        self.new_track = track()
        self.payload = {"videoTranslations": [{"videoId": "video", "translations": []}], "audioTracks": []}
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.fetch = self.stack.enter_context(patch.object(
            self.module, "_get_video_translation_payload", side_effect=lambda *_: copy.deepcopy(self.payload),
        ))
        self.stack.enter_context(patch("src.module.audio_module.get_channels_info",
                                      return_value=SimpleNamespace(cookies=[])))
        self.stack.enter_context(patch.object(self.module, "_get_session_token", return_value="token"))
        self.start = self.stack.enter_context(patch.object(
            self.module, "_upload_http", side_effect=lambda **_: self.event("start", ("https://session", "resource")),
        ))
        self.upload = self.stack.enter_context(patch.object(
            self.module, "_next_upload_http", side_effect=lambda **_: self.event("finalize", "final"),
        ))
        self.register = self.stack.enter_context(patch.object(self.module, "_update", side_effect=self.publish))
        self.wait = self.stack.enter_context(patch("src.module.audio_module.wait_interruptibly"))

    def event(self, name, result):
        self.events.append(name)
        return result

    def publish(self, **kwargs):
        self.assertEqual(self.events, ["start"])
        self.events.append("publish")
        if self.new_track is not None:
            self.payload["audioTracks"].append(self.new_track)
        return 200

    def add(self, kind="descriptive", progress=None):
        return self.module.add("video", "channel", "music.mp3", "en", data=b"audio",
                               audio_content_type=kind, progress=progress)

    def test_registers_before_transfer_and_verifies_processing_only_after_file_finishes(self):
        progress = {}
        self.assertEqual(self.add(progress=progress), 200)
        self.assertEqual(self.events, ["start", "publish", "finalize"])
        self.assertEqual(progress["studio_state"], "processing")
        self.assertEqual(progress["track_id"], "new")
        self.assertEqual(self.fetch.call_count, 2)

    def test_published_new_dub_is_verified_without_waiting_for_description(self):
        self.new_track = track("dubbed", "PROCESSED")
        progress = {}
        self.assertEqual(self.add("dubbed", progress), 200)
        self.assertEqual(progress["studio_state"], "published")
        self.wait.assert_not_called()

    def test_new_failed_track_is_an_error_instead_of_uploaded_success(self):
        self.new_track = track(status="FAILED")
        progress = {}
        with self.assertRaisesRegex(AudioUpdateError, "AUDIO_TRACK_STATUS_FAILED"):
            self.add(progress=progress)
        self.assertEqual(progress["status"], "error")
        self.assertEqual(progress["track_id"], "new")
        self.wait.assert_not_called()

    def test_http_success_with_unchanged_failed_track_is_rejected(self):
        self.payload["audioTracks"] = [track(status="FAILED", track_id="old-error")]
        self.new_track = None
        with self.assertRaisesRegex(AudioUpdateError, "unchanged: old-error"):
            self.add()
        self.assertEqual(self.wait.call_count, 3)

    def test_missing_and_unknown_status_are_not_verified(self):
        for new_track in [None, track(status="UNSPECIFIED")]:
            with self.subTest(track=new_track):
                self.events.clear()
                self.payload["audioTracks"] = []
                self.new_track = new_track
                with self.assertRaises(AudioUpdateError):
                    self.add()

    def test_a_different_video_language_or_type_cannot_confirm_the_upload(self):
        for new_track in [track(video="other"), track(language="fr"), track(kind="dubbed")]:
            with self.subTest(track=new_track):
                self.events.clear()
                self.payload["audioTracks"] = []
                self.new_track = new_track
                with self.assertRaises(AudioUpdateError):
                    self.add()

    def test_a_healthy_track_is_preserved_before_opening_an_upload_session(self):
        self.payload["audioTracks"] = [track(status="PROCESSED", track_id="working")]
        self.assertEqual(self.add(), 409)
        self.start.assert_not_called()
        self.upload.assert_not_called()
        self.register.assert_not_called()

    def test_an_existing_processing_track_is_preserved(self):
        self.payload["audioTracks"] = [track(track_id="already-processing")]
        with self.assertRaises(AudioUpdateError):
            self.add()
        self.start.assert_not_called()

    def test_processing_snapshot_never_counts_an_unchanged_track_as_new(self):
        old = track(track_id="existing")
        self.payload["audioTracks"] = [old]
        with self.assertRaisesRegex(AudioUpdateError, "unchanged"):
            self.module._verify_audio_upload("video", "channel", "en", "descriptive", {"existing": old})

    def test_same_id_is_accepted_only_if_a_failed_track_really_changes_state(self):
        old = track(status="FAILED", track_id="existing")
        self.payload["audioTracks"] = [track(track_id="existing")]
        progress = {}
        self.module._verify_audio_upload("video", "channel", "en", "descriptive", {"existing": old}, progress=progress)
        self.assertEqual(progress["studio_state"], "processing")

    def test_upload_failure_keeps_the_registered_track_unconfirmed(self):
        self.upload.side_effect = AudioUpdateError("file not finalized")
        progress = {}
        with self.assertRaisesRegex(AudioUpdateError, "not finalized"):
            self.add(progress=progress)
        self.register.assert_called_once()
        self.assertTrue(progress["registered"])
        self.assertFalse(progress["file_finalized"])
        self.assertEqual(self.fetch.call_count, 1)

    def test_session_token_is_acquired_before_registering_the_track(self):
        def token(_channel):
            self.assertEqual(self.events, ["start"])
            return "fresh-token"

        with patch.object(self.module, "_get_session_token", side_effect=token):
            self.assertEqual(self.add(), 200)
        self.assertEqual(self.register.call_args.kwargs["session_token"], "fresh-token")

    def test_new_working_track_wins_over_a_new_failed_duplicate(self):
        self.payload["audioTracks"] = [track(track_id="working"), track(status="FAILED", track_id="failed")]
        progress = {}
        self.module._verify_audio_upload("video", "channel", "en", "descriptive", {}, progress=progress)
        self.assertEqual(progress["track_id"], "working")

    def test_unreadable_video_stops_before_uploading(self):
        self.payload = {"videoTranslations": [], "audioTracks": []}
        with self.assertRaises(AudioUpdateError):
            self.add()
        self.start.assert_not_called()

    def test_rpc_error_inside_http_200_is_not_success(self):
        with self.assertRaisesRegex(AudioUpdateError, "permission denied") as raised:
            self.module._check_audio_rpc_response(Response(body={"error": {"code": 403, "message": "permission denied"}}), "add")
        self.assertEqual(raised.exception.status_code, 403)
        self.assertFalse(raised.exception.retryable)

    def test_deletion_waits_for_committed_inventory_and_keeps_unrelated_tracks(self):
        failed = track(status="FAILED", track_id="old")
        working = track(status="PROCESSED", track_id="working", language="fr")
        self.fetch.side_effect = [
            {"videoTranslations": [{"videoId": "video"}], "audioTracks": [failed, working]},
            {"videoTranslations": [{"videoId": "video"}], "audioTracks": [working]},
        ]
        self.module._confirm_audio_tracks_deleted("video", "channel", ["old"])
        self.assertEqual(self.fetch.call_count, 2)
        self.wait.assert_called_once_with(2)

    def test_unchanged_failed_track_cannot_confirm_deletion(self):
        self.payload["audioTracks"] = [track(status="FAILED", track_id="old")]
        with self.assertRaisesRegex(AudioUpdateError, "track_ids=old"):
            self.module._confirm_audio_tracks_deleted("video", "channel", ["old"])
        self.assertEqual(self.fetch.call_count, 4)

    def test_unreadable_inventory_cannot_confirm_deletion(self):
        self.payload = {"videoTranslations": [], "audioTracks": []}
        with self.assertRaises(AudioUpdateError):
            self.module._confirm_audio_tracks_deleted("video", "channel", ["old"])

    def test_deleted_tombstone_confirms_deletion(self):
        self.payload["audioTracks"] = [track(status="DELETED", track_id="old")]
        self.module._confirm_audio_tracks_deleted("video", "channel", ["old"])
        self.wait.assert_not_called()

    def test_empty_other_video_cannot_confirm_deletion_of_target_video(self):
        self.payload = {"videoTranslations": [{"videoId": "other"}], "audioTracks": []}
        with self.assertRaises(AudioUpdateError):
            self.module._confirm_audio_tracks_deleted("video", "channel", ["old"])

    def test_missing_upload_status_requires_a_confirming_query(self):
        with patch("src.module.audio_module.post_with_stop", side_effect=[
            Response(headers={}), Response(headers={"X-Goog-Upload-Status": "final"}),
        ]) as post:
            result = UpdateAudioModule()._next_upload_http("https://session", "music.mp3", "cookie", b"audio")
        self.assertEqual(result, "final")
        self.assertEqual(post.call_args_list[1].kwargs["headers"]["X-Goog-Upload-Command"], "query")

    def test_http_200_without_any_upload_status_is_not_complete(self):
        with patch("src.module.audio_module.post_with_stop", return_value=Response(headers={})):
            with self.assertRaises(AudioUpdateError):
                UpdateAudioModule()._next_upload_http("https://session", "music.mp3", "cookie", b"audio")


if __name__ == "__main__":
    unittest.main()
