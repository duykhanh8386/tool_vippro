# RECOVERED: reconstructed from CPython 3.12 bytecode
import requests
from loguru import logger
from src.module.base import IModule
from src.module.model import Video, VideoType
from src.utils import get_channels_info
from src.task_runtime import check_stopped, post_with_stop
class ListVideosModule(IModule):
    """Public wrapper around IModule._list_videos for use in UI pages."""
    pass

    def list_videos(self, channel_id: str, video_type: VideoType, limit: int=50) -> list[Video]:
        """
        Fetch videos from a channel filtered by privacy type.

        Args:
            channel_id: The YouTube channel ID.
            video_type: VideoType.PRIVATE | PUBLIC | UNLISTED.
            limit:      Maximum number of videos to return (default 50, max 500).

        Returns:
            List of Video dataclass instances.
        """
        return self._list_videos(channel_id, video_type, limit)

    pass
    pass

    def list_all_videos(self, channel_id: str, limit: int=50, page_token: str | None=None) -> tuple[list[Video], str | None]:
        """
        Fetch all uploaded videos for a channel regardless of privacy type.

        Uses a broader filter that omits any privacyIs constraint, returning
        private, public, and unlisted videos together.

        Args:
            channel_id:  The YouTube channel ID.
            limit:       Maximum number of videos per page (default 50, max 500).
            page_token:  Continuation token from a previous call for pagination.

        Returns:
            (videos, next_page_token) — next_page_token is None on the last page.
        """
        check_stopped()
        channel_info = get_channels_info(channel_id)
        if channel_info is None:
            raise ValueError(f"Channel '{channel_id}' not found in database")
        cookie_string = channel_info.cookie_string()
        sapisidhash = channel_info.sapisidhash
        session_token = self._get_session_token(channel_info)
        payload = {"filter": {"and": {"operands": [{"channelIdIs": {"value": channel_info.id}},
    {"and": {"operands": [{"videoOriginIs": {"value": "VIDEO_ORIGIN_UPLOAD"}},
    {"not": {"operand": {"contentTypeIs": {"value": "CREATOR_CONTENT_TYPE_SHORTS"}}}}]}},
    {"not": {"operand": {"tvfilmTypeIs": {"value": "VIDEO_TVFILM_TYPE_MOVIE"}}}},
    {"not": {"operand": {"tvfilmTypeIs": {"value": "VIDEO_TVFILM_TYPE_EPISODE"}}}},
    {"not": {"operand": {"tvfilmTypeIs": {"value": "VIDEO_TVFILM_TYPE_EVENT"}}}}]}}, "order": "VIDEO_ORDER_DISPLAY_TIME_DESC", "pageSize": limit, "mask": {"channelId": True, "videoId": True, "lengthSeconds": True, "livestream": {"all": True}, "publicLivestream": {"all": True}, "origin": True, "premiere": {"all": True}, "publicPremiere": {"all": True}, "status": True, "thumbnailDetails": {"all": True}, "title": True,
    "draftStatus": True, "downloadUrl": True, "watchUrl": True, "shareUrl": True, "permissions": {"all": True}, "features": {"all": True},
    "collaboration": {"all": True}, "timeCreatedSeconds": True, "timePublishedSeconds": True,
    "privacy": True, "contentOwnershipModelSettings": {"all": True}, "contentType": True,
    "publicShorts": {"all": True}, "podcastRssMetadata": {"all": True}, "videoLinkageShortsAttribution": {"all": True}, "alteredContentSettings": {"all": True}, "superfansOnly": {"all": True}, "tvfilmMetadata": {"all": True}, "videoCreatorExperiment": {"all": True}, "responseStatus": {"all": True}, "statusDetails": {"all": True}, "description": True, "titleFormattedString": {"all": True}, "descriptionDetails": {"all": True}, "descriptionFormattedString": {"all": True}, "titleDetails": {"all": True},
    "videoDurationMs": True, "publicMetrics": {"all": True}, "audienceRestriction": {"all": True}, "releaseInfo": {"all": True}, "privateMetrics": {"dislikeCount": True}, "monetization": {"all": True}, "selfCertification": {"all": True}, "allRestrictions": {"all": True}, "mfkSettings": {"all": True}, "inlineEditProcessingStatus": True, "videoPrechecks": {"all": True}, "videoStreamUrl": True, "thumbnailEditorState": {"all": True}, "videoResolutions": {"all": True},
    "shorts": {"all": True}, "scheduledPublishingDetails": {"all": True}, "visibility": {"all": True}, "privateShare": {"all": True}, "sponsorsOnly": {"all": True}, "unlistedExpired": True, "videoTrailers": {"all": True}, "remix": {"isSource": True}, "isPaygated": True}, "context": {"client": {"clientName": 62, "clientVersion": "1.20260520.00.00", "hl": "vi", "gl": "VN", "experimentsToken": "", "utcOffsetMinutes": 420, "userInterfaceTheme": "USER_INTERFACE_THEME_DARK", "screenWidthPoints": 1920, "screenHeightPoints": 150, "screenPixelDensity": 1, "screenDensityFloat": 1}, "request": {"returnLogEntry": True, "internalExperimentFlags": [], "eats": self.EATS, "sessionInfo": {"token": session_token}, "consistencyTokenJars": []}, "user": {"onBehalfOfUser": channel_info.delegated_session_id, "delegationContext": {"externalChannelId": channel_info.id, "roleType": {"channelRoleType": channel_info.role}}, "serializedDelegationContext": ""}, "clickTracking": {"visualElement": {"veType": 31_402}}, "clientScreenNonce": self.CLIENT_SCREEN_NONCE}}
        headers = {"origin": "https://studio.youtube.com", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36", "cookie": cookie_string, "content-type": "application/json", "authorization": f"SAPISIDHASH {sapisidhash}"}
        if page_token:
            payload["pageToken"] = page_token
        url = "https://studio.youtube.com/youtubei/v1/creator/list_creator_videos?alt=json"
        response = post_with_stop(url, headers=headers, json=payload)
        res = response.json()
        next_page_token = res.get("nextPageToken") or None
        videos = []
        for item in res.get("videos", []):
            try:
                prechecks = item.get("videoPrechecks", {})
                monetized = prechecks.get("videoUploadChecksMonetized", {})
                copyright_status = monetized.get("copyrightCheck", {}).get("checkStatus", "")
                if not copyright_status:
                    not_mon = prechecks.get("videoUploadChecksNotMonetized", {})
                    copyright_status = not_mon.get("copyrightCheck", {}).get("checkStatus", "")
                videos.append(Video(id=item.get("videoId", ""), title=item.get("title", ""), description=item.get("description", ""), channel_id=item.get("channelId", ""), duration_ms=item.get("videoDurationMs", 0), thumbnail=item.get("thumbnailDetails", {}).get("thumbnails", [{}])[0].get("url", ""), privacy=item.get("privacy", ""), video_status=item.get("status", ""), copyright_check_status=copyright_status))
            except Exception as exc:
                logger.warning(f"Skipping malformed video entry: {exc}")
        return videos, next_page_token

    def get_copyright_statuses(self, channel_id: str, video_ids: set[str]) -> dict[str, str]:
        """
        Return {video_id: copyright_check_status} for the given video IDs.
        Scans pages newest-first and stops once every requested ID is found.

        Args:
            channel_id: The YouTube channel ID.
            video_ids:  Set of video IDs to look up.

        Returns:
            Dict mapping each found video ID to its current copyright check status.
        """
        remaining = set(video_ids)
        result = {}
        page_token = None
        while remaining:
            check_stopped()
            videos, next_token = self.list_all_videos(channel_id, 50, page_token)
            for v in videos:
                if v.id in remaining:
                    result[v.id] = v.copyright_check_status
                    remaining.discard(v.id)
            if not next_token or not remaining:
                break
            page_token = next_token
        return result


list_videos_module = ListVideosModule()
