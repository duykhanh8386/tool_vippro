"""Shared visual system for the Tuất Videos web interface."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, Iterable, Iterator, Mapping

from nicegui import ui


THEME_CSS = r"""
:root {
  --app-bg: #f4f7f6;
  --app-surface: #ffffff;
  --app-surface-subtle: #f5f8f7;
  --app-surface-muted: #edf3f1;
  --app-text: #1f2937;
  --app-text-strong: #111827;
  --app-text-muted: #64748b;
  --app-text-faint: #94a3b8;
  --app-border: #dde5e2;
  --app-border-strong: #cbd7d2;
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
  background: #f9fbfa !important;
  border-right: 1px solid var(--app-border) !important;
  box-shadow: 4px 0 18px rgba(15, 23, 42, .025) !important;
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
  overflow: hidden;
}
.app-brand-title { color: var(--app-text-strong); font-size: 14px; font-weight: 600; line-height: 1.35; }
.app-brand-copy { color: var(--app-text-faint); font-size: 11px; line-height: 1.4; }
.app-nav-label {
  width: calc(100% - 8px);
  margin: 14px 4px 5px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #5f6b7a;
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: .02em;
  line-height: 16px;
}
.app-nav-label::after {
  content: "";
  height: 1px;
  flex: 1;
  background: #e5e7eb;
}
.app-nav-item {
  min-height: 42px !important;
  margin: 3px 0 !important;
  padding: 0 10px !important;
  display: flex !important;
  align-items: center !important;
  gap: 9px !important;
  border-radius: 9px !important;
  color: #6b7280 !important;
  background: transparent !important;
  border: 1px solid transparent !important;
}
.app-nav-item:hover {
  color: var(--app-text-strong) !important;
  background: #f4f5f6 !important;
  border-color: #eceef0 !important;
}
.app-nav-item--active {
  color: #065f46 !important;
  background: var(--app-primary-soft) !important;
  border-color: #d1fae5 !important;
  font-weight: 600;
  box-shadow: inset 3px 0 0 var(--app-primary);
}
.app-nav-item .q-icon {
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  border-radius: 7px;
  color: #7b8492;
  transition: color .16s ease, background-color .16s ease;
}
.app-nav-item > .nicegui-label {
  min-width: 0;
  display: flex;
  align-items: center;
  line-height: 20px;
}
.app-nav-item:hover .q-icon {
  color: #4b5563;
  background: #ffffff;
}
.app-nav-item--active .q-icon {
  color: #059669 !important;
  background: rgba(255, 255, 255, .78);
}
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
  overflow: hidden;
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
  font-weight: 750;
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
  box-shadow: 0 1px 2px rgba(15, 23, 42, .035), 0 7px 20px rgba(15, 23, 42, .025) !important;
}
.app-card--compact, .q-card.app-card--compact { padding: 16px 18px; }
.app-section-header {
  width: 100%;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.app-section-title { color: var(--app-text-strong); font-size: 16px; font-weight: 650; line-height: 1.4; }
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
  box-shadow: 0 1px 2px rgba(5, 150, 105, .18) !important;
}
.app-button-primary:hover {
  background: var(--app-primary-hover) !important;
  box-shadow: 0 3px 8px rgba(5, 150, 105, .20) !important;
}
.app-button-secondary, .q-btn.app-button-secondary {
  color: #374151 !important;
  background: #ffffff !important;
  border: 1px solid var(--app-border-strong) !important;
}
.app-button-secondary:hover {
  border-color: #aebdb7 !important;
  background: var(--app-surface-subtle) !important;
}
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
  background: #fcfdfd;
  transition: background-color .16s ease, box-shadow .16s ease;
}
.q-field--outlined .q-field__control:before { border-color: var(--app-border-strong) !important; }
.q-field--outlined.q-field--focused .q-field__control:after {
  border-color: var(--app-primary) !important;
  border-width: 1px !important;
}
.q-field--outlined.q-field--focused .q-field__control {
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, .09);
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
  box-shadow: 0 1px 2px rgba(15, 23, 42, .025);
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
.app-workflow-step--current { background: #f4fbf8; }
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
.app-table {
  width: 100%;
  overflow: hidden;
  border: 1px solid var(--app-border);
  border-radius: var(--app-radius);
  background: #ffffff;
}
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
  background: #f0f5f3;
  border-bottom: 1px solid var(--app-border);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0;
}
.app-table-row { background: #ffffff; border-bottom: 1px solid var(--app-border); }
.app-table-row:last-child { border-bottom: 0; }
.app-table-row:hover { background: #f7fbf9; }
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
.app-status--success { color: #047857; background: #ecfdf5; border: 1px solid #d1fae5; }
.app-status--warning { color: #b45309; background: #fffbeb; border: 1px solid #fef3c7; }
.app-status--danger { color: #b91c1c; background: #fef2f2; border: 1px solid #fee2e2; }
.app-status--info { color: #0369a1; background: #f0f9ff; border: 1px solid #e0f2fe; }
.app-status--neutral { color: #4b5563; background: #f3f4f6; border: 1px solid #e5e7eb; }
.app-status-dot { width: 6px; height: 6px; border-radius: 999px; background: currentColor; }
.app-step-chip {
  width: fit-content !important;
  min-height: 27px;
  padding: 3px 8px;
  border: 1px solid transparent;
  border-radius: 7px;
}
.app-step-chip--pending { color: #64748b; background: #f3f6f5; border-color: #e2e8e5; }
.app-step-chip--processing { color: #0369a1; background: #f0f9ff; border-color: #dbeafe; }
.app-step-chip--successful { color: #047857; background: #ecfdf5; border-color: #d1fae5; }
.app-step-chip--stopped { color: #b45309; background: #fffbeb; border-color: #fef3c7; }
.app-step-chip--unsuccessful,
.app-step-chip--error { color: #b91c1c; background: #fef2f2; border-color: #fee2e2; }
.app-step-chip--skipped { color: #64748b; background: #f8fafc; border-color: #e5e7eb; }
.app-empty-state {
  width: 100%;
  min-height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--app-border-strong);
  border-radius: var(--app-radius);
  background: #f6f9f8;
}
.app-channel-card, .q-card.app-channel-card {
  width: 176px;
  min-height: 54px;
  padding: 10px 12px;
  cursor: pointer;
  border: 1px solid var(--app-border) !important;
  border-radius: 9px !important;
  color: var(--app-text);
  background: #f8faf9 !important;
  box-shadow: 0 1px 2px rgba(15, 23, 42, .025) !important;
  transition: border-color .16s ease, background-color .16s ease;
}
.app-channel-card:hover { border-color: #86d8b9 !important; background: #f2fbf7 !important; }
.app-channel-card--selected, .q-card.app-channel-card--selected {
  color: #065f46;
  border-color: #6ee7b7 !important;
  background: var(--app-primary-soft) !important;
  box-shadow: inset 3px 0 0 var(--app-primary) !important;
}

/* Add audio page polish: keep the existing layout while tightening hierarchy. */
.audio-add-page { gap: 20px; }
.audio-add-page .app-card,
.audio-add-page .q-card.app-card {
  padding: 22px;
  border-color: var(--app-border) !important;
  border-radius: 11px !important;
  box-shadow: 0 1px 2px rgba(15, 23, 42, .04), 0 8px 20px rgba(15, 23, 42, .025) !important;
}
.audio-add-page .app-section-title {
  font-size: 18px;
  font-weight: 600;
  line-height: 1.4;
}
.audio-add-page .app-section-copy {
  color: #6b7280;
  font-size: 14px;
  line-height: 1.5;
}
.audio-add-page .q-field--outlined .q-field__control { min-height: 46px; }
.audio-add-page .q-field--outlined .q-field__control:before {
  border-color: #d1d5db !important;
}
.audio-add-page .q-field--outlined.q-field--focused .q-field__control:after {
  border-color: #10b981 !important;
}
.audio-add-page .app-button-primary,
.audio-add-page .audio-add-destructive {
  min-height: 45px;
}
.audio-add-page .app-button-primary {
  color: #ffffff !important;
  background: #10b981 !important;
}
.audio-add-page .audio-add-destructive {
  color: #dc2626 !important;
  background: #ffffff !important;
  border: 1px solid #d1d5db !important;
}
.audio-add-page .audio-add-destructive:hover {
  color: #b91c1c !important;
  background: #fef2f2 !important;
}
.audio-add-page .app-channel-card--selected,
.audio-add-page .q-card.app-channel-card--selected {
  border-color: #a7f3d0 !important;
  background: #ecfdf5 !important;
}
.audio-add-main-card,
.q-card.audio-add-main-card {
  position: relative;
  overflow: hidden;
  border-color: #9fdfc5 !important;
  box-shadow: 0 2px 4px rgba(16, 185, 129, .055), 0 10px 24px rgba(15, 23, 42, .035) !important;
}
.audio-add-main-card::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: var(--app-primary);
}
.audio-add-section .app-section-title { color: #17231f; }
.audio-add-table {
  overflow: hidden;
  border: 1px solid var(--app-border);
  border-radius: 10px;
  gap: 0 !important;
}
.audio-add-table-header { background: #f0f5f3 !important; }
.audio-add-table-row:hover { background: #f7fbf9 !important; }
.audio-add-table-row:last-child { border-bottom: 0 !important; }
.app-auth-page {
  width: 100%;
  min-height: 100vh;
  padding: 32px;
  display: grid;
  place-items: center;
  background: #f7f8f8;
}
.app-auth-panel, .q-card.app-auth-panel {
  width: min(440px, 100%);
  padding: 34px;
  border: 1px solid var(--app-border) !important;
  border-radius: 14px !important;
  background: #ffffff !important;
  box-shadow: 0 10px 35px rgba(17, 24, 39, .055) !important;
}
.app-flow-folder, .q-card.app-flow-folder {
  min-height: 76px;
  border: 1px solid var(--app-border) !important;
  border-radius: 9px !important;
  background: var(--app-surface-subtle) !important;
  box-shadow: none !important;
}
.app-flow-folder:hover { border-color: #a7f3d0 !important; background: #f8fffc !important; }
.app-progress-panel, .q-card.app-progress-panel {
  border: 1px solid #bae6fd !important;
  border-radius: 9px !important;
  background: #f0f9ff !important;
  box-shadow: none !important;
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
  .app-auth-page { padding: 16px; }
  .app-auth-panel, .q-card.app-auth-panel { padding: 26px 22px; }
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
    action_label: str = "",
    on_action: Callable[[], None] | None = None,
) -> None:
    with ui.element("div").classes("app-empty-state"):
        with ui.column().classes("items-center gap-2 text-center px-6"):
            ui.icon(icon).classes("text-3xl text-gray-400")
            ui.label(title).classes("text-sm font-semibold text-gray-700")
            if description:
                ui.label(description).classes("text-xs text-gray-500 max-w-md")
            if action_label and on_action:
                ui.button(
                    action_label,
                    icon="add",
                    on_click=on_action,
                ).classes("app-button-primary mt-2")
