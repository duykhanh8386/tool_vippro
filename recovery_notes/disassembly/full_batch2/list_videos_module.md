# Static CPython 3.12 disassembly — `list_videos_module.pyc`

Generated with `xdis 6.3.0`; the code object was deserialized but never executed.

```text
# pydisasm version 6.3.0
# CPython Python bytecode 3.12.0 (3531)
#   Disassembled from CPython Python 3.13.13 | packaged by Anaconda, Inc. | (main, Apr 14 2026, 06:12:50) [MSC v.1942 64 bit (AMD64)]
# Timestamp in code: 0 (1970-01-01 07:00:00)
# Source code size mod 2**32: 0 bytes
# Method Name:       <module>
# Filename:          src\module\list_videos_module.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        5
# Flags:             0x00000000 (0x0)
# First Line:        1
# Constants:
#    0: 0
#    1: None
#    2: ('logger',)
#    3: ('IModule',)
#    4: ('Video', 'VideoType')
#    5: ('get_channels_info',)
#    6: <Code311 code object ListVideosModule at 0x2e505863ac0, file src\module\list_videos_module.py>, line 9
#    7: 'ListVideosModule'
# Names:
#    0: requests
#    1: loguru
#    2: logger
#    3: src.module.base
#    4: IModule
#    5: src.module.model
#    6: Video
#    7: VideoType
#    8: src.utils
#    9: get_channels_info
#   10: ListVideosModule
#   11: list_videos_module

  0:           0 RESUME               0

  1:           2 LOAD_CONST           (0)
               4 LOAD_CONST           (None)
               6 IMPORT_NAME          (requests)
               8 STORE_NAME           (requests)

  2:          10 LOAD_CONST           (0)
              12 LOAD_CONST           (('logger',))
              14 IMPORT_NAME          (loguru)
              16 IMPORT_FROM          (logger)
              18 STORE_NAME           (logger)
              20 POP_TOP

  4:          22 LOAD_CONST           (0)
              24 LOAD_CONST           (('IModule',))
              26 IMPORT_NAME          (src.module.base)
              28 IMPORT_FROM          (IModule)
              30 STORE_NAME           (IModule)
              32 POP_TOP

  5:          34 LOAD_CONST           (0)
              36 LOAD_CONST           (('Video', 'VideoType'))
              38 IMPORT_NAME          (src.module.model)
              40 IMPORT_FROM          (Video)
              42 STORE_NAME           (Video)
              44 IMPORT_FROM          (VideoType)
              46 STORE_NAME           (VideoType)
              48 POP_TOP

  6:          50 LOAD_CONST           (0)
              52 LOAD_CONST           (('get_channels_info',))
              54 IMPORT_NAME          (src.utils)
              56 IMPORT_FROM          (get_channels_info)
              58 STORE_NAME           (get_channels_info)
              60 POP_TOP

  9:          62 PUSH_NULL
              64 LOAD_BUILD_CLASS
              66 LOAD_CONST           (<Code311 code object ListVideosModule at 0x2e505863ac0, file src\module\list_videos_module.py>, line 9)
              68 MAKE_FUNCTION        (No arguments)
              70 LOAD_CONST           ("ListVideosModule")
              72 LOAD_NAME            (IModule)
              74 CALL                 3
              82 STORE_NAME           (ListVideosModule)

290:          84 PUSH_NULL
              86 LOAD_NAME            (ListVideosModule)
              88 CALL                 0
              96 STORE_NAME           (list_videos_module)
              98 RETURN_CONST         (None)


# Method Name:       ListVideosModule
# Filename:          src\module\list_videos_module.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        12
# Flags:             0x00000000 (0x0)
# First Line:        9
# Constants:
#    0: 'ListVideosModule'
#    1: 'Public wrapper around IModule._list_videos for use in UI pages.'
#    2: 'channel_id'
#    3: 'video_type'
#    4: 'limit'
#    5: 'return'
#    6: <Code311 code object list_videos at 0x2e505863570, file src\module\list_videos_module.py>, line 12
#    7: None
#    8: 'page_token'
#    9: <Code311 code object list_all_videos at 0x2e5058639b0, file src\module\list_videos_module.py>, line 31
#   10: 'video_ids'
#   11: <Code311 code object get_copyright_statuses at 0x2e5058638a0, file src\module\list_videos_module.py>, line 257
#   12: (50,)
#   13: (50, None)
# Names:
#    0: __name__
#    1: __module__
#    2: __qualname__
#    3: __doc__
#    4: str
#    5: VideoType
#    6: int
#    7: list
#    8: Video
#    9: list_videos
#   10: tuple
#   11: list_all_videos
#   12: set
#   13: dict
#   14: get_copyright_statuses

  9:           0 RESUME               0
               2 LOAD_NAME            (__name__)
               4 STORE_NAME           (__module__)
               6 LOAD_CONST           ("ListVideosModule")
               8 STORE_NAME           (__qualname__)

 10:          10 LOAD_CONST           ("Public wrapper around IModule._list_videos for use in UI pages.")
              12 STORE_NAME           (__doc__)

 16:          14 NOP

 12:          16 LOAD_CONST           ((50,))
              18 LOAD_CONST           ("channel_id")

 14:          20 LOAD_NAME            (str)

 12:          22 LOAD_CONST           ("video_type")

 15:          24 LOAD_NAME            (VideoType)

 12:          26 LOAD_CONST           ("limit")

 16:          28 LOAD_NAME            (int)

 12:          30 LOAD_CONST           ("return")

 17:          32 LOAD_NAME            (list)
              34 LOAD_NAME            (Video)
              36 BINARY_SUBSCR

 12:          40 BUILD_TUPLE          8
              42 LOAD_CONST           (<Code311 code object list_videos at 0x2e505863570, file src\module\list_videos_module.py>, line 12)
              44 MAKE_FUNCTION        (default, annotation)
              46 STORE_NAME           (list_videos)

 34:          48 NOP

 35:          50 NOP

 31:          52 LOAD_CONST           ((50, None))
              54 LOAD_CONST           ("channel_id")

 33:          56 LOAD_NAME            (str)

 31:          58 LOAD_CONST           ("limit")

 34:          60 LOAD_NAME            (int)

 31:          62 LOAD_CONST           ("page_token")

 35:          64 LOAD_NAME            (str)
              66 LOAD_CONST           (None)
              68 BINARY_OP            (|)

 31:          72 LOAD_CONST           ("return")

 36:          74 LOAD_NAME            (tuple)
              76 LOAD_NAME            (list)
              78 LOAD_NAME            (Video)
              80 BINARY_SUBSCR
              84 LOAD_NAME            (str)
              86 LOAD_CONST           (None)
              88 BINARY_OP            (|)
              92 BUILD_TUPLE          2
              94 BINARY_SUBSCR

 31:          98 BUILD_TUPLE          8
             100 LOAD_CONST           (<Code311 code object list_all_videos at 0x2e5058639b0, file src\module\list_videos_module.py>, line 31)
             102 MAKE_FUNCTION        (default, annotation)
             104 STORE_NAME           (list_all_videos)

257:         106 LOAD_CONST           ("channel_id")

259:         108 LOAD_NAME            (str)

257:         110 LOAD_CONST           ("video_ids")

260:         112 LOAD_NAME            (set)
             114 LOAD_NAME            (str)
             116 BINARY_SUBSCR

257:         120 LOAD_CONST           ("return")

261:         122 LOAD_NAME            (dict)
             124 LOAD_NAME            (str)
             126 LOAD_NAME            (str)
             128 BUILD_TUPLE          2
             130 BINARY_SUBSCR

257:         134 BUILD_TUPLE          6
             136 LOAD_CONST           (<Code311 code object get_copyright_statuses at 0x2e5058638a0, file src\module\list_videos_module.py>, line 257)
             138 MAKE_FUNCTION        (annotation)
             140 STORE_NAME           (get_copyright_statuses)
             142 RETURN_CONST         (None)


# Method Name:       list_videos
# Filename:          src\module\list_videos_module.py
# Argument count:    4
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  4
# Stack size:        5
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        12
# Constants:
#    0: '\n        Fetch videos from a channel filtered by privacy type.\n\n        Args:\n            channel_id: The YouTube channel ID.\n            video_type: VideoType.PRIVATE | PUBLIC | UNLISTED.\n            limit:      Maximum number of videos to return (default 50, max 500).\n\n        Returns:\n            List of Video dataclass instances.\n        '
# Names:
#    0: _list_videos
# Varnames:
#	self, channel_id, video_type, limit
# Positional arguments:
#	self, channel_id, video_type, limit

 12:           0 RESUME               0

 29:           2 LOAD_FAST            (self)
               4 LOAD_ATTR            (NULL|self + _list_videos)
              24 LOAD_FAST            (channel_id)
              26 LOAD_FAST            (video_type)
              28 LOAD_FAST            (limit)
              30 CALL                 3
              38 RETURN_VALUE


# Method Name:       list_all_videos
# Filename:          src\module\list_videos_module.py
# Argument count:    4
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  21
# Stack size:        16
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        31
# Constants:
#    0: '\n        Fetch all uploaded videos for a channel regardless of privacy type.\n\n        Uses a broader filter that omits any privacyIs constraint, returning\n        private, public, and unlisted videos together.\n\n        Args:\n            channel_id:  The YouTube channel ID.\n            limit:       Maximum number of videos per page (default 50, max 500).\n            page_token:  Continuation token from a previous call for pagination.\n\n        Returns:\n            (videos, next_page_token) — next_page_token is None on the last page.\n        '
#    1: None
#    2: "Channel '"
#    3: "' not found in database"
#    4: 'and'
#    5: 'operands'
#    6: 'channelIdIs'
#    7: 'value'
#    8: 'videoOriginIs'
#    9: 'VIDEO_ORIGIN_UPLOAD'
#   10: 'not'
#   11: 'operand'
#   12: 'contentTypeIs'
#   13: 'CREATOR_CONTENT_TYPE_SHORTS'
#   14: 'tvfilmTypeIs'
#   15: 'VIDEO_TVFILM_TYPE_MOVIE'
#   16: 'VIDEO_TVFILM_TYPE_EPISODE'
#   17: 'VIDEO_TVFILM_TYPE_EVENT'
#   18: 'VIDEO_ORDER_DISPLAY_TIME_DESC'
#   19: 'channelId'
#   20: True
#   21: 'videoId'
#   22: 'lengthSeconds'
#   23: 'livestream'
#   24: 'all'
#   25: 'publicLivestream'
#   26: 'origin'
#   27: 'premiere'
#   28: 'publicPremiere'
#   29: 'status'
#   30: 'thumbnailDetails'
#   31: 'title'
#   32: 'draftStatus'
#   33: 'downloadUrl'
#   34: 'watchUrl'
#   35: 'shareUrl'
#   36: 'permissions'
#   37: 'features'
#   38: 'collaboration'
#   39: 'timeCreatedSeconds'
#   40: 'timePublishedSeconds'
#   41: 'privacy'
#   42: 'contentOwnershipModelSettings'
#   43: 'contentType'
#   44: 'publicShorts'
#   45: 'podcastRssMetadata'
#   46: 'videoLinkageShortsAttribution'
#   47: 'alteredContentSettings'
#   48: 'superfansOnly'
#   49: 'tvfilmMetadata'
#   50: 'videoCreatorExperiment'
#   51: 'responseStatus'
#   52: 'statusDetails'
#   53: 'description'
#   54: 'titleFormattedString'
#   55: 'descriptionDetails'
#   56: 'descriptionFormattedString'
#   57: 'titleDetails'
#   58: 'videoDurationMs'
#   59: 'publicMetrics'
#   60: 'audienceRestriction'
#   61: 'releaseInfo'
#   62: 'privateMetrics'
#   63: 'dislikeCount'
#   64: 'monetization'
#   65: 'selfCertification'
#   66: 'allRestrictions'
#   67: 'mfkSettings'
#   68: 'inlineEditProcessingStatus'
#   69: 'videoPrechecks'
#   70: 'videoStreamUrl'
#   71: 'thumbnailEditorState'
#   72: 'videoResolutions'
#   73: 'isSource'
#   74: ('shorts', 'scheduledPublishingDetails', 'visibility', 'privateShare', 'sponsorsOnly', 'unlistedExpired', 'videoTrailers', 'remix', 'isPaygated')
#   75: 62
#   76: '1.20260520.00.00'
#   77: 'vi'
#   78: 'VN'
#   79: ''
#   80: 420
#   81: 'USER_INTERFACE_THEME_DARK'
#   82: 1920
#   83: 150
#   84: 1
#   85: ('clientName', 'clientVersion', 'hl', 'gl', 'experimentsToken', 'utcOffsetMinutes', 'userInterfaceTheme', 'screenWidthPoints', 'screenHeightPoints', 'screenPixelDensity', 'screenDensityFloat')
#   86: 'token'
#   87: ('returnLogEntry', 'internalExperimentFlags', 'eats', 'sessionInfo', 'consistencyTokenJars')
#   88: 'channelRoleType'
#   89: ('externalChannelId', 'roleType')
#   90: ('onBehalfOfUser', 'delegationContext', 'serializedDelegationContext')
#   91: 'visualElement'
#   92: 'veType'
#   93: 31402
#   94: ('client', 'request', 'user', 'clickTracking', 'clientScreenNonce')
#   95: ('filter', 'order', 'pageSize', 'mask', 'context')
#   96: 'https://studio.youtube.com'
#   97: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'
#   98: 'application/json'
#   99: 'SAPISIDHASH '
#  100: ('origin', 'user-agent', 'cookie', 'content-type', 'authorization')
#  101: 'pageToken'
#  102: 'https://studio.youtube.com/youtubei/v1/creator/list_creator_videos?alt=json'
#  103: ('url', 'headers', 'json')
#  104: 'nextPageToken'
#  105: 'videos'
#  106: 'videoUploadChecksMonetized'
#  107: 'copyrightCheck'
#  108: 'checkStatus'
#  109: 'videoUploadChecksNotMonetized'
#  110: 0
#  111: 'thumbnails'
#  112: 'url'
#  113: ('id', 'title', 'description', 'channel_id', 'duration_ms', 'thumbnail', 'privacy', 'video_status', 'copyright_check_status')
#  114: 'Skipping malformed video entry: '
# Names:
#    0: get_channels_info
#    1: ValueError
#    2: cookie_string
#    3: sapisidhash
#    4: _get_session_token
#    5: id
#    6: EATS
#    7: delegated_session_id
#    8: role
#    9: CLIENT_SCREEN_NONCE
#   10: requests
#   11: post
#   12: json
#   13: get
#   14: append
#   15: Video
#   16: Exception
#   17: logger
#   18: warning
# Varnames:
#	self, channel_id, limit, page_token, channel_info, cookie_string, sapisidhash, session_token, payload, headers, url, response, res, next_page_token, videos, item, prechecks, monetized, copyright_status, not_mon, exc
# Positional arguments:
#	self, channel_id, limit, page_token
# Local variables:
#    4: channel_info
#    5: cookie_string
#    6: sapisidhash
#    7: session_token
#    8: payload
#    9: headers
#   10: url
#   11: response
#   12: res
#   13: next_page_token
#   14: videos
#   15: item
#   16: prechecks
#   17: monetized
#   18: copyright_status
#   19: not_mon
#   20: exc

 31:           0 RESUME               0

 51:           2 LOAD_GLOBAL          (NULL + get_channels_info)
              12 LOAD_FAST            (channel_id)
              14 CALL                 1
              22 STORE_FAST           (channel_info)

 52:          24 LOAD_FAST            (channel_info)
              26 POP_JUMP_IF_NOT_NONE (to 58)

 53:          28 LOAD_GLOBAL          (NULL + ValueError)
              38 LOAD_CONST           ("Channel '")
              40 LOAD_FAST            (channel_id)
              42 FORMAT_VALUE         0
              44 LOAD_CONST           ("' not found in database")
              46 BUILD_STRING         3
              48 CALL                 1
              56 RAISE_VARARGS        (exception instance)

 54:     >>   58 LOAD_FAST            (channel_info)
              60 LOAD_ATTR            (NULL|self + cookie_string)
              80 CALL                 0
              88 STORE_FAST           (cookie_string)

 55:          90 LOAD_FAST            (channel_info)
              92 LOAD_ATTR            (sapisidhash)
             112 STORE_FAST           (sapisidhash)

 56:         114 LOAD_FAST            (self)
             116 LOAD_ATTR            (NULL|self + _get_session_token)
             136 LOAD_FAST            (channel_info)
             138 CALL                 1
             146 STORE_FAST           (session_token)

 60:         148 LOAD_CONST           ("and")

 61:         150 LOAD_CONST           ("operands")

 62:         152 LOAD_CONST           ("channelIdIs")
             154 LOAD_CONST           ("value")
             156 LOAD_FAST            (channel_info)
             158 LOAD_ATTR            (id)
             178 BUILD_MAP            1
             180 BUILD_MAP            1

 64:         182 LOAD_CONST           ("and")

 65:         184 LOAD_CONST           ("operands")

 66:         186 LOAD_CONST           ("videoOriginIs")
             188 LOAD_CONST           ("value")
             190 LOAD_CONST           ("VIDEO_ORIGIN_UPLOAD")
             192 BUILD_MAP            1
             194 BUILD_MAP            1

 68:         196 LOAD_CONST           ("not")

 69:         198 LOAD_CONST           ("operand")

 70:         200 LOAD_CONST           ("contentTypeIs")

 71:         202 LOAD_CONST           ("value")
             204 LOAD_CONST           ("CREATOR_CONTENT_TYPE_SHORTS")

 70:         206 BUILD_MAP            1

 69:         208 BUILD_MAP            1

 68:         210 BUILD_MAP            1

 67:         212 BUILD_MAP            1

 65:         214 BUILD_LIST           2

 64:         216 BUILD_MAP            1

 63:         218 BUILD_MAP            1

 80:         220 LOAD_CONST           ("not")

 81:         222 LOAD_CONST           ("operand")

 82:         224 LOAD_CONST           ("tvfilmTypeIs")
             226 LOAD_CONST           ("value")
             228 LOAD_CONST           ("VIDEO_TVFILM_TYPE_MOVIE")
             230 BUILD_MAP            1

 81:         232 BUILD_MAP            1

 80:         234 BUILD_MAP            1

 79:         236 BUILD_MAP            1

 87:         238 LOAD_CONST           ("not")

 88:         240 LOAD_CONST           ("operand")

 89:         242 LOAD_CONST           ("tvfilmTypeIs")

 90:         244 LOAD_CONST           ("value")
             246 LOAD_CONST           ("VIDEO_TVFILM_TYPE_EPISODE")

 89:         248 BUILD_MAP            1

 88:         250 BUILD_MAP            1

 87:         252 BUILD_MAP            1

 86:         254 BUILD_MAP            1

 96:         256 LOAD_CONST           ("not")

 97:         258 LOAD_CONST           ("operand")

 98:         260 LOAD_CONST           ("tvfilmTypeIs")
             262 LOAD_CONST           ("value")
             264 LOAD_CONST           ("VIDEO_TVFILM_TYPE_EVENT")
             266 BUILD_MAP            1

 97:         268 BUILD_MAP            1

 96:         270 BUILD_MAP            1

 95:         272 BUILD_MAP            1

 61:         274 BUILD_LIST           5

 60:         276 BUILD_MAP            1

 59:         278 BUILD_MAP            1

105:         280 LOAD_CONST           ("VIDEO_ORDER_DISPLAY_TIME_DESC")

106:         282 LOAD_FAST            (limit)

107:         284 BUILD_MAP            0

108:         286 LOAD_CONST           ("channelId")
             288 LOAD_CONST           (True)

107:         290 MAP_ADD              1

109:         292 LOAD_CONST           ("videoId")
             294 LOAD_CONST           (True)

107:         296 MAP_ADD              1

110:         298 LOAD_CONST           ("lengthSeconds")
             300 LOAD_CONST           (True)

107:         302 MAP_ADD              1

111:         304 LOAD_CONST           ("livestream")
             306 LOAD_CONST           ("all")
             308 LOAD_CONST           (True)
             310 BUILD_MAP            1

107:         312 MAP_ADD              1

112:         314 LOAD_CONST           ("publicLivestream")
             316 LOAD_CONST           ("all")
             318 LOAD_CONST           (True)
             320 BUILD_MAP            1

107:         322 MAP_ADD              1

113:         324 LOAD_CONST           ("origin")
             326 LOAD_CONST           (True)

107:         328 MAP_ADD              1

114:         330 LOAD_CONST           ("premiere")
             332 LOAD_CONST           ("all")
             334 LOAD_CONST           (True)
             336 BUILD_MAP            1

107:         338 MAP_ADD              1

115:         340 LOAD_CONST           ("publicPremiere")
             342 LOAD_CONST           ("all")
             344 LOAD_CONST           (True)
             346 BUILD_MAP            1

107:         348 MAP_ADD              1

116:         350 LOAD_CONST           ("status")
             352 LOAD_CONST           (True)

107:         354 MAP_ADD              1

117:         356 LOAD_CONST           ("thumbnailDetails")
             358 LOAD_CONST           ("all")
             360 LOAD_CONST           (True)
             362 BUILD_MAP            1

107:         364 MAP_ADD              1

118:         366 LOAD_CONST           ("title")
             368 LOAD_CONST           (True)

107:         370 MAP_ADD              1

119:         372 LOAD_CONST           ("draftStatus")
             374 LOAD_CONST           (True)

107:         376 MAP_ADD              1

120:         378 LOAD_CONST           ("downloadUrl")
             380 LOAD_CONST           (True)

107:         382 MAP_ADD              1

121:         384 LOAD_CONST           ("watchUrl")
             386 LOAD_CONST           (True)

107:         388 MAP_ADD              1

122:         390 LOAD_CONST           ("shareUrl")
             392 LOAD_CONST           (True)

107:         394 MAP_ADD              1

123:         396 LOAD_CONST           ("permissions")
             398 LOAD_CONST           ("all")
             400 LOAD_CONST           (True)
             402 BUILD_MAP            1

107:         404 MAP_ADD              1

124:         406 LOAD_CONST           ("features")
             408 LOAD_CONST           ("all")
             410 LOAD_CONST           (True)
             412 BUILD_MAP            1

107:         414 MAP_ADD              1
             416 BUILD_MAP            0

125:         418 LOAD_CONST           ("collaboration")
             420 LOAD_CONST           ("all")
             422 LOAD_CONST           (True)
             424 BUILD_MAP            1

107:         426 MAP_ADD              1

126:         428 LOAD_CONST           ("timeCreatedSeconds")
             430 LOAD_CONST           (True)

107:         432 MAP_ADD              1

127:         434 LOAD_CONST           ("timePublishedSeconds")
             436 LOAD_CONST           (True)

107:         438 MAP_ADD              1

128:         440 LOAD_CONST           ("privacy")
             442 LOAD_CONST           (True)

107:         444 MAP_ADD              1

129:         446 LOAD_CONST           ("contentOwnershipModelSettings")
             448 LOAD_CONST           ("all")
             450 LOAD_CONST           (True)
             452 BUILD_MAP            1

107:         454 MAP_ADD              1

130:         456 LOAD_CONST           ("contentType")
             458 LOAD_CONST           (True)

107:         460 MAP_ADD              1

131:         462 LOAD_CONST           ("publicShorts")
             464 LOAD_CONST           ("all")
             466 LOAD_CONST           (True)
             468 BUILD_MAP            1

107:         470 MAP_ADD              1

132:         472 LOAD_CONST           ("podcastRssMetadata")
             474 LOAD_CONST           ("all")
             476 LOAD_CONST           (True)
             478 BUILD_MAP            1

107:         480 MAP_ADD              1

133:         482 LOAD_CONST           ("videoLinkageShortsAttribution")
             484 LOAD_CONST           ("all")
             486 LOAD_CONST           (True)
             488 BUILD_MAP            1

107:         490 MAP_ADD              1

134:         492 LOAD_CONST           ("alteredContentSettings")
             494 LOAD_CONST           ("all")
             496 LOAD_CONST           (True)
             498 BUILD_MAP            1

107:         500 MAP_ADD              1

135:         502 LOAD_CONST           ("superfansOnly")
             504 LOAD_CONST           ("all")
             506 LOAD_CONST           (True)
             508 BUILD_MAP            1

107:         510 MAP_ADD              1

136:         512 LOAD_CONST           ("tvfilmMetadata")
             514 LOAD_CONST           ("all")
             516 LOAD_CONST           (True)
             518 BUILD_MAP            1

107:         520 MAP_ADD              1

137:         522 LOAD_CONST           ("videoCreatorExperiment")
             524 LOAD_CONST           ("all")
             526 LOAD_CONST           (True)
             528 BUILD_MAP            1

107:         530 MAP_ADD              1

138:         532 LOAD_CONST           ("responseStatus")
             534 LOAD_CONST           ("all")
             536 LOAD_CONST           (True)
             538 BUILD_MAP            1

107:         540 MAP_ADD              1

139:         542 LOAD_CONST           ("statusDetails")
             544 LOAD_CONST           ("all")
             546 LOAD_CONST           (True)
             548 BUILD_MAP            1

107:         550 MAP_ADD              1

140:         552 LOAD_CONST           ("description")
             554 LOAD_CONST           (True)

107:         556 MAP_ADD              1

141:         558 LOAD_CONST           ("titleFormattedString")
             560 LOAD_CONST           ("all")
             562 LOAD_CONST           (True)
             564 BUILD_MAP            1

107:         566 MAP_ADD              1
             568 DICT_UPDATE          1
             570 BUILD_MAP            0

142:         572 LOAD_CONST           ("descriptionDetails")
             574 LOAD_CONST           ("all")
             576 LOAD_CONST           (True)
             578 BUILD_MAP            1

107:         580 MAP_ADD              1

143:         582 LOAD_CONST           ("descriptionFormattedString")
             584 LOAD_CONST           ("all")
             586 LOAD_CONST           (True)
             588 BUILD_MAP            1

107:         590 MAP_ADD              1

144:         592 LOAD_CONST           ("titleDetails")
             594 LOAD_CONST           ("all")
             596 LOAD_CONST           (True)
             598 BUILD_MAP            1

107:         600 MAP_ADD              1

145:         602 LOAD_CONST           ("videoDurationMs")
             604 LOAD_CONST           (True)

107:         606 MAP_ADD              1

146:         608 LOAD_CONST           ("publicMetrics")
             610 LOAD_CONST           ("all")
             612 LOAD_CONST           (True)
             614 BUILD_MAP            1

107:         616 MAP_ADD              1

147:         618 LOAD_CONST           ("audienceRestriction")
             620 LOAD_CONST           ("all")
             622 LOAD_CONST           (True)
             624 BUILD_MAP            1

107:         626 MAP_ADD              1

148:         628 LOAD_CONST           ("releaseInfo")
             630 LOAD_CONST           ("all")
             632 LOAD_CONST           (True)
             634 BUILD_MAP            1

107:         636 MAP_ADD              1

149:         638 LOAD_CONST           ("privateMetrics")
             640 LOAD_CONST           ("dislikeCount")
             642 LOAD_CONST           (True)
             644 BUILD_MAP            1

107:         646 MAP_ADD              1

150:         648 LOAD_CONST           ("monetization")
             650 LOAD_CONST           ("all")
             652 LOAD_CONST           (True)
             654 BUILD_MAP            1

107:         656 MAP_ADD              1

151:         658 LOAD_CONST           ("selfCertification")
             660 LOAD_CONST           ("all")
             662 LOAD_CONST           (True)
             664 BUILD_MAP            1

107:         666 MAP_ADD              1

152:         668 LOAD_CONST           ("allRestrictions")
             670 LOAD_CONST           ("all")
             672 LOAD_CONST           (True)
             674 BUILD_MAP            1

107:         676 MAP_ADD              1

153:         678 LOAD_CONST           ("mfkSettings")
             680 LOAD_CONST           ("all")
             682 LOAD_CONST           (True)
             684 BUILD_MAP            1

107:         686 MAP_ADD              1

154:         688 LOAD_CONST           ("inlineEditProcessingStatus")
             690 LOAD_CONST           (True)

107:         692 MAP_ADD              1

155:         694 LOAD_CONST           ("videoPrechecks")
             696 LOAD_CONST           ("all")
             698 LOAD_CONST           (True)
             700 BUILD_MAP            1

107:         702 MAP_ADD              1

156:         704 LOAD_CONST           ("videoStreamUrl")
             706 LOAD_CONST           (True)

107:         708 MAP_ADD              1

157:         710 LOAD_CONST           ("thumbnailEditorState")
             712 LOAD_CONST           ("all")
             714 LOAD_CONST           (True)
             716 BUILD_MAP            1

107:         718 MAP_ADD              1

158:         720 LOAD_CONST           ("videoResolutions")
             722 LOAD_CONST           ("all")
             724 LOAD_CONST           (True)
             726 BUILD_MAP            1

107:         728 MAP_ADD              1
             730 DICT_UPDATE          1

159:         732 LOAD_CONST           ("all")
             734 LOAD_CONST           (True)
             736 BUILD_MAP            1

160:         738 LOAD_CONST           ("all")
             740 LOAD_CONST           (True)
             742 BUILD_MAP            1

161:         744 LOAD_CONST           ("all")
             746 LOAD_CONST           (True)
             748 BUILD_MAP            1

162:         750 LOAD_CONST           ("all")
             752 LOAD_CONST           (True)
             754 BUILD_MAP            1

163:         756 LOAD_CONST           ("all")
             758 LOAD_CONST           (True)
             760 BUILD_MAP            1

164:         762 LOAD_CONST           (True)

165:         764 LOAD_CONST           ("all")
             766 LOAD_CONST           (True)
             768 BUILD_MAP            1

166:         770 LOAD_CONST           ("isSource")
             772 LOAD_CONST           (True)
             774 BUILD_MAP            1

167:         776 LOAD_CONST           (True)

107:         778 LOAD_CONST           (('shorts', 'scheduledPublishingDetails', 'visibility', 'privateShare', 'sponsorsOnly', 'unlistedExpired', 'videoTrailers', 'remix', 'isPaygated'))
             780 BUILD_CONST_KEY_MAP  9
             782 DICT_UPDATE          1

171:         784 LOAD_CONST           (62)

172:         786 LOAD_CONST           ("1.20260520.00.00")

173:         788 LOAD_CONST           ("vi")

174:         790 LOAD_CONST           ("VN")

175:         792 LOAD_CONST           ("")

176:         794 LOAD_CONST           (420)

177:         796 LOAD_CONST           ("USER_INTERFACE_THEME_DARK")

178:         798 LOAD_CONST           (1920)

179:         800 LOAD_CONST           (150)

180:         802 LOAD_CONST           (1)

181:         804 LOAD_CONST           (1)

170:         806 LOAD_CONST           (('clientName', 'clientVersion', 'hl', 'gl', 'experimentsToken', 'utcOffsetMinutes', 'userInterfaceTheme', 'screenWidthPoints', 'screenHeightPoints', 'screenPixelDensity', 'screenDensityFloat'))
             808 BUILD_CONST_KEY_MAP  11

184:         810 LOAD_CONST           (True)

185:         812 BUILD_LIST           0

186:         814 LOAD_FAST            (self)
             816 LOAD_ATTR            (EATS)

187:         836 LOAD_CONST           ("token")
             838 LOAD_FAST            (session_token)
             840 BUILD_MAP            1

188:         842 BUILD_LIST           0

183:         844 LOAD_CONST           (('returnLogEntry', 'internalExperimentFlags', 'eats', 'sessionInfo', 'consistencyTokenJars'))
             846 BUILD_CONST_KEY_MAP  5

191:         848 LOAD_FAST            (channel_info)
             850 LOAD_ATTR            (delegated_session_id)

193:         870 LOAD_FAST            (channel_info)
             872 LOAD_ATTR            (id)

194:         892 LOAD_CONST           ("channelRoleType")
             894 LOAD_FAST            (channel_info)
             896 LOAD_ATTR            (role)
             916 BUILD_MAP            1

192:         918 LOAD_CONST           (('externalChannelId', 'roleType'))
             920 BUILD_CONST_KEY_MAP  2

196:         922 LOAD_CONST           ("")

190:         924 LOAD_CONST           (('onBehalfOfUser', 'delegationContext', 'serializedDelegationContext'))
             926 BUILD_CONST_KEY_MAP  3

198:         928 LOAD_CONST           ("visualElement")
             930 LOAD_CONST           ("veType")
             932 LOAD_CONST           (31402)
             934 BUILD_MAP            1
             936 BUILD_MAP            1

199:         938 LOAD_FAST            (self)
             940 LOAD_ATTR            (CLIENT_SCREEN_NONCE)

169:         960 LOAD_CONST           (('client', 'request', 'user', 'clickTracking', 'clientScreenNonce'))
             962 BUILD_CONST_KEY_MAP  5

 58:         964 LOAD_CONST           (('filter', 'order', 'pageSize', 'mask', 'context'))
             966 BUILD_CONST_KEY_MAP  5
             968 STORE_FAST           (payload)

204:         970 LOAD_CONST           ("https://studio.youtube.com")

206:         972 LOAD_CONST           ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")

210:         974 LOAD_FAST            (cookie_string)

211:         976 LOAD_CONST           ("application/json")

212:         978 LOAD_CONST           ("SAPISIDHASH ")
             980 LOAD_FAST            (sapisidhash)
             982 FORMAT_VALUE         0
             984 BUILD_STRING         2

203:         986 LOAD_CONST           (('origin', 'user-agent', 'cookie', 'content-type', 'authorization'))
             988 BUILD_CONST_KEY_MAP  5
             990 STORE_FAST           (headers)

216:         992 LOAD_FAST            (page_token)
             994 POP_JUMP_IF_FALSE    (to 1006)

217:         996 LOAD_FAST            (page_token)
             998 LOAD_FAST            (payload)
            1000 LOAD_CONST           ("pageToken")
            1002 STORE_SUBSCR

219:     >> 1006 LOAD_CONST           ("https://studio.youtube.com/youtubei/v1/creator/list_creator_videos?alt=json")
            1008 STORE_FAST           (url)

220:        1010 LOAD_GLOBAL          (NULL + requests)
            1020 LOAD_ATTR            (post)
            1040 LOAD_FAST            (url)
            1042 LOAD_FAST            (headers)
            1044 LOAD_FAST            (payload)
            1046 KW_NAMES             (('url', 'headers', 'json'))
            1048 CALL                 3
            1056 STORE_FAST           (response)

221:        1058 LOAD_FAST            (response)
            1060 LOAD_ATTR            (NULL|self + json)
            1080 CALL                 0
            1088 STORE_FAST           (res)

223:        1090 LOAD_FAST            (res)
            1092 LOAD_ATTR            (NULL|self + get)
            1112 LOAD_CONST           ("nextPageToken")
            1114 CALL                 1
            1122 COPY                 1
            1124 POP_JUMP_IF_TRUE     (to 1130)
            1126 POP_TOP
            1128 LOAD_CONST           (None)
         >> 1130 STORE_FAST           (next_page_token)

225:        1132 BUILD_LIST           0
            1134 STORE_FAST           (videos)

226:        1136 LOAD_FAST            (res)
            1138 LOAD_ATTR            (NULL|self + get)
            1158 LOAD_CONST           ("videos")
            1160 BUILD_LIST           0
            1162 CALL                 2
            1170 GET_ITER
            1172 EXTENDED_ARG         (256)
            1174 FOR_ITER             (to 1832)
            1178 STORE_FAST           (item)

227:        1180 NOP

230:        1182 LOAD_FAST            (item)
            1184 LOAD_ATTR            (NULL|self + get)
            1204 LOAD_CONST           ("videoPrechecks")
            1206 BUILD_MAP            0
            1208 CALL                 2
            1216 STORE_FAST           (prechecks)

231:        1218 LOAD_FAST            (prechecks)
            1220 LOAD_ATTR            (NULL|self + get)
            1240 LOAD_CONST           ("videoUploadChecksMonetized")
            1242 BUILD_MAP            0
            1244 CALL                 2
            1252 STORE_FAST           (monetized)

232:        1254 LOAD_FAST            (monetized)
            1256 LOAD_ATTR            (NULL|self + get)
            1276 LOAD_CONST           ("copyrightCheck")
            1278 BUILD_MAP            0
            1280 CALL                 2
            1288 LOAD_ATTR            (NULL|self + get)
            1308 LOAD_CONST           ("checkStatus")
            1310 LOAD_CONST           ("")
            1312 CALL                 2
            1320 STORE_FAST           (copyright_status)

233:        1322 LOAD_FAST            (copyright_status)
            1324 POP_JUMP_IF_TRUE     (to 1430)

234:        1326 LOAD_FAST            (prechecks)
            1328 LOAD_ATTR            (NULL|self + get)
            1348 LOAD_CONST           ("videoUploadChecksNotMonetized")
            1350 BUILD_MAP            0
            1352 CALL                 2
            1360 STORE_FAST           (not_mon)

235:        1362 LOAD_FAST            (not_mon)
            1364 LOAD_ATTR            (NULL|self + get)
            1384 LOAD_CONST           ("copyrightCheck")
            1386 BUILD_MAP            0
            1388 CALL                 2
            1396 LOAD_ATTR            (NULL|self + get)
            1416 LOAD_CONST           ("checkStatus")
            1418 LOAD_CONST           ("")
            1420 CALL                 2
            1428 STORE_FAST           (copyright_status)

237:     >> 1430 LOAD_FAST            (videos)
            1432 LOAD_ATTR            (NULL|self + append)

238:        1452 LOAD_GLOBAL          (NULL + Video)

239:        1462 LOAD_FAST            (item)
            1464 LOAD_ATTR            (NULL|self + get)
            1484 LOAD_CONST           ("videoId")
            1486 LOAD_CONST           ("")
            1488 CALL                 2

240:        1496 LOAD_FAST            (item)
            1498 LOAD_ATTR            (NULL|self + get)
            1518 LOAD_CONST           ("title")
            1520 LOAD_CONST           ("")
            1522 CALL                 2

241:        1530 LOAD_FAST            (item)
            1532 LOAD_ATTR            (NULL|self + get)
            1552 LOAD_CONST           ("description")
            1554 LOAD_CONST           ("")
            1556 CALL                 2

242:        1564 LOAD_FAST            (item)
            1566 LOAD_ATTR            (NULL|self + get)
            1586 LOAD_CONST           ("channelId")
            1588 LOAD_CONST           ("")
            1590 CALL                 2

243:        1598 LOAD_FAST            (item)
            1600 LOAD_ATTR            (NULL|self + get)
            1620 LOAD_CONST           ("videoDurationMs")
            1622 LOAD_CONST           (0)
            1624 CALL                 2

244:        1632 LOAD_FAST            (item)
            1634 LOAD_ATTR            (NULL|self + get)
            1654 LOAD_CONST           ("thumbnailDetails")
            1656 BUILD_MAP            0
            1658 CALL                 2

245:        1666 LOAD_ATTR            (NULL|self + get)
            1686 LOAD_CONST           ("thumbnails")
            1688 BUILD_MAP            0
            1690 BUILD_LIST           1
            1692 CALL                 2
            1700 LOAD_CONST           (0)

244:        1702 BINARY_SUBSCR

246:        1706 LOAD_ATTR            (NULL|self + get)
            1726 LOAD_CONST           ("url")
            1728 LOAD_CONST           ("")
            1730 CALL                 2

247:        1738 LOAD_FAST            (item)
            1740 LOAD_ATTR            (NULL|self + get)
            1760 LOAD_CONST           ("privacy")
            1762 LOAD_CONST           ("")
            1764 CALL                 2

248:        1772 LOAD_FAST            (item)
            1774 LOAD_ATTR            (NULL|self + get)
            1794 LOAD_CONST           ("status")
            1796 LOAD_CONST           ("")
            1798 CALL                 2

249:        1806 LOAD_FAST            (copyright_status)

238:        1808 KW_NAMES             (('id', 'title', 'description', 'channel_id', 'duration_ms', 'thumbnail', 'privacy', 'video_status', 'copyright_check_status'))
            1810 CALL                 9

237:        1818 CALL                 1
            1826 POP_TOP
            1828 EXTENDED_ARG         (256)
         >> 1830 JUMP_BACKWARD        (to 1172)

226:        1832 END_FOR

255:        1834 LOAD_FAST            (videos)
            1836 LOAD_FAST            (next_page_token)
            1838 BUILD_TUPLE          2
            1840 RETURN_VALUE
            1842 PUSH_EXC_INFO

252:        1844 LOAD_GLOBAL          (Exception)
            1854 CHECK_EXC_MATCH
            1856 POP_JUMP_IF_FALSE    (to 1928)
            1858 STORE_FAST           (exc)

253:        1860 LOAD_GLOBAL          (NULL + logger)
            1870 LOAD_ATTR            (warning)
            1890 LOAD_CONST           ("Skipping malformed video entry: ")
            1892 LOAD_FAST            (exc)
            1894 FORMAT_VALUE         0
            1896 BUILD_STRING         2
            1898 CALL                 1
            1906 POP_TOP
            1908 POP_EXCEPT
            1910 LOAD_CONST           (None)
            1912 STORE_FAST           (exc)
            1914 DELETE_FAST          (exc)
            1916 EXTENDED_ARG         (256)
            1918 JUMP_BACKWARD        (to 1172)
            1920 LOAD_CONST           (None)
            1922 STORE_FAST           (exc)
            1924 DELETE_FAST          (exc)
            1926 RERAISE              1

252:     >> 1928 RERAISE              0
            1930 COPY                 3
            1932 POP_EXCEPT
            1934 RERAISE              1

ExceptionTable:
  1182 to 1826 -> 1842 [1]
  1842 to 1858 -> 1930 [2] lasti
  1860 to 1906 -> 1920 [2] lasti
  1920 to 1928 -> 1930 [2] lasti

# Method Name:       get_copyright_statuses
# Filename:          src\module\list_videos_module.py
# Argument count:    3
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  9
# Stack size:        5
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        257
# Constants:
#    0: '\n        Return {video_id: copyright_check_status} for the given video IDs.\n        Scans pages newest-first and stops once every requested ID is found.\n\n        Args:\n            channel_id: The YouTube channel ID.\n            video_ids:  Set of video IDs to look up.\n\n        Returns:\n            Dict mapping each found video ID to its current copyright check status.\n        '
#    1: None
#    2: 50
# Names:
#    0: set
#    1: list_all_videos
#    2: id
#    3: copyright_check_status
#    4: discard
# Varnames:
#	self, channel_id, video_ids, remaining, result, page_token, videos, next_token, v
# Positional arguments:
#	self, channel_id, video_ids
# Local variables:
#    3: remaining
#    4: result
#    5: page_token
#    6: videos
#    7: next_token
#    8: v

257:           0 RESUME               0

273:           2 LOAD_GLOBAL          (NULL + set)
              12 LOAD_FAST            (video_ids)
              14 CALL                 1
              22 STORE_FAST           (remaining)

274:          24 BUILD_MAP            0
              26 STORE_FAST           (result)

275:          28 LOAD_CONST           (None)
              30 STORE_FAST           (page_token)

277:          32 LOAD_FAST            (remaining)
              34 POP_JUMP_IF_FALSE    (to 252)

278:          36 LOAD_FAST            (self)
              38 LOAD_ATTR            (NULL|self + list_all_videos)
              58 LOAD_FAST            (channel_id)
              60 LOAD_CONST           (50)
              62 LOAD_FAST            (page_token)
              64 CALL                 3
              72 UNPACK_SEQUENCE      2
              76 STORE_FAST           (videos)
              78 STORE_FAST           (next_token)

279:          80 LOAD_FAST            (videos)
              82 GET_ITER
              84 FOR_ITER             (to 226)
              88 STORE_FAST           (v)

280:          90 LOAD_FAST            (v)
              92 LOAD_ATTR            (id)
             112 LOAD_FAST            (remaining)
             114 CONTAINS_OP          (in)
             116 POP_JUMP_IF_TRUE     (to 120)
             118 JUMP_BACKWARD        (to 84)

281:     >>  120 LOAD_FAST            (v)
             122 LOAD_ATTR            (copyright_check_status)
             142 LOAD_FAST            (result)
             144 LOAD_FAST            (v)
             146 LOAD_ATTR            (id)
             166 STORE_SUBSCR

282:         170 LOAD_FAST            (remaining)
             172 LOAD_ATTR            (NULL|self + discard)
             192 LOAD_FAST            (v)
             194 LOAD_ATTR            (id)
             214 CALL                 1
             222 POP_TOP
         >>  224 JUMP_BACKWARD        (to 84)

279:         226 END_FOR

283:         228 LOAD_FAST            (next_token)
             230 POP_JUMP_IF_FALSE    (to 236)
             232 LOAD_FAST            (remaining)
             234 POP_JUMP_IF_TRUE     (to 242)

284:     >>  236 NOP

287:         238 LOAD_FAST            (result)
             240 RETURN_VALUE

285:     >>  242 LOAD_FAST            (next_token)
             244 STORE_FAST           (page_token)

277:         246 LOAD_FAST            (remaining)
             248 POP_JUMP_IF_FALSE    (to 252)
             250 JUMP_BACKWARD        (to 36)

287:     >>  252 LOAD_FAST            (result)
             254 RETURN_VALUE

```
