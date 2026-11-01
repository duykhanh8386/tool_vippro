import unittest
from unittest.mock import patch

from src.module.audio_module import AudioUpdateError, UpdateAudioModule


def track(video, language, content_type, status="READY", track_id=None):
    return {
        "videoId": video, "language": language,
        "audioTrackId": track_id or f"{video}-{language}-{content_type}",
        "source": "AUDIO_TRACK_SOURCE_UPLOAD" if content_type == "original" else "AUDIO_TRACK_SOURCE_CREATOR",
        "audioContentTypeString": content_type, "status": "AUDIO_TRACK_STATUS_" + status,
    }


def payload(video_ids, tracks=()):
    return {
        "videoTranslations": [{"videoId": video_id, "translations": []} for video_id in video_ids],
        "audioTracks": list(tracks),
    }


class AudioDescriptionScanTests(unittest.TestCase):
    def test_scan_selects_only_missing_selected_regions_and_keeps_ready_or_processing_descriptions(self):
        module = UpdateAudioModule()
        response = payload(["a", "b", "c"], [
            track("a", "en-AU", "descriptive"),
            track("a", "en-AU", "descriptive", "FAILED", track_id="older-failed"),
            track("a", "en-CA", "dubbed"),
            track("b", "en-AU", "descriptive", "PROCESSING"),
            track("b", "en-CA", "descriptive"),
            track("c", "en-AU", "dubbed"),
            track("other-video", "en-CA", "descriptive"),
        ])
        with patch.object(module, "_get_video_translation_payload", return_value=response):
            found = module.get_missing_audio_description_targets(["a", "b", "c"], "channel", ["en-AU", "en-CA"])
        self.assertEqual(set(found), {"a", "c"})
        self.assertEqual(found["a"], [{
            "language": "en-CA", "reason": "missing_description", "track_ids": [], "audio_present": True,
        }])
        self.assertEqual([action["language"] for action in found["c"]], ["en-AU", "en-CA"])
        self.assertFalse(found["c"][1]["audio_present"])

    def test_source_audio_is_a_valid_prerequisite_but_not_a_description(self):
        module = UpdateAudioModule()
        with patch.object(module, "_get_video_translation_payload", return_value=payload(["a"], [
            track("a", "pcm", "original"), track("a", "en", "dubbed", "FAILED"),
        ])):
            found = module.get_missing_audio_description_targets(["a"], "channel", ["pcm", "en"])
        self.assertTrue(found["a"][0]["audio_present"])
        self.assertEqual(found["a"][0]["track_ids"], [])
        self.assertFalse(found["a"][1]["audio_present"])
        self.assertEqual(found["a"][1]["track_ids"], ["a-en-dubbed"])

    def test_original_language_eligibility_lock_does_not_request_another_dub(self):
        module = UpdateAudioModule()
        with patch.object(module, "_get_video_translation_payload", return_value=payload(["a"], [
            track("a", "pcm", "original", "INELIGIBLE"),
        ])):
            found = module.get_missing_audio_description_targets(["a"], "channel", ["pcm"])
        self.assertTrue(found["a"][0]["audio_present"])
        self.assertEqual(found["a"][0]["track_ids"], [])

    def test_language_rows_supply_missing_root_languages_for_both_track_types(self):
        module = UpdateAudioModule()
        response = payload(["a"], [
            track("a", "", "dubbed", track_id="dub"),
            track("a", "", "descriptive", track_id="desc"),
        ])
        response["videoTranslations"][0]["translations"] = [{
            "languageCode": "pt-BR", "audioTranslation": {"audioTrackId": "dub"},
            "descriptiveAudioTranslation": {"audioTrackId": "desc"},
        }]
        with patch.object(module, "_get_video_translation_payload", return_value=response):
            state = module.get_audio_track_states("a", "channel", ["pt-BR"])
            self.assertEqual(module.get_missing_audio_description_targets(["a"], "channel", ["pt-BR"]), {})
        self.assertEqual(state["pt-BR"]["descriptive"], "healthy")
        self.assertEqual(state["pt-BR"]["dubbed"], "healthy")

    def test_partial_batch_retries_missing_video_without_treating_an_omission_as_missing_audio(self):
        module = UpdateAudioModule()
        unreadable = []
        with patch.object(module, "_get_video_translation_payload", side_effect=[
            payload(["a"]), payload(["unrelated"]),
        ]) as fetch:
            found = module.get_missing_audio_description_targets(["a", "b"], "channel", ["en"], unreadable)
        self.assertEqual(set(found), {"a"})
        self.assertEqual(unreadable, ["b"])
        self.assertEqual([call.args[0] for call in fetch.call_args_list], [["a", "b"], ["b"]])

    def test_precondition_failure_splits_batch_and_preserves_unreadable_ids(self):
        module = UpdateAudioModule()
        unreadable = []

        def fetch(video_ids, _channel):
            if len(video_ids) > 1 or video_ids == ["b"]:
                raise AudioUpdateError("precondition", status_code=400)
            return payload(video_ids)

        with patch.object(module, "_get_video_translation_payload", side_effect=fetch):
            found = module.get_missing_audio_description_targets(["a", "b"], "channel", ["en"], unreadable)
        self.assertEqual(set(found), {"a"})
        self.assertEqual(unreadable, ["b"])

    def test_batched_scan_deduplicates_ids(self):
        module = UpdateAudioModule()
        module._TRANSLATION_BATCH_SIZE = 2
        with patch.object(module, "_get_video_translation_payload", side_effect=lambda ids, channel: payload(ids)) as fetch:
            found = module.get_missing_audio_description_targets(["a", "b", "a", "c"], "channel", ["es-419"])
        self.assertEqual(set(found), {"a", "b", "c"})
        self.assertEqual([call.args[0] for call in fetch.call_args_list], [["a", "b"], ["c"]])

    def test_missing_or_malformed_status_is_not_a_successful_read(self):
        module = UpdateAudioModule()
        for response in (payload(["other"]), {"videoTranslations": [{"videoId": "a"}], "audioTracks": {}},
                         {"videoTranslations": [{"videoId": "a", "status": "ERROR"}]}):
            with self.subTest(response=response), patch.object(module, "_get_video_translation_payload", return_value=response):
                with self.assertRaises(AudioUpdateError):
                    module.get_audio_track_states("a", "channel", ["en"])

    def test_delete_all_dubs_preserves_source_and_descriptive_tracks(self):
        module = UpdateAudioModule()
        response = payload(["a"], [
            track("a", "pcm", "original"), track("a", "en", "dubbed"),
            track("a", "en", "descriptive"), track("other", "fr", "dubbed"),
        ])
        with patch.object(module, "_get_video_translation_payload", return_value=response), patch.object(
            module, "delete_track_ids", return_value=200,
        ) as delete:
            self.assertEqual(module.delete("a", "channel"), 200)
        delete.assert_called_once_with("a", "channel", ["a-en-dubbed"])

    def test_legacy_translation_only_dub_can_still_be_deleted(self):
        module = UpdateAudioModule()
        response = {"videoTranslations": [{"translations": [{
            "languageCode": "en", "audioTranslation": {"audioTrackId": "legacy-dub"},
        }]}]}
        with patch.object(module, "_get_video_translation_payload", return_value=response):
            self.assertEqual(module._get_all_audio_track_ids("a", "channel"), ["legacy-dub"])

    def test_translation_only_description_and_caption_references_are_preserved_on_delete(self):
        module = UpdateAudioModule()
        response = {"videoTranslations": [{"videoId": "a", "translations": [{
            "languageCode": "en", "audioTranslation": {"audioTrackId": "dub"},
            "descriptiveAudioTranslation": {"audioTrackId": "desc", "publishStatus": "PUBLISHED"},
            "captionsTranslation": {"audioTrackId": "caption-source"},
        }]}]}
        with patch.object(module, "_get_video_translation_payload", return_value=response):
            self.assertEqual(module._get_all_audio_track_ids("a", "channel"), ["dub"])
            self.assertEqual(module.get_missing_audio_description_targets(["a"], "channel", ["en"]), {})

    def test_removed_description_is_selected_without_selecting_a_processing_one(self):
        module = UpdateAudioModule()
        with patch.object(module, "_get_video_translation_payload", return_value=payload(["a"], [
            track("a", "en", "descriptive", "DELETED"),
            track("a", "vi", "descriptive", "PROCESSING"),
        ])):
            found = module.get_missing_audio_description_targets(["a"], "channel", ["en", "vi"])
        self.assertEqual([action["language"] for action in found["a"]], ["en"])


if __name__ == "__main__":
    unittest.main()
