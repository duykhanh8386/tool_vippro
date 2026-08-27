# Static CPython 3.12 disassembly — `channel_store.pyc`

Generated with `xdis 6.3.0`; the code object was deserialized but never executed.

```text
# pydisasm version 6.3.0
# CPython Python bytecode 3.12.0 (3531)
#   Disassembled from CPython Python 3.13.13 | packaged by Anaconda, Inc. | (main, Apr 14 2026, 06:12:50) [MSC v.1942 64 bit (AMD64)]
# Timestamp in code: 0 (1970-01-01 07:00:00)
# Source code size mod 2**32: 0 bytes
# Method Name:       <module>
# Filename:          src\channel_store.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        5
# Flags:             0x00000000 (0x0)
# First Line:        1
# Constants:
#    0: '\nSQLite-based channel storage.\n\nReplaces the old file-based (info.json + cookies.pkl) approach with a single\nSQLite database stored in the platform-specific application data directory.\n'
#    1: 0
#    2: None
#    3: ('Path',)
#    4: ('Optional',)
#    5: ('get_data_dir',)
#    6: 'return'
#    7: <Code311 code object _default_db_path at 0x1e8dd2f3680, file src\channel_store.py>, line 19
#    8: 'db_path'
#    9: <Code311 code object _connect at 0x1e8dd2f3570, file src\channel_store.py>, line 23
#   10: 'cookies'
#   11: <Code311 code object _compute_cookies_expires_at at 0x1e8dd2f3790, file src\channel_store.py>, line 30
#   12: "\nCREATE TABLE IF NOT EXISTS channels (\n    id                    TEXT PRIMARY KEY,\n    name                  TEXT,\n    img_src               TEXT,\n    sapisidhash           TEXT,\n    delegated_session_id  TEXT,\n    role                  TEXT,\n    challenge             TEXT,\n    botguardResponse      TEXT,\n    cookies_json          TEXT NOT NULL DEFAULT '[]',\n    cookies_expires_at    INTEGER,\n    created_at            INTEGER NOT NULL,\n    updated_at            INTEGER NOT NULL\n)\n"
#   13: 'conn'
#   14: <Code311 code object _ensure_schema at 0x1e8dd2f38a0, file src\channel_store.py>, line 60
#   15: 'row'
#   16: <Code311 code object _row_to_record at 0x1e8dd2f39b0, file src\channel_store.py>, line 71
#   17: <Code311 code object ChannelStore at 0x1e8dd39c490, file src\channel_store.py>, line 97
#   18: 'ChannelStore'
# Names:
#    0: __doc__
#    1: json
#    2: os
#    3: sqlite3
#    4: threading
#    5: time
#    6: pathlib
#    7: Path
#    8: typing
#    9: Optional
#   10: src.paths
#   11: get_data_dir
#   12: _default_db_path
#   13: Connection
#   14: _connect
#   15: list
#   16: int
#   17: _compute_cookies_expires_at
#   18: _CREATE_TABLE_SQL
#   19: _ensure_schema
#   20: Row
#   21: dict
#   22: _row_to_record
#   23: ChannelStore
#   24: channel_store

  0:           0 RESUME               0

  1:           2 LOAD_CONST           ("\nSQLite-based channel storage.\n\nReplaces the old file-based (info.json + cookies.pkl) approach with a single\nSQLite database stored in the platform-specific application data directory.\n")
               4 STORE_NAME           (__doc__)

  8:           6 LOAD_CONST           (0)
               8 LOAD_CONST           (None)
              10 IMPORT_NAME          (json)
              12 STORE_NAME           (json)

  9:          14 LOAD_CONST           (0)
              16 LOAD_CONST           (None)
              18 IMPORT_NAME          (os)
              20 STORE_NAME           (os)

 10:          22 LOAD_CONST           (0)
              24 LOAD_CONST           (None)
              26 IMPORT_NAME          (sqlite3)
              28 STORE_NAME           (sqlite3)

 11:          30 LOAD_CONST           (0)
              32 LOAD_CONST           (None)
              34 IMPORT_NAME          (threading)
              36 STORE_NAME           (threading)

 12:          38 LOAD_CONST           (0)
              40 LOAD_CONST           (None)
              42 IMPORT_NAME          (time)
              44 STORE_NAME           (time)

 13:          46 LOAD_CONST           (0)
              48 LOAD_CONST           (('Path',))
              50 IMPORT_NAME          (pathlib)
              52 IMPORT_FROM          (Path)
              54 STORE_NAME           (Path)
              56 POP_TOP

 14:          58 LOAD_CONST           (0)
              60 LOAD_CONST           (('Optional',))
              62 IMPORT_NAME          (typing)
              64 IMPORT_FROM          (Optional)
              66 STORE_NAME           (Optional)
              68 POP_TOP

 16:          70 LOAD_CONST           (0)
              72 LOAD_CONST           (('get_data_dir',))
              74 IMPORT_NAME          (src.paths)
              76 IMPORT_FROM          (get_data_dir)
              78 STORE_NAME           (get_data_dir)
              80 POP_TOP

 19:          82 LOAD_CONST           ("return")
              84 LOAD_NAME            (Path)
              86 BUILD_TUPLE          2
              88 LOAD_CONST           (<Code311 code object _default_db_path at 0x1e8dd2f3680, file src\channel_store.py>, line 19)
              90 MAKE_FUNCTION        (annotation)
              92 STORE_NAME           (_default_db_path)

 23:          94 LOAD_CONST           ("db_path")
              96 LOAD_NAME            (Path)
              98 LOAD_CONST           ("return")
             100 LOAD_NAME            (sqlite3)
             102 LOAD_ATTR            (Connection)
             122 BUILD_TUPLE          4
             124 LOAD_CONST           (<Code311 code object _connect at 0x1e8dd2f3570, file src\channel_store.py>, line 23)
             126 MAKE_FUNCTION        (annotation)
             128 STORE_NAME           (_connect)

 30:         130 LOAD_CONST           ("cookies")
             132 LOAD_NAME            (list)
             134 LOAD_CONST           ("return")
             136 LOAD_NAME            (Optional)
             138 LOAD_NAME            (int)
             140 BINARY_SUBSCR
             144 BUILD_TUPLE          4
             146 LOAD_CONST           (<Code311 code object _compute_cookies_expires_at at 0x1e8dd2f3790, file src\channel_store.py>, line 30)
             148 MAKE_FUNCTION        (annotation)
             150 STORE_NAME           (_compute_cookies_expires_at)

 42:         152 LOAD_CONST           ("\nCREATE TABLE IF NOT EXISTS channels (\n    id                    TEXT PRIMARY KEY,\n    name                  TEXT,\n    img_src               TEXT,\n    sapisidhash           TEXT,\n    delegated_session_id  TEXT,\n    role                  TEXT,\n    challenge             TEXT,\n    botguardResponse      TEXT,\n    cookies_json          TEXT NOT NULL DEFAULT '[]',\n    cookies_expires_at    INTEGER,\n    created_at            INTEGER NOT NULL,\n    updated_at            INTEGER NOT NULL\n)\n")
             154 STORE_NAME           (_CREATE_TABLE_SQL)

 60:         156 LOAD_CONST           ("conn")
             158 LOAD_NAME            (sqlite3)
             160 LOAD_ATTR            (Connection)
             180 LOAD_CONST           ("return")
             182 LOAD_CONST           (None)
             184 BUILD_TUPLE          4
             186 LOAD_CONST           (<Code311 code object _ensure_schema at 0x1e8dd2f38a0, file src\channel_store.py>, line 60)
             188 MAKE_FUNCTION        (annotation)
             190 STORE_NAME           (_ensure_schema)

 71:         192 LOAD_CONST           ("row")
             194 LOAD_NAME            (sqlite3)
             196 LOAD_ATTR            (Row)
             216 LOAD_CONST           ("return")
             218 LOAD_NAME            (dict)
             220 BUILD_TUPLE          4
             222 LOAD_CONST           (<Code311 code object _row_to_record at 0x1e8dd2f39b0, file src\channel_store.py>, line 71)
             224 MAKE_FUNCTION        (annotation)
             226 STORE_NAME           (_row_to_record)

 97:         228 PUSH_NULL
             230 LOAD_BUILD_CLASS
             232 LOAD_CONST           (<Code311 code object ChannelStore at 0x1e8dd39c490, file src\channel_store.py>, line 97)
             234 MAKE_FUNCTION        (No arguments)
             236 LOAD_CONST           ("ChannelStore")
             238 CALL                 2
             246 STORE_NAME           (ChannelStore)

203:         248 PUSH_NULL
             250 LOAD_NAME            (ChannelStore)
             252 CALL                 0
             260 STORE_NAME           (channel_store)
             262 RETURN_CONST         (None)


# Method Name:       _default_db_path
# Filename:          src\channel_store.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        2
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        19
# Constants:
#    0: None
#    1: 'channels.db'
# Names:
#    0: get_data_dir

 19:           0 RESUME               0

 20:           2 LOAD_GLOBAL          (NULL + get_data_dir)
              12 CALL                 0
              20 LOAD_CONST           ("channels.db")
              22 BINARY_OP            (/)
              26 RETURN_VALUE


# Method Name:       _connect
# Filename:          src\channel_store.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  2
# Stack size:        5
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        23
# Constants:
#    0: None
#    1: True
#    2: ('parents', 'exist_ok')
#    3: False
#    4: ('check_same_thread',)
# Names:
#    0: parent
#    1: mkdir
#    2: sqlite3
#    3: connect
#    4: str
#    5: Row
#    6: row_factory
# Varnames:
#	db_path, conn
# Positional arguments:
#	db_path
# Local variables:
#    1: conn

 23:           0 RESUME               0

 24:           2 LOAD_FAST            (db_path)
               4 LOAD_ATTR            (parent)
              24 LOAD_ATTR            (NULL|self + mkdir)
              44 LOAD_CONST           (True)
              46 LOAD_CONST           (True)
              48 KW_NAMES             (('parents', 'exist_ok'))
              50 CALL                 2
              58 POP_TOP

 25:          60 LOAD_GLOBAL          (NULL + sqlite3)
              70 LOAD_ATTR            (connect)
              90 LOAD_GLOBAL          (NULL + str)
             100 LOAD_FAST            (db_path)
             102 CALL                 1
             110 LOAD_CONST           (False)
             112 KW_NAMES             (('check_same_thread',))
             114 CALL                 2
             122 STORE_FAST           (conn)

 26:         124 LOAD_GLOBAL          (sqlite3)
             134 LOAD_ATTR            (Row)
             154 LOAD_FAST            (conn)
             156 STORE_ATTR           (row_factory)

 27:         166 LOAD_FAST            (conn)
             168 RETURN_VALUE


# Method Name:       _compute_cookies_expires_at
# Filename:          src\channel_store.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  4
# Stack size:        8
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        30
# Constants:
#    0: 'Return the earliest expiration timestamp among all cookies (unix seconds).'
#    1: 'expiry'
#    2: 'expirationDate'
#    3: None
# Names:
#    0: isinstance
#    1: dict
#    2: get
#    3: append
#    4: int
#    5: float
#    6: min
# Varnames:
#	cookies, expiries, c, raw
# Positional arguments:
#	cookies
# Local variables:
#    1: expiries
#    2: c
#    3: raw

 30:           0 RESUME               0

 32:           2 BUILD_LIST           0
               4 STORE_FAST           (expiries)

 33:           6 LOAD_FAST            (cookies)
               8 COPY                 1
              10 POP_JUMP_IF_TRUE     (to 16)
              12 POP_TOP
              14 BUILD_LIST           0
         >>   16 GET_ITER
              18 FOR_ITER             (to 208)
              22 STORE_FAST           (c)

 34:          24 LOAD_GLOBAL          (NULL + isinstance)
              34 LOAD_FAST            (c)
              36 LOAD_GLOBAL          (dict)
              46 CALL                 2
              54 POP_JUMP_IF_TRUE     (to 58)

 35:          56 JUMP_BACKWARD        (to 18)

 36:     >>   58 LOAD_FAST            (c)
              60 LOAD_ATTR            (NULL|self + get)
              80 LOAD_CONST           ("expiry")
              82 CALL                 1
              90 COPY                 1
              92 POP_JUMP_IF_TRUE     (to 128)
              94 POP_TOP
              96 LOAD_FAST            (c)
         >>   98 LOAD_ATTR            (NULL|self + get)
             118 LOAD_CONST           ("expirationDate")
             120 CALL                 1
         >>  128 STORE_FAST           (raw)

 37:         130 LOAD_FAST            (raw)
             132 POP_JUMP_IF_NOT_NONE (to 136)
             134 JUMP_BACKWARD        (to 18)

 38:     >>  136 LOAD_FAST            (expiries)
             138 LOAD_ATTR            (NULL|self + append)
             158 LOAD_GLOBAL          (NULL + int)
             168 LOAD_GLOBAL          (NULL + float)
             178 LOAD_FAST            (raw)
             180 CALL                 1
             188 CALL                 1
             196 CALL                 1
             204 POP_TOP
         >>  206 JUMP_BACKWARD        (to 18)

 33:         208 END_FOR

 39:         210 LOAD_FAST            (expiries)
             212 POP_JUMP_IF_FALSE    (to 236)
             214 LOAD_GLOBAL          (NULL + min)
             224 LOAD_FAST            (expiries)
             226 CALL                 1
             234 RETURN_VALUE
         >>  236 LOAD_CONST           (None)
             238 RETURN_VALUE


# Method Name:       _ensure_schema
# Filename:          src\channel_store.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  3
# Stack size:        5
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        60
# Constants:
#    0: None
#    1: 'PRAGMA table_info(channels)'
#    2: 'name'
#    3: 'cookies_expires_at'
#    4: 'ALTER TABLE channels ADD COLUMN cookies_expires_at INTEGER'
#    5: 'overlay_png'
#    6: 'ALTER TABLE channels ADD COLUMN overlay_png TEXT'
# Names:
#    0: execute
#    1: _CREATE_TABLE_SQL
#    2: fetchall
#    3: commit
# Varnames:
#	conn, r, cols
# Positional arguments:
#	conn
# Local variables:
#    1: r
#    2: cols

 60:           0 RESUME               0

 61:           2 LOAD_FAST            (conn)
               4 LOAD_ATTR            (NULL|self + execute)
              24 LOAD_GLOBAL          (_CREATE_TABLE_SQL)
              34 CALL                 1
              42 POP_TOP

 63:          44 LOAD_FAST            (conn)
              46 LOAD_ATTR            (NULL|self + execute)
              66 LOAD_CONST           ("PRAGMA table_info(channels)")
              68 CALL                 1
              76 LOAD_ATTR            (NULL|self + fetchall)
              96 CALL                 0
             104 GET_ITER
             106 LOAD_FAST_AND_CLEAR  (r)
             108 SWAP                 (TOS <-> TOS1)
             110 BUILD_SET            0
             112 SWAP                 (TOS <-> TOS1)
             114 FOR_ITER             (to 132)
             118 STORE_FAST           (r)
             120 LOAD_FAST            (r)
             122 LOAD_CONST           ("name")
             124 BINARY_SUBSCR
             128 SET_ADD              2
         >>  130 JUMP_BACKWARD        (to 114)
             132 END_FOR
             134 STORE_FAST           (cols)
             136 STORE_FAST           (r)

 64:         138 LOAD_CONST           ("cookies_expires_at")
             140 LOAD_FAST            (cols)
             142 CONTAINS_OP          (not in)
             144 POP_JUMP_IF_FALSE    (to 180)

 65:         146 LOAD_FAST            (conn)
             148 LOAD_ATTR            (NULL|self + execute)
             168 LOAD_CONST           ("ALTER TABLE channels ADD COLUMN cookies_expires_at INTEGER")
             170 CALL                 1
             178 POP_TOP

 66:     >>  180 LOAD_CONST           ("overlay_png")
             182 LOAD_FAST            (cols)
             184 CONTAINS_OP          (not in)
             186 POP_JUMP_IF_FALSE    (to 222)

 67:         188 LOAD_FAST            (conn)
             190 LOAD_ATTR            (NULL|self + execute)
             210 LOAD_CONST           ("ALTER TABLE channels ADD COLUMN overlay_png TEXT")
             212 CALL                 1
             220 POP_TOP

 68:     >>  222 LOAD_FAST            (conn)
             224 LOAD_ATTR            (NULL|self + commit)
             244 CALL                 0
             252 POP_TOP
             254 RETURN_CONST         (None)
             256 SWAP                 (TOS <-> TOS1)
             258 POP_TOP

 63:         260 SWAP                 (TOS <-> TOS1)
             262 STORE_FAST           (r)
             264 RERAISE              0

ExceptionTable:
  110 to 132 -> 256 [2]

# Method Name:       _row_to_record
# Filename:          src\channel_store.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  3
# Stack size:        13
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        71
# Constants:
#    0: None
#    1: 'cookies_json'
#    2: 'id'
#    3: 'name'
#    4: ''
#    5: 'img_src'
#    6: 'sapisidhash'
#    7: 'delegated_session_id'
#    8: 'role'
#    9: 'challenge'
#   10: 'botguardResponse'
#   11: 'cookies_expires_at'
#   12: 'overlay_png'
#   13: ('id', 'name', 'img_src', 'sapisidhash', 'delegated_session_id', 'role', 'challenge', 'botguardResponse', 'cookies', 'cookies_expires_at', 'overlay_png')
# Names:
#    0: json
#    1: loads
#    2: Exception
#    3: keys
# Varnames:
#	row, cookies, raw
# Positional arguments:
#	row
# Local variables:
#    1: cookies
#    2: raw

 71:           0 RESUME               0

 72:           2 BUILD_LIST           0
               4 STORE_FAST           (cookies)

 73:           6 LOAD_FAST            (row)
               8 LOAD_CONST           ("cookies_json")
              10 BINARY_SUBSCR
              14 STORE_FAST           (raw)

 74:          16 LOAD_FAST            (raw)
              18 POP_JUMP_IF_FALSE    (to 64)

 75:          20 NOP

 76:          22 LOAD_GLOBAL          (NULL + json)
              32 LOAD_ATTR            (loads)
              52 LOAD_FAST            (raw)
              54 CALL                 1
              62 STORE_FAST           (cookies)

 80:     >>   64 LOAD_FAST            (row)
              66 LOAD_CONST           ("id")
              68 BINARY_SUBSCR

 81:          72 LOAD_FAST            (row)
              74 LOAD_CONST           ("name")
              76 BINARY_SUBSCR
              80 COPY                 1
              82 POP_JUMP_IF_TRUE     (to 88)
              84 POP_TOP
              86 LOAD_CONST           ("")

 82:     >>   88 LOAD_FAST            (row)
              90 LOAD_CONST           ("img_src")
              92 BINARY_SUBSCR
              96 COPY                 1
              98 POP_JUMP_IF_TRUE     (to 104)
             100 POP_TOP
             102 LOAD_CONST           ("")

 83:     >>  104 LOAD_FAST            (row)
             106 LOAD_CONST           ("sapisidhash")
             108 BINARY_SUBSCR
             112 COPY                 1
             114 POP_JUMP_IF_TRUE     (to 120)
             116 POP_TOP
             118 LOAD_CONST           ("")

 84:     >>  120 LOAD_FAST            (row)
             122 LOAD_CONST           ("delegated_session_id")
             124 BINARY_SUBSCR
             128 COPY                 1
             130 POP_JUMP_IF_TRUE     (to 136)
             132 POP_TOP
             134 LOAD_CONST           ("")

 85:     >>  136 LOAD_FAST            (row)
             138 LOAD_CONST           ("role")
             140 BINARY_SUBSCR
             144 COPY                 1
             146 POP_JUMP_IF_TRUE     (to 152)
             148 POP_TOP
             150 LOAD_CONST           ("")

 86:     >>  152 LOAD_FAST            (row)
             154 LOAD_CONST           ("challenge")
             156 BINARY_SUBSCR
             160 COPY                 1
             162 POP_JUMP_IF_TRUE     (to 168)
             164 POP_TOP
             166 LOAD_CONST           ("")

 87:     >>  168 LOAD_FAST            (row)
             170 LOAD_CONST           ("botguardResponse")
             172 BINARY_SUBSCR
             176 COPY                 1
             178 POP_JUMP_IF_TRUE     (to 184)
             180 POP_TOP
             182 LOAD_CONST           ("")

 88:     >>  184 LOAD_FAST            (cookies)

 89:         186 LOAD_FAST            (row)
             188 LOAD_CONST           ("cookies_expires_at")
             190 BINARY_SUBSCR

 91:         194 LOAD_CONST           ("overlay_png")
             196 LOAD_FAST            (row)
             198 LOAD_ATTR            (NULL|self + keys)
             218 CALL                 0
             226 CONTAINS_OP          (in)
             228 POP_JUMP_IF_FALSE    (to 240)
             230 LOAD_FAST            (row)
             232 LOAD_CONST           ("overlay_png")
             234 BINARY_SUBSCR
             238 JUMP_FORWARD         (to 242)
         >>  240 LOAD_CONST           ("")

 90:     >>  242 COPY                 1
             244 POP_JUMP_IF_TRUE     (to 250)
             246 POP_TOP

 93:         248 LOAD_CONST           ("")

 79:     >>  250 LOAD_CONST           (('id', 'name', 'img_src', 'sapisidhash', 'delegated_session_id', 'role', 'challenge', 'botguardResponse', 'cookies', 'cookies_expires_at', 'overlay_png'))
             252 BUILD_CONST_KEY_MAP  11
             254 RETURN_VALUE
             256 PUSH_EXC_INFO

 77:         258 LOAD_GLOBAL          (Exception)
             268 CHECK_EXC_MATCH
             270 POP_JUMP_IF_FALSE    (to 282)
             272 POP_TOP

 78:         274 BUILD_LIST           0
             276 STORE_FAST           (cookies)
             278 POP_EXCEPT
             280 JUMP_BACKWARD        (to 64)

 77:     >>  282 RERAISE              0
             284 COPY                 3
             286 POP_EXCEPT
             288 RERAISE              1

ExceptionTable:
  22 to 62 -> 256 [0]
  256 to 276 -> 284 [1] lasti
  282 to 282 -> 284 [1] lasti

# Method Name:       ChannelStore
# Filename:          src\channel_store.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        6
# Flags:             0x00000000 (0x0)
# First Line:        97
# Constants:
#    0: 'ChannelStore'
#    1: 'Thin wrapper around an SQLite database for channel CRUD.'
#    2: None
#    3: 'db_path'
#    4: <Code311 code object __init__ at 0x1e8dd2f3ac0, file src\channel_store.py>, line 100
#    5: 'return'
#    6: <Code311 code object init_db at 0x1e8dd2f3bd0, file src\channel_store.py>, line 114
#    7: <Code311 code object conn at 0x1e8dd2f3ce0, file src\channel_store.py>, line 120
#    8: 'record'
#    9: <Code311 code object upsert_channel at 0x1e8dd2f3df0, file src\channel_store.py>, line 128
#   10: <Code311 code object list_channels at 0x1e8dd2f3f00, file src\channel_store.py>, line 170
#   11: 'channel_id'
#   12: <Code311 code object get_channel at 0x1e8dd39c050, file src\channel_store.py>, line 177
#   13: 'path'
#   14: <Code311 code object set_overlay_png at 0x1e8dd39c270, file src\channel_store.py>, line 184
#   15: <Code311 code object delete_channel at 0x1e8dd39c380, file src\channel_store.py>, line 193
#   16: (None,)
#   17: ('return', None)
# Names:
#    0: __name__
#    1: __module__
#    2: __qualname__
#    3: __doc__
#    4: Optional
#    5: Path
#    6: __init__
#    7: init_db
#    8: property
#    9: sqlite3
#   10: Connection
#   11: conn
#   12: dict
#   13: upsert_channel
#   14: list
#   15: list_channels
#   16: str
#   17: get_channel
#   18: set_overlay_png
#   19: bool
#   20: delete_channel

 97:           0 RESUME               0
               2 LOAD_NAME            (__name__)
               4 STORE_NAME           (__module__)
               6 LOAD_CONST           ("ChannelStore")
               8 STORE_NAME           (__qualname__)

 98:          10 LOAD_CONST           ("Thin wrapper around an SQLite database for channel CRUD.")
              12 STORE_NAME           (__doc__)

100:          14 LOAD_CONST           ((None,))
              16 LOAD_CONST           ("db_path")
              18 LOAD_NAME            (Optional)
              20 LOAD_NAME            (Path)
              22 BINARY_SUBSCR
              26 BUILD_TUPLE          2
              28 LOAD_CONST           (<Code311 code object __init__ at 0x1e8dd2f3ac0, file src\channel_store.py>, line 100)
              30 MAKE_FUNCTION        (default, annotation)
              32 STORE_NAME           (__init__)

114:          34 LOAD_CONST           (('return', None))
              36 LOAD_CONST           (<Code311 code object init_db at 0x1e8dd2f3bd0, file src\channel_store.py>, line 114)
              38 MAKE_FUNCTION        (annotation)
              40 STORE_NAME           (init_db)

120:          42 LOAD_NAME            (property)

121:          44 LOAD_CONST           ("return")
              46 LOAD_NAME            (sqlite3)
              48 LOAD_ATTR            (Connection)
              68 BUILD_TUPLE          2
              70 LOAD_CONST           (<Code311 code object conn at 0x1e8dd2f3ce0, file src\channel_store.py>, line 120)
              72 MAKE_FUNCTION        (annotation)

120:          74 CALL                 0

121:          82 STORE_NAME           (conn)

128:          84 LOAD_CONST           ("record")
              86 LOAD_NAME            (dict)
              88 LOAD_CONST           ("return")
              90 LOAD_CONST           (None)
              92 BUILD_TUPLE          4
              94 LOAD_CONST           (<Code311 code object upsert_channel at 0x1e8dd2f3df0, file src\channel_store.py>, line 128)
              96 MAKE_FUNCTION        (annotation)
              98 STORE_NAME           (upsert_channel)

170:         100 LOAD_CONST           ("return")
             102 LOAD_NAME            (list)
             104 LOAD_NAME            (dict)
             106 BINARY_SUBSCR
             110 BUILD_TUPLE          2
             112 LOAD_CONST           (<Code311 code object list_channels at 0x1e8dd2f3f00, file src\channel_store.py>, line 170)
             114 MAKE_FUNCTION        (annotation)
             116 STORE_NAME           (list_channels)

177:         118 LOAD_CONST           ("channel_id")
             120 LOAD_NAME            (str)
             122 LOAD_CONST           ("return")
             124 LOAD_NAME            (Optional)
             126 LOAD_NAME            (dict)
             128 BINARY_SUBSCR
             132 BUILD_TUPLE          4
             134 LOAD_CONST           (<Code311 code object get_channel at 0x1e8dd39c050, file src\channel_store.py>, line 177)
             136 MAKE_FUNCTION        (annotation)
             138 STORE_NAME           (get_channel)

184:         140 LOAD_CONST           ("channel_id")
             142 LOAD_NAME            (str)
             144 LOAD_CONST           ("path")
             146 LOAD_NAME            (str)
             148 LOAD_CONST           ("return")
             150 LOAD_CONST           (None)
             152 BUILD_TUPLE          6
             154 LOAD_CONST           (<Code311 code object set_overlay_png at 0x1e8dd39c270, file src\channel_store.py>, line 184)
             156 MAKE_FUNCTION        (annotation)
             158 STORE_NAME           (set_overlay_png)

193:         160 LOAD_CONST           ("channel_id")
             162 LOAD_NAME            (str)
             164 LOAD_CONST           ("return")
             166 LOAD_NAME            (bool)
             168 BUILD_TUPLE          4
             170 LOAD_CONST           (<Code311 code object delete_channel at 0x1e8dd39c380, file src\channel_store.py>, line 193)
             172 MAKE_FUNCTION        (annotation)
             174 STORE_NAME           (delete_channel)
             176 RETURN_CONST         (None)


# Method Name:       __init__
# Filename:          src\channel_store.py
# Argument count:    2
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  2
# Stack size:        9
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        100
# Constants:
#    0: None
#    1: 'CHANNEL_DB_PATH'
# Names:
#    0: Path
#    1: os
#    2: environ
#    3: get
#    4: str
#    5: _default_db_path
#    6: _db_path
#    7: _conn
#    8: threading
#    9: RLock
#   10: _lock
# Varnames:
#	self, db_path
# Positional arguments:
#	self, db_path

100:           0 RESUME               0

101:           2 LOAD_FAST            (db_path)
               4 COPY                 1
               6 POP_JUMP_IF_TRUE     (to 124)
               8 POP_TOP
              10 LOAD_GLOBAL          (NULL + Path)

102:          20 LOAD_GLOBAL          (os)
              30 LOAD_ATTR            (environ)
              50 LOAD_ATTR            (NULL|self + get)
              70 LOAD_CONST           ("CHANNEL_DB_PATH")
              72 LOAD_GLOBAL          (NULL + str)
              82 LOAD_GLOBAL          (NULL + _default_db_path)
              92 CALL                 0
             100 CALL                 1
             108 CALL                 2

101:         116 CALL                 1
         >>  124 LOAD_FAST            (self)
             126 STORE_ATTR           (_db_path)

104:         136 LOAD_CONST           (None)
             138 LOAD_FAST            (self)
             140 STORE_ATTR           (_conn)

110:         150 LOAD_GLOBAL          (NULL + threading)
             160 LOAD_ATTR            (RLock)
             180 CALL                 0
             188 LOAD_FAST            (self)
             190 STORE_ATTR           (_lock)
             200 RETURN_CONST         (None)


# Method Name:       init_db
# Filename:          src\channel_store.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  1
# Stack size:        6
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        114
# Constants:
#    0: None
# Names:
#    0: _lock
#    1: _conn
#    2: _connect
#    3: _db_path
#    4: _ensure_schema
# Varnames:
#	self
# Positional arguments:
#	self

114:           0 RESUME               0

115:           2 LOAD_FAST            (self)
               4 LOAD_ATTR            (_lock)
              24 BEFORE_WITH
              26 POP_TOP

116:          28 LOAD_FAST            (self)
              30 LOAD_ATTR            (_conn)
              50 POP_JUMP_IF_NOT_NONE (to 146)

117:          52 LOAD_GLOBAL          (NULL + _connect)
              62 LOAD_FAST            (self)
              64 LOAD_ATTR            (_db_path)
              84 CALL                 1
              92 LOAD_FAST            (self)
              94 STORE_ATTR           (_conn)

118:         104 LOAD_GLOBAL          (NULL + _ensure_schema)
             114 LOAD_FAST            (self)
             116 LOAD_ATTR            (_conn)
             136 CALL                 1
             144 POP_TOP

115:     >>  146 LOAD_CONST           (None)
             148 LOAD_CONST           (None)
             150 LOAD_CONST           (None)
             152 CALL                 2
             160 POP_TOP
             162 RETURN_CONST         (None)
             164 PUSH_EXC_INFO
             166 WITH_EXCEPT_START
             168 POP_JUMP_IF_TRUE     (to 172)
             170 RERAISE              2
         >>  172 POP_TOP
             174 POP_EXCEPT
             176 POP_TOP
             178 POP_TOP
             180 RETURN_CONST         (None)
             182 COPY                 3
             184 POP_EXCEPT
             186 RERAISE              1

ExceptionTable:
  26 to 144 -> 164 [1] lasti
  164 to 172 -> 182 [3] lasti

# Method Name:       conn
# Filename:          src\channel_store.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  1
# Stack size:        2
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        120
# Constants:
#    0: None
# Names:
#    0: _conn
#    1: init_db
# Varnames:
#	self
# Positional arguments:
#	self

120:           0 RESUME               0

122:           2 LOAD_FAST            (self)
               4 LOAD_ATTR            (_conn)
              24 POP_JUMP_IF_NOT_NONE (to 58)

123:          26 LOAD_FAST            (self)
              28 LOAD_ATTR            (NULL|self + init_db)
              48 CALL                 0
              56 POP_TOP

124:     >>   58 LOAD_FAST            (self)
              60 LOAD_ATTR            (_conn)
              80 RETURN_VALUE


# Method Name:       upsert_channel
# Filename:          src\channel_store.py
# Argument count:    2
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  14
# Stack size:        16
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        128
# Constants:
#    0: None
#    1: 'id'
#    2: 'name'
#    3: ''
#    4: 'img_src'
#    5: 'sapisidhash'
#    6: 'delegated_session_id'
#    7: 'role'
#    8: 'challenge'
#    9: 'botguardResponse'
#   10: 'cookies'
#   11: False
#   12: ('ensure_ascii',)
#   13: '\n                INSERT INTO channels (\n                    id, name, img_src, sapisidhash, delegated_session_id,\n                    role, challenge, botguardResponse, cookies_json, cookies_expires_at,\n                    created_at, updated_at\n                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\n                ON CONFLICT(id) DO UPDATE SET\n                    name=excluded.name,\n                    img_src=excluded.img_src,\n                    sapisidhash=excluded.sapisidhash,\n                    delegated_session_id=excluded.delegated_session_id,\n                    role=excluded.role,\n                    challenge=excluded.challenge,\n                    botguardResponse=excluded.botguardResponse,\n                    cookies_json=excluded.cookies_json,\n                    cookies_expires_at=excluded.cookies_expires_at,\n                    updated_at=excluded.updated_at\n                '
# Names:
#    0: get
#    1: int
#    2: time
#    3: json
#    4: dumps
#    5: _compute_cookies_expires_at
#    6: _lock
#    7: conn
#    8: execute
#    9: commit
# Varnames:
#	self, record, channel_id, now, name, img_src, sapisidhash, delegated_session_id, role, challenge, botguardResponse, cookies, cookies_json, cookies_expires_at
# Positional arguments:
#	self, record
# Local variables:
#    2: channel_id
#    3: now
#    4: name
#    5: img_src
#    6: sapisidhash
#    7: delegated_session_id
#    8: role
#    9: challenge
#   10: botguardResponse
#   11: cookies
#   12: cookies_json
#   13: cookies_expires_at

128:           0 RESUME               0

129:           2 LOAD_FAST            (record)
               4 LOAD_ATTR            (NULL|self + get)
              24 LOAD_CONST           ("id")
              26 CALL                 1
              34 STORE_FAST           (channel_id)

130:          36 LOAD_GLOBAL          (NULL + int)
              46 LOAD_GLOBAL          (NULL + time)
              56 LOAD_ATTR            (time)
              76 CALL                 0
              84 CALL                 1
              92 STORE_FAST           (now)

131:          94 LOAD_FAST            (record)
              96 LOAD_ATTR            (NULL|self + get)
             116 LOAD_CONST           ("name")
             118 LOAD_CONST           ("")
             120 CALL                 2
             128 STORE_FAST           (name)

132:         130 LOAD_FAST            (record)
             132 LOAD_ATTR            (NULL|self + get)
             152 LOAD_CONST           ("img_src")
             154 LOAD_CONST           ("")
             156 CALL                 2
             164 STORE_FAST           (img_src)

133:         166 LOAD_FAST            (record)
             168 LOAD_ATTR            (NULL|self + get)
             188 LOAD_CONST           ("sapisidhash")
             190 LOAD_CONST           ("")
             192 CALL                 2
             200 STORE_FAST           (sapisidhash)

134:         202 LOAD_FAST            (record)
             204 LOAD_ATTR            (NULL|self + get)
             224 LOAD_CONST           ("delegated_session_id")
             226 LOAD_CONST           ("")
             228 CALL                 2
             236 STORE_FAST           (delegated_session_id)

135:         238 LOAD_FAST            (record)
             240 LOAD_ATTR            (NULL|self + get)
             260 LOAD_CONST           ("role")
             262 LOAD_CONST           ("")
             264 CALL                 2
             272 STORE_FAST           (role)

136:         274 LOAD_FAST            (record)
             276 LOAD_ATTR            (NULL|self + get)
             296 LOAD_CONST           ("challenge")
             298 LOAD_CONST           ("")
             300 CALL                 2
             308 STORE_FAST           (challenge)

137:         310 LOAD_FAST            (record)
             312 LOAD_ATTR            (NULL|self + get)
             332 LOAD_CONST           ("botguardResponse")
             334 LOAD_CONST           ("")
             336 CALL                 2
             344 STORE_FAST           (botguardResponse)

138:         346 LOAD_FAST            (record)
             348 LOAD_ATTR            (NULL|self + get)
             368 LOAD_CONST           ("cookies")
             370 CALL                 1
             378 COPY                 1
             380 POP_JUMP_IF_TRUE     (to 386)
             382 POP_TOP
             384 BUILD_LIST           0
         >>  386 STORE_FAST           (cookies)

139:         388 LOAD_GLOBAL          (NULL + json)
             398 LOAD_ATTR            (dumps)
             418 LOAD_FAST            (cookies)
             420 LOAD_CONST           (False)
             422 KW_NAMES             (('ensure_ascii',))
             424 CALL                 2
             432 STORE_FAST           (cookies_json)

140:         434 LOAD_GLOBAL          (NULL + _compute_cookies_expires_at)
             444 LOAD_FAST            (cookies)
             446 CALL                 1
             454 STORE_FAST           (cookies_expires_at)

142:         456 LOAD_FAST            (self)
             458 LOAD_ATTR            (_lock)
             478 BEFORE_WITH
             480 POP_TOP

143:         482 LOAD_FAST            (self)
             484 LOAD_ATTR            (conn)
             504 LOAD_ATTR            (NULL|self + execute)

144:         524 LOAD_CONST           ("\n                INSERT INTO channels (\n                    id, name, img_src, sapisidhash, delegated_session_id,\n                    role, challenge, botguardResponse, cookies_json, cookies_expires_at,\n                    created_at, updated_at\n                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\n                ON CONFLICT(id) DO UPDATE SET\n                    name=excluded.name,\n                    img_src=excluded.img_src,\n                    sapisidhash=excluded.sapisidhash,\n                    delegated_session_id=excluded.delegated_session_id,\n                    role=excluded.role,\n                    challenge=excluded.challenge,\n                    botguardResponse=excluded.botguardResponse,\n                    cookies_json=excluded.cookies_json,\n                    cookies_expires_at=excluded.cookies_expires_at,\n                    updated_at=excluded.updated_at\n                ")

163:         526 LOAD_FAST            (channel_id)
             528 LOAD_FAST            (name)
             530 LOAD_FAST            (img_src)
             532 LOAD_FAST            (sapisidhash)
             534 LOAD_FAST            (delegated_session_id)

164:         536 LOAD_FAST            (role)
             538 LOAD_FAST            (challenge)
             540 LOAD_FAST            (botguardResponse)
             542 LOAD_FAST            (cookies_json)
             544 LOAD_FAST            (cookies_expires_at)

165:         546 LOAD_FAST            (now)
             548 LOAD_FAST            (now)

162:         550 BUILD_TUPLE          12

143:         552 CALL                 2
             560 POP_TOP

168:         562 LOAD_FAST            (self)
             564 LOAD_ATTR            (conn)
             584 LOAD_ATTR            (NULL|self + commit)
             604 CALL                 0
             612 POP_TOP

142:         614 LOAD_CONST           (None)
             616 LOAD_CONST           (None)
             618 LOAD_CONST           (None)
             620 CALL                 2
             628 POP_TOP
             630 RETURN_CONST         (None)
             632 PUSH_EXC_INFO
             634 WITH_EXCEPT_START
             636 POP_JUMP_IF_TRUE     (to 640)
             638 RERAISE              2
         >>  640 POP_TOP
             642 POP_EXCEPT
             644 POP_TOP
             646 POP_TOP
             648 RETURN_CONST         (None)
             650 COPY                 3
             652 POP_EXCEPT
             654 RERAISE              1

ExceptionTable:
  480 to 612 -> 632 [1] lasti
  632 to 640 -> 650 [3] lasti

# Method Name:       list_channels
# Filename:          src\channel_store.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  3
# Stack size:        6
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        170
# Constants:
#    0: None
#    1: 'SELECT * FROM channels ORDER BY updated_at DESC'
# Names:
#    0: _lock
#    1: conn
#    2: execute
#    3: fetchall
#    4: _row_to_record
# Varnames:
#	self, rows, r
# Positional arguments:
#	self
# Local variables:
#    1: rows
#    2: r

170:           0 RESUME               0

171:           2 LOAD_FAST            (self)
               4 LOAD_ATTR            (_lock)
              24 BEFORE_WITH
              26 POP_TOP

172:          28 LOAD_FAST            (self)
              30 LOAD_ATTR            (conn)
              50 LOAD_ATTR            (NULL|self + execute)

173:          70 LOAD_CONST           ("SELECT * FROM channels ORDER BY updated_at DESC")

172:          72 CALL                 1

174:          80 LOAD_ATTR            (NULL|self + fetchall)
             100 CALL                 0

172:         108 STORE_FAST           (rows)

171:         110 LOAD_CONST           (None)
             112 LOAD_CONST           (None)
             114 LOAD_CONST           (None)
             116 CALL                 2
             124 POP_TOP

175:         126 LOAD_FAST_CHECK      (rows)
             128 GET_ITER
             130 LOAD_FAST_AND_CLEAR  (r)
             132 SWAP                 (TOS <-> TOS1)
             134 BUILD_LIST           0
             136 SWAP                 (TOS <-> TOS1)
             138 FOR_ITER             (to 168)
             142 STORE_FAST           (r)
             144 LOAD_GLOBAL          (NULL + _row_to_record)
             154 LOAD_FAST            (r)
             156 CALL                 1
             164 LIST_APPEND          2
         >>  166 JUMP_BACKWARD        (to 138)
             168 END_FOR
             170 SWAP                 (TOS <-> TOS1)
             172 STORE_FAST           (r)
             174 RETURN_VALUE

171:         176 PUSH_EXC_INFO
             178 WITH_EXCEPT_START
             180 POP_JUMP_IF_TRUE     (to 184)
             182 RERAISE              2
         >>  184 POP_TOP
             186 POP_EXCEPT
             188 POP_TOP
             190 POP_TOP
             192 JUMP_BACKWARD        (to 126)
             194 COPY                 3
             196 POP_EXCEPT
         >>  198 RERAISE              1
             200 SWAP                 (TOS <-> TOS1)
             202 POP_TOP

175:         204 SWAP                 (TOS <-> TOS1)
             206 STORE_FAST           (r)
             208 RERAISE              0

ExceptionTable:
  26 to 108 -> 176 [1] lasti
  134 to 168 -> 200 [2]
  176 to 184 -> 194 [3] lasti

# Method Name:       get_channel
# Filename:          src\channel_store.py
# Argument count:    2
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  3
# Stack size:        6
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        177
# Constants:
#    0: None
#    1: 'SELECT * FROM channels WHERE id = ?'
# Names:
#    0: _lock
#    1: conn
#    2: execute
#    3: fetchone
#    4: _row_to_record
# Varnames:
#	self, channel_id, row
# Positional arguments:
#	self, channel_id
# Local variables:
#    2: row

177:           0 RESUME               0

178:           2 LOAD_FAST            (self)
               4 LOAD_ATTR            (_lock)
              24 BEFORE_WITH
              26 POP_TOP

179:          28 LOAD_FAST            (self)
              30 LOAD_ATTR            (conn)
              50 LOAD_ATTR            (NULL|self + execute)

180:          70 LOAD_CONST           ("SELECT * FROM channels WHERE id = ?")
              72 LOAD_FAST            (channel_id)
              74 BUILD_TUPLE          1

179:          76 CALL                 2

181:          84 LOAD_ATTR            (NULL|self + fetchone)
             104 CALL                 0

179:         112 STORE_FAST           (row)

178:         114 LOAD_CONST           (None)
             116 LOAD_CONST           (None)
             118 LOAD_CONST           (None)
             120 CALL                 2
             128 POP_TOP

182:         130 LOAD_FAST_CHECK      (row)
             132 POP_JUMP_IF_FALSE    (to 156)
             134 LOAD_GLOBAL          (NULL + _row_to_record)
             144 LOAD_FAST            (row)
             146 CALL                 1
             154 RETURN_VALUE
         >>  156 LOAD_CONST           (None)
             158 RETURN_VALUE

178:         160 PUSH_EXC_INFO
             162 WITH_EXCEPT_START
             164 POP_JUMP_IF_TRUE     (to 168)
             166 RERAISE              2
         >>  168 POP_TOP
             170 POP_EXCEPT
             172 POP_TOP
             174 POP_TOP
             176 JUMP_BACKWARD        (to 130)
             178 COPY                 3
             180 POP_EXCEPT
             182 RERAISE              1

ExceptionTable:
  26 to 112 -> 160 [1] lasti
  160 to 168 -> 178 [3] lasti

# Method Name:       set_overlay_png
# Filename:          src\channel_store.py
# Argument count:    3
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  3
# Stack size:        9
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        184
# Constants:
#    0: 'Lưu đường dẫn PNG tên kênh cho một kênh.'
#    1: 'UPDATE channels SET overlay_png=?, updated_at=? WHERE id=?'
#    2: None
# Names:
#    0: _lock
#    1: conn
#    2: execute
#    3: int
#    4: time
#    5: commit
# Varnames:
#	self, channel_id, path
# Positional arguments:
#	self, channel_id, path

184:           0 RESUME               0

186:           2 LOAD_FAST            (self)
               4 LOAD_ATTR            (_lock)
              24 BEFORE_WITH
              26 POP_TOP

187:          28 LOAD_FAST            (self)
              30 LOAD_ATTR            (conn)
              50 LOAD_ATTR            (NULL|self + execute)

188:          70 LOAD_CONST           ("UPDATE channels SET overlay_png=?, updated_at=? WHERE id=?")

189:          72 LOAD_FAST            (path)
              74 LOAD_GLOBAL          (NULL + int)
              84 LOAD_GLOBAL          (NULL + time)
              94 LOAD_ATTR            (time)
             114 CALL                 0
             122 CALL                 1
             130 LOAD_FAST            (channel_id)
             132 BUILD_TUPLE          3

187:         134 CALL                 2
             142 POP_TOP

191:         144 LOAD_FAST            (self)
             146 LOAD_ATTR            (conn)
             166 LOAD_ATTR            (NULL|self + commit)
             186 CALL                 0
             194 POP_TOP

186:         196 LOAD_CONST           (None)
             198 LOAD_CONST           (None)
             200 LOAD_CONST           (None)
             202 CALL                 2
             210 POP_TOP
             212 RETURN_CONST         (None)
             214 PUSH_EXC_INFO
             216 WITH_EXCEPT_START
             218 POP_JUMP_IF_TRUE     (to 222)
             220 RERAISE              2
         >>  222 POP_TOP
             224 POP_EXCEPT
             226 POP_TOP
             228 POP_TOP
             230 RETURN_CONST         (None)
             232 COPY                 3
             234 POP_EXCEPT
             236 RERAISE              1

ExceptionTable:
  26 to 194 -> 214 [1] lasti
  214 to 222 -> 232 [3] lasti

# Method Name:       delete_channel
# Filename:          src\channel_store.py
# Argument count:    2
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  3
# Stack size:        6
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        193
# Constants:
#    0: None
#    1: 'DELETE FROM channels WHERE id = ?'
#    2: 0
# Names:
#    0: _lock
#    1: conn
#    2: execute
#    3: commit
#    4: rowcount
# Varnames:
#	self, channel_id, cur
# Positional arguments:
#	self, channel_id
# Local variables:
#    2: cur

193:           0 RESUME               0

194:           2 LOAD_FAST            (self)
               4 LOAD_ATTR            (_lock)
              24 BEFORE_WITH
              26 POP_TOP

195:          28 LOAD_FAST            (self)
              30 LOAD_ATTR            (conn)
              50 LOAD_ATTR            (NULL|self + execute)

196:          70 LOAD_CONST           ("DELETE FROM channels WHERE id = ?")
              72 LOAD_FAST            (channel_id)
              74 BUILD_TUPLE          1

195:          76 CALL                 2
              84 STORE_FAST           (cur)

198:          86 LOAD_FAST            (self)
              88 LOAD_ATTR            (conn)
             108 LOAD_ATTR            (NULL|self + commit)
             128 CALL                 0
             136 POP_TOP

199:         138 LOAD_FAST            (cur)
             140 LOAD_ATTR            (rowcount)
             160 COPY                 1
             162 POP_JUMP_IF_TRUE     (to 168)
             164 POP_TOP
             166 LOAD_CONST           (0)
         >>  168 LOAD_CONST           (0)
             170 COMPARE_OP           (>)

194:         174 SWAP                 (TOS <-> TOS1)
             176 LOAD_CONST           (None)
             178 LOAD_CONST           (None)
             180 LOAD_CONST           (None)
             182 CALL                 2
             190 POP_TOP
             192 RETURN_VALUE
             194 PUSH_EXC_INFO
             196 WITH_EXCEPT_START
             198 POP_JUMP_IF_TRUE     (to 202)
             200 RERAISE              2
         >>  202 POP_TOP
             204 POP_EXCEPT
             206 POP_TOP
             208 POP_TOP
             210 RETURN_CONST         (None)
             212 COPY                 3
             214 POP_EXCEPT
             216 RERAISE              1

ExceptionTable:
  26 to 172 -> 194 [1] lasti
  194 to 202 -> 212 [3] lasti
```
