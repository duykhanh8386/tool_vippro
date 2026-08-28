"""Shared visual system for the TV Automation web interface."""

from __future__ import annotations

from nicegui import ui


THEME_CSS = r"""
:root {
  --app-bg: #f4f7fb;
  --app-surface: #ffffff;
  --app-surface-soft: #f8fafc;
  --app-ink: #142033;
  --app-muted: #64748b;
  --app-line: #e2e8f0;
  --app-primary: #0f766e;
  --app-primary-dark: #115e59;
  --app-accent: #14b8a6;
  --app-navy: #0b172a;
  --app-navy-soft: #13233a;
  --app-danger: #dc2626;
  --app-warning: #d97706;
  --app-radius: 18px;
  --nicegui-default-padding: 1rem;
  --nicegui-default-gap: 1rem;
}

html, body, #app { min-height: 100%; }
body {
  margin: 0;
  color: var(--app-ink);
  background:
    radial-gradient(circle at 82% 5%, rgba(20, 184, 166, .08), transparent 24rem),
    var(--app-bg);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
    "Segoe UI", sans-serif;
  -webkit-font-smoothing: antialiased;
}

.nicegui-content {
  width: 100%;
  max-width: 1600px;
  margin-inline: auto;
  padding: 28px 32px 48px;
  gap: 18px;
}

.app-page { width: 100%; gap: 18px; }

.app-sidebar {
  background: linear-gradient(180deg, var(--app-navy) 0%, #0d1c31 100%) !important;
  border-right: 1px solid rgba(255,255,255,.06) !important;
  color: #dbe7f4;
}
.app-sidebar .q-drawer__content { overflow-x: hidden; }
.app-brand-mark {
  width: 44px; height: 44px; border-radius: 14px;
  display: grid; place-items: center;
  color: #052e2b;
  background: linear-gradient(135deg, #5eead4, #2dd4bf);
  box-shadow: 0 10px 28px rgba(20,184,166,.25);
}
.app-nav-item {
  min-height: 46px !important;
  margin: 4px 12px !important;
  padding: 0 14px !important;
  border-radius: 12px !important;
  color: #aebed1 !important;
  background: transparent !important;
}
.app-nav-item:hover {
  color: white !important;
  background: rgba(255,255,255,.07) !important;
}
.app-nav-item--active {
  color: #ecfeff !important;
  background: linear-gradient(90deg, rgba(20,184,166,.24), rgba(20,184,166,.08)) !important;
  box-shadow: inset 3px 0 0 #2dd4bf;
}
.app-sidebar .q-expansion-item__container > .q-item {
  margin: 10px 12px 4px;
  min-height: 42px;
  padding: 0 14px;
  border-radius: 12px;
  color: #d7e2ee;
  font-weight: 700;
}
.app-sidebar .q-expansion-item__container > .q-item:hover {
  background: rgba(255,255,255,.06);
}

.app-topbar {
  height: 72px;
  padding: 0 28px;
  color: var(--app-ink) !important;
  background: rgba(255,255,255,.88) !important;
  border-bottom: 1px solid rgba(226,232,240,.9) !important;
  backdrop-filter: blur(14px);
}
.app-route-kicker {
  color: var(--app-primary);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .12em;
  text-transform: uppercase;
}
.app-route-title { font-size: 18px; font-weight: 800; letter-spacing: -.02em; }

.q-card {
  border: 1px solid var(--app-line) !important;
  border-radius: var(--app-radius) !important;
  background: rgba(255,255,255,.96) !important;
  box-shadow: 0 8px 28px rgba(15,23,42,.055) !important;
}
.q-card[style*="min-height: 85vh"] { min-height: auto !important; }

.q-btn {
  min-height: 42px;
  border-radius: 12px !important;
  font-weight: 750 !important;
  letter-spacing: 0 !important;
  text-transform: none !important;
  box-shadow: none !important;
}
.q-btn.bg-primary, .q-btn.text-primary:not(.q-btn--outline) {
  background: var(--app-primary) !important;
}
.q-btn.bg-primary:hover { background: var(--app-primary-dark) !important; }
.q-btn--round { min-height: auto; }

.q-field--outlined .q-field__control {
  min-height: 48px;
  border-radius: 12px !important;
  background: #fff;
}
.q-field--outlined .q-field__control:before { border-color: #cbd5e1 !important; }
.q-field--outlined.q-field--focused .q-field__control:after {
  border-color: var(--app-primary) !important;
  border-width: 2px !important;
}
.q-field__label { color: var(--app-muted) !important; }

.q-dialog__inner > .q-card {
  border-radius: 22px !important;
  box-shadow: 0 24px 70px rgba(2,6,23,.22) !important;
}
.q-linear-progress { border-radius: 999px; overflow: hidden; }
.q-badge { border-radius: 999px; font-weight: 700; }

.app-section-title { font-size: 16px; font-weight: 800; color: var(--app-ink); }
.app-section-copy { font-size: 13px; color: var(--app-muted); line-height: 1.55; }
.app-empty-state {
  width: 100%; min-height: 220px;
  display: flex; align-items: center; justify-content: center;
  border: 1px dashed #cbd5e1;
  border-radius: 16px;
  background: var(--app-surface-soft);
}
.app-status-dot {
  width: 8px; height: 8px; border-radius: 999px;
  background: #22c55e; box-shadow: 0 0 0 4px rgba(34,197,94,.12);
}
.app-auth-page {
  min-height: 100vh; width: 100%; padding: 24px;
  display: grid; place-items: center;
  background:
    radial-gradient(circle at 18% 20%, rgba(45,212,191,.18), transparent 28rem),
    linear-gradient(135deg, #081426, #10233c);
}
.app-auth-shell {
  width: min(1020px, 100%);
  display: grid;
  grid-template-columns: 1.1fr .9fr;
  overflow: hidden;
  border: 1px solid rgba(255,255,255,.12);
  border-radius: 28px;
  background: rgba(255,255,255,.98);
  box-shadow: 0 32px 90px rgba(0,0,0,.3);
}
.app-auth-brand {
  min-height: 580px; padding: 52px;
  color: white;
  background:
    radial-gradient(circle at 80% 10%, rgba(45,212,191,.3), transparent 18rem),
    linear-gradient(145deg, #0f766e, #0b172a 72%);
}
.app-auth-form { padding: 52px 44px; align-self: center; }

@media (max-width: 900px) {
  .nicegui-content { padding: 20px 16px 36px; }
  .app-topbar { padding: 0 16px; }
  .app-auth-shell { grid-template-columns: 1fr; }
  .app-auth-brand { min-height: auto; padding: 32px; }
  .app-auth-form { padding: 36px 28px; }
}
@media (max-width: 600px) {
  .nicegui-content { padding: 16px 12px 28px; }
  .q-card { border-radius: 14px !important; }
  .app-auth-page { padding: 0; }
  .app-auth-shell { min-height: 100vh; border-radius: 0; }
  .app-auth-brand { display: none; }
  .app-auth-form { padding: 32px 22px; }
}
"""


def install_theme() -> None:
    ui.add_css(THEME_CSS, shared=True)


def apply_page_theme() -> None:
    ui.colors(
        primary="#0f766e",
        secondary="#0b172a",
        accent="#14b8a6",
        positive="#16a34a",
        negative="#dc2626",
        warning="#d97706",
        info="#0284c7",
    )

