# RECOVERED: depyo output corrected from CPython 3.12 disassembly
import json
from abc import ABC
import requests
from loguru import logger
from src.module.model import ChannelInfo, Video, VideoType
from src.utils import get_channels_info
from src.task_runtime import post_with_stop
class IModule(ABC):
    EATS = "AXAuXyagZ24uKnNz0kYZbLTt32KGDRxhKqK2ns7At7Rkxw4UXW19g-oH1ng4py8No7EiqwNid9eQAFhJ7_8XJFiitSaWQdlXlG7nmJStO8tVWrrAAQ=="; CLIENT_SCREEN_NONCE = "8Z1g2AhnbTXfVuBp"; CHALLENGE = "a=6&a2=3&b=UAAoAmaAwwDIrKcvn9_rgzH-Jr4&c=1746756602&d=62&e3=UCAICychz3FdwEAyD6Rv-IRQ&c1a=1&hh=PSyUV3k8pO-Z9_6qmFQtKyKipjuIekgJtEtZvvmqpn0"; BOT_GUARD_RESPONSE = "$euU55b1RAAbvRbg0z0XewMv_S0uMtXGnADQBEArZ1HMQG4pgLXVbdPcdDixwJ1GZIjKtUDtG9tZmNJbg9W0ElVuifwYo-lT9CfcGMbryngAAACzOAAAA8fQBB-IASY3N5JAhIeAY5HKAdoI0yEECI_IJZ-vRui2z4nzlEoLB50R2iz607ou69KS463F-Ncivzmqmrurv2jJXSyl-d0TbLu7WaW-WEbsFBG4ZglwEBE_ccLro1tMinuYe2g0-E842CWJroVmf6sc716sKgXbH8XKn5WXsRjXqeuVHSZ8g-ds5FQLBMCLVRU7zVhpijepG729n8mztRnv3IuDL4sWycDhphf0IyIxPhQ_vVeuwX9En5nue0pZjeNetiMIFmI1acJDq474vIS9dU6XDknDze6gN0QbjXWrsYMYyO1zj5sMiLShfljFfCp7dp2f0LHOmAPGJdklHWgMXIYOmZW2wDi5FmcZBK12hx4YUrtMxXtXv1l6BJftZCzR0apgb5kDcR56jtHzxQCGp4kaNPV5SLO4oUV7vlkUCL2yc_a9seNhRnDeIM3ToQYRv7M1nQpPDfeiFaP4-X3WtlvdNFit_0UQV8BYImVdnnTdulniHz2roAg3PoMhtLT0QFUE5UfE6gupz1A35kHrb9UAqMtAgC0JSEI9Hn2m64wviQH5YyOoYlxNIGYz7vFGDqXX_yquJ57zosGcmgGwPulJjh_cUOBXjnwGRFAgTdvHkaIcwQNmWdJUWT4yxhy7-9AsLAravJUjygijZfajXrVEd9Dhv2GvyKSDGO_8WCunYImbXNy6bjfdO31HD9B0Bb9Yaqsyq3TFlUy1giqhdDJKRVZ2fQpjIKApaXITB-uLJQfleS6VVCKeMfwrtty056wlNQVuWuaQ8-XqDgOJclKHt8wOEMSEBEpwVc5ocBjEZ-wBLiorr7G1q66Ulp-HF4_Iwh7xUULUhH1M5FupXG93XQY9AR1M-MWeqQ07AIJ7FKGthd0wLuTavQ-1xQrymxWULSIuyaC7hpQxf1cIVh7EE2YrOhKVBowEe1LnFCUgCGXPBOd9TrQnkGLyKcYAOwzWdII7Zl5RPfHmPLUyk-niJ1Ygey4Dhmxzv9g8udrOvGr9mZDtIjKr-1z1cl-W2lDXWuRjfiRYNgOhPQOCXq21ULvlEOtR-9C2EVIABVXd14rGtJzsuXUwnr6CD29Odm64nbRPCa3leXuz1pOR1QOi0984sblJ0B_lRIGiXVd4RoUewatihEyzSGg2MFV1k2CdYrxK_yfv0hCHWc-JmixNmWFjXp7PrQvD3NMWZlb5Wb9J1mgl6nnxT7gPGo07xvYpiRBRwA6HU7QFcnP7yYsekWGXte5Sk3QJsu2m1lWpp-R9jiqpfw6Qf8zjwDVgbjXaq7pkrCyJIZeiBgDEWow2IbKa0GlRPuvmxLj3QToOjqCCqCXAtRiYGJzeyH0dd6HdIaJckCHYE1KiWp1SifXILE9TwQs2izR55MteVSZ_D9k3n0GBNnJXhUv5LREKWCFo5i0IgFMIFUEYA9uAaA_KPIxbfNYwy5VL6GvHFctg8RdHvZb6-ZYpieMTnkT2srMF20Yh148zsAIoZ3Z6J6upgwljNeHqOUXYVtIORaPUt7Sq54x67YZ7eVKU1-eA-qpqqAJ9jfTXjalxYRe2RbScWuluGr7lfL4vT5CL_ySttj-4doOtBJgVW4YRkhKjicZpBZg_uZizhgzB3Q7Q"
    pass

    def _list_videos(self, channel_id: str, video_type: VideoType, limit: int=50) -> list[Video]:
        channel_info = get_channels_info(channel_id); cookie_string = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in channel_info.cookies]); sapisidhash = channel_info.sapisidhash; session_token = self._get_session_token(channel_info)

        payload = {"filter": {"and": {"operands": [{"channelIdIs": {"value": channel_info.id}},
    {"and": {"operands": [{"or": {"operands": [{"and": {"operands": [{"privacyIs": {"value": video_type.value}},
    {"not": {"operand": {"isDraft": {}}}},
    {"not": {"operand": {"isScheduledToBePublic": {}}}}]}}]}},
    {"and": {"operands": [{"videoOriginIs": {"value": "VIDEO_ORIGIN_UPLOAD"}},
    {"not": {"operand": {"contentTypeIs": {"value": "CREATOR_CONTENT_TYPE_SHORTS"}}}}]}},
    {"not": {"operand": {"tvfilmTypeIs": {"value": "VIDEO_TVFILM_TYPE_MOVIE"}}}},
    {"not": {"operand": {"tvfilmTypeIs": {"value": "VIDEO_TVFILM_TYPE_EPISODE"}}}},
    {"not": {"operand": {"tvfilmTypeIs": {"value": "VIDEO_TVFILM_TYPE_EVENT"}}}}]}}]}}, "order": "VIDEO_ORDER_DISPLAY_TIME_DESC", "pageSize": limit, "mask": {"channelId": True,

    "videoId": True, "lengthSeconds": True, "livestream": {"all": True},

    "publicLivestream": {"all": True}, "origin": True, "premiere": {"all": True},

    "publicPremiere": {"all": True}, "status": True, "thumbnailDetails": {"all": True}, "title": True, "draftStatus": True, "downloadUrl": True, "watchUrl": True, "shareUrl": True, "permissions": {"all": True}, "features": {"all": True}, "collaboration": {"all": True}, "timeCreatedSeconds": True, "timePublishedSeconds": True, "privacy": True, "contentOwnershipModelSettings": {"all": True}, "contentType": True, "publicShorts": {"all": True},

    "podcastRssMetadata": {"all": True}, "videoLinkageShortsAttribution": {"all": True}, "alteredContentSettings": {"all": True}, "tvfilmMetadata": {"all": True}, "videoCreatorExperiment": {"all": True}, "responseStatus": {"all": True}, "statusDetails": {"all": True}, "description": True, "titleFormattedString": {"all": True}, "descriptionDetails": {"all": True}, "descriptionFormattedString": {"all": True}, "titleDetails": {"all": True}, "videoDurationMs": True, "publicMetrics": {"all": True}, "audienceRestriction": {"all": True}, "releaseInfo": {"all": True}, "privateMetrics": {"dislikeCount": True}, "allRestrictions": {"all": True}, "inlineEditProcessingStatus": True, "videoPrechecks": {"all": True}, "shorts": {"all": True}, "selfCertification": {"all": True}, "videoStreamUrl": True,

    "thumbnailEditorState": {"all": True}, "videoResolutions": {"all": True}, "scheduledPublishingDetails": {"all": True},

    "visibility": {"all": True},
    "privateShare": {"all": True}, "sponsorsOnly": {"all": True}, "unlistedExpired": True, "videoTrailers": {"all": True}, "remix": {"isSource": True}, "isPaygated": True}, "context": {"client": {"clientName": 62, "clientVersion": "1.20250910.04.01", "hl": "vi", "gl": "VN", "experimentsToken": "", "utcOffsetMinutes": 420, "userInterfaceTheme": "USER_INTERFACE_THEME_DARK", "screenWidthPoints": 2560, "screenHeightPoints": 578, "screenPixelDensity": 2, "screenDensityFloat": 1.5}, "request": {"returnLogEntry": True, "internalExperimentFlags": [], "eats": "AQH2GtwBdPiAGJ2T8rGKWNAiZQVd_vf3vyyp2_FoLHT9dGCNih8CNaBwmazsAHXcXYwinRh-c35GmB1fvnAapWD1jXwQpZnFLpu81NzfUTeuNdFMKSTZfCxbEJYI", "sessionInfo": {"token": session_token}, "consistencyTokenJars": []}, "user": {"onBehalfOfUser": channel_info.delegated_session_id, "delegationContext": {"externalChannelId": channel_info.id, "roleType": {"channelRoleType": channel_info.role}}, "serializedDelegationContext": ""}, "clickTracking": {"visualElement": {"veType": 31_402}}, "clientScreenNonce": "qplwEzmZ-f8Ac7kX"}}; headers = {"origin": "https://studio.youtube.com", "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36", "cookie": cookie_string, "content-type": "application/json", "authorization": f"SAPISIDHASH {sapisidhash}"}; url = "https://studio.youtube.com/youtubei/v1/creator/list_creator_videos?alt=json"; response = post_with_stop(url=url, headers=headers, json=payload)

        res = response.json(); videos = []
        for item in res.get("videos", []):
            video = Video(id=item["videoId"], title=item["title"], description=item["description"], channel_id=item["channelId"], duration_ms=item["videoDurationMs"], thumbnail=item["thumbnailDetails"]["thumbnails"][0]["url"])
            videos.append(video)
        return videos

        cookie = None
    def _get_video_info(self, video_id: str, channel_id: str) -> Video:
        channel_info = get_channels_info(channel_id); cookie_string = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in channel_info.cookies]); sapisidhash = channel_info.sapisidhash; session_token = self._get_session_token(channel_info); url = "https://studio.youtube.com/youtubei/v1/creator/get_creator_videos?alt=json"; headers = {"origin": "https://studio.youtube.com", "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36", "cookie": cookie_string, "content-type": "application/json", "authorization": f"SAPISIDHASH {sapisidhash}"}

        payload = {"context": {"client": {"clientName": 62, "clientVersion": "1.20250905.02.00", "hl": "vi", "gl": "VN", "experimentsToken": "", "utcOffsetMinutes": 420, "userInterfaceTheme": "USER_INTERFACE_THEME_DARK", "screenWidthPoints": 2560, "screenHeightPoints": 544, "screenPixelDensity": 2, "screenDensityFloat": 1.5}, "request": {"returnLogEntry": True, "internalExperimentFlags": [], "eats": "AWSNWa2q-ubSn35ywNe6Myhvveym5w_4-S_D3p_lk689PZciFEJrTquCWvtc1PgiFObkpeU638J5M3CTcvCmegVUfkseMdAJaVgmOWE_S5SHQpzuXaZu1I7szwPPUQ==", "sessionInfo": {"token": session_token}, "consistencyTokenJars": []}, "user": {"onBehalfOfUser": channel_info.delegated_session_id, "delegationContext": {"externalChannelId": channel_info.id, "roleType": {"channelRoleType": channel_info.role}}, "serializedDelegationContext": ""}, "clickTracking": {"visualElement": {"veType": 74_615}}, "clientScreenNonce": "rQg33g-jDrOyosOi"}, "failOnError": True, "videoIds": [video_id], "mask": {"channelId": True, "downloadUrl": True, "origin": True, "premiere": {"all": True},

    "privacy": True, "videoId": True, "title": True, "titleDetails": {"all": True},

    "description": True, "descriptionDetails": {"all": True}, "releaseInfo": {"all": True},

    "podcastRssMetadata": {"all": True}, "status": True, "permissions": {"all": True}, "draftStatus": True, "features": {"all": True}, "livestream": {"all": True}, "videoDurationMs": True, "statusDetails": {"all": True}, "inlineEditProcessingStatus": True, "monetization": {"all": True}, "allRestrictions": {"all": True}, "videoPrechecks": {"all": True}, "audienceRestriction": {"all": True}, "mfkSettings": {"all": True}, "selfCertification": {"all": True},

    "videoStreamUrl": True, "visibility": {"all": True}, "shorts": {"all": True}, "responseStatus": {"all": True}, "contentType": True, "videoAdvertiserSpecificAgeGates": {"all": True}, "claimDetails": {"all": True}, "commentsDisabledInternally": True, "music": {"all": True}, "ownedClaimDetails": {"all": True}, "timePublishedSeconds": True, "uncaptionedReason": True, "remix": {"all": True}, "contentOwnershipModelSettings": {"all": True}, "googleAdsVideoLinks": {"all": True}, "dubSettings": {"all": True}, "alteredContentSettings": {"all": True}, "collaboration": {"all": True}, "thumbnailEditorState": {"all": True}, "thumbnailDetails": {"all": True}, "videoCreatorExperiment": {"all": True}, "lengthSeconds": True, "publicLivestream": {"all": True}, "publicPremiere": {"all": True},

    "tvfilmMetadata": {"all": True}, "shareUrl": True,

    "scheduledPublishingDetails": {"all": True},

    "privateShare": {"all": True},

    "sponsorsOnly": {"all": True}, "unlistedExpired": True, "videoTrailers": {"all": True}, "isPaygated": True, "suggestions": {"all": True}, "tvType": {"all": True}, "genres": {"all": True},

    "episode": {"all": True}, "copyrightSummary": {"all": True}, "productSelection": {"all": True}, "productAutotaggingSettings": {"all": True}, "videoLinkageShortsAttribution": {"all": True}, "allowEmbed": True, "allowRatings": True, "ageRestriction": True, "audioLanguage": {"all": True}, "category": True, "commentFilter": True, "commentSettings": {"all": True}, "crowdsourcingEnabled": True, "dateRecorded": {"all": True}, "defaultCommentSortOrder": True, "descriptionFormattedString": {"all": True}, "gameTitle": {"all": True}, "license": True, "liveChat": {"all": True}, "location": {"all": True}, "metadataLanguage": {"all": True}, "paidProductPlacement": True, "paidPoliticalContent": {"all": True}, "publishing": {"all": True}, "tags": {"all": True},

    "titleFormattedString": {"all": True}, "viewCountIsHidden": True, "autoChapterSettings": {"all": True}, "autoPlacesMentionedSettings": {"all": True}, "videoArtworkEditorState": {"all": True}, "learningConceptSettings": {"all": True}, "videoEditorProject": {"all": True}, "originalFilename": True, "timeCreatedSeconds": True,

    "videoResolutions": {"all": True}, "watchUrl": True, "publicShorts": {"all": True}, "publicMetrics": {"all": True}, "academicLearning": {"all": True}, "manualPlacesMentionedPlaces": {"all": True}, "autoProductsSettings": {"all": True},
    "videoAutoSummarySettings": {"all": True}, "issues": {"all": True}}, "criticalRead": False}; response = post_with_stop(url=url, headers=headers, json=payload); res = response.json()
        return Video(id=res["videos"][0].get("videoId", ""), title=res["videos"][0].get("title", ""), description=res["videos"][0].get("description", ""), channel_id=res["videos"][0].get("channelId", ""), duration_ms=res["videos"][0].get("videoDurationMs", 0), thumbnail=res["videos"][0].get("thumbnailDetails", {}).get("thumbnails", [{}])[0].get("url", ""), video_status=res["videos"][0].get("status", ""))

        cookie = None
    def _build_context(self, channel_id: str, role: str, delegated_session_id: str, *, client_version: str="1.20260311.03.00", hl: str="en", theme: str="USER_INTERFACE_THEME_DARK", screen_width: int=1920, screen_height: int=945, include_on_behalf_of_user: bool=True, extra_request_fields: dict | None=None) -> dict:
        """Build the standard YouTube Studio API context payload."""
        user_block = {"delegationContext": {"externalChannelId": channel_id, "roleType": {"channelRoleType": role}}, "serializedDelegationContext": ""}
        if include_on_behalf_of_user:
            user_block["onBehalfOfUser"] = delegated_session_id
        request_block = {"returnLogEntry": True, "internalExperimentFlags": [], "eats": self.EATS, "consistencyTokenJars": []}
        if extra_request_fields:
            request_block.update(extra_request_fields)
        return {"client": {"clientName": 62, "clientVersion": client_version, "hl": hl, "gl": "VN", "experimentsToken": "", "utcOffsetMinutes": 420, "userInterfaceTheme": theme, "screenWidthPoints": screen_width, "screenHeightPoints": screen_height, "screenPixelDensity": 1, "screenDensityFloat": 1}, "request": request_block, "user": user_block, "clickTracking": {"visualElement": {"veType": 74_618}}, "clientScreenNonce": self.CLIENT_SCREEN_NONCE}
    def _get_session_token(self, channel_info) -> str:
        """
        Obtain a YouTube Studio session token for the given channel.

        Args:
            channel_info: A ChannelInfo dataclass instance (from src.utils).

        Returns:
            The session token string.

        Raises:
            Exception: If YouTube has changed its auth algorithm.
        """
        channel_id = channel_info.id; role = channel_info.role; delegated_session_id = channel_info.delegated_session_id; challenge = channel_info.challenge; bot_guard_response = channel_info.botguardResponse; cookie_string = channel_info.cookie_string(); sapisidhash = channel_info.sapisidhash; user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"; headers = {"origin": "https://studio.youtube.com", "user-agent": user_agent, "cookie": cookie_string, "content-type": "application/json", "authorization": f"SAPISIDHASH {sapisidhash}"}; res = post_with_stop(url="https://studio.youtube.com/youtubei/v1/att/esr?alt=json", headers=headers, json={"context": self._build_context(channel_id, role, delegated_session_id), "challenge": challenge, "botguardResponse": bot_guard_response, "xguardClientStatus": 0}).json()
        if "ctx" not in res:
            raise Exception("Youtube thay đổi thuật toán. Vui lòng lấy lại thông tin kênh. Nếu sau đó vẫn lỗi, hãy liên hệ admin!!!")
        ivctx = res["ctx"]

        res = post_with_stop(url="https://studio.youtube.com/youtubei/v1/security/get_web_reauth_url?alt=json", headers=headers, json={"context": self._build_context(channel_id, role, delegated_session_id), "continueUrl": "https://studio.youtube.com/reauth", "flow": "REAUTH_FLOW_YT_STUDIO_COLD_LOAD", "ivctx": ivctx, "challenge": challenge, "botguardResponse": bot_guard_response}).json()
        if "encodedReauthProofToken" not in res:
            logger.warning("Missing encodedReauthProofToken for channel {}, refreshing challenge...", channel_id)
            from src.channel_refresh import refresh_challenge_and_botguard
            from src.utils import get_channels_info
            refresh_challenge_and_botguard(channel_id)
            channel_info = get_channels_info(channel_id)
            challenge = channel_info.challenge
            bot_guard_response = channel_info.botguardResponse
            cookie_string = channel_info.cookie_string()
            sapisidhash = channel_info.sapisidhash
            delegated_session_id = channel_info.delegated_session_id
            headers["cookie"] = cookie_string
            headers["authorization"] = f"SAPISIDHASH {sapisidhash}"
            res = post_with_stop(url="https://studio.youtube.com/youtubei/v1/att/esr?alt=json", headers=headers, json={"context": self._build_context(channel_id, role, delegated_session_id), "challenge": challenge, "botguardResponse": bot_guard_response, "xguardClientStatus": 0}).json()
            if "ctx" not in res:
                raise Exception("Youtube thay đổi thuật toán. Vui lòng lấy lại thông tin kênh. Nếu sau đó vẫn lỗi, hãy liên hệ admin!!!")
            ivctx = res["ctx"]
            res = post_with_stop(url="https://studio.youtube.com/youtubei/v1/security/get_web_reauth_url?alt=json", headers=headers, json={"context": self._build_context(channel_id, role, delegated_session_id), "continueUrl": "https://studio.youtube.com/reauth", "flow": "REAUTH_FLOW_YT_STUDIO_COLD_LOAD", "ivctx": ivctx, "challenge": challenge, "botguardResponse": bot_guard_response}).json()
            if "encodedReauthProofToken" not in res:
                raise Exception("Retry failed: encodedReauthProofToken vẫn không có sau khi refresh challenge. Vui lòng lấy lại thông tin kênh hoặc liên hệ admin!")
            logger.info("Retry successful after refreshing challenge for {}", channel_id)
        encoded_reauth_proof_token = res["encodedReauthProofToken"]; session_risk_ctx = res["sessionRiskCtx"]

        res = post_with_stop(url="https://studio.youtube.com/youtubei/v1/ars/grst?alt=json", headers=headers, json={"context": self._build_context(channel_id, "CREATOR_CHANNEL_ROLE_TYPE_OWNER", delegated_session_id, client_version="1.20241125.01.00", hl="vi", theme="USER_INTERFACE_THEME_LIGHT", screen_width=1847, screen_height=285, include_on_behalf_of_user=False, extra_request_fields={"reauthRequestInfo": {"encodedReauthProofToken": encoded_reauth_proof_token}}), "ctx": session_risk_ctx}).json()
        return res["sessionToken"]
