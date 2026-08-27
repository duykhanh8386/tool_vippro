# 13 — Clean-room Module Functional Smoke Test

## Scope and safety

Three clean-room UI modules were loaded individually under CPython 3.12.14 and
tested with a synthetic NiceGUI surface and dependency mocks:

- `web/components/delete_video.py`
- `web/components/remove_audio.py`
- `web/components/delete_back_flow.py`

The recovered application and NiceGUI server were not started. No browser or
protected route was opened. All controller, network, Selenium, upload, delete,
media, polling, file-dialog, and external API dependencies were replaced
before the target modules were imported.

No Bytecode Exact module was edited. After reproducing the defects, only the
requested clear-state regions in `remove_audio.py` and `delete_back_flow.py`
were changed; `delete_video.py` remained untouched.

Test harness:

```text
recovery_tools/functional_smoke_cleanroom.py
```

The harness itself passes CPython compilation. After the two targeted fixes,
its final process exit code is `0` and all three module-level results pass.

## Mock boundary

The following operations were mocks that only recorded arguments or returned
controlled values:

- NiceGUI elements, callbacks, dialogs, timers, notifications, and UI state;
- channel selection and file/folder dialogs;
- channel/controller scanning and stopping;
- `update_audio_module.delete`;
- audio construction and video/audio muxing;
- video upload and video creation;
- copyright-status polling;
- remote video deletion;
- overlay lookup;
- deletion audit-log output;
- persistent state load/save.

No license module was imported and no license API call was possible through
the harness.

## Results

| Module | Callback/state | Async flow | Error handling | Overall |
|---|---|---|---|---|
| `delete_video.py` | PASS | PASS | PASS | **PASS** |
| `remove_audio.py` | PASS | PASS | PASS | **PASS** |
| `delete_back_flow.py` | PASS | PASS | PASS | **PASS** |

## `delete_video.py` — PASS

Verified behavior:

1. The channel-selection callback updated the closure state used by
   `handle_scan`.
2. Awaiting the scan callback called the mocked controller exactly as:

   ```text
   start(["channel-1", "channel-2"], max_workers=5)
   ```

3. The callback synchronized the controller's running/version state and the
   navigation-lock path.
4. Awaiting the stop callback called `stop()` and returned the controller to
   the non-running state.
5. A forced controller-start exception was caught by `handle_scan` and
   converted into a NiceGUI notification with `type="negative"`.

No real scan, network, or delete operation was invoked.

**Result: PASS.**

## `remove_audio.py` — PASS

### Passing behavior

- `parse_ids_from_text("id-1, id-2\nid-1")` preserved insertion order and
  returned `['id-1', 'id-2']` without duplicates.
- The textarea callback updated the ID list and persisted normal state.
- The async handler processed two IDs concurrently through the mocked delete
  API.
- A successful mock produced `successful`; a forced exception produced
  `unsuccessful`.
- Both per-video statuses were persisted and the mixed result produced a
  warning notification rather than escaping as an exception.

### Defect found and corrected

The original `clear_all_inputs` called `save_remove_state()` while
`suppress_autosave["value"]` was still true, so the save returned without
persisting the cleared state.

Observed result:

```text
in-memory IDs/status/channel: cleared
last persisted state: old IDs/status/channel remain
```

The callback now keeps autosave suppressed throughout the UI/in-memory reset,
restores `suppress_autosave["value"] = False` in `finally`, and only then calls
`save_remove_state()`. The rerun confirmed that empty IDs, status, and channel
state are persisted.

**Result: PASS.**

## `delete_back_flow.py` — PASS

### Passing behavior

The success scenario completed the mocked pipeline in this exact order:

```text
build intermittent audio
→ mux audio into video
→ upload file
→ create video
→ poll copyright status
→ delete remote video
→ record deletion log
```

Additional checks:

- all four step states reached `successful`;
- generated upload identifiers and video ID propagated through later steps;
- the navigation state was locked during processing and unlocked by the
  `finally` path;
- normal state snapshots were saved between stages;
- the mocked status `UPLOAD_CHECKS_DATA_COPYRIGHT_STATUS_COMPLETED` ended the
  polling loop without sleeping;
- the mocked HTTP delete result `204` was accepted.

The error scenario forced the mux mock to raise. The handler:

- set only `merge` to `error`;
- left `upload`, `wait`, and `delete_back` at `pending`;
- did not call any later upload/status/delete mock;
- persisted the error state;
- still released the navigation lock.

### Defect found and corrected

The original `clear_all_inputs` called `save_state()` while
`suppress_autosave["value"]` was still true, so the cleared snapshot was not
written.

Observed result:

```text
in-memory paths/options/channel/items: cleared
last persisted state: previous paths, channel and video statuses remain
```

The callback now restores `suppress_autosave["value"] = False` after the full
UI/in-memory reset and calls `save_state()` afterward. The rerun confirmed
that empty paths, options, channel selection, items, and statuses are
persisted.

**Result: PASS.**

## Reproducibility

Command used:

```powershell
recovered_project/.venv/Scripts/python.exe recovery_tools/functional_smoke_cleanroom.py
```

Final machine-readable outcome:

```text
delete_video.py: PASS
remove_audio.py: PASS
delete_back_flow.py: PASS
```

## Final conclusion

```text
delete_video.py: PASS
remove_audio.py: PASS
delete_back_flow.py: PASS
Network/license/browser activity: NONE
Bytecode Exact modules modified: 0
Recovered clean-room modules modified: 2 — only the two requested clear-state fixes
Overall status: 3 PASS / 0 FAIL
```
