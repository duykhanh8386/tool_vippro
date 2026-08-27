# Static CPython 3.12 disassembly — `base.pyc`

Generated with `xdis 6.3.0`; the code object was deserialized but never executed.

```text
# pydisasm version 6.3.0
# CPython Python bytecode 3.12.0 (3531)
#   Disassembled from CPython Python 3.13.13 | packaged by Anaconda, Inc. | (main, Apr 14 2026, 06:12:50) [MSC v.1942 64 bit (AMD64)]
# Timestamp in code: 0 (1970-01-01 07:00:00)
# Source code size mod 2**32: 0 bytes
# Method Name:       <module>
# Filename:          src\module\base.py
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
#    2: ('ABC',)
#    3: ('logger',)
#    4: ('ChannelInfo', 'Video', 'VideoType')
#    5: ('get_channels_info',)
#    6: <Code311 code object IModule at 0x2e505863130, file src\module\base.py>, line 11
#    7: 'IModule'
# Names:
#    0: json
#    1: abc
#    2: ABC
#    3: requests
#    4: loguru
#    5: logger
#    6: src.module.model
#    7: ChannelInfo
#    8: Video
#    9: VideoType
#   10: src.utils
#   11: get_channels_info
#   12: IModule

  0:           0 RESUME               0

  1:           2 LOAD_CONST           (0)
               4 LOAD_CONST           (None)
               6 IMPORT_NAME          (json)
               8 STORE_NAME           (json)

  2:          10 LOAD_CONST           (0)
              12 LOAD_CONST           (('ABC',))
              14 IMPORT_NAME          (abc)
              16 IMPORT_FROM          (ABC)
              18 STORE_NAME           (ABC)
              20 POP_TOP

  4:          22 LOAD_CONST           (0)
              24 LOAD_CONST           (None)
              26 IMPORT_NAME          (requests)
              28 STORE_NAME           (requests)

  5:          30 LOAD_CONST           (0)
              32 LOAD_CONST           (('logger',))
              34 IMPORT_NAME          (loguru)
              36 IMPORT_FROM          (logger)
              38 STORE_NAME           (logger)
              40 POP_TOP

  7:          42 LOAD_CONST           (0)
              44 LOAD_CONST           (('ChannelInfo', 'Video', 'VideoType'))
              46 IMPORT_NAME          (src.module.model)
              48 IMPORT_FROM          (ChannelInfo)
              50 STORE_NAME           (ChannelInfo)
              52 IMPORT_FROM          (Video)
              54 STORE_NAME           (Video)
              56 IMPORT_FROM          (VideoType)
              58 STORE_NAME           (VideoType)
              60 POP_TOP

  8:          62 LOAD_CONST           (0)
              64 LOAD_CONST           (('get_channels_info',))
              66 IMPORT_NAME          (src.utils)
              68 IMPORT_FROM          (get_channels_info)
              70 STORE_NAME           (get_channels_info)
              72 POP_TOP

 11:          74 PUSH_NULL
              76 LOAD_BUILD_CLASS
              78 LOAD_CONST           (<Code311 code object IModule at 0x2e505863130, file src\module\base.py>, line 11)
              80 MAKE_FUNCTION        (No arguments)
              82 LOAD_CONST           ("IModule")
              84 LOAD_NAME            (ABC)
              86 CALL                 3
              94 STORE_NAME           (IModule)
              96 RETURN_CONST         (None)


# Method Name:       IModule
# Filename:          src\module\base.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        23
# Flags:             0x00000000 (0x0)
# First Line:        11
# Constants:
#    0: 'IModule'
#    1: 'AXAuXyagZ24uKnNz0kYZbLTt32KGDRxhKqK2ns7At7Rkxw4UXW19g-oH1ng4py8No7EiqwNid9eQAFhJ7_8XJFiitSaWQdlXlG7nmJStO8tVWrrAAQ=='
#    2: '8Z1g2AhnbTXfVuBp'
#    3: 'a=6&a2=3&b=UAAoAmaAwwDIrKcvn9_rgzH-Jr4&c=1746756602&d=62&e3=UCAICychz3FdwEAyD6Rv-IRQ&c1a=1&hh=PSyUV3k8pO-Z9_6qmFQtKyKipjuIekgJtEtZvvmqpn0'
#    4: '$euU55b1RAAbvRbg0z0XewMv_S0uMtXGnADQBEArZ1HMQG4pgLXVbdPcdDixwJ1GZIjKtUDtG9tZmNJbg9W0ElVuifwYo-lT9CfcGMbryngAAACzOAAAA8fQBB-IASY3N5JAhIeAY5HKAdoI0yEECI_IJZ-vRui2z4nzlEoLB50R2iz607ou69KS463F-Ncivzmqmrurv2jJXSyl-d0TbLu7WaW-WEbsFBG4ZglwEBE_ccLro1tMinuYe2g0-E842CWJroVmf6sc716sKgXbH8XKn5WXsRjXqeuVHSZ8g-ds5FQLBMCLVRU7zVhpijepG729n8mztRnv3IuDL4sWycDhphf0IyIxPhQ_vVeuwX9En5nue0pZjeNetiMIFmI1acJDq474vIS9dU6XDknDze6gN0QbjXWrsYMYyO1zj5sMiLShfljFfCp7dp2f0LHOmAPGJdklHWgMXIYOmZW2wDi5FmcZBK12hx4YUrtMxXtXv1l6BJftZCzR0apgb5kDcR56jtHzxQCGp4kaNPV5SLO4oUV7vlkUCL2yc_a9seNhRnDeIM3ToQYRv7M1nQpPDfeiFaP4-X3WtlvdNFit_0UQV8BYImVdnnTdulniHz2roAg3PoMhtLT0QFUE5UfE6gupz1A35kHrb9UAqMtAgC0JSEI9Hn2m64wviQH5YyOoYlxNIGYz7vFGDqXX_yquJ57zosGcmgGwPulJjh_cUOBXjnwGRFAgTdvHkaIcwQNmWdJUWT4yxhy7-9AsLAravJUjygijZfajXrVEd9Dhv2GvyKSDGO_8WCunYImbXNy6bjfdO31HD9B0Bb9Yaqsyq3TFlUy1giqhdDJKRVZ2fQpjIKApaXITB-uLJQfleS6VVCKeMfwrtty056wlNQVuWuaQ8-XqDgOJclKHt8wOEMSEBEpwVc5ocBjEZ-wBLiorr7G1q66Ulp-HF4_Iwh7xUULUhH1M5FupXG93XQY9AR1M-MWeqQ07AIJ7FKGthd0wLuTavQ-1xQrymxWULSIuyaC7hpQxf1cIVh7EE2YrOhKVBowEe1LnFCUgCGXPBOd9TrQnkGLyKcYAOwzWdII7Zl5RPfHmPLUyk-niJ1Ygey4Dhmxzv9g8udrOvGr9mZDtIjKr-1z1cl-W2lDXWuRjfiRYNgOhPQOCXq21ULvlEOtR-9C2EVIABVXd14rGtJzsuXUwnr6CD29Odm64nbRPCa3leXuz1pOR1QOi0984sblJ0B_lRIGiXVd4RoUewatihEyzSGg2MFV1k2CdYrxK_yfv0hCHWc-JmixNmWFjXp7PrQvD3NMWZlb5Wb9J1mgl6nnxT7gPGo07xvYpiRBRwA6HU7QFcnP7yYsekWGXte5Sk3QJsu2m1lWpp-R9jiqpfw6Qf8zjwDVgbjXaq7pkrCyJIZeiBgDEWow2IbKa0GlRPuvmxLj3QToOjqCCqCXAtRiYGJzeyH0dd6HdIaJckCHYE1KiWp1SifXILE9TwQs2izR55MteVSZ_D9k3n0GBNnJXhUv5LREKWCFo5i0IgFMIFUEYA9uAaA_KPIxbfNYwy5VL6GvHFctg8RdHvZb6-ZYpieMTnkT2srMF20Yh148zsAIoZ3Z6J6upgwljNeHqOUXYVtIORaPUt7Sq54x67YZ7eVKU1-eA-qpqqAJ9jfTXjalxYRe2RbScWuluGr7lfL4vT5CL_ySttj-4doOtBJgVW4YRkhKjicZpBZg_uZizhgzB3Q7Q'
#    5: 'channel_id'
#    6: 'video_type'
#    7: 'limit'
#    8: 'return'
#    9: <Code311 code object _list_videos at 0x2e505862e00, file src\module\base.py>, line 17
#   10: 'video_id'
#   11: <Code311 code object _get_video_info at 0x2e505863020, file src\module\base.py>, line 238
#   12: '1.20260311.03.00'
#   13: 'en'
#   14: 'USER_INTERFACE_THEME_DARK'
#   15: 1920
#   16: 945
#   17: True
#   18: None
#   19: ('client_version', 'hl', 'theme', 'screen_width', 'screen_height', 'include_on_behalf_of_user', 'extra_request_fields')
#   20: 'role'
#   21: 'delegated_session_id'
#   22: 'client_version'
#   23: 'hl'
#   24: 'theme'
#   25: 'screen_width'
#   26: 'screen_height'
#   27: 'include_on_behalf_of_user'
#   28: 'extra_request_fields'
#   29: <Code311 code object _build_context at 0x2e505862f10, file src\module\base.py>, line 414
#   30: <Code311 code object _get_session_token at 0x2e505863240, file src\module\base.py>, line 468
#   31: (50,)
# Names:
#    0: __name__
#    1: __module__
#    2: __qualname__
#    3: EATS
#    4: CLIENT_SCREEN_NONCE
#    5: CHALLENGE
#    6: BOT_GUARD_RESPONSE
#    7: str
#    8: VideoType
#    9: int
#   10: list
#   11: Video
#   12: _list_videos
#   13: _get_video_info
#   14: bool
#   15: dict
#   16: _build_context
#   17: _get_session_token

 11:           0 RESUME               0
               2 LOAD_NAME            (__name__)
               4 STORE_NAME           (__module__)
               6 LOAD_CONST           ("IModule")
               8 STORE_NAME           (__qualname__)

 12:          10 LOAD_CONST           ("AXAuXyagZ24uKnNz0kYZbLTt32KGDRxhKqK2ns7At7Rkxw4UXW19g-oH1ng4py8No7EiqwNid9eQAFhJ7_8XJFiitSaWQdlXlG7nmJStO8tVWrrAAQ==")
              12 STORE_NAME           (EATS)

 13:          14 LOAD_CONST           ("8Z1g2AhnbTXfVuBp")
              16 STORE_NAME           (CLIENT_SCREEN_NONCE)

 14:          18 LOAD_CONST           ("a=6&a2=3&b=UAAoAmaAwwDIrKcvn9_rgzH-Jr4&c=1746756602&d=62&e3=UCAICychz3FdwEAyD6Rv-IRQ&c1a=1&hh=PSyUV3k8pO-Z9_6qmFQtKyKipjuIekgJtEtZvvmqpn0")
              20 STORE_NAME           (CHALLENGE)

 15:          22 LOAD_CONST           ("$euU55b1RAAbvRbg0z0XewMv_S0uMtXGnADQBEArZ1HMQG4pgLXVbdPcdDixwJ1GZIjKtUDtG9tZmNJbg9W0ElVuifwYo-lT9CfcGMbryngAAACzOAAAA8fQBB-IASY3N5JAhIeAY5HKAdoI0yEECI_IJZ-vRui2z4nzlEoLB50R2iz607ou69KS463F-Ncivzmqmrurv2jJXSyl-d0TbLu7WaW-WEbsFBG4ZglwEBE_ccLro1tMinuYe2g0-E842CWJroVmf6sc716sKgXbH8XKn5WXsRjXqeuVHSZ8g-ds5FQLBMCLVRU7zVhpijepG729n8mztRnv3IuDL4sWycDhphf0IyIxPhQ_vVeuwX9En5nue0pZjeNetiMIFmI1acJDq474vIS9dU6XDknDze6gN0QbjXWrsYMYyO1zj5sMiLShfljFfCp7dp2f0LHOmAPGJdklHWgMXIYOmZW2wDi5FmcZBK12hx4YUrtMxXtXv1l6BJftZCzR0apgb5kDcR56jtHzxQCGp4kaNPV5SLO4oUV7vlkUCL2yc_a9seNhRnDeIM3ToQYRv7M1nQpPDfeiFaP4-X3WtlvdNFit_0UQV8BYImVdnnTdulniHz2roAg3PoMhtLT0QFUE5UfE6gupz1A35kHrb9UAqMtAgC0JSEI9Hn2m64wviQH5YyOoYlxNIGYz7vFGDqXX_yquJ57zosGcmgGwPulJjh_cUOBXjnwGRFAgTdvHkaIcwQNmWdJUWT4yxhy7-9AsLAravJUjygijZfajXrVEd9Dhv2GvyKSDGO_8WCunYImbXNy6bjfdO31HD9B0Bb9Yaqsyq3TFlUy1giqhdDJKRVZ2fQpjIKApaXITB-uLJQfleS6VVCKeMfwrtty056wlNQVuWuaQ8-XqDgOJclKHt8wOEMSEBEpwVc5ocBjEZ-wBLiorr7G1q66Ulp-HF4_Iwh7xUULUhH1M5FupXG93XQY9AR1M-MWeqQ07AIJ7FKGthd0wLuTavQ-1xQrymxWULSIuyaC7hpQxf1cIVh7EE2YrOhKVBowEe1LnFCUgCGXPBOd9TrQnkGLyKcYAOwzWdII7Zl5RPfHmPLUyk-niJ1Ygey4Dhmxzv9g8udrOvGr9mZDtIjKr-1z1cl-W2lDXWuRjfiRYNgOhPQOCXq21ULvlEOtR-9C2EVIABVXd14rGtJzsuXUwnr6CD29Odm64nbRPCa3leXuz1pOR1QOi0984sblJ0B_lRIGiXVd4RoUewatihEyzSGg2MFV1k2CdYrxK_yfv0hCHWc-JmixNmWFjXp7PrQvD3NMWZlb5Wb9J1mgl6nnxT7gPGo07xvYpiRBRwA6HU7QFcnP7yYsekWGXte5Sk3QJsu2m1lWpp-R9jiqpfw6Qf8zjwDVgbjXaq7pkrCyJIZeiBgDEWow2IbKa0GlRPuvmxLj3QToOjqCCqCXAtRiYGJzeyH0dd6HdIaJckCHYE1KiWp1SifXILE9TwQs2izR55MteVSZ_D9k3n0GBNnJXhUv5LREKWCFo5i0IgFMIFUEYA9uAaA_KPIxbfNYwy5VL6GvHFctg8RdHvZb6-ZYpieMTnkT2srMF20Yh148zsAIoZ3Z6J6upgwljNeHqOUXYVtIORaPUt7Sq54x67YZ7eVKU1-eA-qpqqAJ9jfTXjalxYRe2RbScWuluGr7lfL4vT5CL_ySttj-4doOtBJgVW4YRkhKjicZpBZg_uZizhgzB3Q7Q")
              24 STORE_NAME           (BOT_GUARD_RESPONSE)

 18:          26 NOP

 17:          28 LOAD_CONST           ((50,))
              30 LOAD_CONST           ("channel_id")

 18:          32 LOAD_NAME            (str)

 17:          34 LOAD_CONST           ("video_type")

 18:          36 LOAD_NAME            (VideoType)

 17:          38 LOAD_CONST           ("limit")

 18:          40 LOAD_NAME            (int)

 17:          42 LOAD_CONST           ("return")

 19:          44 LOAD_NAME            (list)
              46 LOAD_NAME            (Video)
              48 BINARY_SUBSCR

 17:          52 BUILD_TUPLE          8
              54 LOAD_CONST           (<Code311 code object _list_videos at 0x2e505862e00, file src\module\base.py>, line 17)
              56 MAKE_FUNCTION        (default, annotation)
              58 STORE_NAME           (_list_videos)

238:          60 LOAD_CONST           ("video_id")
              62 LOAD_NAME            (str)
              64 LOAD_CONST           ("channel_id")
              66 LOAD_NAME            (str)
              68 LOAD_CONST           ("return")
              70 LOAD_NAME            (Video)
              72 BUILD_TUPLE          6
              74 LOAD_CONST           (<Code311 code object _get_video_info at 0x2e505863020, file src\module\base.py>, line 238)
              76 MAKE_FUNCTION        (annotation)
              78 STORE_NAME           (_get_video_info)

420:          80 LOAD_CONST           ("1.20260311.03.00")

421:          82 LOAD_CONST           ("en")

422:          84 LOAD_CONST           ("USER_INTERFACE_THEME_DARK")

423:          86 LOAD_CONST           (1920)

424:          88 LOAD_CONST           (945)

425:          90 LOAD_CONST           (True)

426:          92 LOAD_CONST           (None)

414:          94 LOAD_CONST           (('client_version', 'hl', 'theme', 'screen_width', 'screen_height', 'include_on_behalf_of_user', 'extra_request_fields'))
              96 BUILD_CONST_KEY_MAP  7
              98 LOAD_CONST           ("channel_id")

416:         100 LOAD_NAME            (str)

414:         102 LOAD_CONST           ("role")

417:         104 LOAD_NAME            (str)

414:         106 LOAD_CONST           ("delegated_session_id")

418:         108 LOAD_NAME            (str)

414:         110 LOAD_CONST           ("client_version")

420:         112 LOAD_NAME            (str)

414:         114 LOAD_CONST           ("hl")

421:         116 LOAD_NAME            (str)

414:         118 LOAD_CONST           ("theme")

422:         120 LOAD_NAME            (str)

414:         122 LOAD_CONST           ("screen_width")

423:         124 LOAD_NAME            (int)

414:         126 LOAD_CONST           ("screen_height")

424:         128 LOAD_NAME            (int)

414:         130 LOAD_CONST           ("include_on_behalf_of_user")

425:         132 LOAD_NAME            (bool)

414:         134 LOAD_CONST           ("extra_request_fields")

426:         136 LOAD_NAME            (dict)
             138 LOAD_CONST           (None)
             140 BINARY_OP            (|)

414:         144 LOAD_CONST           ("return")

427:         146 LOAD_NAME            (dict)

414:         148 BUILD_TUPLE          22
             150 LOAD_CONST           (<Code311 code object _build_context at 0x2e505862f10, file src\module\base.py>, line 414)
             152 MAKE_FUNCTION        (keyword-only, annotation)
             154 STORE_NAME           (_build_context)

468:         156 LOAD_CONST           ("return")
             158 LOAD_NAME            (str)
             160 BUILD_TUPLE          2
             162 LOAD_CONST           (<Code311 code object _get_session_token at 0x2e505863240, file src\module\base.py>, line 468)
             164 MAKE_FUNCTION        (annotation)
             166 STORE_NAME           (_get_session_token)
             168 RETURN_CONST         (None)


# Method Name:       _list_videos
# Filename:          src\module\base.py
# Argument count:    4
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  17
# Stack size:        16
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        17
# Constants:
#    0: None
#    1: '; '
#    2: 'name'
#    3: '='
#    4: 'value'
#    5: 'and'
#    6: 'operands'
#    7: 'channelIdIs'
#    8: 'or'
#    9: 'privacyIs'
#   10: 'not'
#   11: 'operand'
#   12: 'isDraft'
#   13: 'isScheduledToBePublic'
#   14: 'videoOriginIs'
#   15: 'VIDEO_ORIGIN_UPLOAD'
#   16: 'contentTypeIs'
#   17: 'CREATOR_CONTENT_TYPE_SHORTS'
#   18: 'tvfilmTypeIs'
#   19: 'VIDEO_TVFILM_TYPE_MOVIE'
#   20: 'VIDEO_TVFILM_TYPE_EPISODE'
#   21: 'VIDEO_TVFILM_TYPE_EVENT'
#   22: 'VIDEO_ORDER_DISPLAY_TIME_DESC'
#   23: 'channelId'
#   24: True
#   25: 'videoId'
#   26: 'lengthSeconds'
#   27: 'livestream'
#   28: 'all'
#   29: 'publicLivestream'
#   30: 'origin'
#   31: 'premiere'
#   32: 'publicPremiere'
#   33: 'status'
#   34: 'thumbnailDetails'
#   35: 'title'
#   36: 'draftStatus'
#   37: 'downloadUrl'
#   38: 'watchUrl'
#   39: 'shareUrl'
#   40: 'permissions'
#   41: 'features'
#   42: 'collaboration'
#   43: 'timeCreatedSeconds'
#   44: 'timePublishedSeconds'
#   45: 'privacy'
#   46: 'contentOwnershipModelSettings'
#   47: 'contentType'
#   48: 'publicShorts'
#   49: 'podcastRssMetadata'
#   50: 'videoLinkageShortsAttribution'
#   51: 'alteredContentSettings'
#   52: 'tvfilmMetadata'
#   53: 'videoCreatorExperiment'
#   54: 'responseStatus'
#   55: 'statusDetails'
#   56: 'description'
#   57: 'titleFormattedString'
#   58: 'descriptionDetails'
#   59: 'descriptionFormattedString'
#   60: 'titleDetails'
#   61: 'videoDurationMs'
#   62: 'publicMetrics'
#   63: 'audienceRestriction'
#   64: 'releaseInfo'
#   65: 'privateMetrics'
#   66: 'dislikeCount'
#   67: 'allRestrictions'
#   68: 'inlineEditProcessingStatus'
#   69: 'videoPrechecks'
#   70: 'shorts'
#   71: 'selfCertification'
#   72: 'videoStreamUrl'
#   73: 'thumbnailEditorState'
#   74: 'videoResolutions'
#   75: 'scheduledPublishingDetails'
#   76: 'visibility'
#   77: 'isSource'
#   78: ('privateShare', 'sponsorsOnly', 'unlistedExpired', 'videoTrailers', 'remix', 'isPaygated')
#   79: 62
#   80: '1.20250910.04.01'
#   81: 'vi'
#   82: 'VN'
#   83: ''
#   84: 420
#   85: 'USER_INTERFACE_THEME_DARK'
#   86: 2560
#   87: 578
#   88: 2
#   89: 1.5
#   90: ('clientName', 'clientVersion', 'hl', 'gl', 'experimentsToken', 'utcOffsetMinutes', 'userInterfaceTheme', 'screenWidthPoints', 'screenHeightPoints', 'screenPixelDensity', 'screenDensityFloat')
#   91: 'AQH2GtwBdPiAGJ2T8rGKWNAiZQVd_vf3vyyp2_FoLHT9dGCNih8CNaBwmazsAHXcXYwinRh-c35GmB1fvnAapWD1jXwQpZnFLpu81NzfUTeuNdFMKSTZfCxbEJYI'
#   92: 'token'
#   93: ('returnLogEntry', 'internalExperimentFlags', 'eats', 'sessionInfo', 'consistencyTokenJars')
#   94: 'channelRoleType'
#   95: ('externalChannelId', 'roleType')
#   96: ('onBehalfOfUser', 'delegationContext', 'serializedDelegationContext')
#   97: 'visualElement'
#   98: 'veType'
#   99: 31402
#  100: 'qplwEzmZ-f8Ac7kX'
#  101: ('client', 'request', 'user', 'clickTracking', 'clientScreenNonce')
#  102: ('filter', 'order', 'pageSize', 'mask', 'context')
#  103: 'https://studio.youtube.com'
#  104: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
#  105: 'application/json'
#  106: 'SAPISIDHASH '
#  107: ('origin', 'user-agent', 'cookie', 'content-type', 'authorization')
#  108: 'https://studio.youtube.com/youtubei/v1/creator/list_creator_videos?alt=json'
#  109: ('url', 'headers', 'json')
#  110: 'videos'
#  111: 'thumbnails'
#  112: 0
#  113: 'url'
#  114: ('id', 'title', 'description', 'channel_id', 'duration_ms', 'thumbnail')
# Names:
#    0: get_channels_info
#    1: join
#    2: cookies
#    3: sapisidhash
#    4: _get_session_token
#    5: id
#    6: value
#    7: delegated_session_id
#    8: role
#    9: requests
#   10: post
#   11: json
#   12: get
#   13: Video
#   14: append
# Varnames:
#	self, channel_id, video_type, limit, channel_info, cookie, cookie_string, sapisidhash, session_token, payload, headers, url, response, res, videos, item, video
# Positional arguments:
#	self, channel_id, video_type, limit
# Local variables:
#    4: channel_info
#    5: cookie
#    6: cookie_string
#    7: sapisidhash
#    8: session_token
#    9: payload
#   10: headers
#   11: url
#   12: response
#   13: res
#   14: videos
#   15: item
#   16: video

 17:           0 RESUME               0

 20:           2 LOAD_GLOBAL          (NULL + get_channels_info)
              12 LOAD_FAST            (channel_id)
              14 CALL                 1
              22 STORE_FAST           (channel_info)

 21:          24 LOAD_CONST           ("; ")
              26 LOAD_ATTR            (NULL|self + join)

 22:          46 LOAD_FAST            (channel_info)
              48 LOAD_ATTR            (cookies)
              68 GET_ITER
              70 LOAD_FAST_AND_CLEAR  (cookie)
              72 SWAP                 (TOS <-> TOS1)
              74 BUILD_LIST           0
              76 SWAP                 (TOS <-> TOS1)
              78 FOR_ITER             (to 112)
              82 STORE_FAST           (cookie)
              84 LOAD_FAST            (cookie)
              86 LOAD_CONST           ("name")
              88 BINARY_SUBSCR
              92 FORMAT_VALUE         0
              94 LOAD_CONST           ("=")
              96 LOAD_FAST            (cookie)
              98 LOAD_CONST           ("value")
             100 BINARY_SUBSCR
             104 FORMAT_VALUE         0
             106 BUILD_STRING         3
             108 LIST_APPEND          2
         >>  110 JUMP_BACKWARD        (to 78)
             112 END_FOR
             114 SWAP                 (TOS <-> TOS1)
             116 STORE_FAST           (cookie)

 21:         118 CALL                 1
             126 STORE_FAST           (cookie_string)

 24:         128 LOAD_FAST            (channel_info)
             130 LOAD_ATTR            (sapisidhash)
             150 STORE_FAST           (sapisidhash)

 25:         152 LOAD_FAST            (self)
             154 LOAD_ATTR            (NULL|self + _get_session_token)
             174 LOAD_FAST            (channel_info)
             176 CALL                 1
             184 STORE_FAST           (session_token)

 29:         186 LOAD_CONST           ("and")

 30:         188 LOAD_CONST           ("operands")

 31:         190 LOAD_CONST           ("channelIdIs")
             192 LOAD_CONST           ("value")
             194 LOAD_FAST            (channel_info)
             196 LOAD_ATTR            (id)
             216 BUILD_MAP            1
             218 BUILD_MAP            1

 33:         220 LOAD_CONST           ("and")

 34:         222 LOAD_CONST           ("operands")

 36:         224 LOAD_CONST           ("or")

 37:         226 LOAD_CONST           ("operands")

 39:         228 LOAD_CONST           ("and")

 40:         230 LOAD_CONST           ("operands")

 42:         232 LOAD_CONST           ("privacyIs")

 43:         234 LOAD_CONST           ("value")
             236 LOAD_FAST            (video_type)
             238 LOAD_ATTR            (value)

 42:         258 BUILD_MAP            1

 41:         260 BUILD_MAP            1

 47:         262 LOAD_CONST           ("not")

 48:         264 LOAD_CONST           ("operand")

 49:         266 LOAD_CONST           ("isDraft")
             268 BUILD_MAP            0

 48:         270 BUILD_MAP            1

 47:         272 BUILD_MAP            1

 46:         274 BUILD_MAP            1

 54:         276 LOAD_CONST           ("not")

 55:         278 LOAD_CONST           ("operand")

 56:         280 LOAD_CONST           ("isScheduledToBePublic")
             282 BUILD_MAP            0

 55:         284 BUILD_MAP            1

 54:         286 BUILD_MAP            1

 53:         288 BUILD_MAP            1

 40:         290 BUILD_LIST           3

 39:         292 BUILD_MAP            1

 38:         294 BUILD_MAP            1

 37:         296 BUILD_LIST           1

 36:         298 BUILD_MAP            1

 35:         300 BUILD_MAP            1

 67:         302 LOAD_CONST           ("and")

 68:         304 LOAD_CONST           ("operands")

 70:         306 LOAD_CONST           ("videoOriginIs")

 71:         308 LOAD_CONST           ("value")
             310 LOAD_CONST           ("VIDEO_ORIGIN_UPLOAD")

 70:         312 BUILD_MAP            1

 69:         314 BUILD_MAP            1

 75:         316 LOAD_CONST           ("not")

 76:         318 LOAD_CONST           ("operand")

 77:         320 LOAD_CONST           ("contentTypeIs")

 78:         322 LOAD_CONST           ("value")
             324 LOAD_CONST           ("CREATOR_CONTENT_TYPE_SHORTS")

 77:         326 BUILD_MAP            1

 76:         328 BUILD_MAP            1

 75:         330 BUILD_MAP            1

 74:         332 BUILD_MAP            1

 68:         334 BUILD_LIST           2

 67:         336 BUILD_MAP            1

 66:         338 BUILD_MAP            1

 87:         340 LOAD_CONST           ("not")

 88:         342 LOAD_CONST           ("operand")

 89:         344 LOAD_CONST           ("tvfilmTypeIs")

 90:         346 LOAD_CONST           ("value")
             348 LOAD_CONST           ("VIDEO_TVFILM_TYPE_MOVIE")

 89:         350 BUILD_MAP            1

 88:         352 BUILD_MAP            1

 87:         354 BUILD_MAP            1

 86:         356 BUILD_MAP            1

 96:         358 LOAD_CONST           ("not")

 97:         360 LOAD_CONST           ("operand")

 98:         362 LOAD_CONST           ("tvfilmTypeIs")

 99:         364 LOAD_CONST           ("value")
             366 LOAD_CONST           ("VIDEO_TVFILM_TYPE_EPISODE")

 98:         368 BUILD_MAP            1

 97:         370 BUILD_MAP            1

 96:         372 BUILD_MAP            1

 95:         374 BUILD_MAP            1

105:         376 LOAD_CONST           ("not")

106:         378 LOAD_CONST           ("operand")

107:         380 LOAD_CONST           ("tvfilmTypeIs")

108:         382 LOAD_CONST           ("value")
             384 LOAD_CONST           ("VIDEO_TVFILM_TYPE_EVENT")

107:         386 BUILD_MAP            1

106:         388 BUILD_MAP            1

105:         390 BUILD_MAP            1

104:         392 BUILD_MAP            1

 34:         394 BUILD_LIST           5

 33:         396 BUILD_MAP            1

 32:         398 BUILD_MAP            1

 30:         400 BUILD_LIST           2

 29:         402 BUILD_MAP            1

 28:         404 BUILD_MAP            1

119:         406 LOAD_CONST           ("VIDEO_ORDER_DISPLAY_TIME_DESC")

120:         408 LOAD_FAST            (limit)

121:         410 BUILD_MAP            0

122:         412 LOAD_CONST           ("channelId")
             414 LOAD_CONST           (True)

121:         416 MAP_ADD              1

123:         418 LOAD_CONST           ("videoId")
             420 LOAD_CONST           (True)

121:         422 MAP_ADD              1

124:         424 LOAD_CONST           ("lengthSeconds")
             426 LOAD_CONST           (True)

121:         428 MAP_ADD              1

125:         430 LOAD_CONST           ("livestream")
             432 LOAD_CONST           ("all")
             434 LOAD_CONST           (True)
             436 BUILD_MAP            1

121:         438 MAP_ADD              1

126:         440 LOAD_CONST           ("publicLivestream")
             442 LOAD_CONST           ("all")
             444 LOAD_CONST           (True)
             446 BUILD_MAP            1

121:         448 MAP_ADD              1

127:         450 LOAD_CONST           ("origin")
             452 LOAD_CONST           (True)

121:         454 MAP_ADD              1

128:         456 LOAD_CONST           ("premiere")
             458 LOAD_CONST           ("all")
             460 LOAD_CONST           (True)
             462 BUILD_MAP            1

121:         464 MAP_ADD              1

129:         466 LOAD_CONST           ("publicPremiere")
             468 LOAD_CONST           ("all")
             470 LOAD_CONST           (True)
             472 BUILD_MAP            1

121:         474 MAP_ADD              1

130:         476 LOAD_CONST           ("status")
             478 LOAD_CONST           (True)

121:         480 MAP_ADD              1

131:         482 LOAD_CONST           ("thumbnailDetails")
             484 LOAD_CONST           ("all")
             486 LOAD_CONST           (True)
             488 BUILD_MAP            1

121:         490 MAP_ADD              1

132:         492 LOAD_CONST           ("title")
             494 LOAD_CONST           (True)

121:         496 MAP_ADD              1

133:         498 LOAD_CONST           ("draftStatus")
             500 LOAD_CONST           (True)

121:         502 MAP_ADD              1

134:         504 LOAD_CONST           ("downloadUrl")
             506 LOAD_CONST           (True)

121:         508 MAP_ADD              1

135:         510 LOAD_CONST           ("watchUrl")
             512 LOAD_CONST           (True)

121:         514 MAP_ADD              1

136:         516 LOAD_CONST           ("shareUrl")
             518 LOAD_CONST           (True)

121:         520 MAP_ADD              1

137:         522 LOAD_CONST           ("permissions")
             524 LOAD_CONST           ("all")
             526 LOAD_CONST           (True)
             528 BUILD_MAP            1

121:         530 MAP_ADD              1

138:         532 LOAD_CONST           ("features")
             534 LOAD_CONST           ("all")
             536 LOAD_CONST           (True)
             538 BUILD_MAP            1

121:         540 MAP_ADD              1
             542 BUILD_MAP            0

139:         544 LOAD_CONST           ("collaboration")
             546 LOAD_CONST           ("all")
             548 LOAD_CONST           (True)
             550 BUILD_MAP            1

121:         552 MAP_ADD              1

140:         554 LOAD_CONST           ("timeCreatedSeconds")
             556 LOAD_CONST           (True)

121:         558 MAP_ADD              1

141:         560 LOAD_CONST           ("timePublishedSeconds")
             562 LOAD_CONST           (True)

121:         564 MAP_ADD              1

142:         566 LOAD_CONST           ("privacy")
             568 LOAD_CONST           (True)

121:         570 MAP_ADD              1

143:         572 LOAD_CONST           ("contentOwnershipModelSettings")
             574 LOAD_CONST           ("all")
             576 LOAD_CONST           (True)
             578 BUILD_MAP            1

121:         580 MAP_ADD              1

144:         582 LOAD_CONST           ("contentType")
             584 LOAD_CONST           (True)

121:         586 MAP_ADD              1

145:         588 LOAD_CONST           ("publicShorts")
             590 LOAD_CONST           ("all")
             592 LOAD_CONST           (True)
             594 BUILD_MAP            1

121:         596 MAP_ADD              1

146:         598 LOAD_CONST           ("podcastRssMetadata")
             600 LOAD_CONST           ("all")
             602 LOAD_CONST           (True)
             604 BUILD_MAP            1

121:         606 MAP_ADD              1

147:         608 LOAD_CONST           ("videoLinkageShortsAttribution")
             610 LOAD_CONST           ("all")
             612 LOAD_CONST           (True)
             614 BUILD_MAP            1

121:         616 MAP_ADD              1

148:         618 LOAD_CONST           ("alteredContentSettings")
             620 LOAD_CONST           ("all")
             622 LOAD_CONST           (True)
             624 BUILD_MAP            1

121:         626 MAP_ADD              1

149:         628 LOAD_CONST           ("tvfilmMetadata")
             630 LOAD_CONST           ("all")
             632 LOAD_CONST           (True)
             634 BUILD_MAP            1

121:         636 MAP_ADD              1

150:         638 LOAD_CONST           ("videoCreatorExperiment")
             640 LOAD_CONST           ("all")
             642 LOAD_CONST           (True)
             644 BUILD_MAP            1

121:         646 MAP_ADD              1

151:         648 LOAD_CONST           ("responseStatus")
             650 LOAD_CONST           ("all")
             652 LOAD_CONST           (True)
             654 BUILD_MAP            1

121:         656 MAP_ADD              1

152:         658 LOAD_CONST           ("statusDetails")
             660 LOAD_CONST           ("all")
             662 LOAD_CONST           (True)
             664 BUILD_MAP            1

121:         666 MAP_ADD              1

153:         668 LOAD_CONST           ("description")
             670 LOAD_CONST           (True)

121:         672 MAP_ADD              1

154:         674 LOAD_CONST           ("titleFormattedString")
             676 LOAD_CONST           ("all")
             678 LOAD_CONST           (True)
             680 BUILD_MAP            1

121:         682 MAP_ADD              1

155:         684 LOAD_CONST           ("descriptionDetails")
             686 LOAD_CONST           ("all")
             688 LOAD_CONST           (True)
             690 BUILD_MAP            1

121:         692 MAP_ADD              1
             694 DICT_UPDATE          1
             696 BUILD_MAP            0

156:         698 LOAD_CONST           ("descriptionFormattedString")
             700 LOAD_CONST           ("all")
             702 LOAD_CONST           (True)
             704 BUILD_MAP            1

121:         706 MAP_ADD              1

157:         708 LOAD_CONST           ("titleDetails")
             710 LOAD_CONST           ("all")
             712 LOAD_CONST           (True)
             714 BUILD_MAP            1

121:         716 MAP_ADD              1

158:         718 LOAD_CONST           ("videoDurationMs")
             720 LOAD_CONST           (True)

121:         722 MAP_ADD              1

159:         724 LOAD_CONST           ("publicMetrics")
             726 LOAD_CONST           ("all")
             728 LOAD_CONST           (True)
             730 BUILD_MAP            1

121:         732 MAP_ADD              1

160:         734 LOAD_CONST           ("audienceRestriction")
             736 LOAD_CONST           ("all")
             738 LOAD_CONST           (True)
             740 BUILD_MAP            1

121:         742 MAP_ADD              1

161:         744 LOAD_CONST           ("releaseInfo")
             746 LOAD_CONST           ("all")
             748 LOAD_CONST           (True)
             750 BUILD_MAP            1

121:         752 MAP_ADD              1

162:         754 LOAD_CONST           ("privateMetrics")
             756 LOAD_CONST           ("dislikeCount")
             758 LOAD_CONST           (True)
             760 BUILD_MAP            1

121:         762 MAP_ADD              1

163:         764 LOAD_CONST           ("allRestrictions")
             766 LOAD_CONST           ("all")
             768 LOAD_CONST           (True)
             770 BUILD_MAP            1

121:         772 MAP_ADD              1

164:         774 LOAD_CONST           ("inlineEditProcessingStatus")
             776 LOAD_CONST           (True)

121:         778 MAP_ADD              1

165:         780 LOAD_CONST           ("videoPrechecks")
             782 LOAD_CONST           ("all")
             784 LOAD_CONST           (True)
             786 BUILD_MAP            1

121:         788 MAP_ADD              1

166:         790 LOAD_CONST           ("shorts")
             792 LOAD_CONST           ("all")
             794 LOAD_CONST           (True)
             796 BUILD_MAP            1

121:         798 MAP_ADD              1

167:         800 LOAD_CONST           ("selfCertification")
             802 LOAD_CONST           ("all")
             804 LOAD_CONST           (True)
             806 BUILD_MAP            1

121:         808 MAP_ADD              1

168:         810 LOAD_CONST           ("videoStreamUrl")
             812 LOAD_CONST           (True)

121:         814 MAP_ADD              1

169:         816 LOAD_CONST           ("thumbnailEditorState")
             818 LOAD_CONST           ("all")
             820 LOAD_CONST           (True)
             822 BUILD_MAP            1

121:         824 MAP_ADD              1

170:         826 LOAD_CONST           ("videoResolutions")
             828 LOAD_CONST           ("all")
             830 LOAD_CONST           (True)
             832 BUILD_MAP            1

121:         834 MAP_ADD              1

171:         836 LOAD_CONST           ("scheduledPublishingDetails")
             838 LOAD_CONST           ("all")
             840 LOAD_CONST           (True)
             842 BUILD_MAP            1

121:         844 MAP_ADD              1

172:         846 LOAD_CONST           ("visibility")
             848 LOAD_CONST           ("all")
             850 LOAD_CONST           (True)
             852 BUILD_MAP            1

121:         854 MAP_ADD              1
             856 DICT_UPDATE          1

173:         858 LOAD_CONST           ("all")
             860 LOAD_CONST           (True)
             862 BUILD_MAP            1

174:         864 LOAD_CONST           ("all")
             866 LOAD_CONST           (True)
             868 BUILD_MAP            1

175:         870 LOAD_CONST           (True)

176:         872 LOAD_CONST           ("all")
             874 LOAD_CONST           (True)
             876 BUILD_MAP            1

177:         878 LOAD_CONST           ("isSource")
             880 LOAD_CONST           (True)
             882 BUILD_MAP            1

178:         884 LOAD_CONST           (True)

121:         886 LOAD_CONST           (('privateShare', 'sponsorsOnly', 'unlistedExpired', 'videoTrailers', 'remix', 'isPaygated'))
             888 BUILD_CONST_KEY_MAP  6
             890 DICT_UPDATE          1

182:         892 LOAD_CONST           (62)

183:         894 LOAD_CONST           ("1.20250910.04.01")

184:         896 LOAD_CONST           ("vi")

185:         898 LOAD_CONST           ("VN")

186:         900 LOAD_CONST           ("")

187:         902 LOAD_CONST           (420)

188:         904 LOAD_CONST           ("USER_INTERFACE_THEME_DARK")

189:         906 LOAD_CONST           (2560)

190:         908 LOAD_CONST           (578)

191:         910 LOAD_CONST           (2)

192:         912 LOAD_CONST           (1.5)

181:         914 LOAD_CONST           (('clientName', 'clientVersion', 'hl', 'gl', 'experimentsToken', 'utcOffsetMinutes', 'userInterfaceTheme', 'screenWidthPoints', 'screenHeightPoints', 'screenPixelDensity', 'screenDensityFloat'))
             916 BUILD_CONST_KEY_MAP  11

195:         918 LOAD_CONST           (True)

196:         920 BUILD_LIST           0

197:         922 LOAD_CONST           ("AQH2GtwBdPiAGJ2T8rGKWNAiZQVd_vf3vyyp2_FoLHT9dGCNih8CNaBwmazsAHXcXYwinRh-c35GmB1fvnAapWD1jXwQpZnFLpu81NzfUTeuNdFMKSTZfCxbEJYI")

198:         924 LOAD_CONST           ("token")
             926 LOAD_FAST            (session_token)
             928 BUILD_MAP            1

199:         930 BUILD_LIST           0

194:         932 LOAD_CONST           (('returnLogEntry', 'internalExperimentFlags', 'eats', 'sessionInfo', 'consistencyTokenJars'))
             934 BUILD_CONST_KEY_MAP  5

202:         936 LOAD_FAST            (channel_info)
             938 LOAD_ATTR            (delegated_session_id)

204:         958 LOAD_FAST            (channel_info)
             960 LOAD_ATTR            (id)

205:         980 LOAD_CONST           ("channelRoleType")
             982 LOAD_FAST            (channel_info)
             984 LOAD_ATTR            (role)
            1004 BUILD_MAP            1

203:        1006 LOAD_CONST           (('externalChannelId', 'roleType'))
            1008 BUILD_CONST_KEY_MAP  2

207:        1010 LOAD_CONST           ("")

201:        1012 LOAD_CONST           (('onBehalfOfUser', 'delegationContext', 'serializedDelegationContext'))
            1014 BUILD_CONST_KEY_MAP  3

209:        1016 LOAD_CONST           ("visualElement")
            1018 LOAD_CONST           ("veType")
            1020 LOAD_CONST           (31402)
            1022 BUILD_MAP            1
            1024 BUILD_MAP            1

210:        1026 LOAD_CONST           ("qplwEzmZ-f8Ac7kX")

180:        1028 LOAD_CONST           (('client', 'request', 'user', 'clickTracking', 'clientScreenNonce'))
            1030 BUILD_CONST_KEY_MAP  5

 27:        1032 LOAD_CONST           (('filter', 'order', 'pageSize', 'mask', 'context'))
            1034 BUILD_CONST_KEY_MAP  5
            1036 STORE_FAST           (payload)

215:        1038 LOAD_CONST           ("https://studio.youtube.com")

216:        1040 LOAD_CONST           ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

217:        1042 LOAD_FAST            (cookie_string)

218:        1044 LOAD_CONST           ("application/json")

219:        1046 LOAD_CONST           ("SAPISIDHASH ")
            1048 LOAD_FAST            (sapisidhash)
            1050 FORMAT_VALUE         0
            1052 BUILD_STRING         2

214:        1054 LOAD_CONST           (('origin', 'user-agent', 'cookie', 'content-type', 'authorization'))
            1056 BUILD_CONST_KEY_MAP  5
            1058 STORE_FAST           (headers)

221:        1060 LOAD_CONST           ("https://studio.youtube.com/youtubei/v1/creator/list_creator_videos?alt=json")
            1062 STORE_FAST           (url)

222:        1064 LOAD_GLOBAL          (NULL + requests)
            1074 LOAD_ATTR            (post)
            1094 LOAD_FAST            (url)
            1096 LOAD_FAST            (headers)
            1098 LOAD_FAST            (payload)
            1100 KW_NAMES             (('url', 'headers', 'json'))
            1102 CALL                 3
            1110 STORE_FAST           (response)

223:        1112 LOAD_FAST            (response)
            1114 LOAD_ATTR            (NULL|self + json)
            1134 CALL                 0
            1142 STORE_FAST           (res)

224:        1144 BUILD_LIST           0
            1146 STORE_FAST           (videos)

226:        1148 LOAD_FAST            (res)
            1150 LOAD_ATTR            (NULL|self + get)
            1170 LOAD_CONST           ("videos")
            1172 BUILD_LIST           0
            1174 CALL                 2
            1182 GET_ITER
            1184 FOR_ITER             (to 1314)
            1188 STORE_FAST           (item)

227:        1190 LOAD_GLOBAL          (NULL + Video)

228:        1200 LOAD_FAST            (item)
            1202 LOAD_CONST           ("videoId")
            1204 BINARY_SUBSCR

229:        1208 LOAD_FAST            (item)
            1210 LOAD_CONST           ("title")
            1212 BINARY_SUBSCR

230:        1216 LOAD_FAST            (item)
            1218 LOAD_CONST           ("description")
            1220 BINARY_SUBSCR

231:        1224 LOAD_FAST            (item)
            1226 LOAD_CONST           ("channelId")
            1228 BINARY_SUBSCR

232:        1232 LOAD_FAST            (item)
            1234 LOAD_CONST           ("videoDurationMs")
            1236 BINARY_SUBSCR

233:        1240 LOAD_FAST            (item)
            1242 LOAD_CONST           ("thumbnailDetails")
            1244 BINARY_SUBSCR
            1248 LOAD_CONST           ("thumbnails")
            1250 BINARY_SUBSCR
            1254 LOAD_CONST           (0)
            1256 BINARY_SUBSCR
            1260 LOAD_CONST           ("url")
            1262 BINARY_SUBSCR

227:        1266 KW_NAMES             (('id', 'title', 'description', 'channel_id', 'duration_ms', 'thumbnail'))
            1268 CALL                 6
            1276 STORE_FAST           (video)

235:        1278 LOAD_FAST            (videos)
            1280 LOAD_ATTR            (NULL|self + append)
            1300 LOAD_FAST            (video)
            1302 CALL                 1
            1310 POP_TOP
         >> 1312 JUMP_BACKWARD        (to 1184)

226:        1314 END_FOR

236:        1316 LOAD_FAST            (videos)
            1318 RETURN_VALUE
            1320 SWAP                 (TOS <-> TOS1)
            1322 POP_TOP

 22:        1324 SWAP                 (TOS <-> TOS1)
            1326 STORE_FAST           (cookie)
            1328 RERAISE              0

ExceptionTable:
  74 to 112 -> 1320 [4]

# Method Name:       _get_video_info
# Filename:          src\module\base.py
# Argument count:    3
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  13
# Stack size:        12
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        238
# Constants:
#    0: None
#    1: '; '
#    2: 'name'
#    3: '='
#    4: 'value'
#    5: 'https://studio.youtube.com/youtubei/v1/creator/get_creator_videos?alt=json'
#    6: 'https://studio.youtube.com'
#    7: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
#    8: 'application/json'
#    9: 'SAPISIDHASH '
#   10: ('origin', 'user-agent', 'cookie', 'content-type', 'authorization')
#   11: 62
#   12: '1.20250905.02.00'
#   13: 'vi'
#   14: 'VN'
#   15: ''
#   16: 420
#   17: 'USER_INTERFACE_THEME_DARK'
#   18: 2560
#   19: 544
#   20: 2
#   21: 1.5
#   22: ('clientName', 'clientVersion', 'hl', 'gl', 'experimentsToken', 'utcOffsetMinutes', 'userInterfaceTheme', 'screenWidthPoints', 'screenHeightPoints', 'screenPixelDensity', 'screenDensityFloat')
#   23: True
#   24: 'AWSNWa2q-ubSn35ywNe6Myhvveym5w_4-S_D3p_lk689PZciFEJrTquCWvtc1PgiFObkpeU638J5M3CTcvCmegVUfkseMdAJaVgmOWE_S5SHQpzuXaZu1I7szwPPUQ=='
#   25: 'token'
#   26: ('returnLogEntry', 'internalExperimentFlags', 'eats', 'sessionInfo', 'consistencyTokenJars')
#   27: 'channelRoleType'
#   28: ('externalChannelId', 'roleType')
#   29: ('onBehalfOfUser', 'delegationContext', 'serializedDelegationContext')
#   30: 'visualElement'
#   31: 'veType'
#   32: 74615
#   33: 'rQg33g-jDrOyosOi'
#   34: ('client', 'request', 'user', 'clickTracking', 'clientScreenNonce')
#   35: 'channelId'
#   36: 'downloadUrl'
#   37: 'origin'
#   38: 'premiere'
#   39: 'all'
#   40: 'privacy'
#   41: 'videoId'
#   42: 'title'
#   43: 'titleDetails'
#   44: 'description'
#   45: 'descriptionDetails'
#   46: 'releaseInfo'
#   47: 'podcastRssMetadata'
#   48: 'status'
#   49: 'permissions'
#   50: 'draftStatus'
#   51: 'features'
#   52: 'livestream'
#   53: 'videoDurationMs'
#   54: 'statusDetails'
#   55: 'inlineEditProcessingStatus'
#   56: 'monetization'
#   57: 'allRestrictions'
#   58: 'videoPrechecks'
#   59: 'audienceRestriction'
#   60: 'mfkSettings'
#   61: 'selfCertification'
#   62: 'videoStreamUrl'
#   63: 'visibility'
#   64: 'shorts'
#   65: 'responseStatus'
#   66: 'contentType'
#   67: 'videoAdvertiserSpecificAgeGates'
#   68: 'claimDetails'
#   69: 'commentsDisabledInternally'
#   70: 'music'
#   71: 'ownedClaimDetails'
#   72: 'timePublishedSeconds'
#   73: 'uncaptionedReason'
#   74: 'remix'
#   75: 'contentOwnershipModelSettings'
#   76: 'googleAdsVideoLinks'
#   77: 'dubSettings'
#   78: 'alteredContentSettings'
#   79: 'collaboration'
#   80: 'thumbnailEditorState'
#   81: 'thumbnailDetails'
#   82: 'videoCreatorExperiment'
#   83: 'lengthSeconds'
#   84: 'publicLivestream'
#   85: 'publicPremiere'
#   86: 'tvfilmMetadata'
#   87: 'shareUrl'
#   88: 'scheduledPublishingDetails'
#   89: 'privateShare'
#   90: 'sponsorsOnly'
#   91: 'unlistedExpired'
#   92: 'videoTrailers'
#   93: 'isPaygated'
#   94: 'suggestions'
#   95: 'tvType'
#   96: 'genres'
#   97: 'episode'
#   98: 'copyrightSummary'
#   99: 'productSelection'
#  100: 'productAutotaggingSettings'
#  101: 'videoLinkageShortsAttribution'
#  102: 'allowEmbed'
#  103: 'allowRatings'
#  104: 'ageRestriction'
#  105: 'audioLanguage'
#  106: 'category'
#  107: 'commentFilter'
#  108: 'commentSettings'
#  109: 'crowdsourcingEnabled'
#  110: 'dateRecorded'
#  111: 'defaultCommentSortOrder'
#  112: 'descriptionFormattedString'
#  113: 'gameTitle'
#  114: 'license'
#  115: 'liveChat'
#  116: 'location'
#  117: 'metadataLanguage'
#  118: 'paidProductPlacement'
#  119: 'paidPoliticalContent'
#  120: 'publishing'
#  121: 'tags'
#  122: 'titleFormattedString'
#  123: 'viewCountIsHidden'
#  124: 'autoChapterSettings'
#  125: 'autoPlacesMentionedSettings'
#  126: 'videoArtworkEditorState'
#  127: 'learningConceptSettings'
#  128: 'videoEditorProject'
#  129: 'originalFilename'
#  130: 'timeCreatedSeconds'
#  131: 'videoResolutions'
#  132: 'watchUrl'
#  133: 'publicShorts'
#  134: 'publicMetrics'
#  135: 'academicLearning'
#  136: 'manualPlacesMentionedPlaces'
#  137: 'autoProductsSettings'
#  138: ('videoAutoSummarySettings', 'issues')
#  139: False
#  140: ('context', 'failOnError', 'videoIds', 'mask', 'criticalRead')
#  141: ('url', 'headers', 'json')
#  142: 'videos'
#  143: 0
#  144: 'thumbnails'
#  145: 'url'
#  146: ('id', 'title', 'description', 'channel_id', 'duration_ms', 'thumbnail', 'video_status')
# Names:
#    0: get_channels_info
#    1: join
#    2: cookies
#    3: sapisidhash
#    4: _get_session_token
#    5: delegated_session_id
#    6: id
#    7: role
#    8: requests
#    9: post
#   10: json
#   11: Video
#   12: get
# Varnames:
#	self, video_id, channel_id, channel_info, cookie, cookie_string, sapisidhash, session_token, url, headers, payload, response, res
# Positional arguments:
#	self, video_id, channel_id
# Local variables:
#    3: channel_info
#    4: cookie
#    5: cookie_string
#    6: sapisidhash
#    7: session_token
#    8: url
#    9: headers
#   10: payload
#   11: response
#   12: res

238:           0 RESUME               0

239:           2 LOAD_GLOBAL          (NULL + get_channels_info)
              12 LOAD_FAST            (channel_id)
              14 CALL                 1
              22 STORE_FAST           (channel_info)

240:          24 LOAD_CONST           ("; ")
              26 LOAD_ATTR            (NULL|self + join)

241:          46 LOAD_FAST            (channel_info)
              48 LOAD_ATTR            (cookies)
              68 GET_ITER
              70 LOAD_FAST_AND_CLEAR  (cookie)
              72 SWAP                 (TOS <-> TOS1)
              74 BUILD_LIST           0
              76 SWAP                 (TOS <-> TOS1)
              78 FOR_ITER             (to 112)
              82 STORE_FAST           (cookie)
              84 LOAD_FAST            (cookie)
              86 LOAD_CONST           ("name")
              88 BINARY_SUBSCR
              92 FORMAT_VALUE         0
              94 LOAD_CONST           ("=")
              96 LOAD_FAST            (cookie)
              98 LOAD_CONST           ("value")
             100 BINARY_SUBSCR
             104 FORMAT_VALUE         0
             106 BUILD_STRING         3
             108 LIST_APPEND          2
         >>  110 JUMP_BACKWARD        (to 78)
             112 END_FOR
             114 SWAP                 (TOS <-> TOS1)
             116 STORE_FAST           (cookie)

240:         118 CALL                 1
             126 STORE_FAST           (cookie_string)

243:         128 LOAD_FAST            (channel_info)
             130 LOAD_ATTR            (sapisidhash)
             150 STORE_FAST           (sapisidhash)

244:         152 LOAD_FAST            (self)
             154 LOAD_ATTR            (NULL|self + _get_session_token)
             174 LOAD_FAST            (channel_info)
             176 CALL                 1
             184 STORE_FAST           (session_token)

246:         186 LOAD_CONST           ("https://studio.youtube.com/youtubei/v1/creator/get_creator_videos?alt=json")

245:         188 STORE_FAST           (url)

249:         190 LOAD_CONST           ("https://studio.youtube.com")

250:         192 LOAD_CONST           ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

251:         194 LOAD_FAST            (cookie_string)

252:         196 LOAD_CONST           ("application/json")

253:         198 LOAD_CONST           ("SAPISIDHASH ")
             200 LOAD_FAST            (sapisidhash)
             202 FORMAT_VALUE         0
             204 BUILD_STRING         2

248:         206 LOAD_CONST           (('origin', 'user-agent', 'cookie', 'content-type', 'authorization'))
             208 BUILD_CONST_KEY_MAP  5
             210 STORE_FAST           (headers)

258:         212 LOAD_CONST           (62)

259:         214 LOAD_CONST           ("1.20250905.02.00")

260:         216 LOAD_CONST           ("vi")

261:         218 LOAD_CONST           ("VN")

262:         220 LOAD_CONST           ("")

263:         222 LOAD_CONST           (420)

264:         224 LOAD_CONST           ("USER_INTERFACE_THEME_DARK")

265:         226 LOAD_CONST           (2560)

266:         228 LOAD_CONST           (544)

267:         230 LOAD_CONST           (2)

268:         232 LOAD_CONST           (1.5)

257:         234 LOAD_CONST           (('clientName', 'clientVersion', 'hl', 'gl', 'experimentsToken', 'utcOffsetMinutes', 'userInterfaceTheme', 'screenWidthPoints', 'screenHeightPoints', 'screenPixelDensity', 'screenDensityFloat'))
             236 BUILD_CONST_KEY_MAP  11

271:         238 LOAD_CONST           (True)

272:         240 BUILD_LIST           0

273:         242 LOAD_CONST           ("AWSNWa2q-ubSn35ywNe6Myhvveym5w_4-S_D3p_lk689PZciFEJrTquCWvtc1PgiFObkpeU638J5M3CTcvCmegVUfkseMdAJaVgmOWE_S5SHQpzuXaZu1I7szwPPUQ==")

274:         244 LOAD_CONST           ("token")
             246 LOAD_FAST            (session_token)
             248 BUILD_MAP            1

275:         250 BUILD_LIST           0

270:         252 LOAD_CONST           (('returnLogEntry', 'internalExperimentFlags', 'eats', 'sessionInfo', 'consistencyTokenJars'))
             254 BUILD_CONST_KEY_MAP  5

278:         256 LOAD_FAST            (channel_info)
             258 LOAD_ATTR            (delegated_session_id)

280:         278 LOAD_FAST            (channel_info)
             280 LOAD_ATTR            (id)

281:         300 LOAD_CONST           ("channelRoleType")
             302 LOAD_FAST            (channel_info)
             304 LOAD_ATTR            (role)
             324 BUILD_MAP            1

279:         326 LOAD_CONST           (('externalChannelId', 'roleType'))
             328 BUILD_CONST_KEY_MAP  2

283:         330 LOAD_CONST           ("")

277:         332 LOAD_CONST           (('onBehalfOfUser', 'delegationContext', 'serializedDelegationContext'))
             334 BUILD_CONST_KEY_MAP  3

285:         336 LOAD_CONST           ("visualElement")
             338 LOAD_CONST           ("veType")
             340 LOAD_CONST           (74615)
             342 BUILD_MAP            1
             344 BUILD_MAP            1

286:         346 LOAD_CONST           ("rQg33g-jDrOyosOi")

256:         348 LOAD_CONST           (('client', 'request', 'user', 'clickTracking', 'clientScreenNonce'))
             350 BUILD_CONST_KEY_MAP  5

288:         352 LOAD_CONST           (True)

289:         354 LOAD_FAST            (video_id)
             356 BUILD_LIST           1

290:         358 BUILD_MAP            0

291:         360 LOAD_CONST           ("channelId")
             362 LOAD_CONST           (True)

290:         364 MAP_ADD              1

292:         366 LOAD_CONST           ("downloadUrl")
             368 LOAD_CONST           (True)

290:         370 MAP_ADD              1

293:         372 LOAD_CONST           ("origin")
             374 LOAD_CONST           (True)

290:         376 MAP_ADD              1

294:         378 LOAD_CONST           ("premiere")
             380 LOAD_CONST           ("all")
             382 LOAD_CONST           (True)
             384 BUILD_MAP            1

290:         386 MAP_ADD              1

295:         388 LOAD_CONST           ("privacy")
             390 LOAD_CONST           (True)

290:         392 MAP_ADD              1

296:         394 LOAD_CONST           ("videoId")
             396 LOAD_CONST           (True)

290:         398 MAP_ADD              1

297:         400 LOAD_CONST           ("title")
             402 LOAD_CONST           (True)

290:         404 MAP_ADD              1

298:         406 LOAD_CONST           ("titleDetails")
             408 LOAD_CONST           ("all")
             410 LOAD_CONST           (True)
             412 BUILD_MAP            1

290:         414 MAP_ADD              1

299:         416 LOAD_CONST           ("description")
             418 LOAD_CONST           (True)

290:         420 MAP_ADD              1

300:         422 LOAD_CONST           ("descriptionDetails")
             424 LOAD_CONST           ("all")
             426 LOAD_CONST           (True)
             428 BUILD_MAP            1

290:         430 MAP_ADD              1

301:         432 LOAD_CONST           ("releaseInfo")
             434 LOAD_CONST           ("all")
             436 LOAD_CONST           (True)
             438 BUILD_MAP            1

290:         440 MAP_ADD              1

302:         442 LOAD_CONST           ("podcastRssMetadata")
             444 LOAD_CONST           ("all")
             446 LOAD_CONST           (True)
             448 BUILD_MAP            1

290:         450 MAP_ADD              1

303:         452 LOAD_CONST           ("status")
             454 LOAD_CONST           (True)

290:         456 MAP_ADD              1

304:         458 LOAD_CONST           ("permissions")
             460 LOAD_CONST           ("all")
             462 LOAD_CONST           (True)
             464 BUILD_MAP            1

290:         466 MAP_ADD              1

305:         468 LOAD_CONST           ("draftStatus")
             470 LOAD_CONST           (True)

290:         472 MAP_ADD              1

306:         474 LOAD_CONST           ("features")
             476 LOAD_CONST           ("all")
             478 LOAD_CONST           (True)
             480 BUILD_MAP            1

290:         482 MAP_ADD              1

307:         484 LOAD_CONST           ("livestream")
             486 LOAD_CONST           ("all")
             488 LOAD_CONST           (True)
             490 BUILD_MAP            1

290:         492 MAP_ADD              1
             494 BUILD_MAP            0

308:         496 LOAD_CONST           ("videoDurationMs")
             498 LOAD_CONST           (True)

290:         500 MAP_ADD              1

309:         502 LOAD_CONST           ("statusDetails")
             504 LOAD_CONST           ("all")
             506 LOAD_CONST           (True)
             508 BUILD_MAP            1

290:         510 MAP_ADD              1

310:         512 LOAD_CONST           ("inlineEditProcessingStatus")
             514 LOAD_CONST           (True)

290:         516 MAP_ADD              1

311:         518 LOAD_CONST           ("monetization")
             520 LOAD_CONST           ("all")
             522 LOAD_CONST           (True)
             524 BUILD_MAP            1

290:         526 MAP_ADD              1

312:         528 LOAD_CONST           ("allRestrictions")
             530 LOAD_CONST           ("all")
             532 LOAD_CONST           (True)
             534 BUILD_MAP            1

290:         536 MAP_ADD              1

313:         538 LOAD_CONST           ("videoPrechecks")
             540 LOAD_CONST           ("all")
             542 LOAD_CONST           (True)
             544 BUILD_MAP            1

290:         546 MAP_ADD              1

314:         548 LOAD_CONST           ("audienceRestriction")
             550 LOAD_CONST           ("all")
             552 LOAD_CONST           (True)
             554 BUILD_MAP            1

290:         556 MAP_ADD              1

315:         558 LOAD_CONST           ("mfkSettings")
             560 LOAD_CONST           ("all")
             562 LOAD_CONST           (True)
             564 BUILD_MAP            1

290:         566 MAP_ADD              1

316:         568 LOAD_CONST           ("selfCertification")
             570 LOAD_CONST           ("all")
             572 LOAD_CONST           (True)
             574 BUILD_MAP            1

290:         576 MAP_ADD              1

317:         578 LOAD_CONST           ("videoStreamUrl")
             580 LOAD_CONST           (True)

290:         582 MAP_ADD              1

318:         584 LOAD_CONST           ("visibility")
             586 LOAD_CONST           ("all")
             588 LOAD_CONST           (True)
             590 BUILD_MAP            1

290:         592 MAP_ADD              1

319:         594 LOAD_CONST           ("shorts")
             596 LOAD_CONST           ("all")
             598 LOAD_CONST           (True)
             600 BUILD_MAP            1

290:         602 MAP_ADD              1

320:         604 LOAD_CONST           ("responseStatus")
             606 LOAD_CONST           ("all")
             608 LOAD_CONST           (True)
             610 BUILD_MAP            1

290:         612 MAP_ADD              1

321:         614 LOAD_CONST           ("contentType")
             616 LOAD_CONST           (True)

290:         618 MAP_ADD              1

322:         620 LOAD_CONST           ("videoAdvertiserSpecificAgeGates")
             622 LOAD_CONST           ("all")
             624 LOAD_CONST           (True)
             626 BUILD_MAP            1

290:         628 MAP_ADD              1

323:         630 LOAD_CONST           ("claimDetails")
             632 LOAD_CONST           ("all")
             634 LOAD_CONST           (True)
             636 BUILD_MAP            1

290:         638 MAP_ADD              1

324:         640 LOAD_CONST           ("commentsDisabledInternally")
             642 LOAD_CONST           (True)

290:         644 MAP_ADD              1
             646 DICT_UPDATE          1
             648 BUILD_MAP            0

325:         650 LOAD_CONST           ("music")
             652 LOAD_CONST           ("all")
             654 LOAD_CONST           (True)
             656 BUILD_MAP            1

290:         658 MAP_ADD              1

326:         660 LOAD_CONST           ("ownedClaimDetails")
             662 LOAD_CONST           ("all")
             664 LOAD_CONST           (True)
             666 BUILD_MAP            1

290:         668 MAP_ADD              1

327:         670 LOAD_CONST           ("timePublishedSeconds")
             672 LOAD_CONST           (True)

290:         674 MAP_ADD              1

328:         676 LOAD_CONST           ("uncaptionedReason")
             678 LOAD_CONST           (True)

290:         680 MAP_ADD              1

329:         682 LOAD_CONST           ("remix")
             684 LOAD_CONST           ("all")
             686 LOAD_CONST           (True)
             688 BUILD_MAP            1

290:         690 MAP_ADD              1

330:         692 LOAD_CONST           ("contentOwnershipModelSettings")
             694 LOAD_CONST           ("all")
             696 LOAD_CONST           (True)
             698 BUILD_MAP            1

290:         700 MAP_ADD              1

331:         702 LOAD_CONST           ("googleAdsVideoLinks")
             704 LOAD_CONST           ("all")
             706 LOAD_CONST           (True)
             708 BUILD_MAP            1

290:         710 MAP_ADD              1

332:         712 LOAD_CONST           ("dubSettings")
             714 LOAD_CONST           ("all")
             716 LOAD_CONST           (True)
             718 BUILD_MAP            1

290:         720 MAP_ADD              1

333:         722 LOAD_CONST           ("alteredContentSettings")
             724 LOAD_CONST           ("all")
             726 LOAD_CONST           (True)
             728 BUILD_MAP            1

290:         730 MAP_ADD              1

334:         732 LOAD_CONST           ("collaboration")
             734 LOAD_CONST           ("all")
             736 LOAD_CONST           (True)
             738 BUILD_MAP            1

290:         740 MAP_ADD              1

335:         742 LOAD_CONST           ("thumbnailEditorState")
             744 LOAD_CONST           ("all")
             746 LOAD_CONST           (True)
             748 BUILD_MAP            1

290:         750 MAP_ADD              1

336:         752 LOAD_CONST           ("thumbnailDetails")
             754 LOAD_CONST           ("all")
             756 LOAD_CONST           (True)
             758 BUILD_MAP            1

290:         760 MAP_ADD              1

337:         762 LOAD_CONST           ("videoCreatorExperiment")
             764 LOAD_CONST           ("all")
             766 LOAD_CONST           (True)
             768 BUILD_MAP            1

290:         770 MAP_ADD              1

338:         772 LOAD_CONST           ("lengthSeconds")
             774 LOAD_CONST           (True)

290:         776 MAP_ADD              1

339:         778 LOAD_CONST           ("publicLivestream")
             780 LOAD_CONST           ("all")
             782 LOAD_CONST           (True)
             784 BUILD_MAP            1

290:         786 MAP_ADD              1

340:         788 LOAD_CONST           ("publicPremiere")
             790 LOAD_CONST           ("all")
             792 LOAD_CONST           (True)
             794 BUILD_MAP            1

290:         796 MAP_ADD              1

341:         798 LOAD_CONST           ("tvfilmMetadata")
             800 LOAD_CONST           ("all")
             802 LOAD_CONST           (True)
             804 BUILD_MAP            1

290:         806 MAP_ADD              1
             808 DICT_UPDATE          1
             810 BUILD_MAP            0

342:         812 LOAD_CONST           ("shareUrl")
             814 LOAD_CONST           (True)

290:         816 MAP_ADD              1

343:         818 LOAD_CONST           ("scheduledPublishingDetails")
             820 LOAD_CONST           ("all")
             822 LOAD_CONST           (True)
             824 BUILD_MAP            1

290:         826 MAP_ADD              1

344:         828 LOAD_CONST           ("privateShare")
             830 LOAD_CONST           ("all")
             832 LOAD_CONST           (True)
             834 BUILD_MAP            1

290:         836 MAP_ADD              1

345:         838 LOAD_CONST           ("sponsorsOnly")
             840 LOAD_CONST           ("all")
             842 LOAD_CONST           (True)
             844 BUILD_MAP            1

290:         846 MAP_ADD              1

346:         848 LOAD_CONST           ("unlistedExpired")
             850 LOAD_CONST           (True)

290:         852 MAP_ADD              1

347:         854 LOAD_CONST           ("videoTrailers")
             856 LOAD_CONST           ("all")
             858 LOAD_CONST           (True)
             860 BUILD_MAP            1

290:         862 MAP_ADD              1

348:         864 LOAD_CONST           ("isPaygated")
             866 LOAD_CONST           (True)

290:         868 MAP_ADD              1

349:         870 LOAD_CONST           ("suggestions")
             872 LOAD_CONST           ("all")
             874 LOAD_CONST           (True)
             876 BUILD_MAP            1

290:         878 MAP_ADD              1

350:         880 LOAD_CONST           ("tvType")
             882 LOAD_CONST           ("all")
             884 LOAD_CONST           (True)
             886 BUILD_MAP            1

290:         888 MAP_ADD              1

351:         890 LOAD_CONST           ("genres")
             892 LOAD_CONST           ("all")
             894 LOAD_CONST           (True)
             896 BUILD_MAP            1

290:         898 MAP_ADD              1

352:         900 LOAD_CONST           ("episode")
             902 LOAD_CONST           ("all")
             904 LOAD_CONST           (True)
             906 BUILD_MAP            1

290:         908 MAP_ADD              1

353:         910 LOAD_CONST           ("copyrightSummary")
             912 LOAD_CONST           ("all")
             914 LOAD_CONST           (True)
             916 BUILD_MAP            1

290:         918 MAP_ADD              1

354:         920 LOAD_CONST           ("productSelection")
             922 LOAD_CONST           ("all")
             924 LOAD_CONST           (True)
             926 BUILD_MAP            1

290:         928 MAP_ADD              1

355:         930 LOAD_CONST           ("productAutotaggingSettings")
             932 LOAD_CONST           ("all")
             934 LOAD_CONST           (True)
             936 BUILD_MAP            1

290:         938 MAP_ADD              1

356:         940 LOAD_CONST           ("videoLinkageShortsAttribution")
             942 LOAD_CONST           ("all")
             944 LOAD_CONST           (True)
             946 BUILD_MAP            1

290:         948 MAP_ADD              1

357:         950 LOAD_CONST           ("allowEmbed")
             952 LOAD_CONST           (True)

290:         954 MAP_ADD              1

358:         956 LOAD_CONST           ("allowRatings")
             958 LOAD_CONST           (True)

290:         960 MAP_ADD              1
             962 DICT_UPDATE          1
             964 BUILD_MAP            0

359:         966 LOAD_CONST           ("ageRestriction")
             968 LOAD_CONST           (True)

290:         970 MAP_ADD              1

360:         972 LOAD_CONST           ("audioLanguage")
             974 LOAD_CONST           ("all")
             976 LOAD_CONST           (True)
             978 BUILD_MAP            1

290:         980 MAP_ADD              1

361:         982 LOAD_CONST           ("category")
             984 LOAD_CONST           (True)

290:         986 MAP_ADD              1

362:         988 LOAD_CONST           ("commentFilter")
             990 LOAD_CONST           (True)

290:         992 MAP_ADD              1

363:         994 LOAD_CONST           ("commentSettings")
             996 LOAD_CONST           ("all")
             998 LOAD_CONST           (True)
            1000 BUILD_MAP            1

290:        1002 MAP_ADD              1

364:        1004 LOAD_CONST           ("crowdsourcingEnabled")
            1006 LOAD_CONST           (True)

290:        1008 MAP_ADD              1

365:        1010 LOAD_CONST           ("dateRecorded")
            1012 LOAD_CONST           ("all")
            1014 LOAD_CONST           (True)
            1016 BUILD_MAP            1

290:        1018 MAP_ADD              1

366:        1020 LOAD_CONST           ("defaultCommentSortOrder")
            1022 LOAD_CONST           (True)

290:        1024 MAP_ADD              1

367:        1026 LOAD_CONST           ("descriptionFormattedString")
            1028 LOAD_CONST           ("all")
            1030 LOAD_CONST           (True)
            1032 BUILD_MAP            1

290:        1034 MAP_ADD              1

368:        1036 LOAD_CONST           ("gameTitle")
            1038 LOAD_CONST           ("all")
            1040 LOAD_CONST           (True)
            1042 BUILD_MAP            1

290:        1044 MAP_ADD              1

369:        1046 LOAD_CONST           ("license")
            1048 LOAD_CONST           (True)

290:        1050 MAP_ADD              1

370:        1052 LOAD_CONST           ("liveChat")
            1054 LOAD_CONST           ("all")
            1056 LOAD_CONST           (True)
            1058 BUILD_MAP            1

290:        1060 MAP_ADD              1

371:        1062 LOAD_CONST           ("location")
            1064 LOAD_CONST           ("all")
            1066 LOAD_CONST           (True)
            1068 BUILD_MAP            1

290:        1070 MAP_ADD              1

372:        1072 LOAD_CONST           ("metadataLanguage")
            1074 LOAD_CONST           ("all")
            1076 LOAD_CONST           (True)
            1078 BUILD_MAP            1

290:        1080 MAP_ADD              1

373:        1082 LOAD_CONST           ("paidProductPlacement")
            1084 LOAD_CONST           (True)

290:        1086 MAP_ADD              1

374:        1088 LOAD_CONST           ("paidPoliticalContent")
            1090 LOAD_CONST           ("all")
            1092 LOAD_CONST           (True)
            1094 BUILD_MAP            1

290:        1096 MAP_ADD              1

375:        1098 LOAD_CONST           ("publishing")
            1100 LOAD_CONST           ("all")
            1102 LOAD_CONST           (True)
            1104 BUILD_MAP            1

290:        1106 MAP_ADD              1
            1108 DICT_UPDATE          1
            1110 BUILD_MAP            0

376:        1112 LOAD_CONST           ("tags")
            1114 LOAD_CONST           ("all")
            1116 LOAD_CONST           (True)
            1118 BUILD_MAP            1

290:        1120 MAP_ADD              1

377:        1122 LOAD_CONST           ("titleFormattedString")
            1124 LOAD_CONST           ("all")
            1126 LOAD_CONST           (True)
            1128 BUILD_MAP            1

290:        1130 MAP_ADD              1

378:        1132 LOAD_CONST           ("viewCountIsHidden")
            1134 LOAD_CONST           (True)

290:        1136 MAP_ADD              1

379:        1138 LOAD_CONST           ("autoChapterSettings")
            1140 LOAD_CONST           ("all")
            1142 LOAD_CONST           (True)
            1144 BUILD_MAP            1

290:        1146 MAP_ADD              1

380:        1148 LOAD_CONST           ("autoPlacesMentionedSettings")
            1150 LOAD_CONST           ("all")
            1152 LOAD_CONST           (True)
            1154 BUILD_MAP            1

290:        1156 MAP_ADD              1

381:        1158 LOAD_CONST           ("videoArtworkEditorState")
            1160 LOAD_CONST           ("all")
            1162 LOAD_CONST           (True)
            1164 BUILD_MAP            1

290:        1166 MAP_ADD              1

382:        1168 LOAD_CONST           ("learningConceptSettings")
            1170 LOAD_CONST           ("all")
            1172 LOAD_CONST           (True)
            1174 BUILD_MAP            1

290:        1176 MAP_ADD              1

383:        1178 LOAD_CONST           ("videoEditorProject")
            1180 LOAD_CONST           ("all")
            1182 LOAD_CONST           (True)
            1184 BUILD_MAP            1

290:        1186 MAP_ADD              1

384:        1188 LOAD_CONST           ("originalFilename")
            1190 LOAD_CONST           (True)

290:        1192 MAP_ADD              1

385:        1194 LOAD_CONST           ("timeCreatedSeconds")
            1196 LOAD_CONST           (True)

290:        1198 MAP_ADD              1

386:        1200 LOAD_CONST           ("videoResolutions")
            1202 LOAD_CONST           ("all")
            1204 LOAD_CONST           (True)
            1206 BUILD_MAP            1

290:        1208 MAP_ADD              1

387:        1210 LOAD_CONST           ("watchUrl")
            1212 LOAD_CONST           (True)

290:        1214 MAP_ADD              1

388:        1216 LOAD_CONST           ("publicShorts")
            1218 LOAD_CONST           ("all")
            1220 LOAD_CONST           (True)
            1222 BUILD_MAP            1

290:        1224 MAP_ADD              1

389:        1226 LOAD_CONST           ("publicMetrics")
            1228 LOAD_CONST           ("all")
            1230 LOAD_CONST           (True)
            1232 BUILD_MAP            1

290:        1234 MAP_ADD              1

390:        1236 LOAD_CONST           ("academicLearning")
            1238 LOAD_CONST           ("all")
            1240 LOAD_CONST           (True)
            1242 BUILD_MAP            1

290:        1244 MAP_ADD              1

391:        1246 LOAD_CONST           ("manualPlacesMentionedPlaces")
            1248 LOAD_CONST           ("all")
            1250 LOAD_CONST           (True)
            1252 BUILD_MAP            1

290:        1254 MAP_ADD              1

392:        1256 LOAD_CONST           ("autoProductsSettings")
            1258 LOAD_CONST           ("all")
            1260 LOAD_CONST           (True)
            1262 BUILD_MAP            1

290:        1264 MAP_ADD              1
            1266 DICT_UPDATE          1

393:        1268 LOAD_CONST           ("all")
            1270 LOAD_CONST           (True)
            1272 BUILD_MAP            1

394:        1274 LOAD_CONST           ("all")
            1276 LOAD_CONST           (True)
            1278 BUILD_MAP            1

290:        1280 LOAD_CONST           (('videoAutoSummarySettings', 'issues'))
            1282 BUILD_CONST_KEY_MAP  2
            1284 DICT_UPDATE          1

396:        1286 LOAD_CONST           (False)

255:        1288 LOAD_CONST           (('context', 'failOnError', 'videoIds', 'mask', 'criticalRead'))
            1290 BUILD_CONST_KEY_MAP  5
            1292 STORE_FAST           (payload)

399:        1294 LOAD_GLOBAL          (NULL + requests)
            1304 LOAD_ATTR            (post)
            1324 LOAD_FAST            (url)
            1326 LOAD_FAST            (headers)
            1328 LOAD_FAST            (payload)
            1330 KW_NAMES             (('url', 'headers', 'json'))
            1332 CALL                 3
            1340 STORE_FAST           (response)

400:        1342 LOAD_FAST            (response)
            1344 LOAD_ATTR            (NULL|self + json)
            1364 CALL                 0
            1372 STORE_FAST           (res)

401:        1374 LOAD_GLOBAL          (NULL + Video)

402:        1384 LOAD_FAST            (res)
            1386 LOAD_CONST           ("videos")
            1388 BINARY_SUBSCR
            1392 LOAD_CONST           (0)
            1394 BINARY_SUBSCR
            1398 LOAD_ATTR            (NULL|self + get)
            1418 LOAD_CONST           ("videoId")
            1420 LOAD_CONST           ("")
            1422 CALL                 2

403:        1430 LOAD_FAST            (res)
            1432 LOAD_CONST           ("videos")
            1434 BINARY_SUBSCR
            1438 LOAD_CONST           (0)
            1440 BINARY_SUBSCR
            1444 LOAD_ATTR            (NULL|self + get)
            1464 LOAD_CONST           ("title")
            1466 LOAD_CONST           ("")
            1468 CALL                 2

404:        1476 LOAD_FAST            (res)
            1478 LOAD_CONST           ("videos")
            1480 BINARY_SUBSCR
            1484 LOAD_CONST           (0)
            1486 BINARY_SUBSCR
            1490 LOAD_ATTR            (NULL|self + get)
            1510 LOAD_CONST           ("description")
            1512 LOAD_CONST           ("")
            1514 CALL                 2

405:        1522 LOAD_FAST            (res)
            1524 LOAD_CONST           ("videos")
            1526 BINARY_SUBSCR
            1530 LOAD_CONST           (0)
            1532 BINARY_SUBSCR
            1536 LOAD_ATTR            (NULL|self + get)
            1556 LOAD_CONST           ("channelId")
            1558 LOAD_CONST           ("")
            1560 CALL                 2

406:        1568 LOAD_FAST            (res)
            1570 LOAD_CONST           ("videos")
            1572 BINARY_SUBSCR
            1576 LOAD_CONST           (0)
            1578 BINARY_SUBSCR
            1582 LOAD_ATTR            (NULL|self + get)
            1602 LOAD_CONST           ("videoDurationMs")
            1604 LOAD_CONST           (0)
            1606 CALL                 2

407:        1614 LOAD_FAST            (res)
            1616 LOAD_CONST           ("videos")
            1618 BINARY_SUBSCR
            1622 LOAD_CONST           (0)
            1624 BINARY_SUBSCR

408:        1628 LOAD_ATTR            (NULL|self + get)
            1648 LOAD_CONST           ("thumbnailDetails")
            1650 BUILD_MAP            0
            1652 CALL                 2

409:        1660 LOAD_ATTR            (NULL|self + get)
            1680 LOAD_CONST           ("thumbnails")
            1682 BUILD_MAP            0
            1684 BUILD_LIST           1
            1686 CALL                 2
            1694 LOAD_CONST           (0)

407:        1696 BINARY_SUBSCR

410:        1700 LOAD_ATTR            (NULL|self + get)
            1720 LOAD_CONST           ("url")
            1722 LOAD_CONST           ("")
            1724 CALL                 2

411:        1732 LOAD_FAST            (res)
            1734 LOAD_CONST           ("videos")
            1736 BINARY_SUBSCR
            1740 LOAD_CONST           (0)
            1742 BINARY_SUBSCR
            1746 LOAD_ATTR            (NULL|self + get)
            1766 LOAD_CONST           ("status")
            1768 LOAD_CONST           ("")
            1770 CALL                 2

401:        1778 KW_NAMES             (('id', 'title', 'description', 'channel_id', 'duration_ms', 'thumbnail', 'video_status'))
            1780 CALL                 7
            1788 RETURN_VALUE
            1790 SWAP                 (TOS <-> TOS1)
            1792 POP_TOP

241:        1794 SWAP                 (TOS <-> TOS1)
            1796 STORE_FAST           (cookie)
            1798 RERAISE              0

ExceptionTable:
  74 to 112 -> 1790 [4]

# Method Name:       _build_context
# Filename:          src\module\base.py
# Argument count:    4
# Position-only argument count: 0
# Keyword-only arguments: 7
# Number of locals:  13
# Stack size:        12
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        414
# Constants:
#    0: 'Build the standard YouTube Studio API context payload.'
#    1: 'channelRoleType'
#    2: ('externalChannelId', 'roleType')
#    3: ''
#    4: ('delegationContext', 'serializedDelegationContext')
#    5: 'onBehalfOfUser'
#    6: True
#    7: ('returnLogEntry', 'internalExperimentFlags', 'eats', 'consistencyTokenJars')
#    8: 62
#    9: 'VN'
#   10: 420
#   11: 1
#   12: ('clientName', 'clientVersion', 'hl', 'gl', 'experimentsToken', 'utcOffsetMinutes', 'userInterfaceTheme', 'screenWidthPoints', 'screenHeightPoints', 'screenPixelDensity', 'screenDensityFloat')
#   13: 'visualElement'
#   14: 'veType'
#   15: 74618
#   16: ('client', 'request', 'user', 'clickTracking', 'clientScreenNonce')
# Names:
#    0: EATS
#    1: update
#    2: CLIENT_SCREEN_NONCE
# Varnames:
#	self, channel_id, role, delegated_session_id, client_version, hl, theme, screen_width, screen_height, include_on_behalf_of_user, extra_request_fields, user_block, request_block
# Positional arguments:
#	self, channel_id, role, delegated_session_id
# Local variables:
#    4: client_version
#    5: hl
#    6: theme
#    7: screen_width
#    8: screen_height
#    9: include_on_behalf_of_user
#   10: extra_request_fields
#   11: user_block
#   12: request_block

414:           0 RESUME               0

431:           2 LOAD_FAST            (channel_id)

432:           4 LOAD_CONST           ("channelRoleType")
               6 LOAD_FAST            (role)
               8 BUILD_MAP            1

430:          10 LOAD_CONST           (('externalChannelId', 'roleType'))
              12 BUILD_CONST_KEY_MAP  2

434:          14 LOAD_CONST           ("")

429:          16 LOAD_CONST           (('delegationContext', 'serializedDelegationContext'))
              18 BUILD_CONST_KEY_MAP  2
              20 STORE_FAST           (user_block)

436:          22 LOAD_FAST            (include_on_behalf_of_user)
              24 POP_JUMP_IF_FALSE    (to 36)

437:          26 LOAD_FAST            (delegated_session_id)
              28 LOAD_FAST            (user_block)
              30 LOAD_CONST           ("onBehalfOfUser")
              32 STORE_SUBSCR

440:     >>   36 LOAD_CONST           (True)

441:          38 BUILD_LIST           0

442:          40 LOAD_FAST            (self)
              42 LOAD_ATTR            (EATS)

443:          62 BUILD_LIST           0

439:          64 LOAD_CONST           (('returnLogEntry', 'internalExperimentFlags', 'eats', 'consistencyTokenJars'))
              66 BUILD_CONST_KEY_MAP  4
              68 STORE_FAST           (request_block)

445:          70 LOAD_FAST            (extra_request_fields)
              72 POP_JUMP_IF_FALSE    (to 108)

446:          74 LOAD_FAST            (request_block)
              76 LOAD_ATTR            (NULL|self + update)
              96 LOAD_FAST            (extra_request_fields)
              98 CALL                 1
             106 POP_TOP

450:     >>  108 LOAD_CONST           (62)

451:         110 LOAD_FAST            (client_version)

452:         112 LOAD_FAST            (hl)

453:         114 LOAD_CONST           ("VN")

454:         116 LOAD_CONST           ("")

455:         118 LOAD_CONST           (420)

456:         120 LOAD_FAST            (theme)

457:         122 LOAD_FAST            (screen_width)

458:         124 LOAD_FAST            (screen_height)

459:         126 LOAD_CONST           (1)

460:         128 LOAD_CONST           (1)

449:         130 LOAD_CONST           (('clientName', 'clientVersion', 'hl', 'gl', 'experimentsToken', 'utcOffsetMinutes', 'userInterfaceTheme', 'screenWidthPoints', 'screenHeightPoints', 'screenPixelDensity', 'screenDensityFloat'))
             132 BUILD_CONST_KEY_MAP  11

462:         134 LOAD_FAST            (request_block)

463:         136 LOAD_FAST            (user_block)

464:         138 LOAD_CONST           ("visualElement")
             140 LOAD_CONST           ("veType")
             142 LOAD_CONST           (74618)
             144 BUILD_MAP            1
             146 BUILD_MAP            1

465:         148 LOAD_FAST            (self)
             150 LOAD_ATTR            (CLIENT_SCREEN_NONCE)

448:         170 LOAD_CONST           (('client', 'request', 'user', 'clickTracking', 'clientScreenNonce'))
             172 BUILD_CONST_KEY_MAP  5
             174 RETURN_VALUE


# Method Name:       _get_session_token
# Filename:          src\module\base.py
# Argument count:    2
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  17
# Stack size:        18
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        468
# Constants:
#    0: '\n        Obtain a YouTube Studio session token for the given channel.\n\n        Args:\n            channel_info: A ChannelInfo dataclass instance (from src.utils).\n\n        Returns:\n            The session token string.\n\n        Raises:\n            Exception: If YouTube has changed its auth algorithm.\n        '
#    1: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
#    2: 'https://studio.youtube.com'
#    3: 'application/json'
#    4: 'SAPISIDHASH '
#    5: ('origin', 'user-agent', 'cookie', 'content-type', 'authorization')
#    6: 'https://studio.youtube.com/youtubei/v1/att/esr?alt=json'
#    7: 0
#    8: ('context', 'challenge', 'botguardResponse', 'xguardClientStatus')
#    9: ('url', 'headers', 'json')
#   10: 'ctx'
#   11: 'Youtube thay đổi thuật toán. Vui lòng lấy lại thông tin kênh. Nếu sau đó vẫn lỗi, hãy liên hệ admin!!!'
#   12: 'https://studio.youtube.com/youtubei/v1/security/get_web_reauth_url?alt=json'
#   13: 'https://studio.youtube.com/reauth'
#   14: 'REAUTH_FLOW_YT_STUDIO_COLD_LOAD'
#   15: ('context', 'continueUrl', 'flow', 'ivctx', 'challenge', 'botguardResponse')
#   16: 'encodedReauthProofToken'
#   17: 'Missing encodedReauthProofToken for channel {}, refreshing challenge...'
#   18: ('refresh_challenge_and_botguard',)
#   19: ('get_channels_info',)
#   20: 'cookie'
#   21: 'authorization'
#   22: 'Retry failed: encodedReauthProofToken vẫn không có sau khi refresh challenge. Vui lòng lấy lại thông tin kênh hoặc liên hệ admin!'
#   23: 'Retry successful after refreshing challenge for {}'
#   24: 'sessionRiskCtx'
#   25: 'https://studio.youtube.com/youtubei/v1/ars/grst?alt=json'
#   26: 'CREATOR_CHANNEL_ROLE_TYPE_OWNER'
#   27: '1.20241125.01.00'
#   28: 'vi'
#   29: 'USER_INTERFACE_THEME_LIGHT'
#   30: 1847
#   31: 285
#   32: False
#   33: 'reauthRequestInfo'
#   34: ('client_version', 'hl', 'theme', 'screen_width', 'screen_height', 'include_on_behalf_of_user', 'extra_request_fields')
#   35: ('context', 'ctx')
#   36: 'sessionToken'
# Names:
#    0: id
#    1: role
#    2: delegated_session_id
#    3: challenge
#    4: botguardResponse
#    5: cookie_string
#    6: sapisidhash
#    7: requests
#    8: post
#    9: _build_context
#   10: json
#   11: Exception
#   12: logger
#   13: warning
#   14: src.channel_refresh
#   15: refresh_challenge_and_botguard
#   16: src.utils
#   17: get_channels_info
#   18: info
# Varnames:
#	self, channel_info, channel_id, role, delegated_session_id, challenge, bot_guard_response, cookie_string, sapisidhash, user_agent, headers, res, ivctx, refresh_challenge_and_botguard, get_channels_info, encoded_reauth_proof_token, session_risk_ctx
# Positional arguments:
#	self, channel_info
# Local variables:
#    2: channel_id
#    3: role
#    4: delegated_session_id
#    5: challenge
#    6: bot_guard_response
#    7: cookie_string
#    8: sapisidhash
#    9: user_agent
#   10: headers
#   11: res
#   12: ivctx
#   13: refresh_challenge_and_botguard
#   14: get_channels_info
#   15: encoded_reauth_proof_token
#   16: session_risk_ctx

468:           0 RESUME               0

481:           2 LOAD_FAST            (channel_info)
               4 LOAD_ATTR            (id)
              24 STORE_FAST           (channel_id)

482:          26 LOAD_FAST            (channel_info)
              28 LOAD_ATTR            (role)
              48 STORE_FAST           (role)

483:          50 LOAD_FAST            (channel_info)
              52 LOAD_ATTR            (delegated_session_id)
              72 STORE_FAST           (delegated_session_id)

484:          74 LOAD_FAST            (channel_info)
              76 LOAD_ATTR            (challenge)
              96 STORE_FAST           (challenge)

485:          98 LOAD_FAST            (channel_info)
             100 LOAD_ATTR            (botguardResponse)
             120 STORE_FAST           (bot_guard_response)

486:         122 LOAD_FAST            (channel_info)
             124 LOAD_ATTR            (NULL|self + cookie_string)
             144 CALL                 0
             152 STORE_FAST           (cookie_string)

487:         154 LOAD_FAST            (channel_info)
             156 LOAD_ATTR            (sapisidhash)
             176 STORE_FAST           (sapisidhash)

489:         178 LOAD_CONST           ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
             180 STORE_FAST           (user_agent)

491:         182 LOAD_CONST           ("https://studio.youtube.com")

492:         184 LOAD_FAST            (user_agent)

493:         186 LOAD_FAST            (cookie_string)

494:         188 LOAD_CONST           ("application/json")

495:         190 LOAD_CONST           ("SAPISIDHASH ")
             192 LOAD_FAST            (sapisidhash)
             194 FORMAT_VALUE         0
             196 BUILD_STRING         2

490:         198 LOAD_CONST           (('origin', 'user-agent', 'cookie', 'content-type', 'authorization'))
             200 BUILD_CONST_KEY_MAP  5
             202 STORE_FAST           (headers)

499:         204 LOAD_GLOBAL          (NULL + requests)
             214 LOAD_ATTR            (post)

500:         234 LOAD_CONST           ("https://studio.youtube.com/youtubei/v1/att/esr?alt=json")

501:         236 LOAD_FAST            (headers)

503:         238 LOAD_FAST            (self)
             240 LOAD_ATTR            (NULL|self + _build_context)
             260 LOAD_FAST            (channel_id)
             262 LOAD_FAST            (role)
             264 LOAD_FAST            (delegated_session_id)
             266 CALL                 3

504:         274 LOAD_FAST            (challenge)

505:         276 LOAD_FAST            (bot_guard_response)

506:         278 LOAD_CONST           (0)

502:         280 LOAD_CONST           (('context', 'challenge', 'botguardResponse', 'xguardClientStatus'))
             282 BUILD_CONST_KEY_MAP  4

499:         284 KW_NAMES             (('url', 'headers', 'json'))
             286 CALL                 3

508:         294 LOAD_ATTR            (NULL|self + json)
             314 CALL                 0

499:         322 STORE_FAST           (res)

510:         324 LOAD_CONST           ("ctx")
             326 LOAD_FAST            (res)
             328 CONTAINS_OP          (not in)
             330 POP_JUMP_IF_FALSE    (to 354)

511:         332 LOAD_GLOBAL          (NULL + Exception)

512:         342 LOAD_CONST           ("Youtube thay đổi thuật toán. Vui lòng lấy lại thông tin kênh. Nếu sau đó vẫn lỗi, hãy liên hệ admin!!!")

511:         344 CALL                 1
             352 RAISE_VARARGS        (exception instance)

515:     >>  354 LOAD_FAST            (res)
             356 LOAD_CONST           ("ctx")
             358 BINARY_SUBSCR
             362 STORE_FAST           (ivctx)

518:         364 LOAD_GLOBAL          (NULL + requests)
             374 LOAD_ATTR            (post)

519:         394 LOAD_CONST           ("https://studio.youtube.com/youtubei/v1/security/get_web_reauth_url?alt=json")

520:         396 LOAD_FAST            (headers)

522:         398 LOAD_FAST            (self)
             400 LOAD_ATTR            (NULL|self + _build_context)
             420 LOAD_FAST            (channel_id)
             422 LOAD_FAST            (role)
             424 LOAD_FAST            (delegated_session_id)
             426 CALL                 3

523:         434 LOAD_CONST           ("https://studio.youtube.com/reauth")

524:         436 LOAD_CONST           ("REAUTH_FLOW_YT_STUDIO_COLD_LOAD")

525:         438 LOAD_FAST            (ivctx)

526:         440 LOAD_FAST            (challenge)

527:         442 LOAD_FAST            (bot_guard_response)

521:         444 LOAD_CONST           (('context', 'continueUrl', 'flow', 'ivctx', 'challenge', 'botguardResponse'))
             446 BUILD_CONST_KEY_MAP  6

518:         448 KW_NAMES             (('url', 'headers', 'json'))
             450 CALL                 3

529:         458 LOAD_ATTR            (NULL|self + json)
             478 CALL                 0

518:         486 STORE_FAST           (res)

531:         488 LOAD_CONST           ("encodedReauthProofToken")
             490 LOAD_FAST            (res)
             492 CONTAINS_OP          (not in)
             494 EXTENDED_ARG         (256)
             496 POP_JUMP_IF_FALSE    (to 1110)

532:         498 LOAD_GLOBAL          (NULL + logger)
             508 LOAD_ATTR            (warning)

533:         528 LOAD_CONST           ("Missing encodedReauthProofToken for channel {}, refreshing challenge...")

534:         530 LOAD_FAST            (channel_id)

532:         532 CALL                 2
             540 POP_TOP

536:         542 LOAD_CONST           (0)
             544 LOAD_CONST           (('refresh_challenge_and_botguard',))
             546 IMPORT_NAME          (src.channel_refresh)
             548 IMPORT_FROM          (refresh_challenge_and_botguard)
             550 STORE_FAST           (refresh_challenge_and_botguard)
             552 POP_TOP

537:         554 LOAD_CONST           (0)
             556 LOAD_CONST           (('get_channels_info',))
             558 IMPORT_NAME          (src.utils)
             560 IMPORT_FROM          (get_channels_info)
             562 STORE_FAST           (get_channels_info)
             564 POP_TOP

539:         566 PUSH_NULL
             568 LOAD_FAST            (refresh_challenge_and_botguard)
             570 LOAD_FAST            (channel_id)
             572 CALL                 1
             580 POP_TOP

540:         582 PUSH_NULL
             584 LOAD_FAST            (get_channels_info)
             586 LOAD_FAST            (channel_id)
             588 CALL                 1
             596 STORE_FAST           (channel_info)

541:         598 LOAD_FAST            (channel_info)
             600 LOAD_ATTR            (challenge)
             620 STORE_FAST           (challenge)

542:         622 LOAD_FAST            (channel_info)
             624 LOAD_ATTR            (botguardResponse)
             644 STORE_FAST           (bot_guard_response)

543:         646 LOAD_FAST            (channel_info)
             648 LOAD_ATTR            (NULL|self + cookie_string)
             668 CALL                 0
             676 STORE_FAST           (cookie_string)

544:         678 LOAD_FAST            (channel_info)
             680 LOAD_ATTR            (sapisidhash)
             700 STORE_FAST           (sapisidhash)

545:         702 LOAD_FAST            (channel_info)
             704 LOAD_ATTR            (delegated_session_id)
             724 STORE_FAST           (delegated_session_id)

547:         726 LOAD_FAST            (cookie_string)
             728 LOAD_FAST            (headers)
             730 LOAD_CONST           ("cookie")
             732 STORE_SUBSCR

548:         736 LOAD_CONST           ("SAPISIDHASH ")
             738 LOAD_FAST            (sapisidhash)
             740 FORMAT_VALUE         0
             742 BUILD_STRING         2
             744 LOAD_FAST            (headers)
             746 LOAD_CONST           ("authorization")
             748 STORE_SUBSCR

551:         752 LOAD_GLOBAL          (NULL + requests)
             762 LOAD_ATTR            (post)

552:         782 LOAD_CONST           ("https://studio.youtube.com/youtubei/v1/att/esr?alt=json")

553:         784 LOAD_FAST            (headers)

555:         786 LOAD_FAST            (self)
             788 LOAD_ATTR            (NULL|self + _build_context)

556:         808 LOAD_FAST            (channel_id)
             810 LOAD_FAST            (role)
             812 LOAD_FAST            (delegated_session_id)

555:         814 CALL                 3

558:         822 LOAD_FAST            (challenge)

559:         824 LOAD_FAST            (bot_guard_response)

560:         826 LOAD_CONST           (0)

554:         828 LOAD_CONST           (('context', 'challenge', 'botguardResponse', 'xguardClientStatus'))
             830 BUILD_CONST_KEY_MAP  4

551:         832 KW_NAMES             (('url', 'headers', 'json'))
             834 CALL                 3

562:         842 LOAD_ATTR            (NULL|self + json)
             862 CALL                 0

551:         870 STORE_FAST           (res)

564:         872 LOAD_CONST           ("ctx")
             874 LOAD_FAST            (res)
             876 CONTAINS_OP          (not in)
             878 POP_JUMP_IF_FALSE    (to 902)

565:         880 LOAD_GLOBAL          (NULL + Exception)

566:         890 LOAD_CONST           ("Youtube thay đổi thuật toán. Vui lòng lấy lại thông tin kênh. Nếu sau đó vẫn lỗi, hãy liên hệ admin!!!")

565:         892 CALL                 1
             900 RAISE_VARARGS        (exception instance)

569:     >>  902 LOAD_FAST            (res)
             904 LOAD_CONST           ("ctx")
             906 BINARY_SUBSCR
             910 STORE_FAST           (ivctx)

572:         912 LOAD_GLOBAL          (NULL + requests)
             922 LOAD_ATTR            (post)

573:         942 LOAD_CONST           ("https://studio.youtube.com/youtubei/v1/security/get_web_reauth_url?alt=json")

574:         944 LOAD_FAST            (headers)

576:         946 LOAD_FAST            (self)
             948 LOAD_ATTR            (NULL|self + _build_context)

577:         968 LOAD_FAST            (channel_id)
             970 LOAD_FAST            (role)
             972 LOAD_FAST            (delegated_session_id)

576:         974 CALL                 3

579:         982 LOAD_CONST           ("https://studio.youtube.com/reauth")

580:         984 LOAD_CONST           ("REAUTH_FLOW_YT_STUDIO_COLD_LOAD")

581:         986 LOAD_FAST            (ivctx)

582:         988 LOAD_FAST            (challenge)

583:         990 LOAD_FAST            (bot_guard_response)

575:         992 LOAD_CONST           (('context', 'continueUrl', 'flow', 'ivctx', 'challenge', 'botguardResponse'))
             994 BUILD_CONST_KEY_MAP  6

572:         996 KW_NAMES             (('url', 'headers', 'json'))
             998 CALL                 3

585:        1006 LOAD_ATTR            (NULL|self + json)
            1026 CALL                 0

572:        1034 STORE_FAST           (res)

587:        1036 LOAD_CONST           ("encodedReauthProofToken")
            1038 LOAD_FAST            (res)
            1040 CONTAINS_OP          (not in)
            1042 POP_JUMP_IF_FALSE    (to 1066)

588:        1044 LOAD_GLOBAL          (NULL + Exception)

589:        1054 LOAD_CONST           ("Retry failed: encodedReauthProofToken vẫn không có sau khi refresh challenge. Vui lòng lấy lại thông tin kênh hoặc liên hệ admin!")

588:        1056 CALL                 1
            1064 RAISE_VARARGS        (exception instance)

592:     >> 1066 LOAD_GLOBAL          (NULL + logger)
            1076 LOAD_ATTR            (info)

593:        1096 LOAD_CONST           ("Retry successful after refreshing challenge for {}")
            1098 LOAD_FAST            (channel_id)

592:        1100 CALL                 2
            1108 POP_TOP

596:     >> 1110 LOAD_FAST            (res)
            1112 LOAD_CONST           ("encodedReauthProofToken")
            1114 BINARY_SUBSCR
            1118 STORE_FAST           (encoded_reauth_proof_token)

597:        1120 LOAD_FAST            (res)
            1122 LOAD_CONST           ("sessionRiskCtx")
            1124 BINARY_SUBSCR
            1128 STORE_FAST           (session_risk_ctx)

600:        1130 LOAD_GLOBAL          (NULL + requests)
            1140 LOAD_ATTR            (post)

601:        1160 LOAD_CONST           ("https://studio.youtube.com/youtubei/v1/ars/grst?alt=json")

602:        1162 LOAD_FAST            (headers)

604:        1164 LOAD_FAST            (self)
            1166 LOAD_ATTR            (NULL|self + _build_context)

605:        1186 LOAD_FAST            (channel_id)

606:        1188 LOAD_CONST           ("CREATOR_CHANNEL_ROLE_TYPE_OWNER")

607:        1190 LOAD_FAST            (delegated_session_id)

608:        1192 LOAD_CONST           ("1.20241125.01.00")

609:        1194 LOAD_CONST           ("vi")

610:        1196 LOAD_CONST           ("USER_INTERFACE_THEME_LIGHT")

611:        1198 LOAD_CONST           (1847)

612:        1200 LOAD_CONST           (285)

613:        1202 LOAD_CONST           (False)

615:        1204 LOAD_CONST           ("reauthRequestInfo")

616:        1206 LOAD_CONST           ("encodedReauthProofToken")
            1208 LOAD_FAST            (encoded_reauth_proof_token)

615:        1210 BUILD_MAP            1

614:        1212 BUILD_MAP            1

604:        1214 KW_NAMES             (('client_version', 'hl', 'theme', 'screen_width', 'screen_height', 'include_on_behalf_of_user', 'extra_request_fields'))
            1216 CALL                 10

620:        1224 LOAD_FAST            (session_risk_ctx)

603:        1226 LOAD_CONST           (('context', 'ctx'))
            1228 BUILD_CONST_KEY_MAP  2

600:        1230 KW_NAMES             (('url', 'headers', 'json'))
            1232 CALL                 3

622:        1240 LOAD_ATTR            (NULL|self + json)
            1260 CALL                 0

600:        1268 STORE_FAST           (res)

624:        1270 LOAD_FAST            (res)
            1272 LOAD_CONST           ("sessionToken")
            1274 BINARY_SUBSCR
            1278 RETURN_VALUE

```
