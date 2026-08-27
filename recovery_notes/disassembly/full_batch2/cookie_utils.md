# Static CPython 3.12 disassembly — `cookie_utils.pyc`

Generated with `xdis 6.3.0`; the code object was deserialized but never executed.

```text
# pydisasm version 6.3.0
# CPython Python bytecode 3.12.0 (3531)
#   Disassembled from CPython Python 3.13.13 | packaged by Anaconda, Inc. | (main, Apr 14 2026, 06:12:50) [MSC v.1942 64 bit (AMD64)]
# Timestamp in code: 0 (1970-01-01 07:00:00)
# Source code size mod 2**32: 0 bytes
# Method Name:       <module>
# Filename:          src\cookie_utils.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        5
# Flags:             0x00000000 (0x0)
# First Line:        1
# Constants:
#    0: '\nCookie utilities: normalise Selenium cookies for storage and inject via CDP.\n'
#    1: 0
#    2: ('logger',)
#    3: 'lax'
#    4: 'strict'
#    5: 'unspecified'
#    6: ('Lax', 'Strict', 'None')
#    7: 'selenium_cookies'
#    8: 'return'
#    9: <Code311 code object normalize_cookies_for_storage at 0x2e5058d8050, file src\cookie_utils.py>, line 18
#   10: 'Lax'
#   11: 'Strict'
#   12: 'None'
#   13: ('lax', 'strict', 'unspecified', 'no_restriction')
#   14: 'cookies'
#   15: <Code311 code object inject_cookies_via_cdp at 0x2e50540fa80, file src\cookie_utils.py>, line 57
#   16: None
# Names:
#    0: __doc__
#    1: loguru
#    2: logger
#    3: _SAMESITE_SELENIUM_TO_STORAGE
#    4: list
#    5: normalize_cookies_for_storage
#    6: _SAMESITE_STORAGE_TO_CDP
#    7: int
#    8: inject_cookies_via_cdp

  0:           0 RESUME               0

  1:           2 LOAD_CONST           ("\nCookie utilities: normalise Selenium cookies for storage and inject via CDP.\n")
               4 STORE_NAME           (__doc__)

  5:           6 LOAD_CONST           (0)
               8 LOAD_CONST           (('logger',))
              10 IMPORT_NAME          (loguru)
              12 IMPORT_FROM          (logger)
              14 STORE_NAME           (logger)
              16 POP_TOP

 12:          18 LOAD_CONST           ("lax")

 13:          20 LOAD_CONST           ("strict")

 14:          22 LOAD_CONST           ("unspecified")

 11:          24 LOAD_CONST           (('Lax', 'Strict', 'None'))
              26 BUILD_CONST_KEY_MAP  3
              28 STORE_NAME           (_SAMESITE_SELENIUM_TO_STORAGE)

 18:          30 LOAD_CONST           ("selenium_cookies")
              32 LOAD_NAME            (list)
              34 LOAD_CONST           ("return")
              36 LOAD_NAME            (list)
              38 BUILD_TUPLE          4
              40 LOAD_CONST           (<Code311 code object normalize_cookies_for_storage at 0x2e5058d8050, file src\cookie_utils.py>, line 18)
              42 MAKE_FUNCTION        (annotation)
              44 STORE_NAME           (normalize_cookies_for_storage)

 50:          46 LOAD_CONST           ("Lax")

 51:          48 LOAD_CONST           ("Strict")

 52:          50 LOAD_CONST           ("None")

 53:          52 LOAD_CONST           ("None")

 49:          54 LOAD_CONST           (('lax', 'strict', 'unspecified', 'no_restriction'))
              56 BUILD_CONST_KEY_MAP  4
              58 STORE_NAME           (_SAMESITE_STORAGE_TO_CDP)

 57:          60 LOAD_CONST           ("cookies")
              62 LOAD_NAME            (list)
              64 LOAD_CONST           ("return")
              66 LOAD_NAME            (int)
              68 BUILD_TUPLE          4
              70 LOAD_CONST           (<Code311 code object inject_cookies_via_cdp at 0x2e50540fa80, file src\cookie_utils.py>, line 57)
              72 MAKE_FUNCTION        (annotation)
              74 STORE_NAME           (inject_cookies_via_cdp)
              76 RETURN_CONST         (None)


# Method Name:       normalize_cookies_for_storage
# Filename:          src\cookie_utils.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  5
# Stack size:        14
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        18
# Constants:
#    0: 'Convert Selenium-format cookies to a browser-export-like format.'
#    1: 'domain'
#    2: ''
#    3: '.'
#    4: 'httpOnly'
#    5: False
#    6: 'name'
#    7: 'path'
#    8: '/'
#    9: 'sameSite'
#   10: 'None'
#   11: 'unspecified'
#   12: 'secure'
#   13: 'expiry'
#   14: 'expirationDate'
#   15: '0'
#   16: 'value'
#   17: ('domain', 'hostOnly', 'httpOnly', 'name', 'path', 'sameSite', 'secure', 'session', 'storeId', 'value')
# Names:
#    0: get
#    1: str
#    2: startswith
#    3: _SAMESITE_SELENIUM_TO_STORAGE
#    4: float
#    5: append
# Varnames:
#	selenium_cookies, result, c, domain, cookie
# Positional arguments:
#	selenium_cookies
# Local variables:
#    1: result
#    2: c
#    3: domain
#    4: cookie

 18:           0 RESUME               0

 20:           2 BUILD_LIST           0
               4 STORE_FAST           (result)

 21:           6 LOAD_FAST            (selenium_cookies)
               8 GET_ITER
              10 EXTENDED_ARG         (256)
              12 FOR_ITER             (to 556)
              16 STORE_FAST           (c)

 22:          18 LOAD_FAST            (c)
              20 LOAD_ATTR            (NULL|self + get)
              40 LOAD_CONST           ("domain")
              42 LOAD_CONST           ("")
              44 CALL                 2
              52 STORE_FAST           (domain)

 24:          54 LOAD_FAST            (domain)

 25:          56 LOAD_GLOBAL          (NULL + str)
              66 LOAD_FAST            (domain)
              68 CALL                 1
              76 LOAD_ATTR            (NULL|self + startswith)
              96 LOAD_CONST           (".")
              98 CALL                 1
             106 UNARY_NOT

 26:         108 LOAD_FAST            (c)
             110 LOAD_ATTR            (NULL|self + get)
             130 LOAD_CONST           ("httpOnly")
             132 LOAD_CONST           (False)
             134 CALL                 2

 27:         142 LOAD_FAST            (c)
             144 LOAD_ATTR            (NULL|self + get)
             164 LOAD_CONST           ("name")
             166 LOAD_CONST           ("")
             168 CALL                 2

 28:         176 LOAD_FAST            (c)
             178 LOAD_ATTR            (NULL|self + get)
             198 LOAD_CONST           ("path")
             200 LOAD_CONST           ("/")
             202 CALL                 2

 29:         210 LOAD_GLOBAL          (_SAMESITE_SELENIUM_TO_STORAGE)
             220 LOAD_ATTR            (NULL|self + get)

 30:         240 LOAD_FAST            (c)
             242 LOAD_ATTR            (NULL|self + get)
             262 LOAD_CONST           ("sameSite")
             264 LOAD_CONST           ("None")
             266 CALL                 2
             274 LOAD_CONST           ("unspecified")

 29:         276 CALL                 2

 32:         284 LOAD_FAST            (c)
             286 LOAD_ATTR            (NULL|self + get)
             306 LOAD_CONST           ("secure")
             308 LOAD_CONST           (False)
             310 CALL                 2

 33:         318 LOAD_CONST           ("expiry")
             320 LOAD_FAST            (c)
             322 CONTAINS_OP          (not in)
             324 COPY                 1
             326 POP_JUMP_IF_FALSE    (to 364)
             328 POP_TOP
             330 LOAD_FAST            (c)
             332 LOAD_ATTR            (NULL|self + get)
             352 LOAD_CONST           ("expirationDate")
             354 CALL                 1
             362 UNARY_NOT

 34:     >>  364 LOAD_CONST           ("0")

 35:         366 LOAD_FAST            (c)
             368 LOAD_ATTR            (NULL|self + get)
             388 LOAD_CONST           ("value")
             390 LOAD_CONST           ("")
             392 CALL                 2

 23:         400 LOAD_CONST           (('domain', 'hostOnly', 'httpOnly', 'name', 'path', 'sameSite', 'secure', 'session', 'storeId', 'value'))
             402 BUILD_CONST_KEY_MAP  10
             404 STORE_FAST           (cookie)

 37:         406 LOAD_CONST           ("expiry")
             408 LOAD_FAST            (c)
             410 CONTAINS_OP          (in)
             412 POP_JUMP_IF_FALSE    (to 450)

 38:         414 LOAD_GLOBAL          (NULL + float)
             424 LOAD_FAST            (c)
             426 LOAD_CONST           ("expiry")
             428 BINARY_SUBSCR
             432 CALL                 1
             440 LOAD_FAST            (cookie)
             442 LOAD_CONST           ("expirationDate")
             444 STORE_SUBSCR
             448 JUMP_FORWARD         (to 518)

 39:     >>  450 LOAD_FAST            (c)
             452 LOAD_ATTR            (NULL|self + get)
             472 LOAD_CONST           ("expirationDate")
             474 CALL                 1
             482 POP_JUMP_IF_NONE     (to 518)

 40:         484 LOAD_GLOBAL          (NULL + float)
             494 LOAD_FAST            (c)
             496 LOAD_CONST           ("expirationDate")
             498 BINARY_SUBSCR
             502 CALL                 1
             510 LOAD_FAST            (cookie)
             512 LOAD_CONST           ("expirationDate")
             514 STORE_SUBSCR

 41:     >>  518 LOAD_FAST            (result)
             520 LOAD_ATTR            (NULL|self + append)
             540 LOAD_FAST            (cookie)
             542 CALL                 1
             550 POP_TOP
             552 EXTENDED_ARG         (256)
         >>  554 JUMP_BACKWARD        (to 10)

 21:         556 END_FOR

 42:         558 LOAD_FAST            (result)
             560 RETURN_VALUE


# Method Name:       inject_cookies_via_cdp
# Filename:          src\cookie_utils.py
# Argument count:    2
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  11
# Stack size:        13
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        57
# Constants:
#    0: 'Inject cookies using Chrome DevTools Protocol. Returns attempted count.'
#    1: 'Network.enable'
#    2: 0
#    3: 'name'
#    4: 'value'
#    5: 1
#    6: 'domain'
#    7: '.youtube.com'
#    8: 'youtube'
#    9: 'https://studio.youtube.com'
#   10: 'google'
#   11: 'https://www.google.com'
#   12: 'path'
#   13: '/'
#   14: 'secure'
#   15: False
#   16: 'httpOnly'
#   17: ('name', 'value', 'domain', 'path', 'url', 'secure', 'httpOnly')
#   18: 'expirationDate'
#   19: 'expiry'
#   20: 'expires'
#   21: 'sameSite'
#   22: 'unspecified'
#   23: 'None'
#   24: 'Network.setCookie'
#   25: 'Failed to inject cookie: '
# Names:
#    0: execute_cdp_cmd
#    1: get
#    2: lower
#    3: bool
#    4: float
#    5: _SAMESITE_STORAGE_TO_CDP
#    6: Exception
#    7: logger
#    8: debug
# Varnames:
#	driver, cookies, attempted, cookie, name, value, domain, req_url, cdp_params, expires, raw_ss
# Positional arguments:
#	driver, cookies
# Local variables:
#    2: attempted
#    3: cookie
#    4: name
#    5: value
#    6: domain
#    7: req_url
#    8: cdp_params
#    9: expires
#   10: raw_ss

 57:           0 RESUME               0

 59:           2 LOAD_FAST            (driver)
               4 LOAD_ATTR            (NULL|self + execute_cdp_cmd)
              24 LOAD_CONST           ("Network.enable")
              26 BUILD_MAP            0
              28 CALL                 2
              36 POP_TOP

 61:          38 LOAD_CONST           (0)
              40 STORE_FAST           (attempted)

 62:          42 LOAD_FAST            (cookies)
              44 GET_ITER
              46 EXTENDED_ARG         (256)
              48 FOR_ITER             (to 684)
              52 STORE_FAST           (cookie)

 63:          54 LOAD_FAST            (cookie)
              56 LOAD_ATTR            (NULL|self + get)
              76 LOAD_CONST           ("name")
              78 CALL                 1
              86 STORE_FAST           (name)

 64:          88 LOAD_FAST            (cookie)
              90 LOAD_ATTR            (NULL|self + get)
             110 LOAD_CONST           ("value")
             112 CALL                 1
             120 STORE_FAST           (value)

 65:         122 LOAD_FAST            (name)
             124 POP_JUMP_IF_FALSE    (to 130)
             126 LOAD_FAST            (value)
             128 POP_JUMP_IF_NOT_NONE (to 132)

 66:     >>  130 JUMP_BACKWARD        (to 46)

 67:     >>  132 LOAD_FAST            (attempted)
             134 LOAD_CONST           (1)
             136 BINARY_OP            (+=)
             140 STORE_FAST           (attempted)

 69:         142 LOAD_FAST            (cookie)
             144 LOAD_ATTR            (NULL|self + get)
             164 LOAD_CONST           ("domain")
             166 CALL                 1
             174 COPY                 1
             176 POP_JUMP_IF_TRUE     (to 182)
             178 POP_TOP
             180 LOAD_CONST           (".youtube.com")
         >>  182 STORE_FAST           (domain)

 71:         184 LOAD_CONST           ("youtube")
             186 LOAD_FAST            (domain)
             188 LOAD_ATTR            (NULL|self + lower)
             208 CALL                 0
             216 CONTAINS_OP          (in)
         >>  218 POP_JUMP_IF_FALSE    (to 226)

 72:         220 LOAD_CONST           ("https://studio.youtube.com")
             222 STORE_FAST           (req_url)
             224 JUMP_FORWARD         (to 272)

 73:     >>  226 LOAD_CONST           ("google")
             228 LOAD_FAST            (domain)
             230 LOAD_ATTR            (NULL|self + lower)
             250 CALL                 0
             258 CONTAINS_OP          (in)
             260 POP_JUMP_IF_FALSE    (to 268)

 74:         262 LOAD_CONST           ("https://www.google.com")
             264 STORE_FAST           (req_url)
             266 JUMP_FORWARD         (to 272)

 76:     >>  268 LOAD_CONST           ("https://studio.youtube.com")
             270 STORE_FAST           (req_url)

 79:     >>  272 LOAD_FAST            (name)

 80:         274 LOAD_FAST            (value)

 81:         276 LOAD_FAST            (domain)

 82:         278 LOAD_FAST            (cookie)
             280 LOAD_ATTR            (NULL|self + get)
             300 LOAD_CONST           ("path")
             302 LOAD_CONST           ("/")
             304 CALL                 2

 83:         312 LOAD_FAST            (req_url)

 84:         314 LOAD_GLOBAL          (NULL + bool)
             324 LOAD_FAST            (cookie)
             326 LOAD_ATTR            (NULL|self + get)
             346 LOAD_CONST           ("secure")
             348 LOAD_CONST           (False)
             350 CALL                 2
             358 CALL                 1

 85:         366 LOAD_GLOBAL          (NULL + bool)
             376 LOAD_FAST            (cookie)
             378 LOAD_ATTR            (NULL|self + get)
             398 LOAD_CONST           ("httpOnly")
             400 LOAD_CONST           (False)
             402 CALL                 2
             410 CALL                 1

 78:         418 LOAD_CONST           (('name', 'value', 'domain', 'path', 'url', 'secure', 'httpOnly'))
             420 BUILD_CONST_KEY_MAP  7
             422 STORE_FAST           (cdp_params)

 88:         424 LOAD_FAST            (cookie)
             426 LOAD_ATTR            (NULL|self + get)
             446 LOAD_CONST           ("expirationDate")
             448 CALL                 1
             456 COPY                 1
             458 POP_JUMP_IF_TRUE     (to 494)
             460 POP_TOP
             462 LOAD_FAST            (cookie)
             464 LOAD_ATTR            (NULL|self + get)
             484 LOAD_CONST           ("expiry")
             486 CALL                 1
         >>  494 STORE_FAST           (expires)

 89:         496 LOAD_FAST            (expires)
             498 POP_JUMP_IF_NONE     (to 528)

 90:         500 LOAD_GLOBAL          (NULL + float)
             510 LOAD_FAST            (expires)
             512 CALL                 1
             520 LOAD_FAST            (cdp_params)
             522 LOAD_CONST           ("expires")
             524 STORE_SUBSCR

 92:     >>  528 LOAD_FAST            (cookie)
             530 LOAD_ATTR            (NULL|self + get)
             550 LOAD_CONST           ("sameSite")
             552 LOAD_CONST           ("unspecified")
             554 CALL                 2
             562 STORE_FAST           (raw_ss)

 93:         564 LOAD_GLOBAL          (_SAMESITE_STORAGE_TO_CDP)
             574 LOAD_ATTR            (NULL|self + get)
             594 LOAD_FAST            (raw_ss)
             596 LOAD_ATTR            (NULL|self + lower)
             616 CALL                 0
             624 LOAD_CONST           ("None")
             626 CALL                 2
             634 LOAD_FAST            (cdp_params)
             636 LOAD_CONST           ("sameSite")
             638 STORE_SUBSCR

 95:         642 NOP

 96:         644 LOAD_FAST            (driver)
             646 LOAD_ATTR            (NULL|self + execute_cdp_cmd)
             666 LOAD_CONST           ("Network.setCookie")
             668 LOAD_FAST            (cdp_params)
             670 CALL                 2
             678 POP_TOP
             680 EXTENDED_ARG         (256)
         >>  682 JUMP_BACKWARD        (to 46)

 62:         684 END_FOR

101:         686 LOAD_FAST            (attempted)
             688 RETURN_VALUE
             690 PUSH_EXC_INFO

 97:         692 LOAD_GLOBAL          (Exception)
             702 CHECK_EXC_MATCH
             704 POP_JUMP_IF_FALSE    (to 762)
             706 POP_TOP

 98:         708 LOAD_GLOBAL          (NULL + logger)
             718 LOAD_ATTR            (debug)
             738 LOAD_CONST           ("Failed to inject cookie: ")
             740 LOAD_FAST            (name)
             742 FORMAT_VALUE         0
             744 BUILD_STRING         2
             746 CALL                 1
             754 POP_TOP

 99:         756 POP_EXCEPT
             758 EXTENDED_ARG         (256)
             760 JUMP_BACKWARD        (to 46)

 97:     >>  762 RERAISE              0
             764 COPY                 3
             766 POP_EXCEPT
             768 RERAISE              1

ExceptionTable:
  644 to 678 -> 690 [1]
  690 to 754 -> 764 [2] lasti
  762 to 762 -> 764 [2] lasti
```
