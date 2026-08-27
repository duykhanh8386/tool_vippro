# RECOVERED: reconstructed from CPython 3.12 bytecode
"""
Runtime patches for NiceGUI quirks.

Import this module once, before ``ui.run()``.
"""

from nicegui.client import Client


def _patch_idempotent_client_delete() -> None:
    """Make ``Client.delete()`` safe to call more than once.

    NiceGUI 2.x tears down a disconnected page client with
    ``del Client.instances[self.id]`` (client.py). When the same client is
    deleted twice — a known race that surfaces under rapid page refreshes /
    reconnects (zauberzeug/nicegui#1826) — that line raises ``KeyError`` and
    the traceback is logged, even though all element cleanup before it has
    already run. The error is therefore benign log noise.

    Later NiceGUI releases changed the ``del`` to an idempotent ``pop``; we
    reproduce that here by short-circuiting a second delete. If a future
    upgrade already fixes this, the guard simply never triggers.
    """
    if getattr(Client, "_idempotent_delete_patched", False):
        return

    _orig_delete = Client.delete

    def _safe_delete(self) -> None:
        if self.id not in Client.instances:
            return
        _orig_delete(self)

    Client.delete = _safe_delete
    Client._idempotent_delete_patched = True


def apply_patches() -> None:
    _patch_idempotent_client_delete()
