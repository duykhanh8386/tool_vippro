# Static CPython 3.12 disassembly — `channel_scanner.pyc`

Generated with `xdis 6.3.0`; the code object was deserialized but never executed.

```text
# pydisasm version 6.3.0
# CPython Python bytecode 3.12.0 (3531)
#   Disassembled from CPython Python 3.13.13 | packaged by Anaconda, Inc. | (main, Apr 14 2026, 06:12:50) [MSC v.1942 64 bit (AMD64)]
# Timestamp in code: 0 (1970-01-01 07:00:00)
# Source code size mod 2**32: 0 bytes
# Method Name:       <module>
# Filename:          src\channel_scanner.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        4
# Flags:             0x00000000 (0x0)
# First Line:        1
# Constants:
#    0: 0
#    1: None
#    2: ('logger',)
#    3: ('By',)
#    4: ('expected_conditions',)
#    5: ('WebDriverWait',)
#    6: ('channel_store',)
#    7: ('normalize_cookies_for_storage',)
#    8: ('create_driver', 'get_request_payload_from_performance_log')
#    9: <Code311 code object ChannelFetcher at 0x2e1d0132470, file src\channel_scanner.py>, line 17
#   10: 'ChannelFetcher'
# Names:
#    0: hashlib
#    1: json
#    2: re
#    3: time
#    4: requests
#    5: loguru
#    6: logger
#    7: selenium.webdriver.common.by
#    8: By
#    9: selenium.webdriver.support
#   10: expected_conditions
#   11: EC
#   12: selenium.webdriver.support.ui
#   13: WebDriverWait
#   14: src.channel_store
#   15: channel_store
#   16: src.cookie_utils
#   17: normalize_cookies_for_storage
#   18: src.utils
#   19: create_driver
#   20: get_request_payload_from_performance_log
#   21: ChannelFetcher
#   22: channel_fetcher

  0:           0 RESUME               0

  1:           2 LOAD_CONST           (0)
               4 LOAD_CONST           (None)
               6 IMPORT_NAME          (hashlib)
               8 STORE_NAME           (hashlib)

  2:          10 LOAD_CONST           (0)
              12 LOAD_CONST           (None)
              14 IMPORT_NAME          (json)
              16 STORE_NAME           (json)

  3:          18 LOAD_CONST           (0)
              20 LOAD_CONST           (None)
              22 IMPORT_NAME          (re)
              24 STORE_NAME           (re)

  4:          26 LOAD_CONST           (0)
              28 LOAD_CONST           (None)
              30 IMPORT_NAME          (time)
              32 STORE_NAME           (time)

  6:          34 LOAD_CONST           (0)
              36 LOAD_CONST           (None)
              38 IMPORT_NAME          (requests)
              40 STORE_NAME           (requests)

  7:          42 LOAD_CONST           (0)
              44 LOAD_CONST           (('logger',))
              46 IMPORT_NAME          (loguru)
              48 IMPORT_FROM          (logger)
              50 STORE_NAME           (logger)
              52 POP_TOP

  8:          54 LOAD_CONST           (0)
              56 LOAD_CONST           (('By',))
              58 IMPORT_NAME          (selenium.webdriver.common.by)
              60 IMPORT_FROM          (By)
              62 STORE_NAME           (By)
              64 POP_TOP

  9:          66 LOAD_CONST           (0)
              68 LOAD_CONST           (('expected_conditions',))
              70 IMPORT_NAME          (selenium.webdriver.support)
              72 IMPORT_FROM          (expected_conditions)
              74 STORE_NAME           (EC)
              76 POP_TOP

 10:          78 LOAD_CONST           (0)
              80 LOAD_CONST           (('WebDriverWait',))
              82 IMPORT_NAME          (selenium.webdriver.support.ui)
              84 IMPORT_FROM          (WebDriverWait)
              86 STORE_NAME           (WebDriverWait)
              88 POP_TOP

 12:          90 LOAD_CONST           (0)
              92 LOAD_CONST           (('channel_store',))
              94 IMPORT_NAME          (src.channel_store)
              96 IMPORT_FROM          (channel_store)
              98 STORE_NAME           (channel_store)
             100 POP_TOP

 13:         102 LOAD_CONST           (0)
             104 LOAD_CONST           (('normalize_cookies_for_storage',))
             106 IMPORT_NAME          (src.cookie_utils)
             108 IMPORT_FROM          (normalize_cookies_for_storage)
             110 STORE_NAME           (normalize_cookies_for_storage)
             112 POP_TOP

 14:         114 LOAD_CONST           (0)
             116 LOAD_CONST           (('create_driver', 'get_request_payload_from_performance_log'))
             118 IMPORT_NAME          (src.utils)
             120 IMPORT_FROM          (create_driver)
             122 STORE_NAME           (create_driver)
             124 IMPORT_FROM          (get_request_payload_from_performance_log)
             126 STORE_NAME           (get_request_payload_from_performance_log)
             128 POP_TOP

 17:         130 PUSH_NULL
             132 LOAD_BUILD_CLASS
             134 LOAD_CONST           (<Code311 code object ChannelFetcher at 0x2e1d0132470, file src\channel_scanner.py>, line 17)
             136 MAKE_FUNCTION        (No arguments)
             138 LOAD_CONST           ("ChannelFetcher")
             140 CALL                 2
             148 STORE_NAME           (ChannelFetcher)

219:         150 PUSH_NULL
             152 LOAD_NAME            (ChannelFetcher)
             154 CALL                 0
             162 STORE_NAME           (channel_fetcher)
             164 RETURN_CONST         (None)


# Method Name:       ChannelFetcher
# Filename:          src\channel_scanner.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        4
# Flags:             0x00000000 (0x0)
# First Line:        17
# Constants:
#    0: 'ChannelFetcher'
#    1: 'https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fwww.youtube.com%2Fsignin%3Faction_handle_signin%3Dtrue%26app%3Ddesktop%26hl%3Den%26next%3Dhttps%253A%252F%252Fstudio.youtube.com%252F%26feature%3Dredirect_login&hl=en&ifkv=AcMMx-d4fvrPkXxfIg8o7ivlOtaYz55VcK2EWUx6zTt7iSx9wGyBkzr1KUqgfL5C0oMsTMQ6Zd0U7g&passive=true&service=youtube&uilel=3&flowName=GlifWebSignIn&flowEntry=ServiceLogin&dsh=S-1405244270%3A1731600052448568&ddm=1'
#    2: "//input[@name='identifier' and @id='identifierId']"
#    3: "//input[@type='password' and @name='Passwd']"
#    4: "//span[(text()='Next') or (text()='Tiếp theo')]"
#    5: "//ytd-account-item-renderer[@class='style-scope ytd-account-item-section-renderer']"
#    6: "//ytd-account-item-renderer[@class='style-scope ytd-account-item-section-renderer' and @enable-ring-for-active-account]/following-sibling::ytd-account-item-renderer[1]"
#    7: "//*[@id='avatar-btn'] | //ytcp-topbar-menu-button-renderer[contains(concat(' ', normalize-space(@class), ' '), ' ytcpAppHeaderAccountButton ')]"
#    8: "//ytd-compact-link-renderer[@class='style-scope yt-multi-page-menu-section-renderer' and @has-secondary]"
#    9: "//div[@class='sublabel style-scope ytcp-topbar-menu-button-renderer']"
#   10: <Code311 code object __init__ at 0x2e1d0142270, file src\channel_scanner.py>, line 33
#   11: <Code311 code object run at 0x2e1d01a8550, file src\channel_scanner.py>, line 36
#   12: 'email'
#   13: 'password'
#   14: <Code311 code object _login at 0x2e1d01a87d0, file src\channel_scanner.py>, line 99
#   15: <Code311 code object _get_channel_info at 0x2e1cfce3950, file src\channel_scanner.py>, line 119
#   16: <Code311 code object _extract_channel_id at 0x2e1cfce3a80, file src\channel_scanner.py>, line 183
#   17: <Code311 code object _extract_datasync_id at 0x2e1d0174710, file src\channel_scanner.py>, line 188
#   18: <Code311 code object _generate_sapisidhash_header at 0x2e1d0132360, file src\channel_scanner.py>, line 203
#   19: <Code311 code object _get_role_type at 0x2e1d0132250, file src\channel_scanner.py>, line 211
#   20: None
#   21: ('https://studio.youtube.com',)
# Names:
#    0: __name__
#    1: __module__
#    2: __qualname__
#    3: LOGIN_URL
#    4: EMAIL_XPATH
#    5: PASSWORD_XPATH
#    6: NEXT_BUTTON_XPATH
#    7: CHANNEL_SELECTION_XPATH
#    8: NEXT_CHANNEL_SELECTION_XPATH
#    9: AVATAR_BUTTON_XPATH
#   10: SWTICH_ACCOUNT_BUTTON_XPATH
#   11: ROLE_MANAGER_XPATH
#   12: __init__
#   13: run
#   14: str
#   15: _login
#   16: _get_channel_info
#   17: staticmethod
#   18: _extract_channel_id
#   19: _extract_datasync_id
#   20: _generate_sapisidhash_header
#   21: _get_role_type

 17:           0 RESUME               0
               2 LOAD_NAME            (__name__)
               4 STORE_NAME           (__module__)
               6 LOAD_CONST           ("ChannelFetcher")
               8 STORE_NAME           (__qualname__)

 18:          10 LOAD_CONST           ("https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fwww.youtube.com%2Fsignin%3Faction_handle_signin%3Dtrue%26app%3Ddesktop%26hl%3Den%26next%3Dhttps%253A%252F%252Fstudio.youtube.com%252F%26feature%3Dredirect_login&hl=en&ifkv=AcMMx-d4fvrPkXxfIg8o7ivlOtaYz55VcK2EWUx6zTt7iSx9wGyBkzr1KUqgfL5C0oMsTMQ6Zd0U7g&passive=true&service=youtube&uilel=3&flowName=GlifWebSignIn&flowEntry=ServiceLogin&dsh=S-1405244270%3A1731600052448568&ddm=1")
              12 STORE_NAME           (LOGIN_URL)

 19:          14 LOAD_CONST           ("//input[@name='identifier' and @id='identifierId']")
              16 STORE_NAME           (EMAIL_XPATH)

 20:          18 LOAD_CONST           ("//input[@type='password' and @name='Passwd']")
              20 STORE_NAME           (PASSWORD_XPATH)

 21:          22 LOAD_CONST           ("//span[(text()='Next') or (text()='Tiếp theo')]")
              24 STORE_NAME           (NEXT_BUTTON_XPATH)

 22:          26 LOAD_CONST           ("//ytd-account-item-renderer[@class='style-scope ytd-account-item-section-renderer']")
              28 STORE_NAME           (CHANNEL_SELECTION_XPATH)

 23:          30 LOAD_CONST           ("//ytd-account-item-renderer[@class='style-scope ytd-account-item-section-renderer' and @enable-ring-for-active-account]/following-sibling::ytd-account-item-renderer[1]")
              32 STORE_NAME           (NEXT_CHANNEL_SELECTION_XPATH)

 26:          34 LOAD_CONST           ("//*[@id='avatar-btn'] | //ytcp-topbar-menu-button-renderer[contains(concat(' ', normalize-space(@class), ' '), ' ytcpAppHeaderAccountButton ')]")
              36 STORE_NAME           (AVATAR_BUTTON_XPATH)

 27:          38 LOAD_CONST           ("//ytd-compact-link-renderer[@class='style-scope yt-multi-page-menu-section-renderer' and @has-secondary]")
              40 STORE_NAME           (SWTICH_ACCOUNT_BUTTON_XPATH)

 30:          42 LOAD_CONST           ("//div[@class='sublabel style-scope ytcp-topbar-menu-button-renderer']")

 29:          44 STORE_NAME           (ROLE_MANAGER_XPATH)

 33:          46 LOAD_CONST           (<Code311 code object __init__ at 0x2e1d0142270, file src\channel_scanner.py>, line 33)
              48 MAKE_FUNCTION        (No arguments)
              50 STORE_NAME           (__init__)

 36:          52 LOAD_CONST           (<Code311 code object run at 0x2e1d01a8550, file src\channel_scanner.py>, line 36)
              54 MAKE_FUNCTION        (No arguments)
              56 STORE_NAME           (run)

 99:          58 LOAD_CONST           ("email")
              60 LOAD_NAME            (str)
              62 LOAD_CONST           ("password")
              64 LOAD_NAME            (str)
              66 BUILD_TUPLE          4
              68 LOAD_CONST           (<Code311 code object _login at 0x2e1d01a87d0, file src\channel_scanner.py>, line 99)
              70 MAKE_FUNCTION        (annotation)
              72 STORE_NAME           (_login)

119:          74 LOAD_CONST           (<Code311 code object _get_channel_info at 0x2e1cfce3950, file src\channel_scanner.py>, line 119)
              76 MAKE_FUNCTION        (No arguments)
              78 STORE_NAME           (_get_channel_info)

183:          80 LOAD_NAME            (staticmethod)

184:          82 LOAD_CONST           (<Code311 code object _extract_channel_id at 0x2e1cfce3a80, file src\channel_scanner.py>, line 183)
              84 MAKE_FUNCTION        (No arguments)

183:          86 CALL                 0

184:          94 STORE_NAME           (_extract_channel_id)

188:          96 LOAD_NAME            (staticmethod)

189:          98 LOAD_CONST           (<Code311 code object _extract_datasync_id at 0x2e1d0174710, file src\channel_scanner.py>, line 188)
             100 MAKE_FUNCTION        (No arguments)

188:         102 CALL                 0

189:         110 STORE_NAME           (_extract_datasync_id)

203:         112 LOAD_NAME            (staticmethod)

204:         114 LOAD_CONST           (('https://studio.youtube.com',))
             116 LOAD_CONST           (<Code311 code object _generate_sapisidhash_header at 0x2e1d0132360, file src\channel_scanner.py>, line 203)
             118 MAKE_FUNCTION        (default)

203:         120 CALL                 0

204:         128 STORE_NAME           (_generate_sapisidhash_header)

211:         130 LOAD_NAME            (staticmethod)

212:         132 LOAD_CONST           (<Code311 code object _get_role_type at 0x2e1d0132250, file src\channel_scanner.py>, line 211)
             134 MAKE_FUNCTION        (No arguments)

211:         136 CALL                 0

212:         144 STORE_NAME           (_get_role_type)
             146 RETURN_CONST         (None)


# Method Name:       __init__
# Filename:          src\channel_scanner.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  1
# Stack size:        2
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        33
# Constants:
#    0: None
# Names:
#    0: driver
# Varnames:
#	self
# Positional arguments:
#	self

 33:           0 RESUME               0

 34:           2 LOAD_CONST           (None)
               4 LOAD_FAST            (self)
               6 STORE_ATTR           (driver)
              16 RETURN_CONST         (None)


# Method Name:       run
# Filename:          src\channel_scanner.py
# Argument count:    3
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  8
# Stack size:        6
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        36
# Constants:
#    0: None
#    1: '*** Fetching channel info ***'
#    2: True
#    3: ('enable_performance_log',)
#    4: 60
#    5: 5
#    6: 1
#    7: 0
#    8: 'channel-appeal'
#    9: 'Kênh đã bị xóa!!!'
#   10: 10
# Names:
#    0: logger
#    1: info
#    2: create_driver
#    3: driver
#    4: _login
#    5: WebDriverWait
#    6: until
#    7: EC
#    8: element_to_be_clickable
#    9: By
#   10: XPATH
#   11: CHANNEL_SELECTION_XPATH
#   12: click
#   13: _get_channel_info
#   14: find_element
#   15: AVATAR_BUTTON_XPATH
#   16: SWTICH_ACCOUNT_BUTTON_XPATH
#   17: time
#   18: sleep
#   19: NEXT_CHANNEL_SELECTION_XPATH
#   20: find_elements
#   21: len
#   22: current_url
#   23: error
#   24: quit
# Varnames:
#	self, email, password, channel_selection_button, account_menu_btn, switch_acocunt_button, next_account_button, next
# Positional arguments:
#	self, email, password
# Local variables:
#    3: channel_selection_button
#    4: account_menu_btn
#    5: switch_acocunt_button
#    6: next_account_button
#    7: next

 36:           0 RESUME               0

 37:           2 LOAD_GLOBAL          (NULL + logger)
              12 LOAD_ATTR            (info)
              32 LOAD_CONST           ("*** Fetching channel info ***")
              34 CALL                 1
              42 POP_TOP

 39:          44 LOAD_GLOBAL          (NULL + create_driver)
              54 LOAD_CONST           (True)
              56 KW_NAMES             (('enable_performance_log',))
              58 CALL                 1
              66 LOAD_FAST            (self)
              68 STORE_ATTR           (driver)

 40:          78 LOAD_FAST            (self)
              80 LOAD_ATTR            (NULL|self + _login)
             100 LOAD_FAST            (email)
             102 LOAD_FAST            (password)
             104 CALL                 2
             112 POP_TOP

 42:         114 LOAD_GLOBAL          (NULL + WebDriverWait)
             124 LOAD_FAST            (self)
             126 LOAD_ATTR            (driver)
             146 LOAD_CONST           (60)
             148 CALL                 2
             156 LOAD_ATTR            (NULL|self + until)

 43:         176 LOAD_GLOBAL          (NULL + EC)
             186 LOAD_ATTR            (element_to_be_clickable)
             206 LOAD_GLOBAL          (By)
             216 LOAD_ATTR            (XPATH)
             236 LOAD_FAST            (self)
             238 LOAD_ATTR            (CHANNEL_SELECTION_XPATH)
             258 BUILD_TUPLE          2
             260 CALL                 1

 42:         268 CALL                 1
             276 STORE_FAST           (channel_selection_button)

 46:         278 LOAD_FAST            (channel_selection_button)
             280 LOAD_ATTR            (NULL|self + click)
             300 CALL                 0
             308 POP_TOP

 47:         310 LOAD_FAST            (self)
             312 LOAD_ATTR            (NULL|self + _get_channel_info)
             332 CALL                 0
             340 POP_TOP

 49:         342 LOAD_FAST            (self)
             344 LOAD_ATTR            (driver)
             364 LOAD_ATTR            (NULL|self + find_element)
             384 LOAD_GLOBAL          (By)
             394 LOAD_ATTR            (XPATH)
             414 LOAD_FAST            (self)
             416 LOAD_ATTR            (AVATAR_BUTTON_XPATH)
             436 CALL                 2
             444 STORE_FAST           (account_menu_btn)

 50:         446 LOAD_FAST            (account_menu_btn)
             448 LOAD_ATTR            (NULL|self + click)
             468 CALL                 0
             476 POP_TOP

 52:         478 LOAD_GLOBAL          (NULL + WebDriverWait)
             488 LOAD_FAST            (self)
             490 LOAD_ATTR            (driver)
             510 LOAD_CONST           (5)
             512 CALL                 2
             520 LOAD_ATTR            (NULL|self + until)

 53:         540 LOAD_GLOBAL          (NULL + EC)
             550 LOAD_ATTR            (element_to_be_clickable)
             570 LOAD_GLOBAL          (By)
             580 LOAD_ATTR            (XPATH)
             600 LOAD_FAST            (self)
             602 LOAD_ATTR            (SWTICH_ACCOUNT_BUTTON_XPATH)
             622 BUILD_TUPLE          2
             624 CALL                 1

 52:         632 CALL                 1
             640 STORE_FAST           (switch_acocunt_button)

 55:         642 LOAD_FAST            (switch_acocunt_button)
             644 LOAD_ATTR            (NULL|self + click)
             664 CALL                 0
             672 POP_TOP

 56:         674 LOAD_GLOBAL          (NULL + time)
             684 LOAD_ATTR            (sleep)
             704 LOAD_CONST           (1)
             706 CALL                 1
             714 POP_TOP

 57:         716 LOAD_GLOBAL          (NULL + WebDriverWait)
             726 LOAD_FAST            (self)
             728 LOAD_ATTR            (driver)
             748 LOAD_CONST           (5)
             750 CALL                 2
             758 LOAD_ATTR            (NULL|self + until)

 58:         778 LOAD_GLOBAL          (NULL + EC)
             788 LOAD_ATTR            (element_to_be_clickable)
             808 LOAD_GLOBAL          (By)
             818 LOAD_ATTR            (XPATH)
             838 LOAD_FAST            (self)
             840 LOAD_ATTR            (NEXT_CHANNEL_SELECTION_XPATH)
             860 BUILD_TUPLE          2
             862 CALL                 1

 57:         870 CALL                 1
             878 POP_TOP

 60:         880 LOAD_FAST            (self)
             882 LOAD_ATTR            (driver)
             902 LOAD_ATTR            (NULL|self + find_elements)

 61:         922 LOAD_GLOBAL          (By)
             932 LOAD_ATTR            (XPATH)
             952 LOAD_FAST            (self)
             954 LOAD_ATTR            (NEXT_CHANNEL_SELECTION_XPATH)

 60:         974 CALL                 2
             982 STORE_FAST           (next_account_button)

 63:         984 LOAD_GLOBAL          (NULL + len)
             994 LOAD_FAST            (next_account_button)
             996 CALL                 1
            1004 LOAD_CONST           (0)
            1006 COMPARE_OP           (>)
            1010 EXTENDED_ARG         (256)
            1012 POP_JUMP_IF_FALSE    (to 2030)

 64:        1014 LOAD_GLOBAL          (NULL + WebDriverWait)
            1024 LOAD_FAST            (self)
            1026 LOAD_ATTR            (driver)
            1046 LOAD_CONST           (5)
            1048 CALL                 2
            1056 LOAD_ATTR            (NULL|self + until)

 65:        1076 LOAD_GLOBAL          (NULL + EC)
            1086 LOAD_ATTR            (element_to_be_clickable)

 66:        1106 LOAD_GLOBAL          (By)
            1116 LOAD_ATTR            (XPATH)
            1136 LOAD_FAST            (self)
            1138 LOAD_ATTR            (NEXT_CHANNEL_SELECTION_XPATH)
            1158 BUILD_TUPLE          2

 65:        1160 CALL                 1

 64:        1168 CALL                 1
            1176 STORE_FAST           (next)

 69:        1178 LOAD_FAST            (next)
            1180 LOAD_ATTR            (NULL|self + click)
            1200 CALL                 0
            1208 POP_TOP

 70:        1210 LOAD_CONST           ("channel-appeal")
            1212 LOAD_FAST            (self)
            1214 LOAD_ATTR            (driver)
            1234 LOAD_ATTR            (current_url)
            1254 CONTAINS_OP          (in)
            1256 POP_JUMP_IF_FALSE    (to 1302)

 71:        1258 LOAD_GLOBAL          (NULL + logger)
            1268 LOAD_ATTR            (error)
            1288 LOAD_CONST           ("Kênh đã bị xóa!!!")
            1290 CALL                 1
            1298 POP_TOP
            1300 JUMP_FORWARD         (to 1336)

 73:     >> 1302 NOP

 74:        1304 LOAD_FAST            (self)
            1306 LOAD_ATTR            (NULL|self + _get_channel_info)
            1326 CALL                 0
            1334 POP_TOP

 77:     >> 1336 LOAD_GLOBAL          (NULL + WebDriverWait)
            1346 LOAD_FAST            (self)
            1348 LOAD_ATTR            (driver)
            1368 LOAD_CONST           (10)
            1370 CALL                 2
            1378 LOAD_ATTR            (NULL|self + until)

 78:        1398 LOAD_GLOBAL          (NULL + EC)
            1408 LOAD_ATTR            (element_to_be_clickable)
            1428 LOAD_GLOBAL          (By)
            1438 LOAD_ATTR            (XPATH)
            1458 LOAD_FAST            (self)
            1460 LOAD_ATTR            (AVATAR_BUTTON_XPATH)
            1480 BUILD_TUPLE          2
            1482 CALL                 1

 77:        1490 CALL                 1
            1498 STORE_FAST           (account_menu_btn)

 80:        1500 LOAD_FAST            (account_menu_btn)
            1502 LOAD_ATTR            (NULL|self + click)
            1522 CALL                 0
            1530 POP_TOP

 81:        1532 LOAD_GLOBAL          (NULL + WebDriverWait)
            1542 LOAD_FAST            (self)
            1544 LOAD_ATTR            (driver)
            1564 LOAD_CONST           (5)
            1566 CALL                 2
            1574 LOAD_ATTR            (NULL|self + until)

 82:        1594 LOAD_GLOBAL          (NULL + EC)
            1604 LOAD_ATTR            (element_to_be_clickable)
            1624 LOAD_GLOBAL          (By)
            1634 LOAD_ATTR            (XPATH)
            1654 LOAD_FAST            (self)
            1656 LOAD_ATTR            (SWTICH_ACCOUNT_BUTTON_XPATH)
            1676 BUILD_TUPLE          2
            1678 CALL                 1

 81:        1686 CALL                 1
            1694 STORE_FAST           (switch_acocunt_button)

 84:        1696 LOAD_FAST            (switch_acocunt_button)
            1698 LOAD_ATTR            (NULL|self + click)
            1718 CALL                 0
            1726 POP_TOP

 85:        1728 NOP

 86:        1730 LOAD_GLOBAL          (NULL + WebDriverWait)
            1740 LOAD_FAST            (self)
            1742 LOAD_ATTR            (driver)
            1762 LOAD_CONST           (5)
            1764 CALL                 2
            1772 LOAD_ATTR            (NULL|self + until)

 87:        1792 LOAD_GLOBAL          (NULL + EC)
            1802 LOAD_ATTR            (element_to_be_clickable)

 88:        1822 LOAD_GLOBAL          (By)
            1832 LOAD_ATTR            (XPATH)
            1852 LOAD_FAST            (self)
            1854 LOAD_ATTR            (NEXT_CHANNEL_SELECTION_XPATH)
            1874 BUILD_TUPLE          2

 87:        1876 CALL                 1

 86:        1884 CALL                 1
            1892 POP_TOP

 93:        1894 LOAD_FAST            (self)
            1896 LOAD_ATTR            (driver)
            1916 LOAD_ATTR            (NULL|self + find_elements)

 94:        1936 LOAD_GLOBAL          (By)
            1946 LOAD_ATTR            (XPATH)
            1966 LOAD_FAST            (self)
            1968 LOAD_ATTR            (NEXT_CHANNEL_SELECTION_XPATH)

 93:        1988 CALL                 2
            1996 STORE_FAST           (next_account_button)

 63:        1998 LOAD_GLOBAL          (NULL + len)
            2008 LOAD_FAST            (next_account_button)
            2010 CALL                 1
            2018 LOAD_CONST           (0)
            2020 COMPARE_OP           (>)
            2024 POP_JUMP_IF_FALSE    (to 2030)
            2026 EXTENDED_ARG         (256)
            2028 JUMP_BACKWARD        (to 1014)

 97:     >> 2030 LOAD_FAST            (self)
            2032 LOAD_ATTR            (driver)
            2052 LOAD_ATTR            (NULL|self + quit)
            2072 CALL                 0
            2080 POP_TOP
            2082 RETURN_CONST         (None)
            2084 PUSH_EXC_INFO

 75:        2086 POP_TOP

 76:        2088 LOAD_GLOBAL          (NULL + logger)
            2098 LOAD_ATTR            (error)
            2118 LOAD_CONST           ("Kênh đã bị xóa!!!")
            2120 CALL                 1
            2128 POP_TOP
            2130 POP_EXCEPT
            2132 EXTENDED_ARG         (256)
            2134 JUMP_BACKWARD        (to 1336)
            2136 COPY                 3
            2138 POP_EXCEPT
            2140 RERAISE              1
            2142 PUSH_EXC_INFO

 91:        2144 POP_TOP

 92:        2146 POP_EXCEPT
            2148 JUMP_BACKWARD        (to 2030)
            2150 COPY                 3
            2152 POP_EXCEPT
            2154 RERAISE              1

ExceptionTable:
  1304 to 1334 -> 2084 [0]
  1730 to 1892 -> 2142 [0]
  2084 to 2128 -> 2136 [1] lasti
  2142 to 2144 -> 2150 [1] lasti

# Method Name:       _login
# Filename:          src\channel_scanner.py
# Argument count:    3
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  7
# Stack size:        6
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        99
# Constants:
#    0: None
#    1: 0.05
#    2: 10
# Names:
#    0: driver
#    1: get
#    2: LOGIN_URL
#    3: find_element
#    4: By
#    5: XPATH
#    6: EMAIL_XPATH
#    7: send_keys
#    8: time
#    9: sleep
#   10: NEXT_BUTTON_XPATH
#   11: click
#   12: WebDriverWait
#   13: until
#   14: EC
#   15: element_to_be_clickable
#   16: PASSWORD_XPATH
# Varnames:
#	self, email, password, email_input, char, next_button, password_input
# Positional arguments:
#	self, email, password
# Local variables:
#    3: email_input
#    4: char
#    5: next_button
#    6: password_input

 99:           0 RESUME               0

100:           2 LOAD_FAST            (self)
               4 LOAD_ATTR            (driver)
              24 LOAD_ATTR            (NULL|self + get)
              44 LOAD_FAST            (self)
              46 LOAD_ATTR            (LOGIN_URL)
              66 CALL                 1
              74 POP_TOP

101:          76 LOAD_FAST            (self)
              78 LOAD_ATTR            (driver)
              98 LOAD_ATTR            (NULL|self + find_element)
             118 LOAD_GLOBAL          (By)
             128 LOAD_ATTR            (XPATH)
             148 LOAD_FAST            (self)
             150 LOAD_ATTR            (EMAIL_XPATH)
             170 CALL                 2
             178 STORE_FAST           (email_input)

102:         180 LOAD_FAST            (email)
             182 GET_ITER
             184 FOR_ITER             (to 268)
             188 STORE_FAST           (char)

103:         190 LOAD_FAST            (email_input)
             192 LOAD_ATTR            (NULL|self + send_keys)
             212 LOAD_FAST            (char)
             214 CALL                 1
             222 POP_TOP

104:         224 LOAD_GLOBAL          (NULL + time)
             234 LOAD_ATTR            (sleep)
             254 LOAD_CONST           (0.05)
             256 CALL                 1
             264 POP_TOP
         >>  266 JUMP_BACKWARD        (to 184)

102:         268 END_FOR

106:         270 LOAD_FAST            (self)
             272 LOAD_ATTR            (driver)
             292 LOAD_ATTR            (NULL|self + find_element)
             312 LOAD_GLOBAL          (By)
             322 LOAD_ATTR            (XPATH)
             342 LOAD_FAST            (self)
             344 LOAD_ATTR            (NEXT_BUTTON_XPATH)
             364 CALL                 2
             372 STORE_FAST           (next_button)

107:         374 LOAD_FAST            (next_button)
             376 LOAD_ATTR            (NULL|self + click)
             396 CALL                 0
             404 POP_TOP

109:         406 LOAD_GLOBAL          (NULL + WebDriverWait)
             416 LOAD_FAST            (self)
             418 LOAD_ATTR            (driver)
             438 LOAD_CONST           (10)
             440 CALL                 2
             448 LOAD_ATTR            (NULL|self + until)

110:         468 LOAD_GLOBAL          (NULL + EC)
             478 LOAD_ATTR            (element_to_be_clickable)
             498 LOAD_GLOBAL          (By)
             508 LOAD_ATTR            (XPATH)
             528 LOAD_FAST            (self)
             530 LOAD_ATTR            (PASSWORD_XPATH)
             550 BUILD_TUPLE          2
             552 CALL                 1

109:         560 CALL                 1
             568 STORE_FAST           (password_input)

112:         570 LOAD_FAST            (password)
             572 GET_ITER
             574 FOR_ITER             (to 658)
             578 STORE_FAST           (char)

113:         580 LOAD_FAST            (password_input)
             582 LOAD_ATTR            (NULL|self + send_keys)
             602 LOAD_FAST            (char)
             604 CALL                 1
             612 POP_TOP

114:         614 LOAD_GLOBAL          (NULL + time)
             624 LOAD_ATTR            (sleep)
             644 LOAD_CONST           (0.05)
             646 CALL                 1
             654 POP_TOP
         >>  656 JUMP_BACKWARD        (to 574)

112:         658 END_FOR

116:         660 LOAD_FAST            (self)
             662 LOAD_ATTR            (driver)
             682 LOAD_ATTR            (NULL|self + find_element)
             702 LOAD_GLOBAL          (By)
             712 LOAD_ATTR            (XPATH)
             732 LOAD_FAST            (self)
             734 LOAD_ATTR            (NEXT_BUTTON_XPATH)
             754 CALL                 2
             762 STORE_FAST           (next_button)

117:         764 LOAD_FAST            (next_button)
             766 LOAD_ATTR            (NULL|self + click)
             786 CALL                 0
             794 POP_TOP
             796 RETURN_CONST         (None)


# Method Name:       _get_channel_info
# Filename:          src\channel_scanner.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  24
# Stack size:        12
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        119
# Constants:
#    0: None
#    1: "//img[@class='thumbnail image-thumbnail style-scope ytcp-navigation-drawer']"
#    2: 30
#    3: 'xpath'
#    4: 'src'
#    5: 'alt'
#    6: '*** Channel info fetched successfully: '
#    7: ' ***'
#    8: 'name'
#    9: 'SAPISID'
#   10: 'value'
#   11: '/analytics/tab-overview/period-default'
#   12: 'youtubei/v1/att/esr?alt=json'
#   13: 20.0
#   14: ('timeout',)
#   15: 'challenge'
#   16: 'botguardResponse'
#   17: 'https://studio.youtube.com/channel/'
#   18: '; '
#   19: '='
#   20: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
#   21: ('User-Agent', 'Cookie')
#   22: ('headers',)
#   23: ('id', 'name', 'img_src', 'delegated_session_id', 'sapisidhash', 'role', 'challenge', 'botguardResponse', 'cookies')
#   24: ('id', 'name', 'img_src', 'cookies')
# Names:
#    0: WebDriverWait
#    1: driver
#    2: until
#    3: EC
#    4: element_to_be_clickable
#    5: By
#    6: XPATH
#    7: _extract_channel_id
#    8: current_url
#    9: find_element
#   10: get_attribute
#   11: get_cookies
#   12: normalize_cookies_for_storage
#   13: logger
#   14: info
#   15: _generate_sapisidhash_header
#   16: get
#   17: get_request_payload_from_performance_log
#   18: json
#   19: loads
#   20: TimeoutError
#   21: error
#   22: str
#   23: join
#   24: requests
#   25: _extract_datasync_id
#   26: text
#   27: _get_role_type
#   28: channel_store
#   29: upsert_channel
#   30: dict
# Varnames:
#	self, img_element_xapth, id, img_element, img_src, name, cookies_raw, cookies, sapisidhash, cookie, sapisid, current_url, next_url, payload, payload_json, challenge, botguardResponse, e, url, cookie_string, header, res, delegated_session_id, role
# Positional arguments:
#	self
# Local variables:
#    1: img_element_xapth
#    2: id
#    3: img_element
#    4: img_src
#    5: name
#    6: cookies_raw
#    7: cookies
#    8: sapisidhash
#    9: cookie
#   10: sapisid
#   11: current_url
#   12: next_url
#   13: payload
#   14: payload_json
#   15: challenge
#   16: botguardResponse
#   17: e
#   18: url
#   19: cookie_string
#   20: header
#   21: res
#   22: delegated_session_id
#   23: role

119:           0 RESUME               0

120:           2 LOAD_CONST           ("//img[@class='thumbnail image-thumbnail style-scope ytcp-navigation-drawer']")
               4 STORE_FAST           (img_element_xapth)

121:           6 LOAD_GLOBAL          (NULL + WebDriverWait)
              16 LOAD_FAST            (self)
              18 LOAD_ATTR            (driver)
              38 LOAD_CONST           (30)
              40 CALL                 2
              48 LOAD_ATTR            (NULL|self + until)

122:          68 LOAD_GLOBAL          (NULL + EC)
              78 LOAD_ATTR            (element_to_be_clickable)
              98 LOAD_GLOBAL          (By)
             108 LOAD_ATTR            (XPATH)
             128 LOAD_FAST            (img_element_xapth)
             130 BUILD_TUPLE          2
             132 CALL                 1

121:         140 CALL                 1
             148 POP_TOP

124:         150 LOAD_FAST            (self)
             152 LOAD_ATTR            (NULL|self + _extract_channel_id)
             172 LOAD_FAST            (self)
             174 LOAD_ATTR            (driver)
             194 LOAD_ATTR            (current_url)
             214 CALL                 1
             222 STORE_FAST           (id)

126:         224 LOAD_FAST            (self)
             226 LOAD_ATTR            (driver)
             246 LOAD_ATTR            (NULL|self + find_element)
             266 LOAD_CONST           ("xpath")
             268 LOAD_FAST            (img_element_xapth)
             270 CALL                 2
             278 STORE_FAST           (img_element)

127:         280 LOAD_FAST            (img_element)
             282 LOAD_ATTR            (NULL|self + get_attribute)
             302 LOAD_CONST           ("src")
             304 CALL                 1
             312 STORE_FAST           (img_src)

128:         314 LOAD_FAST            (img_element)
             316 LOAD_ATTR            (NULL|self + get_attribute)
             336 LOAD_CONST           ("alt")
             338 CALL                 1
             346 STORE_FAST           (name)

129:         348 LOAD_FAST            (self)
             350 LOAD_ATTR            (driver)
             370 LOAD_ATTR            (NULL|self + get_cookies)
             390 CALL                 0
             398 STORE_FAST           (cookies_raw)

130:         400 LOAD_GLOBAL          (NULL + normalize_cookies_for_storage)
             410 LOAD_FAST            (cookies_raw)
             412 CALL                 1
             420 STORE_FAST           (cookies)

131:         422 LOAD_GLOBAL          (NULL + logger)
             432 LOAD_ATTR            (info)
             452 LOAD_CONST           ("*** Channel info fetched successfully: ")
             454 LOAD_FAST            (name)
             456 FORMAT_VALUE         0
             458 LOAD_CONST           (" ***")
             460 BUILD_STRING         3
             462 CALL                 1
             470 POP_TOP

133:         472 LOAD_CONST           (None)
             474 STORE_FAST           (sapisidhash)

134:         476 LOAD_FAST            (cookies)
             478 GET_ITER
             480 FOR_ITER             (to 550)
             484 STORE_FAST           (cookie)

135:         486 LOAD_FAST            (cookie)
             488 LOAD_CONST           ("name")
             490 BINARY_SUBSCR
             494 LOAD_CONST           ("SAPISID")
             496 COMPARE_OP           (==)
             500 POP_JUMP_IF_TRUE     (to 504)
             502 JUMP_BACKWARD        (to 480)

136:     >>  504 LOAD_FAST            (cookie)
             506 LOAD_CONST           ("value")
             508 BINARY_SUBSCR
             512 STORE_FAST           (sapisid)

137:         514 LOAD_FAST            (self)
             516 LOAD_ATTR            (NULL|self + _generate_sapisidhash_header)
             536 LOAD_FAST            (sapisid)
             538 CALL                 1
             546 STORE_FAST           (sapisidhash)
         >>  548 JUMP_BACKWARD        (to 480)

134:         550 END_FOR

139:         552 LOAD_FAST            (self)
             554 LOAD_ATTR            (driver)
             574 LOAD_ATTR            (current_url)
             594 STORE_FAST           (current_url)

140:         596 LOAD_FAST            (current_url)
             598 LOAD_CONST           ("/analytics/tab-overview/period-default")
             600 BINARY_OP            (+)
             604 STORE_FAST           (next_url)

141:         606 LOAD_FAST            (self)
             608 LOAD_ATTR            (driver)
             628 LOAD_ATTR            (NULL|self + get)
             648 LOAD_FAST            (next_url)
             650 CALL                 1
             658 POP_TOP

143:         660 NOP

144:         662 LOAD_GLOBAL          (NULL + get_request_payload_from_performance_log)

145:         672 LOAD_FAST            (self)
             674 LOAD_ATTR            (driver)
             694 LOAD_CONST           ("youtubei/v1/att/esr?alt=json")
             696 LOAD_CONST           (20.0)

144:         698 KW_NAMES             (('timeout',))
             700 CALL                 3
             708 STORE_FAST           (payload)

147:         710 LOAD_GLOBAL          (NULL + json)
             720 LOAD_ATTR            (loads)
             740 LOAD_FAST            (payload)
             742 CALL                 1
             750 STORE_FAST           (payload_json)

149:         752 LOAD_FAST            (payload_json)
             754 LOAD_CONST           ("challenge")
             756 BINARY_SUBSCR
             760 STORE_FAST           (challenge)

150:         762 LOAD_FAST            (payload_json)
             764 LOAD_CONST           ("botguardResponse")
             766 BINARY_SUBSCR
             770 STORE_FAST           (botguardResponse)

154:         772 LOAD_CONST           ("https://studio.youtube.com/channel/")
             774 LOAD_FAST            (id)
             776 FORMAT_VALUE         0
             778 BUILD_STRING         2
             780 STORE_FAST           (url)

155:         782 LOAD_CONST           ("; ")
             784 LOAD_ATTR            (NULL|self + join)

156:         804 LOAD_FAST            (cookies)
             806 GET_ITER
             808 LOAD_FAST_AND_CLEAR  (cookie)
             810 SWAP                 (TOS <-> TOS1)
             812 BUILD_LIST           0
             814 SWAP                 (TOS <-> TOS1)
             816 FOR_ITER             (to 850)
             820 STORE_FAST           (cookie)
             822 LOAD_FAST            (cookie)
             824 LOAD_CONST           ("name")
             826 BINARY_SUBSCR
             830 FORMAT_VALUE         0
             832 LOAD_CONST           ("=")
             834 LOAD_FAST            (cookie)
             836 LOAD_CONST           ("value")
             838 BINARY_SUBSCR
             842 FORMAT_VALUE         0
             844 BUILD_STRING         3
             846 LIST_APPEND          2
         >>  848 JUMP_BACKWARD        (to 816)
             850 END_FOR
             852 SWAP                 (TOS <-> TOS1)
             854 STORE_FAST           (cookie)

155:         856 CALL                 1
             864 STORE_FAST           (cookie_string)

159:         866 LOAD_CONST           ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

160:         868 LOAD_FAST            (cookie_string)

158:         870 LOAD_CONST           (('User-Agent', 'Cookie'))
             872 BUILD_CONST_KEY_MAP  2
             874 STORE_FAST           (header)

162:         876 LOAD_GLOBAL          (NULL + requests)
             886 LOAD_ATTR            (get)
             906 LOAD_FAST            (url)
             908 LOAD_FAST            (header)
             910 KW_NAMES             (('headers',))
             912 CALL                 2
             920 STORE_FAST           (res)

163:         922 LOAD_FAST            (self)
             924 LOAD_ATTR            (NULL|self + _extract_datasync_id)
             944 LOAD_FAST            (res)
             946 LOAD_ATTR            (text)
             966 CALL                 1
             974 STORE_FAST           (delegated_session_id)

166:         976 LOAD_FAST            (self)
             978 LOAD_ATTR            (NULL|self + _get_role_type)
             998 LOAD_FAST            (res)
            1000 LOAD_ATTR            (text)
            1020 CALL                 1
            1028 STORE_FAST           (role)

168:        1030 LOAD_GLOBAL          (NULL + channel_store)
            1040 LOAD_ATTR            (upsert_channel)

170:        1060 LOAD_FAST            (id)

171:        1062 LOAD_FAST            (name)

172:        1064 LOAD_FAST            (img_src)

173:        1066 LOAD_FAST            (delegated_session_id)

174:        1068 LOAD_FAST            (sapisidhash)

175:        1070 LOAD_FAST            (role)

176:        1072 LOAD_FAST_CHECK      (challenge)

177:        1074 LOAD_FAST_CHECK      (botguardResponse)

178:        1076 LOAD_FAST            (cookies)

169:        1078 LOAD_CONST           (('id', 'name', 'img_src', 'delegated_session_id', 'sapisidhash', 'role', 'challenge', 'botguardResponse', 'cookies'))
            1080 BUILD_CONST_KEY_MAP  9

168:        1082 CALL                 1
            1090 POP_TOP

181:        1092 LOAD_GLOBAL          (NULL + dict)
            1102 LOAD_FAST            (id)
            1104 LOAD_FAST            (name)
            1106 LOAD_FAST            (img_src)
            1108 LOAD_FAST            (cookies)
            1110 KW_NAMES             (('id', 'name', 'img_src', 'cookies'))
            1112 CALL                 4
            1120 RETURN_VALUE
            1122 PUSH_EXC_INFO

151:        1124 LOAD_GLOBAL          (TimeoutError)
            1134 CHECK_EXC_MATCH
            1136 POP_JUMP_IF_FALSE    (to 1218)
            1138 STORE_FAST           (e)

152:        1140 LOAD_GLOBAL          (NULL + logger)
            1150 LOAD_ATTR            (error)
            1170 LOAD_GLOBAL          (NULL + str)
            1180 LOAD_FAST            (e)
            1182 CALL                 1
            1190 CALL                 1
            1198 POP_TOP
            1200 POP_EXCEPT
            1202 LOAD_CONST           (None)
            1204 STORE_FAST           (e)
            1206 DELETE_FAST          (e)
            1208 JUMP_BACKWARD        (to 772)
            1210 LOAD_CONST           (None)
            1212 STORE_FAST           (e)
            1214 DELETE_FAST          (e)
            1216 RERAISE              1

151:     >> 1218 RERAISE              0
            1220 COPY                 3
            1222 POP_EXCEPT
            1224 RERAISE              1
            1226 SWAP                 (TOS <-> TOS1)
            1228 POP_TOP

156:        1230 SWAP                 (TOS <-> TOS1)
            1232 STORE_FAST           (cookie)
            1234 RERAISE              0

ExceptionTable:
  662 to 770 -> 1122 [0]
  812 to 850 -> 1226 [4]
  1122 to 1138 -> 1220 [1] lasti
  1140 to 1198 -> 1210 [1] lasti
  1210 to 1218 -> 1220 [1] lasti

# Method Name:       _extract_channel_id
# Filename:          src\channel_scanner.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  2
# Stack size:        4
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        183
# Constants:
#    0: None
#    1: 'channel/([A-Za-z0-9_-]+)'
#    2: 1
# Names:
#    0: re
#    1: search
#    2: group
# Varnames:
#	url, match
# Positional arguments:
#	url
# Local variables:
#    1: match

183:           0 RESUME               0

185:           2 LOAD_GLOBAL          (NULL + re)
              12 LOAD_ATTR            (search)
              32 LOAD_CONST           ("channel/([A-Za-z0-9_-]+)")
              34 LOAD_FAST            (url)
              36 CALL                 2
              44 STORE_FAST           (match)

186:          46 LOAD_FAST            (match)
              48 POP_JUMP_IF_FALSE    (to 84)
              50 LOAD_FAST            (match)
              52 LOAD_ATTR            (NULL|self + group)
              72 LOAD_CONST           (1)
              74 CALL                 1
              82 RETURN_VALUE
         >>   84 LOAD_CONST           (None)
              86 RETURN_VALUE


# Method Name:       _extract_datasync_id
# Filename:          src\channel_scanner.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  4
# Stack size:        4
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        188
# Constants:
#    0: None
#    1: '"datasyncId":"(\\d+\\|\\|\\d*)"'
#    2: 1
#    3: '||'
#    4: 0
#    5: '\\|\\|(\\d+)'
# Names:
#    0: re
#    1: search
#    2: group
#    3: split
# Varnames:
#	text, pattern, match, res
# Positional arguments:
#	text
# Local variables:
#    1: pattern
#    2: match
#    3: res

188:           0 RESUME               0

190:           2 LOAD_CONST           ('"datasyncId":"(\\d+\\|\\|\\d*)"')
               4 STORE_FAST           (pattern)

191:           6 LOAD_GLOBAL          (NULL + re)
              16 LOAD_ATTR            (search)
              36 LOAD_FAST            (pattern)
              38 LOAD_FAST            (text)
              40 CALL                 2
              48 STORE_FAST           (match)

192:          50 LOAD_FAST            (match)
              52 POP_JUMP_IF_FALSE    (to 128)

193:          54 LOAD_FAST            (match)
              56 LOAD_ATTR            (NULL|self + group)
              76 LOAD_CONST           (1)
              78 CALL                 1
              86 LOAD_ATTR            (NULL|self + split)
             106 LOAD_CONST           ("||")
             108 CALL                 1
             116 LOAD_CONST           (0)
             118 BINARY_SUBSCR
             122 STORE_FAST           (res)

194:         124 LOAD_FAST            (res)
             126 RETURN_VALUE

196:     >>  128 LOAD_CONST           ("\\|\\|(\\d+)")
             130 STORE_FAST           (pattern)

197:         132 LOAD_GLOBAL          (NULL + re)
             142 LOAD_ATTR            (search)
             162 LOAD_FAST            (pattern)
             164 LOAD_FAST            (text)
             166 CALL                 2
             174 STORE_FAST           (match)

198:         176 LOAD_FAST            (match)
             178 POP_JUMP_IF_FALSE    (to 214)

199:         180 LOAD_FAST            (match)
             182 LOAD_ATTR            (NULL|self + group)
             202 LOAD_CONST           (1)
             204 CALL                 1
             212 RETURN_VALUE

201:     >>  214 RETURN_CONST         (None)


# Method Name:       _generate_sapisidhash_header
# Filename:          src\channel_scanner.py
# Argument count:    2
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  4
# Stack size:        7
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        203
# Constants:
#    0: None
#    1: ' '
#    2: 'utf-8'
#    3: '_'
# Names:
#    0: round
#    1: time
#    2: hashlib
#    3: sha1
#    4: encode
#    5: hexdigest
# Varnames:
#	sapisid, origin, time_now, sapisidhash
# Positional arguments:
#	sapisid, origin
# Local variables:
#    2: time_now
#    3: sapisidhash

203:           0 RESUME               0

205:           2 LOAD_GLOBAL          (NULL + round)
              12 LOAD_GLOBAL          (NULL + time)
              22 LOAD_ATTR            (time)
              42 CALL                 0
              50 CALL                 1
              58 STORE_FAST           (time_now)

206:          60 LOAD_GLOBAL          (NULL + hashlib)
              70 LOAD_ATTR            (sha1)

207:          90 LOAD_FAST            (time_now)
              92 FORMAT_VALUE         0
              94 LOAD_CONST           (" ")
              96 LOAD_FAST            (sapisid)
              98 FORMAT_VALUE         0
             100 LOAD_CONST           (" ")
             102 LOAD_FAST            (origin)
             104 FORMAT_VALUE         0
             106 BUILD_STRING         5
             108 LOAD_ATTR            (NULL|self + encode)
             128 LOAD_CONST           ("utf-8")
             130 CALL                 1

206:         138 CALL                 1

208:         146 LOAD_ATTR            (NULL|self + hexdigest)
             166 CALL                 0

206:         174 STORE_FAST           (sapisidhash)

209:         176 LOAD_FAST            (time_now)
             178 FORMAT_VALUE         0
             180 LOAD_CONST           ("_")
             182 LOAD_FAST            (sapisidhash)
             184 FORMAT_VALUE         0
             186 BUILD_STRING         3
             188 RETURN_VALUE


# Method Name:       _get_role_type
# Filename:          src\channel_scanner.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  4
# Stack size:        4
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        211
# Constants:
#    0: None
#    1: '"channelRoleType":"(CREATOR_CHANNEL_ROLE_TYPE_[A-Z_]+)"'
#    2: 1
# Names:
#    0: re
#    1: search
#    2: group
# Varnames:
#	text, pattern, match, res
# Positional arguments:
#	text
# Local variables:
#    1: pattern
#    2: match
#    3: res

211:           0 RESUME               0

213:           2 LOAD_CONST           ('"channelRoleType":"(CREATOR_CHANNEL_ROLE_TYPE_[A-Z_]+)"')
               4 STORE_FAST           (pattern)

214:           6 LOAD_GLOBAL          (NULL + re)
              16 LOAD_ATTR            (search)
              36 LOAD_FAST            (pattern)
              38 LOAD_FAST            (text)
              40 CALL                 2
              48 STORE_FAST           (match)

215:          50 LOAD_FAST            (match)
              52 LOAD_ATTR            (NULL|self + group)
              72 LOAD_CONST           (1)
              74 CALL                 1
              82 STORE_FAST           (res)

216:          84 LOAD_FAST            (res)
              86 RETURN_VALUE

```
