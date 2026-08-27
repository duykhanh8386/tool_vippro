# Static CPython 3.12 disassembly — `audio_module.pyc`

Generated with `xdis 6.3.0`; the code object was deserialized but never executed.

```text
# pydisasm version 6.3.0
# CPython Python bytecode 3.12.0 (3531)
#   Disassembled from CPython Python 3.13.13 | packaged by Anaconda, Inc. | (main, Apr 14 2026, 06:12:50) [MSC v.1942 64 bit (AMD64)]
# Timestamp in code: 0 (1970-01-01 07:00:00)
# Source code size mod 2**32: 0 bytes
# Method Name:       <module>
# Filename:          src\module\audio_module.py
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
#    2: ('quote',)
#    3: ('logger',)
#    4: ('IModule',)
#    5: ('ChannelInfo',)
#    6: ('get_channels_info',)
#    7: <Code311 code object UpdateAudioModule at 0x2e1d0132f10, file src\module\audio_module.py>, line 13
#    8: 'UpdateAudioModule'
# Names:
#    0: os
#    1: threading
#    2: urllib.parse
#    3: quote
#    4: requests
#    5: loguru
#    6: logger
#    7: src.module.base
#    8: IModule
#    9: src.module.model
#   10: ChannelInfo
#   11: src.utils
#   12: get_channels_info
#   13: UpdateAudioModule
#   14: update_audio_module

  0:           0 RESUME               0

  1:           2 LOAD_CONST           (0)
               4 LOAD_CONST           (None)
               6 IMPORT_NAME          (os)
               8 STORE_NAME           (os)

  2:          10 LOAD_CONST           (0)
              12 LOAD_CONST           (None)
              14 IMPORT_NAME          (threading)
              16 STORE_NAME           (threading)

  3:          18 LOAD_CONST           (0)
              20 LOAD_CONST           (('quote',))
              22 IMPORT_NAME          (urllib.parse)
              24 IMPORT_FROM          (quote)
              26 STORE_NAME           (quote)
              28 POP_TOP

  5:          30 LOAD_CONST           (0)
              32 LOAD_CONST           (None)
              34 IMPORT_NAME          (requests)
              36 STORE_NAME           (requests)

  6:          38 LOAD_CONST           (0)
              40 LOAD_CONST           (('logger',))
              42 IMPORT_NAME          (loguru)
              44 IMPORT_FROM          (logger)
              46 STORE_NAME           (logger)
              48 POP_TOP

  8:          50 LOAD_CONST           (0)
              52 LOAD_CONST           (('IModule',))
              54 IMPORT_NAME          (src.module.base)
              56 IMPORT_FROM          (IModule)
              58 STORE_NAME           (IModule)
              60 POP_TOP

  9:          62 LOAD_CONST           (0)
              64 LOAD_CONST           (('ChannelInfo',))
              66 IMPORT_NAME          (src.module.model)
              68 IMPORT_FROM          (ChannelInfo)
              70 STORE_NAME           (ChannelInfo)
              72 POP_TOP

 10:          74 LOAD_CONST           (0)
              76 LOAD_CONST           (('get_channels_info',))
              78 IMPORT_NAME          (src.utils)
              80 IMPORT_FROM          (get_channels_info)
              82 STORE_NAME           (get_channels_info)
              84 POP_TOP

 13:          86 PUSH_NULL
              88 LOAD_BUILD_CLASS
              90 LOAD_CONST           (<Code311 code object UpdateAudioModule at 0x2e1d0132f10, file src\module\audio_module.py>, line 13)
              92 MAKE_FUNCTION        (No arguments)
              94 LOAD_CONST           ("UpdateAudioModule")
              96 LOAD_NAME            (IModule)
              98 CALL                 3
             106 STORE_NAME           (UpdateAudioModule)

315:         108 PUSH_NULL
             110 LOAD_NAME            (UpdateAudioModule)
             112 CALL                 0
             120 STORE_NAME           (update_audio_module)
             122 RETURN_CONST         (None)


# Method Name:       UpdateAudioModule
# Filename:          src\module\audio_module.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        12
# Flags:             0x00000000 (0x0)
# First Line:        13
# Constants:
#    0: 'UpdateAudioModule'
#    1: 'id_video'
#    2: 'channel_id'
#    3: 'file_name'
#    4: 'language'
#    5: 'data'
#    6: <Code311 code object add at 0x2e1d01327a0, file src\module\audio_module.py>, line 14
#    7: 'fname_header'
#    8: 'cookie_string'
#    9: <Code311 code object _upload_http at 0x2e1d01329c0, file src\module\audio_module.py>, line 65
#   10: 'next_url'
#   11: 'return'
#   12: <Code311 code object _next_upload_http at 0x2e1d01328b0, file src\module\audio_module.py>, line 93
#   13: 'video_id'
#   14: 'scotty_resource_id'
#   15: 'channel_info'
#   16: 'session_token'
#   17: <Code311 code object _update at 0x2e1d0132be0, file src\module\audio_module.py>, line 116
#   18: <Code311 code object delete at 0x2e1d0132cf0, file src\module\audio_module.py>, line 178
#   19: <Code311 code object _get_all_audio_track_ids at 0x2e1d0132e00, file src\module\audio_module.py>, line 241
#   20: None
# Names:
#    0: __name__
#    1: __module__
#    2: __qualname__
#    3: str
#    4: bytes
#    5: add
#    6: _upload_http
#    7: _next_upload_http
#    8: ChannelInfo
#    9: _update
#   10: delete
#   11: _get_all_audio_track_ids

 13:           0 RESUME               0
               2 LOAD_NAME            (__name__)
               4 STORE_NAME           (__module__)
               6 LOAD_CONST           ("UpdateAudioModule")
               8 STORE_NAME           (__qualname__)

 14:          10 LOAD_CONST           ("id_video")

 15:          12 LOAD_NAME            (str)

 14:          14 LOAD_CONST           ("channel_id")

 15:          16 LOAD_NAME            (str)

 14:          18 LOAD_CONST           ("file_name")

 15:          20 LOAD_NAME            (str)

 14:          22 LOAD_CONST           ("language")

 15:          24 LOAD_NAME            (str)

 14:          26 LOAD_CONST           ("data")

 15:          28 LOAD_NAME            (bytes)

 14:          30 BUILD_TUPLE          10
              32 LOAD_CONST           (<Code311 code object add at 0x2e1d01327a0, file src\module\audio_module.py>, line 14)
              34 MAKE_FUNCTION        (annotation)
              36 STORE_NAME           (add)

 65:          38 LOAD_CONST           ("fname_header")
              40 LOAD_NAME            (str)
              42 LOAD_CONST           ("cookie_string")
              44 LOAD_NAME            (str)
              46 BUILD_TUPLE          4
              48 LOAD_CONST           (<Code311 code object _upload_http at 0x2e1d01329c0, file src\module\audio_module.py>, line 65)
              50 MAKE_FUNCTION        (annotation)
              52 STORE_NAME           (_upload_http)

 93:          54 LOAD_CONST           ("next_url")

 94:          56 LOAD_NAME            (str)

 93:          58 LOAD_CONST           ("fname_header")

 94:          60 LOAD_NAME            (str)

 93:          62 LOAD_CONST           ("cookie_string")

 94:          64 LOAD_NAME            (str)

 93:          66 LOAD_CONST           ("data")

 94:          68 LOAD_NAME            (bytes)

 93:          70 LOAD_CONST           ("return")

 95:          72 LOAD_NAME            (str)

 93:          74 BUILD_TUPLE          10
              76 LOAD_CONST           (<Code311 code object _next_upload_http at 0x2e1d01328b0, file src\module\audio_module.py>, line 93)
              78 MAKE_FUNCTION        (annotation)
              80 STORE_NAME           (_next_upload_http)

116:          82 LOAD_CONST           ("video_id")

118:          84 LOAD_NAME            (str)

116:          86 LOAD_CONST           ("scotty_resource_id")

119:          88 LOAD_NAME            (str)

116:          90 LOAD_CONST           ("channel_info")

120:          92 LOAD_NAME            (ChannelInfo)

116:          94 LOAD_CONST           ("cookie_string")

121:          96 LOAD_NAME            (str)

116:          98 LOAD_CONST           ("session_token")

122:         100 LOAD_NAME            (str)

116:         102 LOAD_CONST           ("language")

123:         104 LOAD_NAME            (str)

116:         106 BUILD_TUPLE          12
             108 LOAD_CONST           (<Code311 code object _update at 0x2e1d0132be0, file src\module\audio_module.py>, line 116)
             110 MAKE_FUNCTION        (annotation)
             112 STORE_NAME           (_update)

178:         114 LOAD_CONST           ("id_video")
             116 LOAD_NAME            (str)
             118 LOAD_CONST           ("channel_id")
             120 LOAD_NAME            (str)
             122 BUILD_TUPLE          4
             124 LOAD_CONST           (<Code311 code object delete at 0x2e1d0132cf0, file src\module\audio_module.py>, line 178)
             126 MAKE_FUNCTION        (annotation)
             128 STORE_NAME           (delete)

241:         130 LOAD_CONST           ("id_video")
             132 LOAD_NAME            (str)
             134 LOAD_CONST           ("channel_id")
             136 LOAD_NAME            (str)
             138 BUILD_TUPLE          4
             140 LOAD_CONST           (<Code311 code object _get_all_audio_track_ids at 0x2e1d0132e00, file src\module\audio_module.py>, line 241)
             142 MAKE_FUNCTION        (annotation)
             144 STORE_NAME           (_get_all_audio_track_ids)
             146 RETURN_CONST         (None)


# Method Name:       add
# Filename:          src\module\audio_module.py
# Argument count:    6
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  13
# Stack size:        9
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        14
# Constants:
#    0: None
#    1: '; '
#    2: 'name'
#    3: '='
#    4: 'value'
#    5: ''
#    6: ('safe',)
#    7: ('fname_header', 'cookie_string')
#    8: ('video_id', 'scotty_resource_id', 'channel_info', 'session_token', 'cookie_string', 'language')
#    9: (200, 409)
#   10: 'Failed to update audio for video '
#   11: ', language '
#   12: ': '
#   13: <Code311 code object background_upload at 0x2e1d0132690, file src\module\audio_module.py>, line 45
#   14: True
#   15: ('target', 'daemon')
# Names:
#    0: get_channels_info
#    1: join
#    2: cookies
#    3: _get_session_token
#    4: quote
#    5: os
#    6: path
#    7: basename
#    8: _upload_http
#    9: _update
#   10: Exception
#   11: threading
#   12: Thread
#   13: start
# Varnames:
#	self, id_video, channel_id, file_name, language, data, channel_info, cookie, session_token, scotty_resource_id, res, background_upload, upload_thread
# Positional arguments:
#	self, id_video, channel_id, file_name, language, data
# Local variables:
#    6: channel_info
#    7: cookie
#    8: session_token
#    9: scotty_resource_id
#   10: res
#   11: background_upload
#   12: upload_thread
# Cell variables:
#    0: self
#    1: id_video
#    2: language
#    3: data
#    4: cookie_string
#    5: fname_header
#    6: upload_url
               0 MAKE_CELL            (self)
               2 MAKE_CELL            (id_video)
               4 MAKE_CELL            (language)
               6 MAKE_CELL            (data)
               8 MAKE_CELL            (cookie_string)
              10 MAKE_CELL            (fname_header)
              12 MAKE_CELL            (upload_url)

 14:          14 RESUME               0

 17:          16 LOAD_GLOBAL          (NULL + get_channels_info)
              26 LOAD_FAST            (channel_id)
              28 CALL                 1
              36 STORE_FAST           (channel_info)

 18:          38 LOAD_CONST           ("; ")
              40 LOAD_ATTR            (NULL|self + join)

 21:          60 LOAD_FAST            (channel_info)
              62 LOAD_ATTR            (cookies)
              82 GET_ITER

 19:          84 LOAD_FAST_AND_CLEAR  (cookie)
              86 SWAP                 (TOS <-> TOS1)
              88 BUILD_LIST           0
              90 SWAP                 (TOS <-> TOS1)

 21:          92 FOR_ITER             (to 126)
              96 STORE_FAST           (cookie)

 20:          98 LOAD_FAST            (cookie)
             100 LOAD_CONST           ("name")
             102 BINARY_SUBSCR
             106 FORMAT_VALUE         0
             108 LOAD_CONST           ("=")
             110 LOAD_FAST            (cookie)
             112 LOAD_CONST           ("value")
             114 BINARY_SUBSCR
             118 FORMAT_VALUE         0
             120 BUILD_STRING         3
             122 LIST_APPEND          2
         >>  124 JUMP_BACKWARD        (to 92)

 21:         126 END_FOR

 19:         128 SWAP                 (TOS <-> TOS1)
             130 STORE_FAST           (cookie)

 18:         132 CALL                 1
             140 STORE_DEREF          (cookie_string)

 24:         142 LOAD_DEREF           (self)
             144 LOAD_ATTR            (NULL|self + _get_session_token)
             164 LOAD_FAST            (channel_info)
             166 CALL                 1
             174 STORE_FAST           (session_token)

 25:         176 LOAD_GLOBAL          (NULL + quote)
             186 LOAD_GLOBAL          (os)
             196 LOAD_ATTR            (path)
             216 LOAD_ATTR            (NULL|self + basename)
             236 LOAD_FAST            (file_name)
             238 CALL                 1
             246 LOAD_CONST           ("")
             248 KW_NAMES             (('safe',))
             250 CALL                 2
             258 STORE_DEREF          (fname_header)

 26:         260 LOAD_DEREF           (self)
             262 LOAD_ATTR            (NULL|self + _upload_http)

 27:         282 LOAD_DEREF           (fname_header)
             284 LOAD_DEREF           (cookie_string)

 26:         286 KW_NAMES             (('fname_header', 'cookie_string'))
             288 CALL                 2
             296 UNPACK_SEQUENCE      2
             300 STORE_DEREF          (upload_url)
             302 STORE_FAST           (scotty_resource_id)

 30:         304 LOAD_DEREF           (self)
             306 LOAD_ATTR            (NULL|self + _update)

 31:         326 LOAD_DEREF           (id_video)

 32:         328 LOAD_FAST            (scotty_resource_id)

 33:         330 LOAD_FAST            (channel_info)

 34:         332 LOAD_FAST            (session_token)

 35:         334 LOAD_DEREF           (cookie_string)

 36:         336 LOAD_DEREF           (language)

 30:         338 KW_NAMES             (('video_id', 'scotty_resource_id', 'channel_info', 'session_token', 'cookie_string', 'language'))
             340 CALL                 6
             348 STORE_FAST           (res)

 39:         350 LOAD_FAST            (res)
             352 LOAD_CONST           ((200, 409))
             354 CONTAINS_OP          (not in)
             356 POP_JUMP_IF_FALSE    (to 398)

 40:         358 LOAD_GLOBAL          (NULL + Exception)

 41:         368 LOAD_CONST           ("Failed to update audio for video ")
             370 LOAD_DEREF           (id_video)
             372 FORMAT_VALUE         0
             374 LOAD_CONST           (", language ")
             376 LOAD_DEREF           (language)
             378 FORMAT_VALUE         0
             380 LOAD_CONST           (": ")
             382 LOAD_FAST            (res)
             384 FORMAT_VALUE         0
             386 BUILD_STRING         6

 40:         388 CALL                 1
             396 RAISE_VARARGS        (exception instance)

 45:     >>  398 LOAD_CLOSURE         (cookie_string)
             400 LOAD_CLOSURE         (data)
             402 LOAD_CLOSURE         (fname_header)
             404 LOAD_CLOSURE         (id_video)
             406 LOAD_CLOSURE         (language)
             408 LOAD_CLOSURE         (self)
             410 LOAD_CLOSURE         (upload_url)
             412 BUILD_TUPLE          7
             414 LOAD_CONST           (<Code311 code object background_upload at 0x2e1d0132690, file src\module\audio_module.py>, line 45)
             416 MAKE_FUNCTION        (closure)
             418 STORE_FAST           (background_upload)

 60:         420 LOAD_GLOBAL          (NULL + threading)
             430 LOAD_ATTR            (Thread)
             450 LOAD_FAST            (background_upload)
             452 LOAD_CONST           (True)
             454 KW_NAMES             (('target', 'daemon'))
             456 CALL                 2
             464 STORE_FAST           (upload_thread)

 61:         466 LOAD_FAST            (upload_thread)
             468 LOAD_ATTR            (NULL|self + start)
             488 CALL                 0
             496 POP_TOP

 63:         498 LOAD_FAST            (res)
             500 RETURN_VALUE
             502 SWAP                 (TOS <-> TOS1)
             504 POP_TOP

 19:         506 SWAP                 (TOS <-> TOS1)
             508 STORE_FAST           (cookie)
             510 RERAISE              0

ExceptionTable:
  88 to 126 -> 502 [4]

# Method Name:       _upload_http
# Filename:          src\module\audio_module.py
# Argument count:    3
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  8
# Stack size:        5
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        65
# Constants:
#    0: None
#    1: 'https://upload.youtube.com/upload/audiotrack?authuser=0'
#    2: 'Host'
#    3: 'upload.youtube.com'
#    4: 'Cookie'
#    5: 'Content-Length'
#    6: '2'
#    7: 'Sec-Ch-Ua-Platform'
#    8: '"Windows"'
#    9: 'Sec-Ch-Ua'
#   10: '"Chromium";v="139", "Not;A=Brand";v="99"'
#   11: 'Sec-Ch-Ua-Mobile'
#   12: '?0'
#   13: 'X-Goog-Upload-Protocol'
#   14: 'resumable'
#   15: 'X-Goog-Upload-File-Name'
#   16: 'Content-Type'
#   17: 'application/x-www-form-urlencoded;charset=UTF-8'
#   18: 'Accept-Language'
#   19: 'en-US,en;q=0.9'
#   20: 'User-Agent'
#   21: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'
#   22: 'X-Goog-Upload-Command'
#   23: 'start'
#   24: 'Accept'
#   25: '*/*'
#   26: 'Origin'
#   27: 'https://studio.youtube.com'
#   28: 'Referer'
#   29: 'https://studio.youtube.com/'
#   30: 'Accept-Encoding'
#   31: 'gzip, deflate, br'
#   32: 'Priority'
#   33: 'u=1, i'
#   34: '{}'
#   35: ('headers', 'data')
#   36: 200
#   37: 'Failed to upload audio: '
#   38: 'X-Goog-Upload-URL'
#   39: 'X-Goog-Upload-Header-Scotty-Resource-Id'
# Names:
#    0: requests
#    1: post
#    2: status_code
#    3: Exception
#    4: headers
# Varnames:
#	self, fname_header, cookie_string, url, headers, response, upload_url, scotty_id
# Positional arguments:
#	self, fname_header, cookie_string
# Local variables:
#    3: url
#    4: headers
#    5: response
#    6: upload_url
#    7: scotty_id

 65:           0 RESUME               0

 66:           2 LOAD_CONST           ("https://upload.youtube.com/upload/audiotrack?authuser=0")
               4 STORE_FAST           (url)

 67:           6 BUILD_MAP            0

 68:           8 LOAD_CONST           ("Host")
              10 LOAD_CONST           ("upload.youtube.com")

 67:          12 MAP_ADD              1

 69:          14 LOAD_CONST           ("Cookie")
              16 LOAD_FAST            (cookie_string)

 67:          18 MAP_ADD              1

 70:          20 LOAD_CONST           ("Content-Length")
              22 LOAD_CONST           ("2")

 67:          24 MAP_ADD              1

 71:          26 LOAD_CONST           ("Sec-Ch-Ua-Platform")
              28 LOAD_CONST           ('"Windows"')

 67:          30 MAP_ADD              1

 72:          32 LOAD_CONST           ("Sec-Ch-Ua")
              34 LOAD_CONST           ('"Chromium";v="139", "Not;A=Brand";v="99"')

 67:          36 MAP_ADD              1

 73:          38 LOAD_CONST           ("Sec-Ch-Ua-Mobile")
              40 LOAD_CONST           ("?0")

 67:          42 MAP_ADD              1

 74:          44 LOAD_CONST           ("X-Goog-Upload-Protocol")
              46 LOAD_CONST           ("resumable")

 67:          48 MAP_ADD              1

 75:          50 LOAD_CONST           ("X-Goog-Upload-File-Name")
              52 LOAD_FAST            (fname_header)

 67:          54 MAP_ADD              1

 76:          56 LOAD_CONST           ("Content-Type")
              58 LOAD_CONST           ("application/x-www-form-urlencoded;charset=UTF-8")

 67:          60 MAP_ADD              1

 77:          62 LOAD_CONST           ("Accept-Language")
              64 LOAD_CONST           ("en-US,en;q=0.9")

 67:          66 MAP_ADD              1

 78:          68 LOAD_CONST           ("User-Agent")
              70 LOAD_CONST           ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")

 67:          72 MAP_ADD              1

 79:          74 LOAD_CONST           ("X-Goog-Upload-Command")
              76 LOAD_CONST           ("start")

 67:          78 MAP_ADD              1

 80:          80 LOAD_CONST           ("Accept")
              82 LOAD_CONST           ("*/*")

 67:          84 MAP_ADD              1

 81:          86 LOAD_CONST           ("Origin")
              88 LOAD_CONST           ("https://studio.youtube.com")

 67:          90 MAP_ADD              1

 82:          92 LOAD_CONST           ("Referer")
              94 LOAD_CONST           ("https://studio.youtube.com/")

 67:          96 MAP_ADD              1

 83:          98 LOAD_CONST           ("Accept-Encoding")
             100 LOAD_CONST           ("gzip, deflate, br")

 67:         102 MAP_ADD              1

 84:         104 LOAD_CONST           ("Priority")
             106 LOAD_CONST           ("u=1, i")

 67:         108 MAP_ADD              1
             110 STORE_FAST           (headers)

 86:         112 LOAD_GLOBAL          (NULL + requests)
             122 LOAD_ATTR            (post)
             142 LOAD_FAST            (url)
             144 LOAD_FAST            (headers)
             146 LOAD_CONST           ("{}")
             148 KW_NAMES             (('headers', 'data'))
             150 CALL                 3
             158 STORE_FAST           (response)

 87:         160 LOAD_FAST            (response)
             162 LOAD_ATTR            (status_code)
             182 LOAD_CONST           (200)
             184 COMPARE_OP           (!=)
             188 POP_JUMP_IF_FALSE    (to 238)

 88:         190 LOAD_GLOBAL          (NULL + Exception)
             200 LOAD_CONST           ("Failed to upload audio: ")
             202 LOAD_FAST            (response)
             204 LOAD_ATTR            (status_code)
             224 FORMAT_VALUE         0
             226 BUILD_STRING         2
             228 CALL                 1
             236 RAISE_VARARGS        (exception instance)

 89:     >>  238 LOAD_FAST            (response)
             240 LOAD_ATTR            (headers)
             260 LOAD_CONST           ("X-Goog-Upload-URL")
             262 BINARY_SUBSCR
             266 STORE_FAST           (upload_url)

 90:         268 LOAD_FAST            (response)
             270 LOAD_ATTR            (headers)
             290 LOAD_CONST           ("X-Goog-Upload-Header-Scotty-Resource-Id")
             292 BINARY_SUBSCR
             296 STORE_FAST           (scotty_id)

 91:         298 LOAD_FAST            (upload_url)
             300 LOAD_FAST            (scotty_id)
             302 BUILD_TUPLE          2
             304 RETURN_VALUE


# Method Name:       _next_upload_http
# Filename:          src\module\audio_module.py
# Argument count:    5
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  7
# Stack size:        14
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        93
# Constants:
#    0: None
#    1: 'upload.youtube.com'
#    2: 'application/x-www-form-urlencoded;charset=utf-8'
#    3: 'en-US,en;q=0.9'
#    4: '0'
#    5: 'upload, finalize'
#    6: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'
#    7: '*/*'
#    8: 'https://studio.youtube.com'
#    9: 'https://studio.youtube.com/'
#   10: 'gzip, deflate, br'
#   11: 'u=1, i'
#   12: ('Host', 'Cookie', 'X-Goog-Upload-File-Name', 'Content-Type', 'Accept-Language', 'X-Goog-Upload-Offset', 'X-Goog-Upload-Command', 'User-Agent', 'Accept', 'Origin', 'Referer', 'Accept-Encoding', 'Priority')
#   13: ('headers', 'data')
#   14: 200
#   15: 'Failed to upload audio: '
# Names:
#    0: requests
#    1: post
#    2: status_code
#    3: Exception
# Varnames:
#	self, next_url, fname_header, cookie_string, data, headers, response
# Positional arguments:
#	self, next_url, fname_header, cookie_string, data
# Local variables:
#    5: headers
#    6: response

 93:           0 RESUME               0

 97:           2 LOAD_CONST           ("upload.youtube.com")

 98:           4 LOAD_FAST            (cookie_string)

 99:           6 LOAD_FAST            (fname_header)

100:           8 LOAD_CONST           ("application/x-www-form-urlencoded;charset=utf-8")

101:          10 LOAD_CONST           ("en-US,en;q=0.9")

102:          12 LOAD_CONST           ("0")

103:          14 LOAD_CONST           ("upload, finalize")

104:          16 LOAD_CONST           ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")

105:          18 LOAD_CONST           ("*/*")

106:          20 LOAD_CONST           ("https://studio.youtube.com")

107:          22 LOAD_CONST           ("https://studio.youtube.com/")

108:          24 LOAD_CONST           ("gzip, deflate, br")

109:          26 LOAD_CONST           ("u=1, i")

 96:          28 LOAD_CONST           (('Host', 'Cookie', 'X-Goog-Upload-File-Name', 'Content-Type', 'Accept-Language', 'X-Goog-Upload-Offset', 'X-Goog-Upload-Command', 'User-Agent', 'Accept', 'Origin', 'Referer', 'Accept-Encoding', 'Priority'))
              30 BUILD_CONST_KEY_MAP  13
              32 STORE_FAST           (headers)

111:          34 LOAD_GLOBAL          (NULL + requests)
              44 LOAD_ATTR            (post)
              64 LOAD_FAST            (next_url)
              66 LOAD_FAST            (headers)
              68 LOAD_FAST            (data)
              70 KW_NAMES             (('headers', 'data'))
              72 CALL                 3
              80 STORE_FAST           (response)

113:          82 LOAD_FAST            (response)
              84 LOAD_ATTR            (status_code)
             104 LOAD_CONST           (200)
             106 COMPARE_OP           (!=)
             110 POP_JUMP_IF_FALSE    (to 160)

114:         112 LOAD_GLOBAL          (NULL + Exception)
             122 LOAD_CONST           ("Failed to upload audio: ")
             124 LOAD_FAST            (response)
             126 LOAD_ATTR            (status_code)
             146 FORMAT_VALUE         0
             148 BUILD_STRING         2
             150 CALL                 1
             158 RAISE_VARARGS        (exception instance)

113:     >>  160 RETURN_CONST         (None)


# Method Name:       _update
# Filename:          src\module\audio_module.py
# Argument count:    7
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  11
# Stack size:        16
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        116
# Constants:
#    0: None
#    1: 'https://studio.youtube.com/youtubei/v1/creator/add_audio_track?alt=json'
#    2: 'studio.youtube.com'
#    3: 'SAPISIDHASH '
#    4: 'application/json'
#    5: 'https://studio.youtube.com'
#    6: 'https://studio.youtube.com/video/'
#    7: '/translations'
#    8: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'
#    9: '*/*'
#   10: 'en-US,en;q=0.9'
#   11: ('Host', 'Cookie', 'Authorization', 'Content-Type', 'Origin', 'Referer', 'User-Agent', 'Accept', 'Accept-Language')
#   12: 'scottyResourceId'
#   13: 'id'
#   14: 'dubbed'
#   15: 'AUDIO_TRACK_SOURCE_CREATOR'
#   16: 62
#   17: '1.20250902.04.00'
#   18: 'en'
#   19: 'VN'
#   20: 420
#   21: 'USER_INTERFACE_THEME_DARK'
#   22: 1920
#   23: 945
#   24: 1
#   25: ('clientName', 'clientVersion', 'hl', 'gl', 'utcOffsetMinutes', 'userInterfaceTheme', 'screenWidthPoints', 'screenHeightPoints', 'screenPixelDensity', 'screenDensityFloat')
#   26: True
#   27: 'AWSNWa0l7AGlCHtnt233UutuGGeh33lZ817vfraxpNhL8LY5gqkpaiN73HzUXyRRQ2ApQuCVRfHRtr9rlEQ8rczpjRVn_mm0nP74Qdc4IR95HbzJKhorwIoTVAqfC4o='
#   28: 'token'
#   29: ('returnLogEntry', 'internalExperimentFlags', 'eats', 'sessionInfo')
#   30: 'channelRoleType'
#   31: ('externalChannelId', 'roleType')
#   32: ''
#   33: ('onBehalfOfUser', 'delegationContext', 'serializedDelegationContext')
#   34: 'visualElement'
#   35: 'veType'
#   36: 74618
#   37: 'UUFKQY_AX3QaOzkG'
#   38: ('client', 'request', 'user', 'clickTracking', 'clientScreenNonce')
#   39: ('videoId', 'resourceId', 'language', 'audioContentTypeString', 'audioTrackSource', 'context')
#   40: ('headers', 'json')
# Names:
#    0: sapisidhash
#    1: delegated_session_id
#    2: id
#    3: role
#    4: requests
#    5: post
#    6: status_code
# Varnames:
#	self, video_id, scotty_resource_id, channel_info, cookie_string, session_token, language, url, headers, payload, response
# Positional arguments:
#	self, video_id, scotty_resource_id, channel_info, cookie_string, session_token, language
# Local variables:
#    7: url
#    8: headers
#    9: payload
#   10: response

116:           0 RESUME               0

125:           2 LOAD_CONST           ("https://studio.youtube.com/youtubei/v1/creator/add_audio_track?alt=json")
               4 STORE_FAST           (url)

128:           6 LOAD_CONST           ("studio.youtube.com")

129:           8 LOAD_FAST            (cookie_string)

130:          10 LOAD_CONST           ("SAPISIDHASH ")
              12 LOAD_FAST            (channel_info)
              14 LOAD_ATTR            (sapisidhash)
              34 FORMAT_VALUE         0
              36 BUILD_STRING         2

131:          38 LOAD_CONST           ("application/json")

132:          40 LOAD_CONST           ("https://studio.youtube.com")

133:          42 LOAD_CONST           ("https://studio.youtube.com/video/")
              44 LOAD_FAST            (video_id)
              46 FORMAT_VALUE         0
              48 LOAD_CONST           ("/translations")
              50 BUILD_STRING         3

134:          52 LOAD_CONST           ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")

135:          54 LOAD_CONST           ("*/*")

136:          56 LOAD_CONST           ("en-US,en;q=0.9")

127:          58 LOAD_CONST           (('Host', 'Cookie', 'Authorization', 'Content-Type', 'Origin', 'Referer', 'User-Agent', 'Accept', 'Accept-Language'))
              60 BUILD_CONST_KEY_MAP  9
              62 STORE_FAST           (headers)

139:          64 LOAD_FAST            (video_id)

140:          66 LOAD_CONST           ("scottyResourceId")
              68 LOAD_CONST           ("id")
              70 LOAD_FAST            (scotty_resource_id)
              72 BUILD_MAP            1
              74 BUILD_MAP            1

141:          76 LOAD_FAST            (language)

142:          78 LOAD_CONST           ("dubbed")

143:          80 LOAD_CONST           ("AUDIO_TRACK_SOURCE_CREATOR")

146:          82 LOAD_CONST           (62)

147:          84 LOAD_CONST           ("1.20250902.04.00")

148:          86 LOAD_CONST           ("en")

149:          88 LOAD_CONST           ("VN")

150:          90 LOAD_CONST           (420)

151:          92 LOAD_CONST           ("USER_INTERFACE_THEME_DARK")

152:          94 LOAD_CONST           (1920)

153:          96 LOAD_CONST           (945)

154:          98 LOAD_CONST           (1)

155:         100 LOAD_CONST           (1)

145:         102 LOAD_CONST           (('clientName', 'clientVersion', 'hl', 'gl', 'utcOffsetMinutes', 'userInterfaceTheme', 'screenWidthPoints', 'screenHeightPoints', 'screenPixelDensity', 'screenDensityFloat'))
             104 BUILD_CONST_KEY_MAP  10

158:         106 LOAD_CONST           (True)

159:         108 BUILD_LIST           0

160:         110 LOAD_CONST           ("AWSNWa0l7AGlCHtnt233UutuGGeh33lZ817vfraxpNhL8LY5gqkpaiN73HzUXyRRQ2ApQuCVRfHRtr9rlEQ8rczpjRVn_mm0nP74Qdc4IR95HbzJKhorwIoTVAqfC4o=")

161:         112 LOAD_CONST           ("token")
             114 LOAD_FAST            (session_token)
             116 BUILD_MAP            1

157:         118 LOAD_CONST           (('returnLogEntry', 'internalExperimentFlags', 'eats', 'sessionInfo'))
             120 BUILD_CONST_KEY_MAP  4

164:         122 LOAD_FAST            (channel_info)
             124 LOAD_ATTR            (delegated_session_id)

166:         144 LOAD_FAST            (channel_info)
             146 LOAD_ATTR            (id)

167:         166 LOAD_CONST           ("channelRoleType")
             168 LOAD_FAST            (channel_info)
             170 LOAD_ATTR            (role)
             190 BUILD_MAP            1

165:         192 LOAD_CONST           (('externalChannelId', 'roleType'))
             194 BUILD_CONST_KEY_MAP  2

169:         196 LOAD_CONST           ("")

163:         198 LOAD_CONST           (('onBehalfOfUser', 'delegationContext', 'serializedDelegationContext'))
             200 BUILD_CONST_KEY_MAP  3

171:         202 LOAD_CONST           ("visualElement")
             204 LOAD_CONST           ("veType")
             206 LOAD_CONST           (74618)
             208 BUILD_MAP            1
             210 BUILD_MAP            1

172:         212 LOAD_CONST           ("UUFKQY_AX3QaOzkG")

144:         214 LOAD_CONST           (('client', 'request', 'user', 'clickTracking', 'clientScreenNonce'))
             216 BUILD_CONST_KEY_MAP  5

138:         218 LOAD_CONST           (('videoId', 'resourceId', 'language', 'audioContentTypeString', 'audioTrackSource', 'context'))
             220 BUILD_CONST_KEY_MAP  6
             222 STORE_FAST           (payload)

175:         224 LOAD_GLOBAL          (NULL + requests)
             234 LOAD_ATTR            (post)
             254 LOAD_FAST            (url)
             256 LOAD_FAST            (headers)
             258 LOAD_FAST            (payload)
             260 KW_NAMES             (('headers', 'json'))
             262 CALL                 3
             270 STORE_FAST           (response)

176:         272 LOAD_FAST            (response)
             274 LOAD_ATTR            (status_code)
             294 RETURN_VALUE


# Method Name:       delete
# Filename:          src\module\audio_module.py
# Argument count:    3
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  13
# Stack size:        16
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        178
# Constants:
#    0: None
#    1: 'https://studio.youtube.com/youtubei/v1/creator/delete_audio_track?alt=json'
#    2: '; '
#    3: 'name'
#    4: '='
#    5: 'value'
#    6: 'studio.youtube.com'
#    7: 'SAPISIDHASH '
#    8: 'application/json'
#    9: 'https://studio.youtube.com'
#   10: 'https://studio.youtube.com/video/'
#   11: '/translations'
#   12: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'
#   13: ('Host', 'Cookie', 'Authorization', 'Content-Type', 'Origin', 'Referer', 'User-Agent')
#   14: False
#   15: 62
#   16: '1.20250902.04.00'
#   17: 'en'
#   18: 'VN'
#   19: ''
#   20: 420
#   21: 'USER_INTERFACE_THEME_DARK'
#   22: 1920
#   23: 945
#   24: 1
#   25: ('clientName', 'clientVersion', 'hl', 'gl', 'experimentsToken', 'utcOffsetMinutes', 'userInterfaceTheme', 'screenWidthPoints', 'screenHeightPoints', 'screenPixelDensity', 'screenDensityFloat')
#   26: True
#   27: 'AWSNWa3PV1e-JQRiHlmMmNXCMA9Kt6en05uq7bbw9WnQgnJdNT8RNsEfMheyglxoOPf_TMIzUzU80CM9khDsuy6zp2Uz9ROtcC5RGvGrdEkSa_rIL5z6FDB2wAAYVWg='
#   28: 'token'
#   29: ('returnLogEntry', 'internalExperimentFlags', 'eats', 'sessionInfo')
#   30: 'channelRoleType'
#   31: ('externalChannelId', 'roleType')
#   32: ('onBehalfOfUser', 'delegationContext', 'serializedDelegationContext')
#   33: '7nFa5dcSfcGGJAJS'
#   34: ('client', 'request', 'user', 'clientScreenNonce')
#   35: ('videoId', 'audioTrackId', 'unpublishTrack', 'context')
#   36: ('headers', 'json')
#   37: 200
#   38: 'Failed to delete audio track: '
# Names:
#    0: get_channels_info
#    1: join
#    2: cookies
#    3: _get_session_token
#    4: _get_all_audio_track_ids
#    5: sapisidhash
#    6: delegated_session_id
#    7: id
#    8: role
#    9: requests
#   10: post
#   11: status_code
#   12: logger
#   13: exception
# Varnames:
#	self, id_video, channel_id, channel_info, url, cookie, cookie_string, session_token, all_track_ids, headers, track_id, payload, response
# Positional arguments:
#	self, id_video, channel_id
# Local variables:
#    3: channel_info
#    4: url
#    5: cookie
#    6: cookie_string
#    7: session_token
#    8: all_track_ids
#    9: headers
#   10: track_id
#   11: payload
#   12: response

178:           0 RESUME               0

179:           2 LOAD_GLOBAL          (NULL + get_channels_info)
              12 LOAD_FAST            (channel_id)
              14 CALL                 1
              22 STORE_FAST           (channel_info)

181:          24 LOAD_CONST           ("https://studio.youtube.com/youtubei/v1/creator/delete_audio_track?alt=json")

180:          26 STORE_FAST           (url)

184:          28 LOAD_CONST           ("; ")
              30 LOAD_ATTR            (NULL|self + join)

187:          50 LOAD_FAST            (channel_info)
              52 LOAD_ATTR            (cookies)
              72 GET_ITER

185:          74 LOAD_FAST_AND_CLEAR  (cookie)
              76 SWAP                 (TOS <-> TOS1)
              78 BUILD_LIST           0
              80 SWAP                 (TOS <-> TOS1)

187:          82 FOR_ITER             (to 116)
              86 STORE_FAST           (cookie)

186:          88 LOAD_FAST            (cookie)
              90 LOAD_CONST           ("name")
              92 BINARY_SUBSCR
              96 FORMAT_VALUE         0
              98 LOAD_CONST           ("=")
             100 LOAD_FAST            (cookie)
             102 LOAD_CONST           ("value")
             104 BINARY_SUBSCR
             108 FORMAT_VALUE         0
             110 BUILD_STRING         3
             112 LIST_APPEND          2
         >>  114 JUMP_BACKWARD        (to 82)

187:         116 END_FOR

185:         118 SWAP                 (TOS <-> TOS1)
             120 STORE_FAST           (cookie)

184:         122 CALL                 1
             130 STORE_FAST           (cookie_string)

190:         132 LOAD_FAST            (self)
             134 LOAD_ATTR            (NULL|self + _get_session_token)
             154 LOAD_FAST            (channel_info)
             156 CALL                 1
             164 STORE_FAST           (session_token)

191:         166 LOAD_FAST            (self)
             168 LOAD_ATTR            (NULL|self + _get_all_audio_track_ids)
             188 LOAD_FAST            (id_video)
             190 LOAD_FAST            (channel_id)
             192 CALL                 2
             200 STORE_FAST           (all_track_ids)

193:         202 LOAD_CONST           ("studio.youtube.com")

194:         204 LOAD_FAST            (cookie_string)

195:         206 LOAD_CONST           ("SAPISIDHASH ")
             208 LOAD_FAST            (channel_info)
             210 LOAD_ATTR            (sapisidhash)
             230 FORMAT_VALUE         0
             232 BUILD_STRING         2

196:         234 LOAD_CONST           ("application/json")

197:         236 LOAD_CONST           ("https://studio.youtube.com")

198:         238 LOAD_CONST           ("https://studio.youtube.com/video/")
             240 LOAD_FAST            (id_video)
             242 FORMAT_VALUE         0
             244 LOAD_CONST           ("/translations")
             246 BUILD_STRING         3

199:         248 LOAD_CONST           ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")

192:         250 LOAD_CONST           (('Host', 'Cookie', 'Authorization', 'Content-Type', 'Origin', 'Referer', 'User-Agent'))
             252 BUILD_CONST_KEY_MAP  7
             254 STORE_FAST           (headers)

201:         256 LOAD_FAST            (all_track_ids)
             258 GET_ITER
             260 FOR_ITER             (to 536)
             264 STORE_FAST           (track_id)

203:         266 LOAD_FAST            (id_video)

204:         268 LOAD_FAST            (track_id)

205:         270 LOAD_CONST           (False)

208:         272 LOAD_CONST           (62)

209:         274 LOAD_CONST           ("1.20250902.04.00")

210:         276 LOAD_CONST           ("en")

211:         278 LOAD_CONST           ("VN")

212:         280 LOAD_CONST           ("")

213:         282 LOAD_CONST           (420)

214:         284 LOAD_CONST           ("USER_INTERFACE_THEME_DARK")

215:         286 LOAD_CONST           (1920)

216:         288 LOAD_CONST           (945)

217:         290 LOAD_CONST           (1)

218:         292 LOAD_CONST           (1)

207:         294 LOAD_CONST           (('clientName', 'clientVersion', 'hl', 'gl', 'experimentsToken', 'utcOffsetMinutes', 'userInterfaceTheme', 'screenWidthPoints', 'screenHeightPoints', 'screenPixelDensity', 'screenDensityFloat'))
             296 BUILD_CONST_KEY_MAP  11

221:         298 LOAD_CONST           (True)

222:         300 BUILD_LIST           0

223:         302 LOAD_CONST           ("AWSNWa3PV1e-JQRiHlmMmNXCMA9Kt6en05uq7bbw9WnQgnJdNT8RNsEfMheyglxoOPf_TMIzUzU80CM9khDsuy6zp2Uz9ROtcC5RGvGrdEkSa_rIL5z6FDB2wAAYVWg=")

224:         304 LOAD_CONST           ("token")
             306 LOAD_FAST            (session_token)
             308 BUILD_MAP            1

220:         310 LOAD_CONST           (('returnLogEntry', 'internalExperimentFlags', 'eats', 'sessionInfo'))
             312 BUILD_CONST_KEY_MAP  4

227:         314 LOAD_FAST            (channel_info)
             316 LOAD_ATTR            (delegated_session_id)

229:         336 LOAD_FAST            (channel_info)
             338 LOAD_ATTR            (id)

230:         358 LOAD_CONST           ("channelRoleType")
             360 LOAD_FAST            (channel_info)
             362 LOAD_ATTR            (role)
             382 BUILD_MAP            1

228:         384 LOAD_CONST           (('externalChannelId', 'roleType'))
             386 BUILD_CONST_KEY_MAP  2

232:         388 LOAD_CONST           ("")

226:         390 LOAD_CONST           (('onBehalfOfUser', 'delegationContext', 'serializedDelegationContext'))
             392 BUILD_CONST_KEY_MAP  3

234:         394 LOAD_CONST           ("7nFa5dcSfcGGJAJS")

206:         396 LOAD_CONST           (('client', 'request', 'user', 'clientScreenNonce'))
             398 BUILD_CONST_KEY_MAP  4

202:         400 LOAD_CONST           (('videoId', 'audioTrackId', 'unpublishTrack', 'context'))
             402 BUILD_CONST_KEY_MAP  4
             404 STORE_FAST           (payload)

237:         406 LOAD_GLOBAL          (NULL + requests)
             416 LOAD_ATTR            (post)
             436 LOAD_FAST            (url)
             438 LOAD_FAST            (headers)
             440 LOAD_FAST            (payload)
             442 KW_NAMES             (('headers', 'json'))
             444 CALL                 3
             452 STORE_FAST           (response)

238:         454 LOAD_FAST            (response)
             456 LOAD_ATTR            (status_code)
             476 LOAD_CONST           (200)
             478 COMPARE_OP           (!=)
             482 POP_JUMP_IF_TRUE     (to 486)
             484 JUMP_BACKWARD        (to 260)

239:     >>  486 LOAD_GLOBAL          (NULL + logger)
             496 LOAD_ATTR            (exception)
             516 LOAD_CONST           ("Failed to delete audio track: ")
             518 LOAD_FAST            (response)
             520 FORMAT_VALUE         0
             522 BUILD_STRING         2
             524 CALL                 1
             532 POP_TOP
         >>  534 JUMP_BACKWARD        (to 260)

201:         536 END_FOR
             538 RETURN_CONST         (None)
             540 SWAP                 (TOS <-> TOS1)
             542 POP_TOP

185:         544 SWAP                 (TOS <-> TOS1)
             546 STORE_FAST           (cookie)
             548 RERAISE              0

ExceptionTable:
  78 to 116 -> 540 [4]

# Method Name:       _get_all_audio_track_ids
# Filename:          src\module\audio_module.py
# Argument count:    3
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  13
# Stack size:        12
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        241
# Constants:
#    0: None
#    1: 'https://studio.youtube.com/youtubei/v1/crowdsourcing/get_video_translations?alt=json'
#    2: '; '
#    3: 'name'
#    4: '='
#    5: 'value'
#    6: 'studio.youtube.com'
#    7: 'SAPISIDHASH '
#    8: 'application/json'
#    9: 'https://studio.youtube.com'
#   10: 'https://studio.youtube.com/video/'
#   11: '/translations'
#   12: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'
#   13: ('Host', 'Cookie', 'Authorization', 'Content-Type', 'Origin', 'Referer', 'User-Agent')
#   14: 62
#   15: '1.20250902.04.00'
#   16: 'en'
#   17: 'VN'
#   18: ''
#   19: 420
#   20: 'USER_INTERFACE_THEME_DARK'
#   21: 1920
#   22: 945
#   23: 1
#   24: ('clientName', 'clientVersion', 'hl', 'gl', 'experimentsToken', 'utcOffsetMinutes', 'userInterfaceTheme', 'screenWidthPoints', 'screenHeightPoints', 'screenPixelDensity', 'screenDensityFloat')
#   25: True
#   26: 'AWSNWa3PV1e-JQRiHlmMmNXCMA9Kt6en05uq7bbw9WnQgnJdNT8RNsEfMheyglxoOPf_TMIzUzU80CM9khDsuy6zp2Uz9ROtcC5RGvGrdEkSa_rIL5z6FDB2wAAYVWg='
#   27: 'token'
#   28: ('returnLogEntry', 'internalExperimentFlags', 'eats', 'sessionInfo', 'consistencyTokenJars')
#   29: 'channelRoleType'
#   30: ('externalChannelId', 'roleType')
#   31: ('onBehalfOfUser', 'delegationContext', 'serializedDelegationContext')
#   32: '7nFa5dcSfcGGJAJS'
#   33: ('client', 'request', 'user', 'clientScreenNonce')
#   34: False
#   35: ('context', 'videoIds', 'filters', 'fetchAloudData', 'fetchAutoDubbingData', 'fetchAutoDubbingAsrData', 'fetchBulkActionsStatus')
#   36: ('headers', 'json')
#   37: 200
#   38: 'Failed to get audio track IDs: '
#   39: 'videoTranslations'
#   40: 0
#   41: 'translations'
#   42: 'audioTranslation'
#   43: 'audioTrackId'
# Names:
#    0: get_channels_info
#    1: join
#    2: cookies
#    3: _get_session_token
#    4: sapisidhash
#    5: delegated_session_id
#    6: id
#    7: role
#    8: requests
#    9: post
#   10: status_code
#   11: Exception
#   12: json
#   13: append
# Varnames:
#	self, id_video, channel_id, url, channel_info, cookie, cookie_string, session_token, headers, payload, response, all_track_ids, item
# Positional arguments:
#	self, id_video, channel_id
# Local variables:
#    3: url
#    4: channel_info
#    5: cookie
#    6: cookie_string
#    7: session_token
#    8: headers
#    9: payload
#   10: response
#   11: all_track_ids
#   12: item

241:           0 RESUME               0

242:           2 LOAD_CONST           ("https://studio.youtube.com/youtubei/v1/crowdsourcing/get_video_translations?alt=json")
               4 STORE_FAST           (url)

243:           6 LOAD_GLOBAL          (NULL + get_channels_info)
              16 LOAD_FAST            (channel_id)
              18 CALL                 1
              26 STORE_FAST           (channel_info)

244:          28 LOAD_CONST           ("; ")
              30 LOAD_ATTR            (NULL|self + join)

247:          50 LOAD_FAST            (channel_info)
              52 LOAD_ATTR            (cookies)
              72 GET_ITER

245:          74 LOAD_FAST_AND_CLEAR  (cookie)
              76 SWAP                 (TOS <-> TOS1)
              78 BUILD_LIST           0
              80 SWAP                 (TOS <-> TOS1)

247:          82 FOR_ITER             (to 116)
              86 STORE_FAST           (cookie)

246:          88 LOAD_FAST            (cookie)
              90 LOAD_CONST           ("name")
              92 BINARY_SUBSCR
              96 FORMAT_VALUE         0
              98 LOAD_CONST           ("=")
             100 LOAD_FAST            (cookie)
             102 LOAD_CONST           ("value")
             104 BINARY_SUBSCR
             108 FORMAT_VALUE         0
             110 BUILD_STRING         3
             112 LIST_APPEND          2
         >>  114 JUMP_BACKWARD        (to 82)

247:         116 END_FOR

245:         118 SWAP                 (TOS <-> TOS1)
             120 STORE_FAST           (cookie)

244:         122 CALL                 1
             130 STORE_FAST           (cookie_string)

250:         132 LOAD_FAST            (self)
             134 LOAD_ATTR            (NULL|self + _get_session_token)
             154 LOAD_FAST            (channel_info)
             156 CALL                 1
             164 STORE_FAST           (session_token)

253:         166 LOAD_CONST           ("studio.youtube.com")

254:         168 LOAD_FAST            (cookie_string)

255:         170 LOAD_CONST           ("SAPISIDHASH ")
             172 LOAD_FAST            (channel_info)
             174 LOAD_ATTR            (sapisidhash)
             194 FORMAT_VALUE         0
             196 BUILD_STRING         2

256:         198 LOAD_CONST           ("application/json")

257:         200 LOAD_CONST           ("https://studio.youtube.com")

258:         202 LOAD_CONST           ("https://studio.youtube.com/video/")
             204 LOAD_FAST            (id_video)
             206 FORMAT_VALUE         0
             208 LOAD_CONST           ("/translations")
             210 BUILD_STRING         3

259:         212 LOAD_CONST           ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")

252:         214 LOAD_CONST           (('Host', 'Cookie', 'Authorization', 'Content-Type', 'Origin', 'Referer', 'User-Agent'))
             216 BUILD_CONST_KEY_MAP  7
             218 STORE_FAST           (headers)

264:         220 LOAD_CONST           (62)

265:         222 LOAD_CONST           ("1.20250902.04.00")

266:         224 LOAD_CONST           ("en")

267:         226 LOAD_CONST           ("VN")

268:         228 LOAD_CONST           ("")

269:         230 LOAD_CONST           (420)

270:         232 LOAD_CONST           ("USER_INTERFACE_THEME_DARK")

271:         234 LOAD_CONST           (1920)

272:         236 LOAD_CONST           (945)

273:         238 LOAD_CONST           (1)

274:         240 LOAD_CONST           (1)

263:         242 LOAD_CONST           (('clientName', 'clientVersion', 'hl', 'gl', 'experimentsToken', 'utcOffsetMinutes', 'userInterfaceTheme', 'screenWidthPoints', 'screenHeightPoints', 'screenPixelDensity', 'screenDensityFloat'))
             244 BUILD_CONST_KEY_MAP  11

277:         246 LOAD_CONST           (True)

278:         248 BUILD_LIST           0

279:         250 LOAD_CONST           ("AWSNWa3PV1e-JQRiHlmMmNXCMA9Kt6en05uq7bbw9WnQgnJdNT8RNsEfMheyglxoOPf_TMIzUzU80CM9khDsuy6zp2Uz9ROtcC5RGvGrdEkSa_rIL5z6FDB2wAAYVWg=")

280:         252 LOAD_CONST           ("token")
             254 LOAD_FAST            (session_token)
             256 BUILD_MAP            1

281:         258 BUILD_LIST           0

276:         260 LOAD_CONST           (('returnLogEntry', 'internalExperimentFlags', 'eats', 'sessionInfo', 'consistencyTokenJars'))
             262 BUILD_CONST_KEY_MAP  5

284:         264 LOAD_FAST            (channel_info)
             266 LOAD_ATTR            (delegated_session_id)

286:         286 LOAD_FAST            (channel_info)
             288 LOAD_ATTR            (id)

287:         308 LOAD_CONST           ("channelRoleType")
             310 LOAD_FAST            (channel_info)
             312 LOAD_ATTR            (role)
             332 BUILD_MAP            1

285:         334 LOAD_CONST           (('externalChannelId', 'roleType'))
             336 BUILD_CONST_KEY_MAP  2

289:         338 LOAD_CONST           ("")

283:         340 LOAD_CONST           (('onBehalfOfUser', 'delegationContext', 'serializedDelegationContext'))
             342 BUILD_CONST_KEY_MAP  3

291:         344 LOAD_CONST           ("7nFa5dcSfcGGJAJS")

262:         346 LOAD_CONST           (('client', 'request', 'user', 'clientScreenNonce'))
             348 BUILD_CONST_KEY_MAP  4

293:         350 LOAD_FAST            (id_video)
             352 BUILD_LIST           1

294:         354 BUILD_LIST           0

295:         356 LOAD_CONST           (False)

296:         358 LOAD_CONST           (False)

297:         360 LOAD_CONST           (False)

298:         362 LOAD_CONST           (False)

261:         364 LOAD_CONST           (('context', 'videoIds', 'filters', 'fetchAloudData', 'fetchAutoDubbingData', 'fetchAutoDubbingAsrData', 'fetchBulkActionsStatus'))
             366 BUILD_CONST_KEY_MAP  7
             368 COPY                 1
             370 STORE_FAST           (payload)
             372 STORE_FAST           (payload)

300:         374 LOAD_GLOBAL          (NULL + requests)
             384 LOAD_ATTR            (post)
             404 LOAD_FAST            (url)
             406 LOAD_FAST            (headers)
             408 LOAD_FAST            (payload)
             410 KW_NAMES             (('headers', 'json'))
             412 CALL                 3
             420 STORE_FAST           (response)

302:         422 LOAD_FAST            (response)
             424 LOAD_ATTR            (status_code)
             444 LOAD_CONST           (200)
             446 COMPARE_OP           (!=)
             450 POP_JUMP_IF_FALSE    (to 500)

303:         452 LOAD_GLOBAL          (NULL + Exception)
             462 LOAD_CONST           ("Failed to get audio track IDs: ")
             464 LOAD_FAST            (response)
             466 LOAD_ATTR            (status_code)
             486 FORMAT_VALUE         0
             488 BUILD_STRING         2
             490 CALL                 1
             498 RAISE_VARARGS        (exception instance)

305:     >>  500 BUILD_LIST           0
             502 STORE_FAST           (all_track_ids)

306:         504 LOAD_FAST            (response)
             506 LOAD_ATTR            (NULL|self + json)
             526 CALL                 0
             534 LOAD_CONST           ("videoTranslations")
             536 BINARY_SUBSCR
             540 LOAD_CONST           (0)
             542 BINARY_SUBSCR
             546 LOAD_CONST           ("translations")
             548 BINARY_SUBSCR
             552 GET_ITER
             554 FOR_ITER             (to 610)
             558 STORE_FAST           (item)

307:         560 NOP

308:         562 LOAD_FAST            (all_track_ids)
             564 LOAD_ATTR            (NULL|self + append)
             584 LOAD_FAST            (item)
             586 LOAD_CONST           ("audioTranslation")
             588 BINARY_SUBSCR
             592 LOAD_CONST           ("audioTrackId")
             594 BINARY_SUBSCR
             598 CALL                 1
             606 POP_TOP
         >>  608 JUMP_BACKWARD        (to 554)

306:         610 END_FOR

312:         612 LOAD_FAST            (all_track_ids)
             614 RETURN_VALUE
             616 SWAP                 (TOS <-> TOS1)
             618 POP_TOP

245:         620 SWAP                 (TOS <-> TOS1)
             622 STORE_FAST           (cookie)
             624 RERAISE              0
             626 PUSH_EXC_INFO

309:         628 POP_TOP

310:         630 POP_EXCEPT
             632 JUMP_BACKWARD        (to 554)
             634 COPY                 3
             636 POP_EXCEPT
             638 RERAISE              1

ExceptionTable:
  78 to 116 -> 616 [4]
  562 to 606 -> 626 [1]
  626 to 628 -> 634 [2] lasti

# Method Name:       background_upload
# Filename:          src\module\audio_module.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  1
# Stack size:        9
# Flags:             0x00000013 (NESTED | NEWLOCALS | OPTIMIZED)
# First Line:        45
# Constants:
#    0: None
#    1: ('next_url', 'fname_header', 'cookie_string', 'data')
#    2: 'Background upload failed for video '
#    3: ', language '
#    4: ': '
# Names:
#    0: _next_upload_http
#    1: Exception
#    2: logger
#    3: error
# Varnames:
#	e
# Local variables:
#    0: e
# Free variables:
#    0: cookie_string
#    1: data
#    2: fname_header
#    3: id_video
#    4: language
#    5: self
#    6: upload_url
               0 COPY_FREE_VARS       7

 45:           2 RESUME               0

 46:           4 NOP

 47:           6 LOAD_DEREF           (self)
               8 LOAD_ATTR            (NULL|self + _next_upload_http)

 48:          28 LOAD_DEREF           (upload_url)

 49:          30 LOAD_DEREF           (fname_header)

 50:          32 LOAD_DEREF           (cookie_string)

 51:          34 LOAD_DEREF           (data)

 47:          36 KW_NAMES             (('next_url', 'fname_header', 'cookie_string', 'data'))
              38 CALL                 4
              46 POP_TOP
              48 RETURN_CONST         (None)
              50 PUSH_EXC_INFO

 54:          52 LOAD_GLOBAL          (Exception)
              62 CHECK_EXC_MATCH
              64 POP_JUMP_IF_FALSE    (to 146)
              66 STORE_FAST           (e)

 55:          68 LOAD_GLOBAL          (NULL + logger)
              78 LOAD_ATTR            (error)

 56:          98 LOAD_CONST           ("Background upload failed for video ")
             100 LOAD_DEREF           (id_video)
             102 FORMAT_VALUE         0
             104 LOAD_CONST           (", language ")
             106 LOAD_DEREF           (language)
             108 FORMAT_VALUE         0
             110 LOAD_CONST           (": ")
             112 LOAD_FAST            (e)
             114 FORMAT_VALUE         0
             116 BUILD_STRING         6

 55:         118 CALL                 1
             126 POP_TOP
             128 POP_EXCEPT
             130 LOAD_CONST           (None)
             132 STORE_FAST           (e)
             134 DELETE_FAST          (e)
             136 RETURN_CONST         (None)
             138 LOAD_CONST           (None)
             140 STORE_FAST           (e)
             142 DELETE_FAST          (e)
             144 RERAISE              1

 54:     >>  146 RERAISE              0
             148 COPY                 3
             150 POP_EXCEPT
             152 RERAISE              1

ExceptionTable:
  6 to 46 -> 50 [0]
  50 to 66 -> 148 [1] lasti
  68 to 126 -> 138 [1] lasti
  138 to 146 -> 148 [1] lasti
```
