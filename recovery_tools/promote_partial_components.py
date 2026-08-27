#!/usr/bin/env python3
"""Promote depyo component output while repairing reversible UTF-8 mojibake."""

from pathlib import Path


NAMES = (
    "add_audio_flow.py",
    "audio.py",
    "auth.py",
    "common.py",
    "delete_back_flow.py",
    "delete_video.py",
    "delete_video_controller.py",
    "drawer.py",
    "remove_audio.py",
    "settings.py",
    "studio.py",
)


def repair_mojibake(text: str) -> str:
    output: list[str] = []
    encoded = bytearray()

    def flush() -> None:
        if not encoded:
            return
        data = bytes(encoded)
        try:
            output.append(data.decode("utf-8"))
        except UnicodeDecodeError:
            output.append(data.decode("latin-1"))
        encoded.clear()

    for char in text:
        value = ord(char)
        if value <= 0xFF:
            encoded.append(value)
            continue
        try:
            encoded.extend(char.encode("cp1252"))
        except UnicodeEncodeError:
            flush()
            output.append(char)
    flush()
    return "".join(output)


def sanitize(text: str) -> str:
    text = repair_mojibake(text)
    for index in range(20):
        text = text.replace(f"##FREEVAR_{index}##", f"_recovered_freevar_{index}")
    text = text.replace("##ERROR##", "_recovered_error")
    text = text.replace("elif not True:", "if not True:")
    text = text.replace("None(None, None)", "pass  # TODO: bytecode recovery incomplete")
    text = text.replace(
        "await pass  # TODO: bytecode recovery incomplete",
        "pass  # TODO: bytecode recovery incomplete",
    )
    text = text.replace(
        "count = channel_store.delete_channel(ch.id) or count += 1",
        "if channel_store.delete_channel(ch.id):\n                        count += 1",
    )
    return "# RECOVERED: partial depyo recovery; unresolved regions marked below\n" + text


def main() -> None:
    source_root = Path("work/decompiler_full_stage/decompiled/web/components")
    output_root = Path("recovered_project/web/components")
    output_root.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        raw = (source_root / name).read_text(encoding="utf-8")
        (output_root / name).write_text(sanitize(raw), encoding="utf-8", newline="\n")
        print(f"PROMOTED {name}")


if __name__ == "__main__":
    main()
