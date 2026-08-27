# 11 — Controlled Startup Smoke Test

## Scope

The recovered application was started only to verify import/startup behavior, port binding, route registration, and a localhost HTTP response.

- Runtime was activated through `recovered_project/activate_runtime.ps1`.
- Entrypoint was `recovered_project/app.py` under `recovered_project/.venv`.
- No business control was clicked or submitted.
- Selenium and ChromeDriver were not invoked by the test harness.
- No upload, deletion, media-processing, or updater operation was requested.
- No source file was changed in response to startup behavior.
- The server process tree was terminated after evidence collection.

Raw logs are retained under `work/startup_smoke/`.

## 1. First launch: sandbox-only failure

The first launch used the restricted execution sandbox. NiceGUI starts with `reload=True` because the recovered source is not frozen, which invokes multiprocessing/reloader facilities. The sandbox denied creation of a Windows named pipe in `multiprocessing.resource_sharer`.

Consequences:

- no listener bound to port 8081;
- the parent process remained alive in an error loop;
- the same traceback was emitted 34,938 times;
- the complete 31,444,155-byte raw log is preserved as `work/startup_smoke/sandbox_stderr.log`;
- the entire failed process tree was terminated before retrying.

Every emitted traceback is retained in that raw log. All instances are identical. The complete distinct traceback is:

```text
Traceback (most recent call last):
  File "C:\Users\DucHieu\Documents\mmo\work\tools\python312_full\Lib\multiprocessing\resource_sharer.py", line 138, in _serve
    with self._listener.accept() as conn:
         ^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\DucHieu\Documents\mmo\work\tools\python312_full\Lib\multiprocessing\connection.py", line 480, in accept
    c = self._listener.accept()
        ^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\DucHieu\Documents\mmo\work\tools\python312_full\Lib\multiprocessing\connection.py", line 684, in accept
    self._handle_queue.append(self._new_handle())
                              ^^^^^^^^^^^^^^^^^^
  File "C:\Users\DucHieu\Documents\mmo\work\tools\python312_full\Lib\multiprocessing\connection.py", line 675, in _new_handle
    return _winapi.CreateNamedPipe(
           ^^^^^^^^^^^^^^^^^^^^^^^^
PermissionError: [WinError 5] Access is denied
```

This traceback originates in the restricted host environment, not recovered application logic. Following the sandbox policy for a permission-blocked required test, the same command was retried outside the restricted sandbox.

## 2. Successful controlled launch

The unrestricted retry used the same source, venv, working directory, requirements, and runtime activation. It was launched in a hidden background process with stdout/stderr redirected.

Startup stdout:

```text
NiceGUI ready to go on http://localhost:8081, http://10.1.129.22:8081, http://169.254.1.171:8081, http://169.254.123.9:8081, http://169.254.127.63:8081, http://169.254.82.224:8081, http://172.18.112.1:8081, and http://192.168.5.113:8081
```

No traceback or import exception was emitted by the successful run.

**Startup: PASS on unrestricted retry.**

## 3. Port 8081

The listener was observed through the operating-system TCP table:

```text
TCP  0.0.0.0:8081  0.0.0.0:0  LISTENING
```

The listener belonged to the NiceGUI child server process. After the probes, the parent and all server/reloader child processes were terminated. A final check found no listener remaining on port 8081.

**Port 8081: PASS; cleanup confirmed.**

## 4. Route registration

NiceGUI returned 404 for `/openapi.json`, so OpenAPI could not be used as a route inventory. Route presence was instead tested without executing GET page handlers: HTTP `OPTIONS` was sent to each statically evidenced application path.

An existing GET-only route returns 405 Method Not Allowed for `OPTIONS`; a deliberately nonexistent control path returned 404.

| Path | `OPTIONS` result | Interpretation |
|---|---:|---|
| `/` | 405 | Registered |
| `/auth` | 405 | Registered |
| `/studio` | 405 | Registered |
| `/settings` | 405 | Registered |
| `/audio/add` | 405 | Registered |
| `/audio/flow` | 405 | Registered |
| `/audio/remove` | 405 | Registered |
| `/reup/delete-back-flow` | 405 | Registered |
| `/reup/delete-video` | 405 | Registered |
| `/__smoke_nonexistent__` | 404 | Negative control, not registered |

Result: **9 / 9 expected routes registered**. No route returned a startup registration exception.

The expected 404 probes were logged as:

```text
http://127.0.0.1:8081/openapi.json not found
http://127.0.0.1:8081/__smoke_nonexistent__ not found
```

**Routes: PASS.**

## 5. Main-page HTTP response

A single direct GET was sent to `http://127.0.0.1:8081/` with redirects disabled.

```text
Status: 200 OK
Content-Type: text/html; charset=utf-8
Body length: 13,428 bytes
Title: TV Automation
Body prefix: <!DOCTYPE html> <html> ...
```

The response contained a normal NiceGUI HTML document and referenced NiceGUI 2.23.3 static assets.

**HTTP response: PASS.**

## 6. Unexpected browser/license side effect

The recovered `app.py` calls `ui.run(...)` without `show=False`. NiceGUI therefore used its default browser-opening behavior. It reused a Chrome process that predated this smoke test and opened the application page automatically.

That browser request reached the protected `/studio` route. The route authentication check called the recovered license logic, and the successful-run stderr recorded:

```text
2026-08-28 02:57:10.081 | WARNING | src.license_manager:verify_license:84 - License rejected: invalid_license
```

Static inspection confirms `verify_license()` performs an HTTP POST to the configured Licensify API. Therefore, despite the test harness making only localhost requests, application startup's default browser behavior caused one unintended license API verification. No license bypass, patch, key submission by the tester, or business UI interaction occurred.

The existing Chrome process was not terminated because it predated the test and could contain user sessions. The NiceGUI server/reloader process tree was terminated, which closed the local application connection.

This is a safety deviation from the requested “no network API” boundary and is reported explicitly. A future startup test should suppress NiceGUI's automatic browser opening through an approved launch configuration before starting the app; source was not changed during this test.

## 7. Errors and logs

| Item | Result |
|---|---|
| Successful-run import/startup traceback | None |
| Successful-run application exception | None |
| Sandbox-run traceback | Full traceback above; 34,938 identical occurrences retained in raw log |
| Expected probe warnings | Two 404 log entries (`/openapi.json`, negative control) |
| Application warning | `License rejected: invalid_license` after auto-opened browser reached protected route |
| Source changes | None |

Artifacts:

```text
work/startup_smoke/stdout.log
work/startup_smoke/stderr.log
work/startup_smoke/sandbox_stdout.log
work/startup_smoke/sandbox_stderr.log
```

## Final conclusion

The recovered application imports, registers all expected routes, starts NiceGUI, binds port 8081, and serves the main HTML page successfully in an unrestricted runtime. No recovered-code startup exception was observed.

The test is classified **PASS WITH WARNINGS** because the restricted first run generated an environment-only named-pipe error loop, and the successful run's automatic browser opening triggered one unintended license verification request. The server was fully stopped after testing.

```text
Startup: PASS — successful outside restricted sandbox; no recovered-code startup traceback
Port 8081: PASS — bound on 0.0.0.0:8081; no listener remained after cleanup
Routes: PASS — 9/9 expected routes registered
HTTP response: PASS — GET / returned 200 HTML, 13,428 bytes
Errors: sandbox-only WinError 5 traceback loop; expected 404 probe logs; one unintended invalid-license verification warning
Status: PASS WITH WARNINGS / SERVER STOPPED
```
