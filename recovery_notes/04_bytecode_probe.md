# 04 — CPython 3.12 bytecode probe

## Method and safety

The five selected `.pyc` files were deserialized statically with `xdis 6.3.0`. No code object was passed to `exec`, `eval`, a function constructor, or any import mechanism.

All five files use magic `cb0d0d0a` (magic integer 3531), identified by xdis as CPython 3.12.0 bytecode. The zeroed 16-byte headers originate from PyInstaller extraction and do not prevent code-object loading.

## File-level results

| File | Size | Magic | Load | `co_filename` | Nested code objects |
|---|---:|---|:---:|---|---:|
| `app.pyc` | 670 | `cb0d0d0a` | yes | `app.py` | 0 |
| `route_manager.pyc` | 5908 | `cb0d0d0a` | yes | `src\route_manager.py` | 13 |
| `paths.pyc` | 1203 | `cb0d0d0a` | yes | `src\paths.py` | 1 |
| `state_manager.pyc` | 4548 | `cb0d0d0a` | yes | `src\state_manager.py` | 7 |
| `channel_store.pyc` | 10119 | `cb0d0d0a` | yes | `src\channel_store.py` | 14 |

## Detailed code-object metadata

## `app.pyc`

### `<module>`

- Kind: module
- `co_name`: `<module>`
- `co_filename`: `app.py`
- First line: 1
- Flags: `0x0`; stack size: 7; bytecode: 174 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 0, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': [], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: _(empty)_
- `co_names`: `sys`, `nicegui`, `ui`, `src.route_manager`, `router`, `web.nicegui_patches`, `apply_patches`, `web.views`, `setup_routes`, `getattr`, `_is_frozen`, `run`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `0`
  1. `None`
  2. `('ui',)`
  3. `('router',)`
  4. `('apply_patches',)`
  5. `('*',)`
  6. `'frozen'`
  7. `False`
  8. `'TV Automation'`
  9. `'https://github.com/bmtuan/UPLOADS/blob/main/TVAutomation.png?raw=true'`
  10. `8081`
  11. `120`
  12. `('title', 'favicon', 'port', 'reconnect_timeout', 'reload')`

## `route_manager.pyc`

### `<module>`

- Kind: module
- `co_name`: `<module>`
- `co_filename`: `src\route_manager.py`
- First line: 1
- Flags: `0x0`; stack size: 5; bytecode: 180 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 0, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': [], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: _(empty)_
- `co_names`: `inspect`, `dataclasses`, `dataclass`, `pathlib`, `Path`, `typing`, `Callable`, `Dict`, `Optional`, `Type`, `Union`, `fastapi`, `Request`, `loguru`, `logger`, `nicegui`, `ui`, `src.license_manager`, `is_licensed`, `verify_license`, `Route`, `RouterManager`, `router`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `0`
  1. `None`
  2. `('dataclass',)`
  3. `('Path',)`
  4. `('Callable', 'Dict', 'Optional', 'Type', 'Union')`
  5. `('Request',)`
  6. `('logger',)`
  7. `('ui',)`
  8. `('is_licensed', 'verify_license')`
  9. `<code name='Route' filename='src\\route_manager.py'>`
  10. `'Route'`
  11. `<code name='RouterManager' filename='src\\route_manager.py'>`
  12. `'RouterManager'`

#### `Route`

- Kind: probable class body
- `co_name`: `Route`
- `co_filename`: `src\route_manager.py`
- First line: 13
- Flags: `0x0`; stack size: 4; bytecode: 102 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 0, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': [], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: _(empty)_
- `co_names`: `__name__`, `__module__`, `__qualname__`, `str`, `__annotations__`, `Callable`, `requires_auth`, `bool`, `is_async`, `params`, `Optional`, `Dict`, `Type`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `'Route'`
  1. `'path'`
  2. `'view_func'`
  3. `'title'`
  4. `False`
  5. `'requires_auth'`
  6. `'is_async'`
  7. `None`
  8. `'params'`

#### `RouterManager`

- Kind: probable class body
- `co_name`: `RouterManager`
- `co_filename`: `src\route_manager.py`
- First line: 23
- Flags: `0x0`; stack size: 10; bytecode: 126 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 0, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': [], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: _(empty)_
- `co_names`: `__name__`, `__module__`, `__qualname__`, `NOT_AUTH_PATH`, `__init__`, `str`, `set_start_path`, `Optional`, `Dict`, `Type`, `register`, `setup_routes`, `bool`, `is_authenticated`, `tuple`, `verify_activation_key`, `handle_unauthorized`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `'RouterManager'`
  1. `'/auth'`
  2. `<code name='__init__' filename='src\\route_manager.py'>`
  3. `'path'`
  4. `<code name='set_start_path' filename='src\\route_manager.py'>`
  5. `None`
  6. `'title'`
  7. `'params'`
  8. `<code name='register' filename='src\\route_manager.py'>`
  9. `<code name='setup_routes' filename='src\\route_manager.py'>`
  10. `'return'`
  11. `<code name='is_authenticated' filename='src\\route_manager.py'>`
  12. `'license_key'`
  13. `<code name='verify_activation_key' filename='src\\route_manager.py'>`
  14. `<code name='handle_unauthorized' filename='src\\route_manager.py'>`
  15. `(None,)`

##### `RouterManager.__init__`

- Kind: function/lambda/comprehension
- `co_name`: `__init__`
- `co_filename`: `src\route_manager.py`
- First line: 28
- Flags: `0x3`; stack size: 2; bytecode: 46 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 1, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['self'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `self`
- `co_names`: `routes`, `start_path`, `login_path`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `None`
  1. `'/studio'`
  2. `'/auth'`

##### `RouterManager.set_start_path`

- Kind: function/lambda/comprehension
- `co_name`: `set_start_path`
- `co_filename`: `src\route_manager.py`
- First line: 33
- Flags: `0x3`; stack size: 2; bytecode: 18 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 2, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['self', 'path'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `self`, `path`
- `co_names`: `start_path`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `None`

##### `RouterManager.register`

- Kind: function/lambda/comprehension
- `co_name`: `register`
- `co_filename`: `src\route_manager.py`
- First line: 36
- Flags: `0x3`; stack size: 5; bytecode: 44 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 4, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['self', 'path', 'title', 'params'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `self`, `path`, `title`, `params`, `decorator`
- `co_names`: `Callable`
- `co_freevars`: _(empty)_
- `co_cellvars`: `self`, `path`, `title`, `params`
- `co_consts`:

  0. `None`
  1. `'view_func'`
  2. `<code name='decorator' filename='src\\route_manager.py'>`

###### `RouterManager.register.<locals>.decorator`

- Kind: function/lambda/comprehension
- `co_name`: `decorator`
- `co_filename`: `src\route_manager.py`
- First line: 42
- Flags: `0x13`; stack size: 8; bytecode: 116 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 1, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['view_func'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `view_func`, `is_async`
- `co_names`: `inspect`, `iscoroutinefunction`, `Route`, `routes`
- `co_freevars`: `params`, `path`, `self`, `title`
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `None`
  1. `('path', 'view_func', 'title', 'is_async', 'params')`

##### `RouterManager.setup_routes`

- Kind: function/lambda/comprehension
- `co_name`: `setup_routes`
- `co_filename`: `src\route_manager.py`
- First line: 55
- Flags: `0x3`; stack size: 6; bytecode: 344 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 1, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['self'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `self`, `root_handler`, `route`, `async_route_handler`, `sync_route_handler`
- `co_names`: `ui`, `page`, `routes`, `values`, `is_async`, `path`, `Request`
- `co_freevars`: _(empty)_
- `co_cellvars`: `self`
- `co_consts`:

  0. `None`
  1. `'/'`
  2. `<code name='root_handler' filename='src\\route_manager.py'>`
  3. `'request'`
  4. `<code name='async_route_handler' filename='src\\route_manager.py'>`
  5. `<code name='sync_route_handler' filename='src\\route_manager.py'>`

###### `RouterManager.setup_routes.<locals>.root_handler`

- Kind: function/lambda/comprehension
- `co_name`: `root_handler`
- `co_filename`: `src\route_manager.py`
- First line: 56
- Flags: `0x13`; stack size: 3; bytecode: 86 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 0, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': [], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: _(empty)_
- `co_names`: `ui`, `navigate`, `to`, `start_path`
- `co_freevars`: `self`
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `None`

###### `RouterManager.setup_routes.<locals>.async_route_handler`

- Kind: function/lambda/comprehension
- `co_name`: `async_route_handler`
- `co_filename`: `src\route_manager.py`
- First line: 63
- Flags: `0x93`; stack size: 7; bytecode: 520 bytes
- Exception table: 83 bytes
- Signature metadata: `{'positional_count': 2, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['request', 'route'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `request`, `route`, `param`, `kwargs`, `e`
- `co_names`: `path`, `NOT_AUTH_PATH`, `is_authenticated`, `handle_unauthorized`, `params`, `query_params`, `get`, `view_func`, `Exception`, `logger`, `error`, `ui`, `notify`, `navigate`, `to`
- `co_freevars`: `self`
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `None`
  1. `'Error in async route '`
  2. `': '`
  3. `'An error occurred'`
  4. `'negative'`
  5. `('type',)`
  6. `'/error'`
  7. `()`

###### `RouterManager.setup_routes.<locals>.sync_route_handler`

- Kind: function/lambda/comprehension
- `co_name`: `sync_route_handler`
- `co_filename`: `src\route_manager.py`
- First line: 84
- Flags: `0x13`; stack size: 7; bytecode: 264 bytes
- Exception table: 6 bytes
- Signature metadata: `{'positional_count': 2, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['request', 'route'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `request`, `route`, `param`, `kwargs`
- `co_names`: `path`, `NOT_AUTH_PATH`, `is_authenticated`, `handle_unauthorized`, `params`, `query_params`, `get`, `view_func`
- `co_freevars`: `self`
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `None`
  1. `()`

##### `RouterManager.is_authenticated`

- Kind: function/lambda/comprehension
- `co_name`: `is_authenticated`
- `co_filename`: `src\route_manager.py`
- First line: 97
- Flags: `0x3`; stack size: 2; bytecode: 22 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 1, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['self'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `self`
- `co_names`: `is_licensed`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `'Check if user has a valid license.'`

##### `RouterManager.verify_activation_key`

- Kind: function/lambda/comprehension
- `co_name`: `verify_activation_key`
- `co_filename`: `src\route_manager.py`
- First line: 101
- Flags: `0x3`; stack size: 3; bytecode: 24 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 2, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['self', 'license_key'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `self`, `license_key`
- `co_names`: `verify_license`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `'Verify a license key via Licensify API.'`

##### `RouterManager.handle_unauthorized`

- Kind: function/lambda/comprehension
- `co_name`: `handle_unauthorized`
- `co_filename`: `src\route_manager.py`
- First line: 105
- Flags: `0x3`; stack size: 3; bytecode: 84 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 1, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['self'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `self`
- `co_names`: `ui`, `navigate`, `to`, `login_path`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `'Handle unauthorized access attempts'`

## `paths.pyc`

### `<module>`

- Kind: module
- `co_name`: `<module>`
- `co_filename`: `src\paths.py`
- First line: 1
- Flags: `0x0`; stack size: 2; bytecode: 48 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 0, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': [], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: _(empty)_
- `co_names`: `__doc__`, `os`, `platform`, `pathlib`, `Path`, `get_data_dir`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `'Platform-specific data directory for TV Automation.'`
  1. `0`
  2. `None`
  3. `('Path',)`
  4. `'return'`
  5. `<code name='get_data_dir' filename='src\\paths.py'>`

#### `get_data_dir`

- Kind: function/lambda/comprehension
- `co_name`: `get_data_dir`
- `co_filename`: `src\paths.py`
- First line: 8
- Flags: `0x3`; stack size: 7; bytecode: 462 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 0, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': [], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `base`, `data_dir`
- `co_names`: `platform`, `system`, `Path`, `os`, `environ`, `get`, `home`, `mkdir`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `None`
  1. `'Windows'`
  2. `'APPDATA'`
  3. `'AppData'`
  4. `'Roaming'`
  5. `'Darwin'`
  6. `'Library'`
  7. `'Application Support'`
  8. `'XDG_DATA_HOME'`
  9. `'.local'`
  10. `'share'`
  11. `'TVAutomation'`
  12. `True`
  13. `('parents', 'exist_ok')`

## `state_manager.pyc`

### `<module>`

- Kind: module
- `co_name`: `<module>`
- `co_filename`: `src\state_manager.py`
- First line: 1
- Flags: `0x0`; stack size: 4; bytecode: 106 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 0, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': [], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: _(empty)_
- `co_names`: `__doc__`, `json`, `sqlite3`, `typing`, `Any`, `Dict`, `Optional`, `loguru`, `logger`, `src.paths`, `get_data_dir`, `_CREATE_TABLE_SQL`, `StateManager`, `state_manager`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `'\nState Manager for persisting page states to SQLite.\nProvides automatic save/load functionality for UI components.\n'`
  1. `0`
  2. `None`
  3. `('Any', 'Dict', 'Optional')`
  4. `('logger',)`
  5. `('get_data_dir',)`
  6. `'\nCREATE TABLE IF NOT EXISTS app_state (\n    page_name TEXT PRIMARY KEY,\n    state_json TEXT NOT NULL\n)\n'`
  7. `<code name='StateManager' filename='src\\state_manager.py'>`
  8. `'StateManager'`

#### `StateManager`

- Kind: probable class body
- `co_name`: `StateManager`
- `co_filename`: `src\state_manager.py`
- First line: 22
- Flags: `0x0`; stack size: 7; bytecode: 144 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 0, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': [], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: _(empty)_
- `co_names`: `__name__`, `__module__`, `__qualname__`, `__doc__`, `__init__`, `sqlite3`, `Connection`, `_get_conn`, `str`, `Dict`, `Any`, `bool`, `save_state`, `Optional`, `load_state`, `clear_state`, `clear_all_states`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `'StateManager'`
  1. `'Manages persistent state storage for application pages via SQLite.'`
  2. `<code name='__init__' filename='src\\state_manager.py'>`
  3. `'return'`
  4. `<code name='_get_conn' filename='src\\state_manager.py'>`
  5. `'page_name'`
  6. `'state'`
  7. `<code name='save_state' filename='src\\state_manager.py'>`
  8. `<code name='load_state' filename='src\\state_manager.py'>`
  9. `<code name='clear_state' filename='src\\state_manager.py'>`
  10. `<code name='clear_all_states' filename='src\\state_manager.py'>`
  11. `None`

##### `StateManager.__init__`

- Kind: function/lambda/comprehension
- `co_name`: `__init__`
- `co_filename`: `src\state_manager.py`
- First line: 25
- Flags: `0x3`; stack size: 2; bytecode: 18 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 1, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['self'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `self`
- `co_names`: `_conn`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `None`

##### `StateManager._get_conn`

- Kind: function/lambda/comprehension
- `co_name`: `_get_conn`
- `co_filename`: `src\state_manager.py`
- First line: 28
- Flags: `0x3`; stack size: 5; bytecode: 264 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 1, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['self'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `self`, `db_path`
- `co_names`: `_conn`, `get_data_dir`, `sqlite3`, `connect`, `str`, `execute`, `_CREATE_TABLE_SQL`, `commit`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `None`
  1. `'app_state.db'`
  2. `False`
  3. `('check_same_thread',)`

##### `StateManager.save_state`

- Kind: function/lambda/comprehension
- `co_name`: `save_state`
- `co_filename`: `src\state_manager.py`
- First line: 36
- Flags: `0x3`; stack size: 8; bytecode: 274 bytes
- Exception table: 24 bytes
- Signature metadata: `{'positional_count': 3, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['self', 'page_name', 'state'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `self`, `page_name`, `state`, `e`
- `co_names`: `_get_conn`, `execute`, `json`, `dumps`, `commit`, `Exception`, `logger`, `error`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `'Save state for a specific page.'`
  1. `'INSERT INTO app_state (page_name, state_json) VALUES (?, ?) ON CONFLICT(page_name) DO UPDATE SET state_json=excluded.state_json'`
  2. `False`
  3. `('ensure_ascii',)`
  4. `True`
  5. `'Failed to save state for '`
  6. `': '`
  7. `None`

##### `StateManager.load_state`

- Kind: function/lambda/comprehension
- `co_name`: `load_state`
- `co_filename`: `src\state_manager.py`
- First line: 50
- Flags: `0x3`; stack size: 7; bytecode: 250 bytes
- Exception table: 28 bytes
- Signature metadata: `{'positional_count': 2, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['self', 'page_name'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `self`, `page_name`, `row`, `e`
- `co_names`: `_get_conn`, `execute`, `fetchone`, `json`, `loads`, `Exception`, `logger`, `error`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `'Load state for a specific page.'`
  1. `'SELECT state_json FROM app_state WHERE page_name = ?'`
  2. `None`
  3. `0`
  4. `'Failed to load state for '`
  5. `': '`

##### `StateManager.clear_state`

- Kind: function/lambda/comprehension
- `co_name`: `clear_state`
- `co_filename`: `src\state_manager.py`
- First line: 64
- Flags: `0x3`; stack size: 7; bytecode: 230 bytes
- Exception table: 23 bytes
- Signature metadata: `{'positional_count': 2, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['self', 'page_name'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `self`, `page_name`, `e`
- `co_names`: `_get_conn`, `execute`, `commit`, `Exception`, `logger`, `error`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `'Clear saved state for a specific page.'`
  1. `'DELETE FROM app_state WHERE page_name = ?'`
  2. `True`
  3. `'Failed to clear state for '`
  4. `': '`
  5. `None`
  6. `False`

##### `StateManager.clear_all_states`

- Kind: function/lambda/comprehension
- `co_name`: `clear_all_states`
- `co_filename`: `src\state_manager.py`
- First line: 76
- Flags: `0x3`; stack size: 5; bytecode: 220 bytes
- Exception table: 23 bytes
- Signature metadata: `{'positional_count': 1, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['self'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `self`, `e`
- `co_names`: `_get_conn`, `execute`, `commit`, `Exception`, `logger`, `error`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `'Clear all saved states.'`
  1. `'DELETE FROM app_state'`
  2. `True`
  3. `'Failed to clear all states: '`
  4. `None`
  5. `False`

## `channel_store.pyc`

### `<module>`

- Kind: module
- `co_name`: `<module>`
- `co_filename`: `src\channel_store.py`
- First line: 1
- Flags: `0x0`; stack size: 5; bytecode: 264 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 0, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': [], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: _(empty)_
- `co_names`: `__doc__`, `json`, `os`, `sqlite3`, `threading`, `time`, `pathlib`, `Path`, `typing`, `Optional`, `src.paths`, `get_data_dir`, `_default_db_path`, `Connection`, `_connect`, `list`, `int`, `_compute_cookies_expires_at`, `_CREATE_TABLE_SQL`, `_ensure_schema`, `Row`, `dict`, `_row_to_record`, `ChannelStore`, `channel_store`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `'\nSQLite-based channel storage.\n\nReplaces the old file-based (info.json + cookies.pkl) approach with a single\nSQLite database stored in the platform-specific application data directory.\n'`
  1. `0`
  2. `None`
  3. `('Path',)`
  4. `('Optional',)`
  5. `('get_data_dir',)`
  6. `'return'`
  7. `<code name='_default_db_path' filename='src\\channel_store.py'>`
  8. `'db_path'`
  9. `<code name='_connect' filename='src\\channel_store.py'>`
  10. `'cookies'`
  11. `<code name='_compute_cookies_expires_at' filename='src\\channel_store.py'>`
  12. `"\nCREATE TABLE IF NOT EXISTS channels (\n    id                    TEXT PRIMARY KEY,\n    name                  TEXT,\n    img_src               TEXT,\n    sapisidhash           TEXT,\n    delegated_session_id  TEXT,\n    role                  TEXT,\n    challenge             TEXT,\n    botguardResponse      TEXT,\n    cookies_json          TEXT NOT NULL DEFAULT '[]',\n    cookies_expires_at    INTEGER,\n    created_at            INTEGER NOT NULL,\n    updated_at            INTEGER NOT NULL\n)\n"`
  13. `'conn'`
  14. `<code name='_ensure_schema' filename='src\\channel_store.py'>`
  15. `'row'`
  16. `<code name='_row_to_record' filename='src\\channel_store.py'>`
  17. `<code name='ChannelStore' filename='src\\channel_store.py'>`
  18. `'ChannelStore'`

#### `_default_db_path`

- Kind: function/lambda/comprehension
- `co_name`: `_default_db_path`
- `co_filename`: `src\channel_store.py`
- First line: 19
- Flags: `0x3`; stack size: 2; bytecode: 28 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 0, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': [], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: _(empty)_
- `co_names`: `get_data_dir`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `None`
  1. `'channels.db'`

#### `_connect`

- Kind: function/lambda/comprehension
- `co_name`: `_connect`
- `co_filename`: `src\channel_store.py`
- First line: 23
- Flags: `0x3`; stack size: 5; bytecode: 170 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 1, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['db_path'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `db_path`, `conn`
- `co_names`: `parent`, `mkdir`, `sqlite3`, `connect`, `str`, `Row`, `row_factory`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `None`
  1. `True`
  2. `('parents', 'exist_ok')`
  3. `False`
  4. `('check_same_thread',)`

#### `_compute_cookies_expires_at`

- Kind: function/lambda/comprehension
- `co_name`: `_compute_cookies_expires_at`
- `co_filename`: `src\channel_store.py`
- First line: 30
- Flags: `0x3`; stack size: 8; bytecode: 240 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 1, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['cookies'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `cookies`, `expiries`, `c`, `raw`
- `co_names`: `isinstance`, `dict`, `get`, `append`, `int`, `float`, `min`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `'Return the earliest expiration timestamp among all cookies (unix seconds).'`
  1. `'expiry'`
  2. `'expirationDate'`
  3. `None`

#### `_ensure_schema`

- Kind: function/lambda/comprehension
- `co_name`: `_ensure_schema`
- `co_filename`: `src\channel_store.py`
- First line: 60
- Flags: `0x3`; stack size: 5; bytecode: 266 bytes
- Exception table: 5 bytes
- Signature metadata: `{'positional_count': 1, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['conn'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `conn`, `r`, `cols`
- `co_names`: `execute`, `_CREATE_TABLE_SQL`, `fetchall`, `commit`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `None`
  1. `'PRAGMA table_info(channels)'`
  2. `'name'`
  3. `'cookies_expires_at'`
  4. `'ALTER TABLE channels ADD COLUMN cookies_expires_at INTEGER'`
  5. `'overlay_png'`
  6. `'ALTER TABLE channels ADD COLUMN overlay_png TEXT'`

#### `_row_to_record`

- Kind: function/lambda/comprehension
- `co_name`: `_row_to_record`
- `co_filename`: `src\channel_store.py`
- First line: 71
- Flags: `0x3`; stack size: 13; bytecode: 290 bytes
- Exception table: 17 bytes
- Signature metadata: `{'positional_count': 1, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['row'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `row`, `cookies`, `raw`
- `co_names`: `json`, `loads`, `Exception`, `keys`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `None`
  1. `'cookies_json'`
  2. `'id'`
  3. `'name'`
  4. `''`
  5. `'img_src'`
  6. `'sapisidhash'`
  7. `'delegated_session_id'`
  8. `'role'`
  9. `'challenge'`
  10. `'botguardResponse'`
  11. `'cookies_expires_at'`
  12. `'overlay_png'`
  13. `('id', 'name', 'img_src', 'sapisidhash', 'delegated_session_id', 'role', 'challenge', 'botguardResponse', 'cookies', 'cookies_expires_at', 'overlay_png')`

#### `ChannelStore`

- Kind: probable class body
- `co_name`: `ChannelStore`
- `co_filename`: `src\channel_store.py`
- First line: 97
- Flags: `0x0`; stack size: 6; bytecode: 178 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 0, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': [], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: _(empty)_
- `co_names`: `__name__`, `__module__`, `__qualname__`, `__doc__`, `Optional`, `Path`, `__init__`, `init_db`, `property`, `sqlite3`, `Connection`, `conn`, `dict`, `upsert_channel`, `list`, `list_channels`, `str`, `get_channel`, `set_overlay_png`, `bool`, `delete_channel`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `'ChannelStore'`
  1. `'Thin wrapper around an SQLite database for channel CRUD.'`
  2. `None`
  3. `'db_path'`
  4. `<code name='__init__' filename='src\\channel_store.py'>`
  5. `'return'`
  6. `<code name='init_db' filename='src\\channel_store.py'>`
  7. `<code name='conn' filename='src\\channel_store.py'>`
  8. `'record'`
  9. `<code name='upsert_channel' filename='src\\channel_store.py'>`
  10. `<code name='list_channels' filename='src\\channel_store.py'>`
  11. `'channel_id'`
  12. `<code name='get_channel' filename='src\\channel_store.py'>`
  13. `'path'`
  14. `<code name='set_overlay_png' filename='src\\channel_store.py'>`
  15. `<code name='delete_channel' filename='src\\channel_store.py'>`
  16. `(None,)`
  17. `('return', None)`

##### `ChannelStore.__init__`

- Kind: function/lambda/comprehension
- `co_name`: `__init__`
- `co_filename`: `src\channel_store.py`
- First line: 100
- Flags: `0x3`; stack size: 9; bytecode: 202 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 2, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['self', 'db_path'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `self`, `db_path`
- `co_names`: `Path`, `os`, `environ`, `get`, `str`, `_default_db_path`, `_db_path`, `_conn`, `threading`, `RLock`, `_lock`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `None`
  1. `'CHANNEL_DB_PATH'`

##### `ChannelStore.init_db`

- Kind: function/lambda/comprehension
- `co_name`: `init_db`
- `co_filename`: `src\channel_store.py`
- First line: 114
- Flags: `0x3`; stack size: 6; bytecode: 188 bytes
- Exception table: 11 bytes
- Signature metadata: `{'positional_count': 1, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['self'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `self`
- `co_names`: `_lock`, `_conn`, `_connect`, `_db_path`, `_ensure_schema`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `None`

##### `ChannelStore.conn`

- Kind: function/lambda/comprehension
- `co_name`: `conn`
- `co_filename`: `src\channel_store.py`
- First line: 120
- Flags: `0x3`; stack size: 2; bytecode: 82 bytes
- Exception table: 0 bytes
- Signature metadata: `{'positional_count': 1, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['self'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `self`
- `co_names`: `_conn`, `init_db`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `None`

##### `ChannelStore.upsert_channel`

- Kind: function/lambda/comprehension
- `co_name`: `upsert_channel`
- `co_filename`: `src\channel_store.py`
- First line: 128
- Flags: `0x3`; stack size: 16; bytecode: 656 bytes
- Exception table: 13 bytes
- Signature metadata: `{'positional_count': 2, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['self', 'record'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `self`, `record`, `channel_id`, `now`, `name`, `img_src`, `sapisidhash`, `delegated_session_id`, `role`, `challenge`, `botguardResponse`, `cookies`, `cookies_json`, `cookies_expires_at`
- `co_names`: `get`, `int`, `time`, `json`, `dumps`, `_compute_cookies_expires_at`, `_lock`, `conn`, `execute`, `commit`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `None`
  1. `'id'`
  2. `'name'`
  3. `''`
  4. `'img_src'`
  5. `'sapisidhash'`
  6. `'delegated_session_id'`
  7. `'role'`
  8. `'challenge'`
  9. `'botguardResponse'`
  10. `'cookies'`
  11. `False`
  12. `('ensure_ascii',)`
  13. `'\n                INSERT INTO channels (\n                    id, name, img_src, sapisidhash, delegated_session_id,\n                    role, challenge, botguardResponse, cookies_json, cookies_expires_at,\n                    created_at, updated_at\n                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\n                ON CONFLICT(id) DO UPDATE SET\n                    name=excluded.name,\n                    img_src=excluded.img_src,\n                    sapisidhash=excluded.sapisidhash,\n                    delegated_session_id=excluded.delegated_session_id,\n                    role=excluded.role,\n                    challenge=excluded.challenge,\n                    botguardResponse=excluded.botguardResponse,\n                    cookies_json=excluded.cookies_json,\n                    cookies_expires_at=excluded.cookies_expires_at,\n                    updated_at=excluded.updated_at\n                '`

##### `ChannelStore.list_channels`

- Kind: function/lambda/comprehension
- `co_name`: `list_channels`
- `co_filename`: `src\channel_store.py`
- First line: 170
- Flags: `0x3`; stack size: 6; bytecode: 210 bytes
- Exception table: 17 bytes
- Signature metadata: `{'positional_count': 1, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['self'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `self`, `rows`, `r`
- `co_names`: `_lock`, `conn`, `execute`, `fetchall`, `_row_to_record`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `None`
  1. `'SELECT * FROM channels ORDER BY updated_at DESC'`

##### `ChannelStore.get_channel`

- Kind: function/lambda/comprehension
- `co_name`: `get_channel`
- `co_filename`: `src\channel_store.py`
- First line: 177
- Flags: `0x3`; stack size: 6; bytecode: 184 bytes
- Exception table: 11 bytes
- Signature metadata: `{'positional_count': 2, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['self', 'channel_id'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `self`, `channel_id`, `row`
- `co_names`: `_lock`, `conn`, `execute`, `fetchone`, `_row_to_record`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `None`
  1. `'SELECT * FROM channels WHERE id = ?'`

##### `ChannelStore.set_overlay_png`

- Kind: function/lambda/comprehension
- `co_name`: `set_overlay_png`
- `co_filename`: `src\channel_store.py`
- First line: 184
- Flags: `0x3`; stack size: 9; bytecode: 238 bytes
- Exception table: 12 bytes
- Signature metadata: `{'positional_count': 3, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['self', 'channel_id', 'path'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `self`, `channel_id`, `path`
- `co_names`: `_lock`, `conn`, `execute`, `int`, `time`, `commit`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `'Lưu đường dẫn PNG tên kênh cho một kênh.'`
  1. `'UPDATE channels SET overlay_png=?, updated_at=? WHERE id=?'`
  2. `None`

##### `ChannelStore.delete_channel`

- Kind: function/lambda/comprehension
- `co_name`: `delete_channel`
- `co_filename`: `src\channel_store.py`
- First line: 193
- Flags: `0x3`; stack size: 6; bytecode: 218 bytes
- Exception table: 12 bytes
- Signature metadata: `{'positional_count': 2, 'posonly_count': 0, 'kwonly_count': 0, 'positional_names': ['self', 'channel_id'], 'kwonly_names': [], 'vararg': None, 'varkw': None}`
- `co_varnames`: `self`, `channel_id`, `cur`
- `co_names`: `_lock`, `conn`, `execute`, `commit`, `rowcount`
- `co_freevars`: _(empty)_
- `co_cellvars`: _(empty)_
- `co_consts`:

  0. `None`
  1. `'DELETE FROM channels WHERE id = ?'`
  2. `0`

