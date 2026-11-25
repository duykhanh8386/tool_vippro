"""Synthetic sessions only: never change real YouTube videos or call ChatGPT."""
import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests

from src.module.model import Video
from src.module.video_publishing_module import VideoPublishingModule
from src.publishing_browser import video_search_results
from src.task_runtime import create_run_context
from src.publishing_browser import ChatGPTSessionNeedsAction
from src.video_publishing import (
    REFERENCE_SELECTION_VERSION, copyright_category, first_song, parse_chatgpt_cookies, plan_daily,
    publishing_row_matches, publishing_row_selectable, publishing_video_type,
    reference_search_query, reference_video_id, schedule_timestamp,
)
from src.video_publishing_tasks import STATE_KEY, VideoPublishingController
from src.video_scan_dates import VIETNAM_TIMEZONE

CHANNEL = "UC" + "a" * 22
CHANNEL2 = "UC" + "b" * 22
VIDEO = "Abc123_-XYZ"
OTHER = "Def123_-XYZ"
NOW = datetime(2099, 1, 1, tzinfo=VIETNAM_TIMEZONE)
STAMP = int(datetime(2099, 1, 2, 18, tzinfo=VIETNAM_TIMEZONE).timestamp())
REFERENCE = {"video_id": "Ghi123_-XYZ", "url": "https://www.youtube.com/watch?v=Ghi123_-XYZ",
             "title": "Músicas Católicas 🎵", "description": "Primeira linha\n\n00:00 Canção de Fé\n#Música",
             "thumbnail": "https://i.ytimg.com/vi/Ghi123_-XYZ/maxresdefault.jpg"}


def video(identifier=VIDEO, **changes):
    values = dict(id=identifier, channel_id=CHANNEL, title="Original", description="00:00 First song\n03:00 Second song",
                  thumbnail="", duration_ms=60000, privacy="PRIVATE", copyright_check_status="COPYRIGHT_CHECK_NO_ISSUES",
                  time_created_seconds=1000)
    values.update(changes)
    return Video(**values)


def row(identifier=VIDEO, **changes):
    values = dict(video_id=identifier, channel_id=CHANNEL, old_title="Original", old_description="old description",
                  song="First song", copyright="clear", copyright_label="Không có vấn đề bản quyền", selected=True,
                  status="scanned", detail="")
    values.update(changes)
    return values


class MemoryState:
    def __init__(self):
        self.data, self.fail = {}, False

    def load_state(self, key):
        return copy.deepcopy(self.data.get(key))

    def save_state(self, key, value):
        if self.fail:
            return False
        self.data[key] = copy.deepcopy(value)
        return True


class CopyrightTests(unittest.TestCase):
    def test_finished_check_is_not_claim_free(self):
        self.assertEqual(copyright_category(video(copyright_check_status="CHECK_STATUS_COMPLETED")), "unknown")

    def test_no_issues_is_clear(self):
        self.assertEqual(copyright_category(video()), "clear")

    def test_blocking_overrides_successful_precheck(self):
        details = {"copyrightSummary": {"policy": "COPYRIGHT_POLICY_PARTIALLY_BLOCKED"}}
        self.assertEqual(copyright_category(video(restriction_details=details)), "partial")
        details["copyrightSummary"]["policy"] = "COPYRIGHT_POLICY_BLOCKED"
        self.assertEqual(copyright_category(video(restriction_details=details)), "blocked")


class VideoTypeSelectionTests(unittest.TestCase):
    def test_studio_visibility_and_draft_status_are_separate(self):
        for item, expected in ((video(privacy="PUBLIC", draft_status="DRAFT_STATUS_DRAFT"), "draft"),
                               (video(video_status="VIDEO_STATUS_DRAFT"), "draft"),
                               (video(), "private"), (video(privacy="VIDEO_PRIVACY_UNLISTED"), "unlisted"),
                               (video(privacy="PUBLIC"), "public"),
                               (video(privacy="PUBLIC", scheduled_publishing_details={"publishTimeSeconds": STAMP}), "scheduled"),
                               (video(privacy=""), "unknown")):
            self.assertEqual(publishing_video_type(item), expected)

    def test_filtering_is_independent_from_selectability(self):
        item = row(visibility_type="private", copyright="partial")
        self.assertFalse(publishing_row_matches(item, scope="draft", categories=["clear"]))
        self.assertTrue(publishing_row_selectable(item))
        self.assertTrue(publishing_row_matches(item, scope="private", categories=["partial"]))
        self.assertTrue(publishing_row_matches(item, scope="unpublished", categories=[]))

    def test_public_scheduled_and_unknown_rows_cannot_be_selected(self):
        for changes in ({"visibility_type": "public"}, {"visibility_type": "scheduled"}, {"visibility_type": "unknown"},
                        {"copyright": "unknown"}, {"copyright": "checking"}, {"status": "successful"}):
            self.assertFalse(publishing_row_selectable(row(**changes)))

    def test_claim_ids_and_flags_override_clear_status(self):
        for details in ({"claimDetails": {"claims": [{"claimId": "claim-1"}]}},
                        {"copyrightSummary": {"hasCopyrightClaims": True}}):
            self.assertEqual(copyright_category(video(restriction_details=details)), "limited")

    def test_unrelated_none_and_false_do_not_prove_no_copyright(self):
        item = video(copyright_check_status="", restriction_details={"statusDetails": {"ageRestriction": "NONE", "hasWarning": False}})
        self.assertEqual(copyright_category(item), "unknown")

    def test_explicit_no_claims_and_completed_empty_restrictions(self):
        self.assertEqual(copyright_category(video(copyright_check_status="", restriction_details={"copyrightSummary": {"hasClaims": False}})), "clear")
        self.assertEqual(copyright_category(video(copyright_check_status="CHECK_COMPLETED", restriction_details={"allRestrictions": {"restrictions": []}})), "clear")

    def test_checking_overrides_stale_no_claims(self):
        self.assertEqual(copyright_category(video(copyright_check_status="CHECK_STATUS_PENDING", restriction_details={"copyrightSummary": {"hasClaims": False}})), "checking")

    def test_global_block_overrides_partial_block(self):
        details = {"copyrightSummary": {"policy": "PARTIALLY_BLOCKED", "isBlockedWorldwide": True}}
        self.assertEqual(copyright_category(video(restriction_details=details)), "blocked")


class ReferenceAndCookieTests(unittest.TestCase):
    def test_youtube_id_suffix_in_thai_mp4_filename(self):
        name = "เจ็บกว่าเธอ – ดอน สอนระเบียบ ｜ Acoustic & Rock Version ｜ AC-Studio-Official [ZoHtnOPSE80]"
        for suffix in ("", ".mp4", ".MP4", ".webm", "   "):
            self.assertEqual(reference_video_id(name + suffix), "ZoHtnOPSE80")

    def test_only_valid_ids_at_end_of_filename_are_recognized(self):
        for title in ("Song [short]", "Song [ZoHtnOPSE80] more text", "Song [ZoHtnOPSE800]", "Song ZoHtnOPSE80", "Song [bad id here]"):
            self.assertEqual(reference_video_id(title), "")

    def test_search_query_omits_file_extension_and_source_id(self):
        for title in ("Song.mp4", "Song [ZoHtnOPSE80].MP4", "Song [ZoHtnOPSE80]", "Song"):
            self.assertEqual(reference_search_query(title), "Song")

    def test_first_track_timestamps_preserve_accents(self):
        self.assertEqual(first_song("Mix", "Tracklist\n00:00:00 Diante do Rei\n03:00 Outra"), "Diante do Rei")
        self.assertEqual(first_song("Mix", "[00:00] - Canção de Fé\n03:00 Outra"), "Canção de Fé")
        self.assertEqual(first_song("Mix", "1. Canção de Fé 00:00\n2. Outra 03:00"), "Canção de Fé")
        self.assertEqual(first_song("Fallback title", "No chapters"), "Fallback title")

    def test_search_ignores_ads_and_shorts(self):
        data = {"contents": [{"adSlotRenderer": {"videoRenderer": {"videoId": OTHER}}},
                             {"reelShelfRenderer": {"videoRenderer": {"videoId": OTHER}}},
                             {"videoRenderer": {"videoId": VIDEO}}, {"videoRenderer": {"videoId": "bad"}}]}
        self.assertEqual(list(video_search_results(data)), [VIDEO])

    def test_header_cookie_preserves_equals_in_values(self):
        cookies = parse_chatgpt_cookies("Cookie: __Secure-next-auth.session-token=abc==; other=value")
        self.assertEqual(cookies[0]["value"], "abc==")
        self.assertEqual(cookies[0]["domain"], ".chatgpt.com")

    def test_json_cookie_filters_other_domains_and_keeps_host_only(self):
        cookies = parse_chatgpt_cookies(json.dumps([
            {"name": "session", "value": "secret", "domain": ".chatgpt.com", "expirationDate": 1234567890.5},
            {"name": "__Host-csrf", "value": "csrf", "domain": "chatgpt.com"},
            {"name": "evil", "value": "secret", "domain": "evilchatgpt.com"}]))
        self.assertEqual(len(cookies), 2)
        self.assertEqual(cookies[0]["expiry"], 1234567890)
        self.assertNotIn("domain", cookies[1])

    def test_invalid_cookie_errors_do_not_echo_secrets(self):
        for text in ("", "{badsecret", "[]", "abcsecret", '{"cookies": "mysecret"}'):
            with self.subTest(text=text), self.assertRaises(ValueError) as result:
                parse_chatgpt_cookies(text)
            self.assertNotIn("secret", str(result.exception))


class DailyPlanTests(unittest.TestCase):
    def test_daily_slots_are_independent_per_channel(self):
        rows = [row(), row(OTHER), row("Ghi123_-XYZ", channel_id=CHANNEL2)]
        result = plan_daily(rows, "2099-01-02", "18:00", now=NOW)
        self.assertEqual([item["publish_at"] for item in result], [STAMP, STAMP + 86400, STAMP])

    def test_any_existing_schedule_reserves_whole_day(self):
        result = plan_daily([row()], "2099-01-02", "18:00", now=NOW, occupied={CHANNEL: [STAMP - 3600]})
        self.assertEqual(result[0]["publish_at"], STAMP + 86400)

    def test_saved_assignments_and_successes_do_not_shift_on_retry(self):
        rows = [row(status="successful", selected=False, publish_at=STAMP), row(OTHER, publish_at=STAMP + 86400), row("Ghi123_-XYZ")]
        result = plan_daily(rows, "2099-01-02", "18:00", now=NOW)
        self.assertEqual([item["publish_at"] for item in result], [STAMP + 86400, STAMP + 172800])

    def test_can_resume_future_assignments_after_initial_start_day(self):
        result = plan_daily([row(publish_at=STAMP + 2 * 86400)], "2099-01-01", "18:00", now=NOW + timedelta(days=2))
        self.assertEqual(result[0]["publish_at"], STAMP + 2 * 86400)

    def test_schedule_timestamp_supports_studio_command_shape(self):
        for details in ({"timeSec": str(STAMP)}, {"scheduledPublishing": {"set": {"timeSec": str(STAMP)}}}):
            self.assertEqual(schedule_timestamp(video(scheduled_publishing_details=details)), STAMP)

    def test_invalid_past_and_expired_plans_are_rejected(self):
        for start, hour, rows in (("invalid", "18:00", [row()]), ("2098-01-01", "18:00", [row()]),
                                  ("2099-01-02", "25:00", [row()]), ("2099-01-02", "18:00:01", [row()]),
                                  ("2099-01-02", "18:00", [row(publish_at=NOW.timestamp() - 1)])):
            with self.subTest(start=start, hour=hour), self.assertRaises(ValueError):
                plan_daily(rows, start, hour, now=NOW)


class PublishingModuleTests(unittest.TestCase):
    def setUp(self):
        self.module = VideoPublishingModule()
        channel = SimpleNamespace(id=CHANNEL, role="OWNER", delegated_session_id="session", cookies=[], cookie_string=lambda: "cookie")
        self.patches = [patch("src.module.video_publishing_module.get_channels_info", return_value=channel),
                        patch("src.module.video_publishing_module.studio_authorization_header", return_value="hash"),
                        patch.object(self.module, "_get_session_token", return_value="token"),
                        patch("src.module.video_publishing_module.wait_interruptibly")]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)
        self.response = Mock(status_code=200)
        self.response.json.return_value = {}
        self.post = patch("src.module.video_publishing_module.post_with_stop", return_value=self.response).start()
        self.addCleanup(patch.stopall)

    def copy_metadata(self):
        return self.module.copy_metadata(CHANNEL, VIDEO, REFERENCE, expected_title="Original", expected_description="old description", categories=["clear"])

    def test_metadata_copy_is_exact_and_read_back(self):
        before = video(description="old description")
        after = video(title=REFERENCE["title"], description=REFERENCE["description"])
        with patch.object(self.module, "_get_video_info", side_effect=[before, after]):
            self.copy_metadata()
        payload = self.post.call_args.kwargs["json"]
        self.assertEqual(payload["title"]["newTitle"], REFERENCE["title"])
        self.assertEqual(payload["description"]["newDescription"], REFERENCE["description"])
        self.assertNotIn("scheduledPublishing", payload)

    def test_metadata_already_saved_does_not_submit_again(self):
        after = video(title=REFERENCE["title"], description=REFERENCE["description"])
        with patch.object(self.module, "_get_video_info", return_value=after):
            self.copy_metadata()
        self.post.assert_not_called()

    def test_changed_original_and_foreign_channel_block_mutation(self):
        for before in (video(title="Manual edit"), video(channel_id=CHANNEL2), video(privacy="PUBLIC"),
                       video(copyright_check_status="CHECK_COMPLETED"), video(privacy="")):
            with self.subTest(before=before), patch.object(self.module, "_get_video_info", return_value=before), self.assertRaises(ValueError):
                self.copy_metadata()
        self.post.assert_not_called()

    def test_uncertain_network_response_reads_back_without_resubmitting(self):
        after = video(title=REFERENCE["title"], description=REFERENCE["description"])
        self.post.side_effect = requests.ConnectionError("disconnect")
        with patch.object(self.module, "_get_video_info", side_effect=[video(description="old description"), after]):
            self.copy_metadata()
        self.assertEqual(self.post.call_count, 1)

    def test_no_success_without_readback(self):
        with patch.object(self.module, "_get_video_info", return_value=video(description="old description")), self.assertRaises(ValueError):
            self.copy_metadata()
        self.assertEqual(self.post.call_count, 1)

    def test_schedule_wire_format_and_readback(self):
        before = video(title=REFERENCE["title"], description=REFERENCE["description"])
        after = video(title=REFERENCE["title"], description=REFERENCE["description"], scheduled_publishing_details={"publishTimeSeconds": str(STAMP)})
        with patch.object(self.module, "_get_video_info", side_effect=[before, after]):
            result = self.module.schedule(CHANNEL, VIDEO, STAMP, REFERENCE, categories=["clear"])
        payload = self.post.call_args.kwargs["json"]
        self.assertEqual(payload["scheduledPublishing"]["set"], {"timeSec": str(STAMP), "privacy": "PUBLIC"})
        self.assertEqual(payload["privacyState"], {"newPrivacy": "PRIVATE"})
        self.assertEqual(schedule_timestamp(result), STAMP)

    def test_existing_schedule_is_idempotent_and_other_schedule_is_preserved(self):
        before = video(title=REFERENCE["title"], description=REFERENCE["description"], scheduled_publishing_details={"publishTimeSeconds": STAMP})
        with patch.object(self.module, "_get_video_info", return_value=before):
            self.module.schedule(CHANNEL, VIDEO, STAMP, REFERENCE, categories=["clear"])
            with self.assertRaises(ValueError):
                self.module.schedule(CHANNEL, VIDEO, STAMP + 86400, REFERENCE, categories=["clear"])
        self.post.assert_not_called()

    def test_unreadable_existing_schedule_is_preserved(self):
        before = video(scheduled_publishing_details={"unrecognizedScheduleShape": True})
        with patch.object(self.module, "_get_video_info", return_value=before), self.assertRaises(ValueError):
            self.copy_metadata()
        self.post.assert_not_called()


class PublishingControllerTests(unittest.TestCase):
    def setUp(self):
        self.storage = MemoryState()
        self.module, self.listing, self.reference, self.image, self.thumbnail = Mock(), Mock(), Mock(), Mock(), Mock()
        self.module.require_eligible.return_value = video()
        self.reference.find.return_value = dict(REFERENCE)
        self.listing.list_all_videos.return_value = ([], None)
        self.controller = VideoPublishingController(storage=self.storage, module=self.module, listing=self.listing,
                reference_factory=lambda: self.reference, image_factory=lambda cookie: self.image, thumbnail_factory=lambda: self.thumbnail)
        self.controller.settings.update(channel_ids=[CHANNEL], start_date="2099-01-02", hour="18:00")
        self.controller.set_cookie("session=private-secret")

    def test_cookie_never_saved_or_returned_in_snapshot(self):
        self.controller.change_settings(hour="19:00")
        self.assertNotIn("private-secret", json.dumps(self.storage.data))
        self.assertNotIn("private-secret", json.dumps(self.controller.snapshot()))
        self.assertTrue(self.controller.snapshot()["has_cookie"])

    def test_scan_all_pages_deduplicates_drafts_filters_and_reserves_days(self):
        claimed = video(OTHER, copyright_check_status="COPYRIGHT_CLAIMED")
        scheduled = video("Ghi123_-XYZ", scheduled_publishing_details={"publishTimeSeconds": STAMP})
        self.listing.list_all_videos.side_effect = [([video(), claimed], "next"), ([scheduled], None), ([video()], None)]
        with patch("src.video_publishing_tasks.get_channels_info", return_value=[SimpleNamespace(id=CHANNEL)]):
            self.controller._scan(self.controller.settings, self.reference)
        rows = self.controller.rows
        self.assertEqual(len(rows), 3)
        self.assertEqual([item["video_id"] for item in rows if item["selected"]], [])
        self.assertEqual(rows[0]["visibility_type"], "private")
        self.assertEqual(rows[1]["status"], "scanned")
        self.controller.select_filtered()
        self.assertEqual([item["video_id"] for item in rows if item["selected"]], [VIDEO])
        self.assertEqual(self.controller.occupied[CHANNEL], [STAMP])
        self.assertEqual(self.listing.list_all_videos.call_count, 3)

    def test_scan_repeated_tokens_and_foreign_channel_fail(self):
        for page in (([], "repeat"), ([video(channel_id=CHANNEL2)], None)):
            with self.subTest(page=page), patch("src.video_publishing_tasks.get_channels_info", return_value=[SimpleNamespace(id=CHANNEL)]):
                self.listing.list_all_videos.side_effect = None
                self.listing.list_all_videos.return_value = page
                with self.assertRaises(ValueError):
                    self.controller._scan(self.controller.settings, self.reference)

    def test_only_explicit_channel_source_is_used_even_when_both_inputs_exist(self):
        self.controller.settings.update(channel_ids=[CHANNEL], channel_links="https://www.youtube.com/channel/" + CHANNEL2)
        self.reference.resolve_channels.return_value = [CHANNEL2]
        with patch("src.video_publishing_tasks.get_channels_info", return_value=[SimpleNamespace(id=CHANNEL), SimpleNamespace(id=CHANNEL2)]):
            self.controller._scan(self.controller.settings, self.reference)
            self.reference.resolve_channels.assert_not_called()
            self.assertEqual(self.listing.list_all_videos.call_args.args[0], CHANNEL)
            self.controller.change_settings(channel_source="links")
            self.controller._scan(self.controller.settings, self.reference)
            self.reference.resolve_channels.assert_called_once()
            self.assertEqual(self.listing.list_all_videos.call_args.args[0], CHANNEL2)

    def test_legacy_channel_link_priority_is_restored_as_explicit_link_mode(self):
        self.storage.data[STATE_KEY] = {"settings": {"channel_ids": [CHANNEL], "channel_links": "https://youtube.com/@music"}, "rows": []}
        restored = VideoPublishingController(storage=self.storage)
        self.assertEqual(restored.settings["channel_source"], "links")

    def test_empty_selected_source_does_not_fall_back_to_other_source(self):
        self.controller.settings.update(channel_source="selected", channel_ids=[], channel_links="https://youtube.com/@music")
        with self.assertRaises(ValueError):
            self.controller.start("scan")
        self.controller.settings.update(channel_source="links", channel_ids=[CHANNEL], channel_links="")
        with self.assertRaises(ValueError):
            self.controller.start("scan")

    def test_changing_type_filter_keeps_scan_and_accumulates_selections(self):
        self.controller.rows = [row(visibility_type="private"), row(OTHER, visibility_type="draft", copyright="partial")]
        self.controller.select_filtered()
        self.assertTrue(self.controller.rows[0]["selected"])
        self.controller.change_settings(scope="draft", categories=["partial"])
        self.assertEqual(len(self.controller.rows), 2)
        self.controller.select_filtered()
        self.assertTrue(all(item["selected"] for item in self.controller.rows))
        self.controller.select_filtered(selected=False)
        self.assertTrue(self.controller.rows[0]["selected"])
        self.assertFalse(self.controller.rows[1]["selected"])

    def test_manual_checkbox_changes_only_visible_rows_and_rejects_disabled_rows(self):
        self.controller.rows = [row(visibility_type="private", selected=True), row(OTHER, visibility_type="private", selected=False),
                                row("Ghi123_-XYZ", visibility_type="public", selected=False)]
        self.controller.select([OTHER, "Ghi123_-XYZ"], within_ids=[OTHER, "Ghi123_-XYZ"])
        self.assertEqual([item["video_id"] for item in self.controller.rows if item["selected"]], [VIDEO, OTHER])
        self.controller.select([], within_ids=[OTHER])
        self.assertTrue(self.controller.rows[0]["selected"])
        self.assertFalse(self.controller.rows[1]["selected"])

    def test_draft_filter_does_not_permanently_skip_private_or_claimed_videos(self):
        self.controller.settings.update(scope="draft", categories=["clear"])
        self.listing.list_all_videos.return_value = ([video(), video(OTHER, copyright_check_status="COPYRIGHT_CLAIMED")], None)
        with patch("src.video_publishing_tasks.get_channels_info", return_value=[SimpleNamespace(id=CHANNEL)]):
            self.controller._scan(self.controller.settings, self.reference)
        self.assertEqual([item["status"] for item in self.controller.rows], ["scanned", "scanned"])
        self.controller.change_settings(scope="private", categories=["limited"])
        self.controller.select_filtered()
        self.assertEqual([item["video_id"] for item in self.controller.rows if item["selected"]], [OTHER])

    def test_selected_rows_are_processed_using_their_type_not_current_display_filter(self):
        self.controller.rows = [row(copyright="partial", visibility_type="private")]
        self.controller.settings.update(scope="draft", categories=["clear"])
        self.controller._process(self.controller.settings, self.reference, None, "references")
        self.module.require_eligible.assert_called_once_with(CHANNEL, VIDEO, ["partial"], publish_at=None)
        self.assertIn("reference", self.controller.rows[0])

    def test_settings_validation_does_not_partially_change_schedule(self):
        self.controller.rows = [row(thumbnail_uploaded=True)]
        with self.assertRaises(ValueError):
            self.controller.change_settings(hour="21:00")
        self.assertEqual(self.controller.settings["hour"], "18:00")
        for value in (None, 0, -1, 1.5, float("nan")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.controller.change_settings(limit=value)

    def test_reference_preview_makes_no_remote_mutations_or_image_requests(self):
        self.controller.rows = [row()]
        self.controller._process(self.controller.settings, self.reference, None, "references")
        self.assertEqual(self.controller.rows[0]["reference"]["description"], REFERENCE["description"])
        self.module.copy_metadata.assert_not_called()
        self.module.schedule.assert_not_called()
        self.image.generate.assert_not_called()

    def test_schedule_conflicts_detected_before_processing(self):
        self.controller.rows = [row(publish_at=STAMP)]
        self.listing.list_all_videos.return_value = ([video(OTHER, scheduled_publishing_details={"publishTimeSeconds": STAMP - 3600})], None)
        with self.assertRaises(ValueError):
            self.controller._check_schedule_conflicts()
        self.module.copy_metadata.assert_not_called()

    def test_reference_selection_receives_original_filename_and_current_duration(self):
        self.controller.rows = [row(old_title="Song [ZoHtnOPSE80].mp4", duration_seconds=99)]
        self.module.require_eligible.return_value = video(duration_ms=61234)
        self.controller._process(self.controller.settings, self.reference, None, "references")
        self.reference.find.assert_called_once_with("First song", source_title="Song [ZoHtnOPSE80].mp4", duration_seconds=61.234, exclude_ids=[VIDEO])
        self.assertEqual(self.controller.rows[0]["duration_seconds"], 61.234)

    def test_old_preview_is_reselected_and_image_invalidated_only_if_source_changes(self):
        self.controller.rows = [row(reference={**REFERENCE, "video_id": OTHER}, thumbnail_path="old.jpg", conversation_url="https://chatgpt.com/c/old")]
        self.controller._process(self.controller.settings, self.reference, None, "references")
        self.reference.find.assert_called_once()
        self.assertNotIn("thumbnail_path", self.controller.rows[0])
        self.assertNotIn("conversation_url", self.controller.rows[0])

    def test_same_source_keeps_generated_image_when_upgrading_preview(self):
        self.controller.rows = [row(reference=REFERENCE, thumbnail_path="keep.jpg", conversation_url="https://chatgpt.com/c/keep")]
        self.controller._process(self.controller.settings, self.reference, None, "references")
        self.assertEqual(self.controller.rows[0]["thumbnail_path"], "keep.jpg")

    def test_new_preview_is_reused_until_current_duration_changes(self):
        reference = {**REFERENCE, "selection_version": REFERENCE_SELECTION_VERSION, "selection": "duration", "target_duration_seconds": 60}
        self.controller.rows = [row(reference=reference, duration_seconds=60)]
        self.controller._process(self.controller.settings, self.reference, None, "references")
        self.reference.find.assert_not_called()
        self.module.require_eligible.return_value = video(duration_ms=61000)
        self.controller._process(self.controller.settings, self.reference, None, "references")
        self.reference.find.assert_called_once()

    def test_partially_published_rows_keep_source_across_policy_update(self):
        self.controller.rows = [row(reference=REFERENCE, metadata_copied=True)]
        self.controller._process(self.controller.settings, self.reference, None, "references")
        self.reference.find.assert_not_called()

    def test_unknown_existing_schedule_blocks_new_schedules(self):
        self.controller.rows = [row(publish_at=STAMP)]
        self.listing.list_all_videos.return_value = ([video(OTHER, scheduled_publishing_details={"unrecognizedScheduleShape": True})], None)
        with self.assertRaises(ValueError):
            self.controller._check_schedule_conflicts()
        self.module.schedule.assert_not_called()

    def test_full_worker_checkpoints_and_resumes_without_regenerating(self):
        with tempfile.TemporaryDirectory() as folder:
            self.controller.settings["output_folder"] = folder
            self.controller.rows = [row(publish_at=STAMP, publish_label="02/01/2099 18:00")]
            thumb = Path(folder) / "thumbnail.jpg"
            thumb.write_bytes(b"fake")
            self.image.generate.side_effect = lambda *args, **kw: (kw["on_conversation"]("https://chatgpt.com/c/abc-123") or "generated")
            self.module.schedule.side_effect = [ValueError("response pending"), None]
            with patch("src.video_publishing_tasks.download_reference_image", return_value="reference.jpg"), patch("src.video_publishing_tasks.normalize_thumbnail", return_value=str(thumb)):
                self.controller._worker("run", create_run_context("publishing-test"))
                self.assertEqual(self.controller.rows[0]["status"], "error")
                self.assertTrue(self.controller.rows[0]["thumbnail_uploaded"])
                saved = self.storage.load_state(STATE_KEY)
                self.assertIn("conversation_url", saved["rows"][0])
                self.controller._worker("run", create_run_context("publishing-test-resume"))
            self.assertEqual(self.controller.rows[0]["status"], "successful")
            self.assertFalse(self.controller.rows[0]["selected"])
            self.assertEqual(self.image.generate.call_count, 1)
            self.assertEqual(self.reference.find.call_count, 1)
            self.assertEqual(self.thumbnail.upload.call_count, 1)

    def test_resume_after_chatgpt_pause_reuses_valid_source_without_searching_again(self):
        reference = {**REFERENCE, "selection_version": REFERENCE_SELECTION_VERSION,
                     "selection": "first", "target_duration_seconds": 60}
        self.controller.rows = [row(status="waiting_session", reference=reference, duration_seconds=60, publish_at=STAMP,
                                    conversation_url="https://chatgpt.com/c/keep")]
        self.reference.find.side_effect = ValueError("Search temporarily unavailable")
        with tempfile.TemporaryDirectory() as folder, patch("src.video_publishing_tasks.download_reference_image", return_value="reference.jpg"), \
                patch("src.video_publishing_tasks.normalize_thumbnail", return_value="thumbnail.jpg"):
            self.controller.settings["output_folder"] = folder
            self.controller._worker("run", create_run_context("publishing-resume-source"))
        self.reference.find.assert_not_called()
        self.image.generate.assert_called_once()
        self.assertEqual(self.image.generate.call_args.kwargs["conversation_url"], "https://chatgpt.com/c/keep")
        self.assertEqual(self.controller.rows[0]["reference"], reference)
        self.assertEqual(self.controller.rows[0]["status"], "successful")
        self.module.schedule.assert_called_once()

    def test_storage_failure_stops_before_remote_mutation(self):
        self.controller.rows = [row(publish_at=STAMP)]
        self.storage.fail = True
        self.controller._worker("run", create_run_context("publishing-save-failure"))
        self.module.copy_metadata.assert_not_called()
        self.module.schedule.assert_not_called()

    def test_session_preflight_pauses_whole_batch_without_touching_later_rows(self):
        self.controller.rows = [row(publish_at=STAMP), row(OTHER, publish_at=STAMP + 86400)]
        self.image.ensure_ready.side_effect = ChatGPTSessionNeedsAction("Verify in existing window", reason="verification")
        self.controller._worker("run", create_run_context("publishing-auth-pause"))
        self.assertEqual([item["status"] for item in self.controller.rows], ["waiting_session", "scanned"])
        self.image.generate.assert_not_called()
        self.reference.find.assert_not_called()
        self.module.copy_metadata.assert_not_called()
        self.image.close.assert_not_called()
        self.assertIs(self.controller.image_session, self.image)
        self.assertFalse(self.controller.busy)

    def test_mid_generation_auth_problem_pauses_instead_of_processing_next_video(self):
        self.controller.rows = [row(publish_at=STAMP), row(OTHER, publish_at=STAMP + 86400)]
        self.image.generate.side_effect = ChatGPTSessionNeedsAction("Verify existing session", reason="verification")
        with tempfile.TemporaryDirectory() as folder, patch("src.video_publishing_tasks.download_reference_image", return_value="fake.jpg"):
            self.controller.settings["output_folder"] = folder
            self.controller._worker("run", create_run_context("publishing-auth-mid-image"))
        self.assertEqual([item["status"] for item in self.controller.rows], ["waiting_session", "scanned"])
        self.assertEqual(self.reference.find.call_count, 1)
        self.assertEqual(self.image.generate.call_count, 1)
        self.module.copy_metadata.assert_not_called()
        self.module.schedule.assert_not_called()
        self.image.close.assert_not_called()

    def test_waiting_session_stays_active_and_continues_same_video_when_ready(self):
        self.controller.rows = [row(publish_at=STAMP)]
        self.controller.busy = True
        observed = []
        def ready(**kwargs):
            self.assertTrue(kwargs["wait_for_user"])
            kwargs["on_state"]("verification", "Waiting for manual verification")
            snapshot = self.controller.snapshot()
            observed.append((snapshot["busy"], snapshot["rows"][0]["status"]))
            self.image.generate.assert_not_called()
            kwargs["on_state"]("ready", "Ready")
        self.image.ensure_ready.side_effect = ready
        with tempfile.TemporaryDirectory() as folder, patch("src.video_publishing_tasks.download_reference_image", return_value="reference.jpg"), \
                patch("src.video_publishing_tasks.normalize_thumbnail", return_value="thumbnail.jpg"):
            self.controller.settings["output_folder"] = folder
            self.controller._worker("run", create_run_context("publishing-auto-resume"))
        self.assertEqual(observed, [(True, "waiting_session")])
        self.image.generate.assert_called_once()
        self.module.schedule.assert_called_once()
        self.assertEqual(self.controller.rows[0]["status"], "successful")
        self.image.close.assert_not_called()

    def test_stop_while_waiting_marks_row_stopped_and_does_not_touch_later_videos(self):
        self.controller.rows = [row(publish_at=STAMP), row(OTHER, publish_at=STAMP + 86400)]
        self.controller.busy = True
        run = create_run_context("publishing-cancel-auth-wait")
        self.controller.run = run
        def stop(**kwargs):
            kwargs["on_state"]("verification", "Waiting")
            self.controller.stop()
            run.checkpoint()
        self.image.ensure_ready.side_effect = stop
        self.controller._worker("run", run)
        self.assertEqual([item["status"] for item in self.controller.rows], ["stopped", "scanned"])
        self.assertFalse(self.controller.busy)
        self.image.generate.assert_not_called()
        self.module.copy_metadata.assert_not_called()
        self.module.schedule.assert_not_called()
        self.image.close.assert_not_called()

    def test_same_image_session_is_reused_for_separate_preparations_and_runs(self):
        factory = Mock(return_value=self.image)
        self.controller.image_factory = factory
        self.controller.prepare_chatgpt_session()
        self.controller.prepare_chatgpt_session()
        self.controller.rows = [row(publish_at=STAMP)]
        self.image.ensure_ready.side_effect = ChatGPTSessionNeedsAction("needs login", reason="login")
        self.controller._worker("run", create_run_context("publishing-reuse-image-session"))
        factory.assert_called_once_with("session=private-secret")
        self.image.close.assert_not_called()
        self.assertIs(self.controller.image_session, self.image)

    def test_cookie_update_is_queued_on_same_session_without_saving_secret(self):
        self.controller.prepare_chatgpt_session()
        self.controller.set_cookie("session=updated-secret")
        self.image.update_cookies.assert_called_once_with("session=updated-secret")
        self.controller._save()
        self.assertNotIn("updated-secret", json.dumps(self.storage.data))
        self.assertNotIn("updated-secret", json.dumps(self.controller.snapshot()))

    def test_all_prepared_thumbnails_need_no_chatgpt_session(self):
        with tempfile.TemporaryDirectory() as folder:
            thumb = Path(folder) / "thumbnail.jpg"
            thumb.write_bytes(b"fake")
            self.controller.rows = [row(reference=REFERENCE, publish_at=STAMP, metadata_copied=True, thumbnail_uploaded=True, thumbnail_path=str(thumb))]
            self.controller._worker("run", create_run_context("publishing-existing-thumbnail"))
        self.image.ensure_ready.assert_not_called()
        self.image.generate.assert_not_called()
        self.assertEqual(self.controller.rows[0]["status"], "successful")

    def test_preparation_and_browser_close_are_blocked_during_batch(self):
        self.controller.busy = True
        with self.assertRaises(ValueError):
            self.controller.prepare_chatgpt_session()
        with self.assertRaises(ValueError):
            self.controller.close_chatgpt_session()

    def test_conversation_receipt_can_be_saved_after_stop_request(self):
        run = create_run_context("publishing-stopped-conversation-receipt")
        self.addCleanup(run.cleanup)
        self.controller.rows = [row()]
        run.request_stop()
        from src.task_runtime import bind_run_context
        with bind_run_context(run):
            self.controller._remember_conversation(self.controller.rows[0], "https://chatgpt.com/c/accepted-request")
        self.assertEqual(self.storage.load_state(STATE_KEY)["rows"][0]["conversation_url"], "https://chatgpt.com/c/accepted-request")

    def test_reload_restores_checkpoints_but_requires_new_cookie(self):
        for status in ("processing", "waiting_session"):
            with self.subTest(status=status):
                self.controller.rows = [row(status=status, publish_at=STAMP, reference=REFERENCE, thumbnail_uploaded=True)]
                self.controller._save()
                restored = VideoPublishingController(storage=self.storage)
                self.assertEqual(restored.rows[0]["status"], "stopped")
                self.assertEqual(restored.rows[0]["publish_at"], STAMP)
                self.assertTrue(restored.rows[0]["thumbnail_uploaded"])
                self.assertFalse(restored.snapshot()["has_cookie"])
                self.assertFalse(restored.busy)

    def test_query_edit_invalidates_reference_before_remote_writes(self):
        self.controller.rows = [row(reference=REFERENCE, thumbnail_path="old.jpg", conversation_url="https://chatgpt.com/c/abc")]
        self.controller.set_song(VIDEO, "New song")
        self.assertEqual(self.controller.rows[0]["song"], "New song")
        self.assertNotIn("reference", self.controller.rows[0])
        self.assertNotIn("thumbnail_path", self.controller.rows[0])
        self.controller.rows[0]["metadata_copied"] = True
        with self.assertRaises(ValueError):
            self.controller.set_song(VIDEO, "Another song")


if __name__ == "__main__":
    unittest.main()
