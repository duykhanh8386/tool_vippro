# Static CPython 3.12 disassembly — `state_manager.pyc`

Generated with `xdis 6.3.0`; the code object was deserialized but never executed.

```text
# pydisasm version 6.3.0
# CPython Python bytecode 3.12.0 (3531)
#   Disassembled from CPython Python 3.13.13 | packaged by Anaconda, Inc. | (main, Apr 14 2026, 06:12:50) [MSC v.1942 64 bit (AMD64)]
# Timestamp in code: 0 (1970-01-01 07:00:00)
# Source code size mod 2**32: 0 bytes
# Method Name:       <module>
# Filename:          src\state_manager.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        4
# Flags:             0x00000000 (0x0)
# First Line:        1
# Constants:
#    0: '\nState Manager for persisting page states to SQLite.\nProvides automatic save/load functionality for UI components.\n'
#    1: 0
#    2: None
#    3: ('Any', 'Dict', 'Optional')
#    4: ('logger',)
#    5: ('get_data_dir',)
#    6: '\nCREATE TABLE IF NOT EXISTS app_state (\n    page_name TEXT PRIMARY KEY,\n    state_json TEXT NOT NULL\n)\n'
#    7: <Code311 code object StateManager at 0x1e8dd2f3350, file src\state_manager.py>, line 22
#    8: 'StateManager'
# Names:
#    0: __doc__
#    1: json
#    2: sqlite3
#    3: typing
#    4: Any
#    5: Dict
#    6: Optional
#    7: loguru
#    8: logger
#    9: src.paths
#   10: get_data_dir
#   11: _CREATE_TABLE_SQL
#   12: StateManager
#   13: state_manager

  0:           0 RESUME               0

  1:           2 LOAD_CONST           ("\nState Manager for persisting page states to SQLite.\nProvides automatic save/load functionality for UI components.\n")
               4 STORE_NAME           (__doc__)

  6:           6 LOAD_CONST           (0)
               8 LOAD_CONST           (None)
              10 IMPORT_NAME          (json)
              12 STORE_NAME           (json)

  7:          14 LOAD_CONST           (0)
              16 LOAD_CONST           (None)
              18 IMPORT_NAME          (sqlite3)
              20 STORE_NAME           (sqlite3)

  8:          22 LOAD_CONST           (0)
              24 LOAD_CONST           (('Any', 'Dict', 'Optional'))
              26 IMPORT_NAME          (typing)
              28 IMPORT_FROM          (Any)
              30 STORE_NAME           (Any)
              32 IMPORT_FROM          (Dict)
              34 STORE_NAME           (Dict)
              36 IMPORT_FROM          (Optional)
              38 STORE_NAME           (Optional)
              40 POP_TOP

 10:          42 LOAD_CONST           (0)
              44 LOAD_CONST           (('logger',))
              46 IMPORT_NAME          (loguru)
              48 IMPORT_FROM          (logger)
              50 STORE_NAME           (logger)
              52 POP_TOP

 12:          54 LOAD_CONST           (0)
              56 LOAD_CONST           (('get_data_dir',))
              58 IMPORT_NAME          (src.paths)
              60 IMPORT_FROM          (get_data_dir)
              62 STORE_NAME           (get_data_dir)
              64 POP_TOP

 14:          66 LOAD_CONST           ("\nCREATE TABLE IF NOT EXISTS app_state (\n    page_name TEXT PRIMARY KEY,\n    state_json TEXT NOT NULL\n)\n")
              68 STORE_NAME           (_CREATE_TABLE_SQL)

 22:          70 PUSH_NULL
              72 LOAD_BUILD_CLASS
              74 LOAD_CONST           (<Code311 code object StateManager at 0x1e8dd2f3350, file src\state_manager.py>, line 22)
              76 MAKE_FUNCTION        (No arguments)
              78 LOAD_CONST           ("StateManager")
              80 CALL                 2
              88 STORE_NAME           (StateManager)

 88:          90 PUSH_NULL
              92 LOAD_NAME            (StateManager)
              94 CALL                 0
             102 STORE_NAME           (state_manager)
             104 RETURN_CONST         (None)


# Method Name:       StateManager
# Filename:          src\state_manager.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        7
# Flags:             0x00000000 (0x0)
# First Line:        22
# Constants:
#    0: 'StateManager'
#    1: 'Manages persistent state storage for application pages via SQLite.'
#    2: <Code311 code object __init__ at 0x1e8dd2f2be0, file src\state_manager.py>, line 25
#    3: 'return'
#    4: <Code311 code object _get_conn at 0x1e8dd2f2cf0, file src\state_manager.py>, line 28
#    5: 'page_name'
#    6: 'state'
#    7: <Code311 code object save_state at 0x1e8dd2f2e00, file src\state_manager.py>, line 36
#    8: <Code311 code object load_state at 0x1e8dd2f2f10, file src\state_manager.py>, line 50
#    9: <Code311 code object clear_state at 0x1e8dd2f3130, file src\state_manager.py>, line 64
#   10: <Code311 code object clear_all_states at 0x1e8dd2f3240, file src\state_manager.py>, line 76
#   11: None
# Names:
#    0: __name__
#    1: __module__
#    2: __qualname__
#    3: __doc__
#    4: __init__
#    5: sqlite3
#    6: Connection
#    7: _get_conn
#    8: str
#    9: Dict
#   10: Any
#   11: bool
#   12: save_state
#   13: Optional
#   14: load_state
#   15: clear_state
#   16: clear_all_states

 22:           0 RESUME               0
               2 LOAD_NAME            (__name__)
               4 STORE_NAME           (__module__)
               6 LOAD_CONST           ("StateManager")
               8 STORE_NAME           (__qualname__)

 23:          10 LOAD_CONST           ("Manages persistent state storage for application pages via SQLite.")
              12 STORE_NAME           (__doc__)

 25:          14 LOAD_CONST           (<Code311 code object __init__ at 0x1e8dd2f2be0, file src\state_manager.py>, line 25)
              16 MAKE_FUNCTION        (No arguments)
              18 STORE_NAME           (__init__)

 28:          20 LOAD_CONST           ("return")
              22 LOAD_NAME            (sqlite3)
              24 LOAD_ATTR            (Connection)
              44 BUILD_TUPLE          2
              46 LOAD_CONST           (<Code311 code object _get_conn at 0x1e8dd2f2cf0, file src\state_manager.py>, line 28)
              48 MAKE_FUNCTION        (annotation)
              50 STORE_NAME           (_get_conn)

 36:          52 LOAD_CONST           ("page_name")
              54 LOAD_NAME            (str)
              56 LOAD_CONST           ("state")
              58 LOAD_NAME            (Dict)
              60 LOAD_NAME            (str)
              62 LOAD_NAME            (Any)
              64 BUILD_TUPLE          2
              66 BINARY_SUBSCR
              70 LOAD_CONST           ("return")
              72 LOAD_NAME            (bool)
              74 BUILD_TUPLE          6
              76 LOAD_CONST           (<Code311 code object save_state at 0x1e8dd2f2e00, file src\state_manager.py>, line 36)
              78 MAKE_FUNCTION        (annotation)
              80 STORE_NAME           (save_state)

 50:          82 LOAD_CONST           ("page_name")
              84 LOAD_NAME            (str)
              86 LOAD_CONST           ("return")
              88 LOAD_NAME            (Optional)
              90 LOAD_NAME            (Dict)
              92 LOAD_NAME            (str)
              94 LOAD_NAME            (Any)
              96 BUILD_TUPLE          2
              98 BINARY_SUBSCR
             102 BINARY_SUBSCR
             106 BUILD_TUPLE          4
             108 LOAD_CONST           (<Code311 code object load_state at 0x1e8dd2f2f10, file src\state_manager.py>, line 50)
             110 MAKE_FUNCTION        (annotation)
             112 STORE_NAME           (load_state)

 64:         114 LOAD_CONST           ("page_name")
             116 LOAD_NAME            (str)
             118 LOAD_CONST           ("return")
             120 LOAD_NAME            (bool)
             122 BUILD_TUPLE          4
             124 LOAD_CONST           (<Code311 code object clear_state at 0x1e8dd2f3130, file src\state_manager.py>, line 64)
             126 MAKE_FUNCTION        (annotation)
             128 STORE_NAME           (clear_state)

 76:         130 LOAD_CONST           ("return")
             132 LOAD_NAME            (bool)
             134 BUILD_TUPLE          2
             136 LOAD_CONST           (<Code311 code object clear_all_states at 0x1e8dd2f3240, file src\state_manager.py>, line 76)
             138 MAKE_FUNCTION        (annotation)
             140 STORE_NAME           (clear_all_states)
             142 RETURN_CONST         (None)


# Method Name:       __init__
# Filename:          src\state_manager.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  1
# Stack size:        2
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        25
# Constants:
#    0: None
# Names:
#    0: _conn
# Varnames:
#	self
# Positional arguments:
#	self

 25:           0 RESUME               0

 26:           2 LOAD_CONST           (None)
               4 LOAD_FAST            (self)
               6 STORE_ATTR           (_conn)
              16 RETURN_CONST         (None)


# Method Name:       _get_conn
# Filename:          src\state_manager.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  2
# Stack size:        5
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        28
# Constants:
#    0: None
#    1: 'app_state.db'
#    2: False
#    3: ('check_same_thread',)
# Names:
#    0: _conn
#    1: get_data_dir
#    2: sqlite3
#    3: connect
#    4: str
#    5: execute
#    6: _CREATE_TABLE_SQL
#    7: commit
# Varnames:
#	self, db_path
# Positional arguments:
#	self
# Local variables:
#    1: db_path

 28:           0 RESUME               0

 29:           2 LOAD_FAST            (self)
               4 LOAD_ATTR            (_conn)
              24 POP_JUMP_IF_NOT_NONE (to 240)

 30:          26 LOAD_GLOBAL          (NULL + get_data_dir)
              36 CALL                 0
              44 LOAD_CONST           ("app_state.db")
              46 BINARY_OP            (/)
              50 STORE_FAST           (db_path)

 31:          52 LOAD_GLOBAL          (NULL + sqlite3)
              62 LOAD_ATTR            (connect)
              82 LOAD_GLOBAL          (NULL + str)
              92 LOAD_FAST            (db_path)
              94 CALL                 1
             102 LOAD_CONST           (False)
             104 KW_NAMES             (('check_same_thread',))
             106 CALL                 2
             114 LOAD_FAST            (self)
             116 STORE_ATTR           (_conn)

 32:         126 LOAD_FAST            (self)
             128 LOAD_ATTR            (_conn)
             148 LOAD_ATTR            (NULL|self + execute)
             168 LOAD_GLOBAL          (_CREATE_TABLE_SQL)
             178 CALL                 1
             186 POP_TOP

 33:         188 LOAD_FAST            (self)
             190 LOAD_ATTR            (_conn)
             210 LOAD_ATTR            (NULL|self + commit)
             230 CALL                 0
             238 POP_TOP

 34:     >>  240 LOAD_FAST            (self)
             242 LOAD_ATTR            (_conn)
             262 RETURN_VALUE


# Method Name:       save_state
# Filename:          src\state_manager.py
# Argument count:    3
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  4
# Stack size:        8
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        36
# Constants:
#    0: 'Save state for a specific page.'
#    1: 'INSERT INTO app_state (page_name, state_json) VALUES (?, ?) ON CONFLICT(page_name) DO UPDATE SET state_json=excluded.state_json'
#    2: False
#    3: ('ensure_ascii',)
#    4: True
#    5: 'Failed to save state for '
#    6: ': '
#    7: None
# Names:
#    0: _get_conn
#    1: execute
#    2: json
#    3: dumps
#    4: commit
#    5: Exception
#    6: logger
#    7: error
# Varnames:
#	self, page_name, state, e
# Positional arguments:
#	self, page_name, state
# Local variables:
#    3: e

 36:           0 RESUME               0

 38:           2 NOP

 39:           4 LOAD_FAST            (self)
               6 LOAD_ATTR            (NULL|self + _get_conn)
              26 CALL                 0
              34 LOAD_ATTR            (NULL|self + execute)

 40:          54 LOAD_CONST           ("INSERT INTO app_state (page_name, state_json) VALUES (?, ?) ON CONFLICT(page_name) DO UPDATE SET state_json=excluded.state_json")

 42:          56 LOAD_FAST            (page_name)
              58 LOAD_GLOBAL          (NULL + json)
              68 LOAD_ATTR            (dumps)
              88 LOAD_FAST            (state)
              90 LOAD_CONST           (False)
              92 KW_NAMES             (('ensure_ascii',))
              94 CALL                 2
             102 BUILD_TUPLE          2

 39:         104 CALL                 2
             112 POP_TOP

 44:         114 LOAD_FAST            (self)
             116 LOAD_ATTR            (NULL|self + _get_conn)
             136 CALL                 0
             144 LOAD_ATTR            (NULL|self + commit)
             164 CALL                 0
             172 POP_TOP

 45:         174 RETURN_CONST         (True)
             176 PUSH_EXC_INFO

 46:         178 LOAD_GLOBAL          (Exception)
             188 CHECK_EXC_MATCH
             190 POP_JUMP_IF_FALSE    (to 266)
             192 STORE_FAST           (e)

 47:         194 LOAD_GLOBAL          (NULL + logger)
             204 LOAD_ATTR            (error)
             224 LOAD_CONST           ("Failed to save state for ")
             226 LOAD_FAST            (page_name)
             228 FORMAT_VALUE         0
             230 LOAD_CONST           (": ")
             232 LOAD_FAST            (e)
             234 FORMAT_VALUE         0
             236 BUILD_STRING         4
             238 CALL                 1
             246 POP_TOP

 48:         248 POP_EXCEPT
             250 LOAD_CONST           (None)
             252 STORE_FAST           (e)
             254 DELETE_FAST          (e)
             256 RETURN_CONST         (False)
             258 LOAD_CONST           (None)
             260 STORE_FAST           (e)
             262 DELETE_FAST          (e)
             264 RERAISE              1

 46:     >>  266 RERAISE              0
             268 COPY                 3
             270 POP_EXCEPT
             272 RERAISE              1

ExceptionTable:
  4 to 172 -> 176 [0]
  176 to 192 -> 268 [1] lasti
  194 to 246 -> 258 [1] lasti
  258 to 266 -> 268 [1] lasti

# Method Name:       load_state
# Filename:          src\state_manager.py
# Argument count:    2
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  4
# Stack size:        7
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        50
# Constants:
#    0: 'Load state for a specific page.'
#    1: 'SELECT state_json FROM app_state WHERE page_name = ?'
#    2: None
#    3: 0
#    4: 'Failed to load state for '
#    5: ': '
# Names:
#    0: _get_conn
#    1: execute
#    2: fetchone
#    3: json
#    4: loads
#    5: Exception
#    6: logger
#    7: error
# Varnames:
#	self, page_name, row, e
# Positional arguments:
#	self, page_name
# Local variables:
#    2: row
#    3: e

 50:           0 RESUME               0

 52:           2 NOP

 53:           4 LOAD_FAST            (self)
               6 LOAD_ATTR            (NULL|self + _get_conn)
              26 CALL                 0
              34 LOAD_ATTR            (NULL|self + execute)

 54:          54 LOAD_CONST           ("SELECT state_json FROM app_state WHERE page_name = ?")

 55:          56 LOAD_FAST            (page_name)
              58 BUILD_TUPLE          1

 53:          60 CALL                 2

 56:          68 LOAD_ATTR            (NULL|self + fetchone)
              88 CALL                 0

 53:          96 STORE_FAST           (row)

 57:          98 LOAD_FAST            (row)
             100 POP_JUMP_IF_NOT_NONE (to 104)

 58:         102 RETURN_CONST         (None)

 59:     >>  104 LOAD_GLOBAL          (NULL + json)
             114 LOAD_ATTR            (loads)
             134 LOAD_FAST            (row)
             136 LOAD_CONST           (0)
             138 BINARY_SUBSCR
             142 CALL                 1
             150 RETURN_VALUE
             152 PUSH_EXC_INFO

 60:         154 LOAD_GLOBAL          (Exception)
             164 CHECK_EXC_MATCH
             166 POP_JUMP_IF_FALSE    (to 242)
             168 STORE_FAST           (e)

 61:         170 LOAD_GLOBAL          (NULL + logger)
             180 LOAD_ATTR            (error)
             200 LOAD_CONST           ("Failed to load state for ")
             202 LOAD_FAST            (page_name)
             204 FORMAT_VALUE         0
             206 LOAD_CONST           (": ")
             208 LOAD_FAST            (e)
             210 FORMAT_VALUE         0
             212 BUILD_STRING         4
             214 CALL                 1
             222 POP_TOP

 62:         224 POP_EXCEPT
             226 LOAD_CONST           (None)
             228 STORE_FAST           (e)
             230 DELETE_FAST          (e)
             232 RETURN_CONST         (None)
             234 LOAD_CONST           (None)
             236 STORE_FAST           (e)
             238 DELETE_FAST          (e)
             240 RERAISE              1

 60:     >>  242 RERAISE              0
             244 COPY                 3
             246 POP_EXCEPT
             248 RERAISE              1

ExceptionTable:
  4 to 100 -> 152 [0]
  104 to 148 -> 152 [0]
  152 to 168 -> 244 [1] lasti
  170 to 222 -> 234 [1] lasti
  234 to 242 -> 244 [1] lasti

# Method Name:       clear_state
# Filename:          src\state_manager.py
# Argument count:    2
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  3
# Stack size:        7
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        64
# Constants:
#    0: 'Clear saved state for a specific page.'
#    1: 'DELETE FROM app_state WHERE page_name = ?'
#    2: True
#    3: 'Failed to clear state for '
#    4: ': '
#    5: None
#    6: False
# Names:
#    0: _get_conn
#    1: execute
#    2: commit
#    3: Exception
#    4: logger
#    5: error
# Varnames:
#	self, page_name, e
# Positional arguments:
#	self, page_name
# Local variables:
#    2: e

 64:           0 RESUME               0

 66:           2 NOP

 67:           4 LOAD_FAST            (self)
               6 LOAD_ATTR            (NULL|self + _get_conn)
              26 CALL                 0
              34 LOAD_ATTR            (NULL|self + execute)

 68:          54 LOAD_CONST           ("DELETE FROM app_state WHERE page_name = ?")
              56 LOAD_FAST            (page_name)
              58 BUILD_TUPLE          1

 67:          60 CALL                 2
              68 POP_TOP

 70:          70 LOAD_FAST            (self)
              72 LOAD_ATTR            (NULL|self + _get_conn)
              92 CALL                 0
             100 LOAD_ATTR            (NULL|self + commit)
             120 CALL                 0
             128 POP_TOP

 71:         130 RETURN_CONST         (True)
             132 PUSH_EXC_INFO

 72:         134 LOAD_GLOBAL          (Exception)
             144 CHECK_EXC_MATCH
             146 POP_JUMP_IF_FALSE    (to 222)
             148 STORE_FAST           (e)

 73:         150 LOAD_GLOBAL          (NULL + logger)
             160 LOAD_ATTR            (error)
             180 LOAD_CONST           ("Failed to clear state for ")
             182 LOAD_FAST            (page_name)
             184 FORMAT_VALUE         0
             186 LOAD_CONST           (": ")
             188 LOAD_FAST            (e)
             190 FORMAT_VALUE         0
             192 BUILD_STRING         4
             194 CALL                 1
             202 POP_TOP

 74:         204 POP_EXCEPT
             206 LOAD_CONST           (None)
             208 STORE_FAST           (e)
             210 DELETE_FAST          (e)
             212 RETURN_CONST         (False)
             214 LOAD_CONST           (None)
             216 STORE_FAST           (e)
             218 DELETE_FAST          (e)
             220 RERAISE              1

 72:     >>  222 RERAISE              0
             224 COPY                 3
             226 POP_EXCEPT
             228 RERAISE              1

ExceptionTable:
  4 to 128 -> 132 [0]
  132 to 148 -> 224 [1] lasti
  150 to 202 -> 214 [1] lasti
  214 to 222 -> 224 [1] lasti

# Method Name:       clear_all_states
# Filename:          src\state_manager.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  2
# Stack size:        5
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        76
# Constants:
#    0: 'Clear all saved states.'
#    1: 'DELETE FROM app_state'
#    2: True
#    3: 'Failed to clear all states: '
#    4: None
#    5: False
# Names:
#    0: _get_conn
#    1: execute
#    2: commit
#    3: Exception
#    4: logger
#    5: error
# Varnames:
#	self, e
# Positional arguments:
#	self
# Local variables:
#    1: e

 76:           0 RESUME               0

 78:           2 NOP

 79:           4 LOAD_FAST            (self)
               6 LOAD_ATTR            (NULL|self + _get_conn)
              26 CALL                 0
              34 LOAD_ATTR            (NULL|self + execute)
              54 LOAD_CONST           ("DELETE FROM app_state")
              56 CALL                 1
              64 POP_TOP

 80:          66 LOAD_FAST            (self)
              68 LOAD_ATTR            (NULL|self + _get_conn)
              88 CALL                 0
              96 LOAD_ATTR            (NULL|self + commit)
             116 CALL                 0
             124 POP_TOP

 81:         126 RETURN_CONST         (True)
             128 PUSH_EXC_INFO

 82:         130 LOAD_GLOBAL          (Exception)
             140 CHECK_EXC_MATCH
             142 POP_JUMP_IF_FALSE    (to 212)
             144 STORE_FAST           (e)

 83:         146 LOAD_GLOBAL          (NULL + logger)
             156 LOAD_ATTR            (error)
             176 LOAD_CONST           ("Failed to clear all states: ")
             178 LOAD_FAST            (e)
             180 FORMAT_VALUE         0
             182 BUILD_STRING         2
             184 CALL                 1
             192 POP_TOP

 84:         194 POP_EXCEPT
             196 LOAD_CONST           (None)
             198 STORE_FAST           (e)
             200 DELETE_FAST          (e)
             202 RETURN_CONST         (False)
             204 LOAD_CONST           (None)
             206 STORE_FAST           (e)
             208 DELETE_FAST          (e)
             210 RERAISE              1

 82:     >>  212 RERAISE              0
             214 COPY                 3
             216 POP_EXCEPT
             218 RERAISE              1

ExceptionTable:
  4 to 124 -> 128 [0]
  128 to 144 -> 214 [1] lasti
  146 to 192 -> 204 [1] lasti
  204 to 212 -> 214 [1] lasti
```
