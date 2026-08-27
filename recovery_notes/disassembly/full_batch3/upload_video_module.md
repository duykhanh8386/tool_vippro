# Static CPython 3.12 disassembly — `upload_video_module.pyc`

Generated with `xdis 6.3.0`; the code object was deserialized but never executed.

```text
# pydisasm version 6.3.0
# CPython Python bytecode 3.12.0 (3531)
#   Disassembled from CPython Python 3.13.13 | packaged by Anaconda, Inc. | (main, Apr 14 2026, 06:12:50) [MSC v.1942 64 bit (AMD64)]
# Timestamp in code: 0 (1970-01-01 07:00:00)
# Source code size mod 2**32: 0 bytes
# Method Name:       <module>
# Filename:          src\module\upload_video_module.py
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
#    5: ('get_channels_info',)
#    6: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36'
#    7: 'index'
#    8: 'return'
#    9: <Code311 code object make_frontend_upload_id at 0x2e1d0133130, file src\module\upload_video_module.py>, line 19
#   10: 'title'
#   11: <Code311 code object _sanitize_title at 0x2e1d0133240, file src\module\upload_video_module.py>, line 24
#   12: <Code311 code object UploadVideoModule at 0x2e1d01338a0, file src\module\upload_video_module.py>, line 37
#   13: 'UploadVideoModule'
#   14: (0,)
# Names:
#    0: json
#    1: os
#    2: time
#    3: uuid
#    4: urllib.parse
#    5: quote
#    6: requests
#    7: loguru
#    8: logger
#    9: src.module.base
#   10: IModule
#   11: src.utils
#   12: get_channels_info
#   13: _USER_AGENT
#   14: int
#   15: str
#   16: make_frontend_upload_id
#   17: _sanitize_title
#   18: UploadVideoModule
#   19: upload_video_module

  0:           0 RESUME               0

  1:           2 LOAD_CONST           (0)
               4 LOAD_CONST           (None)
               6 IMPORT_NAME          (json)
               8 STORE_NAME           (json)

  2:          10 LOAD_CONST           (0)
              12 LOAD_CONST           (None)
              14 IMPORT_NAME          (os)
              16 STORE_NAME           (os)

  3:          18 LOAD_CONST           (0)
              20 LOAD_CONST           (None)
              22 IMPORT_NAME          (time)
              24 STORE_NAME           (time)

  4:          26 LOAD_CONST           (0)
              28 LOAD_CONST           (None)
              30 IMPORT_NAME          (uuid)
              32 STORE_NAME           (uuid)

  5:          34 LOAD_CONST           (0)
              36 LOAD_CONST           (('quote',))
              38 IMPORT_NAME          (urllib.parse)
              40 IMPORT_FROM          (quote)
              42 STORE_NAME           (quote)
              44 POP_TOP

  7:          46 LOAD_CONST           (0)
              48 LOAD_CONST           (None)
              50 IMPORT_NAME          (requests)
              52 STORE_NAME           (requests)

  8:          54 LOAD_CONST           (0)
              56 LOAD_CONST           (('logger',))
              58 IMPORT_NAME          (loguru)
              60 IMPORT_FROM          (logger)
              62 STORE_NAME           (logger)
              64 POP_TOP

 10:          66 LOAD_CONST           (0)
              68 LOAD_CONST           (('IModule',))
              70 IMPORT_NAME          (src.module.base)
              72 IMPORT_FROM          (IModule)
              74 STORE_NAME           (IModule)
              76 POP_TOP

 11:          78 LOAD_CONST           (0)
              80 LOAD_CONST           (('get_channels_info',))
              82 IMPORT_NAME          (src.utils)
              84 IMPORT_FROM          (get_channels_info)
              86 STORE_NAME           (get_channels_info)
              88 POP_TOP

 14:          90 LOAD_CONST           ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36")

 13:          92 STORE_NAME           (_USER_AGENT)

 19:          94 LOAD_CONST           ((0,))
              96 LOAD_CONST           ("index")
              98 LOAD_NAME            (int)
             100 LOAD_CONST           ("return")
             102 LOAD_NAME            (str)
             104 BUILD_TUPLE          4
             106 LOAD_CONST           (<Code311 code object make_frontend_upload_id at 0x2e1d0133130, file src\module\upload_video_module.py>, line 19)
             108 MAKE_FUNCTION        (default, annotation)
             110 STORE_NAME           (make_frontend_upload_id)

 24:         112 LOAD_CONST           ("title")
             114 LOAD_NAME            (str)
             116 LOAD_CONST           ("return")
             118 LOAD_NAME            (str)
             120 BUILD_TUPLE          4
             122 LOAD_CONST           (<Code311 code object _sanitize_title at 0x2e1d0133240, file src\module\upload_video_module.py>, line 24)
             124 MAKE_FUNCTION        (annotation)
             126 STORE_NAME           (_sanitize_title)

 37:         128 PUSH_NULL
             130 LOAD_BUILD_CLASS
             132 LOAD_CONST           (<Code311 code object UploadVideoModule at 0x2e1d01338a0, file src\module\upload_video_module.py>, line 37)
             134 MAKE_FUNCTION        (No arguments)
             136 LOAD_CONST           ("UploadVideoModule")
             138 LOAD_NAME            (IModule)
             140 CALL                 3
             148 STORE_NAME           (UploadVideoModule)

341:         150 PUSH_NULL
             152 LOAD_NAME            (UploadVideoModule)
             154 CALL                 0
             162 STORE_NAME           (upload_video_module)
             164 RETURN_CONST         (None)


# Method Name:       make_frontend_upload_id
# Filename:          src\module\upload_video_module.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  1
# Stack size:        5
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        19
# Constants:
#    0: 'Client-generated id for an upload session (không lấy từ server).'
#    1: 'innertube_studio:'
#    2: ':'
# Names:
#    0: str
#    1: uuid
#    2: uuid4
#    3: upper
# Varnames:
#	index
# Positional arguments:
#	index

 19:           0 RESUME               0

 21:           2 LOAD_CONST           ("innertube_studio:")
               4 LOAD_GLOBAL          (NULL + str)
              14 LOAD_GLOBAL          (NULL + uuid)
              24 LOAD_ATTR            (uuid4)
              44 CALL                 0
              52 CALL                 1
              60 LOAD_ATTR            (NULL|self + upper)
              80 CALL                 0
              88 FORMAT_VALUE         0
              90 LOAD_CONST           (":")
              92 LOAD_FAST            (index)
              94 FORMAT_VALUE         0
              96 BUILD_STRING         4
              98 RETURN_VALUE


# Method Name:       _sanitize_title
# Filename:          src\module\upload_video_module.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  2
# Stack size:        4
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        24
# Constants:
#    0: "YouTube title: bỏ '<' '>' và xuống dòng, cắt tối đa 100 ký tự."
#    1: ''
#    2: '<'
#    3: '>'
#    4: '\n'
#    5: ' '
#    6: '\r'
#    7: None
#    8: 100
#    9: 'Untitled'
# Names:
#    0: replace
#    1: strip
# Varnames:
#	title, cleaned
# Positional arguments:
#	title
# Local variables:
#    1: cleaned

 24:           0 RESUME               0

 27:           2 LOAD_FAST            (title)
               4 COPY                 1
               6 POP_JUMP_IF_TRUE     (to 12)
               8 POP_TOP
              10 LOAD_CONST           ("")

 28:     >>   12 LOAD_ATTR            (NULL|self + replace)
              32 LOAD_CONST           ("<")
              34 LOAD_CONST           ("")
              36 CALL                 2

 29:          44 LOAD_ATTR            (NULL|self + replace)
              64 LOAD_CONST           (">")
              66 LOAD_CONST           ("")
              68 CALL                 2

 30:          76 LOAD_ATTR            (NULL|self + replace)
              96 LOAD_CONST           ("\n")
              98 LOAD_CONST           (" ")
             100 CALL                 2

 31:         108 LOAD_ATTR            (NULL|self + replace)
             128 LOAD_CONST           ("\r")
             130 LOAD_CONST           (" ")
             132 CALL                 2

 32:         140 LOAD_ATTR            (NULL|self + strip)
             160 CALL                 0

 26:         168 STORE_FAST           (cleaned)

 34:         170 LOAD_FAST            (cleaned)
             172 LOAD_CONST           (None)
             174 LOAD_CONST           (100)
             176 BINARY_SLICE
             178 COPY                 1
             180 POP_JUMP_IF_TRUE     (to 186)
             182 POP_TOP
             184 LOAD_CONST           ("Untitled")
         >>  186 RETURN_VALUE


# Method Name:       UploadVideoModule
# Filename:          src\module\upload_video_module.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        19
# Flags:             0x00000000 (0x0)
# First Line:        37
# Constants:
#    0: 'UploadVideoModule'
#    1: 'Upload một file video lên YouTube qua resumable protocol (chặng 1 + 2).\n\n    Chặng 3 (tạo video + set title/description) sẽ được bổ sung sau.\n    '
#    2: 67108864
#    3: 5
#    4: None
#    5: 'channel_id'
#    6: 'file_path'
#    7: 'index'
#    8: 'progress'
#    9: 'return'
#   10: <Code311 code object upload at 0x2e1d0133350, file src\module\upload_video_module.py>, line 47
#   11: 'cookie_string'
#   12: 'fname_header'
#   13: 'file_size'
#   14: 'frontend_upload_id'
#   15: <Code311 code object _start at 0x2e1d0133460, file src\module\upload_video_module.py>, line 103
#   16: <Code311 code object _base_upload_headers at 0x2e1d0133570, file src\module\upload_video_module.py>, line 151
#   17: 'upload_url'
#   18: 'base_headers'
#   19: <Code311 code object _query_offset at 0x2e1d0133680, file src\module\upload_video_module.py>, line 163
#   20: 'granularity'
#   21: <Code311 code object _upload_bytes at 0x2e1d0133790, file src\module\upload_video_module.py>, line 175
#   22: 'scotty_resource_id'
#   23: 'title'
#   24: 'description'
#   25: 'tags'
#   26: 'privacy'
#   27: 'is_draft'
#   28: <Code311 code object create_video at 0x2e1d0133ac0, file src\module\upload_video_module.py>, line 240
#   29: 'video_id'
#   30: <Code311 code object is_processed at 0x2e1d01339b0, file src\module\upload_video_module.py>, line 328
#   31: (0, None)
#   32: (262144, None)
#   33: ('', None, 'PRIVATE', True)
# Names:
#    0: __name__
#    1: __module__
#    2: __qualname__
#    3: __doc__
#    4: _CHUNK_TARGET
#    5: _MAX_CHUNK_RETRIES
#    6: str
#    7: int
#    8: dict
#    9: upload
#   10: tuple
#   11: _start
#   12: _base_upload_headers
#   13: _query_offset
#   14: _upload_bytes
#   15: list
#   16: bool
#   17: create_video
#   18: is_processed

 37:           0 RESUME               0
               2 LOAD_NAME            (__name__)
               4 STORE_NAME           (__module__)
               6 LOAD_CONST           ("UploadVideoModule")
               8 STORE_NAME           (__qualname__)

 38:          10 LOAD_CONST           ("Upload một file video lên YouTube qua resumable protocol (chặng 1 + 2).\n\n    Chặng 3 (tạo video + set title/description) sẽ được bổ sung sau.\n    ")
              12 STORE_NAME           (__doc__)

 44:          14 LOAD_CONST           (67108864)
              16 STORE_NAME           (_CHUNK_TARGET)

 45:          18 LOAD_CONST           (5)
              20 STORE_NAME           (_MAX_CHUNK_RETRIES)

 51:          22 NOP

 52:          24 NOP

 47:          26 LOAD_CONST           ((0, None))
              28 LOAD_CONST           ("channel_id")

 49:          30 LOAD_NAME            (str)

 47:          32 LOAD_CONST           ("file_path")

 50:          34 LOAD_NAME            (str)

 47:          36 LOAD_CONST           ("index")

 51:          38 LOAD_NAME            (int)

 47:          40 LOAD_CONST           ("progress")

 52:          42 LOAD_NAME            (dict)
              44 LOAD_CONST           (None)
              46 BINARY_OP            (|)

 47:          50 LOAD_CONST           ("return")

 53:          52 LOAD_NAME            (dict)

 47:          54 BUILD_TUPLE          10
              56 LOAD_CONST           (<Code311 code object upload at 0x2e1d0133350, file src\module\upload_video_module.py>, line 47)
              58 MAKE_FUNCTION        (default, annotation)
              60 STORE_NAME           (upload)

103:          62 LOAD_CONST           ("cookie_string")

105:          64 LOAD_NAME            (str)

103:          66 LOAD_CONST           ("fname_header")

106:          68 LOAD_NAME            (str)

103:          70 LOAD_CONST           ("file_size")

107:          72 LOAD_NAME            (int)

103:          74 LOAD_CONST           ("frontend_upload_id")

108:          76 LOAD_NAME            (str)

103:          78 LOAD_CONST           ("return")

109:          80 LOAD_NAME            (tuple)
              82 LOAD_NAME            (str)
              84 LOAD_NAME            (str)
              86 LOAD_NAME            (int)
              88 BUILD_TUPLE          3
              90 BINARY_SUBSCR

103:          94 BUILD_TUPLE          10
              96 LOAD_CONST           (<Code311 code object _start at 0x2e1d0133460, file src\module\upload_video_module.py>, line 103)
              98 MAKE_FUNCTION        (annotation)
             100 STORE_NAME           (_start)

151:         102 LOAD_CONST           ("cookie_string")
             104 LOAD_NAME            (str)
             106 LOAD_CONST           ("fname_header")
             108 LOAD_NAME            (str)
             110 LOAD_CONST           ("return")
             112 LOAD_NAME            (dict)
             114 BUILD_TUPLE          6
             116 LOAD_CONST           (<Code311 code object _base_upload_headers at 0x2e1d0133570, file src\module\upload_video_module.py>, line 151)
             118 MAKE_FUNCTION        (annotation)
             120 STORE_NAME           (_base_upload_headers)

163:         122 LOAD_CONST           ("upload_url")
             124 LOAD_NAME            (str)
             126 LOAD_CONST           ("base_headers")
             128 LOAD_NAME            (dict)
             130 LOAD_CONST           ("return")
             132 LOAD_NAME            (int)
             134 LOAD_CONST           (None)
             136 BINARY_OP            (|)
             140 BUILD_TUPLE          6
             142 LOAD_CONST           (<Code311 code object _query_offset at 0x2e1d0133680, file src\module\upload_video_module.py>, line 163)
             144 MAKE_FUNCTION        (annotation)
             146 STORE_NAME           (_query_offset)

181:         148 NOP

182:         150 NOP

175:         152 LOAD_CONST           ((262144, None))
             154 LOAD_CONST           ("upload_url")

177:         156 LOAD_NAME            (str)

175:         158 LOAD_CONST           ("cookie_string")

178:         160 LOAD_NAME            (str)

175:         162 LOAD_CONST           ("fname_header")

179:         164 LOAD_NAME            (str)

175:         166 LOAD_CONST           ("file_path")

180:         168 LOAD_NAME            (str)

175:         170 LOAD_CONST           ("granularity")

181:         172 LOAD_NAME            (int)

175:         174 LOAD_CONST           ("progress")

182:         176 LOAD_NAME            (dict)
             178 LOAD_CONST           (None)
             180 BINARY_OP            (|)

175:         184 LOAD_CONST           ("return")

183:         186 LOAD_CONST           (None)

175:         188 BUILD_TUPLE          14
             190 LOAD_CONST           (<Code311 code object _upload_bytes at 0x2e1d0133790, file src\module\upload_video_module.py>, line 175)
             192 MAKE_FUNCTION        (default, annotation)
             194 STORE_NAME           (_upload_bytes)

246:         196 NOP

247:         198 NOP

248:         200 NOP

249:         202 NOP

240:         204 LOAD_CONST           (('', None, 'PRIVATE', True))
             206 LOAD_CONST           ("channel_id")

242:         208 LOAD_NAME            (str)

240:         210 LOAD_CONST           ("scotty_resource_id")

243:         212 LOAD_NAME            (str)

240:         214 LOAD_CONST           ("frontend_upload_id")

244:         216 LOAD_NAME            (str)

240:         218 LOAD_CONST           ("title")

245:         220 LOAD_NAME            (str)

240:         222 LOAD_CONST           ("description")

246:         224 LOAD_NAME            (str)

240:         226 LOAD_CONST           ("tags")

247:         228 LOAD_NAME            (list)
             230 LOAD_NAME            (str)
             232 BINARY_SUBSCR
             236 LOAD_CONST           (None)
             238 BINARY_OP            (|)

240:         242 LOAD_CONST           ("privacy")

248:         244 LOAD_NAME            (str)

240:         246 LOAD_CONST           ("is_draft")

249:         248 LOAD_NAME            (bool)

240:         250 LOAD_CONST           ("return")

250:         252 LOAD_NAME            (str)

240:         254 BUILD_TUPLE          18
             256 LOAD_CONST           (<Code311 code object create_video at 0x2e1d0133ac0, file src\module\upload_video_module.py>, line 240)
             258 MAKE_FUNCTION        (default, annotation)
             260 STORE_NAME           (create_video)

328:         262 LOAD_CONST           ("channel_id")
             264 LOAD_NAME            (str)
             266 LOAD_CONST           ("video_id")
             268 LOAD_NAME            (str)
             270 LOAD_CONST           ("return")
             272 LOAD_NAME            (bool)
             274 BUILD_TUPLE          6
             276 LOAD_CONST           (<Code311 code object is_processed at 0x2e1d01339b0, file src\module\upload_video_module.py>, line 328)
             278 MAKE_FUNCTION        (annotation)
             280 STORE_NAME           (is_processed)
             282 RETURN_CONST         (None)


# Method Name:       upload
# Filename:          src\module\upload_video_module.py
# Argument count:    5
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  13
# Stack size:        8
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        47
# Constants:
#    0: 'Chạy chặng 1 (start) + chặng 2 (upload theo chunk, resumable).\n\n        `progress` (nếu truyền) là dict được cập nhật {"sent": bytes, "total": bytes}\n        sau mỗi chunk để UI hiển thị %.\n\n        Trả về dict gồm frontend_upload_id, scotty_resource_id (dùng cho chặng 3).\n        '
#    1: 'Không tìm thấy kênh: '
#    2: 'File không tồn tại: '
#    3: ''
#    4: ('safe',)
#    5: ('cookie_string', 'fname_header', 'file_size', 'frontend_upload_id')
#    6: ('upload_url', 'cookie_string', 'fname_header', 'file_path', 'granularity', 'progress')
#    7: "Uploaded '"
#    8: "' (frontendUploadId="
#    9: ')'
#   10: ('frontend_upload_id', 'scotty_resource_id', 'upload_url', 'file_name', 'file_size')
# Names:
#    0: get_channels_info
#    1: Exception
#    2: os
#    3: path
#    4: isfile
#    5: cookie_string
#    6: getsize
#    7: quote
#    8: basename
#    9: make_frontend_upload_id
#   10: _start
#   11: _upload_bytes
#   12: logger
#   13: info
# Varnames:
#	self, channel_id, file_path, index, progress, channel_info, cookie_string, file_size, fname_header, frontend_upload_id, upload_url, scotty_resource_id, granularity
# Positional arguments:
#	self, channel_id, file_path, index, progress
# Local variables:
#    5: channel_info
#    6: cookie_string
#    7: file_size
#    8: fname_header
#    9: frontend_upload_id
#   10: upload_url
#   11: scotty_resource_id
#   12: granularity

 47:           0 RESUME               0

 61:           2 LOAD_GLOBAL          (NULL + get_channels_info)
              12 LOAD_FAST            (channel_id)
              14 CALL                 1
              22 STORE_FAST           (channel_info)

 62:          24 LOAD_FAST            (channel_info)
              26 POP_JUMP_IF_TRUE     (to 56)

 63:          28 LOAD_GLOBAL          (NULL + Exception)
              38 LOAD_CONST           ("Không tìm thấy kênh: ")
              40 LOAD_FAST            (channel_id)
              42 FORMAT_VALUE         0
              44 BUILD_STRING         2
              46 CALL                 1
              54 RAISE_VARARGS        (exception instance)

 65:     >>   56 LOAD_GLOBAL          (os)
              66 LOAD_ATTR            (path)
              86 LOAD_ATTR            (NULL|self + isfile)
             106 LOAD_FAST            (file_path)
             108 CALL                 1
             116 POP_JUMP_IF_TRUE     (to 146)

 66:         118 LOAD_GLOBAL          (NULL + Exception)
             128 LOAD_CONST           ("File không tồn tại: ")
             130 LOAD_FAST            (file_path)
             132 FORMAT_VALUE         0
             134 BUILD_STRING         2
             136 CALL                 1
             144 RAISE_VARARGS        (exception instance)

 68:     >>  146 LOAD_FAST            (channel_info)
             148 LOAD_ATTR            (NULL|self + cookie_string)
             168 CALL                 0
             176 STORE_FAST           (cookie_string)

 69:         178 LOAD_GLOBAL          (os)
             188 LOAD_ATTR            (path)
             208 LOAD_ATTR            (NULL|self + getsize)
             228 LOAD_FAST            (file_path)
             230 CALL                 1
             238 STORE_FAST           (file_size)

 70:         240 LOAD_GLOBAL          (NULL + quote)
             250 LOAD_GLOBAL          (os)
             260 LOAD_ATTR            (path)
             280 LOAD_ATTR            (NULL|self + basename)
             300 LOAD_FAST            (file_path)
             302 CALL                 1
             310 LOAD_CONST           ("")
             312 KW_NAMES             (('safe',))
             314 CALL                 2
             322 STORE_FAST           (fname_header)

 71:         324 LOAD_GLOBAL          (NULL + make_frontend_upload_id)
             334 LOAD_FAST            (index)
             336 CALL                 1
             344 STORE_FAST           (frontend_upload_id)

 74:         346 LOAD_FAST            (self)
             348 LOAD_ATTR            (NULL|self + _start)

 75:         368 LOAD_FAST            (cookie_string)

 76:         370 LOAD_FAST            (fname_header)

 77:         372 LOAD_FAST            (file_size)

 78:         374 LOAD_FAST            (frontend_upload_id)

 74:         376 KW_NAMES             (('cookie_string', 'fname_header', 'file_size', 'frontend_upload_id'))
             378 CALL                 4
             386 UNPACK_SEQUENCE      3
             390 STORE_FAST           (upload_url)
             392 STORE_FAST           (scotty_resource_id)
             394 STORE_FAST           (granularity)

 82:         396 LOAD_FAST            (self)
             398 LOAD_ATTR            (NULL|self + _upload_bytes)

 83:         418 LOAD_FAST            (upload_url)

 84:         420 LOAD_FAST            (cookie_string)

 85:         422 LOAD_FAST            (fname_header)

 86:         424 LOAD_FAST            (file_path)

 87:         426 LOAD_FAST            (granularity)

 88:         428 LOAD_FAST            (progress)

 82:         430 KW_NAMES             (('upload_url', 'cookie_string', 'fname_header', 'file_path', 'granularity', 'progress'))
             432 CALL                 6
             440 POP_TOP

 91:         442 LOAD_GLOBAL          (NULL + logger)
             452 LOAD_ATTR            (info)

 92:         472 LOAD_CONST           ("Uploaded '")
             474 LOAD_GLOBAL          (os)
             484 LOAD_ATTR            (path)
             504 LOAD_ATTR            (NULL|self + basename)
             524 LOAD_FAST            (file_path)
             526 CALL                 1
             534 FORMAT_VALUE         0
             536 LOAD_CONST           ("' (frontendUploadId=")

 93:         538 LOAD_FAST            (frontend_upload_id)
             540 FORMAT_VALUE         0
             542 LOAD_CONST           (")")

 92:         544 BUILD_STRING         5

 91:         546 CALL                 1
             554 POP_TOP

 96:         556 LOAD_FAST            (frontend_upload_id)

 97:         558 LOAD_FAST            (scotty_resource_id)

 98:         560 LOAD_FAST            (upload_url)

 99:         562 LOAD_GLOBAL          (os)
             572 LOAD_ATTR            (path)
             592 LOAD_ATTR            (NULL|self + basename)
             612 LOAD_FAST            (file_path)
             614 CALL                 1

100:         622 LOAD_FAST            (file_size)

 95:         624 LOAD_CONST           (('frontend_upload_id', 'scotty_resource_id', 'upload_url', 'file_name', 'file_size'))
             626 BUILD_CONST_KEY_MAP  5
             628 RETURN_VALUE


# Method Name:       _start
# Filename:          src\module\upload_video_module.py
# Argument count:    5
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  13
# Stack size:        13
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        103
# Constants:
#    0: None
#    1: 'https://upload.youtube.com/upload/studio?authuser=0'
#    2: 'upload.youtube.com'
#    3: 'resumable'
#    4: 'start'
#    5: 'application/x-www-form-urlencoded;charset=UTF-8'
#    6: '*/*'
#    7: 'en-US,en;q=0.9'
#    8: 'https://studio.youtube.com'
#    9: 'https://studio.youtube.com/'
#   10: ('Host', 'Cookie', 'X-Goog-Upload-Protocol', 'X-Goog-Upload-Command', 'X-Goog-Upload-File-Name', 'X-Goog-Upload-Header-Content-Length', 'Content-Type', 'User-Agent', 'Accept', 'Accept-Language', 'Origin', 'Referer')
#   11: 'frontendUploadId'
#   12: ('headers', 'data')
#   13: 200
#   14: 'Upload start thất bại: HTTP '
#   15: 'X-Goog-Upload-Status'
#   16: 'active'
#   17: 'Trạng thái start không hợp lệ: '
#   18: 'X-Goog-Upload-URL'
#   19: 'X-Goog-Upload-Header-Scotty-Resource-Id'
#   20: 'Thiếu upload URL hoặc scotty resource id trong response'
#   21: 'X-Goog-Upload-Chunk-Granularity'
#   22: 262144
# Names:
#    0: str
#    1: _USER_AGENT
#    2: json
#    3: dumps
#    4: requests
#    5: post
#    6: status_code
#    7: Exception
#    8: headers
#    9: get
#   10: int
#   11: TypeError
#   12: ValueError
# Varnames:
#	self, cookie_string, fname_header, file_size, frontend_upload_id, url, headers, body, response, status, upload_url, scotty_resource_id, granularity
# Positional arguments:
#	self, cookie_string, fname_header, file_size, frontend_upload_id
# Local variables:
#    5: url
#    6: headers
#    7: body
#    8: response
#    9: status
#   10: upload_url
#   11: scotty_resource_id
#   12: granularity

103:           0 RESUME               0

110:           2 LOAD_CONST           ("https://upload.youtube.com/upload/studio?authuser=0")
               4 STORE_FAST           (url)

112:           6 LOAD_CONST           ("upload.youtube.com")

113:           8 LOAD_FAST            (cookie_string)

114:          10 LOAD_CONST           ("resumable")

115:          12 LOAD_CONST           ("start")

116:          14 LOAD_FAST            (fname_header)

117:          16 LOAD_GLOBAL          (NULL + str)
              26 LOAD_FAST            (file_size)
              28 CALL                 1

118:          36 LOAD_CONST           ("application/x-www-form-urlencoded;charset=UTF-8")

119:          38 LOAD_GLOBAL          (_USER_AGENT)

120:          48 LOAD_CONST           ("*/*")

121:          50 LOAD_CONST           ("en-US,en;q=0.9")

122:          52 LOAD_CONST           ("https://studio.youtube.com")

123:          54 LOAD_CONST           ("https://studio.youtube.com/")

111:          56 LOAD_CONST           (('Host', 'Cookie', 'X-Goog-Upload-Protocol', 'X-Goog-Upload-Command', 'X-Goog-Upload-File-Name', 'X-Goog-Upload-Header-Content-Length', 'Content-Type', 'User-Agent', 'Accept', 'Accept-Language', 'Origin', 'Referer'))
              58 BUILD_CONST_KEY_MAP  12
              60 STORE_FAST           (headers)

125:          62 LOAD_GLOBAL          (NULL + json)
              72 LOAD_ATTR            (dumps)
              92 LOAD_CONST           ("frontendUploadId")
              94 LOAD_FAST            (frontend_upload_id)
              96 BUILD_MAP            1
              98 CALL                 1
             106 STORE_FAST           (body)

126:         108 LOAD_GLOBAL          (NULL + requests)
             118 LOAD_ATTR            (post)
             138 LOAD_FAST            (url)
             140 LOAD_FAST            (headers)
             142 LOAD_FAST            (body)
             144 KW_NAMES             (('headers', 'data'))
             146 CALL                 3
             154 STORE_FAST           (response)

128:         156 LOAD_FAST            (response)
             158 LOAD_ATTR            (status_code)
             178 LOAD_CONST           (200)
             180 COMPARE_OP           (!=)
             184 POP_JUMP_IF_FALSE    (to 234)

129:         186 LOAD_GLOBAL          (NULL + Exception)
             196 LOAD_CONST           ("Upload start thất bại: HTTP ")
             198 LOAD_FAST            (response)
             200 LOAD_ATTR            (status_code)
             220 FORMAT_VALUE         0
             222 BUILD_STRING         2
             224 CALL                 1
             232 RAISE_VARARGS        (exception instance)

131:     >>  234 LOAD_FAST            (response)
             236 LOAD_ATTR            (headers)
             256 LOAD_ATTR            (NULL|self + get)
             276 LOAD_CONST           ("X-Goog-Upload-Status")
             278 CALL                 1
             286 STORE_FAST           (status)

132:         288 LOAD_FAST            (status)
             290 LOAD_CONST           ("active")
             292 COMPARE_OP           (!=)
             296 POP_JUMP_IF_FALSE    (to 326)

133:         298 LOAD_GLOBAL          (NULL + Exception)
             308 LOAD_CONST           ("Trạng thái start không hợp lệ: ")
             310 LOAD_FAST            (status)
             312 FORMAT_VALUE         0
             314 BUILD_STRING         2
             316 CALL                 1
             324 RAISE_VARARGS        (exception instance)

135:     >>  326 LOAD_FAST            (response)
             328 LOAD_ATTR            (headers)
             348 LOAD_ATTR            (NULL|self + get)
             368 LOAD_CONST           ("X-Goog-Upload-URL")
             370 CALL                 1
             378 STORE_FAST           (upload_url)

136:         380 LOAD_FAST            (response)
             382 LOAD_ATTR            (headers)
             402 LOAD_ATTR            (NULL|self + get)

137:         422 LOAD_CONST           ("X-Goog-Upload-Header-Scotty-Resource-Id")

136:         424 CALL                 1
             432 STORE_FAST           (scotty_resource_id)

139:         434 LOAD_FAST            (upload_url)
             436 POP_JUMP_IF_FALSE    (to 442)
             438 LOAD_FAST            (scotty_resource_id)
             440 POP_JUMP_IF_TRUE     (to 464)

140:     >>  442 LOAD_GLOBAL          (NULL + Exception)
             452 LOAD_CONST           ("Thiếu upload URL hoặc scotty resource id trong response")
             454 CALL                 1
             462 RAISE_VARARGS        (exception instance)

142:     >>  464 NOP

143:         466 LOAD_GLOBAL          (NULL + int)

144:         476 LOAD_FAST            (response)
             478 LOAD_ATTR            (headers)
             498 LOAD_ATTR            (NULL|self + get)
             518 LOAD_CONST           ("X-Goog-Upload-Chunk-Granularity")
             520 LOAD_CONST           (262144)
             522 CALL                 2

143:         530 CALL                 1
             538 STORE_FAST           (granularity)

149:         540 LOAD_FAST            (upload_url)
             542 LOAD_FAST            (scotty_resource_id)
             544 LOAD_FAST            (granularity)
             546 BUILD_TUPLE          3
             548 RETURN_VALUE
             550 PUSH_EXC_INFO

146:         552 LOAD_GLOBAL          (TypeError)
             562 LOAD_GLOBAL          (ValueError)
             572 BUILD_TUPLE          2
             574 CHECK_EXC_MATCH
             576 POP_JUMP_IF_FALSE    (to 588)
             578 POP_TOP

147:         580 LOAD_CONST           (262144)
             582 STORE_FAST           (granularity)
             584 POP_EXCEPT
             586 JUMP_BACKWARD        (to 540)

146:     >>  588 RERAISE              0
             590 COPY                 3
             592 POP_EXCEPT
             594 RERAISE              1

ExceptionTable:
  466 to 538 -> 550 [0]
  550 to 582 -> 590 [1] lasti
  588 to 588 -> 590 [1] lasti

# Method Name:       _base_upload_headers
# Filename:          src\module\upload_video_module.py
# Argument count:    3
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  3
# Stack size:        9
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        151
# Constants:
#    0: None
#    1: 'upload.youtube.com'
#    2: 'application/x-www-form-urlencoded;charset=utf-8'
#    3: '*/*'
#    4: 'https://studio.youtube.com'
#    5: 'https://studio.youtube.com/'
#    6: ('Host', 'Cookie', 'X-Goog-Upload-File-Name', 'Content-Type', 'User-Agent', 'Accept', 'Origin', 'Referer')
# Names:
#    0: _USER_AGENT
# Varnames:
#	self, cookie_string, fname_header
# Positional arguments:
#	self, cookie_string, fname_header

151:           0 RESUME               0

153:           2 LOAD_CONST           ("upload.youtube.com")

154:           4 LOAD_FAST            (cookie_string)

155:           6 LOAD_FAST            (fname_header)

156:           8 LOAD_CONST           ("application/x-www-form-urlencoded;charset=utf-8")

157:          10 LOAD_GLOBAL          (_USER_AGENT)

158:          20 LOAD_CONST           ("*/*")

159:          22 LOAD_CONST           ("https://studio.youtube.com")

160:          24 LOAD_CONST           ("https://studio.youtube.com/")

152:          26 LOAD_CONST           (('Host', 'Cookie', 'X-Goog-Upload-File-Name', 'Content-Type', 'User-Agent', 'Accept', 'Origin', 'Referer'))
              28 BUILD_CONST_KEY_MAP  8
              30 RETURN_VALUE


# Method Name:       _query_offset
# Filename:          src\module\upload_video_module.py
# Argument count:    3
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  7
# Stack size:        6
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        163
# Constants:
#    0: 'Hỏi server đã nhận được bao nhiêu byte (để resume).'
#    1: 'query'
#    2: 'X-Goog-Upload-Command'
#    3: b''
#    4: 60
#    5: ('headers', 'data', 'timeout')
#    6: 'X-Goog-Upload-Size-Received'
#    7: None
#    8: 'Query upload offset lỗi: '
# Names:
#    0: dict
#    1: requests
#    2: post
#    3: headers
#    4: get
#    5: int
#    6: Exception
#    7: logger
#    8: warning
# Varnames:
#	self, upload_url, base_headers, headers, resp, recv, e
# Positional arguments:
#	self, upload_url, base_headers
# Local variables:
#    3: headers
#    4: resp
#    5: recv
#    6: e

163:           0 RESUME               0

165:           2 NOP

166:           4 LOAD_GLOBAL          (NULL + dict)
              14 LOAD_FAST            (base_headers)
              16 CALL                 1
              24 STORE_FAST           (headers)

167:          26 LOAD_CONST           ("query")
              28 LOAD_FAST            (headers)
              30 LOAD_CONST           ("X-Goog-Upload-Command")
              32 STORE_SUBSCR

168:          36 LOAD_GLOBAL          (NULL + requests)
              46 LOAD_ATTR            (post)
              66 LOAD_FAST            (upload_url)
              68 LOAD_FAST            (headers)
              70 LOAD_CONST           (b'')
              72 LOAD_CONST           (60)
              74 KW_NAMES             (('headers', 'data', 'timeout'))
              76 CALL                 4
              84 STORE_FAST           (resp)

169:          86 LOAD_FAST            (resp)
              88 LOAD_ATTR            (headers)
             108 LOAD_ATTR            (NULL|self + get)
             128 LOAD_CONST           ("X-Goog-Upload-Size-Received")
             130 CALL                 1
             138 STORE_FAST           (recv)

170:         140 LOAD_FAST            (recv)
             142 POP_JUMP_IF_NONE     (to 166)
             144 LOAD_GLOBAL          (NULL + int)
             154 LOAD_FAST            (recv)
             156 CALL                 1
             164 RETURN_VALUE
         >>  166 LOAD_CONST           (None)
             168 RETURN_VALUE
             170 PUSH_EXC_INFO

171:         172 LOAD_GLOBAL          (Exception)
             182 CHECK_EXC_MATCH
             184 POP_JUMP_IF_FALSE    (to 254)
             186 STORE_FAST           (e)

172:         188 LOAD_GLOBAL          (NULL + logger)
             198 LOAD_ATTR            (warning)
             218 LOAD_CONST           ("Query upload offset lỗi: ")
             220 LOAD_FAST            (e)
             222 FORMAT_VALUE         0
             224 BUILD_STRING         2
             226 CALL                 1
             234 POP_TOP

173:         236 POP_EXCEPT
             238 LOAD_CONST           (None)
             240 STORE_FAST           (e)
             242 DELETE_FAST          (e)
             244 RETURN_CONST         (None)
             246 LOAD_CONST           (None)
             248 STORE_FAST           (e)
             250 DELETE_FAST          (e)
             252 RERAISE              1

171:     >>  254 RERAISE              0
             256 COPY                 3
             258 POP_EXCEPT
             260 RERAISE              1

ExceptionTable:
  4 to 162 -> 170 [0]
  166 to 166 -> 170 [0]
  170 to 186 -> 256 [1] lasti
  188 to 234 -> 246 [1] lasti
  246 to 254 -> 256 [1] lasti

# Method Name:       _upload_bytes
# Filename:          src\module\upload_video_module.py
# Argument count:    7
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  20
# Stack size:        12
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        175
# Constants:
#    0: None
#    1: 'total'
#    2: 0
#    3: 'sent'
#    4: 1
#    5: 'rb'
#    6: 'upload, finalize'
#    7: 'upload'
#    8: 'X-Goog-Upload-Command'
#    9: 'X-Goog-Upload-Offset'
#   10: 600
#   11: ('headers', 'data', 'timeout')
#   12: 200
#   13: 'X-Goog-Upload-Status'
#   14: ('final', 'active')
#   15: 'Trạng thái finalize bất thường: '
#   16: 'HTTP '
#   17: 'Upload chunk lỗi tại offset '
#   18: ' (lần '
#   19: '/'
#   20: '): '
#   21: 'Upload thất bại tại offset '
#   22: ' sau nhiều lần thử'
#   23: 2
# Names:
#    0: os
#    1: path
#    2: getsize
#    3: max
#    4: _CHUNK_TARGET
#    5: _base_upload_headers
#    6: open
#    7: seek
#    8: read
#    9: len
#   10: dict
#   11: str
#   12: requests
#   13: post
#   14: status_code
#   15: headers
#   16: get
#   17: logger
#   18: warning
#   19: Exception
#   20: _MAX_CHUNK_RETRIES
#   21: _query_offset
#   22: time
#   23: sleep
# Varnames:
#	self, upload_url, cookie_string, fname_header, file_path, granularity, progress, file_size, chunk_size, base_headers, offset, retries, f, chunk, is_last, headers, resp, status, e, srv
# Positional arguments:
#	self, upload_url, cookie_string, fname_header, file_path, granularity, progress
# Local variables:
#    7: file_size
#    8: chunk_size
#    9: base_headers
#   10: offset
#   11: retries
#   12: f
#   13: chunk
#   14: is_last
#   15: headers
#   16: resp
#   17: status
#   18: e
#   19: srv

175:           0 RESUME               0

184:           2 LOAD_GLOBAL          (os)
              12 LOAD_ATTR            (path)
              32 LOAD_ATTR            (NULL|self + getsize)
              52 LOAD_FAST            (file_path)
              54 CALL                 1
              62 STORE_FAST           (file_size)

185:          64 LOAD_FAST            (progress)
              66 POP_JUMP_IF_NONE     (to 88)

186:          68 LOAD_FAST            (file_size)
              70 LOAD_FAST            (progress)
              72 LOAD_CONST           ("total")
              74 STORE_SUBSCR

187:          78 LOAD_CONST           (0)
              80 LOAD_FAST            (progress)
              82 LOAD_CONST           ("sent")
              84 STORE_SUBSCR

189:     >>   88 LOAD_GLOBAL          (NULL + max)
              98 LOAD_CONST           (1)
             100 LOAD_FAST            (granularity)
             102 CALL                 2
             110 STORE_FAST           (granularity)

190:         112 LOAD_GLOBAL          (NULL + max)
             122 LOAD_FAST            (granularity)
             124 LOAD_FAST            (self)
             126 LOAD_ATTR            (_CHUNK_TARGET)
             146 LOAD_FAST            (granularity)
             148 BINARY_OP            (//)
             152 LOAD_FAST            (granularity)
             154 BINARY_OP            (*)
             158 CALL                 2
             166 STORE_FAST           (chunk_size)

191:         168 LOAD_FAST            (self)
             170 LOAD_ATTR            (NULL|self + _base_upload_headers)
             190 LOAD_FAST            (cookie_string)
             192 LOAD_FAST            (fname_header)
             194 CALL                 2
             202 STORE_FAST           (base_headers)

193:         204 LOAD_CONST           (0)
             206 STORE_FAST           (offset)

194:         208 LOAD_CONST           (0)
             210 STORE_FAST           (retries)

195:         212 LOAD_GLOBAL          (NULL + open)
             222 LOAD_FAST            (file_path)
             224 LOAD_CONST           ("rb")
             226 CALL                 2
             234 BEFORE_WITH
             236 STORE_FAST           (f)

196:         238 LOAD_FAST            (offset)
             240 LOAD_FAST            (file_size)
             242 COMPARE_OP           (<)
             246 POP_JUMP_IF_FALSE    (to 714)

197:         248 LOAD_FAST            (f)
             250 LOAD_ATTR            (NULL|self + seek)
             270 LOAD_FAST            (offset)
             272 CALL                 1
             280 POP_TOP

198:         282 LOAD_FAST            (f)
             284 LOAD_ATTR            (NULL|self + read)
             304 LOAD_FAST            (chunk_size)
             306 CALL                 1
             314 STORE_FAST           (chunk)

199:         316 LOAD_FAST            (offset)
             318 LOAD_GLOBAL          (NULL + len)
             328 LOAD_FAST            (chunk)
             330 CALL                 1
             338 BINARY_OP            (+)
             342 LOAD_FAST            (file_size)
             344 COMPARE_OP           (>=)
             348 STORE_FAST           (is_last)

201:         350 LOAD_GLOBAL          (NULL + dict)
             360 LOAD_FAST            (base_headers)
             362 CALL                 1
             370 STORE_FAST           (headers)

203:         372 LOAD_FAST            (is_last)
             374 POP_JUMP_IF_FALSE    (to 380)
             376 LOAD_CONST           ("upload, finalize")
             378 JUMP_FORWARD         (to 382)
         >>  380 LOAD_CONST           ("upload")

202:     >>  382 LOAD_FAST            (headers)
             384 LOAD_CONST           ("X-Goog-Upload-Command")
             386 STORE_SUBSCR

205:         390 LOAD_GLOBAL          (NULL + str)
             400 LOAD_FAST            (offset)
             402 CALL                 1
             410 LOAD_FAST            (headers)
             412 LOAD_CONST           ("X-Goog-Upload-Offset")
             414 STORE_SUBSCR

207:         418 NOP

208:         420 LOAD_GLOBAL          (NULL + requests)
             430 LOAD_ATTR            (post)

209:         450 LOAD_FAST            (upload_url)
             452 LOAD_FAST            (headers)
             454 LOAD_FAST            (chunk)
             456 LOAD_CONST           (600)

208:         458 KW_NAMES             (('headers', 'data', 'timeout'))
             460 CALL                 4
             468 STORE_FAST           (resp)

211:         470 LOAD_FAST            (resp)
             472 LOAD_ATTR            (status_code)
             492 LOAD_CONST           (200)
             494 COMPARE_OP           (==)
             498 POP_JUMP_IF_FALSE    (to 666)

212:         500 LOAD_FAST            (offset)
             502 LOAD_GLOBAL          (NULL + len)
             512 LOAD_FAST            (chunk)
             514 CALL                 1
             522 BINARY_OP            (+=)
             526 STORE_FAST           (offset)

213:         528 LOAD_CONST           (0)
             530 STORE_FAST           (retries)

214:         532 LOAD_FAST            (progress)
             534 POP_JUMP_IF_NONE     (to 546)

215:         536 LOAD_FAST            (offset)
             538 LOAD_FAST            (progress)
             540 LOAD_CONST           ("sent")
             542 STORE_SUBSCR

216:     >>  546 LOAD_FAST            (is_last)
             548 POP_JUMP_IF_FALSE    (to 664)

217:         550 LOAD_FAST            (resp)
             552 LOAD_ATTR            (headers)
             572 LOAD_ATTR            (NULL|self + get)
             592 LOAD_CONST           ("X-Goog-Upload-Status")
             594 CALL                 1
             602 STORE_FAST           (status)

218:         604 LOAD_FAST            (status)
             606 POP_JUMP_IF_FALSE    (to 664)
             608 LOAD_FAST            (status)
             610 LOAD_CONST           (('final', 'active'))
             612 CONTAINS_OP          (not in)
             614 POP_JUMP_IF_FALSE    (to 664)

219:         616 LOAD_GLOBAL          (NULL + logger)
             626 LOAD_ATTR            (warning)
             646 LOAD_CONST           ("Trạng thái finalize bất thường: ")
             648 LOAD_FAST            (status)
             650 FORMAT_VALUE         0
             652 BUILD_STRING         2
             654 CALL                 1
             662 POP_TOP

220:     >>  664 JUMP_BACKWARD        (to 238)

221:     >>  666 LOAD_GLOBAL          (NULL + Exception)
             676 LOAD_CONST           ("HTTP ")
             678 LOAD_FAST            (resp)
             680 LOAD_ATTR            (status_code)
             700 FORMAT_VALUE         0
             702 BUILD_STRING         2
             704 CALL                 1
             712 RAISE_VARARGS        (exception instance)

195:     >>  714 LOAD_CONST           (None)
             716 LOAD_CONST           (None)
             718 LOAD_CONST           (None)
             720 CALL                 2
             728 POP_TOP
             730 RETURN_CONST         (None)
             732 PUSH_EXC_INFO

222:         734 LOAD_GLOBAL          (Exception)
             744 CHECK_EXC_MATCH
             746 POP_JUMP_IF_FALSE    (to 1052)
             748 STORE_FAST           (e)

223:         750 LOAD_FAST            (retries)
             752 LOAD_CONST           (1)
             754 BINARY_OP            (+=)
             758 STORE_FAST           (retries)

224:         760 LOAD_GLOBAL          (NULL + logger)
             770 LOAD_ATTR            (warning)

225:         790 LOAD_CONST           ("Upload chunk lỗi tại offset ")
             792 LOAD_FAST            (offset)
             794 FORMAT_VALUE         0
             796 LOAD_CONST           (" (lần ")

226:         798 LOAD_FAST            (retries)
             800 FORMAT_VALUE         0
             802 LOAD_CONST           ("/")
             804 LOAD_FAST            (self)
             806 LOAD_ATTR            (_MAX_CHUNK_RETRIES)
             826 FORMAT_VALUE         0
             828 LOAD_CONST           ("): ")
             830 LOAD_FAST            (e)
             832 FORMAT_VALUE         0

225:         834 BUILD_STRING         8

224:         836 CALL                 1
             844 POP_TOP

228:         846 LOAD_FAST            (retries)
             848 LOAD_FAST            (self)
             850 LOAD_ATTR            (_MAX_CHUNK_RETRIES)
             870 COMPARE_OP           (>)
             874 POP_JUMP_IF_FALSE    (to 906)

229:         876 LOAD_GLOBAL          (NULL + Exception)

230:         886 LOAD_CONST           ("Upload thất bại tại offset ")
             888 LOAD_FAST            (offset)
             890 FORMAT_VALUE         0
             892 LOAD_CONST           (" sau nhiều lần thử")
             894 BUILD_STRING         3

229:         896 CALL                 1
             904 RAISE_VARARGS        (exception instance)

233:     >>  906 LOAD_FAST            (self)
             908 LOAD_ATTR            (NULL|self + _query_offset)
             928 LOAD_FAST            (upload_url)
             930 LOAD_FAST            (base_headers)
             932 CALL                 2
             940 STORE_FAST           (srv)

234:         942 LOAD_FAST            (srv)
             944 POP_JUMP_IF_NONE     (to 992)
             946 LOAD_CONST           (0)
             948 LOAD_FAST            (srv)
             950 SWAP                 (TOS <-> TOS1)
             952 COPY                 2
             954 COMPARE_OP           (<=)
             958 POP_JUMP_IF_FALSE    (to 970)
             960 LOAD_FAST            (file_size)
             962 COMPARE_OP           (<=)
             966 POP_JUMP_IF_FALSE    (to 992)
             968 JUMP_FORWARD         (to 974)
         >>  970 POP_TOP
             972 JUMP_FORWARD         (to 992)

235:     >>  974 LOAD_FAST            (srv)
             976 STORE_FAST           (offset)

236:         978 LOAD_FAST            (progress)
             980 POP_JUMP_IF_NONE     (to 992)

237:         982 LOAD_FAST            (offset)
             984 LOAD_FAST            (progress)
             986 LOAD_CONST           ("sent")
             988 STORE_SUBSCR

238:     >>  992 LOAD_GLOBAL          (NULL + time)
            1002 LOAD_ATTR            (sleep)
            1022 LOAD_CONST           (2)
            1024 CALL                 1
            1032 POP_TOP
            1034 POP_EXCEPT
            1036 LOAD_CONST           (None)
            1038 STORE_FAST           (e)
            1040 DELETE_FAST          (e)
            1042 JUMP_FORWARD         (to 1060)
            1044 LOAD_CONST           (None)
            1046 STORE_FAST           (e)
            1048 DELETE_FAST          (e)
            1050 RERAISE              1

222:     >> 1052 RERAISE              0
            1054 COPY                 3
            1056 POP_EXCEPT
            1058 RERAISE              1

196:     >> 1060 LOAD_FAST            (offset)
            1062 LOAD_FAST            (file_size)
            1064 COMPARE_OP           (<)
            1068 POP_JUMP_IF_FALSE    (to 1074)
            1070 EXTENDED_ARG         (256)
            1072 JUMP_BACKWARD        (to 248)
         >> 1074 JUMP_BACKWARD        (to 714)

195:        1076 PUSH_EXC_INFO
            1078 WITH_EXCEPT_START
            1080 POP_JUMP_IF_TRUE     (to 1084)
            1082 RERAISE              2
         >> 1084 POP_TOP
            1086 POP_EXCEPT
            1088 POP_TOP
            1090 POP_TOP
            1092 RETURN_CONST         (None)
         >> 1094 COPY                 3
            1096 POP_EXCEPT
            1098 RERAISE              1

ExceptionTable:
  236 to 416 -> 1076 [1] lasti
  420 to 662 -> 732 [1]
  664 to 664 -> 1076 [1] lasti
  666 to 712 -> 732 [1]
  732 to 748 -> 1054 [2] lasti
  750 to 1032 -> 1044 [2] lasti
  1034 to 1042 -> 1076 [1] lasti
  1044 to 1052 -> 1054 [2] lasti
  1054 to 1068 -> 1076 [1] lasti
  1076 to 1084 -> 1094 [3] lasti

# Method Name:       create_video
# Filename:          src\module\upload_video_module.py
# Argument count:    9
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  19
# Stack size:        12
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        240
# Constants:
#    0: 'Chặng 3: tạo video từ scottyResourceId, set title/description/tags.\n\n        Trả về videoId. Metadata được set ngay khi tạo (không cần call update).\n        '
#    1: 'Không tìm thấy kênh: '
#    2: '1.20260708.06.00'
#    3: 'vi'
#    4: ('challenge', 'webResponse')
#    5: 'token'
#    6: ('attestationResponseData', 'sessionInfo')
#    7: ('client_version', 'hl', 'extra_request_fields')
#    8: 'scottyResourceId'
#    9: 'id'
#   10: 'newTitle'
#   11: 'newPrivacy'
#   12: 'isDraft'
#   13: 'newDescription'
#   14: ''
#   15: 'newTags'
#   16: ('title', 'privacy', 'draftState', 'description', 'tags')
#   17: 'enableRequiresContentLevelProtection'
#   18: False
#   19: ('channelId', 'resourceId', 'frontendUploadId', 'initialMetadata', 'contentLevelProtection', 'context', 'presumedShort')
#   20: 'studio.youtube.com'
#   21: 'SAPISIDHASH '
#   22: 'application/json'
#   23: 'https://studio.youtube.com'
#   24: 'https://studio.youtube.com/'
#   25: '0'
#   26: '62'
#   27: ('Host', 'Cookie', 'Authorization', 'Content-Type', 'Origin', 'X-Origin', 'Referer', 'User-Agent', 'X-Goog-AuthUser', 'X-Youtube-Client-Name', 'X-Youtube-Client-Version')
#   28: 'https://studio.youtube.com/youtubei/v1/upload/createvideo?alt=json'
#   29: ('headers', 'json')
#   30: 200
#   31: 'createvideo thất bại: HTTP '
#   32: ': '
#   33: None
#   34: 300
#   35: 'videoId'
#   36: 'createvideo không trả videoId: '
#   37: 'Created video '
#   38: " (title='"
#   39: "')"
# Names:
#    0: get_channels_info
#    1: Exception
#    2: _get_session_token
#    3: cookie_string
#    4: _build_context
#    5: id
#    6: role
#    7: delegated_session_id
#    8: challenge
#    9: botguardResponse
#   10: _sanitize_title
#   11: sapisidhash
#   12: _USER_AGENT
#   13: requests
#   14: post
#   15: status_code
#   16: text
#   17: json
#   18: get
#   19: str
#   20: logger
#   21: info
# Varnames:
#	self, channel_id, scotty_resource_id, frontend_upload_id, title, description, tags, privacy, is_draft, channel_info, session_token, cookie_string, context, payload, headers, url, response, data, video_id
# Positional arguments:
#	self, channel_id, scotty_resource_id, frontend_upload_id, title, description, tags, privacy, is_draft
# Local variables:
#    9: channel_info
#   10: session_token
#   11: cookie_string
#   12: context
#   13: payload
#   14: headers
#   15: url
#   16: response
#   17: data
#   18: video_id

240:           0 RESUME               0

255:           2 LOAD_GLOBAL          (NULL + get_channels_info)
              12 LOAD_FAST            (channel_id)
              14 CALL                 1
              22 STORE_FAST           (channel_info)

256:          24 LOAD_FAST            (channel_info)
              26 POP_JUMP_IF_TRUE     (to 56)

257:          28 LOAD_GLOBAL          (NULL + Exception)
              38 LOAD_CONST           ("Không tìm thấy kênh: ")
              40 LOAD_FAST            (channel_id)
              42 FORMAT_VALUE         0
              44 BUILD_STRING         2
              46 CALL                 1
              54 RAISE_VARARGS        (exception instance)

259:     >>   56 LOAD_FAST            (self)
              58 LOAD_ATTR            (NULL|self + _get_session_token)
              78 LOAD_FAST            (channel_info)
              80 CALL                 1
              88 STORE_FAST           (session_token)

262:          90 LOAD_GLOBAL          (NULL + get_channels_info)
             100 LOAD_FAST            (channel_id)
             102 CALL                 1
             110 STORE_FAST           (channel_info)

263:         112 LOAD_FAST            (channel_info)
             114 LOAD_ATTR            (NULL|self + cookie_string)
             134 CALL                 0
             142 STORE_FAST           (cookie_string)

265:         144 LOAD_FAST            (self)
             146 LOAD_ATTR            (NULL|self + _build_context)

266:         166 LOAD_FAST            (channel_info)
             168 LOAD_ATTR            (id)

267:         188 LOAD_FAST            (channel_info)
             190 LOAD_ATTR            (role)

268:         210 LOAD_FAST            (channel_info)
             212 LOAD_ATTR            (delegated_session_id)

269:         232 LOAD_CONST           ("1.20260708.06.00")

270:         234 LOAD_CONST           ("vi")

273:         236 LOAD_FAST            (channel_info)
             238 LOAD_ATTR            (challenge)

274:         258 LOAD_FAST            (channel_info)
             260 LOAD_ATTR            (botguardResponse)

272:         280 LOAD_CONST           (('challenge', 'webResponse'))
             282 BUILD_CONST_KEY_MAP  2

276:         284 LOAD_CONST           ("token")
             286 LOAD_FAST            (session_token)
             288 BUILD_MAP            1

271:         290 LOAD_CONST           (('attestationResponseData', 'sessionInfo'))
             292 BUILD_CONST_KEY_MAP  2

265:         294 KW_NAMES             (('client_version', 'hl', 'extra_request_fields'))
             296 CALL                 6
             304 STORE_FAST           (context)

281:         306 LOAD_FAST            (channel_info)
             308 LOAD_ATTR            (id)

282:         328 LOAD_CONST           ("scottyResourceId")
             330 LOAD_CONST           ("id")
             332 LOAD_FAST            (scotty_resource_id)
             334 BUILD_MAP            1
             336 BUILD_MAP            1

283:         338 LOAD_FAST            (frontend_upload_id)

285:         340 LOAD_CONST           ("newTitle")
             342 LOAD_GLOBAL          (NULL + _sanitize_title)
             352 LOAD_FAST            (title)
             354 CALL                 1
             362 BUILD_MAP            1

286:         364 LOAD_CONST           ("newPrivacy")
             366 LOAD_FAST            (privacy)
             368 BUILD_MAP            1

287:         370 LOAD_CONST           ("isDraft")
             372 LOAD_FAST            (is_draft)
             374 BUILD_MAP            1

288:         376 LOAD_CONST           ("newDescription")
             378 LOAD_FAST            (description)
             380 COPY                 1
             382 POP_JUMP_IF_TRUE     (to 388)
             384 POP_TOP
             386 LOAD_CONST           ("")
         >>  388 BUILD_MAP            1

289:         390 LOAD_CONST           ("newTags")
             392 LOAD_FAST            (tags)
             394 COPY                 1
             396 POP_JUMP_IF_TRUE     (to 402)
             398 POP_TOP
             400 BUILD_LIST           0
         >>  402 BUILD_MAP            1

284:         404 LOAD_CONST           (('title', 'privacy', 'draftState', 'description', 'tags'))
             406 BUILD_CONST_KEY_MAP  5

292:         408 LOAD_CONST           ("enableRequiresContentLevelProtection")
             410 LOAD_CONST           (False)

291:         412 BUILD_MAP            1

294:         414 LOAD_FAST            (context)

295:         416 LOAD_CONST           (False)

280:         418 LOAD_CONST           (('channelId', 'resourceId', 'frontendUploadId', 'initialMetadata', 'contentLevelProtection', 'context', 'presumedShort'))
             420 BUILD_CONST_KEY_MAP  7
             422 STORE_FAST           (payload)

299:         424 LOAD_CONST           ("studio.youtube.com")

300:         426 LOAD_FAST            (cookie_string)

301:         428 LOAD_CONST           ("SAPISIDHASH ")
             430 LOAD_FAST            (channel_info)
             432 LOAD_ATTR            (sapisidhash)
             452 FORMAT_VALUE         0
             454 BUILD_STRING         2

302:         456 LOAD_CONST           ("application/json")

303:         458 LOAD_CONST           ("https://studio.youtube.com")

304:         460 LOAD_CONST           ("https://studio.youtube.com")

305:         462 LOAD_CONST           ("https://studio.youtube.com/")

306:         464 LOAD_GLOBAL          (_USER_AGENT)

307:         474 LOAD_CONST           ("0")

308:         476 LOAD_CONST           ("62")

309:         478 LOAD_CONST           ("1.20260708.06.00")

298:         480 LOAD_CONST           (('Host', 'Cookie', 'Authorization', 'Content-Type', 'Origin', 'X-Origin', 'Referer', 'User-Agent', 'X-Goog-AuthUser', 'X-Youtube-Client-Name', 'X-Youtube-Client-Version'))
             482 BUILD_CONST_KEY_MAP  11
             484 STORE_FAST           (headers)

311:         486 LOAD_CONST           ("https://studio.youtube.com/youtubei/v1/upload/createvideo?alt=json")
             488 STORE_FAST           (url)

312:         490 LOAD_GLOBAL          (NULL + requests)
             500 LOAD_ATTR            (post)
             520 LOAD_FAST            (url)
             522 LOAD_FAST            (headers)
             524 LOAD_FAST            (payload)
             526 KW_NAMES             (('headers', 'json'))
             528 CALL                 3
             536 STORE_FAST           (response)

314:         538 LOAD_FAST            (response)
             540 LOAD_ATTR            (status_code)
             560 LOAD_CONST           (200)
             562 COMPARE_OP           (!=)
             566 POP_JUMP_IF_FALSE    (to 648)

315:         568 LOAD_GLOBAL          (NULL + Exception)

316:         578 LOAD_CONST           ("createvideo thất bại: HTTP ")
             580 LOAD_FAST            (response)
             582 LOAD_ATTR            (status_code)
             602 FORMAT_VALUE         0
             604 LOAD_CONST           (": ")

317:         606 LOAD_FAST            (response)
             608 LOAD_ATTR            (text)
             628 LOAD_CONST           (None)
             630 LOAD_CONST           (300)
             632 BINARY_SLICE
             634 FORMAT_VALUE         0

316:         636 BUILD_STRING         4

315:         638 CALL                 1
             646 RAISE_VARARGS        (exception instance)

320:     >>  648 LOAD_FAST            (response)
             650 LOAD_ATTR            (NULL|self + json)
             670 CALL                 0
             678 STORE_FAST           (data)

321:         680 LOAD_FAST            (data)
             682 LOAD_ATTR            (NULL|self + get)
             702 LOAD_CONST           ("videoId")
             704 CALL                 1
             712 STORE_FAST           (video_id)

322:         714 LOAD_FAST            (video_id)
             716 POP_JUMP_IF_TRUE     (to 770)

323:         718 LOAD_GLOBAL          (NULL + Exception)
             728 LOAD_CONST           ("createvideo không trả videoId: ")
             730 LOAD_GLOBAL          (NULL + str)
             740 LOAD_FAST            (data)
             742 CALL                 1
             750 LOAD_CONST           (None)
             752 LOAD_CONST           (300)
             754 BINARY_SLICE
             756 FORMAT_VALUE         0
             758 BUILD_STRING         2
             760 CALL                 1
             768 RAISE_VARARGS        (exception instance)

325:     >>  770 LOAD_GLOBAL          (NULL + logger)
             780 LOAD_ATTR            (info)
             800 LOAD_CONST           ("Created video ")
             802 LOAD_FAST            (video_id)
             804 FORMAT_VALUE         0
             806 LOAD_CONST           (" (title='")
             808 LOAD_GLOBAL          (NULL + _sanitize_title)
             818 LOAD_FAST            (title)
             820 CALL                 1
             828 FORMAT_VALUE         0
             830 LOAD_CONST           ("')")
             832 BUILD_STRING         5
             834 CALL                 1
             842 POP_TOP

326:         844 LOAD_FAST            (video_id)
             846 RETURN_VALUE


# Method Name:       is_processed
# Filename:          src\module\upload_video_module.py
# Argument count:    3
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  5
# Stack size:        7
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        328
# Constants:
#    0: 'Kiểm tra video đã được YouTube xử lý xong chưa.\n\n        Trả True khi video.status == "VIDEO_STATUS_PROCESSED".\n        '
#    1: ('video_id', 'channel_id')
#    2: 'Không lấy được trạng thái video '
#    3: ': '
#    4: None
#    5: False
#    6: 'VIDEO_STATUS_PROCESSED'
# Names:
#    0: _get_video_info
#    1: Exception
#    2: logger
#    3: warning
#    4: bool
#    5: video_status
# Varnames:
#	self, channel_id, video_id, info, e
# Positional arguments:
#	self, channel_id, video_id
# Local variables:
#    3: info
#    4: e

328:           0 RESUME               0

333:           2 NOP

334:           4 LOAD_FAST            (self)
               6 LOAD_ATTR            (NULL|self + _get_video_info)
              26 LOAD_FAST            (video_id)
              28 LOAD_FAST            (channel_id)
              30 KW_NAMES             (('video_id', 'channel_id'))
              32 CALL                 2
              40 STORE_FAST           (info)

338:          42 LOAD_GLOBAL          (NULL + bool)
              52 LOAD_FAST            (info)
              54 COPY                 1
              56 POP_JUMP_IF_FALSE    (to 88)
              58 POP_TOP
              60 LOAD_FAST            (info)
              62 LOAD_ATTR            (video_status)
              82 LOAD_CONST           ("VIDEO_STATUS_PROCESSED")
              84 COMPARE_OP           (==)
         >>   88 CALL                 1
              96 RETURN_VALUE
              98 PUSH_EXC_INFO

335:         100 LOAD_GLOBAL          (Exception)
             110 CHECK_EXC_MATCH
             112 POP_JUMP_IF_FALSE    (to 188)
             114 STORE_FAST           (e)

336:         116 LOAD_GLOBAL          (NULL + logger)
             126 LOAD_ATTR            (warning)
             146 LOAD_CONST           ("Không lấy được trạng thái video ")
             148 LOAD_FAST            (video_id)
             150 FORMAT_VALUE         0
             152 LOAD_CONST           (": ")
             154 LOAD_FAST            (e)
             156 FORMAT_VALUE         0
             158 BUILD_STRING         4
             160 CALL                 1
             168 POP_TOP

337:         170 POP_EXCEPT
             172 LOAD_CONST           (None)
             174 STORE_FAST           (e)
             176 DELETE_FAST          (e)
             178 RETURN_CONST         (False)
             180 LOAD_CONST           (None)
             182 STORE_FAST           (e)
             184 DELETE_FAST          (e)
             186 RERAISE              1

335:     >>  188 RERAISE              0
             190 COPY                 3
             192 POP_EXCEPT
             194 RERAISE              1

ExceptionTable:
  4 to 40 -> 98 [0]
  98 to 114 -> 190 [1] lasti
  116 to 168 -> 180 [1] lasti
  180 to 188 -> 190 [1] lasti
```
