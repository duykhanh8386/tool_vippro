# Static CPython 3.12 disassembly — `channel_refresh.pyc`

Generated with `xdis 6.3.0`; the code object was deserialized but never executed.

```text
# pydisasm version 6.3.0
# CPython Python bytecode 3.12.0 (3531)
#   Disassembled from CPython Python 3.13.13 | packaged by Anaconda, Inc. | (main, Apr 14 2026, 06:12:50) [MSC v.1942 64 bit (AMD64)]
# Timestamp in code: 0 (1970-01-01 07:00:00)
# Source code size mod 2**32: 0 bytes
# Method Name:       <module>
# Filename:          src\channel_refresh.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        7
# Flags:             0x00000000 (0x0)
# First Line:        1
# Constants:
#    0: '\nRefresh challenge & botguardResponse for a channel.\n\nOpens a headless Chrome, injects stored cookies, navigates to YouTube Studio\nanalytics page, and captures the fresh tokens from the performance log.\n'
#    1: 0
#    2: None
#    3: ('logger',)
#    4: ('channel_store',)
#    5: ('inject_cookies_via_cdp',)
#    6: ('create_driver', 'get_request_payload_from_performance_log')
#    7: 20.0
#    8: ('timeout',)
#    9: 'channel_id'
#   10: 'timeout'
#   11: 'return'
#   12: <Code311 code object refresh_challenge_and_botguard at 0x2e505872270, file src\channel_refresh.py>, line 17
# Names:
#    0: __doc__
#    1: json
#    2: loguru
#    3: logger
#    4: src.channel_store
#    5: channel_store
#    6: src.cookie_utils
#    7: inject_cookies_via_cdp
#    8: src.utils
#    9: create_driver
#   10: get_request_payload_from_performance_log
#   11: str
#   12: float
#   13: dict
#   14: refresh_challenge_and_botguard

  0:           0 RESUME               0

  1:           2 LOAD_CONST           ("\nRefresh challenge & botguardResponse for a channel.\n\nOpens a headless Chrome, injects stored cookies, navigates to YouTube Studio\nanalytics page, and captures the fresh tokens from the performance log.\n")
               4 STORE_NAME           (__doc__)

  8:           6 LOAD_CONST           (0)
               8 LOAD_CONST           (None)
              10 IMPORT_NAME          (json)
              12 STORE_NAME           (json)

 10:          14 LOAD_CONST           (0)
              16 LOAD_CONST           (('logger',))
              18 IMPORT_NAME          (loguru)
              20 IMPORT_FROM          (logger)
              22 STORE_NAME           (logger)
              24 POP_TOP

 12:          26 LOAD_CONST           (0)
              28 LOAD_CONST           (('channel_store',))
              30 IMPORT_NAME          (src.channel_store)
              32 IMPORT_FROM          (channel_store)
              34 STORE_NAME           (channel_store)
              36 POP_TOP

 13:          38 LOAD_CONST           (0)
              40 LOAD_CONST           (('inject_cookies_via_cdp',))
              42 IMPORT_NAME          (src.cookie_utils)
              44 IMPORT_FROM          (inject_cookies_via_cdp)
              46 STORE_NAME           (inject_cookies_via_cdp)
              48 POP_TOP

 14:          50 LOAD_CONST           (0)
              52 LOAD_CONST           (('create_driver', 'get_request_payload_from_performance_log'))
              54 IMPORT_NAME          (src.utils)
              56 IMPORT_FROM          (create_driver)
              58 STORE_NAME           (create_driver)
              60 IMPORT_FROM          (get_request_payload_from_performance_log)
              62 STORE_NAME           (get_request_payload_from_performance_log)
              64 POP_TOP

 18:          66 LOAD_CONST           (20.0)

 17:          68 LOAD_CONST           (('timeout',))
              70 BUILD_CONST_KEY_MAP  1
              72 LOAD_CONST           ("channel_id")

 18:          74 LOAD_NAME            (str)

 17:          76 LOAD_CONST           ("timeout")

 18:          78 LOAD_NAME            (float)

 17:          80 LOAD_CONST           ("return")

 19:          82 LOAD_NAME            (dict)

 17:          84 BUILD_TUPLE          6
              86 LOAD_CONST           (<Code311 code object refresh_challenge_and_botguard at 0x2e505872270, file src\channel_refresh.py>, line 17)
              88 MAKE_FUNCTION        (keyword-only, annotation)
              90 STORE_NAME           (refresh_challenge_and_botguard)
              92 RETURN_CONST         (None)


# Method Name:       refresh_challenge_and_botguard
# Filename:          src\channel_refresh.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 1
# Number of locals:  10
# Stack size:        14
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        17
# Constants:
#    0: '\n    Refresh ``challenge`` and ``botguardResponse`` for *channel_id*.\n\n    Returns a dict ``{"challenge": ..., "botguardResponse": ...}`` on success.\n    Raises ``ValueError`` if the channel is not found in the database.\n    '
#    1: 'Channel not found: '
#    2: 'cookies'
#    3: True
#    4: ('enable_performance_log', 'start_offscreen')
#    5: 'https://studio.youtube.com/'
#    6: 'https://studio.youtube.com/channel/'
#    7: '/analytics/tab-overview/period-default'
#    8: 'youtubei/v1/att/esr?alt=json'
#    9: ('timeout',)
#   10: 'challenge'
#   11: 'botguardResponse'
#   12: 'name'
#   13: ''
#   14: 'img_src'
#   15: 'delegated_session_id'
#   16: 'sapisidhash'
#   17: 'role'
#   18: ('id', 'name', 'img_src', 'delegated_session_id', 'sapisidhash', 'role', 'challenge', 'botguardResponse', 'cookies')
#   19: 'Refreshed challenge/botguard for '
#   20: ('challenge', 'botguardResponse')
# Names:
#    0: channel_store
#    1: init_db
#    2: get_channel
#    3: ValueError
#    4: get
#    5: create_driver
#    6: inject_cookies_via_cdp
#    7: get_request_payload_from_performance_log
#    8: json
#    9: loads
#   10: upsert_channel
#   11: logger
#   12: info
#   13: quit
# Varnames:
#	channel_id, timeout, rec, cookies, driver, target_url, payload, payload_json, challenge, botguardResponse
# Positional arguments:
#	channel_id
# Local variables:
#    1: timeout
#    2: rec
#    3: cookies
#    4: driver
#    5: target_url
#    6: payload
#    7: payload_json
#    8: challenge
#    9: botguardResponse

 17:           0 RESUME               0

 26:           2 LOAD_GLOBAL          (NULL + channel_store)
              12 LOAD_ATTR            (init_db)
              32 CALL                 0
              40 POP_TOP

 27:          42 LOAD_GLOBAL          (NULL + channel_store)
              52 LOAD_ATTR            (get_channel)
              72 LOAD_FAST            (channel_id)
              74 CALL                 1
              82 STORE_FAST           (rec)

 28:          84 LOAD_FAST            (rec)
              86 POP_JUMP_IF_TRUE     (to 116)

 29:          88 LOAD_GLOBAL          (NULL + ValueError)
              98 LOAD_CONST           ("Channel not found: ")
             100 LOAD_FAST            (channel_id)
             102 FORMAT_VALUE         0
             104 BUILD_STRING         2
             106 CALL                 1
             114 RAISE_VARARGS        (exception instance)

 31:     >>  116 LOAD_FAST            (rec)
             118 LOAD_ATTR            (NULL|self + get)
             138 LOAD_CONST           ("cookies")
             140 BUILD_LIST           0
             142 CALL                 2
             150 COPY                 1
             152 POP_JUMP_IF_TRUE     (to 158)
             154 POP_TOP
             156 BUILD_LIST           0
         >>  158 STORE_FAST           (cookies)

 32:         160 LOAD_GLOBAL          (NULL + create_driver)
             170 LOAD_CONST           (True)
             172 LOAD_CONST           (True)
             174 KW_NAMES             (('enable_performance_log', 'start_offscreen'))
             176 CALL                 2
             184 STORE_FAST           (driver)

 34:         186 NOP

 36:         188 LOAD_FAST            (driver)
             190 LOAD_ATTR            (NULL|self + get)
             210 LOAD_CONST           ("https://studio.youtube.com/")
             212 CALL                 1
             220 POP_TOP

 37:         222 LOAD_GLOBAL          (NULL + inject_cookies_via_cdp)
             232 LOAD_FAST            (driver)
             234 LOAD_FAST            (cookies)
             236 CALL                 2
             244 POP_TOP

 41:         246 LOAD_CONST           ("https://studio.youtube.com/channel/")
             248 LOAD_FAST            (channel_id)
             250 FORMAT_VALUE         0

 42:         252 LOAD_CONST           ("/analytics/tab-overview/period-default")

 41:         254 BUILD_STRING         3

 40:         256 STORE_FAST           (target_url)

 44:         258 LOAD_FAST            (driver)
             260 LOAD_ATTR            (NULL|self + get)
             280 LOAD_FAST            (target_url)
             282 CALL                 1
             290 POP_TOP

 47:         292 LOAD_GLOBAL          (NULL + get_request_payload_from_performance_log)

 48:         302 LOAD_FAST            (driver)
             304 LOAD_CONST           ("youtubei/v1/att/esr?alt=json")
             306 LOAD_FAST            (timeout)

 47:         308 KW_NAMES             (('timeout',))
             310 CALL                 3
             318 STORE_FAST           (payload)

 50:         320 LOAD_GLOBAL          (NULL + json)
             330 LOAD_ATTR            (loads)
             350 LOAD_FAST            (payload)
             352 CALL                 1
             360 STORE_FAST           (payload_json)

 51:         362 LOAD_FAST            (payload_json)
             364 LOAD_ATTR            (NULL|self + get)
             384 LOAD_CONST           ("challenge")
             386 CALL                 1
             394 STORE_FAST           (challenge)

 52:         396 LOAD_FAST            (payload_json)
             398 LOAD_ATTR            (NULL|self + get)
             418 LOAD_CONST           ("botguardResponse")
             420 CALL                 1
             428 STORE_FAST           (botguardResponse)

 55:         430 LOAD_GLOBAL          (NULL + channel_store)
             440 LOAD_ATTR            (upsert_channel)

 57:         460 LOAD_FAST            (channel_id)

 58:         462 LOAD_FAST            (rec)
             464 LOAD_ATTR            (NULL|self + get)
             484 LOAD_CONST           ("name")
             486 LOAD_CONST           ("")
             488 CALL                 2

 59:         496 LOAD_FAST            (rec)
             498 LOAD_ATTR            (NULL|self + get)
             518 LOAD_CONST           ("img_src")
             520 LOAD_CONST           ("")
             522 CALL                 2

 60:         530 LOAD_FAST            (rec)
             532 LOAD_ATTR            (NULL|self + get)
             552 LOAD_CONST           ("delegated_session_id")
             554 LOAD_CONST           ("")
             556 CALL                 2

 61:         564 LOAD_FAST            (rec)
             566 LOAD_ATTR            (NULL|self + get)
             586 LOAD_CONST           ("sapisidhash")
             588 LOAD_CONST           ("")
             590 CALL                 2

 62:         598 LOAD_FAST            (rec)
             600 LOAD_ATTR            (NULL|self + get)
             620 LOAD_CONST           ("role")
             622 LOAD_CONST           ("")
             624 CALL                 2

 63:         632 LOAD_FAST            (challenge)

 64:         634 LOAD_FAST            (botguardResponse)

 65:         636 LOAD_FAST            (rec)
             638 LOAD_ATTR            (NULL|self + get)
             658 LOAD_CONST           ("cookies")
             660 BUILD_LIST           0
             662 CALL                 2

 56:         670 LOAD_CONST           (('id', 'name', 'img_src', 'delegated_session_id', 'sapisidhash', 'role', 'challenge', 'botguardResponse', 'cookies'))
             672 BUILD_CONST_KEY_MAP  9

 55:         674 CALL                 1
             682 POP_TOP

 69:         684 LOAD_GLOBAL          (NULL + logger)
             694 LOAD_ATTR            (info)
             714 LOAD_CONST           ("Refreshed challenge/botguard for ")
             716 LOAD_FAST            (channel_id)
             718 FORMAT_VALUE         0
             720 BUILD_STRING         2
             722 CALL                 1
             730 POP_TOP

 70:         732 LOAD_FAST            (challenge)
             734 LOAD_FAST            (botguardResponse)
             736 LOAD_CONST           (('challenge', 'botguardResponse'))
             738 BUILD_CONST_KEY_MAP  2

 72:         740 LOAD_FAST            (driver)
             742 LOAD_ATTR            (NULL|self + quit)
             762 CALL                 0
             770 POP_TOP
             772 RETURN_VALUE
             774 PUSH_EXC_INFO
             776 LOAD_FAST            (driver)
             778 LOAD_ATTR            (NULL|self + quit)
             798 CALL                 0
             806 POP_TOP
             808 RERAISE              0
             810 COPY                 3
             812 POP_EXCEPT
             814 RERAISE              1

ExceptionTable:
  188 to 738 -> 774 [0]
  774 to 808 -> 810 [1] lasti
```
