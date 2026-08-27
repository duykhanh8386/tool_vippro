# Static CPython 3.12 disassembly — `updater.pyc`

Generated with `xdis 6.3.0`; the code object was deserialized but never executed.

```text
# pydisasm version 6.3.0
# CPython Python bytecode 3.12.0 (3531)
#   Disassembled from CPython Python 3.13.13 | packaged by Anaconda, Inc. | (main, Apr 14 2026, 06:12:50) [MSC v.1942 64 bit (AMD64)]
# Timestamp in code: 0 (1970-01-01 07:00:00)
# Source code size mod 2**32: 0 bytes
# Method Name:       <module>
# Filename:          src\updater.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        6
# Flags:             0x01000000 (0x1000000)
# First Line:        1
# Constants:
#    0: "GitHub Release auto-updater for TV Automation (NiceGUI / asyncio).\n\nAdapted from the Qt/PySide6 updater pattern to NiceGUI's single asyncio event\nloop. Instead of QThreads + signals, the blocking network work runs in worker\nthreads via ``asyncio.to_thread`` and the UI polls this singleton's in-memory\nstate with a ``ui.timer`` (same approach as ``delete_video_controller``).\n\n────────────────────────────────────────────────────────────────────────────\nCONFIG — set these before building a release:\n  * REPO_OWNER / REPO_NAME → the GitHub repo that publishes the Release assets.\n  * FALLBACK_DOWNLOAD_URL  → optional direct installer URL used when a release\n                             has no platform-matching asset.\nThe current version is read from the bundled ``VERSION`` file.\n────────────────────────────────────────────────────────────────────────────\n"
#    1: 0
#    2: ('annotations',)
#    3: None
#    4: ('Path',)
#    5: ('Callable', 'Optional')
#    6: ('HTTPError', 'URLError')
#    7: ('Request', 'urlopen')
#    8: ('logger',)
#    9: 'bmtuan'
#   10: 'TV-Automation-Release'
#   11: 'TVAutomation_Setup.exe'
#   12: 'https://github.com/'
#   13: '/'
#   14: '/releases/latest/download/'
#   15: 'str | None'
#   16: 'FALLBACK_DOWNLOAD_URL'
#   17: 'TV-Automation-Updater'
#   18: <Code311 code object get_current_version at 0x2e1d0133ce0, file src\updater.py>, line 51
#   19: <Code311 code object _get_ssl_context at 0x2e1d0133df0, file src\updater.py>, line 71
#   20: <Code311 code object _version_key at 0x2e1d0133f00, file src\updater.py>, line 83
#   21: <Code311 code object _version_newer at 0x2e1d01e0050, file src\updater.py>, line 97
#   22: <Code311 code object _find_platform_asset at 0x2e1d01e0270, file src\updater.py>, line 101
#   23: <Code311 code object _check_latest_release at 0x2e1d01e0380, file src\updater.py>, line 120
#   24: <Code311 code object _download_installer at 0x2e1d01e0490, file src\updater.py>, line 180
#   25: <Code311 code object UpdaterService at 0x2e1d01e1bf0, file src\updater.py>, line 213
#   26: 'UpdaterService'
#   27: ('current_version', 'fallback_download_url')
#   28: ('return', 'str')
#   29: ('return', 'ssl.SSLContext')
#   30: ('v', 'str', 'return', 'tuple[int, ...]')
#   31: ('latest', 'str', 'current', 'str', 'return', 'bool')
#   32: ('assets', 'list[dict]', 'return', 'dict | None')
#   33: ('owner', 'str', 'repo', 'str', 'current_version', 'str', 'fallback_url', 'str | None', 'return', 'dict | None')
#   34: ('url', 'str', 'filename', 'str', 'progress_cb', 'Callable[[int], None]', 'should_stop', 'Callable[[], bool]', 'return', 'str')
# Names:
#    0: __doc__
#    1: __future__
#    2: annotations
#    3: asyncio
#    4: json
#    5: os
#    6: platform
#    7: re
#    8: ssl
#    9: subprocess
#   10: sys
#   11: tempfile
#   12: pathlib
#   13: Path
#   14: typing
#   15: Callable
#   16: Optional
#   17: urllib.error
#   18: HTTPError
#   19: URLError
#   20: urllib.request
#   21: Request
#   22: urlopen
#   23: loguru
#   24: logger
#   25: REPO_OWNER
#   26: REPO_NAME
#   27: DEFAULT_INSTALLER_NAME
#   28: FALLBACK_DOWNLOAD_URL
#   29: __annotations__
#   30: _USER_AGENT
#   31: get_current_version
#   32: _get_ssl_context
#   33: _version_key
#   34: _version_newer
#   35: _find_platform_asset
#   36: _check_latest_release
#   37: _download_installer
#   38: UpdaterService
#   39: create
#   40: updater_service

  0:           0 RESUME               0

  1:           2 SETUP_ANNOTATIONS
               4 LOAD_CONST           ("GitHub Release auto-updater for TV Automation (NiceGUI / asyncio).\n\nAdapted from the Qt/PySide6 updater pattern to NiceGUI's single asyncio event\nloop. Instead of QThreads + signals, the blocking network work runs in worker\nthreads via ``asyncio.to_thread`` and the UI polls this singleton's in-memory\nstate with a ``ui.timer`` (same approach as ``delete_video_controller``).\n\n────────────────────────────────────────────────────────────────────────────\nCONFIG — set these before building a release:\n  * REPO_OWNER / REPO_NAME → the GitHub repo that publishes the Release assets.\n  * FALLBACK_DOWNLOAD_URL  → optional direct installer URL used when a release\n                             has no platform-matching asset.\nThe current version is read from the bundled ``VERSION`` file.\n────────────────────────────────────────────────────────────────────────────\n")
               6 STORE_NAME           (__doc__)

 17:           8 LOAD_CONST           (0)
              10 LOAD_CONST           (('annotations',))
              12 IMPORT_NAME          (__future__)
              14 IMPORT_FROM          (annotations)
              16 STORE_NAME           (annotations)
              18 POP_TOP

 19:          20 LOAD_CONST           (0)
              22 LOAD_CONST           (None)
              24 IMPORT_NAME          (asyncio)
              26 STORE_NAME           (asyncio)

 20:          28 LOAD_CONST           (0)
              30 LOAD_CONST           (None)
              32 IMPORT_NAME          (json)
              34 STORE_NAME           (json)

 21:          36 LOAD_CONST           (0)
              38 LOAD_CONST           (None)
              40 IMPORT_NAME          (os)
              42 STORE_NAME           (os)

 22:          44 LOAD_CONST           (0)
              46 LOAD_CONST           (None)
              48 IMPORT_NAME          (platform)
              50 STORE_NAME           (platform)

 23:          52 LOAD_CONST           (0)
              54 LOAD_CONST           (None)
              56 IMPORT_NAME          (re)
              58 STORE_NAME           (re)

 24:          60 LOAD_CONST           (0)
              62 LOAD_CONST           (None)
              64 IMPORT_NAME          (ssl)
              66 STORE_NAME           (ssl)

 25:          68 LOAD_CONST           (0)
              70 LOAD_CONST           (None)
              72 IMPORT_NAME          (subprocess)
              74 STORE_NAME           (subprocess)

 26:          76 LOAD_CONST           (0)
              78 LOAD_CONST           (None)
              80 IMPORT_NAME          (sys)
              82 STORE_NAME           (sys)

 27:          84 LOAD_CONST           (0)
              86 LOAD_CONST           (None)
              88 IMPORT_NAME          (tempfile)
              90 STORE_NAME           (tempfile)

 28:          92 LOAD_CONST           (0)
              94 LOAD_CONST           (('Path',))
              96 IMPORT_NAME          (pathlib)
              98 IMPORT_FROM          (Path)
             100 STORE_NAME           (Path)
             102 POP_TOP

 29:         104 LOAD_CONST           (0)
             106 LOAD_CONST           (('Callable', 'Optional'))
             108 IMPORT_NAME          (typing)
             110 IMPORT_FROM          (Callable)
             112 STORE_NAME           (Callable)
             114 IMPORT_FROM          (Optional)
             116 STORE_NAME           (Optional)
             118 POP_TOP

 30:         120 LOAD_CONST           (0)
             122 LOAD_CONST           (('HTTPError', 'URLError'))
             124 IMPORT_NAME          (urllib.error)
             126 IMPORT_FROM          (HTTPError)
             128 STORE_NAME           (HTTPError)
             130 IMPORT_FROM          (URLError)
             132 STORE_NAME           (URLError)
             134 POP_TOP

 31:         136 LOAD_CONST           (0)
             138 LOAD_CONST           (('Request', 'urlopen'))
             140 IMPORT_NAME          (urllib.request)
             142 IMPORT_FROM          (Request)
             144 STORE_NAME           (Request)
             146 IMPORT_FROM          (urlopen)
             148 STORE_NAME           (urlopen)
             150 POP_TOP

 33:         152 LOAD_CONST           (0)
             154 LOAD_CONST           (('logger',))
             156 IMPORT_NAME          (loguru)
             158 IMPORT_FROM          (logger)
             160 STORE_NAME           (logger)
             162 POP_TOP

 36:         164 LOAD_CONST           ("bmtuan")
             166 STORE_NAME           (REPO_OWNER)

 37:         168 LOAD_CONST           ("TV-Automation-Release")
             170 STORE_NAME           (REPO_NAME)

 38:         172 LOAD_CONST           ("TVAutomation_Setup.exe")
             174 STORE_NAME           (DEFAULT_INSTALLER_NAME)

 41:         176 LOAD_CONST           ("https://github.com/")
             178 LOAD_NAME            (REPO_OWNER)
             180 FORMAT_VALUE         0
             182 LOAD_CONST           ("/")
             184 LOAD_NAME            (REPO_NAME)
             186 FORMAT_VALUE         0
             188 LOAD_CONST           ("/releases/latest/download/")

 42:         190 LOAD_NAME            (DEFAULT_INSTALLER_NAME)
             192 FORMAT_VALUE         0

 41:         194 BUILD_STRING         6

 40:         196 STORE_NAME           (FALLBACK_DOWNLOAD_URL)
             198 LOAD_CONST           ("str | None")
             200 LOAD_NAME            (__annotations__)
             202 LOAD_CONST           ("FALLBACK_DOWNLOAD_URL")
             204 STORE_SUBSCR

 45:         208 LOAD_CONST           ("TV-Automation-Updater")
             210 STORE_NAME           (_USER_AGENT)

 51:         212 LOAD_CONST           (('return', 'str'))
             214 LOAD_CONST           (<Code311 code object get_current_version at 0x2e1d0133ce0, file src\updater.py>, line 51)
             216 MAKE_FUNCTION        (annotation)
             218 STORE_NAME           (get_current_version)

 71:         220 LOAD_CONST           (('return', 'ssl.SSLContext'))
             222 LOAD_CONST           (<Code311 code object _get_ssl_context at 0x2e1d0133df0, file src\updater.py>, line 71)
             224 MAKE_FUNCTION        (annotation)
             226 STORE_NAME           (_get_ssl_context)

 83:         228 LOAD_CONST           (('v', 'str', 'return', 'tuple[int, ...]'))
             230 LOAD_CONST           (<Code311 code object _version_key at 0x2e1d0133f00, file src\updater.py>, line 83)
             232 MAKE_FUNCTION        (annotation)
             234 STORE_NAME           (_version_key)

 97:         236 LOAD_CONST           (('latest', 'str', 'current', 'str', 'return', 'bool'))
             238 LOAD_CONST           (<Code311 code object _version_newer at 0x2e1d01e0050, file src\updater.py>, line 97)
             240 MAKE_FUNCTION        (annotation)
             242 STORE_NAME           (_version_newer)

101:         244 LOAD_CONST           (('assets', 'list[dict]', 'return', 'dict | None'))
             246 LOAD_CONST           (<Code311 code object _find_platform_asset at 0x2e1d01e0270, file src\updater.py>, line 101)
             248 MAKE_FUNCTION        (annotation)
             250 STORE_NAME           (_find_platform_asset)

120:         252 NOP

121:         254 NOP

120:         256 NOP

122:         258 NOP

120:         260 NOP

123:         262 NOP

120:         264 NOP

124:         266 NOP

120:         268 NOP

125:         270 NOP

120:         272 LOAD_CONST           (('owner', 'str', 'repo', 'str', 'current_version', 'str', 'fallback_url', 'str | None', 'return', 'dict | None'))
             274 LOAD_CONST           (<Code311 code object _check_latest_release at 0x2e1d01e0380, file src\updater.py>, line 120)
             276 MAKE_FUNCTION        (annotation)
             278 STORE_NAME           (_check_latest_release)

180:         280 NOP

181:         282 NOP

180:         284 NOP

182:         286 NOP

180:         288 NOP

183:         290 NOP

180:         292 NOP

184:         294 NOP

180:         296 NOP

185:         298 NOP

180:         300 LOAD_CONST           (('url', 'str', 'filename', 'str', 'progress_cb', 'Callable[[int], None]', 'should_stop', 'Callable[[], bool]', 'return', 'str'))
             302 LOAD_CONST           (<Code311 code object _download_installer at 0x2e1d01e0490, file src\updater.py>, line 180)
             304 MAKE_FUNCTION        (annotation)
             306 STORE_NAME           (_download_installer)

213:         308 PUSH_NULL
             310 LOAD_BUILD_CLASS
             312 LOAD_CONST           (<Code311 code object UpdaterService at 0x2e1d01e1bf0, file src\updater.py>, line 213)
             314 MAKE_FUNCTION        (No arguments)
             316 LOAD_CONST           ("UpdaterService")
             318 CALL                 2
             326 STORE_NAME           (UpdaterService)

435:         328 LOAD_NAME            (UpdaterService)
             330 LOAD_ATTR            (NULL|self + create)

436:         350 LOAD_NAME            (REPO_OWNER)

437:         352 LOAD_NAME            (REPO_NAME)

438:         354 PUSH_NULL
             356 LOAD_NAME            (get_current_version)
             358 CALL                 0

439:         366 LOAD_NAME            (FALLBACK_DOWNLOAD_URL)

435:         368 KW_NAMES             (('current_version', 'fallback_download_url'))
             370 CALL                 4
             378 STORE_NAME           (updater_service)
             380 RETURN_CONST         (None)


# Method Name:       get_current_version
# Filename:          src\updater.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  4
# Stack size:        9
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        51
# Constants:
#    0: 'Read the bundled VERSION file (works both frozen and from source).'
#    1: 'frozen'
#    2: False
#    3: '_MEIPASS'
#    4: 'VERSION'
#    5: 'utf-8'
#    6: ('encoding',)
#    7: 'Failed to read VERSION file: '
#    8: None
#    9: 'v0.0.0'
# Names:
#    0: getattr
#    1: sys
#    2: Path
#    3: executable
#    4: parent
#    5: __file__
#    6: resolve
#    7: exists
#    8: read_text
#    9: strip
#   10: Exception
#   11: logger
#   12: error
# Varnames:
#	base, version_file, text, exc
# Local variables:
#    0: base
#    1: version_file
#    2: text
#    3: exc

 51:           0 RESUME               0

 53:           2 NOP

 54:           4 LOAD_GLOBAL          (NULL + getattr)
              14 LOAD_GLOBAL          (sys)
              24 LOAD_CONST           ("frozen")
              26 LOAD_CONST           (False)
              28 CALL                 3
              36 POP_JUMP_IF_FALSE    (to 158)

 55:          38 LOAD_GLOBAL          (NULL + Path)
              48 LOAD_GLOBAL          (NULL + getattr)
              58 LOAD_GLOBAL          (sys)
              68 LOAD_CONST           ("_MEIPASS")
              70 LOAD_GLOBAL          (NULL + Path)
              80 LOAD_GLOBAL          (sys)
              90 LOAD_ATTR            (executable)
             110 CALL                 1
             118 LOAD_ATTR            (parent)
             138 CALL                 3
             146 CALL                 1
             154 STORE_FAST           (base)
             156 JUMP_FORWARD         (to 256)

 57:     >>  158 LOAD_GLOBAL          (NULL + Path)
             168 LOAD_GLOBAL          (__file__)
             178 CALL                 1
             186 LOAD_ATTR            (NULL|self + resolve)
             206 CALL                 0
             214 LOAD_ATTR            (parent)
             234 LOAD_ATTR            (parent)
             254 STORE_FAST           (base)

 58:     >>  256 LOAD_FAST            (base)
             258 LOAD_CONST           ("VERSION")
             260 BINARY_OP            (/)
             264 STORE_FAST           (version_file)

 59:         266 LOAD_FAST            (version_file)
             268 LOAD_ATTR            (NULL|self + exists)
             288 CALL                 0
             296 POP_JUMP_IF_FALSE    (to 370)

 60:         298 LOAD_FAST            (version_file)
             300 LOAD_ATTR            (NULL|self + read_text)
             320 LOAD_CONST           ("utf-8")
             322 KW_NAMES             (('encoding',))
             324 CALL                 1
             332 LOAD_ATTR            (NULL|self + strip)
             352 CALL                 0
             360 STORE_FAST           (text)

 61:         362 LOAD_FAST            (text)
             364 POP_JUMP_IF_FALSE    (to 370)

 62:         366 LOAD_FAST            (text)
             368 RETURN_VALUE

 65:     >>  370 RETURN_CONST         ("v0.0.0")
             372 PUSH_EXC_INFO

 63:         374 LOAD_GLOBAL          (Exception)
             384 CHECK_EXC_MATCH
             386 POP_JUMP_IF_FALSE    (to 456)
             388 STORE_FAST           (exc)

 64:         390 LOAD_GLOBAL          (NULL + logger)
             400 LOAD_ATTR            (error)
             420 LOAD_CONST           ("Failed to read VERSION file: ")
             422 LOAD_FAST            (exc)
             424 FORMAT_VALUE         0
             426 BUILD_STRING         2
             428 CALL                 1
             436 POP_TOP
             438 POP_EXCEPT
             440 LOAD_CONST           (None)
             442 STORE_FAST           (exc)
             444 DELETE_FAST          (exc)

 65:         446 RETURN_CONST         ("v0.0.0")
             448 LOAD_CONST           (None)
             450 STORE_FAST           (exc)
             452 DELETE_FAST          (exc)
             454 RERAISE              1

 63:     >>  456 RERAISE              0
             458 COPY                 3
             460 POP_EXCEPT
             462 RERAISE              1

ExceptionTable:
  4 to 366 -> 372 [0]
  372 to 388 -> 458 [1] lasti
  390 to 436 -> 448 [1] lasti
  448 to 456 -> 458 [1] lasti

# Method Name:       _get_ssl_context
# Filename:          src\updater.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  1
# Stack size:        4
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        71
# Constants:
#    0: None
#    1: 0
#    2: ('cafile',)
# Names:
#    0: certifi
#    1: ssl
#    2: create_default_context
#    3: where
#    4: Exception
# Varnames:
#	certifi
# Local variables:
#    0: certifi

 71:           0 RESUME               0

 72:           2 NOP

 73:           4 LOAD_CONST           (0)
               6 LOAD_CONST           (None)
               8 IMPORT_NAME          (certifi)
              10 STORE_FAST           (certifi)

 75:          12 LOAD_GLOBAL          (NULL + ssl)
              22 LOAD_ATTR            (create_default_context)
              42 LOAD_FAST            (certifi)
              44 LOAD_ATTR            (NULL|self + where)
              64 CALL                 0
              72 KW_NAMES             (('cafile',))
              74 CALL                 1
              82 RETURN_VALUE
              84 PUSH_EXC_INFO

 76:          86 LOAD_GLOBAL          (Exception)
              96 CHECK_EXC_MATCH
              98 POP_JUMP_IF_FALSE    (to 146)
             100 POP_TOP

 77:         102 LOAD_GLOBAL          (NULL + ssl)
             112 LOAD_ATTR            (create_default_context)
             132 CALL                 0
             140 SWAP                 (TOS <-> TOS1)
             142 POP_EXCEPT
             144 RETURN_VALUE

 76:     >>  146 RERAISE              0
             148 COPY                 3
             150 POP_EXCEPT
             152 RERAISE              1

ExceptionTable:
  4 to 80 -> 84 [0]
  84 to 140 -> 148 [1] lasti
  146 to 146 -> 148 [1] lasti

# Method Name:       _version_key
# Filename:          src\updater.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  6
# Stack size:        7
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        83
# Constants:
#    0: None
#    1: ''
#    2: 'v'
#    3: (0, 0, 0)
#    4: '-'
#    5: 1
#    6: 0
#    7: '+'
#    8: '.'
#    9: '\\d+'
#   10: 3
# Names:
#    0: str
#    1: strip
#    2: lower
#    3: lstrip
#    4: split
#    5: re
#    6: search
#    7: append
#    8: int
#    9: group
#   10: len
#   11: tuple
# Varnames:
#	v, text, core, parts, tok, m
# Positional arguments:
#	v
# Local variables:
#    1: text
#    2: core
#    3: parts
#    4: tok
#    5: m

 83:           0 RESUME               0

 84:           2 LOAD_GLOBAL          (NULL + str)
              12 LOAD_FAST            (v)
              14 COPY                 1
              16 POP_JUMP_IF_TRUE     (to 22)
              18 POP_TOP
              20 LOAD_CONST           ("")
         >>   22 CALL                 1
              30 LOAD_ATTR            (NULL|self + strip)
              50 CALL                 0
              58 LOAD_ATTR            (NULL|self + lower)
              78 CALL                 0
              86 LOAD_ATTR            (NULL|self + lstrip)
             106 LOAD_CONST           ("v")
             108 CALL                 1
             116 STORE_FAST           (text)

 85:         118 LOAD_FAST            (text)
             120 POP_JUMP_IF_TRUE     (to 124)

 86:         122 RETURN_CONST         ((0, 0, 0))

 87:     >>  124 LOAD_FAST            (text)
             126 LOAD_ATTR            (NULL|self + split)
             146 LOAD_CONST           ("-")
             148 LOAD_CONST           (1)
             150 CALL                 2
             158 LOAD_CONST           (0)
             160 BINARY_SUBSCR
             164 LOAD_ATTR            (NULL|self + split)
             184 LOAD_CONST           ("+")
             186 LOAD_CONST           (1)
             188 CALL                 2
             196 LOAD_CONST           (0)
             198 BINARY_SUBSCR
             202 STORE_FAST           (core)

 88:         204 BUILD_LIST           0
             206 STORE_FAST           (parts)

 89:         208 LOAD_FAST            (core)
             210 LOAD_ATTR            (NULL|self + split)
             230 LOAD_CONST           (".")
             232 CALL                 1
             240 GET_ITER
             242 FOR_ITER             (to 382)
             246 STORE_FAST           (tok)

 90:         248 LOAD_GLOBAL          (NULL + re)
             258 LOAD_ATTR            (search)
             278 LOAD_CONST           ("\\d+")
             280 LOAD_FAST            (tok)
             282 CALL                 2
             290 STORE_FAST           (m)

 91:         292 LOAD_FAST            (parts)
             294 LOAD_ATTR            (NULL|self + append)
             314 LOAD_FAST            (m)
             316 POP_JUMP_IF_FALSE    (to 368)
             318 LOAD_GLOBAL          (NULL + int)
             328 LOAD_FAST            (m)
             330 LOAD_ATTR            (NULL|self + group)
             350 CALL                 0
             358 CALL                 1
             366 JUMP_FORWARD         (to 370)
         >>  368 LOAD_CONST           (0)
         >>  370 CALL                 1
             378 POP_TOP
         >>  380 JUMP_BACKWARD        (to 242)

 89:         382 END_FOR

 92:         384 LOAD_GLOBAL          (NULL + len)
             394 LOAD_FAST            (parts)
             396 CALL                 1
             404 LOAD_CONST           (3)
             406 COMPARE_OP           (<)
             410 POP_JUMP_IF_FALSE    (to 476)

 93:         412 LOAD_FAST            (parts)
             414 LOAD_ATTR            (NULL|self + append)
             434 LOAD_CONST           (0)
             436 CALL                 1
             444 POP_TOP

 92:         446 LOAD_GLOBAL          (NULL + len)
             456 LOAD_FAST            (parts)
             458 CALL                 1
             466 LOAD_CONST           (3)
             468 COMPARE_OP           (<)
             472 POP_JUMP_IF_FALSE    (to 476)
             474 JUMP_BACKWARD        (to 412)

 94:     >>  476 LOAD_GLOBAL          (NULL + tuple)
             486 LOAD_FAST            (parts)
             488 CALL                 1
             496 RETURN_VALUE


# Method Name:       _version_newer
# Filename:          src\updater.py
# Argument count:    2
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  2
# Stack size:        4
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        97
# Constants:
#    0: None
# Names:
#    0: _version_key
# Varnames:
#	latest, current
# Positional arguments:
#	latest, current

 97:           0 RESUME               0

 98:           2 LOAD_GLOBAL          (NULL + _version_key)
              12 LOAD_FAST            (latest)
              14 CALL                 1
              22 LOAD_GLOBAL          (NULL + _version_key)
              32 LOAD_FAST            (current)
              34 CALL                 1
              42 COMPARE_OP           (>)
              46 RETURN_VALUE


# Method Name:       _find_platform_asset
# Filename:          src\updater.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  4
# Stack size:        8
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        101
# Constants:
#    0: None
#    1: ('.exe', '.msi', 'windows', 'win')
#    2: ('.dmg', '.pkg', 'macos', 'mac', 'darwin')
#    3: ('.appimage', '.deb', '.rpm', '.tar.gz', 'linux')
#    4: ('windows', 'darwin', 'linux')
#    5: 'name'
#    6: ''
#    7: <Code311 code object <genexpr> at 0x2e1d01e0160, file src\updater.py>, line 112
# Names:
#    0: platform
#    1: system
#    2: lower
#    3: isinstance
#    4: dict
#    5: str
#    6: get
#    7: any
# Varnames:
#	assets, system, patterns, asset
# Positional arguments:
#	assets
# Local variables:
#    1: system
#    2: patterns
#    3: asset
# Cell variables:
#    0: name
               0 MAKE_CELL            (name)

101:           2 RESUME               0

102:           4 LOAD_GLOBAL          (NULL + platform)
              14 LOAD_ATTR            (system)
              34 CALL                 0
              42 LOAD_ATTR            (NULL|self + lower)
              62 CALL                 0
              70 STORE_FAST           (system)

104:          72 BUILD_LIST           0
              74 LOAD_CONST           (('.exe', '.msi', 'windows', 'win'))
              76 LIST_EXTEND          1

105:          78 BUILD_LIST           0
              80 LOAD_CONST           (('.dmg', '.pkg', 'macos', 'mac', 'darwin'))
              82 LIST_EXTEND          1

106:          84 BUILD_LIST           0
              86 LOAD_CONST           (('.appimage', '.deb', '.rpm', '.tar.gz', 'linux'))
              88 LIST_EXTEND          1

103:          90 LOAD_CONST           (('windows', 'darwin', 'linux'))
              92 BUILD_CONST_KEY_MAP  3
              94 STORE_FAST           (patterns)

108:          96 LOAD_FAST            (assets)
              98 GET_ITER
             100 FOR_ITER             (to 316)
             104 STORE_FAST           (asset)

109:         106 LOAD_GLOBAL          (NULL + isinstance)
             116 LOAD_FAST            (asset)
             118 LOAD_GLOBAL          (dict)
             128 CALL                 2
             136 POP_JUMP_IF_TRUE     (to 140)

110:         138 JUMP_BACKWARD        (to 100)

111:     >>  140 LOAD_GLOBAL          (NULL + str)
             150 LOAD_FAST            (asset)
             152 LOAD_ATTR            (NULL|self + get)
             172 LOAD_CONST           ("name")
             174 CALL                 1
             182 COPY                 1
             184 POP_JUMP_IF_TRUE     (to 190)
             186 POP_TOP
             188 LOAD_CONST           ("")
         >>  190 CALL                 1
             198 LOAD_ATTR            (NULL|self + lower)
             218 CALL                 0
             226 STORE_DEREF          (name)

112:         228 LOAD_DEREF           (name)
             230 POP_JUMP_IF_TRUE     (to 234)
             232 JUMP_BACKWARD        (to 100)
         >>  234 LOAD_GLOBAL          (NULL + any)
             244 LOAD_CLOSURE         (name)
             246 BUILD_TUPLE          1
             248 LOAD_CONST           (<Code311 code object <genexpr> at 0x2e1d01e0160, file src\updater.py>, line 112)
             250 MAKE_FUNCTION        (closure)
             252 LOAD_FAST            (patterns)
             254 LOAD_ATTR            (NULL|self + get)
             274 LOAD_FAST            (system)
             276 BUILD_LIST           0
             278 CALL                 2
             286 GET_ITER
             288 CALL                 0
             296 CALL                 1
             304 POP_JUMP_IF_TRUE     (to 308)
             306 JUMP_BACKWARD        (to 100)

113:     >>  308 LOAD_FAST            (asset)
             310 SWAP                 (TOS <-> TOS1)
             312 POP_TOP
         >>  314 RETURN_VALUE

108:         316 END_FOR

114:         318 LOAD_FAST            (assets)
             320 GET_ITER
             322 FOR_ITER             (to 370)
             326 STORE_FAST           (asset)

115:         328 LOAD_GLOBAL          (NULL + isinstance)
             338 LOAD_FAST            (asset)
             340 LOAD_GLOBAL          (dict)
             350 CALL                 2
             358 POP_JUMP_IF_TRUE     (to 362)
             360 JUMP_BACKWARD        (to 322)

116:     >>  362 LOAD_FAST            (asset)
             364 SWAP                 (TOS <-> TOS1)
             366 POP_TOP
         >>  368 RETURN_VALUE

114:         370 END_FOR

117:         372 RETURN_CONST         (None)


# Method Name:       _check_latest_release
# Filename:          src\updater.py
# Argument count:    4
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  15
# Stack size:        12
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        120
# Constants:
#    0: 'Blocking GitHub API call — run inside a worker thread.\n\n    Returns the release info dict if a newer version exists, else None.\n    Raises RuntimeError on network/API problems.\n    '
#    1: 'https://api.github.com/repos/'
#    2: '/'
#    3: '/releases/latest'
#    4: 'application/vnd.github+json'
#    5: ('User-Agent', 'Accept')
#    6: ('headers',)
#    7: 15
#    8: ('timeout', 'context')
#    9: None
#   10: 'GitHub API error: HTTP '
#   11: 'Network error: '
#   12: 'tag_name'
#   13: ''
#   14: 'Missing tag_name in release'
#   15: 'v'
#   16: 'assets'
#   17: 'browser_download_url'
#   18: 'name'
#   19: 'No downloadable asset for this platform'
#   20: 'body'
#   21: 'published_at'
#   22: 'html_url'
#   23: ('version', 'tag_name', 'name', 'body', 'published_at', 'download_url', 'filename', 'html_url')
# Names:
#    0: Request
#    1: _USER_AGENT
#    2: urlopen
#    3: _get_ssl_context
#    4: json
#    5: loads
#    6: read
#    7: decode
#    8: HTTPError
#    9: RuntimeError
#   10: code
#   11: URLError
#   12: reason
#   13: str
#   14: get
#   15: strip
#   16: lstrip
#   17: _version_newer
#   18: _find_platform_asset
#   19: Path
#   20: name
#   21: DEFAULT_INSTALLER_NAME
# Varnames:
#	owner, repo, current_version, fallback_url, url, req, resp, data, e, tag, latest, assets, asset, dl_url, filename
# Positional arguments:
#	owner, repo, current_version, fallback_url
# Local variables:
#    4: url
#    5: req
#    6: resp
#    7: data
#    8: e
#    9: tag
#   10: latest
#   11: assets
#   12: asset
#   13: dl_url
#   14: filename

120:           0 RESUME               0

131:           2 LOAD_CONST           ("https://api.github.com/repos/")
               4 LOAD_FAST            (owner)
               6 FORMAT_VALUE         0
               8 LOAD_CONST           ("/")
              10 LOAD_FAST            (repo)
              12 FORMAT_VALUE         0
              14 LOAD_CONST           ("/releases/latest")
              16 BUILD_STRING         5
              18 STORE_FAST           (url)

132:          20 LOAD_GLOBAL          (NULL + Request)

133:          30 LOAD_FAST            (url)

135:          32 LOAD_GLOBAL          (_USER_AGENT)

136:          42 LOAD_CONST           ("application/vnd.github+json")

134:          44 LOAD_CONST           (('User-Agent', 'Accept'))
              46 BUILD_CONST_KEY_MAP  2

132:          48 KW_NAMES             (('headers',))
              50 CALL                 2
              58 STORE_FAST           (req)

139:          60 NOP

140:          62 LOAD_GLOBAL          (NULL + urlopen)
              72 LOAD_FAST            (req)
              74 LOAD_CONST           (15)
              76 LOAD_GLOBAL          (NULL + _get_ssl_context)
              86 CALL                 0
              94 KW_NAMES             (('timeout', 'context'))
              96 CALL                 3
             104 BEFORE_WITH
             106 STORE_FAST           (resp)

141:         108 LOAD_GLOBAL          (NULL + json)
             118 LOAD_ATTR            (loads)
             138 LOAD_FAST            (resp)
             140 LOAD_ATTR            (NULL|self + read)
             160 CALL                 0
             168 LOAD_ATTR            (NULL|self + decode)
             188 CALL                 0
             196 CALL                 1
             204 STORE_FAST           (data)

140:         206 LOAD_CONST           (None)
             208 LOAD_CONST           (None)
             210 LOAD_CONST           (None)
             212 CALL                 2
             220 POP_TOP

147:         222 LOAD_GLOBAL          (NULL + str)
             232 LOAD_FAST_CHECK      (data)
             234 LOAD_ATTR            (NULL|self + get)
             254 LOAD_CONST           ("tag_name")
             256 CALL                 1
             264 COPY                 1
             266 POP_JUMP_IF_TRUE     (to 272)
             268 POP_TOP
             270 LOAD_CONST           ("")
         >>  272 CALL                 1
             280 LOAD_ATTR            (NULL|self + strip)
             300 CALL                 0
             308 STORE_FAST           (tag)

148:         310 LOAD_FAST            (tag)
             312 POP_JUMP_IF_TRUE     (to 336)

149:         314 LOAD_GLOBAL          (NULL + RuntimeError)
             324 LOAD_CONST           ("Missing tag_name in release")
             326 CALL                 1
             334 RAISE_VARARGS        (exception instance)

151:     >>  336 LOAD_FAST            (tag)
             338 LOAD_ATTR            (NULL|self + lstrip)
             358 LOAD_CONST           ("v")
             360 CALL                 1
             368 STORE_FAST           (latest)

152:         370 LOAD_GLOBAL          (NULL + _version_newer)
             380 LOAD_FAST            (latest)
             382 LOAD_FAST            (current_version)
             384 CALL                 2
             392 POP_JUMP_IF_TRUE     (to 396)

153:         394 RETURN_CONST         (None)

155:     >>  396 LOAD_FAST            (data)
             398 LOAD_ATTR            (NULL|self + get)
             418 LOAD_CONST           ("assets")
             420 CALL                 1
             428 COPY                 1
             430 POP_JUMP_IF_TRUE     (to 436)
             432 POP_TOP
             434 BUILD_LIST           0
         >>  436 STORE_FAST           (assets)

156:         438 LOAD_GLOBAL          (NULL + _find_platform_asset)
             448 LOAD_FAST            (assets)
             450 CALL                 1
             458 STORE_FAST           (asset)

157:         460 LOAD_CONST           ("")
             462 STORE_FAST           (dl_url)

158:         464 LOAD_CONST           ("")
             466 STORE_FAST           (filename)

159:         468 LOAD_FAST            (asset)
             470 POP_JUMP_IF_FALSE    (to 648)

160:         472 LOAD_GLOBAL          (NULL + str)
             482 LOAD_FAST            (asset)
             484 LOAD_ATTR            (NULL|self + get)
             504 LOAD_CONST           ("browser_download_url")
             506 CALL                 1
             514 COPY                 1
             516 POP_JUMP_IF_TRUE     (to 522)
             518 POP_TOP
             520 LOAD_CONST           ("")
         >>  522 CALL                 1
             530 LOAD_ATTR            (NULL|self + strip)
             550 CALL                 0
             558 STORE_FAST           (dl_url)

161:         560 LOAD_GLOBAL          (NULL + str)
             570 LOAD_FAST            (asset)
             572 LOAD_ATTR            (NULL|self + get)
             592 LOAD_CONST           ("name")
             594 CALL                 1
             602 COPY                 1
             604 POP_JUMP_IF_TRUE     (to 610)
             606 POP_TOP
             608 LOAD_CONST           ("")
         >>  610 CALL                 1
             618 LOAD_ATTR            (NULL|self + strip)
             638 CALL                 0
             646 STORE_FAST           (filename)

162:     >>  648 LOAD_FAST            (dl_url)
             650 POP_JUMP_IF_TRUE     (to 718)
             652 LOAD_FAST            (fallback_url)
             654 POP_JUMP_IF_FALSE    (to 718)

163:         656 LOAD_FAST            (fallback_url)
             658 STORE_FAST           (dl_url)

164:         660 LOAD_GLOBAL          (NULL + Path)
             670 LOAD_FAST            (dl_url)
             672 CALL                 1
             680 LOAD_ATTR            (name)
             700 COPY                 1
             702 POP_JUMP_IF_TRUE     (to 716)
             704 POP_TOP
             706 LOAD_GLOBAL          (DEFAULT_INSTALLER_NAME)
         >>  716 STORE_FAST           (filename)

165:     >>  718 LOAD_FAST            (dl_url)
             720 POP_JUMP_IF_TRUE     (to 744)

166:         722 LOAD_GLOBAL          (NULL + RuntimeError)
             732 LOAD_CONST           ("No downloadable asset for this platform")
             734 CALL                 1
             742 RAISE_VARARGS        (exception instance)

169:     >>  744 LOAD_FAST            (latest)

170:         746 LOAD_FAST            (tag)

171:         748 LOAD_GLOBAL          (NULL + str)
             758 LOAD_FAST            (data)
             760 LOAD_ATTR            (NULL|self + get)
             780 LOAD_CONST           ("name")
             782 CALL                 1
             790 COPY                 1
             792 POP_JUMP_IF_TRUE     (to 798)
             794 POP_TOP
             796 LOAD_FAST            (tag)
         >>  798 CALL                 1

172:         806 LOAD_GLOBAL          (NULL + str)
             816 LOAD_FAST            (data)
             818 LOAD_ATTR            (NULL|self + get)
             838 LOAD_CONST           ("body")
             840 CALL                 1
             848 COPY                 1
             850 POP_JUMP_IF_TRUE     (to 856)
             852 POP_TOP
             854 LOAD_CONST           ("")
         >>  856 CALL                 1

173:         864 LOAD_GLOBAL          (NULL + str)
             874 LOAD_FAST            (data)
             876 LOAD_ATTR            (NULL|self + get)
             896 LOAD_CONST           ("published_at")
             898 CALL                 1
             906 COPY                 1
             908 POP_JUMP_IF_TRUE     (to 914)
             910 POP_TOP
             912 LOAD_CONST           ("")
         >>  914 CALL                 1

174:         922 LOAD_FAST            (dl_url)

175:         924 LOAD_FAST            (filename)
             926 COPY                 1
             928 POP_JUMP_IF_TRUE     (to 942)
             930 POP_TOP
             932 LOAD_GLOBAL          (DEFAULT_INSTALLER_NAME)

176:     >>  942 LOAD_GLOBAL          (NULL + str)
             952 LOAD_FAST            (data)
             954 LOAD_ATTR            (NULL|self + get)
             974 LOAD_CONST           ("html_url")
             976 CALL                 1
             984 COPY                 1
             986 POP_JUMP_IF_TRUE     (to 992)
             988 POP_TOP
             990 LOAD_CONST           ("")
         >>  992 CALL                 1

168:        1000 LOAD_CONST           (('version', 'tag_name', 'name', 'body', 'published_at', 'download_url', 'filename', 'html_url'))
            1002 BUILD_CONST_KEY_MAP  8
            1004 RETURN_VALUE

140:        1006 PUSH_EXC_INFO
            1008 WITH_EXCEPT_START
            1010 POP_JUMP_IF_TRUE     (to 1014)
            1012 RERAISE              2
         >> 1014 POP_TOP
            1016 POP_EXCEPT
            1018 POP_TOP
            1020 POP_TOP
            1022 EXTENDED_ARG         (256)
            1024 JUMP_BACKWARD        (to 222)
            1026 COPY                 3
            1028 POP_EXCEPT
            1030 RERAISE              1
            1032 PUSH_EXC_INFO

142:        1034 LOAD_GLOBAL          (HTTPError)
            1044 CHECK_EXC_MATCH
            1046 POP_JUMP_IF_FALSE    (to 1108)
            1048 STORE_FAST           (e)

143:        1050 LOAD_GLOBAL          (NULL + RuntimeError)
            1060 LOAD_CONST           ("GitHub API error: HTTP ")
            1062 LOAD_FAST            (e)
            1064 LOAD_ATTR            (code)
            1084 FORMAT_VALUE         0
            1086 BUILD_STRING         2
            1088 CALL                 1
            1096 LOAD_FAST            (e)
            1098 RAISE_VARARGS        (exception instance with __cause__)
            1100 LOAD_CONST           (None)
            1102 STORE_FAST           (e)
            1104 DELETE_FAST          (e)
            1106 RERAISE              1

144:     >> 1108 LOAD_GLOBAL          (URLError)
            1118 CHECK_EXC_MATCH
            1120 POP_JUMP_IF_FALSE    (to 1182)
            1122 STORE_FAST           (e)

145:        1124 LOAD_GLOBAL          (NULL + RuntimeError)
            1134 LOAD_CONST           ("Network error: ")
            1136 LOAD_FAST            (e)
            1138 LOAD_ATTR            (reason)
            1158 FORMAT_VALUE         0
            1160 BUILD_STRING         2
            1162 CALL                 1
            1170 LOAD_FAST            (e)
            1172 RAISE_VARARGS        (exception instance with __cause__)
            1174 LOAD_CONST           (None)
            1176 STORE_FAST           (e)
            1178 DELETE_FAST          (e)
            1180 RERAISE              1

144:     >> 1182 RERAISE              0
            1184 COPY                 3
            1186 POP_EXCEPT
            1188 RERAISE              1

ExceptionTable:
  62 to 104 -> 1032 [0]
  106 to 204 -> 1006 [1] lasti
  206 to 220 -> 1032 [0]
  1006 to 1014 -> 1026 [3] lasti
  1016 to 1030 -> 1032 [0]
  1032 to 1048 -> 1184 [1] lasti
  1050 to 1098 -> 1100 [1] lasti
  1100 to 1122 -> 1184 [1] lasti
  1124 to 1172 -> 1174 [1] lasti
  1174 to 1182 -> 1184 [1] lasti

# Method Name:       _download_installer
# Filename:          src\updater.py
# Argument count:    4
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  12
# Stack size:        14
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        180
# Constants:
#    0: 'Blocking download — run inside a worker thread. Returns the file path.'
#    1: 'tv_update_'
#    2: ('prefix',)
#    3: '*/*'
#    4: ('User-Agent', 'Accept')
#    5: ('headers',)
#    6: 60
#    7: ('timeout', 'context')
#    8: 'Content-Length'
#    9: 0
#   10: 'wb'
#   11: 'Đã hủy tải xuống'
#   12: 8192
#   13: 100
#   14: None
# Names:
#    0: tempfile
#    1: mkdtemp
#    2: os
#    3: path
#    4: join
#    5: Request
#    6: _USER_AGENT
#    7: urlopen
#    8: _get_ssl_context
#    9: int
#   10: headers
#   11: get
#   12: open
#   13: RuntimeError
#   14: read
#   15: write
#   16: len
#   17: max
#   18: min
# Varnames:
#	url, filename, progress_cb, should_stop, tmp, path, req, resp, total, downloaded, f, chunk
# Positional arguments:
#	url, filename, progress_cb, should_stop
# Local variables:
#    4: tmp
#    5: path
#    6: req
#    7: resp
#    8: total
#    9: downloaded
#   10: f
#   11: chunk

180:           0 RESUME               0

187:           2 LOAD_GLOBAL          (NULL + tempfile)
              12 LOAD_ATTR            (mkdtemp)
              32 LOAD_CONST           ("tv_update_")
              34 KW_NAMES             (('prefix',))
              36 CALL                 1
              44 STORE_FAST           (tmp)

188:          46 LOAD_GLOBAL          (os)
              56 LOAD_ATTR            (path)
              76 LOAD_ATTR            (NULL|self + join)
              96 LOAD_FAST            (tmp)
              98 LOAD_FAST            (filename)
             100 CALL                 2
             108 STORE_FAST           (path)

190:         110 LOAD_GLOBAL          (NULL + Request)
             120 LOAD_FAST            (url)
             122 LOAD_GLOBAL          (_USER_AGENT)
             132 LOAD_CONST           ("*/*")
             134 LOAD_CONST           (('User-Agent', 'Accept'))
             136 BUILD_CONST_KEY_MAP  2
             138 KW_NAMES             (('headers',))
             140 CALL                 2
             148 STORE_FAST           (req)

191:         150 LOAD_GLOBAL          (NULL + urlopen)
             160 LOAD_FAST            (req)
             162 LOAD_CONST           (60)
             164 LOAD_GLOBAL          (NULL + _get_ssl_context)
             174 CALL                 0
             182 KW_NAMES             (('timeout', 'context'))
             184 CALL                 3
             192 BEFORE_WITH
             194 STORE_FAST           (resp)

192:         196 LOAD_GLOBAL          (NULL + int)
             206 LOAD_FAST            (resp)
             208 LOAD_ATTR            (headers)
             228 LOAD_ATTR            (NULL|self + get)
             248 LOAD_CONST           ("Content-Length")
             250 LOAD_CONST           (0)
             252 CALL                 2
             260 CALL                 1
             268 STORE_FAST           (total)

193:         270 LOAD_CONST           (0)
             272 STORE_FAST           (downloaded)

194:         274 LOAD_GLOBAL          (NULL + open)
             284 LOAD_FAST            (path)
             286 LOAD_CONST           ("wb")
             288 CALL                 2
             296 BEFORE_WITH
             298 STORE_FAST           (f)

195:         300 NOP

196:         302 PUSH_NULL
             304 LOAD_FAST            (should_stop)
             306 CALL                 0
             314 POP_JUMP_IF_FALSE    (to 338)

197:         316 LOAD_GLOBAL          (NULL + RuntimeError)
             326 LOAD_CONST           ("Đã hủy tải xuống")
             328 CALL                 1
             336 RAISE_VARARGS        (exception instance)

198:     >>  338 LOAD_FAST            (resp)
             340 LOAD_ATTR            (NULL|self + read)
             360 LOAD_CONST           (8192)
             362 CALL                 1
             370 STORE_FAST           (chunk)

199:         372 LOAD_FAST            (chunk)
             374 POP_JUMP_IF_TRUE     (to 378)

200:         376 JUMP_FORWARD         (to 538)

201:     >>  378 LOAD_FAST            (f)
             380 LOAD_ATTR            (NULL|self + write)
             400 LOAD_FAST            (chunk)
             402 CALL                 1
             410 POP_TOP

202:         412 LOAD_FAST            (downloaded)
             414 LOAD_GLOBAL          (NULL + len)
             424 LOAD_FAST            (chunk)
             426 CALL                 1
             434 BINARY_OP            (+=)
             438 STORE_FAST           (downloaded)

203:         440 LOAD_FAST            (total)
             442 LOAD_CONST           (0)
             444 COMPARE_OP           (>)
             448 POP_JUMP_IF_FALSE    (to 536)

204:         450 PUSH_NULL
             452 LOAD_FAST            (progress_cb)
             454 LOAD_GLOBAL          (NULL + max)
             464 LOAD_CONST           (0)
             466 LOAD_GLOBAL          (NULL + min)
             476 LOAD_CONST           (100)
             478 LOAD_GLOBAL          (NULL + int)
             488 LOAD_FAST            (downloaded)
             490 LOAD_FAST            (total)
             492 BINARY_OP            (/)
             496 LOAD_CONST           (100)
             498 BINARY_OP            (*)
             502 CALL                 1
             510 CALL                 2
             518 CALL                 2
             526 CALL                 1
             534 POP_TOP

195:     >>  536 JUMP_BACKWARD        (to 302)

200:     >>  538 NOP

194:         540 LOAD_CONST           (None)
             542 LOAD_CONST           (None)
             544 LOAD_CONST           (None)
             546 CALL                 2
             554 POP_TOP

191:         556 LOAD_CONST           (None)
             558 LOAD_CONST           (None)
             560 LOAD_CONST           (None)
             562 CALL                 2
             570 POP_TOP

205:         572 LOAD_FAST_CHECK      (total)
             574 LOAD_CONST           (0)
             576 COMPARE_OP           (<=)
             580 POP_JUMP_IF_FALSE    (to 598)

206:         582 PUSH_NULL
             584 LOAD_FAST            (progress_cb)
             586 LOAD_CONST           (100)
             588 CALL                 1
             596 POP_TOP

207:     >>  598 LOAD_FAST            (path)
             600 RETURN_VALUE

194:         602 PUSH_EXC_INFO
             604 WITH_EXCEPT_START
             606 POP_JUMP_IF_TRUE     (to 610)
             608 RERAISE              2
         >>  610 POP_TOP
             612 POP_EXCEPT
             614 POP_TOP
             616 POP_TOP
             618 JUMP_BACKWARD        (to 556)
             620 COPY                 3
             622 POP_EXCEPT
             624 RERAISE              1

191:         626 PUSH_EXC_INFO
             628 WITH_EXCEPT_START
             630 POP_JUMP_IF_TRUE     (to 634)
             632 RERAISE              2
         >>  634 POP_TOP
             636 POP_EXCEPT
             638 POP_TOP
             640 POP_TOP
             642 JUMP_BACKWARD        (to 572)
             644 COPY                 3
             646 POP_EXCEPT
             648 RERAISE              1

ExceptionTable:
  194 to 296 -> 626 [1] lasti
  298 to 536 -> 602 [2] lasti
  540 to 554 -> 626 [1] lasti
  602 to 610 -> 620 [4] lasti
  612 to 624 -> 626 [1] lasti
  626 to 634 -> 644 [3] lasti

# Method Name:       UpdaterService
# Filename:          src\updater.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        4
# Flags:             0x01000000 (0x1000000)
# First Line:        213
# Constants:
#    0: 'UpdaterService'
#    1: 'Singleton holding update state; mutated by async tasks, polled by the UI.\n\n    Phases: ``idle`` → ``checking`` → ``available`` / ``up_to_date`` / ``error``\n            → ``downloading`` → ``ready`` (installer downloaded).\n    '
#    2: None
#    3: "'UpdaterService | None'"
#    4: '_instance'
#    5: ('fallback_download_url',)
#    6: <Code311 code object __init__ at 0x2e1d01e05a0, file src\updater.py>, line 222
#    7: <Code311 code object instance at 0x2e1d01e06b0, file src\updater.py>, line 250
#    8: <Code311 code object create at 0x2e1d01e07c0, file src\updater.py>, line 254
#    9: <Code311 code object _bump at 0x2e1d01e08d0, file src\updater.py>, line 272
#   10: <Code311 code object current_version at 0x2e1d01e09e0, file src\updater.py>, line 275
#   11: <Code311 code object is_configured at 0x2e1d01e0af0, file src\updater.py>, line 279
#   12: <Code311 code object is_busy at 0x2e1d01e0c00, file src\updater.py>, line 287
#   13: <Code311 code object update_available at 0x2e1d01e0d10, file src\updater.py>, line 290
#   14: <Code311 code object auto_check_once at 0x2e1d01e0e20, file src\updater.py>, line 293
#   15: <Code311 code object check_for_updates at 0x2e1d01e0f30, file src\updater.py>, line 302
#   16: <Code311 code object _run_check at 0x2e1d01e1150, file src\updater.py>, line 320
#   17: <Code311 code object download_update at 0x2e1d01e1370, file src\updater.py>, line 346
#   18: <Code311 code object _run_download at 0x2e1d01e16a0, file src\updater.py>, line 367
#   19: <Code311 code object _set_progress at 0x2e1d01e17b0, file src\updater.py>, line 394
#   20: <Code311 code object cancel_download at 0x2e1d01e18c0, file src\updater.py>, line 400
#   21: <Code311 code object install_update at 0x2e1d01e19d0, file src\updater.py>, line 407
#   22: ('repo_owner', 'str', 'repo_name', 'str', 'current_version', 'str', 'fallback_download_url', 'str | None')
#   23: ('return', "'UpdaterService | None'")
#   24: ('repo_owner', 'str', 'repo_name', 'str', 'current_version', 'str', 'fallback_download_url', 'str | None', 'return', "'UpdaterService'")
#   25: ('return', 'str')
#   26: ('return', 'bool')
#   27: ('url', 'str', 'filename', 'str')
#   28: ('pct', 'int')
#   29: ('return', 'tuple[bool, str]')
# Names:
#    0: __name__
#    1: __module__
#    2: __qualname__
#    3: __doc__
#    4: _instance
#    5: __annotations__
#    6: __init__
#    7: classmethod
#    8: instance
#    9: create
#   10: _bump
#   11: property
#   12: current_version
#   13: is_configured
#   14: is_busy
#   15: update_available
#   16: auto_check_once
#   17: check_for_updates
#   18: _run_check
#   19: download_update
#   20: _run_download
#   21: _set_progress
#   22: cancel_download
#   23: install_update

213:           0 RESUME               0
               2 LOAD_NAME            (__name__)
               4 STORE_NAME           (__module__)
               6 LOAD_CONST           ("UpdaterService")
               8 STORE_NAME           (__qualname__)
              10 SETUP_ANNOTATIONS

214:          12 LOAD_CONST           ("Singleton holding update state; mutated by async tasks, polled by the UI.\n\n    Phases: ``idle`` → ``checking`` → ``available`` / ``up_to_date`` / ``error``\n            → ``downloading`` → ``ready`` (installer downloaded).\n    ")
              14 STORE_NAME           (__doc__)

220:          16 LOAD_CONST           (None)
              18 STORE_NAME           (_instance)
              20 LOAD_CONST           ("'UpdaterService | None'")
              22 LOAD_NAME            (__annotations__)
              24 LOAD_CONST           ("_instance")
              26 STORE_SUBSCR

228:          30 LOAD_CONST           (None)

222:          32 LOAD_CONST           (('fallback_download_url',))
              34 BUILD_CONST_KEY_MAP  1

224:          36 NOP

222:          38 NOP

225:          40 NOP

222:          42 NOP

227:          44 NOP

222:          46 NOP

228:          48 NOP

222:          50 LOAD_CONST           (('repo_owner', 'str', 'repo_name', 'str', 'current_version', 'str', 'fallback_download_url', 'str | None'))
              52 LOAD_CONST           (<Code311 code object __init__ at 0x2e1d01e05a0, file src\updater.py>, line 222)
              54 MAKE_FUNCTION        (keyword-only, annotation)
              56 STORE_NAME           (__init__)

250:          58 LOAD_NAME            (classmethod)

251:          60 LOAD_CONST           (('return', "'UpdaterService | None'"))
              62 LOAD_CONST           (<Code311 code object instance at 0x2e1d01e06b0, file src\updater.py>, line 250)
              64 MAKE_FUNCTION        (annotation)

250:          66 CALL                 0

251:          74 STORE_NAME           (instance)

254:          76 LOAD_NAME            (classmethod)

261:          78 LOAD_CONST           (None)

255:          80 LOAD_CONST           (('fallback_download_url',))
              82 BUILD_CONST_KEY_MAP  1

257:          84 NOP

255:          86 NOP

258:          88 NOP

255:          90 NOP

260:          92 NOP

255:          94 NOP

261:          96 NOP

255:          98 NOP

262:         100 NOP

255:         102 LOAD_CONST           (('repo_owner', 'str', 'repo_name', 'str', 'current_version', 'str', 'fallback_download_url', 'str | None', 'return', "'UpdaterService'"))
             104 LOAD_CONST           (<Code311 code object create at 0x2e1d01e07c0, file src\updater.py>, line 254)
             106 MAKE_FUNCTION        (keyword-only, annotation)

254:         108 CALL                 0

255:         116 STORE_NAME           (create)

272:         118 LOAD_CONST           (<Code311 code object _bump at 0x2e1d01e08d0, file src\updater.py>, line 272)
             120 MAKE_FUNCTION        (No arguments)
             122 STORE_NAME           (_bump)

275:         124 LOAD_NAME            (property)

276:         126 LOAD_CONST           (('return', 'str'))
             128 LOAD_CONST           (<Code311 code object current_version at 0x2e1d01e09e0, file src\updater.py>, line 275)
             130 MAKE_FUNCTION        (annotation)

275:         132 CALL                 0

276:         140 STORE_NAME           (current_version)

279:         142 LOAD_CONST           (('return', 'bool'))
             144 LOAD_CONST           (<Code311 code object is_configured at 0x2e1d01e0af0, file src\updater.py>, line 279)
             146 MAKE_FUNCTION        (annotation)
             148 STORE_NAME           (is_configured)

287:         150 LOAD_CONST           (('return', 'bool'))
             152 LOAD_CONST           (<Code311 code object is_busy at 0x2e1d01e0c00, file src\updater.py>, line 287)
             154 MAKE_FUNCTION        (annotation)
             156 STORE_NAME           (is_busy)

290:         158 LOAD_CONST           (('return', 'bool'))
             160 LOAD_CONST           (<Code311 code object update_available at 0x2e1d01e0d10, file src\updater.py>, line 290)
             162 MAKE_FUNCTION        (annotation)
             164 STORE_NAME           (update_available)

293:         166 LOAD_CONST           (<Code311 code object auto_check_once at 0x2e1d01e0e20, file src\updater.py>, line 293)
             168 MAKE_FUNCTION        (No arguments)
             170 STORE_NAME           (auto_check_once)

302:         172 LOAD_CONST           (<Code311 code object check_for_updates at 0x2e1d01e0f30, file src\updater.py>, line 302)
             174 MAKE_FUNCTION        (No arguments)
             176 STORE_NAME           (check_for_updates)

320:         178 LOAD_CONST           (<Code311 code object _run_check at 0x2e1d01e1150, file src\updater.py>, line 320)
             180 MAKE_FUNCTION        (No arguments)
             182 STORE_NAME           (_run_check)

346:         184 LOAD_CONST           (<Code311 code object download_update at 0x2e1d01e1370, file src\updater.py>, line 346)
             186 MAKE_FUNCTION        (No arguments)
             188 STORE_NAME           (download_update)

367:         190 LOAD_CONST           (('url', 'str', 'filename', 'str'))
             192 LOAD_CONST           (<Code311 code object _run_download at 0x2e1d01e16a0, file src\updater.py>, line 367)
             194 MAKE_FUNCTION        (annotation)
             196 STORE_NAME           (_run_download)

394:         198 LOAD_CONST           (('pct', 'int'))
             200 LOAD_CONST           (<Code311 code object _set_progress at 0x2e1d01e17b0, file src\updater.py>, line 394)
             202 MAKE_FUNCTION        (annotation)
             204 STORE_NAME           (_set_progress)

400:         206 LOAD_CONST           (<Code311 code object cancel_download at 0x2e1d01e18c0, file src\updater.py>, line 400)
             208 MAKE_FUNCTION        (No arguments)
             210 STORE_NAME           (cancel_download)

407:         212 LOAD_CONST           (('return', 'tuple[bool, str]'))
             214 LOAD_CONST           (<Code311 code object install_update at 0x2e1d01e19d0, file src\updater.py>, line 407)
             216 MAKE_FUNCTION        (annotation)
             218 STORE_NAME           (install_update)
             220 RETURN_CONST         (None)


# Method Name:       <genexpr>
# Filename:          src\updater.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  2
# Stack size:        3
# Flags:             0x01000033 (0x1000000 | GENERATOR | NESTED | NEWLOCALS | OPTIMIZED)
# First Line:        112
# Constants:
#    0: None
# Varnames:
#	.0, p
# Positional arguments:
#	.0
# Local variables:
#    1: p
# Free variables:
#    0: name
               0 COPY_FREE_VARS       1

112:           2 RETURN_GENERATOR
               4 POP_TOP
               6 RESUME               0
               8 LOAD_FAST            (.0)
              10 FOR_ITER             (to 30)
              14 STORE_FAST           (p)
              16 LOAD_FAST            (p)
              18 LOAD_DEREF           (name)
              20 CONTAINS_OP          (in)
              22 YIELD_VALUE          1
              24 RESUME               1
              26 POP_TOP
         >>   28 JUMP_BACKWARD        (to 10)
              30 END_FOR
              32 RETURN_CONST         (None)
              34 CALL_INTRINSIC_1     3
              36 RERAISE              1

ExceptionTable:
  6 to 32 -> 34 [0] lasti

# Method Name:       __init__
# Filename:          src\updater.py
# Argument count:    3
# Position-only argument count: 0
# Keyword-only arguments: 2
# Number of locals:  5
# Stack size:        2
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        222
# Constants:
#    0: None
#    1: 'idle'
#    2: ''
#    3: 0
#    4: False
# Names:
#    0: _owner
#    1: _repo
#    2: _version
#    3: _fallback
#    4: phase
#    5: status_text
#    6: progress
#    7: release_info
#    8: installer_path
#    9: error
#   10: version
#   11: _check_task
#   12: _dl_task
#   13: _stop_download
#   14: _auto_checked
# Varnames:
#	self, repo_owner, repo_name, current_version, fallback_download_url
# Positional arguments:
#	self, repo_owner, repo_name
# Local variables:
#    3: current_version
#    4: fallback_download_url

222:           0 RESUME               0

230:           2 LOAD_FAST            (repo_owner)
               4 LOAD_FAST            (self)
               6 STORE_ATTR           (_owner)

231:          16 LOAD_FAST            (repo_name)
              18 LOAD_FAST            (self)
              20 STORE_ATTR           (_repo)

232:          30 LOAD_FAST            (current_version)
              32 LOAD_FAST            (self)
              34 STORE_ATTR           (_version)

233:          44 LOAD_FAST            (fallback_download_url)
              46 LOAD_FAST            (self)
              48 STORE_ATTR           (_fallback)

236:          58 LOAD_CONST           ("idle")
              60 LOAD_FAST            (self)
              62 STORE_ATTR           (phase)

237:          72 LOAD_CONST           ("")
              74 LOAD_FAST            (self)
              76 STORE_ATTR           (status_text)

238:          86 LOAD_CONST           (0)
              88 LOAD_FAST            (self)
              90 STORE_ATTR           (progress)

239:         100 LOAD_CONST           (None)
             102 LOAD_FAST            (self)
             104 STORE_ATTR           (release_info)

240:         114 LOAD_CONST           (None)
             116 LOAD_FAST            (self)
             118 STORE_ATTR           (installer_path)

241:         128 LOAD_CONST           (None)
             130 LOAD_FAST            (self)
             132 STORE_ATTR           (error)

242:         142 LOAD_CONST           (0)
             144 LOAD_FAST            (self)
             146 STORE_ATTR           (version)

244:         156 LOAD_CONST           (None)
             158 LOAD_FAST            (self)
             160 STORE_ATTR           (_check_task)

245:         170 LOAD_CONST           (None)
             172 LOAD_FAST            (self)
             174 STORE_ATTR           (_dl_task)

246:         184 LOAD_CONST           (False)
             186 LOAD_FAST            (self)
             188 STORE_ATTR           (_stop_download)

247:         198 LOAD_CONST           (False)
             200 LOAD_FAST            (self)
             202 STORE_ATTR           (_auto_checked)
             212 RETURN_CONST         (None)


# Method Name:       instance
# Filename:          src\updater.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  1
# Stack size:        1
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        250
# Constants:
#    0: None
# Names:
#    0: _instance
# Varnames:
#	cls
# Positional arguments:
#	cls

250:           0 RESUME               0

252:           2 LOAD_FAST            (cls)
               4 LOAD_ATTR            (_instance)
              24 RETURN_VALUE


# Method Name:       create
# Filename:          src\updater.py
# Argument count:    3
# Position-only argument count: 0
# Keyword-only arguments: 2
# Number of locals:  5
# Stack size:        6
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        254
# Constants:
#    0: None
#    1: ('current_version', 'fallback_download_url')
# Names:
#    0: _instance
# Varnames:
#	cls, repo_owner, repo_name, current_version, fallback_download_url
# Positional arguments:
#	cls, repo_owner, repo_name
# Local variables:
#    3: current_version
#    4: fallback_download_url

254:           0 RESUME               0

263:           2 PUSH_NULL
               4 LOAD_FAST            (cls)

264:           6 LOAD_FAST            (repo_owner)

265:           8 LOAD_FAST            (repo_name)

266:          10 LOAD_FAST            (current_version)

267:          12 LOAD_FAST            (fallback_download_url)

263:          14 KW_NAMES             (('current_version', 'fallback_download_url'))
              16 CALL                 4
              24 LOAD_FAST            (cls)
              26 STORE_ATTR           (_instance)

269:          36 LOAD_FAST            (cls)
              38 LOAD_ATTR            (_instance)
              58 RETURN_VALUE


# Method Name:       _bump
# Filename:          src\updater.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  1
# Stack size:        3
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        272
# Constants:
#    0: None
#    1: 1
# Names:
#    0: version
# Varnames:
#	self
# Positional arguments:
#	self

272:           0 RESUME               0

273:           2 LOAD_FAST            (self)
               4 COPY                 1
               6 LOAD_ATTR            (version)
              26 LOAD_CONST           (1)
              28 BINARY_OP            (+=)
              32 SWAP                 (TOS <-> TOS1)
              34 STORE_ATTR           (version)
              44 RETURN_CONST         (None)


# Method Name:       current_version
# Filename:          src\updater.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  1
# Stack size:        1
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        275
# Constants:
#    0: None
# Names:
#    0: _version
# Varnames:
#	self
# Positional arguments:
#	self

275:           0 RESUME               0

277:           2 LOAD_FAST            (self)
               4 LOAD_ATTR            (_version)
              24 RETURN_VALUE


# Method Name:       is_configured
# Filename:          src\updater.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  1
# Stack size:        3
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        279
# Constants:
#    0: None
#    1: 'REPLACE_ME'
# Names:
#    0: bool
#    1: _owner
#    2: _repo
# Varnames:
#	self
# Positional arguments:
#	self

279:           0 RESUME               0

281:           2 LOAD_GLOBAL          (NULL + bool)
              12 LOAD_FAST            (self)
              14 LOAD_ATTR            (_owner)
              34 CALL                 1
              42 COPY                 1
              44 POP_JUMP_IF_FALSE    (to 152)
              46 POP_TOP

282:          48 LOAD_GLOBAL          (NULL + bool)
              58 LOAD_FAST            (self)
              60 LOAD_ATTR            (_repo)
              80 CALL                 1

281:          88 COPY                 1
              90 POP_JUMP_IF_FALSE    (to 152)
              92 POP_TOP

283:          94 LOAD_CONST           ("REPLACE_ME")
              96 LOAD_FAST            (self)
              98 LOAD_ATTR            (_owner)
             118 CONTAINS_OP          (not in)

281:         120 COPY                 1
             122 POP_JUMP_IF_FALSE    (to 152)
             124 POP_TOP

284:         126 LOAD_CONST           ("REPLACE_ME")
             128 LOAD_FAST            (self)
             130 LOAD_ATTR            (_repo)
             150 CONTAINS_OP          (not in)

280:     >>  152 RETURN_VALUE


# Method Name:       is_busy
# Filename:          src\updater.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  1
# Stack size:        2
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        287
# Constants:
#    0: None
#    1: ('checking', 'downloading')
# Names:
#    0: phase
# Varnames:
#	self
# Positional arguments:
#	self

287:           0 RESUME               0

288:           2 LOAD_FAST            (self)
               4 LOAD_ATTR            (phase)
              24 LOAD_CONST           (('checking', 'downloading'))
              26 CONTAINS_OP          (in)
              28 RETURN_VALUE


# Method Name:       update_available
# Filename:          src\updater.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  1
# Stack size:        3
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        290
# Constants:
#    0: None
#    1: 'available'
# Names:
#    0: phase
#    1: bool
#    2: release_info
# Varnames:
#	self
# Positional arguments:
#	self

290:           0 RESUME               0

291:           2 LOAD_FAST            (self)
               4 LOAD_ATTR            (phase)
              24 LOAD_CONST           ("available")
              26 COMPARE_OP           (==)
              30 COPY                 1
              32 POP_JUMP_IF_FALSE    (to 76)
              34 POP_TOP
              36 LOAD_GLOBAL          (NULL + bool)
              46 LOAD_FAST            (self)
              48 LOAD_ATTR            (release_info)
              68 CALL                 1
         >>   76 RETURN_VALUE


# Method Name:       auto_check_once
# Filename:          src\updater.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  1
# Stack size:        2
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        293
# Constants:
#    0: 'Run a single background check per app session (called by the sidebar).'
#    1: None
#    2: True
# Names:
#    0: _auto_checked
#    1: is_configured
#    2: check_for_updates
# Varnames:
#	self
# Positional arguments:
#	self

293:           0 RESUME               0

295:           2 LOAD_FAST            (self)
               4 LOAD_ATTR            (_auto_checked)
              24 POP_JUMP_IF_FALSE    (to 28)

296:          26 RETURN_CONST         (None)

297:     >>   28 LOAD_CONST           (True)
              30 LOAD_FAST            (self)
              32 STORE_ATTR           (_auto_checked)

298:          42 LOAD_FAST            (self)
              44 LOAD_ATTR            (NULL|self + is_configured)
              64 CALL                 0
              72 POP_JUMP_IF_FALSE    (to 108)

299:          74 LOAD_FAST            (self)
              76 LOAD_ATTR            (NULL|self + check_for_updates)
              96 CALL                 0
             104 POP_TOP
             106 RETURN_CONST         (None)

298:     >>  108 RETURN_CONST         (None)


# Method Name:       check_for_updates
# Filename:          src\updater.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  1
# Stack size:        4
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        302
# Constants:
#    0: None
#    1: 'error'
#    2: 'Chưa cấu hình repo cập nhật (REPO_OWNER/REPO_NAME trong src/updater.py).'
#    3: 'checking'
#    4: 'Đang kiểm tra cập nhật...'
# Names:
#    0: is_busy
#    1: is_configured
#    2: phase
#    3: error
#    4: status_text
#    5: _bump
#    6: asyncio
#    7: create_task
#    8: _run_check
#    9: _check_task
# Varnames:
#	self
# Positional arguments:
#	self

302:           0 RESUME               0

303:           2 LOAD_FAST            (self)
               4 LOAD_ATTR            (NULL|self + is_busy)
              24 CALL                 0
              32 POP_JUMP_IF_FALSE    (to 36)

304:          34 RETURN_CONST         (None)

305:     >>   36 LOAD_FAST            (self)
              38 LOAD_ATTR            (NULL|self + is_configured)
              58 CALL                 0
              66 POP_JUMP_IF_TRUE     (to 164)

306:          68 LOAD_CONST           ("error")
              70 LOAD_FAST            (self)
              72 STORE_ATTR           (phase)

308:          82 LOAD_CONST           ("Chưa cấu hình repo cập nhật (REPO_OWNER/REPO_NAME trong src/updater.py).")

307:          84 LOAD_FAST            (self)
              86 STORE_ATTR           (error)

311:          96 LOAD_FAST            (self)
              98 LOAD_ATTR            (error)
             118 LOAD_FAST            (self)
             120 STORE_ATTR           (status_text)

312:         130 LOAD_FAST            (self)
             132 LOAD_ATTR            (NULL|self + _bump)
             152 CALL                 0
             160 POP_TOP

313:         162 RETURN_CONST         (None)

314:     >>  164 LOAD_CONST           ("checking")
             166 LOAD_FAST            (self)
             168 STORE_ATTR           (phase)

315:         178 LOAD_CONST           (None)
             180 LOAD_FAST            (self)
             182 STORE_ATTR           (error)

316:         192 LOAD_CONST           ("Đang kiểm tra cập nhật...")
             194 LOAD_FAST            (self)
             196 STORE_ATTR           (status_text)

317:         206 LOAD_FAST            (self)
             208 LOAD_ATTR            (NULL|self + _bump)
             228 CALL                 0
             236 POP_TOP

318:         238 LOAD_GLOBAL          (NULL + asyncio)
             248 LOAD_ATTR            (create_task)
             268 LOAD_FAST            (self)
             270 LOAD_ATTR            (NULL|self + _run_check)
             290 CALL                 0
             298 CALL                 1
             306 LOAD_FAST            (self)
             308 STORE_ATTR           (_check_task)
             318 RETURN_CONST         (None)


# Method Name:       _run_check
# Filename:          src\updater.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  3
# Stack size:        7
# Flags:             0x01000083 (0x1000000 | COROUTINE | NEWLOCALS | OPTIMIZED)
# First Line:        320
# Constants:
#    0: None
#    1: 'available'
#    2: 'Đã có phiên bản mới: v'
#    3: 'version'
#    4: 'up_to_date'
#    5: 'Bạn đang dùng phiên bản mới nhất.'
#    6: 'error'
#    7: 'Kiểm tra thất bại: '
#    8: 'Update check failed: '
# Names:
#    0: asyncio
#    1: to_thread
#    2: _check_latest_release
#    3: _owner
#    4: _repo
#    5: _version
#    6: _fallback
#    7: release_info
#    8: phase
#    9: status_text
#   10: Exception
#   11: str
#   12: error
#   13: logger
#   14: _bump
# Varnames:
#	self, result, exc
# Positional arguments:
#	self
# Local variables:
#    1: result
#    2: exc

320:           0 RETURN_GENERATOR
               2 POP_TOP
               4 RESUME               0

321:           6 NOP

322:           8 LOAD_GLOBAL          (NULL + asyncio)
              18 LOAD_ATTR            (to_thread)

323:          38 LOAD_GLOBAL          (_check_latest_release)

324:          48 LOAD_FAST            (self)
              50 LOAD_ATTR            (_owner)

325:          70 LOAD_FAST            (self)
              72 LOAD_ATTR            (_repo)

326:          92 LOAD_FAST            (self)
              94 LOAD_ATTR            (_version)

327:         114 LOAD_FAST            (self)
             116 LOAD_ATTR            (_fallback)

322:         136 CALL                 5
             144 GET_AWAITABLE        0
             146 LOAD_CONST           (None)
             148 SEND                 (to 156)
             152 YIELD_VALUE          4
             154 RESUME               3
         >>  156 JUMP_BACKWARD_NO_INTERRUPT (to 148)
             158 END_SEND
             160 STORE_FAST           (result)

329:         162 LOAD_FAST            (result)
             164 POP_JUMP_IF_FALSE    (to 222)

330:         166 LOAD_FAST            (result)
         >>  168 LOAD_FAST            (self)
             170 STORE_ATTR           (release_info)

331:         180 LOAD_CONST           ("available")
             182 LOAD_FAST            (self)
             184 STORE_ATTR           (phase)

332:         194 LOAD_CONST           ("Đã có phiên bản mới: v")
             196 LOAD_FAST            (result)
             198 LOAD_CONST           ("version")
             200 BINARY_SUBSCR
             204 FORMAT_VALUE         0
             206 BUILD_STRING         2
             208 LOAD_FAST            (self)
             210 STORE_ATTR           (status_text)
             220 JUMP_FORWARD         (to 264)

334:     >>  222 LOAD_CONST           (None)
             224 LOAD_FAST            (self)
             226 STORE_ATTR           (release_info)

335:         236 LOAD_CONST           ("up_to_date")
             238 LOAD_FAST            (self)
             240 STORE_ATTR           (phase)

336:         250 LOAD_CONST           ("Bạn đang dùng phiên bản mới nhất.")
             252 LOAD_FAST            (self)
             254 STORE_ATTR           (status_text)

343:     >>  264 LOAD_FAST            (self)
             266 LOAD_ATTR            (NULL|self + _bump)
             286 CALL                 0
             294 POP_TOP
             296 RETURN_CONST         (None)

322:         298 CLEANUP_THROW
             300 JUMP_BACKWARD        (to 158)
             302 PUSH_EXC_INFO

337:         304 LOAD_GLOBAL          (Exception)
             314 CHECK_EXC_MATCH
             316 POP_JUMP_IF_FALSE    (to 452)
             318 STORE_FAST           (exc)

338:         320 LOAD_CONST           ("error")
             322 LOAD_FAST            (self)
             324 STORE_ATTR           (phase)

339:         334 LOAD_GLOBAL          (NULL + str)
             344 LOAD_FAST            (exc)
             346 CALL                 1
             354 LOAD_FAST            (self)
             356 STORE_ATTR           (error)

340:         366 LOAD_CONST           ("Kiểm tra thất bại: ")
             368 LOAD_FAST            (exc)
             370 FORMAT_VALUE         0
             372 BUILD_STRING         2
             374 LOAD_FAST            (self)
             376 STORE_ATTR           (status_text)

341:         386 LOAD_GLOBAL          (NULL + logger)
             396 LOAD_ATTR            (error)
             416 LOAD_CONST           ("Update check failed: ")
             418 LOAD_FAST            (exc)
             420 FORMAT_VALUE         0
             422 BUILD_STRING         2
             424 CALL                 1
             432 POP_TOP
             434 POP_EXCEPT
             436 LOAD_CONST           (None)
             438 STORE_FAST           (exc)
             440 DELETE_FAST          (exc)
             442 JUMP_BACKWARD        (to 264)
             444 LOAD_CONST           (None)
         >>  446 STORE_FAST           (exc)
             448 DELETE_FAST          (exc)
             450 RERAISE              1

337:     >>  452 RERAISE              0
             454 COPY                 3
             456 POP_EXCEPT
             458 RERAISE              1
             460 PUSH_EXC_INFO

343:         462 LOAD_FAST            (self)
             464 LOAD_ATTR            (NULL|self + _bump)
             484 CALL                 0
             492 POP_TOP
             494 RERAISE              0
             496 COPY                 3
             498 POP_EXCEPT
             500 RERAISE              1
             502 CALL_INTRINSIC_1     3
             504 RERAISE              1

ExceptionTable:
  4 to 4 -> 502 [0] lasti
  8 to 150 -> 302 [0]
  152 to 152 -> 298 [2]
  154 to 262 -> 302 [0]
  264 to 296 -> 502 [0] lasti
  298 to 298 -> 302 [0]
  302 to 318 -> 454 [1] lasti
  320 to 432 -> 444 [1] lasti
  434 to 442 -> 460 [0]
  444 to 452 -> 454 [1] lasti
  454 to 458 -> 460 [0]
  460 to 494 -> 496 [1] lasti
  496 to 500 -> 502 [0] lasti

# Method Name:       download_update
# Filename:          src\updater.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  3
# Stack size:        6
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        346
# Constants:
#    0: None
#    1: 'download_url'
#    2: ''
#    3: 'filename'
#    4: 'error'
#    5: 'Không tìm thấy URL tải xuống'
#    6: False
#    7: 'downloading'
#    8: 0
#    9: 'Đang tải '
#   10: '...'
# Names:
#    0: is_busy
#    1: release_info
#    2: str
#    3: get
#    4: strip
#    5: DEFAULT_INSTALLER_NAME
#    6: phase
#    7: error
#    8: status_text
#    9: _bump
#   10: _stop_download
#   11: progress
#   12: asyncio
#   13: create_task
#   14: _run_download
#   15: _dl_task
# Varnames:
#	self, url, filename
# Positional arguments:
#	self
# Local variables:
#    1: url
#    2: filename

346:           0 RESUME               0

347:           2 LOAD_FAST            (self)
               4 LOAD_ATTR            (NULL|self + is_busy)
              24 CALL                 0
              32 POP_JUMP_IF_TRUE     (to 58)
              34 LOAD_FAST            (self)
              36 LOAD_ATTR            (release_info)
              56 POP_JUMP_IF_TRUE     (to 60)

348:     >>   58 RETURN_CONST         (None)

349:     >>   60 LOAD_GLOBAL          (NULL + str)
              70 LOAD_FAST            (self)
              72 LOAD_ATTR            (release_info)
              92 LOAD_ATTR            (NULL|self + get)
             112 LOAD_CONST           ("download_url")
             114 CALL                 1
             122 COPY                 1
             124 POP_JUMP_IF_TRUE     (to 130)
             126 POP_TOP
             128 LOAD_CONST           ("")
         >>  130 CALL                 1
             138 LOAD_ATTR            (NULL|self + strip)
             158 CALL                 0
             166 STORE_FAST           (url)

350:         168 LOAD_GLOBAL          (NULL + str)

351:         178 LOAD_FAST            (self)
             180 LOAD_ATTR            (release_info)
             200 LOAD_ATTR            (NULL|self + get)
             220 LOAD_CONST           ("filename")
             222 CALL                 1
             230 COPY                 1
             232 POP_JUMP_IF_TRUE     (to 246)
             234 POP_TOP
             236 LOAD_GLOBAL          (DEFAULT_INSTALLER_NAME)

350:     >>  246 CALL                 1

352:         254 LOAD_ATTR            (NULL|self + strip)
             274 CALL                 0

350:         282 STORE_FAST           (filename)

353:         284 LOAD_FAST            (url)
             286 POP_JUMP_IF_TRUE     (to 384)

354:         288 LOAD_CONST           ("error")
             290 LOAD_FAST            (self)
             292 STORE_ATTR           (phase)

355:         302 LOAD_CONST           ("Không tìm thấy URL tải xuống")
             304 LOAD_FAST            (self)
             306 STORE_ATTR           (error)

356:         316 LOAD_FAST            (self)
             318 LOAD_ATTR            (error)
             338 LOAD_FAST            (self)
             340 STORE_ATTR           (status_text)

357:         350 LOAD_FAST            (self)
             352 LOAD_ATTR            (NULL|self + _bump)
             372 CALL                 0
             380 POP_TOP

358:         382 RETURN_CONST         (None)

359:     >>  384 LOAD_CONST           (False)
             386 LOAD_FAST            (self)
             388 STORE_ATTR           (_stop_download)

360:         398 LOAD_CONST           ("downloading")
             400 LOAD_FAST            (self)
             402 STORE_ATTR           (phase)

361:         412 LOAD_CONST           (0)
             414 LOAD_FAST            (self)
             416 STORE_ATTR           (progress)

362:         426 LOAD_CONST           (None)
             428 LOAD_FAST            (self)
             430 STORE_ATTR           (error)

363:         440 LOAD_CONST           ("Đang tải ")
             442 LOAD_FAST            (filename)
             444 FORMAT_VALUE         0
             446 LOAD_CONST           ("...")
             448 BUILD_STRING         3
             450 LOAD_FAST            (self)
             452 STORE_ATTR           (status_text)

364:         462 LOAD_FAST            (self)
             464 LOAD_ATTR            (NULL|self + _bump)
             484 CALL                 0
             492 POP_TOP

365:         494 LOAD_GLOBAL          (NULL + asyncio)
             504 LOAD_ATTR            (create_task)
             524 LOAD_FAST            (self)
             526 LOAD_ATTR            (NULL|self + _run_download)
             546 LOAD_FAST            (url)
             548 LOAD_FAST            (filename)
             550 CALL                 2
             558 CALL                 1
             566 LOAD_FAST            (self)
             568 STORE_ATTR           (_dl_task)
             578 RETURN_CONST         (None)


# Method Name:       _run_download
# Filename:          src\updater.py
# Argument count:    3
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  6
# Stack size:        8
# Flags:             0x01000083 (0x1000000 | COROUTINE | NEWLOCALS | OPTIMIZED)
# First Line:        367
# Constants:
#    0: None
#    1: <Code311 code object _progress at 0x2e1d01e1480, file src\updater.py>, line 370
#    2: <Code311 code object <lambda> at 0x2e1d01e1590, file src\updater.py>, line 380
#    3: 100
#    4: 'ready'
#    5: 'Tải xuống hoàn tất. Sẵn sàng cài đặt.'
#    6: 'error'
#    7: 'Tải xuống thất bại: '
#    8: 'Update download failed: '
#    9: ('pct', 'int')
# Names:
#    0: asyncio
#    1: get_running_loop
#    2: to_thread
#    3: _download_installer
#    4: installer_path
#    5: progress
#    6: phase
#    7: status_text
#    8: Exception
#    9: str
#   10: error
#   11: logger
#   12: _bump
# Varnames:
#	self, url, filename, _progress, path, exc
# Positional arguments:
#	self, url, filename
# Local variables:
#    3: _progress
#    4: path
#    5: exc
# Cell variables:
#    0: self
#    1: loop
               0 MAKE_CELL            (self)
               2 MAKE_CELL            (loop)

367:           4 RETURN_GENERATOR
               6 POP_TOP
               8 RESUME               0

368:          10 LOAD_GLOBAL          (NULL + asyncio)
              20 LOAD_ATTR            (get_running_loop)
              40 CALL                 0
              48 STORE_DEREF          (loop)

370:          50 LOAD_CONST           (('pct', 'int'))
              52 LOAD_CLOSURE         (loop)
              54 LOAD_CLOSURE         (self)
              56 BUILD_TUPLE          2
              58 LOAD_CONST           (<Code311 code object _progress at 0x2e1d01e1480, file src\updater.py>, line 370)
              60 MAKE_FUNCTION        (annotation, closure)
              62 STORE_FAST           (_progress)

374:          64 NOP

375:          66 LOAD_GLOBAL          (NULL + asyncio)
              76 LOAD_ATTR            (to_thread)

376:          96 LOAD_GLOBAL          (_download_installer)

377:         106 LOAD_FAST            (url)

378:         108 LOAD_FAST            (filename)

379:         110 LOAD_FAST            (_progress)

380:         112 LOAD_CLOSURE         (self)
             114 BUILD_TUPLE          1
             116 LOAD_CONST           (<Code311 code object <lambda> at 0x2e1d01e1590, file src\updater.py>, line 380)
             118 MAKE_FUNCTION        (closure)

375:         120 CALL                 5
             128 GET_AWAITABLE        0
             130 LOAD_CONST           (None)
             132 SEND                 (to 140)
             136 YIELD_VALUE          4
             138 RESUME               3
         >>  140 JUMP_BACKWARD_NO_INTERRUPT (to 132)
             142 END_SEND
             144 STORE_FAST           (path)

382:         146 LOAD_FAST            (path)
             148 LOAD_DEREF           (self)
             150 STORE_ATTR           (installer_path)

383:         160 LOAD_CONST           (100)
             162 LOAD_DEREF           (self)
             164 STORE_ATTR           (progress)

384:         174 LOAD_CONST           ("ready")
             176 LOAD_DEREF           (self)
             178 STORE_ATTR           (phase)

385:         188 LOAD_CONST           ("Tải xuống hoàn tất. Sẵn sàng cài đặt.")
             190 LOAD_DEREF           (self)
             192 STORE_ATTR           (status_text)

392:         202 LOAD_DEREF           (self)
             204 LOAD_ATTR            (NULL|self + _bump)
             224 CALL                 0
             232 POP_TOP
             234 RETURN_CONST         (None)

375:         236 CLEANUP_THROW
             238 JUMP_BACKWARD        (to 142)
             240 PUSH_EXC_INFO

386:         242 LOAD_GLOBAL          (Exception)
             252 CHECK_EXC_MATCH
             254 POP_JUMP_IF_FALSE    (to 390)
             256 STORE_FAST           (exc)

387:         258 LOAD_CONST           ("error")
             260 LOAD_DEREF           (self)
             262 STORE_ATTR           (phase)

388:         272 LOAD_GLOBAL          (NULL + str)
             282 LOAD_FAST            (exc)
             284 CALL                 1
             292 LOAD_DEREF           (self)
             294 STORE_ATTR           (error)

389:         304 LOAD_CONST           ("Tải xuống thất bại: ")
             306 LOAD_FAST            (exc)
             308 FORMAT_VALUE         0
             310 BUILD_STRING         2
             312 LOAD_DEREF           (self)
             314 STORE_ATTR           (status_text)

390:         324 LOAD_GLOBAL          (NULL + logger)
             334 LOAD_ATTR            (error)
             354 LOAD_CONST           ("Update download failed: ")
             356 LOAD_FAST            (exc)
             358 FORMAT_VALUE         0
             360 BUILD_STRING         2
             362 CALL                 1
             370 POP_TOP
             372 POP_EXCEPT
             374 LOAD_CONST           (None)
             376 STORE_FAST           (exc)
             378 DELETE_FAST          (exc)
             380 JUMP_BACKWARD        (to 202)
             382 LOAD_CONST           (None)
             384 STORE_FAST           (exc)
             386 DELETE_FAST          (exc)
             388 RERAISE              1

386:     >>  390 RERAISE              0
             392 COPY                 3
             394 POP_EXCEPT
             396 RERAISE              1
             398 PUSH_EXC_INFO

392:         400 LOAD_DEREF           (self)
             402 LOAD_ATTR            (NULL|self + _bump)
             422 CALL                 0
             430 POP_TOP
             432 RERAISE              0
             434 COPY                 3
             436 POP_EXCEPT
             438 RERAISE              1
             440 CALL_INTRINSIC_1     3
             442 RERAISE              1

ExceptionTable:
  8 to 62 -> 440 [0] lasti
  66 to 134 -> 240 [0]
  136 to 136 -> 236 [2]
  138 to 200 -> 240 [0]
  202 to 234 -> 440 [0] lasti
  236 to 236 -> 240 [0]
  240 to 256 -> 392 [1] lasti
  258 to 370 -> 382 [1] lasti
  372 to 380 -> 398 [0]
  382 to 390 -> 392 [1] lasti
  392 to 396 -> 398 [0]
  398 to 432 -> 434 [1] lasti
  434 to 438 -> 440 [0] lasti

# Method Name:       _set_progress
# Filename:          src\updater.py
# Argument count:    2
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  2
# Stack size:        2
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        394
# Constants:
#    0: None
# Names:
#    0: progress
# Varnames:
#	self, pct
# Positional arguments:
#	self, pct

394:           0 RESUME               0

398:           2 LOAD_FAST            (pct)
               4 LOAD_FAST            (self)
               6 STORE_ATTR           (progress)
              16 RETURN_CONST         (None)


# Method Name:       cancel_download
# Filename:          src\updater.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  1
# Stack size:        2
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        400
# Constants:
#    0: None
#    1: 'downloading'
#    2: True
#    3: 'Đang hủy tải xuống...'
# Names:
#    0: phase
#    1: _stop_download
#    2: status_text
#    3: _bump
# Varnames:
#	self
# Positional arguments:
#	self

400:           0 RESUME               0

401:           2 LOAD_FAST            (self)
               4 LOAD_ATTR            (phase)
              24 LOAD_CONST           ("downloading")
              26 COMPARE_OP           (==)
              30 POP_JUMP_IF_FALSE    (to 94)

402:          32 LOAD_CONST           (True)
              34 LOAD_FAST            (self)
              36 STORE_ATTR           (_stop_download)

403:          46 LOAD_CONST           ("Đang hủy tải xuống...")
              48 LOAD_FAST            (self)
              50 STORE_ATTR           (status_text)

404:          60 LOAD_FAST            (self)
              62 LOAD_ATTR            (NULL|self + _bump)
              82 CALL                 0
              90 POP_TOP
              92 RETURN_CONST         (None)

401:     >>   94 RETURN_CONST         (None)


# Method Name:       install_update
# Filename:          src\updater.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  4
# Stack size:        5
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        407
# Constants:
#    0: 'Launch the downloaded installer. Returns (ok, message).\n\n        On success the caller should close the app so the installer can replace\n        the running files.\n        '
#    1: ''
#    2: (False, 'File cài đặt không tồn tại')
#    3: 'Windows'
#    4: 'Darwin'
#    5: 'open'
#    6: 'xdg-open'
#    7: 493
#    8: (True, 'Đang mở trình cài đặt...')
#    9: 'Install launch failed: '
#   10: False
#   11: 'Cài đặt thất bại: '
#   12: None
# Names:
#    0: str
#    1: installer_path
#    2: strip
#    3: os
#    4: path
#    5: exists
#    6: platform
#    7: system
#    8: startfile
#    9: subprocess
#   10: Popen
#   11: Exception
#   12: chmod
#   13: logger
#   14: error
# Varnames:
#	self, path, system, exc
# Positional arguments:
#	self
# Local variables:
#    1: path
#    2: system
#    3: exc

407:           0 RESUME               0

413:           2 LOAD_GLOBAL          (NULL + str)
              12 LOAD_FAST            (self)
              14 LOAD_ATTR            (installer_path)
              34 COPY                 1
              36 POP_JUMP_IF_TRUE     (to 42)
              38 POP_TOP
              40 LOAD_CONST           ("")
         >>   42 CALL                 1
              50 LOAD_ATTR            (NULL|self + strip)
              70 CALL                 0
              78 STORE_FAST           (path)

414:          80 LOAD_FAST            (path)
              82 POP_JUMP_IF_FALSE    (to 146)
              84 LOAD_GLOBAL          (os)
              94 LOAD_ATTR            (path)
             114 LOAD_ATTR            (NULL|self + exists)
             134 LOAD_FAST            (path)
             136 CALL                 1
             144 POP_JUMP_IF_TRUE     (to 148)

415:     >>  146 RETURN_CONST         ((False, 'File cài đặt không tồn tại'))

416:     >>  148 NOP

417:         150 LOAD_GLOBAL          (NULL + platform)
             160 LOAD_ATTR            (system)
             180 CALL                 0
             188 STORE_FAST           (system)

418:         190 LOAD_FAST            (system)
             192 LOAD_CONST           ("Windows")
             194 COMPARE_OP           (==)
             198 POP_JUMP_IF_FALSE    (to 244)

419:         200 LOAD_GLOBAL          (NULL + os)
             210 LOAD_ATTR            (startfile)
             230 LOAD_FAST            (path)
             232 CALL                 1
             240 POP_TOP

428:         242 RETURN_CONST         ((True, 'Đang mở trình cài đặt...'))

420:     >>  244 LOAD_FAST            (system)
             246 LOAD_CONST           ("Darwin")
             248 COMPARE_OP           (==)
             252 POP_JUMP_IF_FALSE    (to 302)

421:         254 LOAD_GLOBAL          (NULL + subprocess)
             264 LOAD_ATTR            (Popen)
             284 LOAD_CONST           ("open")
             286 LOAD_FAST            (path)
             288 BUILD_LIST           2
             290 CALL                 1
             298 POP_TOP

428:         300 RETURN_CONST         ((True, 'Đang mở trình cài đặt...'))

423:     >>  302 NOP

424:         304 LOAD_GLOBAL          (NULL + subprocess)
             314 LOAD_ATTR            (Popen)
             334 LOAD_CONST           ("xdg-open")
             336 LOAD_FAST            (path)
             338 BUILD_LIST           2
             340 CALL                 1
             348 POP_TOP

428:         350 RETURN_CONST         ((True, 'Đang mở trình cài đặt...'))
             352 PUSH_EXC_INFO

425:         354 LOAD_GLOBAL          (Exception)
             364 CHECK_EXC_MATCH
             366 POP_JUMP_IF_FALSE    (to 462)
             368 POP_TOP

426:         370 LOAD_GLOBAL          (NULL + os)
             380 LOAD_ATTR            (chmod)
             400 LOAD_FAST            (path)
             402 LOAD_CONST           (493)
             404 CALL                 2
             412 POP_TOP

427:         414 LOAD_GLOBAL          (NULL + subprocess)
             424 LOAD_ATTR            (Popen)
             444 LOAD_FAST            (path)
             446 BUILD_LIST           1
             448 CALL                 1
             456 POP_TOP
             458 POP_EXCEPT

428:         460 RETURN_CONST         ((True, 'Đang mở trình cài đặt...'))

425:     >>  462 RERAISE              0
             464 COPY                 3
             466 POP_EXCEPT
             468 RERAISE              1
             470 PUSH_EXC_INFO

429:         472 LOAD_GLOBAL          (Exception)
             482 CHECK_EXC_MATCH
             484 POP_JUMP_IF_FALSE    (to 568)
             486 STORE_FAST           (exc)

430:         488 LOAD_GLOBAL          (NULL + logger)
             498 LOAD_ATTR            (error)
             518 LOAD_CONST           ("Install launch failed: ")
             520 LOAD_FAST            (exc)
             522 FORMAT_VALUE         0
             524 BUILD_STRING         2
             526 CALL                 1
             534 POP_TOP

431:         536 LOAD_CONST           (False)
             538 LOAD_CONST           ("Cài đặt thất bại: ")
             540 LOAD_FAST            (exc)
             542 FORMAT_VALUE         0
             544 BUILD_STRING         2
             546 BUILD_TUPLE          2
             548 SWAP                 (TOS <-> TOS1)
             550 POP_EXCEPT
             552 LOAD_CONST           (None)
             554 STORE_FAST           (exc)
             556 DELETE_FAST          (exc)
             558 RETURN_VALUE
             560 LOAD_CONST           (None)
             562 STORE_FAST           (exc)
             564 DELETE_FAST          (exc)
             566 RERAISE              1

429:     >>  568 RERAISE              0
             570 COPY                 3
             572 POP_EXCEPT
             574 RERAISE              1

ExceptionTable:
  150 to 240 -> 470 [0]
  244 to 298 -> 470 [0]
  304 to 348 -> 352 [0]
  352 to 456 -> 464 [1] lasti
  458 to 458 -> 470 [0]
  462 to 462 -> 464 [1] lasti
  464 to 468 -> 470 [0]
  470 to 486 -> 570 [1] lasti
  488 to 546 -> 560 [1] lasti
  548 to 548 -> 570 [1] lasti
  560 to 568 -> 570 [1] lasti

# Method Name:       _progress
# Filename:          src\updater.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  1
# Stack size:        4
# Flags:             0x01000013 (0x1000000 | NESTED | NEWLOCALS | OPTIMIZED)
# First Line:        370
# Constants:
#    0: None
# Names:
#    0: call_soon_threadsafe
#    1: _set_progress
# Varnames:
#	pct
# Positional arguments:
#	pct
# Free variables:
#    0: loop
#    1: self
               0 COPY_FREE_VARS       2

370:           2 RESUME               0

372:           4 LOAD_DEREF           (loop)
               6 LOAD_ATTR            (NULL|self + call_soon_threadsafe)
              26 LOAD_DEREF           (self)
              28 LOAD_ATTR            (_set_progress)
              48 LOAD_FAST            (pct)
              50 CALL                 2
              58 POP_TOP
              60 RETURN_CONST         (None)


# Method Name:       <lambda>
# Filename:          src\updater.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        1
# Flags:             0x01000013 (0x1000000 | NESTED | NEWLOCALS | OPTIMIZED)
# First Line:        380
# Constants:
#    0: None
# Names:
#    0: _stop_download
# Free variables:
#    0: self
               0 COPY_FREE_VARS       1

380:           2 RESUME               0
               4 LOAD_DEREF           (self)
               6 LOAD_ATTR            (_stop_download)
              26 RETURN_VALUE

```
