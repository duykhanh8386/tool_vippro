"""Shared visual system for the TV Automation web interface."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterable, Iterator, Mapping

from nicegui import ui


THEME_CSS = r"""
:root {
  --app-bg: #fafafa;
  --app-surface: #ffffff;
  --app-surface-subtle: #f9fafb;
  --app-surface-muted: #f3f4f6;
  --app-text: #1f2937;
  --app-text-strong: #111827;
  --app-text-muted: #6b7280;
  --app-text-faint: #9ca3af;
  --app-border: #e5e7eb;
  --app-border-strong: #d1d5db;
  --app-primary: #10b981;
  --app-primary-hover: #059669;
  --app-primary-soft: #ecfdf5;
  --app-primary-border: #a7f3d0;
  --app-danger: #dc2626;
  --app-warning: #d97706;
  --app-info: #0284c7;
  --app-radius: 10px;
  --app-sidebar-width: 212px;
  --nicegui-default-padding: 1rem;
  --nicegui-default-gap: 1rem;
}

html, body, #app { min-height: 100%; }
body {
  margin: 0;
  color: var(--app-text);
  background: var(--app-bg);
  font-family: "Segoe UI Variable Text", "Segoe UI Variable", "Segoe UI",
    ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
  font-size: 14px;
  font-weight: 400;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

.nicegui-content {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 32px 40px 48px;
  gap: 24px;
}
.app-page { width: 100%; gap: 24px; }

/* Sidebar */
.app-sidebar {
  width: var(--app-sidebar-width) !important;
  color: var(--app-text);
  background: #fbfbfb !important;
  border-right: 1px solid var(--app-border) !important;
  box-shadow: none !important;
}
.app-sidebar .q-drawer__content { overflow-x: hidden; }
.app-sidebar-shell { min-height: 100%; padding: 18px 10px 12px; }
.app-brand { min-height: 48px; padding: 0 8px; }
.app-brand-mark {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  color: #ffffff;
  background: var(--app-primary);
}
.app-brand-title { color: var(--app-text-strong); font-size: 14px; font-weight: 600; line-height: 1.35; }
.app-brand-copy { color: var(--app-text-faint); font-size: 11px; line-height: 1.4; }
.app-nav-label {
  margin: 16px 10px 4px;
  color: var(--app-text-faint);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: .02em;
}
.app-nav-item {
  min-height: 40px !important;
  margin: 3px 0 !important;
  padding: 0 12px !important;
  border-radius: 9px !important;
  color: #6b7280 !important;
  background: transparent !important;
}
.app-nav-item:hover {
  color: var(--app-text-strong) !important;
  background: var(--app-surface-muted) !important;
}
.app-nav-item--active {
  color: var(--app-text-strong) !important;
  background: #eef0f2 !important;
  font-weight: 600;
}
.app-nav-item--active .q-icon { color: var(--app-primary) !important; }
.app-sidebar .q-expansion-item__container > .q-item {
  min-height: 42px;
  margin: 3px 0;
  padding: 0 12px;
  border-radius: 9px;
  color: var(--app-text-muted);
  font-size: 13px;
  font-weight: 500;
}
.app-sidebar .q-expansion-item__container > .q-item:hover {
  color: var(--app-text-strong);
  background: var(--app-surface-muted);
}
.app-sidebar .q-expansion-item__content { padding-left: 8px; }
.app-account {
  min-height: 54px;
  padding: 8px;
  border: 1px solid transparent;
  border-radius: 10px;
}
.app-account:hover { background: var(--app-surface-muted); border-color: var(--app-border); }
.app-account-avatar {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: 9px;
  color: #047857;
  background: #d1fae5;
  font-size: 12px;
  font-weight: 700;
}

/* Page hierarchy */
.app-page-header {
  width: 100%;
  min-height: 68px;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}
.app-page-title {
  color: var(--app-text-strong);
  font-size: clamp(24px, 2vw, 28px);
  line-height: 1.25;
  font-weight: 700;
  letter-spacing: -.025em;
}
.app-page-subtitle {
  max-width: 720px;
  color: var(--app-text-muted);
  font-size: 14px;
  line-height: 1.5;
}
.app-page-eyebrow {
  color: #059669;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: .02em;
}
.app-page-actions { align-items: center; justify-content: flex-end; gap: 10px; }

/* Cards and sections */
.app-card, .q-card.app-card {
  width: 100%;
  padding: 22px;
  border: 1px solid var(--app-border) !important;
  border-radius: var(--app-radius) !important;
  background: var(--app-surface) !important;
  box-shadow: 0 1px 2px rgba(17, 24, 39, .025) !important;
}
.app-card--compact, .q-card.app-card--compact { padding: 16px 18px; }
.app-section-header {
  width: 100%;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.app-section-title { color: var(--app-text-strong); font-size: 16px; font-weight: 600; line-height: 1.4; }
.app-section-copy { color: var(--app-text-muted); font-size: 13px; line-height: 1.5; }

/* Buttons and forms */
.q-btn {
  min-height: 40px;
  padding-inline: 14px;
  border-radius: 8px !important;
  font-size: 13px;
  font-weight: 600 !important;
  letter-spacing: 0 !important;
  text-transform: none !important;
  box-shadow: none !important;
}
.app-button-primary, .q-btn.app-button-primary {
  color: #ffffff !important;
  background: var(--app-primary) !important;
}
.app-button-primary:hover { background: var(--app-primary-hover) !important; }
.app-button-secondary, .q-btn.app-button-secondary {
  color: #374151 !important;
  background: #ffffff !important;
  border: 1px solid var(--app-border-strong) !important;
}
.app-button-secondary:hover { background: var(--app-surface-subtle) !important; }
.app-button-danger, .q-btn.app-button-danger {
  color: #b91c1c !important;
  background: #ffffff !important;
  border: 1px solid #fecaca !important;
}
.app-button-danger.disabled, .q-btn.app-button-danger.disabled {
  color: var(--app-text-faint) !important;
  border-color: var(--app-border) !important;
  background: var(--app-surface-subtle) !important;
  opacity: 1 !important;
}
.app-icon-button { color: var(--app-text-muted) !important; }
.app-icon-button:hover { color: var(--app-text-strong) !important; background: var(--app-surface-muted) !important; }
.q-field--outlined .q-field__control {
  min-height: 46px;
  border-radius: 8px !important;
  background: #ffffff;
}
.q-field--outlined .q-field__control:before { border-color: var(--app-border-strong) !important; }
.q-field--outlined.q-field--focused .q-field__control:after {
  border-color: var(--app-primary) !important;
  border-width: 1px !important;
}
.q-field__label { color: var(--app-text-muted) !important; }

/* Workflow */
.app-workflow {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(var(--workflow-count, 3), minmax(0, 1fr));
  overflow: hidden;
  border: 1px solid var(--app-border);
  border-radius: var(--app-radius);
  background: var(--app-surface);
}
.app-workflow-step {
  min-height: 70px;
  padding: 14px 18px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.app-workflow-step:not(:last-child) { border-right: 1px solid var(--app-border); }
.app-step-marker {
  width: 30px;
  height: 30px;
  flex: 0 0 30px;
  display: grid;
  place-items: center;
  border: 1.5px solid var(--app-border-strong);
  border-radius: 999px;
  color: var(--app-text-muted);
  background: #ffffff;
  font-size: 12px;
  font-weight: 600;
}
.app-workflow-step--complete .app-step-marker {
  color: #ffffff;
  border-color: var(--app-primary);
  background: var(--app-primary);
}
.app-workflow-step--current .app-step-marker {
  color: #059669;
  border-color: var(--app-primary);
  background: var(--app-primary-soft);
}
.app-workflow-title { color: var(--app-text-strong); font-size: 13px; font-weight: 600; line-height: 1.4; }
.app-workflow-copy { color: var(--app-text-muted); font-size: 12px; }

.app-metrics {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-top: 1px solid var(--app-border);
}
.app-metric { min-width: 0; padding: 18px 20px 2px 0; }
.app-metric + .app-metric {
  padding-left: 20px;
  border-left: 1px solid var(--app-border);
}
.app-metric-label { color: var(--app-text-muted); font-size: 12px; font-weight: 500; }
.app-metric-value { color: var(--app-text-strong); font-size: 15px; font-weight: 600; }

/* Tables and status */
.app-table { width: 100%; overflow: hidden; border: 1px solid var(--app-border); border-radius: var(--app-radius); }
.app-table-header, .app-table-row {
  width: 100%;
  min-height: 52px;
  padding: 0 16px;
  display: grid;
  grid-template-columns: var(--app-table-columns, minmax(0, 1fr));
  align-items: center;
  column-gap: 16px;
}
.app-table-header {
  min-height: 42px;
  color: var(--app-text-muted);
  background: var(--app-surface-subtle);
  border-bottom: 1px solid var(--app-border);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0;
}
.app-table-row { background: #ffffff; border-bottom: 1px solid var(--app-border); }
.app-table-row:last-child { border-bottom: 0; }
.app-table-row:hover { background: #fcfcfc; }
.app-status {
  width: fit-content;
  min-height: 24px;
  padding: 2px 8px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}
.app-status--success { color: #047857; background: #ecfdf5; }
.app-status--warning { color: #b45309; background: #fffbeb; }
.app-status--danger { color: #b91c1c; background: #fef2f2; }
.app-status--info { color: #0369a1; background: #f0f9ff; }
.app-status--neutral { color: #4b5563; background: #f3f4f6; }
.app-status-dot { width: 6px; height: 6px; border-radius: 999px; background: currentColor; }
.app-empty-state {
  width: 100%;
  min-height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--app-border-strong);
  border-radius: var(--app-radius);
  background: var(--app-surface-subtle);
}
.q-linear-progress { overflow: hidden; border-radius: 999px; }
.q-dialog__inner > .q-card { border-radius: 12px !important; box-shadow: 0 18px 50px rgba(17,24,39,.12) !important; }

@media (max-width: 980px) {
  .nicegui-content { padding: 28px 24px 40px; }
  .app-page-header { flex-direction: column; }
  .app-page-actions { width: 100%; justify-content: flex-start; }
  .app-workflow { grid-template-columns: 1fr; }
  .app-workflow-step:not(:last-child) { border-right: 0; border-bottom: 1px solid var(--app-border); }
  .app-metrics { grid-template-columns: 1fr; }
  .app-metric { padding: 14px 0; }
  .app-metric + .app-metric { padding-left: 0; border-left: 0; border-top: 1px solid var(--app-border); }
}
@media (max-width: 700px) {
  .nicegui-content { padding: 22px 16px 32px; }
  .app-card, .q-card.app-card { padding: 18px; }
  .app-table { overflow-x: auto; }
  .app-table-header, .app-table-row { min-width: 680px; }
}
"""


def install_theme() -> None:
    ui.add_css(THEME_CSS, shared=True)
    apply_page_theme()


def apply_page_theme() -> None:
    ui.colors(
        primary="#10b981",
        secondary="#374151",
        accent="#059669",
        positive="#10b981",
        negative="#dc2626",
        warning="#d97706",
        info="#0284c7",
    )


@contextmanager
def page_shell() -> Iterator[None]:
    with ui.column().classes("app-page"):
        yield


@contextmanager
def page_header(
    title: str,
    subtitle: str = "",
    *,
    eyebrow: str = "",
) -> Iterator[None]:
    with ui.row().classes("app-page-header"):
        with ui.column().classes("gap-1"):
            if eyebrow:
                ui.label(eyebrow).classes("app-page-eyebrow")
            ui.label(title).classes("app-page-title")
            if subtitle:
                ui.label(subtitle).classes("app-page-subtitle")
        with ui.row().classes("app-page-actions"):
            yield


@contextmanager
def app_card(*, compact: bool = False, classes: str = "") -> Iterator[None]:
    card_classes = "app-card"
    if compact:
        card_classes += " app-card--compact"
    if classes:
        card_classes += f" {classes}"
    with ui.card().classes(card_classes):
        yield


@contextmanager
def section_header(title: str, subtitle: str = "") -> Iterator[None]:
    with ui.row().classes("app-section-header"):
        with ui.column().classes("gap-0.5"):
            ui.label(title).classes("app-section-title")
            if subtitle:
                ui.label(subtitle).classes("app-section-copy")
        with ui.row().classes("items-center gap-2"):
            yield


def status_badge(text: str, status: str = "neutral"):
    valid_statuses = {"success", "warning", "danger", "info", "neutral"}
    tone = status if status in valid_statuses else "neutral"
    with ui.row().classes(f"app-status app-status--{tone}") as badge:
        ui.element("span").classes("app-status-dot")
        ui.label(text)
    return badge


def workflow_steps(steps: Iterable[Mapping[str, str]]) -> None:
    step_list = list(steps)
    with ui.element("div").classes("app-workflow").style(
        f"--workflow-count: {max(len(step_list), 1)}"
    ):
        for index, step in enumerate(step_list, start=1):
            state = step.get("state", "pending")
            state_class = (
                f" app-workflow-step--{state}"
                if state in {"complete", "current"}
                else ""
            )
            with ui.element("div").classes(f"app-workflow-step{state_class}"):
                with ui.element("div").classes("app-step-marker"):
                    if state == "complete":
                        ui.icon("check").classes("text-base")
                    else:
                        ui.label(str(index))
                with ui.column().classes("gap-0.5 min-w-0"):
                    ui.label(step.get("title", f"Bước {index}")).classes(
                        "app-workflow-title"
                    )
                    copy = step.get("description", "")
                    if copy:
                        ui.label(copy).classes("app-workflow-copy")


@contextmanager
def app_table(columns: str) -> Iterator[None]:
    with ui.element("div").classes("app-table").style(
        f"--app-table-columns: {columns}"
    ):
        yield


def empty_state(
    title: str,
    description: str = "",
    *,
    icon: str = "inbox",
) -> None:
    with ui.element("div").classes("app-empty-state"):
        with ui.column().classes("items-center gap-2 text-center px-6"):
            ui.icon(icon).classes("text-3xl text-gray-400")
            ui.label(title).classes("text-sm font-semibold text-gray-700")
            if description:
                ui.label(description).classes("text-xs text-gray-500 max-w-md")
