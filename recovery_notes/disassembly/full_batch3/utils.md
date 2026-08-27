# Static CPython 3.12 disassembly — `utils.pyc`

Generated with `xdis 6.3.0`; the code object was deserialized but never executed.

```text
# pydisasm version 6.3.0
# CPython Python bytecode 3.12.0 (3531)
#   Disassembled from CPython Python 3.13.13 | packaged by Anaconda, Inc. | (main, Apr 14 2026, 06:12:50) [MSC v.1942 64 bit (AMD64)]
# Timestamp in code: 0 (1970-01-01 07:00:00)
# Source code size mod 2**32: 0 bytes
# Method Name:       <module>
# Filename:          src\utils.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        15
# Flags:             0x00000000 (0x0)
# First Line:        1
# Constants:
#    0: 0
#    1: None
#    2: ('Path',)
#    3: ('logger',)
#    4: ('webdriver',)
#    5: ('Service',)
#    6: ('ChromeDriverManager',)
#    7: ('ChannelInfo',)
#    8: <Code311 code object get_video_duration at 0x2e1d01e1e10, file src\utils.py>, line 18
#    9: <Code311 code object calculate_total_seconds at 0x2e1d01e1d00, file src\utils.py>, line 54
#   10: 'input_file'
#   11: 'output_file'
#   12: 'times'
#   13: 'return'
#   14: <Code311 code object multiply_audio at 0x2e1d01e1f20, file src\utils.py>, line 76
#   15: frozenset({'.flv', '.mkv', '.mov', '.mp4', '.m4v', '.avi', '.webm'})
#   16: frozenset({'.flac', '.mp3', '.m4a', '.ogg', '.wav', '.aac', '.opus'})
#   17: 'folder'
#   18: 'extensions'
#   19: <Code311 code object list_media_files at 0x2e1d01e2140, file src\utils.py>, line 151
#   20: 'music_file'
#   21: 'audio_out'
#   22: 'play_sec'
#   23: 'mute_sec'
#   24: <Code311 code object build_intermittent_audio at 0x2e1d01e2250, file src\utils.py>, line 164
#   25: 'video_file'
#   26: 'audio_file'
#   27: 'video_out'
#   28: 'duration'
#   29: 'video_bitrate'
#   30: 'overlay_png'
#   31: <Code311 code object mux_audio_into_video at 0x2e1d01e2470, file src\utils.py>, line 222
#   32: 'channel_id'
#   33: <Code311 code object get_channels_info at 0x2e1d01e2580, file src\utils.py>, line 332
#   34: False
#   35: ('start_offscreen',)
#   36: 'enable_performance_log'
#   37: 'start_offscreen'
#   38: <Code311 code object create_driver at 0x2e1d01e27a0, file src\utils.py>, line 390
#   39: 'path_text'
#   40: <Code311 code object normalize_path at 0x2e1d01e29c0, file src\utils.py>, line 418
#   41: <Code311 code object validate_path_text at 0x2e1d01e2ad0, file src\utils.py>, line 425
#   42: 'url_substring'
#   43: 'timeout'
#   44: 'poll_interval'
#   45: <Code311 code object get_request_payload_from_performance_log at 0x2e1d01e2be0, file src\utils.py>, line 445
#   46: (0, None)
#   47: (3.0, 7.0)
#   48: (None, '1M', None)
#   49: (None,)
#   50: (False,)
#   51: (15.0, 0.5)
# Names:
#    0: json
#    1: math
#    2: re
#    3: subprocess
#    4: tempfile
#    5: time
#    6: unicodedata
#    7: pathlib
#    8: Path
#    9: loguru
#   10: logger
#   11: selenium
#   12: webdriver
#   13: selenium.webdriver.chrome.service
#   14: Service
#   15: webdriver_manager.chrome
#   16: ChromeDriverManager
#   17: src.module.model
#   18: ChannelInfo
#   19: get_video_duration
#   20: calculate_total_seconds
#   21: str
#   22: int
#   23: multiply_audio
#   24: VIDEO_EXTENSIONS
#   25: AUDIO_EXTENSIONS
#   26: set
#   27: list
#   28: list_media_files
#   29: float
#   30: build_intermittent_audio
#   31: mux_audio_into_video
#   32: get_channels_info
#   33: bool
#   34: create_driver
#   35: normalize_path
#   36: tuple
#   37: validate_path_text
#   38: get_request_payload_from_performance_log

  0:           0 RESUME               0

  1:           2 LOAD_CONST           (0)
               4 LOAD_CONST           (None)
               6 IMPORT_NAME          (json)
               8 STORE_NAME           (json)

  2:          10 LOAD_CONST           (0)
              12 LOAD_CONST           (None)
              14 IMPORT_NAME          (math)
              16 STORE_NAME           (math)

  3:          18 LOAD_CONST           (0)
              20 LOAD_CONST           (None)
              22 IMPORT_NAME          (re)
              24 STORE_NAME           (re)

  4:          26 LOAD_CONST           (0)
              28 LOAD_CONST           (None)
              30 IMPORT_NAME          (subprocess)
              32 STORE_NAME           (subprocess)

  5:          34 LOAD_CONST           (0)
              36 LOAD_CONST           (None)
              38 IMPORT_NAME          (tempfile)
              40 STORE_NAME           (tempfile)

  6:          42 LOAD_CONST           (0)
              44 LOAD_CONST           (None)
              46 IMPORT_NAME          (time)
              48 STORE_NAME           (time)

  7:          50 LOAD_CONST           (0)
              52 LOAD_CONST           (None)
              54 IMPORT_NAME          (unicodedata)
              56 STORE_NAME           (unicodedata)

  8:          58 LOAD_CONST           (0)
              60 LOAD_CONST           (('Path',))
              62 IMPORT_NAME          (pathlib)
              64 IMPORT_FROM          (Path)
              66 STORE_NAME           (Path)
              68 POP_TOP

 10:          70 LOAD_CONST           (0)
              72 LOAD_CONST           (('logger',))
              74 IMPORT_NAME          (loguru)
              76 IMPORT_FROM          (logger)
              78 STORE_NAME           (logger)
              80 POP_TOP

 11:          82 LOAD_CONST           (0)
              84 LOAD_CONST           (('webdriver',))
              86 IMPORT_NAME          (selenium)
              88 IMPORT_FROM          (webdriver)
              90 STORE_NAME           (webdriver)
              92 POP_TOP

 12:          94 LOAD_CONST           (0)
              96 LOAD_CONST           (('Service',))
              98 IMPORT_NAME          (selenium.webdriver.chrome.service)
             100 IMPORT_FROM          (Service)
             102 STORE_NAME           (Service)
             104 POP_TOP

 13:         106 LOAD_CONST           (0)
             108 LOAD_CONST           (('ChromeDriverManager',))
             110 IMPORT_NAME          (webdriver_manager.chrome)
             112 IMPORT_FROM          (ChromeDriverManager)
             114 STORE_NAME           (ChromeDriverManager)
             116 POP_TOP

 15:         118 LOAD_CONST           (0)
             120 LOAD_CONST           (('ChannelInfo',))
             122 IMPORT_NAME          (src.module.model)
             124 IMPORT_FROM          (ChannelInfo)
             126 STORE_NAME           (ChannelInfo)
             128 POP_TOP

 18:         130 LOAD_CONST           (<Code311 code object get_video_duration at 0x2e1d01e1e10, file src\utils.py>, line 18)
             132 MAKE_FUNCTION        (No arguments)
             134 STORE_NAME           (get_video_duration)

 54:         136 LOAD_CONST           (<Code311 code object calculate_total_seconds at 0x2e1d01e1d00, file src\utils.py>, line 54)
             138 MAKE_FUNCTION        (No arguments)
             140 STORE_NAME           (calculate_total_seconds)

 80:         142 NOP

 81:         144 NOP

 76:         146 LOAD_CONST           ((0, None))
             148 LOAD_CONST           ("input_file")

 77:         150 LOAD_NAME            (str)

 76:         152 LOAD_CONST           ("output_file")

 78:         154 LOAD_NAME            (str)

 76:         156 LOAD_CONST           ("times")

 79:         158 LOAD_NAME            (int)

 76:         160 LOAD_CONST           ("return")

 82:         162 LOAD_CONST           (None)

 76:         164 BUILD_TUPLE          8
             166 LOAD_CONST           (<Code311 code object multiply_audio at 0x2e1d01e1f20, file src\utils.py>, line 76)
             168 MAKE_FUNCTION        (default, annotation)
             170 STORE_NAME           (multiply_audio)

147:         172 BUILD_SET            0
             174 LOAD_CONST           (frozenset({'.flv', '.mkv', '.mov', '.mp4', '.m4v', '.avi', '.webm'}))
             176 SET_UPDATE           1
             178 STORE_NAME           (VIDEO_EXTENSIONS)

148:         180 BUILD_SET            0
             182 LOAD_CONST           (frozenset({'.flac', '.mp3', '.m4a', '.ogg', '.wav', '.aac', '.opus'}))
             184 SET_UPDATE           1
             186 STORE_NAME           (AUDIO_EXTENSIONS)

151:         188 LOAD_CONST           ("folder")
             190 LOAD_NAME            (str)
             192 LOAD_CONST           ("extensions")
             194 LOAD_NAME            (set)
             196 LOAD_NAME            (str)
             198 BINARY_SUBSCR
             202 LOAD_CONST           ("return")
             204 LOAD_NAME            (list)
             206 LOAD_NAME            (Path)
             208 BINARY_SUBSCR
             212 BUILD_TUPLE          6
             214 LOAD_CONST           (<Code311 code object list_media_files at 0x2e1d01e2140, file src\utils.py>, line 151)
             216 MAKE_FUNCTION        (annotation)
             218 STORE_NAME           (list_media_files)

167:         220 NOP

168:         222 NOP

164:         224 LOAD_CONST           ((3.0, 7.0))
             226 LOAD_CONST           ("music_file")

165:         228 LOAD_NAME            (str)

164:         230 LOAD_CONST           ("audio_out")

166:         232 LOAD_NAME            (str)

164:         234 LOAD_CONST           ("play_sec")

167:         236 LOAD_NAME            (float)

164:         238 LOAD_CONST           ("mute_sec")

168:         240 LOAD_NAME            (float)

164:         242 LOAD_CONST           ("return")

169:         244 LOAD_NAME            (float)

164:         246 BUILD_TUPLE          10
             248 LOAD_CONST           (<Code311 code object build_intermittent_audio at 0x2e1d01e2250, file src\utils.py>, line 164)
             250 MAKE_FUNCTION        (default, annotation)
             252 STORE_NAME           (build_intermittent_audio)

226:         254 NOP

227:         256 NOP

228:         258 NOP

222:         260 LOAD_CONST           ((None, '1M', None))
             262 LOAD_CONST           ("video_file")

223:         264 LOAD_NAME            (str)

222:         266 LOAD_CONST           ("audio_file")

224:         268 LOAD_NAME            (str)

222:         270 LOAD_CONST           ("video_out")

225:         272 LOAD_NAME            (str)

222:         274 LOAD_CONST           ("duration")

226:         276 LOAD_NAME            (float)
             278 LOAD_CONST           (None)
             280 BINARY_OP            (|)

222:         284 LOAD_CONST           ("video_bitrate")

227:         286 LOAD_NAME            (str)

222:         288 LOAD_CONST           ("overlay_png")

228:         290 LOAD_NAME            (str)
             292 LOAD_CONST           (None)
             294 BINARY_OP            (|)

222:         298 LOAD_CONST           ("return")

229:         300 LOAD_CONST           (None)

222:         302 BUILD_TUPLE          14
             304 LOAD_CONST           (<Code311 code object mux_audio_into_video at 0x2e1d01e2470, file src\utils.py>, line 222)
             306 MAKE_FUNCTION        (default, annotation)
             308 STORE_NAME           (mux_audio_into_video)

333:         310 NOP

332:         312 LOAD_CONST           ((None,))
             314 LOAD_CONST           ("channel_id")

333:         316 LOAD_NAME            (str)
             318 LOAD_CONST           (None)
             320 BINARY_OP            (|)

332:         324 LOAD_CONST           ("return")

334:         326 LOAD_NAME            (list)
             328 LOAD_NAME            (ChannelInfo)
             330 BINARY_SUBSCR
             334 LOAD_NAME            (ChannelInfo)
             336 BINARY_OP            (|)
             340 LOAD_CONST           (None)
             342 BINARY_OP            (|)

332:         346 BUILD_TUPLE          4
             348 LOAD_CONST           (<Code311 code object get_channels_info at 0x2e1d01e2580, file src\utils.py>, line 332)
             350 MAKE_FUNCTION        (default, annotation)
             352 STORE_NAME           (get_channels_info)

391:         354 NOP

390:         356 LOAD_CONST           ((False,))

393:         358 LOAD_CONST           (False)

390:         360 LOAD_CONST           (('start_offscreen',))
             362 BUILD_CONST_KEY_MAP  1
             364 LOAD_CONST           ("enable_performance_log")

391:         366 LOAD_NAME            (bool)

390:         368 LOAD_CONST           ("start_offscreen")

393:         370 LOAD_NAME            (bool)

390:         372 BUILD_TUPLE          4
             374 LOAD_CONST           (<Code311 code object create_driver at 0x2e1d01e27a0, file src\utils.py>, line 390)
             376 MAKE_FUNCTION        (default, keyword-only, annotation)
             378 STORE_NAME           (create_driver)

418:         380 LOAD_CONST           ("path_text")
             382 LOAD_NAME            (str)
             384 LOAD_CONST           ("return")
             386 LOAD_NAME            (str)
             388 BUILD_TUPLE          4
             390 LOAD_CONST           (<Code311 code object normalize_path at 0x2e1d01e29c0, file src\utils.py>, line 418)
             392 MAKE_FUNCTION        (annotation)
             394 STORE_NAME           (normalize_path)

425:         396 LOAD_CONST           ("path_text")
             398 LOAD_NAME            (str)
             400 LOAD_CONST           ("return")
             402 LOAD_NAME            (tuple)
             404 LOAD_NAME            (bool)
             406 LOAD_NAME            (str)
             408 LOAD_CONST           (None)
             410 BINARY_OP            (|)
             414 BUILD_TUPLE          2
             416 BINARY_SUBSCR
             420 BUILD_TUPLE          4
             422 LOAD_CONST           (<Code311 code object validate_path_text at 0x2e1d01e2ad0, file src\utils.py>, line 425)
             424 MAKE_FUNCTION        (annotation)
             426 STORE_NAME           (validate_path_text)

446:         428 NOP

445:         430 LOAD_CONST           ((15.0, 0.5))
             432 LOAD_CONST           ("url_substring")

446:         434 LOAD_NAME            (str)

445:         436 LOAD_CONST           ("timeout")

446:         438 LOAD_NAME            (float)

445:         440 LOAD_CONST           ("poll_interval")

446:         442 LOAD_NAME            (float)

445:         444 BUILD_TUPLE          6
             446 LOAD_CONST           (<Code311 code object get_request_payload_from_performance_log at 0x2e1d01e2be0, file src\utils.py>, line 445)
             448 MAKE_FUNCTION        (default, annotation)
             450 STORE_NAME           (get_request_payload_from_performance_log)
             452 RETURN_CONST         (None)


# Method Name:       get_video_duration
# Filename:          src\utils.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  6
# Stack size:        8
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        18
# Constants:
#    0: 'Get duration of video file in seconds using ffprobe'
#    1: 'ffprobe'
#    2: '-v'
#    3: 'error'
#    4: '-show_entries'
#    5: 'format=duration'
#    6: '-of'
#    7: 'json'
#    8: ('stderr',)
#    9: 'utf-8'
#   10: 'format'
#   11: 'duration'
#   12: 0
#   13: 'Invalid duration for '
#   14: ': '
#   15: None
#   16: 'FFprobe not found. Please install FFmpeg to use video processing features.'
#   17: 'FFprobe failed for '
#   18: 'Failed to parse FFprobe output for '
#   19: 'Unexpected error getting duration for '
# Names:
#    0: subprocess
#    1: check_output
#    2: DEVNULL
#    3: decode
#    4: json
#    5: loads
#    6: float
#    7: logger
#    8: warning
#    9: FileNotFoundError
#   10: error
#   11: CalledProcessError
#   12: JSONDecodeError
#   13: KeyError
#   14: ValueError
#   15: Exception
# Varnames:
#	input_file, cmd, result, data, duration, e
# Positional arguments:
#	input_file
# Local variables:
#    1: cmd
#    2: result
#    3: data
#    4: duration
#    5: e

 18:           0 RESUME               0

 20:           2 NOP

 22:           4 LOAD_CONST           ("ffprobe")

 23:           6 LOAD_CONST           ("-v")

 24:           8 LOAD_CONST           ("error")

 25:          10 LOAD_CONST           ("-show_entries")

 26:          12 LOAD_CONST           ("format=duration")

 27:          14 LOAD_CONST           ("-of")

 28:          16 LOAD_CONST           ("json")

 29:          18 LOAD_FAST            (input_file)

 21:          20 BUILD_LIST           8
              22 STORE_FAST           (cmd)

 31:          24 LOAD_GLOBAL          (NULL + subprocess)
              34 LOAD_ATTR            (check_output)
              54 LOAD_FAST            (cmd)
              56 LOAD_GLOBAL          (subprocess)
              66 LOAD_ATTR            (DEVNULL)
              86 KW_NAMES             (('stderr',))
              88 CALL                 2
              96 LOAD_ATTR            (NULL|self + decode)
             116 LOAD_CONST           ("utf-8")
             118 CALL                 1
             126 STORE_FAST           (result)

 32:         128 LOAD_GLOBAL          (NULL + json)
             138 LOAD_ATTR            (loads)
             158 LOAD_FAST            (result)
             160 CALL                 1
             168 STORE_FAST           (data)

 33:         170 LOAD_GLOBAL          (NULL + float)
             180 LOAD_FAST            (data)
             182 LOAD_CONST           ("format")
             184 BINARY_SUBSCR
             188 LOAD_CONST           ("duration")
             190 BINARY_SUBSCR
             194 CALL                 1
             202 STORE_FAST           (duration)

 34:         204 LOAD_FAST            (duration)
             206 LOAD_CONST           (0)
             208 COMPARE_OP           (<=)
             212 POP_JUMP_IF_FALSE    (to 270)

 35:         214 LOAD_GLOBAL          (NULL + logger)
             224 LOAD_ATTR            (warning)
             244 LOAD_CONST           ("Invalid duration for ")
             246 LOAD_FAST            (input_file)
             248 FORMAT_VALUE         0
             250 LOAD_CONST           (": ")
             252 LOAD_FAST            (duration)
             254 FORMAT_VALUE         0
             256 BUILD_STRING         4
             258 CALL                 1
             266 POP_TOP

 36:         268 RETURN_CONST         (None)

 37:     >>  270 LOAD_FAST            (duration)
             272 RETURN_VALUE
             274 PUSH_EXC_INFO

 38:         276 LOAD_GLOBAL          (FileNotFoundError)
             286 CHECK_EXC_MATCH
             288 POP_JUMP_IF_FALSE    (to 338)
             290 POP_TOP

 39:         292 LOAD_GLOBAL          (NULL + logger)
             302 LOAD_ATTR            (error)

 40:         322 LOAD_CONST           ("FFprobe not found. Please install FFmpeg to use video processing features.")

 39:         324 CALL                 1
             332 POP_TOP

 42:         334 POP_EXCEPT
             336 RETURN_CONST         (None)

 43:     >>  338 LOAD_GLOBAL          (subprocess)
             348 LOAD_ATTR            (CalledProcessError)
             368 CHECK_EXC_MATCH
             370 POP_JUMP_IF_FALSE    (to 446)
             372 STORE_FAST           (e)

 44:         374 LOAD_GLOBAL          (NULL + logger)
             384 LOAD_ATTR            (error)
             404 LOAD_CONST           ("FFprobe failed for ")
             406 LOAD_FAST            (input_file)
             408 FORMAT_VALUE         0
             410 LOAD_CONST           (": ")
             412 LOAD_FAST            (e)
             414 FORMAT_VALUE         0
             416 BUILD_STRING         4
             418 CALL                 1
             426 POP_TOP

 45:         428 POP_EXCEPT
             430 LOAD_CONST           (None)
             432 STORE_FAST           (e)
             434 DELETE_FAST          (e)
             436 RETURN_CONST         (None)
             438 LOAD_CONST           (None)
             440 STORE_FAST           (e)
             442 DELETE_FAST          (e)
             444 RERAISE              1

 46:     >>  446 LOAD_GLOBAL          (json)
             456 LOAD_ATTR            (JSONDecodeError)
             476 LOAD_GLOBAL          (KeyError)
             486 LOAD_GLOBAL          (ValueError)
             496 BUILD_TUPLE          3
             498 CHECK_EXC_MATCH
             500 POP_JUMP_IF_FALSE    (to 576)
             502 STORE_FAST           (e)

 47:         504 LOAD_GLOBAL          (NULL + logger)
             514 LOAD_ATTR            (error)
             534 LOAD_CONST           ("Failed to parse FFprobe output for ")
             536 LOAD_FAST            (input_file)
             538 FORMAT_VALUE         0
             540 LOAD_CONST           (": ")
             542 LOAD_FAST            (e)
             544 FORMAT_VALUE         0
             546 BUILD_STRING         4
             548 CALL                 1
             556 POP_TOP

 48:         558 POP_EXCEPT
             560 LOAD_CONST           (None)
             562 STORE_FAST           (e)
             564 DELETE_FAST          (e)
             566 RETURN_CONST         (None)
             568 LOAD_CONST           (None)
             570 STORE_FAST           (e)
             572 DELETE_FAST          (e)
             574 RERAISE              1

 49:     >>  576 LOAD_GLOBAL          (Exception)
             586 CHECK_EXC_MATCH
             588 POP_JUMP_IF_FALSE    (to 664)
             590 STORE_FAST           (e)

 50:         592 LOAD_GLOBAL          (NULL + logger)
             602 LOAD_ATTR            (error)
             622 LOAD_CONST           ("Unexpected error getting duration for ")
             624 LOAD_FAST            (input_file)
             626 FORMAT_VALUE         0
             628 LOAD_CONST           (": ")
             630 LOAD_FAST            (e)
             632 FORMAT_VALUE         0
             634 BUILD_STRING         4
             636 CALL                 1
             644 POP_TOP

 51:         646 POP_EXCEPT
             648 LOAD_CONST           (None)
             650 STORE_FAST           (e)
             652 DELETE_FAST          (e)
             654 RETURN_CONST         (None)
             656 LOAD_CONST           (None)
             658 STORE_FAST           (e)
             660 DELETE_FAST          (e)
             662 RERAISE              1

 49:     >>  664 RERAISE              0
             666 COPY                 3
             668 POP_EXCEPT
             670 RERAISE              1

ExceptionTable:
  4 to 266 -> 274 [0]
  270 to 270 -> 274 [0]
  274 to 332 -> 666 [1] lasti
  338 to 372 -> 666 [1] lasti
  374 to 426 -> 438 [1] lasti
  438 to 502 -> 666 [1] lasti
  504 to 556 -> 568 [1] lasti
  568 to 590 -> 666 [1] lasti
  592 to 644 -> 656 [1] lasti
  656 to 664 -> 666 [1] lasti

# Method Name:       calculate_total_seconds
# Filename:          src\utils.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  7
# Stack size:        5
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        54
# Constants:
#    0: None
#    1: 'Video chưa được public!!!'
#    2: 0
#    3: 'P(?:T(?:(\\d+)H)?(?:(\\d+)M)?(?:(\\d+)S)?)'
#    4: 'Invalid ISO 8601 duration format'
#    5: 1
#    6: 2
#    7: 3
#    8: 3600
#    9: 60
# Names:
#    0: logger
#    1: error
#    2: re
#    3: compile
#    4: match
#    5: group
#    6: int
# Varnames:
#	iso_duration, pattern, match, hours, minutes, seconds, total_seconds
# Positional arguments:
#	iso_duration
# Local variables:
#    1: pattern
#    2: match
#    3: hours
#    4: minutes
#    5: seconds
#    6: total_seconds

 54:           0 RESUME               0

 55:           2 LOAD_FAST            (iso_duration)
               4 POP_JUMP_IF_TRUE     (to 50)

 56:           6 LOAD_GLOBAL          (NULL + logger)
              16 LOAD_ATTR            (error)
              36 LOAD_CONST           ("Video chưa được public!!!")
              38 CALL                 1
              46 POP_TOP

 57:          48 RETURN_CONST         (0)

 59:     >>   50 LOAD_GLOBAL          (NULL + re)
              60 LOAD_ATTR            (compile)
              80 LOAD_CONST           ("P(?:T(?:(\\d+)H)?(?:(\\d+)M)?(?:(\\d+)S)?)")
              82 CALL                 1
              90 STORE_FAST           (pattern)

 60:          92 LOAD_FAST            (pattern)
              94 LOAD_ATTR            (NULL|self + match)
             114 LOAD_FAST            (iso_duration)
             116 CALL                 1
             124 STORE_FAST           (match)

 62:         126 LOAD_FAST            (match)
             128 POP_JUMP_IF_TRUE     (to 132)

 63:         130 RETURN_CONST         ("Invalid ISO 8601 duration format")

 66:     >>  132 LOAD_FAST            (match)
             134 LOAD_ATTR            (NULL|self + group)
             154 LOAD_CONST           (1)
             156 CALL                 1
             164 POP_JUMP_IF_FALSE    (to 218)
             166 LOAD_GLOBAL          (NULL + int)
             176 LOAD_FAST            (match)
             178 LOAD_ATTR            (NULL|self + group)
             198 LOAD_CONST           (1)
             200 CALL                 1
             208 CALL                 1
             216 JUMP_FORWARD         (to 220)
         >>  218 LOAD_CONST           (0)
         >>  220 STORE_FAST           (hours)

 67:         222 LOAD_FAST            (match)
             224 LOAD_ATTR            (NULL|self + group)
             244 LOAD_CONST           (2)
             246 CALL                 1
             254 POP_JUMP_IF_FALSE    (to 308)
             256 LOAD_GLOBAL          (NULL + int)
             266 LOAD_FAST            (match)
             268 LOAD_ATTR            (NULL|self + group)
             288 LOAD_CONST           (2)
             290 CALL                 1
             298 CALL                 1
             306 JUMP_FORWARD         (to 310)
         >>  308 LOAD_CONST           (0)
         >>  310 STORE_FAST           (minutes)

 68:         312 LOAD_FAST            (match)
             314 LOAD_ATTR            (NULL|self + group)
             334 LOAD_CONST           (3)
             336 CALL                 1
             344 POP_JUMP_IF_FALSE    (to 398)
             346 LOAD_GLOBAL          (NULL + int)
             356 LOAD_FAST            (match)
             358 LOAD_ATTR            (NULL|self + group)
             378 LOAD_CONST           (3)
             380 CALL                 1
             388 CALL                 1
             396 JUMP_FORWARD         (to 400)
         >>  398 LOAD_CONST           (0)
         >>  400 STORE_FAST           (seconds)

 71:         402 LOAD_FAST            (hours)
             404 LOAD_CONST           (3600)
             406 BINARY_OP            (*)
             410 LOAD_FAST            (minutes)
             412 LOAD_CONST           (60)
             414 BINARY_OP            (*)
             418 BINARY_OP            (+)
             422 LOAD_FAST            (seconds)
             424 BINARY_OP            (+)
             428 STORE_FAST           (total_seconds)

 73:         430 LOAD_FAST            (total_seconds)
             432 RETURN_VALUE


# Method Name:       multiply_audio
# Filename:          src\utils.py
# Argument count:    5
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  15
# Stack size:        12
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        76
# Constants:
#    0: '\n    Super-fast version: no filters, no temp files.\n    - Computes total target duration.\n    - Uses -stream_loop to repeat input and -t to trim exactly.\n    - Tries stream copy first; on failure, re-encodes audio.\n    - If video_duration_seconds is provided, trims the final audio to match video duration.\n    '
#    1: 1
#    2: 'Times must be >= 1'
#    3: 0
#    4: 'Extra minutes must be >= 0'
#    5: 'Input duration is zero or could not be read.'
#    6: 60
#    7: None
#    8: 'ffmpeg'
#    9: '-v'
#   10: 'quiet'
#   11: '-stats'
#   12: '-y'
#   13: '-stream_loop'
#   14: '-i'
#   15: '-t'
#   16: '.6f'
#   17: '-c'
#   18: 'copy'
#   19: True
#   20: ('check',)
#   21: '-c:a'
#   22: 'libmp3lame'
#   23: '-q:a'
#   24: '2'
# Names:
#    0: ValueError
#    1: get_video_duration
#    2: RuntimeError
#    3: math
#    4: ceil
#    5: max
#    6: str
#    7: subprocess
#    8: run
#    9: CalledProcessError
# Varnames:
#	input_file, output_file, times, extra_minutes, video_duration_seconds, src, dst, dur, extra_seconds, total_seconds, needed_copies, stream_loop, base_cmd, cmd_copy, cmd_reencode
# Positional arguments:
#	input_file, output_file, times, extra_minutes, video_duration_seconds
# Local variables:
#    5: src
#    6: dst
#    7: dur
#    8: extra_seconds
#    9: total_seconds
#   10: needed_copies
#   11: stream_loop
#   12: base_cmd
#   13: cmd_copy
#   14: cmd_reencode

 76:           0 RESUME               0

 90:           2 LOAD_FAST            (times)
               4 LOAD_CONST           (1)
               6 COMPARE_OP           (<)
              10 POP_JUMP_IF_FALSE    (to 34)

 91:          12 LOAD_GLOBAL          (NULL + ValueError)
              22 LOAD_CONST           ("Times must be >= 1")
              24 CALL                 1
              32 RAISE_VARARGS        (exception instance)

 92:     >>   34 LOAD_FAST            (extra_minutes)
              36 LOAD_CONST           (0)
              38 COMPARE_OP           (<)
              42 POP_JUMP_IF_FALSE    (to 66)

 93:          44 LOAD_GLOBAL          (NULL + ValueError)
              54 LOAD_CONST           ("Extra minutes must be >= 0")
              56 CALL                 1
              64 RAISE_VARARGS        (exception instance)

 96:     >>   66 LOAD_FAST            (input_file)
              68 STORE_FAST           (src)

 97:          70 LOAD_FAST            (output_file)
              72 STORE_FAST           (dst)

100:          74 LOAD_GLOBAL          (NULL + get_video_duration)
              84 LOAD_FAST            (src)
              86 CALL                 1
              94 STORE_FAST           (dur)

101:          96 LOAD_FAST            (dur)
              98 LOAD_CONST           (0)
             100 COMPARE_OP           (<=)
             104 POP_JUMP_IF_FALSE    (to 128)

102:         106 LOAD_GLOBAL          (NULL + RuntimeError)
             116 LOAD_CONST           ("Input duration is zero or could not be read.")
             118 CALL                 1
             126 RAISE_VARARGS        (exception instance)

107:     >>  128 LOAD_FAST            (extra_minutes)
             130 LOAD_CONST           (60)
             132 BINARY_OP            (*)
             136 STORE_FAST           (extra_seconds)

108:         138 LOAD_FAST            (video_duration_seconds)
             140 POP_JUMP_IF_NONE     (to 158)
             142 LOAD_FAST            (video_duration_seconds)
             144 LOAD_CONST           (0)
             146 COMPARE_OP           (>)
             150 POP_JUMP_IF_FALSE    (to 158)

109:         152 LOAD_FAST            (video_duration_seconds)
             154 STORE_FAST           (total_seconds)
             156 JUMP_FORWARD         (to 174)

111:     >>  158 LOAD_FAST            (times)
             160 LOAD_FAST            (dur)
             162 LOAD_FAST            (extra_seconds)
             164 BINARY_OP            (+)
             168 BINARY_OP            (*)
             172 STORE_FAST           (total_seconds)

115:     >>  174 LOAD_GLOBAL          (NULL + math)
             184 LOAD_ATTR            (ceil)
             204 LOAD_FAST            (total_seconds)
             206 LOAD_FAST            (dur)
             208 BINARY_OP            (/)
             212 CALL                 1
             220 STORE_FAST           (needed_copies)

116:         222 LOAD_GLOBAL          (NULL + max)
             232 LOAD_CONST           (0)
             234 LOAD_FAST            (needed_copies)
             236 LOAD_CONST           (1)
             238 BINARY_OP            (-)
             242 CALL                 2
             250 STORE_FAST           (stream_loop)

120:         252 LOAD_CONST           ("ffmpeg")

121:         254 LOAD_CONST           ("-v")

122:         256 LOAD_CONST           ("quiet")

123:         258 LOAD_CONST           ("-stats")

124:         260 LOAD_CONST           ("-y")

125:         262 LOAD_CONST           ("-stream_loop")

126:         264 LOAD_GLOBAL          (NULL + str)
             274 LOAD_FAST            (stream_loop)
             276 CALL                 1

127:         284 LOAD_CONST           ("-i")

128:         286 LOAD_FAST            (src)

129:         288 LOAD_CONST           ("-t")

130:         290 LOAD_FAST            (total_seconds)
             292 LOAD_CONST           (".6f")
             294 FORMAT_VALUE         4

119:         296 BUILD_LIST           11
             298 STORE_FAST           (base_cmd)

134:         300 NOP

135:         302 LOAD_FAST            (base_cmd)
             304 LOAD_CONST           ("-c")
             306 LOAD_CONST           ("copy")
             308 LOAD_FAST            (dst)
             310 BUILD_LIST           3
             312 BINARY_OP            (+)
             316 STORE_FAST           (cmd_copy)

136:         318 LOAD_GLOBAL          (NULL + subprocess)
             328 LOAD_ATTR            (run)
             348 LOAD_FAST            (cmd_copy)
             350 LOAD_CONST           (True)
             352 KW_NAMES             (('check',))
             354 CALL                 2
             362 POP_TOP

137:         364 RETURN_CONST         (None)
             366 PUSH_EXC_INFO

138:         368 LOAD_GLOBAL          (subprocess)
             378 LOAD_ATTR            (CalledProcessError)
             398 CHECK_EXC_MATCH
             400 POP_JUMP_IF_FALSE    (to 408)
             402 POP_TOP

139:         404 POP_EXCEPT
             406 JUMP_FORWARD         (to 416)

138:     >>  408 RERAISE              0
             410 COPY                 3
             412 POP_EXCEPT
             414 RERAISE              1

143:     >>  416 LOAD_FAST            (base_cmd)
             418 LOAD_CONST           ("-c:a")
             420 LOAD_CONST           ("libmp3lame")
             422 LOAD_CONST           ("-q:a")
             424 LOAD_CONST           ("2")
             426 LOAD_FAST            (dst)
             428 BUILD_LIST           5
             430 BINARY_OP            (+)
             434 STORE_FAST           (cmd_reencode)

144:         436 LOAD_GLOBAL          (NULL + subprocess)
             446 LOAD_ATTR            (run)
             466 LOAD_FAST            (cmd_reencode)
             468 LOAD_CONST           (True)
             470 KW_NAMES             (('check',))
             472 CALL                 2
             480 POP_TOP
             482 RETURN_CONST         (None)

ExceptionTable:
  302 to 362 -> 366 [0]
  366 to 402 -> 410 [1] lasti
  408 to 408 -> 410 [1] lasti

# Method Name:       list_media_files
# Filename:          src\utils.py
# Argument count:    2
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  5
# Stack size:        5
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        151
# Constants:
#    0: 'Return sorted media files (by name) directly inside `folder`.'
#    1: <Code311 code object <lambda> at 0x2e1d01e2030, file src\utils.py>, line 161
#    2: ('key',)
# Names:
#    0: Path
#    1: normalize_path
#    2: exists
#    3: is_dir
#    4: iterdir
#    5: is_file
#    6: suffix
#    7: lower
#    8: sorted
# Varnames:
#	folder, extensions, folder_path, p, files
# Positional arguments:
#	folder, extensions
# Local variables:
#    2: folder_path
#    3: p
#    4: files

151:           0 RESUME               0

153:           2 LOAD_GLOBAL          (NULL + Path)
              12 LOAD_GLOBAL          (NULL + normalize_path)
              22 LOAD_FAST            (folder)
              24 CALL                 1
              32 CALL                 1
              40 STORE_FAST           (folder_path)

154:          42 LOAD_FAST            (folder_path)
              44 LOAD_ATTR            (NULL|self + exists)
              64 CALL                 0
              72 POP_JUMP_IF_FALSE    (to 106)
              74 LOAD_FAST            (folder_path)
              76 LOAD_ATTR            (NULL|self + is_dir)
              96 CALL                 0
             104 POP_JUMP_IF_TRUE     (to 110)

155:     >>  106 BUILD_LIST           0
             108 RETURN_VALUE

158:     >>  110 LOAD_FAST            (folder_path)
             112 LOAD_ATTR            (NULL|self + iterdir)
             132 CALL                 0
             140 GET_ITER

156:         142 LOAD_FAST_AND_CLEAR  (p)
             144 SWAP                 (TOS <-> TOS1)
             146 BUILD_LIST           0
             148 SWAP                 (TOS <-> TOS1)

158:         150 FOR_ITER             (to 250)
             154 STORE_FAST           (p)

159:         156 LOAD_FAST            (p)
             158 LOAD_ATTR            (NULL|self + is_file)
             178 CALL                 0
             186 POP_JUMP_IF_FALSE    (to 248)
             188 LOAD_FAST            (p)
             190 LOAD_ATTR            (suffix)
             210 LOAD_ATTR            (NULL|self + lower)
             230 CALL                 0
             238 LOAD_FAST            (extensions)
             240 CONTAINS_OP          (in)
             242 POP_JUMP_IF_FALSE    (to 248)

157:         244 LOAD_FAST            (p)
             246 LIST_APPEND          2
         >>  248 JUMP_BACKWARD        (to 150)

158:         250 END_FOR

156:         252 STORE_FAST           (files)
             254 STORE_FAST           (p)

161:         256 LOAD_GLOBAL          (NULL + sorted)
             266 LOAD_FAST            (files)
             268 LOAD_CONST           (<Code311 code object <lambda> at 0x2e1d01e2030, file src\utils.py>, line 161)
             270 MAKE_FUNCTION        (No arguments)
             272 KW_NAMES             (('key',))
             274 CALL                 2
             282 RETURN_VALUE
             284 SWAP                 (TOS <-> TOS1)
             286 POP_TOP

156:         288 SWAP                 (TOS <-> TOS1)
             290 STORE_FAST           (p)
             292 RERAISE              0

ExceptionTable:
  146 to 250 -> 284 [2]

# Method Name:       build_intermittent_audio
# Filename:          src\utils.py
# Argument count:    4
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  10
# Stack size:        20
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        164
# Constants:
#    0: '\n    Build a gated (intermittent) audio track spanning the whole music length.\n\n    The music is audible for `play_sec` seconds, silent for `mute_sec` seconds,\n    repeating for the whole music length; the final `play_sec` seconds are\n    always audible.\n\n    Returns the music duration in seconds (dùng làm thời lượng đích khi mux —\n    video gốc sẽ được loop cho bằng thời lượng này).\n    '
#    1: 0
#    2: 'Could not read music duration: '
#    3: 0.0
#    4: 'if(lt(mod(t,'
#    5: '),'
#    6: '),1,if(gte(t,'
#    7: '),1,0))'
#    8: "[0:a]volume=volume='"
#    9: "':eval=frame[aud]"
#   10: 'ffmpeg'
#   11: '-v'
#   12: 'quiet'
#   13: '-stats'
#   14: '-y'
#   15: '-stream_loop'
#   16: '-1'
#   17: '-i'
#   18: '-filter_complex'
#   19: '-map'
#   20: '[aud]'
#   21: '-t'
#   22: '.6f'
#   23: '-c:a'
#   24: 'aac'
#   25: '-b:a'
#   26: '192k'
#   27: True
#   28: ('check',)
# Names:
#    0: get_video_duration
#    1: RuntimeError
#    2: max
#    3: subprocess
#    4: run
# Varnames:
#	music_file, audio_out, play_sec, mute_sec, dur, cycle, tail_start, volume_expr, filter_complex, cmd
# Positional arguments:
#	music_file, audio_out, play_sec, mute_sec
# Local variables:
#    4: dur
#    5: cycle
#    6: tail_start
#    7: volume_expr
#    8: filter_complex
#    9: cmd

164:           0 RESUME               0

180:           2 LOAD_GLOBAL          (NULL + get_video_duration)
              12 LOAD_FAST            (music_file)
              14 CALL                 1
              22 STORE_FAST           (dur)

181:          24 LOAD_FAST            (dur)
              26 POP_JUMP_IF_FALSE    (to 38)
              28 LOAD_FAST            (dur)
              30 LOAD_CONST           (0)
              32 COMPARE_OP           (<=)
              36 POP_JUMP_IF_FALSE    (to 66)

182:     >>   38 LOAD_GLOBAL          (NULL + RuntimeError)
              48 LOAD_CONST           ("Could not read music duration: ")
              50 LOAD_FAST            (music_file)
              52 FORMAT_VALUE         0
              54 BUILD_STRING         2
              56 CALL                 1
              64 RAISE_VARARGS        (exception instance)

184:     >>   66 LOAD_FAST            (play_sec)
              68 LOAD_FAST            (mute_sec)
              70 BINARY_OP            (+)
              74 STORE_FAST           (cycle)

185:          76 LOAD_GLOBAL          (NULL + max)
              86 LOAD_CONST           (0.0)
              88 LOAD_FAST            (dur)
              90 LOAD_FAST            (play_sec)
              92 BINARY_OP            (-)
              96 CALL                 2
             104 STORE_FAST           (tail_start)

191:         106 LOAD_CONST           ("if(lt(mod(t,")
             108 LOAD_FAST            (cycle)
             110 FORMAT_VALUE         0
             112 LOAD_CONST           ("),")
             114 LOAD_FAST            (play_sec)
             116 FORMAT_VALUE         0
             118 LOAD_CONST           ("),1,if(gte(t,")

192:         120 LOAD_FAST            (tail_start)
             122 FORMAT_VALUE         0
             124 LOAD_CONST           ("),1,0))")

191:         126 BUILD_STRING         7

190:         128 STORE_FAST           (volume_expr)

194:         130 LOAD_CONST           ("[0:a]volume=volume='")
             132 LOAD_FAST            (volume_expr)
             134 FORMAT_VALUE         0
             136 LOAD_CONST           ("':eval=frame[aud]")
             138 BUILD_STRING         3
             140 STORE_FAST           (filter_complex)

197:         142 LOAD_CONST           ("ffmpeg")

198:         144 LOAD_CONST           ("-v")

199:         146 LOAD_CONST           ("quiet")

200:         148 LOAD_CONST           ("-stats")

201:         150 LOAD_CONST           ("-y")

202:         152 LOAD_CONST           ("-stream_loop")

203:         154 LOAD_CONST           ("-1")

204:         156 LOAD_CONST           ("-i")

205:         158 LOAD_FAST            (music_file)

206:         160 LOAD_CONST           ("-filter_complex")

207:         162 LOAD_FAST            (filter_complex)

208:         164 LOAD_CONST           ("-map")

209:         166 LOAD_CONST           ("[aud]")

210:         168 LOAD_CONST           ("-t")

211:         170 LOAD_FAST            (dur)
             172 LOAD_CONST           (".6f")
             174 FORMAT_VALUE         4

212:         176 LOAD_CONST           ("-c:a")

213:         178 LOAD_CONST           ("aac")

214:         180 LOAD_CONST           ("-b:a")

215:         182 LOAD_CONST           ("192k")

216:         184 LOAD_FAST            (audio_out)

196:         186 BUILD_LIST           20
             188 STORE_FAST           (cmd)

218:         190 LOAD_GLOBAL          (NULL + subprocess)
             200 LOAD_ATTR            (run)
             220 LOAD_FAST            (cmd)
             222 LOAD_CONST           (True)
             224 KW_NAMES             (('check',))
             226 CALL                 2
             234 POP_TOP

219:         236 LOAD_FAST            (dur)
             238 RETURN_VALUE


# Method Name:       mux_audio_into_video
# Filename:          src\utils.py
# Argument count:    6
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  13
# Stack size:        18
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        222
# Constants:
#    0: '\n    Nén clip gốc 1 lần rồi loop cho bằng `duration` và ghép `audio_file`.\n\n    Vì clip gốc được lặp lại để phủ 2-3 tiếng, dung lượng file (do đó thời gian\n    upload) tỉ lệ với bitrate của clip. Ở đây clip ngắn được nén xuống\n    `video_bitrate` (giữ nguyên độ phân giải) MỘT lần — rất nhanh vì clip ngắn —\n    sau đó loop-copy nên file dài 2-3 tiếng vẫn nhỏ và tạo nhanh.\n\n    Audio thay thế hoàn toàn tiếng gốc.\n    '
#    1: 0
#    2: 'Could not determine target duration for '
#    3: '.mp4'
#    4: False
#    5: ('suffix', 'delete')
#    6: None
#    7: 'ffmpeg'
#    8: '-v'
#    9: 'quiet'
#   10: '-stats'
#   11: '-y'
#   12: '-i'
#   13: '-loop'
#   14: '1'
#   15: ('-filter_complex', '[1:v][0:v]scale2ref[ovl][base];[base][ovl]overlay=0:0[outv]', '-map', '[outv]', '-shortest')
#   16: '-an'
#   17: '-c:v'
#   18: 'libx264'
#   19: '-preset'
#   20: 'veryfast'
#   21: '-b:v'
#   22: '-maxrate'
#   23: '1400k'
#   24: '-bufsize'
#   25: '2M'
#   26: '-pix_fmt'
#   27: 'yuv420p'
#   28: True
#   29: ('check',)
#   30: '-stream_loop'
#   31: '-1'
#   32: '-map'
#   33: '0:v:0'
#   34: '1:a:0'
#   35: '-t'
#   36: '.6f'
#   37: 'copy'
#   38: '-c:a'
#   39: 'Không xóa được clip tạm '
#   40: ': '
#   41: 'aac'
#   42: '-b:a'
#   43: '192k'
# Names:
#    0: get_video_duration
#    1: RuntimeError
#    2: bool
#    3: Path
#    4: normalize_path
#    5: is_file
#    6: tempfile
#    7: NamedTemporaryFile
#    8: name
#    9: subprocess
#   10: run
#   11: exists
#   12: unlink
#   13: Exception
#   14: logger
#   15: warning
#   16: CalledProcessError
# Varnames:
#	video_file, audio_file, video_out, duration, video_bitrate, overlay_png, dur, use_overlay, tf, compressed_clip, compress_cmd, base_cmd, exc
# Positional arguments:
#	video_file, audio_file, video_out, duration, video_bitrate, overlay_png
# Local variables:
#    6: dur
#    7: use_overlay
#    8: tf
#    9: compressed_clip
#   10: compress_cmd
#   11: base_cmd
#   12: exc

222:           0 RESUME               0

240:           2 LOAD_FAST            (duration)
               4 COPY                 1
               6 POP_JUMP_IF_TRUE     (to 30)
               8 POP_TOP
              10 LOAD_GLOBAL          (NULL + get_video_duration)
              20 LOAD_FAST            (audio_file)
              22 CALL                 1
         >>   30 STORE_FAST           (dur)

241:          32 LOAD_FAST            (dur)
              34 POP_JUMP_IF_FALSE    (to 46)
              36 LOAD_FAST            (dur)
              38 LOAD_CONST           (0)
              40 COMPARE_OP           (<=)
              44 POP_JUMP_IF_FALSE    (to 74)

242:     >>   46 LOAD_GLOBAL          (NULL + RuntimeError)
              56 LOAD_CONST           ("Could not determine target duration for ")
              58 LOAD_FAST            (video_file)
              60 FORMAT_VALUE         0
              62 BUILD_STRING         2
              64 CALL                 1
              72 RAISE_VARARGS        (exception instance)

244:     >>   74 LOAD_GLOBAL          (NULL + bool)
              84 LOAD_FAST            (overlay_png)
              86 COPY                 1
              88 POP_JUMP_IF_FALSE    (to 158)
              90 POP_TOP
              92 LOAD_GLOBAL          (NULL + Path)
             102 LOAD_GLOBAL          (NULL + normalize_path)
             112 LOAD_FAST            (overlay_png)
             114 CALL                 1
             122 CALL                 1
             130 LOAD_ATTR            (NULL|self + is_file)
             150 CALL                 0
         >>  158 CALL                 1
             166 STORE_FAST           (use_overlay)

248:         168 LOAD_GLOBAL          (NULL + tempfile)
             178 LOAD_ATTR            (NamedTemporaryFile)
             198 LOAD_CONST           (".mp4")
             200 LOAD_CONST           (False)
             202 KW_NAMES             (('suffix', 'delete'))
             204 CALL                 2
             212 BEFORE_WITH
             214 STORE_FAST           (tf)

249:         216 LOAD_FAST            (tf)
             218 LOAD_ATTR            (name)
             238 STORE_FAST           (compressed_clip)

248:         240 LOAD_CONST           (None)
             242 LOAD_CONST           (None)
             244 LOAD_CONST           (None)
             246 CALL                 2
             254 POP_TOP

250:         256 NOP

251:         258 LOAD_CONST           ("ffmpeg")
             260 LOAD_CONST           ("-v")
             262 LOAD_CONST           ("quiet")
             264 LOAD_CONST           ("-stats")
             266 LOAD_CONST           ("-y")
             268 LOAD_CONST           ("-i")
             270 LOAD_FAST            (video_file)
             272 BUILD_LIST           7
             274 STORE_FAST           (compress_cmd)

252:         276 LOAD_FAST            (use_overlay)
             278 POP_JUMP_IF_FALSE    (to 330)

254:         280 LOAD_FAST            (compress_cmd)
             282 LOAD_CONST           ("-loop")
             284 LOAD_CONST           ("1")
             286 LOAD_CONST           ("-i")
             288 LOAD_GLOBAL          (NULL + normalize_path)
             298 LOAD_FAST            (overlay_png)
             300 CALL                 1
             308 BUILD_LIST           4
             310 BINARY_OP            (+=)
             314 STORE_FAST           (compress_cmd)

256:         316 LOAD_FAST            (compress_cmd)
             318 BUILD_LIST           0
             320 LOAD_CONST           (('-filter_complex', '[1:v][0:v]scale2ref[ovl][base];[base][ovl]overlay=0:0[outv]', '-map', '[outv]', '-shortest'))
             322 LIST_EXTEND          1
             324 BINARY_OP            (+=)
             328 STORE_FAST           (compress_cmd)

263:     >>  330 LOAD_FAST            (compress_cmd)

264:         332 LOAD_CONST           ("-an")

265:         334 LOAD_CONST           ("-c:v")

266:         336 LOAD_CONST           ("libx264")

267:         338 LOAD_CONST           ("-preset")

268:         340 LOAD_CONST           ("veryfast")

269:         342 LOAD_CONST           ("-b:v")

270:         344 LOAD_FAST            (video_bitrate)

271:         346 LOAD_CONST           ("-maxrate")

272:         348 LOAD_CONST           ("1400k")

273:         350 LOAD_CONST           ("-bufsize")

274:         352 LOAD_CONST           ("2M")

275:         354 LOAD_CONST           ("-pix_fmt")

276:         356 LOAD_CONST           ("yuv420p")

277:         358 LOAD_FAST_CHECK      (compressed_clip)

263:         360 BUILD_LIST           14
             362 BINARY_OP            (+=)
             366 STORE_FAST           (compress_cmd)

279:         368 LOAD_GLOBAL          (NULL + subprocess)
             378 LOAD_ATTR            (run)
             398 LOAD_FAST            (compress_cmd)
             400 LOAD_CONST           (True)
             402 KW_NAMES             (('check',))
             404 CALL                 2
             412 POP_TOP

283:         414 LOAD_CONST           ("ffmpeg")

284:         416 LOAD_CONST           ("-v")

285:         418 LOAD_CONST           ("quiet")

286:         420 LOAD_CONST           ("-stats")

287:         422 LOAD_CONST           ("-y")

288:         424 LOAD_CONST           ("-stream_loop")

289:         426 LOAD_CONST           ("-1")

290:         428 LOAD_CONST           ("-i")

291:         430 LOAD_FAST            (compressed_clip)

292:         432 LOAD_CONST           ("-i")

293:         434 LOAD_FAST            (audio_file)

294:         436 LOAD_CONST           ("-map")

295:         438 LOAD_CONST           ("0:v:0")

296:         440 LOAD_CONST           ("-map")

297:         442 LOAD_CONST           ("1:a:0")

298:         444 LOAD_CONST           ("-t")

299:         446 LOAD_FAST            (dur)
             448 LOAD_CONST           (".6f")
             450 FORMAT_VALUE         4

282:         452 BUILD_LIST           17
             454 STORE_FAST           (base_cmd)

301:         456 NOP

302:         458 LOAD_GLOBAL          (NULL + subprocess)
             468 LOAD_ATTR            (run)

303:         488 LOAD_FAST            (base_cmd)
             490 LOAD_CONST           ("-c:v")
             492 LOAD_CONST           ("copy")
             494 LOAD_CONST           ("-c:a")
             496 LOAD_CONST           ("copy")
             498 LOAD_FAST            (video_out)
             500 BUILD_LIST           5
             502 BINARY_OP            (+)
             506 LOAD_CONST           (True)

302:         508 KW_NAMES             (('check',))
             510 CALL                 2
             518 POP_TOP

305:         520 NOP

325:         522 NOP

326:         524 LOAD_GLOBAL          (NULL + Path)
             534 LOAD_FAST            (compressed_clip)
             536 CALL                 1
             544 LOAD_ATTR            (NULL|self + exists)
             564 CALL                 0
             572 POP_JUMP_IF_FALSE    (to 626)

327:         574 LOAD_GLOBAL          (NULL + Path)
             584 LOAD_FAST            (compressed_clip)
             586 CALL                 1
             594 LOAD_ATTR            (NULL|self + unlink)
             614 CALL                 0
             622 POP_TOP
             624 RETURN_CONST         (None)

326:     >>  626 RETURN_CONST         (None)

248:         628 PUSH_EXC_INFO
             630 WITH_EXCEPT_START
             632 POP_JUMP_IF_TRUE     (to 636)
             634 RERAISE              2
         >>  636 POP_TOP
             638 POP_EXCEPT
             640 POP_TOP
             642 POP_TOP
             644 JUMP_BACKWARD        (to 256)
             646 COPY                 3
             648 POP_EXCEPT
             650 RERAISE              1
             652 PUSH_EXC_INFO

328:         654 LOAD_GLOBAL          (Exception)
             664 CHECK_EXC_MATCH
             666 POP_JUMP_IF_FALSE    (to 742)
             668 STORE_FAST           (exc)

329:         670 LOAD_GLOBAL          (NULL + logger)
             680 LOAD_ATTR            (warning)
             700 LOAD_CONST           ("Không xóa được clip tạm ")
             702 LOAD_FAST            (compressed_clip)
             704 FORMAT_VALUE         0
             706 LOAD_CONST           (": ")
             708 LOAD_FAST            (exc)
             710 FORMAT_VALUE         0
             712 BUILD_STRING         4
             714 CALL                 1
             722 POP_TOP
             724 POP_EXCEPT
             726 LOAD_CONST           (None)
             728 STORE_FAST           (exc)
             730 DELETE_FAST          (exc)
             732 RETURN_CONST         (None)
             734 LOAD_CONST           (None)
             736 STORE_FAST           (exc)
             738 DELETE_FAST          (exc)
             740 RERAISE              1

328:     >>  742 RERAISE              0
             744 COPY                 3
             746 POP_EXCEPT
             748 RERAISE              1
             750 PUSH_EXC_INFO

306:         752 LOAD_GLOBAL          (subprocess)
             762 LOAD_ATTR            (CalledProcessError)
             782 CHECK_EXC_MATCH
             784 POP_JUMP_IF_FALSE    (to 792)
             786 POP_TOP

307:         788 POP_EXCEPT
             790 JUMP_FORWARD         (to 800)

306:     >>  792 RERAISE              0
             794 COPY                 3
             796 POP_EXCEPT
             798 RERAISE              1

309:     >>  800 LOAD_GLOBAL          (NULL + subprocess)
             810 LOAD_ATTR            (run)

310:         830 LOAD_FAST            (base_cmd)

312:         832 LOAD_CONST           ("-c:v")

313:         834 LOAD_CONST           ("libx264")

314:         836 LOAD_CONST           ("-preset")

315:         838 LOAD_CONST           ("veryfast")

316:         840 LOAD_CONST           ("-c:a")

317:         842 LOAD_CONST           ("aac")

318:         844 LOAD_CONST           ("-b:a")

319:         846 LOAD_CONST           ("192k")

320:         848 LOAD_FAST            (video_out)

311:         850 BUILD_LIST           9

310:         852 BINARY_OP            (+)

322:         856 LOAD_CONST           (True)

309:         858 KW_NAMES             (('check',))
             860 CALL                 2
             868 POP_TOP

325:         870 NOP

326:         872 LOAD_GLOBAL          (NULL + Path)
             882 LOAD_FAST            (compressed_clip)
             884 CALL                 1
             892 LOAD_ATTR            (NULL|self + exists)
             912 CALL                 0
             920 POP_JUMP_IF_FALSE    (to 974)

327:         922 LOAD_GLOBAL          (NULL + Path)
             932 LOAD_FAST            (compressed_clip)
             934 CALL                 1
             942 LOAD_ATTR            (NULL|self + unlink)
             962 CALL                 0
             970 POP_TOP
             972 RETURN_CONST         (None)

326:     >>  974 RETURN_CONST         (None)
             976 PUSH_EXC_INFO

328:         978 LOAD_GLOBAL          (Exception)
             988 CHECK_EXC_MATCH
             990 POP_JUMP_IF_FALSE    (to 1066)
             992 STORE_FAST           (exc)

329:         994 LOAD_GLOBAL          (NULL + logger)
            1004 LOAD_ATTR            (warning)
            1024 LOAD_CONST           ("Không xóa được clip tạm ")
            1026 LOAD_FAST            (compressed_clip)
            1028 FORMAT_VALUE         0
            1030 LOAD_CONST           (": ")
            1032 LOAD_FAST            (exc)
            1034 FORMAT_VALUE         0
         >> 1036 BUILD_STRING         4
            1038 CALL                 1
            1046 POP_TOP
            1048 POP_EXCEPT
            1050 LOAD_CONST           (None)
            1052 STORE_FAST           (exc)
            1054 DELETE_FAST          (exc)
            1056 RETURN_CONST         (None)
            1058 LOAD_CONST           (None)
            1060 STORE_FAST           (exc)
            1062 DELETE_FAST          (exc)
            1064 RERAISE              1

328:     >> 1066 RERAISE              0
            1068 COPY                 3
            1070 POP_EXCEPT
            1072 RERAISE              1
            1074 PUSH_EXC_INFO

325:        1076 NOP

326:        1078 LOAD_GLOBAL          (NULL + Path)
            1088 LOAD_FAST_CHECK      (compressed_clip)
            1090 CALL                 1
            1098 LOAD_ATTR            (NULL|self + exists)
            1118 CALL                 0
            1126 POP_JUMP_IF_FALSE    (to 1180)

327:        1128 LOAD_GLOBAL          (NULL + Path)
            1138 LOAD_FAST            (compressed_clip)
            1140 CALL                 1
            1148 LOAD_ATTR            (NULL|self + unlink)
            1168 CALL                 0
            1176 POP_TOP
            1178 RERAISE              0

326:     >> 1180 RERAISE              0
            1182 PUSH_EXC_INFO

328:        1184 LOAD_GLOBAL          (Exception)
            1194 CHECK_EXC_MATCH
            1196 POP_JUMP_IF_FALSE    (to 1272)
            1198 STORE_FAST           (exc)

329:        1200 LOAD_GLOBAL          (NULL + logger)
            1210 LOAD_ATTR            (warning)
            1230 LOAD_CONST           ("Không xóa được clip tạm ")
            1232 LOAD_FAST_CHECK      (compressed_clip)
            1234 FORMAT_VALUE         0
            1236 LOAD_CONST           (": ")
            1238 LOAD_FAST            (exc)
            1240 FORMAT_VALUE         0
            1242 BUILD_STRING         4
            1244 CALL                 1
            1252 POP_TOP
            1254 POP_EXCEPT
            1256 LOAD_CONST           (None)
            1258 STORE_FAST           (exc)
            1260 DELETE_FAST          (exc)
            1262 RERAISE              0
            1264 LOAD_CONST           (None)
            1266 STORE_FAST           (exc)
            1268 DELETE_FAST          (exc)
            1270 RERAISE              1

328:     >> 1272 RERAISE              0
            1274 COPY                 3
            1276 POP_EXCEPT
            1278 RERAISE              1
            1280 COPY                 3
            1282 POP_EXCEPT
            1284 RERAISE              1

ExceptionTable:
  214 to 238 -> 628 [1] lasti
  258 to 454 -> 1074 [0]
  458 to 518 -> 750 [0]
  524 to 622 -> 652 [0]
  628 to 636 -> 646 [3] lasti
  652 to 668 -> 744 [1] lasti
  670 to 722 -> 734 [1] lasti
  734 to 742 -> 744 [1] lasti
  750 to 786 -> 794 [1] lasti
  788 to 790 -> 1074 [0]
  792 to 792 -> 794 [1] lasti
  794 to 868 -> 1074 [0]
  872 to 970 -> 976 [0]
  976 to 992 -> 1068 [1] lasti
  994 to 1046 -> 1058 [1] lasti
  1058 to 1066 -> 1068 [1] lasti
  1074 to 1074 -> 1280 [1] lasti
  1078 to 1176 -> 1182 [2]
  1178 to 1180 -> 1280 [1] lasti
  1182 to 1198 -> 1274 [3] lasti
  1200 to 1252 -> 1264 [3] lasti
  1254 to 1262 -> 1280 [1] lasti
  1264 to 1272 -> 1274 [3] lasti
  1274 to 1278 -> 1280 [1] lasti

# Method Name:       get_channels_info
# Filename:          src\utils.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  6
# Stack size:        19
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        332
# Constants:
#    0: "\n    Retrieve channel info from SQLite database.\n\n    Args:\n        channel_id: Specific channel ID to fetch. If None, fetch all channels.\n\n    Returns:\n        - list[ChannelInfo]: when channel_id is None (may be empty)\n        - ChannelInfo: for a specific channel_id\n        - None: if the specific channel doesn't exist\n    "
#    1: 0
#    2: ('channel_store',)
#    3: "Channel ID '%s' not found in database"
#    4: None
#    5: 'id'
#    6: 'name'
#    7: ''
#    8: 'img_src'
#    9: 'sapisidhash'
#   10: 'delegated_session_id'
#   11: 'cookies'
#   12: 'cookies_expires_at'
#   13: 'role'
#   14: 'challenge'
#   15: 'botguardResponse'
#   16: 'overlay_png'
#   17: ('id', 'name', 'img_src', 'sapisidhash', 'delegated_session_id', 'cookies', 'cookies_expires_at', 'role', 'challenge', 'botguardResponse', 'overlay_png')
#   18: 'Total channels loaded: '
# Names:
#    0: src.channel_store
#    1: channel_store
#    2: init_db
#    3: get_channel
#    4: logger
#    5: error
#    6: ChannelInfo
#    7: get
#    8: list_channels
#    9: append
#   10: info
#   11: len
# Varnames:
#	channel_id, channel_store, rec, rows, channels, r
# Positional arguments:
#	channel_id
# Local variables:
#    1: channel_store
#    2: rec
#    3: rows
#    4: channels
#    5: r

332:           0 RESUME               0

346:           2 LOAD_CONST           (0)
               4 LOAD_CONST           (('channel_store',))
               6 IMPORT_NAME          (src.channel_store)
               8 IMPORT_FROM          (channel_store)
              10 STORE_FAST           (channel_store)
              12 POP_TOP

348:          14 LOAD_FAST            (channel_store)
              16 LOAD_ATTR            (NULL|self + init_db)
              36 CALL                 0
              44 POP_TOP

350:          46 LOAD_FAST            (channel_id)
              48 POP_JUMP_IF_FALSE    (to 502)

351:          50 LOAD_FAST            (channel_store)
              52 LOAD_ATTR            (NULL|self + get_channel)
              72 LOAD_FAST            (channel_id)
              74 CALL                 1
              82 STORE_FAST           (rec)

352:          84 LOAD_FAST            (rec)
              86 POP_JUMP_IF_TRUE     (to 134)

353:          88 LOAD_GLOBAL          (NULL + logger)
              98 LOAD_ATTR            (error)
             118 LOAD_CONST           ("Channel ID '%s' not found in database")
             120 LOAD_FAST            (channel_id)
             122 CALL                 2
             130 POP_TOP

354:         132 RETURN_CONST         (None)

355:     >>  134 LOAD_GLOBAL          (NULL + ChannelInfo)

356:         144 LOAD_FAST            (rec)
             146 LOAD_CONST           ("id")
             148 BINARY_SUBSCR

357:         152 LOAD_FAST            (rec)
             154 LOAD_ATTR            (NULL|self + get)
             174 LOAD_CONST           ("name")
             176 LOAD_CONST           ("")
             178 CALL                 2

358:         186 LOAD_FAST            (rec)
             188 LOAD_ATTR            (NULL|self + get)
             208 LOAD_CONST           ("img_src")
             210 LOAD_CONST           ("")
             212 CALL                 2

359:         220 LOAD_FAST            (rec)
             222 LOAD_ATTR            (NULL|self + get)
             242 LOAD_CONST           ("sapisidhash")
             244 LOAD_CONST           ("")
             246 CALL                 2

360:         254 LOAD_FAST            (rec)
             256 LOAD_ATTR            (NULL|self + get)
             276 LOAD_CONST           ("delegated_session_id")
             278 LOAD_CONST           ("")
             280 CALL                 2

361:         288 LOAD_FAST            (rec)
             290 LOAD_ATTR            (NULL|self + get)
             310 LOAD_CONST           ("cookies")
             312 BUILD_LIST           0
             314 CALL                 2

362:         322 LOAD_FAST            (rec)
             324 LOAD_ATTR            (NULL|self + get)
             344 LOAD_CONST           ("cookies_expires_at")
             346 CALL                 1

363:         354 LOAD_FAST            (rec)
             356 LOAD_ATTR            (NULL|self + get)
             376 LOAD_CONST           ("role")
             378 LOAD_CONST           ("")
             380 CALL                 2

364:         388 LOAD_FAST            (rec)
             390 LOAD_ATTR            (NULL|self + get)
             410 LOAD_CONST           ("challenge")
             412 LOAD_CONST           ("")
             414 CALL                 2

365:         422 LOAD_FAST            (rec)
             424 LOAD_ATTR            (NULL|self + get)
             444 LOAD_CONST           ("botguardResponse")
             446 LOAD_CONST           ("")
             448 CALL                 2

366:         456 LOAD_FAST            (rec)
             458 LOAD_ATTR            (NULL|self + get)
             478 LOAD_CONST           ("overlay_png")
             480 LOAD_CONST           ("")
             482 CALL                 2

355:         490 KW_NAMES             (('id', 'name', 'img_src', 'sapisidhash', 'delegated_session_id', 'cookies', 'cookies_expires_at', 'role', 'challenge', 'botguardResponse', 'overlay_png'))
             492 CALL                 11
             500 RETURN_VALUE

369:     >>  502 LOAD_FAST            (channel_store)
             504 LOAD_ATTR            (NULL|self + list_channels)
             524 CALL                 0
             532 STORE_FAST           (rows)

370:         534 BUILD_LIST           0
             536 STORE_FAST           (channels)

371:         538 LOAD_FAST            (rows)
             540 GET_ITER
             542 FOR_ITER             (to 984)
             546 STORE_FAST           (r)

372:         548 LOAD_FAST            (r)
             550 LOAD_ATTR            (NULL|self + get)
             570 LOAD_CONST           ("id")
             572 CALL                 1
             580 POP_JUMP_IF_TRUE     (to 584)
             582 JUMP_BACKWARD        (to 542)

373:     >>  584 LOAD_FAST            (channels)
             586 LOAD_ATTR            (NULL|self + append)
             606 LOAD_GLOBAL          (NULL + ChannelInfo)

374:         616 LOAD_FAST            (r)
             618 LOAD_CONST           ("id")
             620 BINARY_SUBSCR

375:         624 LOAD_FAST            (r)
         >>  626 LOAD_ATTR            (NULL|self + get)
             646 LOAD_CONST           ("name")
             648 LOAD_CONST           ("")
             650 CALL                 2

376:         658 LOAD_FAST            (r)
             660 LOAD_ATTR            (NULL|self + get)
             680 LOAD_CONST           ("img_src")
             682 LOAD_CONST           ("")
             684 CALL                 2

377:         692 LOAD_FAST            (r)
             694 LOAD_ATTR            (NULL|self + get)
             714 LOAD_CONST           ("sapisidhash")
             716 LOAD_CONST           ("")
             718 CALL                 2

378:         726 LOAD_FAST            (r)
             728 LOAD_ATTR            (NULL|self + get)
             748 LOAD_CONST           ("delegated_session_id")
             750 LOAD_CONST           ("")
             752 CALL                 2

379:         760 LOAD_FAST            (r)
             762 LOAD_ATTR            (NULL|self + get)
             782 LOAD_CONST           ("cookies")
             784 BUILD_LIST           0
             786 CALL                 2

380:         794 LOAD_FAST            (r)
             796 LOAD_ATTR            (NULL|self + get)
             816 LOAD_CONST           ("cookies_expires_at")
             818 CALL                 1

381:         826 LOAD_FAST            (r)
             828 LOAD_ATTR            (NULL|self + get)
             848 LOAD_CONST           ("role")
             850 LOAD_CONST           ("")
             852 CALL                 2

382:         860 LOAD_FAST            (r)
             862 LOAD_ATTR            (NULL|self + get)
             882 LOAD_CONST           ("challenge")
             884 LOAD_CONST           ("")
             886 CALL                 2

383:         894 LOAD_FAST            (r)
             896 LOAD_ATTR            (NULL|self + get)
             916 LOAD_CONST           ("botguardResponse")
             918 LOAD_CONST           ("")
             920 CALL                 2

384:         928 LOAD_FAST            (r)
             930 LOAD_ATTR            (NULL|self + get)
             950 LOAD_CONST           ("overlay_png")
             952 LOAD_CONST           ("")
             954 CALL                 2

373:         962 KW_NAMES             (('id', 'name', 'img_src', 'sapisidhash', 'delegated_session_id', 'cookies', 'cookies_expires_at', 'role', 'challenge', 'botguardResponse', 'overlay_png'))
             964 CALL                 11
             972 CALL                 1
             980 POP_TOP
         >>  982 JUMP_BACKWARD        (to 542)

371:         984 END_FOR

386:         986 LOAD_GLOBAL          (NULL + logger)
             996 LOAD_ATTR            (info)
            1016 LOAD_CONST           ("Total channels loaded: ")
            1018 LOAD_GLOBAL          (NULL + len)
            1028 LOAD_FAST            (channels)
            1030 CALL                 1
            1038 FORMAT_VALUE         0
            1040 BUILD_STRING         2
            1042 CALL                 1
            1050 POP_TOP

387:        1052 LOAD_FAST            (channels)
            1054 RETURN_VALUE


# Method Name:       create_driver
# Filename:          src\utils.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 1
# Number of locals:  3
# Stack size:        6
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        390
# Constants:
#    0: None
#    1: '--disable-blink-features=AutomationControlled'
#    2: 'excludeSwitches'
#    3: 'enable-automation'
#    4: 'useAutomationExtension'
#    5: False
#    6: '--log-level=3'
#    7: '--disable-gpu'
#    8: '--disable-notifications'
#    9: '--no-first-run'
#   10: '--disable-infobars'
#   11: '--window-position=-32000,-32000'
#   12: 'goog:loggingPrefs'
#   13: 'performance'
#   14: 'ALL'
#   15: ('service', 'options')
# Names:
#    0: webdriver
#    1: ChromeOptions
#    2: add_argument
#    3: add_experimental_option
#    4: set_capability
#    5: Chrome
#    6: Service
#    7: ChromeDriverManager
#    8: install
# Varnames:
#	enable_performance_log, start_offscreen, options
# Positional arguments:
#	enable_performance_log
# Local variables:
#    1: start_offscreen
#    2: options

390:           0 RESUME               0

395:           2 LOAD_GLOBAL          (NULL + webdriver)
              12 LOAD_ATTR            (ChromeOptions)
              32 CALL                 0
              40 STORE_FAST           (options)

396:          42 LOAD_FAST            (options)
              44 LOAD_ATTR            (NULL|self + add_argument)

397:          64 LOAD_CONST           ("--disable-blink-features=AutomationControlled")

396:          66 CALL                 1
              74 POP_TOP

399:          76 LOAD_FAST            (options)
              78 LOAD_ATTR            (NULL|self + add_experimental_option)

400:          98 LOAD_CONST           ("excludeSwitches")
             100 LOAD_CONST           ("enable-automation")
             102 BUILD_LIST           1

399:         104 CALL                 2
             112 POP_TOP

402:         114 LOAD_FAST            (options)
             116 LOAD_ATTR            (NULL|self + add_experimental_option)
             136 LOAD_CONST           ("useAutomationExtension")
             138 LOAD_CONST           (False)
             140 CALL                 2
             148 POP_TOP

403:         150 LOAD_FAST            (options)
             152 LOAD_ATTR            (NULL|self + add_argument)
             172 LOAD_CONST           ("--log-level=3")
             174 CALL                 1
             182 POP_TOP

404:         184 LOAD_FAST            (options)
             186 LOAD_ATTR            (NULL|self + add_argument)
             206 LOAD_CONST           ("--disable-gpu")
             208 CALL                 1
             216 POP_TOP

405:         218 LOAD_FAST            (options)
             220 LOAD_ATTR            (NULL|self + add_argument)
             240 LOAD_CONST           ("--disable-notifications")
             242 CALL                 1
             250 POP_TOP

406:         252 LOAD_FAST            (start_offscreen)
             254 POP_JUMP_IF_FALSE    (to 358)

408:         256 LOAD_FAST            (options)
             258 LOAD_ATTR            (NULL|self + add_argument)
             278 LOAD_CONST           ("--no-first-run")
             280 CALL                 1
             288 POP_TOP

409:         290 LOAD_FAST            (options)
             292 LOAD_ATTR            (NULL|self + add_argument)
             312 LOAD_CONST           ("--disable-infobars")
             314 CALL                 1
             322 POP_TOP

410:         324 LOAD_FAST            (options)
             326 LOAD_ATTR            (NULL|self + add_argument)
             346 LOAD_CONST           ("--window-position=-32000,-32000")
             348 CALL                 1
             356 POP_TOP

411:     >>  358 LOAD_FAST            (enable_performance_log)
             360 POP_JUMP_IF_FALSE    (to 402)

412:         362 LOAD_FAST            (options)
             364 LOAD_ATTR            (NULL|self + set_capability)
             384 LOAD_CONST           ("goog:loggingPrefs")
             386 LOAD_CONST           ("performance")
             388 LOAD_CONST           ("ALL")
             390 BUILD_MAP            1
             392 CALL                 2
             400 POP_TOP

413:     >>  402 LOAD_GLOBAL          (NULL + webdriver)
             412 LOAD_ATTR            (Chrome)

414:         432 LOAD_GLOBAL          (NULL + Service)
             442 LOAD_GLOBAL          (NULL + ChromeDriverManager)
             452 CALL                 0
             460 LOAD_ATTR            (NULL|self + install)
             480 CALL                 0
             488 CALL                 1
             496 LOAD_FAST            (options)

413:         498 KW_NAMES             (('service', 'options'))
             500 CALL                 2
             508 RETURN_VALUE


# Method Name:       normalize_path
# Filename:          src\utils.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  2
# Stack size:        5
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        418
# Constants:
#    0: None
#    1: 'NFC'
#    2: ''
#    3: <Code311 code object <genexpr> at 0x2e1d01e28b0, file src\utils.py>, line 422
# Names:
#    0: unicodedata
#    1: normalize
#    2: strip
#    3: join
# Varnames:
#	path_text, cleaned
# Positional arguments:
#	path_text
# Local variables:
#    1: cleaned

418:           0 RESUME               0

420:           2 LOAD_GLOBAL          (NULL + unicodedata)
              12 LOAD_ATTR            (normalize)
              32 LOAD_CONST           ("NFC")
              34 LOAD_FAST            (path_text)
              36 LOAD_ATTR            (NULL|self + strip)
              56 CALL                 0
              64 CALL                 2
              72 STORE_FAST           (cleaned)

422:          74 LOAD_CONST           ("")
              76 LOAD_ATTR            (NULL|self + join)
              96 LOAD_CONST           (<Code311 code object <genexpr> at 0x2e1d01e28b0, file src\utils.py>, line 422)
              98 MAKE_FUNCTION        (No arguments)
             100 LOAD_FAST            (cleaned)
             102 GET_ITER
             104 CALL                 0
             112 CALL                 1
             120 RETURN_VALUE


# Method Name:       validate_path_text
# Filename:          src\utils.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  3
# Stack size:        5
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        425
# Constants:
#    0: 'Validate an absolute file path for allowed audio types.'
#    1: (False, 'Vui lòng nhập đường dẫn tuyệt đối tới file âm thanh')
#    2: False
#    3: 'File không tồn tại hoặc không phải là file hợp lệ: '
#    4: ('.mp4', '.wav', '.mp3')
#    5: 'Định dạng không hợp lệ. Chỉ chấp nhận '
#    6: ', '
#    7: (True, None)
# Names:
#    0: normalize_path
#    1: Path
#    2: exists
#    3: is_file
#    4: suffix
#    5: lower
#    6: join
# Varnames:
#	path_text, p, allowed_extensions
# Positional arguments:
#	path_text
# Local variables:
#    1: p
#    2: allowed_extensions

425:           0 RESUME               0

427:           2 LOAD_FAST            (path_text)
               4 POP_JUMP_IF_TRUE     (to 8)

428:           6 RETURN_CONST         ((False, 'Vui lòng nhập đường dẫn tuyệt đối tới file âm thanh'))

429:     >>    8 LOAD_GLOBAL          (NULL + normalize_path)
              18 LOAD_FAST            (path_text)
              20 CALL                 1
              28 STORE_FAST           (path_text)

430:          30 LOAD_GLOBAL          (NULL + Path)
              40 LOAD_FAST            (path_text)
              42 CALL                 1
              50 STORE_FAST           (p)

431:          52 LOAD_FAST            (p)
              54 LOAD_ATTR            (NULL|self + exists)
              74 CALL                 0
              82 POP_JUMP_IF_FALSE    (to 116)
              84 LOAD_FAST            (p)
              86 LOAD_ATTR            (NULL|self + is_file)
             106 CALL                 0
             114 POP_JUMP_IF_TRUE     (to 130)

433:     >>  116 LOAD_CONST           (False)

434:         118 LOAD_CONST           ("File không tồn tại hoặc không phải là file hợp lệ: ")
             120 LOAD_FAST            (path_text)
             122 FORMAT_VALUE         0
             124 BUILD_STRING         2

432:         126 BUILD_TUPLE          2
             128 RETURN_VALUE

436:     >>  130 BUILD_LIST           0
             132 LOAD_CONST           (('.mp4', '.wav', '.mp3'))
             134 LIST_EXTEND          1
             136 STORE_FAST           (allowed_extensions)

437:         138 LOAD_FAST            (p)
             140 LOAD_ATTR            (suffix)
             160 LOAD_ATTR            (NULL|self + lower)
             180 CALL                 0
             188 LOAD_FAST            (allowed_extensions)
             190 CONTAINS_OP          (not in)
             192 POP_JUMP_IF_FALSE    (to 238)

439:         194 LOAD_CONST           (False)

440:         196 LOAD_CONST           ("Định dạng không hợp lệ. Chỉ chấp nhận ")
             198 LOAD_CONST           (", ")
             200 LOAD_ATTR            (NULL|self + join)
             220 LOAD_FAST            (allowed_extensions)
             222 CALL                 1
             230 FORMAT_VALUE         0
             232 BUILD_STRING         2

438:         234 BUILD_TUPLE          2
             236 RETURN_VALUE

442:     >>  238 RETURN_CONST         ((True, None))


# Method Name:       get_request_payload_from_performance_log
# Filename:          src\utils.py
# Argument count:    4
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  10
# Stack size:        7
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        445
# Constants:
#    0: '\n    Đọc performance log của Chrome, tìm request có URL chứa `url_substring`,\n    trả về payload (postData) của request đó.\n\n    Returns:\n        - str: postData nếu request có body\n        - None: nếu request match nhưng không có body (GET/empty)\n    Raises:\n        - TimeoutError: nếu hết timeout vẫn không thấy request\n    '
#    1: 'performance'
#    2: 'message'
#    3: 'method'
#    4: 'Network.requestWillBeSent'
#    5: 'params'
#    6: 'request'
#    7: 'url'
#    8: ''
#    9: 'postData'
#   10: "Không tìm thấy request chứa '"
#   11: "' sau "
#   12: 's'
# Names:
#    0: time
#    1: monotonic
#    2: get_log
#    3: json
#    4: loads
#    5: get
#    6: JSONDecodeError
#    7: KeyError
#    8: TypeError
#    9: sleep
#   10: TimeoutError
# Varnames:
#	driver, url_substring, timeout, poll_interval, deadline, entry, msg, method, params, request
# Positional arguments:
#	driver, url_substring, timeout, poll_interval
# Local variables:
#    4: deadline
#    5: entry
#    6: msg
#    7: method
#    8: params
#    9: request

445:           0 RESUME               0

458:           2 LOAD_GLOBAL          (NULL + time)
              12 LOAD_ATTR            (monotonic)
              32 CALL                 0
              40 LOAD_FAST            (timeout)
              42 BINARY_OP            (+)
              46 STORE_FAST           (deadline)

459:          48 LOAD_GLOBAL          (NULL + time)
              58 LOAD_ATTR            (monotonic)
              78 CALL                 0
              86 LOAD_FAST            (deadline)
              88 COMPARE_OP           (<)
              92 POP_JUMP_IF_FALSE    (to 538)

460:          94 LOAD_FAST            (driver)
              96 LOAD_ATTR            (NULL|self + get_log)
             116 LOAD_CONST           ("performance")
             118 CALL                 1
             126 GET_ITER
             128 FOR_ITER             (to 446)
             132 STORE_FAST           (entry)

461:         134 NOP

462:         136 LOAD_GLOBAL          (NULL + json)
             146 LOAD_ATTR            (loads)
             166 LOAD_FAST            (entry)
             168 LOAD_CONST           ("message")
             170 BINARY_SUBSCR
             174 CALL                 1
             182 STORE_FAST           (msg)

463:         184 LOAD_FAST            (msg)
             186 LOAD_ATTR            (NULL|self + get)
             206 LOAD_CONST           ("message")
             208 BUILD_MAP            0
             210 CALL                 2
             218 LOAD_ATTR            (NULL|self + get)
             238 LOAD_CONST           ("method")
             240 CALL                 1
             248 STORE_FAST           (method)

464:         250 LOAD_FAST            (method)
             252 LOAD_CONST           ("Network.requestWillBeSent")
             254 COMPARE_OP           (!=)
             258 POP_JUMP_IF_FALSE    (to 262)

465:         260 JUMP_BACKWARD        (to 128)

466:     >>  262 LOAD_FAST            (msg)
             264 LOAD_ATTR            (NULL|self + get)
             284 LOAD_CONST           ("message")
             286 BUILD_MAP            0
             288 CALL                 2
             296 LOAD_ATTR            (NULL|self + get)
             316 LOAD_CONST           ("params")
             318 BUILD_MAP            0
             320 CALL                 2
             328 STORE_FAST           (params)

467:         330 LOAD_FAST            (params)
             332 LOAD_ATTR            (NULL|self + get)
             352 LOAD_CONST           ("request")
             354 BUILD_MAP            0
             356 CALL                 2
             364 STORE_FAST           (request)

468:         366 LOAD_FAST            (url_substring)
             368 LOAD_FAST            (request)
             370 LOAD_ATTR            (NULL|self + get)
             390 LOAD_CONST           ("url")
             392 LOAD_CONST           ("")
             394 CALL                 2
             402 CONTAINS_OP          (not in)
             404 POP_JUMP_IF_FALSE    (to 408)

469:         406 JUMP_BACKWARD        (to 128)

470:     >>  408 LOAD_FAST            (request)
             410 LOAD_ATTR            (NULL|self + get)
             430 LOAD_CONST           ("postData")
             432 CALL                 1
             440 SWAP                 (TOS <-> TOS1)
             442 POP_TOP
         >>  444 RETURN_VALUE

460:         446 END_FOR

473:         448 LOAD_GLOBAL          (NULL + time)
             458 LOAD_ATTR            (sleep)
             478 LOAD_FAST            (poll_interval)
             480 CALL                 1
             488 POP_TOP

459:         490 LOAD_GLOBAL          (NULL + time)
             500 LOAD_ATTR            (monotonic)
             520 CALL                 0
             528 LOAD_FAST            (deadline)
             530 COMPARE_OP           (<)
             534 POP_JUMP_IF_FALSE    (to 538)
             536 JUMP_BACKWARD        (to 94)

474:     >>  538 LOAD_GLOBAL          (NULL + TimeoutError)
             548 LOAD_CONST           ("Không tìm thấy request chứa '")
             550 LOAD_FAST            (url_substring)
             552 FORMAT_VALUE         0
             554 LOAD_CONST           ("' sau ")
             556 LOAD_FAST            (timeout)
             558 FORMAT_VALUE         0
             560 LOAD_CONST           ("s")
             562 BUILD_STRING         5
             564 CALL                 1
             572 RAISE_VARARGS        (exception instance)
             574 PUSH_EXC_INFO

471:         576 LOAD_GLOBAL          (json)
             586 LOAD_ATTR            (JSONDecodeError)
             606 LOAD_GLOBAL          (KeyError)
             616 LOAD_GLOBAL          (TypeError)
             626 BUILD_TUPLE          3
             628 CHECK_EXC_MATCH
             630 POP_JUMP_IF_FALSE    (to 638)
             632 POP_TOP

472:         634 POP_EXCEPT
             636 JUMP_BACKWARD        (to 128)

471:     >>  638 RERAISE              0
             640 COPY                 3
             642 POP_EXCEPT
             644 RERAISE              1

ExceptionTable:
  136 to 258 -> 574 [1]
  262 to 404 -> 574 [1]
  408 to 438 -> 574 [1]
  574 to 632 -> 640 [2] lasti
  638 to 638 -> 640 [2] lasti

# Method Name:       <lambda>
# Filename:          src\utils.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  1
# Stack size:        2
# Flags:             0x00000013 (NESTED | NEWLOCALS | OPTIMIZED)
# First Line:        161
# Constants:
#    0: None
# Names:
#    0: name
#    1: lower
# Varnames:
#	p
# Positional arguments:
#	p

161:           0 RESUME               0
               2 LOAD_FAST            (p)
               4 LOAD_ATTR            (name)
              24 LOAD_ATTR            (NULL|self + lower)
              44 CALL                 0
              52 RETURN_VALUE


# Method Name:       <genexpr>
# Filename:          src\utils.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  2
# Stack size:        4
# Flags:             0x00000033 (GENERATOR | NESTED | NEWLOCALS | OPTIMIZED)
# First Line:        422
# Constants:
#    0: 0
#    1: 'C'
#    2: None
# Names:
#    0: unicodedata
#    1: category
# Varnames:
#	.0, ch
# Positional arguments:
#	.0
# Local variables:
#    1: ch

422:           0 RETURN_GENERATOR
               2 POP_TOP
               4 RESUME               0
               6 LOAD_FAST            (.0)
               8 FOR_ITER             (to 80)
              12 STORE_FAST           (ch)
              14 LOAD_GLOBAL          (NULL + unicodedata)
              24 LOAD_ATTR            (category)
              44 LOAD_FAST            (ch)
              46 CALL                 1
              54 LOAD_CONST           (0)
              56 BINARY_SUBSCR
              60 LOAD_CONST           ("C")
              62 COMPARE_OP           (!=)
              66 POP_JUMP_IF_TRUE     (to 70)
              68 JUMP_BACKWARD        (to 8)
         >>   70 LOAD_FAST            (ch)
              72 YIELD_VALUE          1
              74 RESUME               1
              76 POP_TOP
         >>   78 JUMP_BACKWARD        (to 8)
              80 END_FOR
              82 RETURN_CONST         (None)
              84 CALL_INTRINSIC_1     3
              86 RERAISE              1

ExceptionTable:
  4 to 66 -> 84 [0] lasti
  70 to 82 -> 84 [0] lasti
```
