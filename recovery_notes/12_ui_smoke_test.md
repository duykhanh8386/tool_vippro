# 12 — Controlled UI Smoke Test

## Scope and safety

This step tested only the recovered application's public landing endpoint, the
unprotected authentication page, NiceGUI static assets, and the local
Socket.IO handshake.

- `TV Automation.exe` was not run.
- Selenium, ChromeDriver, upload/delete operations, media processing, and the
  updater were not invoked.
- No business UI control was clicked or submitted.
- No protected application route was deliberately requested.
- Recovered application source was not modified.
- The server was stopped after evidence collection; port 8081 was clear.

## Controlled launch configuration

`recovered_project/activate_runtime.ps1` was used before launching the app with
the recovered venv. A smoke-test-only harness,
`recovery_tools/run_ui_smoke_no_browser.py`, intercepted only the final
`ui.run(...)` call and supplied:

```text
show=False
reload=False
host=127.0.0.2
```

The application imports and route setup remained unchanged. The isolated
loopback address prevented a stale Chrome tab on `localhost:8081` from
reconnecting to protected routes. Outbound HTTP/HTTPS in the server process
was additionally directed to a closed loopback proxy; localhost and
`127.0.0.2` were excluded from that proxy.

The isolated launch reported:

```text
NiceGUI ready to go on http://127.0.0.2:8081
```

## Browser availability limitation

The in-app browser control runtime was initialized according to its required
workflow, but reported no available browser instances. Its one permitted
discovery check returned an empty list. Therefore this step did **not** replace
it with Selenium, Playwright, ChromeDriver, or another browser automation
surface.

Consequently, JavaScript execution, pixel-level rendering, and the browser
console could not be observed directly. HTTP structure and assets were tested
fully, but they are not presented as proof that client-side JavaScript has no
runtime error.

## Main page (`/`)

`GET http://127.0.0.2:8081/` was sent with redirects disabled and without a
browser JavaScript runtime.

```text
Status: 200 OK
Content-Type: text/html; charset=utf-8
Body length: 13,428 bytes
Title: TV Automation
```

Static source inspection established that the root NiceGUI handler calls
`ui.navigate.to('/studio')`. `/studio` is protected and can call license
verification. For that reason `/` was deliberately **not** loaded in a real
browser, where its JavaScript navigation would execute.

**Main page: HTTP PASS; interactive browser render intentionally not run.**

## Authentication page (`/auth`)

Before the test, the expected Windows application-data path contained no
`TVAutomation/license.json`. This means the page's initial
`router.is_authenticated()` check returns locally without calling the license
API. The activation button was not clicked.

```text
Status: 200 OK
Content-Type: text/html; charset=utf-8
Body length: 15,029 bytes
Title: TV Automation
```

The returned NiceGUI document contained the expected UI model strings:

```text
License Activation
Nhap license key
Kich hoat
Xoa tat ca
```

**Auth page: HTTP/markup PASS; JavaScript render and browser console unverified.**

## Static assets and local transport

All local `src`/`href` resources referenced by `/` and `/auth` were requested
individually. Result: **11 / 11 returned 200**.

| Resource | HTTP | Type | Bytes |
|---|---:|---|---:|
| `/_nicegui/2.23.3/components/e136c57a667887dcbfe4527fbe4f5d87/input.js` | 200 | JavaScript | 1,750 |
| `/_nicegui/2.23.3/static/es-module-shims.js` | 200 | JavaScript | 63,661 |
| `/_nicegui/2.23.3/static/fonts.css` | 200 | CSS | 15,256 |
| `/_nicegui/2.23.3/static/lang/en-US.umd.prod.js` | 200 | JavaScript | 2,091 |
| `/_nicegui/2.23.3/static/nicegui.css` | 200 | CSS | 7,419 |
| `/_nicegui/2.23.3/static/nicegui.js` | 200 | JavaScript | 14,496 |
| `/_nicegui/2.23.3/static/quasar.prod.css` | 200 | CSS | 204,294 |
| `/_nicegui/2.23.3/static/quasar.umd.prod.js` | 200 | JavaScript | 499,404 |
| `/_nicegui/2.23.3/static/socket.io.min.js` | 200 | JavaScript | 49,993 |
| `/_nicegui/2.23.3/static/tailwindcss.min.js` | 200 | JavaScript | 366,328 |
| `/_nicegui/2.23.3/static/vue.global.prod.js` | 200 | JavaScript | 146,843 |

A local Engine.IO polling handshake also succeeded:

```text
GET /_nicegui_ws/socket.io/?EIO=4&transport=polling
Status: 200
Content-Type: text/plain; charset=UTF-8
Handshake advertised websocket upgrade support
```

The favicon is an external GitHub URL. It was not fetched because outbound
network access was intentionally excluded from this test.

**Static assets: PASS for 11/11 required local assets; external favicon not
tested by design.**

## Errors and safety observation

The final isolated run produced no stderr output, traceback, HTTP 4xx/5xx,
NiceGUI exception, or license warning.

An earlier launch attempt in this same step did suppress NiceGUI's automatic
browser opening by assigning a no-op browser command. However, a Chrome tab
left open from the preceding smoke test independently reconnected to
`localhost:8081` and replayed an activation action. The server logged:

```text
ERROR | src.license_manager:verify_license - Khong the ket noi den server license
```

The outbound proxy blocked that attempted request at loopback; it did not
reach the Licensify service. That server was stopped immediately. The final
isolated `127.0.0.2` run eliminated the stale-tab connection and remained
clean.

Retained logs:

```text
work/ui_smoke/stdout.log
work/ui_smoke/stderr.log
work/ui_smoke/isolated_stdout.log
work/ui_smoke/isolated_stderr.log
```

## Final conclusion

```text
Main page: HTTP PASS — 200 HTML, 13,428 bytes; browser execution intentionally avoided because / navigates to protected /studio
Auth page: HTTP/MARKUP PASS — 200 HTML, 15,029 bytes; activation was not clicked; browser render unavailable
Static assets: PASS — 11/11 local JS/CSS/component assets returned 200; Socket.IO polling handshake returned 200; external favicon not fetched
UI errors: UNVERIFIED IN BROWSER — no browser instance was available for JS console or visual-render inspection
Server errors: NONE in the final isolated run; one blocked stale-tab license attempt occurred during the discarded first launch
Status: PARTIAL PASS WITH DOCUMENTED LIMITATION / SERVER STOPPED
```
