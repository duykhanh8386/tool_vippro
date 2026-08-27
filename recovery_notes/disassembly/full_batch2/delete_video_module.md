# Static CPython 3.12 disassembly — `delete_video_module.pyc`

Generated with `xdis 6.3.0`; the code object was deserialized but never executed.

```text
# pydisasm version 6.3.0
# CPython Python bytecode 3.12.0 (3531)
#   Disassembled from CPython Python 3.13.13 | packaged by Anaconda, Inc. | (main, Apr 14 2026, 06:12:50) [MSC v.1942 64 bit (AMD64)]
# Timestamp in code: 0 (1970-01-01 07:00:00)
# Source code size mod 2**32: 0 bytes
# Method Name:       <module>
# Filename:          src\module\delete_video_module.py
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
#    4: ('get_channels_info',)
#    5: <Code311 code object DeleteVideoModule at 0x2e505863680, file src\module\delete_video_module.py>, line 8
#    6: 'DeleteVideoModule'
# Names:
#    0: requests
#    1: loguru
#    2: logger
#    3: src.module.base
#    4: IModule
#    5: src.utils
#    6: get_channels_info
#    7: DeleteVideoModule
#    8: delete_video_module

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
              36 LOAD_CONST           (('get_channels_info',))
              38 IMPORT_NAME          (src.utils)
              40 IMPORT_FROM          (get_channels_info)
              42 STORE_NAME           (get_channels_info)
              44 POP_TOP

  8:          46 PUSH_NULL
              48 LOAD_BUILD_CLASS
              50 LOAD_CONST           (<Code311 code object DeleteVideoModule at 0x2e505863680, file src\module\delete_video_module.py>, line 8)
              52 MAKE_FUNCTION        (No arguments)
              54 LOAD_CONST           ("DeleteVideoModule")
              56 LOAD_NAME            (IModule)
              58 CALL                 3
              66 STORE_NAME           (DeleteVideoModule)

113:          68 PUSH_NULL
              70 LOAD_NAME            (DeleteVideoModule)
              72 CALL                 0
              80 STORE_NAME           (delete_video_module)
              82 RETURN_CONST         (None)


# Method Name:       DeleteVideoModule
# Filename:          src\module\delete_video_module.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        6
# Flags:             0x00000000 (0x0)
# First Line:        8
# Constants:
#    0: 'DeleteVideoModule'
#    1: 'video_id'
#    2: 'channel_id'
#    3: 'return'
#    4: <Code311 code object delete at 0x2e505863790, file src\module\delete_video_module.py>, line 9
#    5: None
# Names:
#    0: __name__
#    1: __module__
#    2: __qualname__
#    3: str
#    4: int
#    5: delete

  8:           0 RESUME               0
               2 LOAD_NAME            (__name__)
               4 STORE_NAME           (__module__)
               6 LOAD_CONST           ("DeleteVideoModule")
               8 STORE_NAME           (__qualname__)

  9:          10 LOAD_CONST           ("video_id")
              12 LOAD_NAME            (str)
              14 LOAD_CONST           ("channel_id")
              16 LOAD_NAME            (str)
              18 LOAD_CONST           ("return")
              20 LOAD_NAME            (int)
              22 BUILD_TUPLE          6
              24 LOAD_CONST           (<Code311 code object delete at 0x2e505863790, file src\module\delete_video_module.py>, line 9)
              26 MAKE_FUNCTION        (annotation)
              28 STORE_NAME           (delete)
              30 RETURN_CONST         (None)


# Method Name:       delete
# Filename:          src\module\delete_video_module.py
# Argument count:    3
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  11
# Stack size:        12
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        9
# Constants:
#    0: '\n        Permanently delete a single video from YouTube Studio.\n\n        Args:\n            video_id:   The YouTube video ID to delete.\n            channel_id: The channel that owns the video.\n\n        Returns:\n            HTTP status code (200 = success).\n        '
#    1: None
#    2: "Channel '"
#    3: "' not found in database"
#    4: 'https://studio.youtube.com/youtubei/v1/video/delete'
#    5: '*/*'
#    6: 'SAPISIDHASH '
#    7: 'application/json'
#    8: 'https://studio.youtube.com'
#    9: 'https://studio.youtube.com/channel/'
#   10: '/videos'
#   11: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
#   12: '0'
#   13: '62'
#   14: '1.20260520.00.00'
#   15: ('accept', 'authorization', 'content-type', 'cookie', 'origin', 'referer', 'user-agent', 'x-goog-authuser', 'x-youtube-client-name', 'x-youtube-client-version', 'x-origin')
#   16: 62
#   17: 'vi'
#   18: 'VN'
#   19: ''
#   20: 420
#   21: 'USER_INTERFACE_THEME_DARK'
#   22: 1920
#   23: 484
#   24: 1
#   25: ('clientName', 'clientVersion', 'hl', 'gl', 'experimentsToken', 'utcOffsetMinutes', 'userInterfaceTheme', 'screenWidthPoints', 'screenHeightPoints', 'screenPixelDensity', 'screenDensityFloat')
#   26: True
#   27: 'token'
#   28: ('returnLogEntry', 'internalExperimentFlags', 'eats', 'sessionInfo', 'consistencyTokenJars')
#   29: 'channelRoleType'
#   30: ('externalChannelId', 'roleType')
#   31: ('onBehalfOfUser', 'delegationContext', 'serializedDelegationContext')
#   32: 'visualElement'
#   33: 'veType'
#   34: 31402
#   35: ('client', 'request', 'user', 'clickTracking', 'clientScreenNonce')
#   36: ('context', 'videoId')
#   37: 'alt'
#   38: 'json'
#   39: ('headers', 'json', 'params')
#   40: 'Delete video '
#   41: ' response: '
#   42: 200
#   43: 'Failed to delete video '
#   44: ': HTTP '
#   45: ' — '
#   46: ': phản hồi không phải JSON — '
#   47: 0
#   48: 'success'
#   49: False
#   50: ': server trả về "success": false — '
# Names:
#    0: get_channels_info
#    1: ValueError
#    2: cookie_string
#    3: _get_session_token
#    4: sapisidhash
#    5: id
#    6: EATS
#    7: delegated_session_id
#    8: role
#    9: CLIENT_SCREEN_NONCE
#   10: requests
#   11: post
#   12: logger
#   13: info
#   14: status_code
#   15: error
#   16: text
#   17: json
#   18: get
# Varnames:
#	self, video_id, channel_id, channel_info, cookie_string, session_token, url, headers, payload, response, body
# Positional arguments:
#	self, video_id, channel_id
# Local variables:
#    3: channel_info
#    4: cookie_string
#    5: session_token
#    6: url
#    7: headers
#    8: payload
#    9: response
#   10: body

  9:           0 RESUME               0

 20:           2 LOAD_GLOBAL          (NULL + get_channels_info)
              12 LOAD_FAST            (channel_id)
              14 CALL                 1
              22 STORE_FAST           (channel_info)

 21:          24 LOAD_FAST            (channel_info)
              26 POP_JUMP_IF_NOT_NONE (to 58)

 22:          28 LOAD_GLOBAL          (NULL + ValueError)
              38 LOAD_CONST           ("Channel '")
              40 LOAD_FAST            (channel_id)
              42 FORMAT_VALUE         0
              44 LOAD_CONST           ("' not found in database")
              46 BUILD_STRING         3
              48 CALL                 1
              56 RAISE_VARARGS        (exception instance)

 23:     >>   58 LOAD_FAST            (channel_info)
              60 LOAD_ATTR            (NULL|self + cookie_string)
              80 CALL                 0
              88 STORE_FAST           (cookie_string)

 24:          90 LOAD_FAST            (self)
              92 LOAD_ATTR            (NULL|self + _get_session_token)
             112 LOAD_FAST            (channel_info)
             114 CALL                 1
             122 STORE_FAST           (session_token)

 26:         124 LOAD_CONST           ("https://studio.youtube.com/youtubei/v1/video/delete")
             126 STORE_FAST           (url)

 29:         128 LOAD_CONST           ("*/*")

 30:         130 LOAD_CONST           ("SAPISIDHASH ")
             132 LOAD_FAST            (channel_info)
             134 LOAD_ATTR            (sapisidhash)
             154 FORMAT_VALUE         0
             156 BUILD_STRING         2

 31:         158 LOAD_CONST           ("application/json")

 32:         160 LOAD_FAST            (cookie_string)

 33:         162 LOAD_CONST           ("https://studio.youtube.com")

 34:         164 LOAD_CONST           ("https://studio.youtube.com/channel/")
             166 LOAD_FAST            (channel_info)
             168 LOAD_ATTR            (id)
             188 FORMAT_VALUE         0
             190 LOAD_CONST           ("/videos")
             192 BUILD_STRING         3

 36:         194 LOAD_CONST           ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")

 40:         196 LOAD_CONST           ("0")

 41:         198 LOAD_CONST           ("62")

 42:         200 LOAD_CONST           ("1.20260520.00.00")

 43:         202 LOAD_CONST           ("https://studio.youtube.com")

 28:         204 LOAD_CONST           (('accept', 'authorization', 'content-type', 'cookie', 'origin', 'referer', 'user-agent', 'x-goog-authuser', 'x-youtube-client-name', 'x-youtube-client-version', 'x-origin'))
             206 BUILD_CONST_KEY_MAP  11
             208 STORE_FAST           (headers)

 49:         210 LOAD_CONST           (62)

 50:         212 LOAD_CONST           ("1.20260520.00.00")

 51:         214 LOAD_CONST           ("vi")

 52:         216 LOAD_CONST           ("VN")

 53:         218 LOAD_CONST           ("")

 54:         220 LOAD_CONST           (420)

 55:         222 LOAD_CONST           ("USER_INTERFACE_THEME_DARK")

 56:         224 LOAD_CONST           (1920)

 57:         226 LOAD_CONST           (484)

 58:         228 LOAD_CONST           (1)

 59:         230 LOAD_CONST           (1)

 48:         232 LOAD_CONST           (('clientName', 'clientVersion', 'hl', 'gl', 'experimentsToken', 'utcOffsetMinutes', 'userInterfaceTheme', 'screenWidthPoints', 'screenHeightPoints', 'screenPixelDensity', 'screenDensityFloat'))
             234 BUILD_CONST_KEY_MAP  11

 62:         236 LOAD_CONST           (True)

 63:         238 BUILD_LIST           0

 64:         240 LOAD_FAST            (self)
             242 LOAD_ATTR            (EATS)

 65:         262 LOAD_CONST           ("token")
             264 LOAD_FAST            (session_token)
             266 BUILD_MAP            1

 66:         268 BUILD_LIST           0

 61:         270 LOAD_CONST           (('returnLogEntry', 'internalExperimentFlags', 'eats', 'sessionInfo', 'consistencyTokenJars'))
             272 BUILD_CONST_KEY_MAP  5

 69:         274 LOAD_FAST            (channel_info)
             276 LOAD_ATTR            (delegated_session_id)

 71:         296 LOAD_FAST            (channel_info)
             298 LOAD_ATTR            (id)

 72:         318 LOAD_CONST           ("channelRoleType")
             320 LOAD_FAST            (channel_info)
             322 LOAD_ATTR            (role)
             342 BUILD_MAP            1

 70:         344 LOAD_CONST           (('externalChannelId', 'roleType'))
             346 BUILD_CONST_KEY_MAP  2

 74:         348 LOAD_CONST           ("")

 68:         350 LOAD_CONST           (('onBehalfOfUser', 'delegationContext', 'serializedDelegationContext'))
             352 BUILD_CONST_KEY_MAP  3

 76:         354 LOAD_CONST           ("visualElement")
             356 LOAD_CONST           ("veType")
             358 LOAD_CONST           (31402)
             360 BUILD_MAP            1
             362 BUILD_MAP            1

 77:         364 LOAD_FAST            (self)
             366 LOAD_ATTR            (CLIENT_SCREEN_NONCE)

 47:         386 LOAD_CONST           (('client', 'request', 'user', 'clickTracking', 'clientScreenNonce'))
             388 BUILD_CONST_KEY_MAP  5

 79:         390 LOAD_FAST            (video_id)

 46:         392 LOAD_CONST           (('context', 'videoId'))
             394 BUILD_CONST_KEY_MAP  2
             396 STORE_FAST           (payload)

 82:         398 LOAD_GLOBAL          (NULL + requests)
             408 LOAD_ATTR            (post)

 83:         428 LOAD_FAST            (url)
             430 LOAD_FAST            (headers)
             432 LOAD_FAST            (payload)
             434 LOAD_CONST           ("alt")
             436 LOAD_CONST           ("json")
             438 BUILD_MAP            1

 82:         440 KW_NAMES             (('headers', 'json', 'params'))
             442 CALL                 4
             450 STORE_FAST           (response)

 85:         452 LOAD_GLOBAL          (NULL + logger)
             462 LOAD_ATTR            (info)
             482 LOAD_CONST           ("Delete video ")
             484 LOAD_FAST            (video_id)
             486 FORMAT_VALUE         0
             488 LOAD_CONST           (" response: ")
             490 LOAD_FAST            (response)
             492 LOAD_ATTR            (status_code)
             512 FORMAT_VALUE         0
             514 BUILD_STRING         4
             516 CALL                 1
             524 POP_TOP

 86:         526 LOAD_FAST            (response)
             528 LOAD_ATTR            (status_code)
             548 LOAD_CONST           (200)
             550 COMPARE_OP           (!=)
             554 POP_JUMP_IF_FALSE    (to 686)

 87:         556 LOAD_GLOBAL          (NULL + logger)
             566 LOAD_ATTR            (error)

 88:         586 LOAD_CONST           ("Failed to delete video ")
             588 LOAD_FAST            (video_id)
             590 FORMAT_VALUE         0
             592 LOAD_CONST           (": HTTP ")

 89:         594 LOAD_FAST            (response)
             596 LOAD_ATTR            (status_code)
             616 FORMAT_VALUE         0
             618 LOAD_CONST           (" — ")
             620 LOAD_FAST            (response)
             622 LOAD_ATTR            (text)
             642 LOAD_CONST           (None)
             644 LOAD_CONST           (200)
             646 BINARY_SLICE
             648 FORMAT_VALUE         0

 88:         650 BUILD_STRING         6

 87:         652 CALL                 1
             660 POP_TOP

 91:         662 LOAD_FAST            (response)
             664 LOAD_ATTR            (status_code)
             684 RETURN_VALUE

 94:     >>  686 NOP

 95:         688 LOAD_FAST            (response)
             690 LOAD_ATTR            (NULL|self + json)
             710 CALL                 0
             718 STORE_FAST           (body)

103:         720 LOAD_FAST            (body)
             722 LOAD_ATTR            (NULL|self + get)
             742 LOAD_CONST           ("success")
             744 CALL                 1
             752 LOAD_CONST           (False)
             754 IS_OP                (is)
             756 POP_JUMP_IF_FALSE    (to 840)

104:         758 LOAD_GLOBAL          (NULL + logger)
             768 LOAD_ATTR            (error)

105:         788 LOAD_CONST           ("Failed to delete video ")
             790 LOAD_FAST            (video_id)
             792 FORMAT_VALUE         0
             794 LOAD_CONST           (': server trả về "success": false — ')

106:         796 LOAD_FAST            (response)
             798 LOAD_ATTR            (text)
             818 LOAD_CONST           (None)
             820 LOAD_CONST           (200)
             822 BINARY_SLICE
             824 FORMAT_VALUE         0

105:         826 BUILD_STRING         4

104:         828 CALL                 1
             836 POP_TOP

108:         838 RETURN_CONST         (0)

110:     >>  840 LOAD_FAST            (response)
             842 LOAD_ATTR            (status_code)
             862 RETURN_VALUE
             864 PUSH_EXC_INFO

 96:         866 LOAD_GLOBAL          (ValueError)
             876 CHECK_EXC_MATCH
             878 POP_JUMP_IF_FALSE    (to 966)
             880 POP_TOP

 97:         882 LOAD_GLOBAL          (NULL + logger)
             892 LOAD_ATTR            (error)

 98:         912 LOAD_CONST           ("Failed to delete video ")
             914 LOAD_FAST            (video_id)
             916 FORMAT_VALUE         0
             918 LOAD_CONST           (": phản hồi không phải JSON — ")

 99:         920 LOAD_FAST            (response)
             922 LOAD_ATTR            (text)
             942 LOAD_CONST           (None)
             944 LOAD_CONST           (200)
             946 BINARY_SLICE
             948 FORMAT_VALUE         0

 98:         950 BUILD_STRING         4

 97:         952 CALL                 1
             960 POP_TOP

101:         962 POP_EXCEPT
             964 RETURN_CONST         (0)

 96:     >>  966 RERAISE              0
             968 COPY                 3
             970 POP_EXCEPT
             972 RERAISE              1

ExceptionTable:
  688 to 718 -> 864 [0]
  864 to 960 -> 968 [1] lasti
  966 to 966 -> 968 [1] lasti
```
