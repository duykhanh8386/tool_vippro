from __future__ import annotations

import unittest
from unittest.mock import patch

from src.updater import _check_latest_release


class BranchPinnedUpdaterTests(unittest.TestCase):
    def test_selects_only_release_built_from_branch_head(self):
        def fake_request(url: str):
            if "/branches/" in url:
                return {"commit": {"sha": "branch-head"}}
            return [
                {
                    "tag_name": "v999.0.0",
                    "target_commitish": "other-branch-head",
                    "draft": False,
                    "prerelease": False,
                    "assets": [{"name": "TuatVideos_Setup.exe", "browser_download_url": "https://wrong"}],
                },
                {
                    "tag_name": "v2026.9.5.4",
                    "target_commitish": "branch-head",
                    "draft": False,
                    "prerelease": False,
                    "name": "correct release",
                    "assets": [{"name": "TuatVideos_Setup.exe", "browser_download_url": "https://correct"}],
                },
            ]

        with patch("src.updater._request_github_json", side_effect=fake_request):
            result = _check_latest_release(
                "owner", "repo", "v2026.9.5.3", None, "recovered-project-only"
            )

        self.assertIsNotNone(result)
        self.assertEqual(result["version"], "2026.9.5.4")
        self.assertEqual(result["download_url"], "https://correct")
        self.assertEqual(result["commit_sha"], "branch-head")

    def test_reports_when_branch_head_installer_is_still_building(self):
        responses = [
            {"commit": {"sha": "new-head"}},
            [{"tag_name": "v1.0.0", "target_commitish": "old-head"}],
        ]
        with patch("src.updater._request_github_json", side_effect=responses):
            with self.assertRaisesRegex(RuntimeError, "new-hea"):
                _check_latest_release(
                    "owner", "repo", "v1.0.0", None, "recovered-project-only"
                )

    def test_latest_fallback_is_rewritten_to_the_pinned_release(self):
        responses = [
            {"commit": {"sha": "branch-head"}},
            [
                {
                    "tag_name": "v2.0.0",
                    "target_commitish": "branch-head",
                    "draft": False,
                    "prerelease": False,
                    "assets": [],
                }
            ],
        ]
        with patch("src.updater._request_github_json", side_effect=responses):
            result = _check_latest_release(
                "owner",
                "repo",
                "v1.0.0",
                "https://github.com/owner/repo/releases/latest/download/TuatVideos_Setup.exe",
                "recovered-project-only",
            )

        self.assertEqual(
            result["download_url"],
            "https://github.com/owner/repo/releases/download/v2.0.0/TuatVideos_Setup.exe",
        )


if __name__ == "__main__":
    unittest.main()
