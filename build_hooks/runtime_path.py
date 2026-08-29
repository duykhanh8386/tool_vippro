"""Expose bundled command-line tools to subprocess calls at runtime."""

import os
import sys


if getattr(sys, "frozen", False):
    bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    media_dir = os.path.join(bundle_dir, "tools", "ffmpeg")
    os.environ["PATH"] = media_dir + os.pathsep + os.environ.get("PATH", "")
