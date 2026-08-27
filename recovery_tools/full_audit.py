#!/usr/bin/env python3
"""Full audit: deep recursive comparator for all 39 scoped modules."""

from __future__ import annotations
import marshal, types, sys
from pathlib import Path

PYZ = Path("work/extracted/PYZ.pyz_extracted")
REC = Path("recovered_project")

# Map: (recovered relative path without .py) -> (PYZ relative path without .pyc)
# Package __init__.py files are stored differently in PYZ
SCOPED = {
    "src/__init__":                       "src",
    "src/channel_refresh":                "src/channel_refresh",
    "src/channel_scanner":                "src/channel_scanner",
    "src/channel_store":                  "src/channel_store",
    "src/cookie_utils":                   "src/cookie_utils",
    "src/license_manager":                "src/license_manager",
    "src/module/__init__":                "src/module",
    "src/module/audio_module":            "src/module/audio_module",
    "src/module/base":                    "src/module/base",
    "src/module/delete_video_module":     "src/module/delete_video_module",
    "src/module/list_videos_module":      "src/module/list_videos_module",
    "src/module/model":                   "src/module/model",
    "src/module/upload_video_module":     "src/module/upload_video_module",
    "src/paths":                          "src/paths",
    "src/route_manager":                  "src/route_manager",
    "src/state_manager":                  "src/state_manager",
    "src/updater":                        "src/updater",
    "src/utils":                          "src/utils",
    "web/__init__":                       "web",
    "web/components/__init__":            "web/components",
    "web/components/add_audio_flow":      "web/components/add_audio_flow",
    "web/components/audio":               "web/components/audio",
    "web/components/auth":                "web/components/auth",
    "web/components/common":              "web/components/common",
    "web/components/delete_back_flow":    "web/components/delete_back_flow",
    "web/components/delete_video":        "web/components/delete_video",
    "web/components/delete_video_controller": "web/components/delete_video_controller",
    "web/components/drawer":              "web/components/drawer",
    "web/components/remove_audio":        "web/components/remove_audio",
    "web/components/settings":            "web/components/settings",
    "web/components/studio":              "web/components/studio",
    "web/nicegui_patches":                "web/nicegui_patches",
    "web/views/__init__":                 "web/views/__init__",
    "web/views/audio":                    "web/views/audio",
    "web/views/auth":                     "web/views/auth",
    "web/views/delete_back_flow":         "web/views/delete_back_flow",
    "web/views/delete_video":             "web/views/delete_video",
    "web/views/settings":                 "web/views/settings",
    "web/views/studio":                   "web/views/studio",
}

assert len(SCOPED) == 39, f"Expected 39, got {len(SCOPED)}"


def walk_code(code):
    """Recursively yield (qualname, code_object) preserving tree order."""
    qn = getattr(code, "co_qualname", code.co_name)
    yield qn, code
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            yield from walk_code(const)


def leaf_consts(code):
    # Compare immutable constant values directly. Using repr() made frozenset
    # constants depend on hash-table display order and produced intermittent
    # false mismatches across otherwise identical audit runs.
    return tuple(v for v in code.co_consts if not isinstance(v, types.CodeType))


def nested_code_order(code):
    """Return tuple of qualnames of nested code objects in const order."""
    return tuple(
        getattr(c, "co_qualname", c.co_name)
        for c in code.co_consts
        if isinstance(c, types.CodeType)
    )


def deep_compare(orig_code, rec_code):
    """Deep recursive comparison. Returns list of failure strings."""
    failures = []
    orig_map = dict(walk_code(orig_code))
    rec_map = dict(walk_code(rec_code))

    orig_keys = set(orig_map.keys())
    rec_keys = set(rec_map.keys())
    if orig_keys != rec_keys:
        missing = sorted(orig_keys - rec_keys)
        extra = sorted(rec_keys - orig_keys)
        failures.append(f"qualnames differ: missing={missing}, extra={extra}")

    for qn in sorted(orig_keys & rec_keys):
        old = orig_map[qn]
        new = rec_map[qn]
        checks = {
            "co_code": bytes(old.co_code) == bytes(new.co_code),
            "co_exceptiontable": bytes(getattr(old, "co_exceptiontable", b""))
                == bytes(getattr(new, "co_exceptiontable", b"")),
            "co_names": tuple(old.co_names) == tuple(new.co_names),
            "co_varnames": tuple(old.co_varnames) == tuple(new.co_varnames),
            "co_freevars": tuple(old.co_freevars) == tuple(new.co_freevars),
            "co_cellvars": tuple(old.co_cellvars) == tuple(new.co_cellvars),
            "leaf_consts": leaf_consts(old) == leaf_consts(new),
            "co_argcount": old.co_argcount == new.co_argcount,
            "co_posonlyargcount": old.co_posonlyargcount == new.co_posonlyargcount,
            "co_kwonlyargcount": old.co_kwonlyargcount == new.co_kwonlyargcount,
            "co_flags": (old.co_flags & 0x1EC) == (new.co_flags & 0x1EC),
            "nested_code_order": nested_code_order(old) == nested_code_order(new),
        }
        for label, passed in checks.items():
            if not passed:
                detail = ""
                if label == "co_names":
                    detail = f"\n      orig={tuple(old.co_names)!r}\n      rec ={tuple(new.co_names)!r}"
                elif label == "co_varnames":
                    detail = f"\n      orig={tuple(old.co_varnames)!r}\n      rec ={tuple(new.co_varnames)!r}"
                elif label == "co_freevars":
                    detail = f"\n      orig={tuple(old.co_freevars)!r}\n      rec ={tuple(new.co_freevars)!r}"
                elif label == "co_cellvars":
                    detail = f"\n      orig={tuple(old.co_cellvars)!r}\n      rec ={tuple(new.co_cellvars)!r}"
                elif label == "leaf_consts":
                    detail = f"\n      orig={leaf_consts(old)!r}\n      rec ={leaf_consts(new)!r}"
                elif label == "co_argcount":
                    detail = f" orig={old.co_argcount} rec={new.co_argcount}"
                elif label == "co_flags":
                    detail = f" orig=0x{old.co_flags:x} rec=0x{new.co_flags:x}"
                elif label == "nested_code_order":
                    detail = f"\n      orig={nested_code_order(old)!r}\n      rec ={nested_code_order(new)!r}"
                failures.append(f"  {qn}: {label} DIFFERS{detail}")
    return failures


def audit_module(rec_rel, pyz_rel):
    """Audit a single module. Returns (status, details_list)."""
    pyc_path = PYZ / (pyz_rel.replace("/", "\\") + ".pyc")
    py_path = REC / (rec_rel.replace("/", "\\") + ".py")

    if not pyc_path.exists():
        return "MISSING_PYC", [f"  {pyc_path} not found"]
    if not py_path.exists():
        return "MISSING_PY", [f"  {py_path} not found"]

    data = pyc_path.read_bytes()
    if len(data) == 16:
        # Verify the recovered .py is empty (or has only comments/docstrings)
        src = py_path.read_text(encoding="utf-8").strip()
        if src == "":
            return "EXACT", ["  Empty package marker (16-byte .pyc, empty .py)"]
        else:
            # Compile the non-empty source and check it against the empty marker
            try:
                rec_code = compile(src, str(py_path), "exec", dont_inherit=True)
                # An empty module compiles to RESUME + RETURN_CONST None
                if len(rec_code.co_code) <= 4 and not any(isinstance(c, types.CodeType) for c in rec_code.co_consts):
                    return "EXACT", ["  Empty package marker (16-byte .pyc, trivial .py)"]
                else:
                    return "MISMATCH", [f"  Empty .pyc marker but non-trivial recovered source ({len(src)} chars)"]
            except Exception as e:
                return "COMPILE_ERROR", [f"  Empty .pyc marker but source compile failed: {e}"]

    try:
        orig_code = marshal.loads(data[16:])
    except Exception as e:
        return "MARSHAL_ERROR", [f"  Cannot unmarshal original: {e}"]

    try:
        src = py_path.read_text(encoding="utf-8")
        rec_code = compile(src, str(py_path), "exec", dont_inherit=True)
    except Exception as e:
        return "COMPILE_ERROR", [f"  Cannot compile recovered source: {e}"]

    failures = deep_compare(orig_code, rec_code)
    if failures:
        return "MISMATCH", failures
    return "EXACT", ["  Full deep comparator passed — all code objects match"]


def main():
    print("=" * 72)
    print("FULL RECOVERY AUDIT — 39 Scoped Modules")
    print("Deep recursive bytecode comparator (CPython 3.12.10)")
    print("=" * 72)
    print()

    results = {}
    for rec_rel, pyz_rel in sorted(SCOPED.items()):
        status, details = audit_module(rec_rel, pyz_rel)
        results[rec_rel] = (status, details)
        tag = "PASS" if status == "EXACT" else "FAIL"
        print(f"  [{tag}] {rec_rel}: {status}")

    # Summary
    exact = [r for r, (s, _) in results.items() if s == "EXACT"]
    mismatch = [r for r, (s, _) in results.items() if s == "MISMATCH"]
    compile_err = [r for r, (s, _) in results.items() if s == "COMPILE_ERROR"]
    missing = [r for r, (s, _) in results.items() if s.startswith("MISSING")]
    other = [r for r, (s, _) in results.items() if s not in ("EXACT", "MISMATCH", "COMPILE_ERROR") and not s.startswith("MISSING")]

    print()
    print("=" * 72)
    print("SUMMARY")
    print("=" * 72)
    print(f"Scoped modules: {len(SCOPED)}")
    print(f"Verified Exact: {len(exact)}")
    print(f"Mismatch:       {len(mismatch)}")
    print(f"Compile Error:  {len(compile_err)}")
    print(f"Missing:        {len(missing)}")
    if other:
        print(f"Other:          {len(other)}")
    print()

    # Detail for non-Exact modules
    non_exact = [(r, s, d) for r, (s, d) in results.items() if s != "EXACT"]
    if non_exact:
        print("=" * 72)
        print("NON-EXACT MODULE DETAILS")
        print("=" * 72)
        for rel, status, details in sorted(non_exact):
            print(f"\n{'─'*60}")
            print(f"Module: {rel}")
            print(f"Status: {status}")
            # Count distinct code objects with failures
            co_names_with_issues = set()
            for line in details:
                stripped = line.strip()
                if ": " in stripped and " DIFFERS" in stripped:
                    co_name = stripped.split(":")[0]
                    co_names_with_issues.add(co_name)
            if co_names_with_issues:
                print(f"Code objects with mismatches: {len(co_names_with_issues)}")
            for line in details:
                print(line)

    # Special section for the 4 suspect modules
    suspects = [
        "web/components/audio",
        "web/components/delete_back_flow",
        "web/components/delete_video",
        "web/components/remove_audio",
    ]
    print()
    print("=" * 72)
    print("SPECIAL CHECK — 4 SUSPECT MODULES")
    print("=" * 72)
    for rel in suspects:
        status, details = results.get(rel, ("NOT_IN_SCOPE", []))
        tag = "PASS" if status == "EXACT" else "FAIL"
        print(f"\n  [{tag}] {rel}: {status}")
        if status != "EXACT":
            co_names_with_issues = set()
            for line in details:
                stripped = line.strip()
                if ": " in stripped and " DIFFERS" in stripped:
                    co_name = stripped.split(":")[0]
                    co_names_with_issues.add(co_name)
            if co_names_with_issues:
                print(f"    Code objects with mismatches: {len(co_names_with_issues)}")
                for cn in sorted(co_names_with_issues):
                    print(f"      - {cn}")

    print()
    print("=" * 72)
    print("AUDIT COMPLETE — No source files modified")
    print("=" * 72)


if __name__ == "__main__":
    main()
