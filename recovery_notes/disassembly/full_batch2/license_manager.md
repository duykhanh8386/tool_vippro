# Static CPython 3.12 disassembly — `license_manager.pyc`

Generated with `xdis 6.3.0`; the code object was deserialized but never executed.

```text
# pydisasm version 6.3.0
# CPython Python bytecode 3.12.0 (3531)
#   Disassembled from CPython Python 3.13.13 | packaged by Anaconda, Inc. | (main, Apr 14 2026, 06:12:50) [MSC v.1942 64 bit (AMD64)]
# Timestamp in code: 0 (1970-01-01 07:00:00)
# Source code size mod 2**32: 0 bytes
# Method Name:       <module>
# Filename:          src\license_manager.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        2
# Flags:             0x01000000 (0x1000000)
# First Line:        1
# Constants:
#    0: 0
#    1: ('annotations',)
#    2: None
#    3: ('Path',)
#    4: ('Optional',)
#    5: ('get_mac_address',)
#    6: ('logger',)
#    7: ('get_data_dir',)
#    8: 'https://api.licensify.vn/v1'
#    9: '2c8a6b04-4322-4b65-bcd1-e0cefe2fdcf4'
#   10: 'license.json'
#   11: <Code311 code object _device_fingerprint at 0x2e5058a44d0, file src\license_manager.py>, line 20
#   12: <Code311 code object _device_name at 0x2e505862250, file src\license_manager.py>, line 27
#   13: <Code311 code object _os_info at 0x2e505862470, file src\license_manager.py>, line 31
#   14: <Code311 code object _save_license at 0x2e505862580, file src\license_manager.py>, line 35
#   15: <Code311 code object _load_license at 0x2e505862690, file src\license_manager.py>, line 45
#   16: <Code311 code object verify_license at 0x2e5058627a0, file src\license_manager.py>, line 54
#   17: <Code311 code object is_licensed at 0x2e5058629c0, file src\license_manager.py>, line 91
#   18: <Code311 code object get_license_info at 0x2e505862ad0, file src\license_manager.py>, line 123
#   19: <Code311 code object deactivate at 0x2e505862be0, file src\license_manager.py>, line 128
#   20: ('return', 'str')
#   21: ('license_key', 'str', 'data', 'dict', 'return', 'None')
#   22: ('return', 'Optional[dict]')
#   23: ('license_key', 'str', 'return', 'tuple[bool, str]')
#   24: ('return', 'bool')
#   25: ('return', 'None')
# Names:
#    0: __future__
#    1: annotations
#    2: json
#    3: platform
#    4: pathlib
#    5: Path
#    6: typing
#    7: Optional
#    8: requests
#    9: getmac
#   10: get_mac_address
#   11: loguru
#   12: logger
#   13: src.paths
#   14: get_data_dir
#   15: BASE_URL
#   16: PRODUCT_ID
#   17: _LICENSE_FILE
#   18: _device_fingerprint
#   19: _device_name
#   20: _os_info
#   21: _save_license
#   22: _load_license
#   23: verify_license
#   24: is_licensed
#   25: get_license_info
#   26: deactivate

  0:           0 RESUME               0

  1:           2 LOAD_CONST           (0)
               4 LOAD_CONST           (('annotations',))
               6 IMPORT_NAME          (__future__)
               8 IMPORT_FROM          (annotations)
              10 STORE_NAME           (annotations)
              12 POP_TOP

  3:          14 LOAD_CONST           (0)
              16 LOAD_CONST           (None)
              18 IMPORT_NAME          (json)
              20 STORE_NAME           (json)

  4:          22 LOAD_CONST           (0)
              24 LOAD_CONST           (None)
              26 IMPORT_NAME          (platform)
              28 STORE_NAME           (platform)

  5:          30 LOAD_CONST           (0)
              32 LOAD_CONST           (('Path',))
              34 IMPORT_NAME          (pathlib)
              36 IMPORT_FROM          (Path)
              38 STORE_NAME           (Path)
              40 POP_TOP

  6:          42 LOAD_CONST           (0)
              44 LOAD_CONST           (('Optional',))
              46 IMPORT_NAME          (typing)
              48 IMPORT_FROM          (Optional)
              50 STORE_NAME           (Optional)
              52 POP_TOP

  8:          54 LOAD_CONST           (0)
              56 LOAD_CONST           (None)
              58 IMPORT_NAME          (requests)
              60 STORE_NAME           (requests)

  9:          62 LOAD_CONST           (0)
              64 LOAD_CONST           (('get_mac_address',))
              66 IMPORT_NAME          (getmac)
              68 IMPORT_FROM          (get_mac_address)
              70 STORE_NAME           (get_mac_address)
              72 POP_TOP

 10:          74 LOAD_CONST           (0)
              76 LOAD_CONST           (('logger',))
              78 IMPORT_NAME          (loguru)
              80 IMPORT_FROM          (logger)
              82 STORE_NAME           (logger)
              84 POP_TOP

 12:          86 LOAD_CONST           (0)
              88 LOAD_CONST           (('get_data_dir',))
              90 IMPORT_NAME          (src.paths)
              92 IMPORT_FROM          (get_data_dir)
              94 STORE_NAME           (get_data_dir)
              96 POP_TOP

 14:          98 LOAD_CONST           ("https://api.licensify.vn/v1")
             100 STORE_NAME           (BASE_URL)

 15:         102 LOAD_CONST           ("2c8a6b04-4322-4b65-bcd1-e0cefe2fdcf4")
             104 STORE_NAME           (PRODUCT_ID)

 17:         106 PUSH_NULL
             108 LOAD_NAME            (get_data_dir)
             110 CALL                 0
             118 LOAD_CONST           ("license.json")
             120 BINARY_OP            (/)
             124 STORE_NAME           (_LICENSE_FILE)

 20:         126 LOAD_CONST           (('return', 'str'))
             128 LOAD_CONST           (<Code311 code object _device_fingerprint at 0x2e5058a44d0, file src\license_manager.py>, line 20)
             130 MAKE_FUNCTION        (annotation)
             132 STORE_NAME           (_device_fingerprint)

 27:         134 LOAD_CONST           (('return', 'str'))
             136 LOAD_CONST           (<Code311 code object _device_name at 0x2e505862250, file src\license_manager.py>, line 27)
             138 MAKE_FUNCTION        (annotation)
             140 STORE_NAME           (_device_name)

 31:         142 LOAD_CONST           (('return', 'str'))
             144 LOAD_CONST           (<Code311 code object _os_info at 0x2e505862470, file src\license_manager.py>, line 31)
             146 MAKE_FUNCTION        (annotation)
             148 STORE_NAME           (_os_info)

 35:         150 LOAD_CONST           (('license_key', 'str', 'data', 'dict', 'return', 'None'))
             152 LOAD_CONST           (<Code311 code object _save_license at 0x2e505862580, file src\license_manager.py>, line 35)
             154 MAKE_FUNCTION        (annotation)
             156 STORE_NAME           (_save_license)

 45:         158 LOAD_CONST           (('return', 'Optional[dict]'))
             160 LOAD_CONST           (<Code311 code object _load_license at 0x2e505862690, file src\license_manager.py>, line 45)
             162 MAKE_FUNCTION        (annotation)
             164 STORE_NAME           (_load_license)

 54:         166 LOAD_CONST           (('license_key', 'str', 'return', 'tuple[bool, str]'))
             168 LOAD_CONST           (<Code311 code object verify_license at 0x2e5058627a0, file src\license_manager.py>, line 54)
             170 MAKE_FUNCTION        (annotation)
             172 STORE_NAME           (verify_license)

 91:         174 LOAD_CONST           (('return', 'bool'))
             176 LOAD_CONST           (<Code311 code object is_licensed at 0x2e5058629c0, file src\license_manager.py>, line 91)
             178 MAKE_FUNCTION        (annotation)
             180 STORE_NAME           (is_licensed)

123:         182 LOAD_CONST           (('return', 'Optional[dict]'))
             184 LOAD_CONST           (<Code311 code object get_license_info at 0x2e505862ad0, file src\license_manager.py>, line 123)
             186 MAKE_FUNCTION        (annotation)
             188 STORE_NAME           (get_license_info)

128:         190 LOAD_CONST           (('return', 'None'))
             192 LOAD_CONST           (<Code311 code object deactivate at 0x2e505862be0, file src\license_manager.py>, line 128)
             194 MAKE_FUNCTION        (annotation)
             196 STORE_NAME           (deactivate)
             198 RETURN_CONST         (None)


# Method Name:       _device_fingerprint
# Filename:          src\license_manager.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  1
# Stack size:        2
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        20
# Constants:
#    0: None
#    1: '00:00:00:00:00:00'
# Names:
#    0: get_mac_address
#    1: upper
#    2: platform
#    3: node
# Varnames:
#	mac
# Local variables:
#    0: mac

 20:           0 RESUME               0

 21:           2 LOAD_GLOBAL          (NULL + get_mac_address)
              12 CALL                 0
              20 STORE_FAST           (mac)

 22:          22 LOAD_FAST            (mac)
              24 POP_JUMP_IF_FALSE    (to 68)
              26 LOAD_FAST            (mac)
              28 LOAD_CONST           ("00:00:00:00:00:00")
              30 COMPARE_OP           (!=)
              34 POP_JUMP_IF_FALSE    (to 68)

 23:          36 LOAD_FAST            (mac)
              38 LOAD_ATTR            (NULL|self + upper)
              58 CALL                 0
              66 RETURN_VALUE

 24:     >>   68 LOAD_GLOBAL          (NULL + platform)
              78 LOAD_ATTR            (node)
              98 CALL                 0
             106 RETURN_VALUE


# Method Name:       _device_name
# Filename:          src\license_manager.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        2
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        27
# Constants:
#    0: None
# Names:
#    0: platform
#    1: node

 27:           0 RESUME               0

 28:           2 LOAD_GLOBAL          (NULL + platform)
              12 LOAD_ATTR            (node)
              32 CALL                 0
              40 RETURN_VALUE


# Method Name:       _os_info
# Filename:          src\license_manager.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        4
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        31
# Constants:
#    0: None
#    1: ' '
# Names:
#    0: platform
#    1: system
#    2: release

 31:           0 RESUME               0

 32:           2 LOAD_GLOBAL          (NULL + platform)
              12 LOAD_ATTR            (system)
              32 CALL                 0
              40 FORMAT_VALUE         0
              42 LOAD_CONST           (" ")
              44 LOAD_GLOBAL          (NULL + platform)
              54 LOAD_ATTR            (release)
              74 CALL                 0
              82 FORMAT_VALUE         0
              84 BUILD_STRING         3
              86 RETURN_VALUE


# Method Name:       _save_license
# Filename:          src\license_manager.py
# Argument count:    2
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  3
# Stack size:        6
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        35
# Constants:
#    0: None
#    1: 'expires_at'
#    2: 'devices_used'
#    3: 'max_devices'
#    4: ('license_key', 'expires_at', 'devices_used', 'max_devices')
#    5: False
#    6: ('ensure_ascii',)
#    7: 'utf-8'
#    8: ('encoding',)
# Names:
#    0: get
#    1: _LICENSE_FILE
#    2: write_text
#    3: json
#    4: dumps
# Varnames:
#	license_key, data, payload
# Positional arguments:
#	license_key, data
# Local variables:
#    2: payload

 35:           0 RESUME               0

 37:           2 LOAD_FAST            (license_key)

 38:           4 LOAD_FAST            (data)
               6 LOAD_ATTR            (NULL|self + get)
              26 LOAD_CONST           ("expires_at")
              28 CALL                 1

 39:          36 LOAD_FAST            (data)
              38 LOAD_ATTR            (NULL|self + get)
              58 LOAD_CONST           ("devices_used")
              60 CALL                 1

 40:          68 LOAD_FAST            (data)
              70 LOAD_ATTR            (NULL|self + get)
              90 LOAD_CONST           ("max_devices")
              92 CALL                 1

 36:         100 LOAD_CONST           (('license_key', 'expires_at', 'devices_used', 'max_devices'))
             102 BUILD_CONST_KEY_MAP  4
             104 STORE_FAST           (payload)

 42:         106 LOAD_GLOBAL          (_LICENSE_FILE)
             116 LOAD_ATTR            (NULL|self + write_text)
             136 LOAD_GLOBAL          (NULL + json)
             146 LOAD_ATTR            (dumps)
             166 LOAD_FAST            (payload)
             168 LOAD_CONST           (False)
             170 KW_NAMES             (('ensure_ascii',))
             172 CALL                 2
             180 LOAD_CONST           ("utf-8")
             182 KW_NAMES             (('encoding',))
             184 CALL                 2
             192 POP_TOP
             194 RETURN_CONST         (None)


# Method Name:       _load_license
# Filename:          src\license_manager.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        5
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        45
# Constants:
#    0: None
#    1: 'utf-8'
#    2: ('encoding',)
# Names:
#    0: _LICENSE_FILE
#    1: exists
#    2: json
#    3: loads
#    4: read_text
#    5: Exception

 45:           0 RESUME               0

 46:           2 LOAD_GLOBAL          (_LICENSE_FILE)
              12 LOAD_ATTR            (NULL|self + exists)
              32 CALL                 0
              40 POP_JUMP_IF_TRUE     (to 44)

 47:          42 RETURN_CONST         (None)

 48:     >>   44 NOP

 49:          46 LOAD_GLOBAL          (NULL + json)
              56 LOAD_ATTR            (loads)
              76 LOAD_GLOBAL          (_LICENSE_FILE)
              86 LOAD_ATTR            (NULL|self + read_text)
             106 LOAD_CONST           ("utf-8")
             108 KW_NAMES             (('encoding',))
             110 CALL                 1
             118 CALL                 1
             126 RETURN_VALUE
             128 PUSH_EXC_INFO

 50:         130 LOAD_GLOBAL          (Exception)
             140 CHECK_EXC_MATCH
             142 POP_JUMP_IF_FALSE    (to 150)
             144 POP_TOP

 51:         146 POP_EXCEPT
             148 RETURN_CONST         (None)

 50:     >>  150 RERAISE              0
             152 COPY                 3
             154 POP_EXCEPT
             156 RERAISE              1

ExceptionTable:
  46 to 124 -> 128 [0]
  128 to 144 -> 152 [1] lasti
  150 to 150 -> 152 [1] lasti

# Method Name:       verify_license
# Filename:          src\license_manager.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  7
# Stack size:        9
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        54
# Constants:
#    0: 'Verify a license key against the Licensify API.\n\n    Returns (success, message).\n    '
#    1: '/licenses/verify'
#    2: ('license_key', 'product_id', 'device_fingerprint', 'device_name', 'os_info')
#    3: 15
#    4: ('json', 'timeout')
#    5: 'data'
#    6: 'valid'
#    7: 'expires_at'
#    8: 'Vinh vien'
#    9: 'License activated -- expires: {}'
#   10: (True, 'Kich hoat thanh cong!')
#   11: 'reason'
#   12: 'Khong xac dinh'
#   13: 'License rejected: {}'
#   14: False
#   15: 'License khong hop le: '
#   16: 'Khong the ket noi den server license'
#   17: (False, 'Khong co ket noi internet!')
#   18: 'License verification error: {}'
#   19: 'Loi xac thuc: '
#   20: None
# Names:
#    0: requests
#    1: post
#    2: BASE_URL
#    3: PRODUCT_ID
#    4: _device_fingerprint
#    5: _device_name
#    6: _os_info
#    7: json
#    8: get
#    9: _save_license
#   10: logger
#   11: info
#   12: warning
#   13: ConnectionError
#   14: error
#   15: Exception
# Varnames:
#	license_key, resp, body, data, expires, reason, e
# Positional arguments:
#	license_key
# Local variables:
#    1: resp
#    2: body
#    3: data
#    4: expires
#    5: reason
#    6: e

 54:           0 RESUME               0

 59:           2 NOP

 60:           4 LOAD_GLOBAL          (NULL + requests)
              14 LOAD_ATTR            (post)

 61:          34 LOAD_GLOBAL          (BASE_URL)
              44 FORMAT_VALUE         0
              46 LOAD_CONST           ("/licenses/verify")
              48 BUILD_STRING         2

 63:          50 LOAD_FAST            (license_key)

 64:          52 LOAD_GLOBAL          (PRODUCT_ID)

 65:          62 LOAD_GLOBAL          (NULL + _device_fingerprint)
              72 CALL                 0

 66:          80 LOAD_GLOBAL          (NULL + _device_name)
              90 CALL                 0

 67:          98 LOAD_GLOBAL          (NULL + _os_info)
             108 CALL                 0

 62:         116 LOAD_CONST           (('license_key', 'product_id', 'device_fingerprint', 'device_name', 'os_info'))
             118 BUILD_CONST_KEY_MAP  5

 69:         120 LOAD_CONST           (15)

 60:         122 KW_NAMES             (('json', 'timeout'))
             124 CALL                 3
             132 STORE_FAST           (resp)

 71:         134 LOAD_FAST            (resp)
             136 LOAD_ATTR            (NULL|self + json)
             156 CALL                 0
             164 STORE_FAST           (body)

 72:         166 LOAD_FAST            (body)
             168 LOAD_ATTR            (NULL|self + get)
             188 LOAD_CONST           ("data")
             190 BUILD_MAP            0
             192 CALL                 2
             200 STORE_FAST           (data)

 74:         202 LOAD_FAST            (data)
             204 LOAD_ATTR            (NULL|self + get)
             224 LOAD_CONST           ("valid")
             226 CALL                 1
             234 POP_JUMP_IF_FALSE    (to 348)

 75:         236 LOAD_GLOBAL          (NULL + _save_license)
             246 LOAD_FAST            (license_key)
             248 LOAD_FAST            (data)
             250 CALL                 2
             258 POP_TOP

 76:         260 LOAD_FAST            (data)
             262 LOAD_ATTR            (NULL|self + get)
             282 LOAD_CONST           ("expires_at")
             284 CALL                 1
             292 COPY                 1
             294 POP_JUMP_IF_TRUE     (to 300)
             296 POP_TOP
             298 LOAD_CONST           ("Vinh vien")
         >>  300 STORE_FAST           (expires)

 77:         302 LOAD_GLOBAL          (NULL + logger)
             312 LOAD_ATTR            (info)
             332 LOAD_CONST           ("License activated -- expires: {}")
             334 LOAD_FAST            (expires)
             336 CALL                 2
             344 POP_TOP

 78:         346 RETURN_CONST         ((True, 'Kich hoat thanh cong!'))

 80:     >>  348 LOAD_FAST            (data)
             350 LOAD_ATTR            (NULL|self + get)
             370 LOAD_CONST           ("reason")
             372 LOAD_CONST           ("Khong xac dinh")
             374 CALL                 2
             382 STORE_FAST           (reason)

 81:         384 LOAD_GLOBAL          (NULL + logger)
             394 LOAD_ATTR            (warning)
             414 LOAD_CONST           ("License rejected: {}")
             416 LOAD_FAST            (reason)
             418 CALL                 2
             426 POP_TOP

 82:         428 LOAD_CONST           (False)
             430 LOAD_CONST           ("License khong hop le: ")
             432 LOAD_FAST            (reason)
             434 FORMAT_VALUE         0
             436 BUILD_STRING         2
             438 BUILD_TUPLE          2
             440 RETURN_VALUE
             442 PUSH_EXC_INFO

 83:         444 LOAD_GLOBAL          (requests)
             454 LOAD_ATTR            (ConnectionError)
             474 CHECK_EXC_MATCH
             476 POP_JUMP_IF_FALSE    (to 526)
             478 POP_TOP

 84:         480 LOAD_GLOBAL          (NULL + logger)
             490 LOAD_ATTR            (error)
             510 LOAD_CONST           ("Khong the ket noi den server license")
             512 CALL                 1
             520 POP_TOP

 85:         522 POP_EXCEPT
             524 RETURN_CONST         ((False, 'Khong co ket noi internet!'))

 86:     >>  526 LOAD_GLOBAL          (Exception)
             536 CHECK_EXC_MATCH
             538 POP_JUMP_IF_FALSE    (to 618)
             540 STORE_FAST           (e)

 87:         542 LOAD_GLOBAL          (NULL + logger)
             552 LOAD_ATTR            (error)
             572 LOAD_CONST           ("License verification error: {}")
             574 LOAD_FAST            (e)
             576 CALL                 2
             584 POP_TOP

 88:         586 LOAD_CONST           (False)
             588 LOAD_CONST           ("Loi xac thuc: ")
             590 LOAD_FAST            (e)
             592 FORMAT_VALUE         0
             594 BUILD_STRING         2
             596 BUILD_TUPLE          2
             598 SWAP                 (TOS <-> TOS1)
             600 POP_EXCEPT
             602 LOAD_CONST           (None)
             604 STORE_FAST           (e)
             606 DELETE_FAST          (e)
             608 RETURN_VALUE
             610 LOAD_CONST           (None)
             612 STORE_FAST           (e)
             614 DELETE_FAST          (e)
             616 RERAISE              1

 86:     >>  618 RERAISE              0
             620 COPY                 3
             622 POP_EXCEPT
             624 RERAISE              1

ExceptionTable:
  4 to 344 -> 442 [0]
  348 to 438 -> 442 [0]
  442 to 520 -> 620 [1] lasti
  526 to 540 -> 620 [1] lasti
  542 to 596 -> 610 [1] lasti
  598 to 598 -> 620 [1] lasti
  610 to 618 -> 620 [1] lasti

# Method Name:       is_licensed
# Filename:          src\license_manager.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  4
# Stack size:        9
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        91
# Constants:
#    0: 'Check whether a valid license exists locally, then re-verify online.'
#    1: 'license_key'
#    2: False
#    3: '/licenses/verify'
#    4: ('license_key', 'product_id', 'device_fingerprint', 'device_name', 'os_info')
#    5: 10
#    6: ('json', 'timeout')
#    7: 'data'
#    8: 'valid'
#    9: True
#   10: ('missing_ok',)
#   11: 'Offline -- trusting cached license'
#   12: 'License check error: {}'
#   13: None
# Names:
#    0: _load_license
#    1: get
#    2: requests
#    3: post
#    4: BASE_URL
#    5: PRODUCT_ID
#    6: _device_fingerprint
#    7: _device_name
#    8: _os_info
#    9: json
#   10: _save_license
#   11: _LICENSE_FILE
#   12: unlink
#   13: ConnectionError
#   14: logger
#   15: warning
#   16: Exception
#   17: error
# Varnames:
#	stored, resp, data, e
# Local variables:
#    0: stored
#    1: resp
#    2: data
#    3: e

 91:           0 RESUME               0

 93:           2 LOAD_GLOBAL          (NULL + _load_license)
              12 CALL                 0
              20 STORE_FAST           (stored)

 94:          22 LOAD_FAST            (stored)
              24 POP_JUMP_IF_FALSE    (to 60)
              26 LOAD_FAST            (stored)
              28 LOAD_ATTR            (NULL|self + get)
              48 LOAD_CONST           ("license_key")
              50 CALL                 1
              58 POP_JUMP_IF_TRUE     (to 62)

 95:     >>   60 RETURN_CONST         (False)

 97:     >>   62 NOP

 98:          64 LOAD_GLOBAL          (NULL + requests)
              74 LOAD_ATTR            (post)

 99:          94 LOAD_GLOBAL          (BASE_URL)
             104 FORMAT_VALUE         0
             106 LOAD_CONST           ("/licenses/verify")
             108 BUILD_STRING         2

101:         110 LOAD_FAST            (stored)
             112 LOAD_CONST           ("license_key")
             114 BINARY_SUBSCR

102:         118 LOAD_GLOBAL          (PRODUCT_ID)

103:         128 LOAD_GLOBAL          (NULL + _device_fingerprint)
             138 CALL                 0

104:         146 LOAD_GLOBAL          (NULL + _device_name)
             156 CALL                 0

105:         164 LOAD_GLOBAL          (NULL + _os_info)
             174 CALL                 0

100:         182 LOAD_CONST           (('license_key', 'product_id', 'device_fingerprint', 'device_name', 'os_info'))
             184 BUILD_CONST_KEY_MAP  5

107:         186 LOAD_CONST           (10)

 98:         188 KW_NAMES             (('json', 'timeout'))
             190 CALL                 3
             198 STORE_FAST           (resp)

109:         200 LOAD_FAST            (resp)
             202 LOAD_ATTR            (NULL|self + json)
             222 CALL                 0
             230 LOAD_ATTR            (NULL|self + get)
             250 LOAD_CONST           ("data")
             252 BUILD_MAP            0
             254 CALL                 2
             262 STORE_FAST           (data)

110:         264 LOAD_FAST            (data)
             266 LOAD_ATTR            (NULL|self + get)
             286 LOAD_CONST           ("valid")
             288 CALL                 1
             296 POP_JUMP_IF_FALSE    (to 330)

111:         298 LOAD_GLOBAL          (NULL + _save_license)
             308 LOAD_FAST            (stored)
             310 LOAD_CONST           ("license_key")
             312 BINARY_SUBSCR
             316 LOAD_FAST            (data)
             318 CALL                 2
             326 POP_TOP

112:         328 RETURN_CONST         (True)

113:     >>  330 LOAD_GLOBAL          (_LICENSE_FILE)
             340 LOAD_ATTR            (NULL|self + unlink)
             360 LOAD_CONST           (True)
             362 KW_NAMES             (('missing_ok',))
             364 CALL                 1
             372 POP_TOP

114:         374 RETURN_CONST         (False)
             376 PUSH_EXC_INFO

115:         378 LOAD_GLOBAL          (requests)
             388 LOAD_ATTR            (ConnectionError)
             408 CHECK_EXC_MATCH
             410 POP_JUMP_IF_FALSE    (to 460)
             412 POP_TOP

116:         414 LOAD_GLOBAL          (NULL + logger)
             424 LOAD_ATTR            (warning)
             444 LOAD_CONST           ("Offline -- trusting cached license")
             446 CALL                 1
             454 POP_TOP

117:         456 POP_EXCEPT
             458 RETURN_CONST         (True)

118:     >>  460 LOAD_GLOBAL          (Exception)
             470 CHECK_EXC_MATCH
             472 POP_JUMP_IF_FALSE    (to 538)
             474 STORE_FAST           (e)

119:         476 LOAD_GLOBAL          (NULL + logger)
             486 LOAD_ATTR            (error)
             506 LOAD_CONST           ("License check error: {}")
             508 LOAD_FAST            (e)
             510 CALL                 2
             518 POP_TOP

120:         520 POP_EXCEPT
             522 LOAD_CONST           (None)
             524 STORE_FAST           (e)
             526 DELETE_FAST          (e)
             528 RETURN_CONST         (False)
             530 LOAD_CONST           (None)
             532 STORE_FAST           (e)
             534 DELETE_FAST          (e)
             536 RERAISE              1

118:     >>  538 RERAISE              0
             540 COPY                 3
             542 POP_EXCEPT
             544 RERAISE              1

ExceptionTable:
  64 to 326 -> 376 [0]
  330 to 372 -> 376 [0]
  376 to 454 -> 540 [1] lasti
  460 to 474 -> 540 [1] lasti
  476 to 518 -> 530 [1] lasti
  530 to 538 -> 540 [1] lasti

# Method Name:       get_license_info
# Filename:          src\license_manager.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        2
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        123
# Constants:
#    0: 'Return cached license info or None.'
# Names:
#    0: _load_license

123:           0 RESUME               0

125:           2 LOAD_GLOBAL          (NULL + _load_license)
              12 CALL                 0
              20 RETURN_VALUE


# Method Name:       deactivate
# Filename:          src\license_manager.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        3
# Flags:             0x01000003 (0x1000000 | NEWLOCALS | OPTIMIZED)
# First Line:        128
# Constants:
#    0: 'Remove stored license.'
#    1: True
#    2: ('missing_ok',)
#    3: None
# Names:
#    0: _LICENSE_FILE
#    1: unlink

128:           0 RESUME               0

130:           2 LOAD_GLOBAL          (_LICENSE_FILE)
              12 LOAD_ATTR            (NULL|self + unlink)
              32 LOAD_CONST           (True)
              34 KW_NAMES             (('missing_ok',))
              36 CALL                 1
              44 POP_TOP
              46 RETURN_CONST         (None)

```
