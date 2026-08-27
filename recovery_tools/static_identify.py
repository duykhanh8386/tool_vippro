#!/usr/bin/env python3
"""Static PE/Python packager identification without executing the target."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
from pathlib import Path


MACHINES = {
    0x014C: "x86 (I386)",
    0x8664: "x86-64 (AMD64)",
    0x01C0: "ARM",
    0x01C4: "ARMv7",
    0xAA64: "ARM64",
}

SUBSYSTEMS = {
    1: "Native",
    2: "Windows GUI",
    3: "Windows console",
    9: "Windows CE GUI",
    10: "EFI application",
}

MARKERS = [
    b"PYINSTALLER",
    b"PyInstaller",
    b"PYZ",
    b"_MEIPASS",
    b"_PYI_ARCHIVE_FILE",
    b"python3",
    b"python312.dll",
    b"python311.dll",
    b"python310.dll",
    b"python39.dll",
    b"python38.dll",
    b"MEI\x0c\x0b\x0a\x0b\x0e",
    b"Inno Setup",
    b"Nullsoft",
    b"NSIS",
    b"UPX!",
    b"7zS.sfx",
    b"electron",
]


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def u64(data: bytes, offset: int) -> int:
    return struct.unpack_from("<Q", data, offset)[0]


def entropy(blob: bytes) -> float:
    if not blob:
        return 0.0
    counts = [0] * 256
    for byte in blob:
        counts[byte] += 1
    total = len(blob)
    return -sum((n / total) * math.log2(n / total) for n in counts if n)


def c_string(data: bytes, offset: int, limit: int = 1024) -> str:
    if not 0 <= offset < len(data):
        return ""
    end = data.find(b"\0", offset, min(len(data), offset + limit))
    if end < 0:
        end = min(len(data), offset + limit)
    return data[offset:end].decode("ascii", "replace")


def offsets(data: bytes, needle: bytes, ignore_case: bool = False) -> list[int]:
    haystack = data.lower() if ignore_case else data
    target = needle.lower() if ignore_case else needle
    found: list[int] = []
    start = 0
    while True:
        pos = haystack.find(target, start)
        if pos < 0:
            return found
        found.append(pos)
        start = pos + 1


def parse_pe(data: bytes) -> dict:
    if len(data) < 0x100 or data[:2] != b"MZ":
        raise ValueError("Not a DOS/PE executable (missing MZ)")
    pe_offset = u32(data, 0x3C)
    if pe_offset + 24 > len(data) or data[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise ValueError("Invalid PE signature")

    coff = pe_offset + 4
    machine = u16(data, coff)
    number_of_sections = u16(data, coff + 2)
    timestamp = u32(data, coff + 4)
    optional_size = u16(data, coff + 16)
    characteristics = u16(data, coff + 18)
    optional = coff + 20
    magic = u16(data, optional)
    if magic not in (0x10B, 0x20B):
        raise ValueError(f"Unsupported optional-header magic 0x{magic:04x}")
    is_64 = magic == 0x20B
    entrypoint_rva = u32(data, optional + 16)
    image_base = u64(data, optional + 24) if is_64 else u32(data, optional + 28)
    subsystem = u16(data, optional + 68)
    data_directory = optional + (112 if is_64 else 96)

    section_table = optional + optional_size
    sections = []
    for index in range(number_of_sections):
        pos = section_table + index * 40
        if pos + 40 > len(data):
            break
        name = data[pos:pos + 8].split(b"\0", 1)[0].decode("ascii", "replace")
        virtual_size = u32(data, pos + 8)
        virtual_address = u32(data, pos + 12)
        raw_size = u32(data, pos + 16)
        raw_offset = u32(data, pos + 20)
        section_data = data[raw_offset:min(len(data), raw_offset + raw_size)]
        sections.append({
            "name": name,
            "virtual_address": virtual_address,
            "virtual_size": virtual_size,
            "raw_offset": raw_offset,
            "raw_size": raw_size,
            "entropy": round(entropy(section_data), 4),
            "characteristics": f"0x{u32(data, pos + 36):08x}",
        })

    def rva_to_offset(rva: int) -> int | None:
        for section in sections:
            start = section["virtual_address"]
            span = max(section["virtual_size"], section["raw_size"])
            if start <= rva < start + span:
                result = section["raw_offset"] + (rva - start)
                return result if result < len(data) else None
        return rva if rva < len(data) else None

    imports = []
    import_rva = u32(data, data_directory + 8) if data_directory + 16 <= len(data) else 0
    import_offset = rva_to_offset(import_rva) if import_rva else None
    if import_offset is not None:
        for index in range(4096):
            descriptor = import_offset + index * 20
            if descriptor + 20 > len(data):
                break
            values = struct.unpack_from("<IIIII", data, descriptor)
            if not any(values):
                break
            name_offset = rva_to_offset(values[3])
            name = c_string(data, name_offset) if name_offset is not None else ""
            if name:
                imports.append(name)

    raw_end = max((s["raw_offset"] + s["raw_size"] for s in sections), default=0)
    overlay_size = max(0, len(data) - raw_end)
    overlay = data[raw_end:] if overlay_size else b""

    return {
        "format": "PE32+" if is_64 else "PE32",
        "machine": MACHINES.get(machine, f"unknown (0x{machine:04x})"),
        "pe_offset": pe_offset,
        "timestamp_raw": timestamp,
        "number_of_sections": number_of_sections,
        "characteristics": f"0x{characteristics:04x}",
        "entrypoint_rva": f"0x{entrypoint_rva:x}",
        "image_base": f"0x{image_base:x}",
        "subsystem": SUBSYSTEMS.get(subsystem, f"unknown ({subsystem})"),
        "sections": sections,
        "imports": imports,
        "overlay": {
            "offset": raw_end,
            "size": overlay_size,
            "sha256": hashlib.sha256(overlay).hexdigest() if overlay else None,
            "first_32_bytes_hex": overlay[:32].hex(),
            "entropy": round(entropy(overlay), 4),
        },
    }


def embedded_pes(data: bytes) -> list[dict]:
    results = []
    for match in re.finditer(b"MZ", data):
        start = match.start()
        if start + 0x40 > len(data):
            continue
        pe_rel = u32(data, start + 0x3C)
        pe_pos = start + pe_rel
        if pe_rel < 0x40 or pe_pos + 24 > len(data) or data[pe_pos:pe_pos + 4] != b"PE\0\0":
            continue
        machine = u16(data, pe_pos + 4)
        results.append({"offset": start, "pe_offset_relative": pe_rel, "machine": MACHINES.get(machine, hex(machine))})
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    data = args.path.read_bytes()
    pe = parse_pe(data)

    marker_hits = {}
    for marker in MARKERS:
        hits = offsets(data, marker, ignore_case=True)
        wide = b"".join(bytes((byte, 0)) for byte in marker)
        wide_hits = offsets(data, wide, ignore_case=True)
        if hits or wide_hits:
            marker_hits[marker.decode("ascii", "backslashreplace")] = {
                "ascii_offsets": hits[:50],
                "utf16le_offsets": wide_hits[:50],
                "ascii_count": len(hits),
                "utf16le_count": len(wide_hits),
            }

    archive_signatures = {
        "PyInstaller cookie": b"MEI\x0c\x0b\x0a\x0b\x0e",
        "ZIP local header": b"PK\x03\x04",
        "ZIP end directory": b"PK\x05\x06",
        "7-Zip": b"7z\xbc\xaf\x27\x1c",
        "RAR4": b"Rar!\x1a\x07\x00",
        "RAR5": b"Rar!\x1a\x07\x01\x00",
        "GZIP": b"\x1f\x8b\x08",
        "XZ": b"\xfd7zXZ\x00",
        "CAB/MSCF": b"MSCF",
        "PYZ": b"PYZ\x00",
    }
    archives = {
        name: {"count": len(found), "offsets": found[:100]}
        for name, signature in archive_signatures.items()
        if (found := offsets(data, signature))
    }

    report = {
        "path": str(args.path.resolve()),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "md5": hashlib.md5(data).hexdigest(),
        "pe": pe,
        "marker_hits": marker_hits,
        "archive_signatures": archives,
        "embedded_pe_candidates": embedded_pes(data)[:500],
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
