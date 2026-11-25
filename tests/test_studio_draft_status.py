"""Regression coverage for Studio's observed DRAFT_STATUS_PUBLIC payloads."""
import copy
from collections import Counter
from datetime import date
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from src.audio_recovery import _is_currently_public_video, _is_currently_scheduled_video
from src.module.list_videos_module import ListVideosModule
from src.module.model import Video
from src.video_publishing import publishing_row_matches, publishing_video_type
from src.video_publishing_tasks import VideoPublishingController
from src.video_scan_dates import _status_indicates_draft, scan_date_bounds, video_matches_scan_dates

CHANNEL = "UC" + "a" * 22


def video(index, **changes):
    values = dict(id=f"v{index:010d}", channel_id=CHANNEL, title=f"Song {index}", description="", thumbnail="", duration_ms=60000,
                  privacy="VIDEO_PRIVACY_PRIVATE", draft_status="DRAFT_STATUS_PUBLIC", copyright_check_status="COPYRIGHT_CHECK_NO_ISSUES")
    values.update(changes)
    return Video(**values)


class MemoryState:
    def load_state(self, _key):
        return None

    def save_state(self, _key, _value):
        return True


class StudioDraftEnumTests(unittest.TestCase):
    def test_intended_privacy_draft_enums_are_all_drafts(self):
        for prefix in ("DRAFT_STATUS_", "VIDEO_DRAFT_STATUS_"):
            for privacy in ("PUBLIC", "PRIVATE", "UNLISTED"):
                with self.subTest(prefix=prefix, privacy=privacy):
                    value = prefix + privacy
                    self.assertTrue(_status_indicates_draft(value))
                    self.assertEqual(publishing_video_type(video(1, draft_status=value)), "draft")

    def test_none_and_plain_privacy_values_are_not_drafts(self):
        for value in ("DRAFT_STATUS_NONE", "VIDEO_DRAFT_STATUS_NONE", "DRAFT_STATUS_UNSPECIFIED", "PUBLIC", "VIDEO_PRIVACY_PUBLIC", "PRIVATE", "", None):
            with self.subTest(value=value):
                self.assertFalse(_status_indicates_draft(value))

    def test_nested_enums_and_explicit_false_are_distinguished(self):
        self.assertTrue(_status_indicates_draft({"status": "DRAFT_STATUS_PUBLIC"}))
        self.assertFalse(_status_indicates_draft({"isDraft": False, "status": "DRAFT_STATUS_PUBLIC"}))

    def test_public_target_draft_is_neither_already_public_nor_finally_scheduled(self):
        item = video(1, privacy="VIDEO_PRIVACY_PUBLIC", scheduled_publishing_details={"publishTimeSeconds": 2000000000})
        self.assertFalse(_is_currently_public_video(item))
        self.assertFalse(_is_currently_scheduled_video(item))
        self.assertEqual(publishing_video_type(item), "draft")

    def test_draft_public_uses_upload_date_instead_of_publication_date(self):
        item = video(1, privacy="VIDEO_PRIVACY_PUBLIC", time_created_seconds="2026-10-21T12:00:00+07:00",
                     time_published_seconds="2026-10-19T12:00:00+07:00")
        bounds = scan_date_bounds("2026-10-20", end_date=date(2026, 10, 22))
        self.assertTrue(video_matches_scan_dates(item, bounds, date_type="auto"))
        self.assertFalse(video_matches_scan_dates(item, bounds, date_type="published"))


class StudioDraftListTests(unittest.TestCase):
    def test_server_draft_filter_is_evidence_only_when_enum_is_omitted(self):
        channel = SimpleNamespace(id=CHANNEL, delegated_session_id="delegate", role="OWNER", cookies=[{"name": "SAPISID", "value": "fake"}], cookie_string=lambda: "SID=fake")
        module = ListVideosModule()
        for draft_only, raw, expected in ((False, {}, "private"), (True, {}, "draft"),
                                          (True, {"draftStatus": "DRAFT_STATUS_NONE"}, "private"),
                                          (True, {"draftStatus": False}, "private"),
                                          (True, {"draftStatus": 0}, "private"),
                                          (False, {"draftStatus": "DRAFT_STATUS_PUBLIC"}, "draft")):
            item = {"videoId": "v0000000001", "channelId": CHANNEL, "privacy": "VIDEO_PRIVACY_PRIVATE", **raw}
            response = Mock(status_code=200)
            response.json.return_value = {"videos": [item]}
            with self.subTest(draft_only=draft_only, raw=raw), \
                    patch("src.module.list_videos_module.get_channels_info", return_value=channel), \
                    patch.object(module, "_get_session_token", return_value="fake-token"), \
                    patch("src.module.list_videos_module.post_with_stop", return_value=response):
                videos, _ = module.list_all_videos(CHANNEL, draft_only=draft_only)
                self.assertEqual(publishing_video_type(videos[0]), expected)
                if "draftStatus" in raw:
                    self.assertEqual(videos[0].draft_status, raw["draftStatus"])

    def test_merge_keeps_draft_specific_evidence_without_duplicating_video(self):
        broad = video(1, draft_status="")
        draft = video(1, draft_status={"isDraft": True})
        listing = Mock()
        listing.list_all_videos.side_effect = [([broad], None), ([draft], None)]
        controller = VideoPublishingController(storage=MemoryState(), listing=listing)
        controller.settings["channel_ids"] = [CHANNEL]
        with patch("src.video_publishing_tasks.get_channels_info", return_value=[SimpleNamespace(id=CHANNEL)]):
            controller._scan(controller.settings, Mock())
        self.assertEqual(len(controller.rows), 1)
        self.assertEqual(controller.rows[0]["visibility_type"], "draft")
        self.assertEqual(controller.rows[0]["draft_status"], {"isDraft": True})
        self.assertFalse(controller.snapshot()["needs_rescan"])

    def test_observed_channel_shape_has_39_drafts_not_39_private_videos(self):
        drafts = [video(index) for index in range(1, 40)]
        for item in drafts[2:35]:
            item.restriction_details = {"copyrightSummary": {"policy": "COPYRIGHT_POLICY_PARTIALLY_BLOCKED"}}
        drafts[35].restriction_details = {"copyrightSummary": {"policy": "COPYRIGHT_POLICY_BLOCKED"}}
        for item in drafts[36:]:
            item.copyright_check_status = "CHECK_STATUS_COMPLETED"
        public = [video(index, privacy="VIDEO_PRIVACY_PUBLIC", draft_status="DRAFT_STATUS_NONE") for index in range(40, 44)]
        broad = copy.deepcopy(drafts)
        for item in broad:
            item.draft_status = ""
        listing = Mock()
        listing.list_all_videos.side_effect = [(broad + public, None), (drafts, None)]
        controller = VideoPublishingController(storage=MemoryState(), listing=listing)
        controller.settings.update(channel_ids=[CHANNEL], scope="draft", categories=[])
        with patch("src.video_publishing_tasks.get_channels_info", return_value=[SimpleNamespace(id=CHANNEL)]):
            controller._scan(controller.settings, Mock())
        self.assertEqual(Counter(item["visibility_type"] for item in controller.rows), {"draft": 39, "public": 4})
        visible = [item for item in controller.rows if publishing_row_matches(item, scope="draft", categories=[])]
        self.assertEqual(len(visible), 39)
        self.assertEqual(Counter(item["copyright"] for item in visible), {"clear": 2, "partial": 33, "blocked": 1, "unknown": 3})
        self.assertEqual(sum(publishing_row_matches(item, scope="draft", categories=["clear"]) for item in controller.rows), 2)
        controller.select_filtered()
        self.assertEqual(sum(item["selected"] for item in controller.rows), 36)


if __name__ == "__main__":
    unittest.main()
