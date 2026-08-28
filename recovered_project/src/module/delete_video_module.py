# RECOVERED: reconstructed from CPython 3.12 bytecode
import requests
from loguru import logger

from src.module.base import IModule
from src.utils import get_channels_info
from src.task_runtime import check_stopped, post_with_stop


class DeleteVideoModule(IModule):
    def delete(self, video_id: str, channel_id: str) -> int:
        """
        Permanently delete a single video from YouTube Studio.

        Args:
            video_id:   The YouTube video ID to delete.
            channel_id: The channel that owns the video.

        Returns:
            HTTP status code (200 = success).
        """
        check_stopped()
        channel_info = get_channels_info(channel_id)
        if channel_info is None:
            raise ValueError(f"Channel '{channel_id}' not found in database")
        cookie_string = channel_info.cookie_string()
        session_token = self._get_session_token(channel_info)

        url = "https://studio.youtube.com/youtubei/v1/video/delete"
        headers = {
            "accept": "*/*",
            "authorization": f"SAPISIDHASH {channel_info.sapisidhash}",
            "content-type": "application/json",
            "cookie": cookie_string,
            "origin": "https://studio.youtube.com",
            "referer": f"https://studio.youtube.com/channel/{channel_info.id}/videos",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
            "x-goog-authuser": "0",
            "x-youtube-client-name": "62",
            "x-youtube-client-version": "1.20260520.00.00",
            "x-origin": "https://studio.youtube.com",
        }
        payload = {
            "context": {
                "client": {
                    "clientName": 62,
                    "clientVersion": "1.20260520.00.00",
                    "hl": "vi",
                    "gl": "VN",
                    "experimentsToken": "",
                    "utcOffsetMinutes": 420,
                    "userInterfaceTheme": "USER_INTERFACE_THEME_DARK",
                    "screenWidthPoints": 1920,
                    "screenHeightPoints": 484,
                    "screenPixelDensity": 1,
                    "screenDensityFloat": 1,
                },
                "request": {
                    "returnLogEntry": True,
                    "internalExperimentFlags": [],
                    "eats": self.EATS,
                    "sessionInfo": {"token": session_token},
                    "consistencyTokenJars": [],
                },
                "user": {
                    "onBehalfOfUser": channel_info.delegated_session_id,
                    "delegationContext": {
                        "externalChannelId": channel_info.id,
                        "roleType": {"channelRoleType": channel_info.role},
                    },
                    "serializedDelegationContext": "",
                },
                "clickTracking": {"visualElement": {"veType": 31_402}},
                "clientScreenNonce": self.CLIENT_SCREEN_NONCE,
            },
            "videoId": video_id,
        }

        response = post_with_stop(
            url, headers=headers, json=payload, params={"alt": "json"}
        )
        logger.info(f"Delete video {video_id} response: {response.status_code}")
        if response.status_code != 200:
            logger.error(
                f"Failed to delete video {video_id}: HTTP {response.status_code} — {response.text[:200]}"
            )
            return response.status_code

        try:
            body = response.json()
        except ValueError:
            logger.error(
                f"Failed to delete video {video_id}: phản hồi không phải JSON — {response.text[:200]}"
            )
            return 0

        if body.get("success") is False:
            logger.error(
                f'Failed to delete video {video_id}: server trả về "success": false — {response.text[:200]}'
            )
            return 0
        return response.status_code


delete_video_module = DeleteVideoModule()
