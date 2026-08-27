# Static CPython 3.12 disassembly — `route_manager.pyc`

Generated with `xdis 6.3.0`; the code object was deserialized but never executed.

```text
# pydisasm version 6.3.0
# CPython Python bytecode 3.12.0 (3531)
#   Disassembled from CPython Python 3.13.13 | packaged by Anaconda, Inc. | (main, Apr 14 2026, 06:12:50) [MSC v.1942 64 bit (AMD64)]
# Timestamp in code: 0 (1970-01-01 07:00:00)
# Source code size mod 2**32: 0 bytes
# Method Name:       <module>
# Filename:          src\route_manager.py
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
#    2: ('dataclass',)
#    3: ('Path',)
#    4: ('Callable', 'Dict', 'Optional', 'Type', 'Union')
#    5: ('Request',)
#    6: ('logger',)
#    7: ('ui',)
#    8: ('is_licensed', 'verify_license')
#    9: <Code311 code object Route at 0x1e8dd302270, file src\route_manager.py>, line 13
#   10: 'Route'
#   11: <Code311 code object RouterManager at 0x1e8dd2f29c0, file src\route_manager.py>, line 23
#   12: 'RouterManager'
# Names:
#    0: inspect
#    1: dataclasses
#    2: dataclass
#    3: pathlib
#    4: Path
#    5: typing
#    6: Callable
#    7: Dict
#    8: Optional
#    9: Type
#   10: Union
#   11: fastapi
#   12: Request
#   13: loguru
#   14: logger
#   15: nicegui
#   16: ui
#   17: src.license_manager
#   18: is_licensed
#   19: verify_license
#   20: Route
#   21: RouterManager
#   22: router

  0:           0 RESUME               0

  1:           2 LOAD_CONST           (0)
               4 LOAD_CONST           (None)
               6 IMPORT_NAME          (inspect)
               8 STORE_NAME           (inspect)

  2:          10 LOAD_CONST           (0)
              12 LOAD_CONST           (('dataclass',))
              14 IMPORT_NAME          (dataclasses)
              16 IMPORT_FROM          (dataclass)
              18 STORE_NAME           (dataclass)
              20 POP_TOP

  3:          22 LOAD_CONST           (0)
              24 LOAD_CONST           (('Path',))
              26 IMPORT_NAME          (pathlib)
              28 IMPORT_FROM          (Path)
              30 STORE_NAME           (Path)
              32 POP_TOP

  4:          34 LOAD_CONST           (0)
              36 LOAD_CONST           (('Callable', 'Dict', 'Optional', 'Type', 'Union'))
              38 IMPORT_NAME          (typing)
              40 IMPORT_FROM          (Callable)
              42 STORE_NAME           (Callable)
              44 IMPORT_FROM          (Dict)
              46 STORE_NAME           (Dict)
              48 IMPORT_FROM          (Optional)
              50 STORE_NAME           (Optional)
              52 IMPORT_FROM          (Type)
              54 STORE_NAME           (Type)
              56 IMPORT_FROM          (Union)
              58 STORE_NAME           (Union)
              60 POP_TOP

  6:          62 LOAD_CONST           (0)
              64 LOAD_CONST           (('Request',))
              66 IMPORT_NAME          (fastapi)
              68 IMPORT_FROM          (Request)
              70 STORE_NAME           (Request)
              72 POP_TOP

  7:          74 LOAD_CONST           (0)
              76 LOAD_CONST           (('logger',))
              78 IMPORT_NAME          (loguru)
              80 IMPORT_FROM          (logger)
              82 STORE_NAME           (logger)
              84 POP_TOP

  8:          86 LOAD_CONST           (0)
              88 LOAD_CONST           (('ui',))
              90 IMPORT_NAME          (nicegui)
              92 IMPORT_FROM          (ui)
              94 STORE_NAME           (ui)
              96 POP_TOP

 10:          98 LOAD_CONST           (0)
             100 LOAD_CONST           (('is_licensed', 'verify_license'))
             102 IMPORT_NAME          (src.license_manager)
             104 IMPORT_FROM          (is_licensed)
             106 STORE_NAME           (is_licensed)
             108 IMPORT_FROM          (verify_license)
             110 STORE_NAME           (verify_license)
             112 POP_TOP

 13:         114 LOAD_NAME            (dataclass)

 14:         116 PUSH_NULL
             118 LOAD_BUILD_CLASS
             120 LOAD_CONST           (<Code311 code object Route at 0x1e8dd302270, file src\route_manager.py>, line 13)
             122 MAKE_FUNCTION        (No arguments)
             124 LOAD_CONST           ("Route")
             126 CALL                 2

 13:         134 CALL                 0

 14:         142 STORE_NAME           (Route)

 23:         144 PUSH_NULL
             146 LOAD_BUILD_CLASS
             148 LOAD_CONST           (<Code311 code object RouterManager at 0x1e8dd2f29c0, file src\route_manager.py>, line 23)
             150 MAKE_FUNCTION        (No arguments)
             152 LOAD_CONST           ("RouterManager")
             154 CALL                 2
             162 STORE_NAME           (RouterManager)

110:         164 PUSH_NULL
             166 LOAD_NAME            (RouterManager)
             168 CALL                 0
             176 STORE_NAME           (router)
             178 RETURN_CONST         (None)


# Method Name:       Route
# Filename:          src\route_manager.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        4
# Flags:             0x00000000 (0x0)
# First Line:        13
# Constants:
#    0: 'Route'
#    1: 'path'
#    2: 'view_func'
#    3: 'title'
#    4: False
#    5: 'requires_auth'
#    6: 'is_async'
#    7: None
#    8: 'params'
# Names:
#    0: __name__
#    1: __module__
#    2: __qualname__
#    3: str
#    4: __annotations__
#    5: Callable
#    6: requires_auth
#    7: bool
#    8: is_async
#    9: params
#   10: Optional
#   11: Dict
#   12: Type

 13:           0 RESUME               0
               2 LOAD_NAME            (__name__)
               4 STORE_NAME           (__module__)
               6 LOAD_CONST           ("Route")
               8 STORE_NAME           (__qualname__)
              10 SETUP_ANNOTATIONS

 15:          12 LOAD_NAME            (str)
              14 LOAD_NAME            (__annotations__)
              16 LOAD_CONST           ("path")
              18 STORE_SUBSCR

 16:          22 LOAD_NAME            (Callable)
              24 LOAD_NAME            (__annotations__)
              26 LOAD_CONST           ("view_func")
              28 STORE_SUBSCR

 17:          32 LOAD_NAME            (str)
              34 LOAD_NAME            (__annotations__)
              36 LOAD_CONST           ("title")
              38 STORE_SUBSCR

 18:          42 LOAD_CONST           (False)
              44 STORE_NAME           (requires_auth)
              46 LOAD_NAME            (bool)
              48 LOAD_NAME            (__annotations__)
              50 LOAD_CONST           ("requires_auth")
              52 STORE_SUBSCR

 19:          56 LOAD_CONST           (False)
              58 STORE_NAME           (is_async)
              60 LOAD_NAME            (bool)
              62 LOAD_NAME            (__annotations__)
              64 LOAD_CONST           ("is_async")
              66 STORE_SUBSCR

 20:          70 LOAD_CONST           (None)
              72 STORE_NAME           (params)
              74 LOAD_NAME            (Optional)
              76 LOAD_NAME            (Dict)
              78 LOAD_NAME            (str)
              80 LOAD_NAME            (Type)
              82 BUILD_TUPLE          2
              84 BINARY_SUBSCR
              88 BINARY_SUBSCR
              92 LOAD_NAME            (__annotations__)
              94 LOAD_CONST           ("params")
              96 STORE_SUBSCR
             100 RETURN_CONST         (None)


# Method Name:       RouterManager
# Filename:          src\route_manager.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        10
# Flags:             0x00000000 (0x0)
# First Line:        23
# Constants:
#    0: 'RouterManager'
#    1: '/auth'
#    2: <Code311 code object __init__ at 0x1e8dd368550, file src\route_manager.py>, line 28
#    3: 'path'
#    4: <Code311 code object set_start_path at 0x1e8dd368690, file src\route_manager.py>, line 33
#    5: None
#    6: 'title'
#    7: 'params'
#    8: <Code311 code object register at 0x1e8dd29fa80, file src\route_manager.py>, line 36
#    9: <Code311 code object setup_routes at 0x1e8dd2f2580, file src\route_manager.py>, line 55
#   10: 'return'
#   11: <Code311 code object is_authenticated at 0x1e8dd2f2690, file src\route_manager.py>, line 97
#   12: 'license_key'
#   13: <Code311 code object verify_activation_key at 0x1e8dd2f27a0, file src\route_manager.py>, line 101
#   14: <Code311 code object handle_unauthorized at 0x1e8dd2f28b0, file src\route_manager.py>, line 105
#   15: (None,)
# Names:
#    0: __name__
#    1: __module__
#    2: __qualname__
#    3: NOT_AUTH_PATH
#    4: __init__
#    5: str
#    6: set_start_path
#    7: Optional
#    8: Dict
#    9: Type
#   10: register
#   11: setup_routes
#   12: bool
#   13: is_authenticated
#   14: tuple
#   15: verify_activation_key
#   16: handle_unauthorized

 23:           0 RESUME               0
               2 LOAD_NAME            (__name__)
               4 STORE_NAME           (__module__)
               6 LOAD_CONST           ("RouterManager")
               8 STORE_NAME           (__qualname__)

 25:          10 LOAD_CONST           ("/auth")

 24:          12 BUILD_LIST           1
              14 STORE_NAME           (NOT_AUTH_PATH)

 28:          16 LOAD_CONST           (<Code311 code object __init__ at 0x1e8dd368550, file src\route_manager.py>, line 28)
              18 MAKE_FUNCTION        (No arguments)
              20 STORE_NAME           (__init__)

 33:          22 LOAD_CONST           ("path")
              24 LOAD_NAME            (str)
              26 BUILD_TUPLE          2
              28 LOAD_CONST           (<Code311 code object set_start_path at 0x1e8dd368690, file src\route_manager.py>, line 33)
              30 MAKE_FUNCTION        (annotation)
              32 STORE_NAME           (set_start_path)

 40:          34 NOP

 36:          36 LOAD_CONST           ((None,))
              38 LOAD_CONST           ("path")

 38:          40 LOAD_NAME            (str)

 36:          42 LOAD_CONST           ("title")

 39:          44 LOAD_NAME            (str)

 36:          46 LOAD_CONST           ("params")

 40:          48 LOAD_NAME            (Optional)
              50 LOAD_NAME            (Dict)
              52 LOAD_NAME            (str)
              54 LOAD_NAME            (Type)
              56 BUILD_TUPLE          2
              58 BINARY_SUBSCR
              62 BINARY_SUBSCR

 36:          66 BUILD_TUPLE          6
              68 LOAD_CONST           (<Code311 code object register at 0x1e8dd29fa80, file src\route_manager.py>, line 36)
              70 MAKE_FUNCTION        (default, annotation)
              72 STORE_NAME           (register)

 55:          74 LOAD_CONST           (<Code311 code object setup_routes at 0x1e8dd2f2580, file src\route_manager.py>, line 55)
              76 MAKE_FUNCTION        (No arguments)
              78 STORE_NAME           (setup_routes)

 97:          80 LOAD_CONST           ("return")
              82 LOAD_NAME            (bool)
              84 BUILD_TUPLE          2
              86 LOAD_CONST           (<Code311 code object is_authenticated at 0x1e8dd2f2690, file src\route_manager.py>, line 97)
              88 MAKE_FUNCTION        (annotation)
              90 STORE_NAME           (is_authenticated)

101:          92 LOAD_CONST           ("license_key")
              94 LOAD_NAME            (str)
              96 LOAD_CONST           ("return")
              98 LOAD_NAME            (tuple)
             100 LOAD_NAME            (bool)
             102 LOAD_NAME            (str)
             104 BUILD_TUPLE          2
             106 BINARY_SUBSCR
             110 BUILD_TUPLE          4
             112 LOAD_CONST           (<Code311 code object verify_activation_key at 0x1e8dd2f27a0, file src\route_manager.py>, line 101)
             114 MAKE_FUNCTION        (annotation)
             116 STORE_NAME           (verify_activation_key)

105:         118 LOAD_CONST           (<Code311 code object handle_unauthorized at 0x1e8dd2f28b0, file src\route_manager.py>, line 105)
             120 MAKE_FUNCTION        (No arguments)
             122 STORE_NAME           (handle_unauthorized)
             124 RETURN_CONST         (None)


# Method Name:       __init__
# Filename:          src\route_manager.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  1
# Stack size:        2
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        28
# Constants:
#    0: None
#    1: '/studio'
#    2: '/auth'
# Names:
#    0: routes
#    1: start_path
#    2: login_path
# Varnames:
#	self
# Positional arguments:
#	self

 28:           0 RESUME               0

 29:           2 BUILD_MAP            0
               4 LOAD_FAST            (self)
               6 STORE_ATTR           (routes)

 30:          16 LOAD_CONST           ("/studio")
              18 LOAD_FAST            (self)
              20 STORE_ATTR           (start_path)

 31:          30 LOAD_CONST           ("/auth")
              32 LOAD_FAST            (self)
              34 STORE_ATTR           (login_path)
              44 RETURN_CONST         (None)


# Method Name:       set_start_path
# Filename:          src\route_manager.py
# Argument count:    2
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  2
# Stack size:        2
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        33
# Constants:
#    0: None
# Names:
#    0: start_path
# Varnames:
#	self, path
# Positional arguments:
#	self, path

 33:           0 RESUME               0

 34:           2 LOAD_FAST            (path)
               4 LOAD_FAST            (self)
               6 STORE_ATTR           (start_path)
              16 RETURN_CONST         (None)


# Method Name:       register
# Filename:          src\route_manager.py
# Argument count:    4
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  5
# Stack size:        5
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        36
# Constants:
#    0: None
#    1: 'view_func'
#    2: <Code311 code object decorator at 0x1e8dd29f950, file src\route_manager.py>, line 42
# Names:
#    0: Callable
# Varnames:
#	self, path, title, params, decorator
# Positional arguments:
#	self, path, title, params
# Local variables:
#    4: decorator
# Cell variables:
#    0: self
#    1: path
#    2: title
#    3: params
               0 MAKE_CELL            (self)
               2 MAKE_CELL            (path)
               4 MAKE_CELL            (title)
               6 MAKE_CELL            (params)

 36:           8 RESUME               0

 42:          10 LOAD_CONST           ("view_func")
              12 LOAD_GLOBAL          (Callable)
              22 BUILD_TUPLE          2
              24 LOAD_CLOSURE         (params)
              26 LOAD_CLOSURE         (path)
              28 LOAD_CLOSURE         (self)
              30 LOAD_CLOSURE         (title)
              32 BUILD_TUPLE          4
              34 LOAD_CONST           (<Code311 code object decorator at 0x1e8dd29f950, file src\route_manager.py>, line 42)
              36 MAKE_FUNCTION        (annotation, closure)
              38 STORE_FAST           (decorator)

 53:          40 LOAD_FAST            (decorator)
              42 RETURN_VALUE


# Method Name:       setup_routes
# Filename:          src\route_manager.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  5
# Stack size:        6
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        55
# Constants:
#    0: None
#    1: '/'
#    2: <Code311 code object root_handler at 0x1e8dd348710, file src\route_manager.py>, line 56
#    3: 'request'
#    4: <Code311 code object async_route_handler at 0x1e8dd2f2360, file src\route_manager.py>, line 63
#    5: <Code311 code object sync_route_handler at 0x1e8dd2f2470, file src\route_manager.py>, line 84
# Names:
#    0: ui
#    1: page
#    2: routes
#    3: values
#    4: is_async
#    5: path
#    6: Request
# Varnames:
#	self, root_handler, route, async_route_handler, sync_route_handler
# Positional arguments:
#	self
# Local variables:
#    1: root_handler
#    2: route
#    3: async_route_handler
#    4: sync_route_handler
# Cell variables:
#    0: self
               0 MAKE_CELL            (self)

 55:           2 RESUME               0

 56:           4 LOAD_GLOBAL          (NULL + ui)
              14 LOAD_ATTR            (page)
              34 LOAD_CONST           ("/")
              36 CALL                 1

 57:          44 LOAD_CLOSURE         (self)
              46 BUILD_TUPLE          1
              48 LOAD_CONST           (<Code311 code object root_handler at 0x1e8dd348710, file src\route_manager.py>, line 56)
              50 MAKE_FUNCTION        (closure)

 56:          52 CALL                 0

 57:          60 STORE_FAST           (root_handler)

 60:          62 LOAD_DEREF           (self)
              64 LOAD_ATTR            (routes)
              84 LOAD_ATTR            (NULL|self + values)
             104 CALL                 0
             112 GET_ITER
             114 FOR_ITER             (to 340)
             118 STORE_FAST           (route)

 61:         120 LOAD_FAST            (route)
             122 LOAD_ATTR            (is_async)
             142 POP_JUMP_IF_FALSE    (to 242)

 63:         144 LOAD_GLOBAL          (NULL + ui)
             154 LOAD_ATTR            (page)
             174 LOAD_FAST            (route)
             176 LOAD_ATTR            (path)
             196 CALL                 1

 64:         204 LOAD_FAST            (route)
             206 BUILD_TUPLE          1
             208 LOAD_CONST           ("request")
             210 LOAD_GLOBAL          (Request)
             220 BUILD_TUPLE          2
             222 LOAD_CLOSURE         (self)
             224 BUILD_TUPLE          1
             226 LOAD_CONST           (<Code311 code object async_route_handler at 0x1e8dd2f2360, file src\route_manager.py>, line 63)
             228 MAKE_FUNCTION        (default, annotation, closure)

 63:         230 CALL                 0

 64:         238 STORE_FAST           (async_route_handler)
             240 JUMP_BACKWARD        (to 114)

 84:     >>  242 LOAD_GLOBAL          (NULL + ui)
             252 LOAD_ATTR            (page)
             272 LOAD_FAST            (route)
             274 LOAD_ATTR            (path)
             294 CALL                 1

 85:         302 LOAD_FAST            (route)
             304 BUILD_TUPLE          1
             306 LOAD_CONST           ("request")
             308 LOAD_GLOBAL          (Request)
             318 BUILD_TUPLE          2
             320 LOAD_CLOSURE         (self)
             322 BUILD_TUPLE          1
             324 LOAD_CONST           (<Code311 code object sync_route_handler at 0x1e8dd2f2470, file src\route_manager.py>, line 84)
             326 MAKE_FUNCTION        (default, annotation, closure)

 84:         328 CALL                 0

 85:         336 STORE_FAST           (sync_route_handler)
         >>  338 JUMP_BACKWARD        (to 114)

 60:         340 END_FOR
             342 RETURN_CONST         (None)


# Method Name:       is_authenticated
# Filename:          src\route_manager.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  1
# Stack size:        2
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        97
# Constants:
#    0: 'Check if user has a valid license.'
# Names:
#    0: is_licensed
# Varnames:
#	self
# Positional arguments:
#	self

 97:           0 RESUME               0

 99:           2 LOAD_GLOBAL          (NULL + is_licensed)
              12 CALL                 0
              20 RETURN_VALUE


# Method Name:       verify_activation_key
# Filename:          src\route_manager.py
# Argument count:    2
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  2
# Stack size:        3
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        101
# Constants:
#    0: 'Verify a license key via Licensify API.'
# Names:
#    0: verify_license
# Varnames:
#	self, license_key
# Positional arguments:
#	self, license_key

101:           0 RESUME               0

103:           2 LOAD_GLOBAL          (NULL + verify_license)
              12 LOAD_FAST            (license_key)
              14 CALL                 1
              22 RETURN_VALUE


# Method Name:       handle_unauthorized
# Filename:          src\route_manager.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  1
# Stack size:        3
# Flags:             0x00000003 (NEWLOCALS | OPTIMIZED)
# First Line:        105
# Constants:
#    0: 'Handle unauthorized access attempts'
# Names:
#    0: ui
#    1: navigate
#    2: to
#    3: login_path
# Varnames:
#	self
# Positional arguments:
#	self

105:           0 RESUME               0

107:           2 LOAD_GLOBAL          (ui)
              12 LOAD_ATTR            (navigate)
              32 LOAD_ATTR            (NULL|self + to)
              52 LOAD_FAST            (self)
              54 LOAD_ATTR            (login_path)
              74 CALL                 1
              82 RETURN_VALUE


# Method Name:       decorator
# Filename:          src\route_manager.py
# Argument count:    1
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  2
# Stack size:        8
# Flags:             0x00000013 (NESTED | NEWLOCALS | OPTIMIZED)
# First Line:        42
# Constants:
#    0: None
#    1: ('path', 'view_func', 'title', 'is_async', 'params')
# Names:
#    0: inspect
#    1: iscoroutinefunction
#    2: Route
#    3: routes
# Varnames:
#	view_func, is_async
# Positional arguments:
#	view_func
# Local variables:
#    1: is_async
# Free variables:
#    0: params
#    1: path
#    2: self
#    3: title
               0 COPY_FREE_VARS       4

 42:           2 RESUME               0

 43:           4 LOAD_GLOBAL          (NULL + inspect)
              14 LOAD_ATTR            (iscoroutinefunction)
              34 LOAD_FAST            (view_func)
              36 CALL                 1
              44 STORE_FAST           (is_async)

 44:          46 LOAD_GLOBAL          (NULL + Route)

 45:          56 LOAD_DEREF           (path)

 46:          58 LOAD_FAST            (view_func)

 47:          60 LOAD_DEREF           (title)

 48:          62 LOAD_FAST            (is_async)

 49:          64 LOAD_DEREF           (params)
              66 COPY                 1
              68 POP_JUMP_IF_TRUE     (to 74)
              70 POP_TOP
              72 BUILD_MAP            0

 44:     >>   74 KW_NAMES             (('path', 'view_func', 'title', 'is_async', 'params'))
              76 CALL                 5
              84 LOAD_DEREF           (self)
              86 LOAD_ATTR            (routes)
             106 LOAD_DEREF           (path)
             108 STORE_SUBSCR

 51:         112 LOAD_FAST            (view_func)
             114 RETURN_VALUE


# Method Name:       root_handler
# Filename:          src\route_manager.py
# Argument count:    0
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  0
# Stack size:        3
# Flags:             0x00000013 (NESTED | NEWLOCALS | OPTIMIZED)
# First Line:        56
# Constants:
#    0: None
# Names:
#    0: ui
#    1: navigate
#    2: to
#    3: start_path
# Free variables:
#    0: self
               0 COPY_FREE_VARS       1

 56:           2 RESUME               0

 58:           4 LOAD_GLOBAL          (ui)
              14 LOAD_ATTR            (navigate)
              34 LOAD_ATTR            (NULL|self + to)
              54 LOAD_DEREF           (self)
              56 LOAD_ATTR            (start_path)
              76 CALL                 1
              84 RETURN_VALUE


# Method Name:       async_route_handler
# Filename:          src\route_manager.py
# Argument count:    2
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  5
# Stack size:        7
# Flags:             0x00000093 (COROUTINE | NESTED | NEWLOCALS | OPTIMIZED)
# First Line:        63
# Constants:
#    0: None
#    1: 'Error in async route '
#    2: ': '
#    3: 'An error occurred'
#    4: 'negative'
#    5: ('type',)
#    6: '/error'
#    7: ()
# Names:
#    0: path
#    1: NOT_AUTH_PATH
#    2: is_authenticated
#    3: handle_unauthorized
#    4: params
#    5: query_params
#    6: get
#    7: view_func
#    8: Exception
#    9: logger
#   10: error
#   11: ui
#   12: notify
#   13: navigate
#   14: to
# Varnames:
#	request, route, param, kwargs, e
# Positional arguments:
#	request, route
# Local variables:
#    2: param
#    3: kwargs
#    4: e
# Free variables:
#    0: self
               0 COPY_FREE_VARS       1

 63:           2 RETURN_GENERATOR
               4 POP_TOP
               6 RESUME               0

 66:           8 LOAD_FAST            (route)
              10 LOAD_ATTR            (path)
              30 LOAD_DEREF           (self)
              32 LOAD_ATTR            (NOT_AUTH_PATH)
              52 CONTAINS_OP          (not in)
              54 POP_JUMP_IF_FALSE    (to 120)

 67:          56 LOAD_DEREF           (self)
              58 LOAD_ATTR            (NULL|self + is_authenticated)
              78 CALL                 0
              86 POP_JUMP_IF_TRUE     (to 120)

 69:          88 LOAD_DEREF           (self)
              90 LOAD_ATTR            (NULL|self + handle_unauthorized)
             110 CALL                 0
             118 RETURN_VALUE

 71:     >>  120 NOP

 74:         122 LOAD_FAST            (route)
             124 LOAD_ATTR            (params)
             144 GET_ITER

 72:         146 LOAD_FAST_AND_CLEAR  (param)
             148 SWAP                 (TOS <-> TOS1)
             150 BUILD_MAP            0
             152 SWAP                 (TOS <-> TOS1)

 74:         154 FOR_ITER             (to 218)
             158 STORE_FAST           (param)

 73:         160 LOAD_FAST            (param)
             162 LOAD_FAST            (request)
             164 LOAD_ATTR            (query_params)
             184 LOAD_ATTR            (NULL|self + get)
             204 LOAD_FAST            (param)
             206 CALL                 1
             214 MAP_ADD              2
         >>  216 JUMP_BACKWARD        (to 154)

 74:         218 END_FOR

 72:         220 STORE_FAST           (kwargs)
             222 STORE_FAST           (param)

 76:         224 PUSH_NULL
             226 LOAD_FAST            (route)
             228 LOAD_ATTR            (view_func)
             248 LOAD_CONST           (())
             250 BUILD_MAP            0
             252 LOAD_FAST            (kwargs)
             254 DICT_MERGE           1
             256 CALL_FUNCTION_EX     (keyword and positional arguments)
             258 GET_AWAITABLE        0
             260 LOAD_CONST           (None)
             262 SEND                 (to 270)
             266 YIELD_VALUE          3
             268 RESUME               3
         >>  270 JUMP_BACKWARD_NO_INTERRUPT (to 262)
             272 END_SEND
             274 RETURN_VALUE
             276 SWAP                 (TOS <-> TOS1)
             278 POP_TOP

 72:         280 SWAP                 (TOS <-> TOS1)
         >>  282 STORE_FAST           (param)
             284 RERAISE              0

 76:         286 CLEANUP_THROW
             288 JUMP_BACKWARD        (to 272)
             290 PUSH_EXC_INFO

 77:         292 LOAD_GLOBAL          (Exception)
             302 CHECK_EXC_MATCH
             304 POP_JUMP_IF_FALSE    (to 508)
             306 STORE_FAST           (e)

 78:     >>  308 LOAD_GLOBAL          (NULL + logger)
             318 LOAD_ATTR            (error)
             338 LOAD_CONST           ("Error in async route ")
             340 LOAD_FAST            (route)
             342 LOAD_ATTR            (path)
             362 FORMAT_VALUE         0
             364 LOAD_CONST           (": ")
             366 LOAD_FAST            (e)
             368 FORMAT_VALUE         0
             370 BUILD_STRING         4
             372 CALL                 1
             380 POP_TOP

 79:         382 LOAD_GLOBAL          (NULL + ui)
             392 LOAD_ATTR            (notify)
             412 LOAD_CONST           ("An error occurred")
             414 LOAD_CONST           ("negative")
             416 KW_NAMES             (('type',))
             418 CALL                 2
             426 POP_TOP

 80:         428 LOAD_GLOBAL          (ui)
             438 LOAD_ATTR            (navigate)
             458 LOAD_ATTR            (NULL|self + to)
             478 LOAD_CONST           ("/error")
             480 CALL                 1
             488 SWAP                 (TOS <-> TOS1)
             490 POP_EXCEPT
             492 LOAD_CONST           (None)
             494 STORE_FAST           (e)
             496 DELETE_FAST          (e)
             498 RETURN_VALUE
             500 LOAD_CONST           (None)
             502 STORE_FAST           (e)
             504 DELETE_FAST          (e)
             506 RERAISE              1

 77:     >>  508 RERAISE              0
             510 COPY                 3
             512 POP_EXCEPT
             514 RERAISE              1
             516 CALL_INTRINSIC_1     3
             518 RERAISE              1

ExceptionTable:
  6 to 118 -> 516 [0] lasti
  122 to 148 -> 290 [0]
  150 to 218 -> 276 [2]
  220 to 264 -> 290 [0]
  266 to 266 -> 286 [2]
  268 to 272 -> 290 [0]
  274 to 274 -> 516 [0] lasti
  276 to 286 -> 290 [0]
  290 to 306 -> 510 [1] lasti
  308 to 486 -> 500 [1] lasti
  488 to 488 -> 510 [1] lasti
  490 to 498 -> 516 [0] lasti
  500 to 508 -> 510 [1] lasti
  510 to 514 -> 516 [0] lasti

# Method Name:       sync_route_handler
# Filename:          src\route_manager.py
# Argument count:    2
# Position-only argument count: 0
# Keyword-only arguments: 0
# Number of locals:  4
# Stack size:        7
# Flags:             0x00000013 (NESTED | NEWLOCALS | OPTIMIZED)
# First Line:        84
# Constants:
#    0: None
#    1: ()
# Names:
#    0: path
#    1: NOT_AUTH_PATH
#    2: is_authenticated
#    3: handle_unauthorized
#    4: params
#    5: query_params
#    6: get
#    7: view_func
# Varnames:
#	request, route, param, kwargs
# Positional arguments:
#	request, route
# Local variables:
#    2: param
#    3: kwargs
# Free variables:
#    0: self
               0 COPY_FREE_VARS       1

 84:           2 RESUME               0

 87:           4 LOAD_FAST            (route)
               6 LOAD_ATTR            (path)
              26 LOAD_DEREF           (self)
              28 LOAD_ATTR            (NOT_AUTH_PATH)
              48 CONTAINS_OP          (not in)
              50 POP_JUMP_IF_FALSE    (to 116)

 88:          52 LOAD_DEREF           (self)
              54 LOAD_ATTR            (NULL|self + is_authenticated)
              74 CALL                 0
              82 POP_JUMP_IF_TRUE     (to 116)

 90:          84 LOAD_DEREF           (self)
              86 LOAD_ATTR            (NULL|self + handle_unauthorized)
             106 CALL                 0
             114 RETURN_VALUE

 93:     >>  116 LOAD_FAST            (route)
             118 LOAD_ATTR            (params)
             138 GET_ITER

 92:         140 LOAD_FAST_AND_CLEAR  (param)
             142 SWAP                 (TOS <-> TOS1)
             144 BUILD_MAP            0
             146 SWAP                 (TOS <-> TOS1)

 93:         148 FOR_ITER             (to 212)
             152 STORE_FAST           (param)
             154 LOAD_FAST            (param)
             156 LOAD_FAST            (request)
             158 LOAD_ATTR            (query_params)
             178 LOAD_ATTR            (NULL|self + get)
             198 LOAD_FAST            (param)
             200 CALL                 1
             208 MAP_ADD              2
         >>  210 JUMP_BACKWARD        (to 148)
             212 END_FOR

 92:         214 STORE_FAST           (kwargs)
             216 STORE_FAST           (param)

 95:         218 PUSH_NULL
             220 LOAD_FAST            (route)
             222 LOAD_ATTR            (view_func)
             242 LOAD_CONST           (())
             244 BUILD_MAP            0
             246 LOAD_FAST            (kwargs)
             248 DICT_MERGE           1
             250 CALL_FUNCTION_EX     (keyword and positional arguments)
             252 RETURN_VALUE
             254 SWAP                 (TOS <-> TOS1)
             256 POP_TOP

 92:         258 SWAP                 (TOS <-> TOS1)
             260 STORE_FAST           (param)
             262 RERAISE              0

ExceptionTable:
  144 to 212 -> 254 [2]
```
