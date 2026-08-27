#!/usr/bin/env python3
"""Re-layout depyo's list_videos output using verified 3.12 control flow."""

from pathlib import Path


source = Path("work/decompiler_full_stage/decompiled/src/module/list_videos_module.py")
target = Path("recovered_project/src/module/list_videos_module.py")
lines = source.read_text(encoding="utf-8").splitlines()

out = ["# RECOVERED: reconstructed from CPython 3.12 bytecode"]
start = next(i for i, line in enumerate(lines) if "def list_all_videos" in line)
for line in lines[:start]:
    if line.strip() or (out and out[-1].strip()):
        out.append(line)
out.append(
    "    def list_all_videos(self, channel_id: str, limit: int=50, "
    "page_token: str | None=None) -> tuple[list[Video], str | None]:"
)

i = start + 1
if lines[i].strip() != "try:":
    raise RuntimeError("expected outer depyo try block")
i += 1
while i < len(lines):
    stripped = lines[i].strip()
    if stripped == 'if not res.get("nextPageToken"):' :
        out.append('        next_page_token = res.get("nextPageToken") or None')
        i += 3
        continue
    if stripped == 'for item in res.get("videos", []):':
        out.append('        for item in res.get("videos", []):')
        out.append('            try:')
        i += 1
        while i < len(lines) and "videos.append(Video(" not in lines[i]:
            if lines[i].strip():
                out.append(lines[i])
            i += 1
        if i >= len(lines):
            raise RuntimeError("videos.append block not found")
        out.append(lines[i])
        out.append('            except Exception as exc:')
        out.append('                logger.warning(f"Skipping malformed video entry: {exc}")')
        out.append('        return videos, next_page_token')
        break
    line = lines[i]
    if line.startswith("            "):
        line = line[4:]
    if line.strip():
        out.append(line)
    i += 1

out.extend(
    [
        "",
        "    def get_copyright_statuses(self, channel_id: str, video_ids: set[str]) -> dict[str, str]:",
        "        remaining = set(video_ids)",
        "        result = {}",
        "        page_token = None",
        "        while remaining:",
        "            videos, next_token = self.list_all_videos(channel_id, 50, page_token)",
        "            for v in videos:",
        "                if v.id not in remaining:",
        "                    continue",
        "                result[v.id] = v.copyright_check_status",
        "                remaining.discard(v.id)",
        "            if not next_token or not remaining:",
        "                break",
        "            page_token = next_token",
        "        return result",
        "",
        "",
        "list_videos_module = ListVideosModule()",
        "",
    ]
)
target.write_text("\n".join(out), encoding="utf-8", newline="\n")
