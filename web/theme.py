"""Shared visual system for the Tuất Videos web interface (hieu_theme DS)."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, Iterable, Iterator, Mapping

from nicegui import ui

FONT_LINK = (
    '<link rel="preload" href="/tuat-videos-assets/fonts/inter-vietnamese-wght-normal.woff2" as="font" type="font/woff2" crossorigin>'
    '<link rel="preload" href="/tuat-videos-assets/fonts/inter-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>'
)

FONT_CSS = r"""
/* Bundled offline Inter Variable font */
@font-face {
  font-family: 'Inter';
  font-style: normal;
  font-display: swap;
  font-weight: 100 900;
  src: url('/tuat-videos-assets/fonts/inter-vietnamese-wght-normal.woff2') format('woff2-variations');
  unicode-range: U+0102-0103,U+0110-0111,U+0128-0129,U+0168-0169,U+01A0-01A1,U+01AF-01B0,U+0300-0301,U+0303-0304,U+0308-0309,U+0323,U+0329,U+1EA0-1EF9,U+20AB;
}
@font-face {
  font-family: 'Inter';
  font-style: normal;
  font-display: swap;
  font-weight: 100 900;
  src: url('/tuat-videos-assets/fonts/inter-latin-ext-wght-normal.woff2') format('woff2-variations');
  unicode-range: U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF;
}
@font-face {
  font-family: 'Inter';
  font-style: normal;
  font-display: swap;
  font-weight: 100 900;
  src: url('/tuat-videos-assets/fonts/inter-latin-wght-normal.woff2') format('woff2-variations');
  unicode-range: U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD;
}
"""

TOKENS_CSS = r"""
:root {
  --ds-neutral-0: #ffffff;
  --ds-neutral-25: #f9f9f9;
  --ds-neutral-100: #e6e8eb;
  --ds-neutral-200: #ccd0d5;
  --ds-neutral-300: #b3b8c1;
  --ds-neutral-500: #667183;
  --ds-neutral-700: #404d64;
  --ds-neutral-800: #1a2a45;
  --ds-neutral-900: #001230;
  --ds-purple-25: #f5f4fb;
  --ds-purple-50: #f0effe;
  --ds-purple-100: #e2e0fd;
  --ds-purple-500: #7260f4;
  --ds-purple-600: #5739f0;
  --ds-purple-700: #3612ed;
  --ds-purple-800: #3010d5;
  --ds-green-50: #f0fff1;
  --ds-green-600: #00ad14;
  --ds-green-800: #00840f;
  --ds-yellow-50: #fff7e5;
  --ds-yellow-500: #ffad14;
  --ds-yellow-800: #9b6500;
  --ds-orange-50: #fff6eb;
  --ds-orange-500: #ff9714;
  --ds-orange-800: #a85e00;
  --ds-red-50: #fff5f6;
  --ds-red-500: #f63741;
  --ds-red-700: #dc0a15;
  --ds-red-800: #b80811;
  --ds-red-900: #96060e;
  --ds-blue-50: #f0f6ff;
  --ds-blue-600: #0062ff;
  --ds-black-a5: #0000000d;
  --ds-black-a40: #00000066;
  --background: #ffffff;
  --muted: #f9f9f9;
  --ds-bg-brand-subtle: #f5f4fb;
  --card: #ffffff;
  --popover: #ffffff;
  --primary: #5739f0;
  --ds-primary-hover: #3612ed;
  --ds-primary-pressed: #3010d5;
  --accent: #f0effe;
  --ds-primary-soft-hover: #e2e0fd;
  --secondary: #e6e8eb;
  --ds-bg-disabled: #e6e8eb;
  --ds-control-off: #667183;
  --ds-bg-inverse: #1a2a45;
  --ds-success: #00ad14;
  --ds-success-bg: #f0fff1;
  --ds-warning: #ffad14;
  --ds-warning-bg: #fff7e5;
  --ds-orange: #ff9714;
  --ds-orange-bg: #fff6eb;
  --destructive: #dc0a15;
  --ds-error-hover: #b80811;
  --ds-error-pressed: #96060e;
  --ds-error-bg: #fff5f6;
  --ds-info: #0062ff;
  --ds-info-bg: #f0f6ff;
  --ds-overlay-subtle: #0000000d;
  --ds-scrim: #00000066;
  --ds-text-title: #001230;
  --foreground: #1a2a45;
  --ds-text-subtitle: #404d64;
  --muted-foreground: #667183;
  --ds-text-placeholder: #667183;
  --ds-text-disabled: #b3b8c1;
  --primary-foreground: #ffffff;
  --ds-text-brand: #5739f0;
  --ds-text-success: #00840f;
  --ds-text-warning: #9b6500;
  --ds-text-orange: #a85e00;
  --ds-text-error: #dc0a15;
  --ds-text-info: #0062ff;
  --ds-icon-default: #404d64;
  --ds-icon-muted: #667183;
  --ds-icon-disabled: #b3b8c1;
  --ds-icon-brand: #5739f0;
  --ds-icon-error: #f63741;
  --input: #667183;
  --border: #e6e8eb;
  --ring: #5739f0;
  --ds-border-brand-soft: #7260f4;
  --ds-border-success: #00ad14;
  --ds-border-warning: #ffad14;
  --ds-border-orange: #ff9714;
  --ds-border-error: #f63741;
  --ds-border-info: #0062ff;
  --ds-border-inverse: #ffffff;
  --radius: 8px;
  --ds-radius-xs: 4px;
  --ds-radius-md: 12px;
  --ds-radius-lg: 16px;
  --ds-radius-full: 9999px;
  --ds-shadow-popover: 0 4px 10px 0 #0000001a;
  --ds-shadow-knob: 0 1px 2px 0 #00000026;
  --ds-sidebar-width: 220px;
  --ds-sidebar-collapsed: 88px;

  /* App semantic aliases mapped to DS tokens */
  --app-bg: var(--ds-bg-brand-subtle);
  --app-surface: var(--card);
  --app-surface-subtle: var(--muted);
  --app-surface-muted: var(--ds-purple-25);
  --app-text: var(--foreground);
  --app-text-strong: var(--ds-text-title);
  --app-text-muted: var(--muted-foreground);
  --app-text-faint: #94a3b8;
  --app-border: var(--border);
  --app-border-strong: var(--ds-neutral-200);
  --app-primary: var(--primary);
  --app-primary-hover: var(--ds-primary-hover);
  --app-primary-soft: var(--accent);
  --app-primary-border: var(--ds-purple-100);
  --app-danger: var(--destructive);
  --app-warning: var(--ds-warning);
  --app-info: var(--ds-info);
  --app-radius: var(--radius);
  --app-sidebar-width: var(--ds-sidebar-width);
  --nicegui-default-padding: 1rem;
  --nicegui-default-gap: 1rem;
}

.text-canvas { color: #f5f4fb; }
.bg-canvas { background-color: #f5f4fb; }
.border-canvas { border-color: #f5f4fb; }
.text-sunken { color: #f9f9f9; }
.bg-sunken { background-color: #f9f9f9; }
.border-sunken { border-color: #f9f9f9; }
.text-line { color: #e6e8eb; }
.bg-line { background-color: #e6e8eb; }
.border-line { border-color: #e6e8eb; }
.text-line-strong { color: #ccd0d5; }
.bg-line-strong { background-color: #ccd0d5; }
.border-line-strong { border-color: #ccd0d5; }
.text-input { color: #667183; }
.bg-input { background-color: #667183; }
.border-input { border-color: #667183; }
.text-ink { color: #001230; }
.bg-ink { background-color: #001230; }
.border-ink { border-color: #001230; }
.text-body { color: #1a2a45; }
.bg-body { background-color: #1a2a45; }
.border-body { border-color: #1a2a45; }
.text-subtitle { color: #404d64; }
.bg-subtitle { background-color: #404d64; }
.border-subtitle { border-color: #404d64; }
.text-muted { color: #667183; }
.bg-muted { background-color: var(--muted); }
.border-muted { border-color: #667183; }
.text-faint { color: #94a3b8; }
.bg-faint { background-color: #94a3b8; }
.border-faint { border-color: #94a3b8; }
.text-disabled { color: #b3b8c1; }
.bg-disabled { background-color: #b3b8c1; }
.border-disabled { border-color: #b3b8c1; }
.text-disabled-bg { color: #e6e8eb; }
.bg-disabled-bg { background-color: #e6e8eb; }
.border-disabled-bg { border-color: #e6e8eb; }
.text-inverse { color: #1a2a45; }
.bg-inverse { background-color: #1a2a45; }
.border-inverse { border-color: #1a2a45; }
.text-scrim { color: #00000066; }
.bg-scrim { background-color: #00000066; }
.border-scrim { border-color: #00000066; }
.text-control-off { color: #667183; }
.bg-control-off { background-color: #667183; }
.border-control-off { border-color: #667183; }
.text-brand { color: #5739f0; }
.bg-brand { background-color: #5739f0; }
.border-brand { border-color: #5739f0; }
.text-brand-hover { color: #3612ed; }
.bg-brand-hover { background-color: #3612ed; }
.border-brand-hover { border-color: #3612ed; }
.text-brand-deep { color: #3010d5; }
.bg-brand-deep { background-color: #3010d5; }
.border-brand-deep { border-color: #3010d5; }
.text-brand-soft { color: #f0effe; }
.bg-brand-soft { background-color: #f0effe; }
.border-brand-soft { border-color: #f0effe; }
.text-brand-tint { color: #e2e0fd; }
.bg-brand-tint { background-color: #e2e0fd; }
.border-brand-tint { border-color: #e2e0fd; }
.text-brand-line { color: #7260f4; }
.bg-brand-line { background-color: #7260f4; }
.border-brand-line { border-color: #7260f4; }
.text-ok { color: #00840f; }
.bg-ok { background-color: #00840f; }
.border-ok { border-color: #00840f; }
.text-ok-dot { color: #00ad14; }
.bg-ok-dot { background-color: #00ad14; }
.border-ok-dot { border-color: #00ad14; }
.text-ok-soft { color: #f0fff1; }
.bg-ok-soft { background-color: #f0fff1; }
.border-ok-soft { border-color: #f0fff1; }
.text-ok-line { color: #00ad14; }
.bg-ok-line { background-color: #00ad14; }
.border-ok-line { border-color: #00ad14; }
.text-warn { color: #9b6500; }
.bg-warn { background-color: #9b6500; }
.border-warn { border-color: #9b6500; }
.text-warn-dot { color: #ffad14; }
.bg-warn-dot { background-color: #ffad14; }
.border-warn-dot { border-color: #ffad14; }
.text-warn-soft { color: #fff7e5; }
.bg-warn-soft { background-color: #fff7e5; }
.border-warn-soft { border-color: #fff7e5; }
.text-warn-line { color: #ffad14; }
.bg-warn-line { background-color: #ffad14; }
.border-warn-line { border-color: #ffad14; }
.text-bad { color: #dc0a15; }
.bg-bad { background-color: #dc0a15; }
.border-bad { border-color: #dc0a15; }
.text-bad-dot { color: #dc0a15; }
.bg-bad-dot { background-color: #dc0a15; }
.border-bad-dot { border-color: #dc0a15; }
.text-bad-hover { color: #b80811; }
.bg-bad-hover { background-color: #b80811; }
.border-bad-hover { border-color: #b80811; }
.text-bad-pressed { color: #96060e; }
.bg-bad-pressed { background-color: #96060e; }
.border-bad-pressed { border-color: #96060e; }
.text-bad-soft { color: #fff5f6; }
.bg-bad-soft { background-color: #fff5f6; }
.border-bad-soft { border-color: #fff5f6; }
.text-bad-line { color: #f63741; }
.bg-bad-line { background-color: #f63741; }
.border-bad-line { border-color: #f63741; }
.text-info { color: #0062ff; }
.bg-info { background-color: #0062ff; }
.border-info { border-color: #0062ff; }
.text-info-dot { color: #0062ff; }
.bg-info-dot { background-color: #0062ff; }
.border-info-dot { border-color: #0062ff; }
.text-info-soft { color: #f0f6ff; }
.bg-info-soft { background-color: #f0f6ff; }
.border-info-soft { border-color: #f0f6ff; }
.text-info-line { color: #0062ff; }
.bg-info-line { background-color: #0062ff; }
.border-info-line { border-color: #0062ff; }
.text-orange { color: #a85e00; }
.bg-orange { background-color: #a85e00; }
.border-orange { border-color: #a85e00; }
.text-orange-dot { color: #ff9714; }
.bg-orange-dot { background-color: #ff9714; }
.border-orange-dot { border-color: #ff9714; }
.text-orange-soft { color: #fff6eb; }
.bg-orange-soft { background-color: #fff6eb; }
.border-orange-soft { border-color: #fff6eb; }
.text-orange-line { color: #ff9714; }
.bg-orange-line { background-color: #ff9714; }
.border-orange-line { border-color: #ff9714; }
.text-2xs { font-size: 10px; line-height: 14px; }
.text-title-m { font-size: 24px; line-height: 32px; font-weight: 700; }
.text-title-s { font-size: 20px; line-height: 28px; font-weight: 600; }
.text-title-xs { font-size: 18px; line-height: 28px; font-weight: 600; }
.text-body-m { font-size: 16px; line-height: 24px; }
.text-body-s { font-size: 14px; line-height: 20px; }
.text-label-m { font-size: 12px; line-height: 16px; }
.text-label-s { font-size: 10px; line-height: 14px; font-weight: 500; }
.text-label-caps { font-size: 12px; line-height: 16px; font-weight: 500; letter-spacing: 0.04em; }
.rounded-xs { border-radius: var(--ds-radius-xs); }
.rounded-md { border-radius: var(--ds-radius-md); }
.rounded-card { border-radius: var(--radius); }
.rounded-panel { border-radius: var(--ds-radius-lg); }
.shadow-pop { box-shadow: var(--ds-shadow-popover); }
.shadow-knob { box-shadow: var(--ds-shadow-knob); }
"""

BASE_CSS = r"""
html, body, #app { min-height: 100%; }
body, .q-body, .nicegui-content {
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  color: var(--foreground);
  font-size: 14px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
body {
  margin: 0;
  background: var(--app-bg);
}
code, kbd, pre, samp, .font-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
}
:focus-visible { outline: 2px solid var(--ring); outline-offset: 2px; }

.nicegui-content {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 32px 40px 48px;
  gap: 24px;
}
.app-page { width: 100%; gap: 24px; }

/* Quasar according to DS */
.q-btn {
  min-height: 38px;
  padding-inline: 14px;
  text-transform: none !important;
  font-size: 13px;
  font-weight: 500 !important;
  letter-spacing: 0 !important;
  border-radius: var(--radius) !important;
  box-shadow: none !important;
}
.q-btn:before { box-shadow: none !important; }
.q-btn.bg-primary:hover { background-color: var(--ds-primary-hover) !important; }
.q-btn--dense { min-height: 30px; padding-inline: 10px; }
.q-card {
  border-radius: var(--radius);
  box-shadow: none;
  border: 1px solid var(--border);
  background: var(--card);
}
.q-field--outlined .q-field__control {
  min-height: 44px;
  border-radius: var(--radius) !important;
  background: var(--card);
  transition: background-color .16s ease, box-shadow .16s ease, border-color .16s ease;
}
.q-field--outlined.q-field--dense .q-field__control { min-height: 38px; }
.q-field--outlined .q-field__control:before { border-color: var(--ds-neutral-200) !important; }
.q-field--outlined:hover .q-field__control:before { border-color: var(--ds-neutral-300) !important; }
.q-field--outlined.q-field--focused .q-field__control:after {
  border-color: var(--ring) !important;
  border-width: 2px !important;
}
.q-field--outlined.q-field--focused .q-field__control {
  background: var(--card);
  box-shadow: 0 0 0 3px rgba(87, 57, 240, .10);
}
.q-field__label { color: var(--muted-foreground) !important; }
.q-menu, .q-dialog .q-card { box-shadow: var(--ds-shadow-popover) !important; }
.q-dialog__inner > .q-card { border-radius: var(--ds-radius-md) !important; }
.q-tab { text-transform: none; }
.q-btn-toggle {
  display: inline-flex;
  padding: 3px;
  gap: 2px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--muted);
  box-shadow: none !important;
}
.q-btn-toggle .q-btn {
  min-height: 32px;
  padding-inline: 12px;
  border-radius: 6px !important;
  font-size: 13px;
  font-weight: 500 !important;
  color: var(--ds-text-subtitle);
  background: transparent;
}
.q-btn-toggle .q-btn:not(.bg-primary):hover {
  background: var(--card);
  color: var(--ds-text-title);
}
.q-btn-toggle .q-btn.bg-primary {
  background: var(--primary) !important;
  color: var(--primary-foreground) !important;
  box-shadow: var(--ds-shadow-knob) !important;
}
.q-btn--outline {
  background: var(--card) !important;
  color: var(--foreground);
}
.q-btn--outline:before {
  border: 1px solid var(--ds-neutral-200) !important;
}
.q-btn--outline:hover {
  background: var(--muted) !important;
}
.q-btn--outline:hover:before {
  border-color: var(--ds-neutral-300) !important;
}
.q-btn--outline.text-negative {
  color: var(--destructive) !important;
}
.q-btn--outline.text-negative:before {
  border-color: #fecdd0 !important;
}
.q-btn--outline.text-negative:hover {
  background: var(--ds-error-bg) !important;
}
.q-btn--outline.text-negative:hover:before {
  border-color: var(--ds-border-error) !important;
}
.q-btn--flat:hover {
  background: var(--ds-purple-25) !important;
}
.q-btn--flat.text-negative:hover {
  background: var(--ds-error-bg) !important;
}
.q-table__card { box-shadow: none; border: 1px solid var(--border); border-radius: var(--radius); }
.q-table th, .q-table td { border-color: var(--border) !important; }
.q-table thead th { font-size: 12px; font-weight: 600; color: var(--muted-foreground); background: var(--muted); }
.q-table tbody tr:hover td { background: var(--ds-purple-25); }
.q-tooltip { background: var(--ds-bg-inverse); font-size: 12px; }
.q-linear-progress { overflow: hidden; border-radius: var(--ds-radius-full); }
* { scrollbar-width: thin; scrollbar-color: var(--ds-neutral-200) transparent; }
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--ds-neutral-200); border-radius: 9999px; }
::-webkit-scrollbar-thumb:hover { background: var(--ds-neutral-300); }

/* Sidebar */
.app-sidebar {
  width: var(--ds-sidebar-width) !important;
  color: var(--foreground);
  background: var(--card) !important;
  border-right: 1px solid var(--border) !important;
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
  border-radius: var(--radius);
  color: var(--primary-foreground);
  background: var(--primary);
  overflow: hidden;
}
.app-brand-title { color: var(--ds-text-title); font-size: 14px; font-weight: 600; line-height: 1.35; }
.app-brand-copy { color: var(--muted-foreground); font-size: 11px; line-height: 1.4; }
.app-nav-label {
  width: calc(100% - 8px);
  margin: 14px 4px 5px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--muted-foreground);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: .04em;
  text-transform: uppercase;
  line-height: 16px;
}
.app-nav-label::after {
  content: "";
  height: 1px;
  flex: 1;
  background: var(--border);
}
.app-nav-item {
  min-height: 40px !important;
  margin: 2px 0 !important;
  padding: 0 10px !important;
  display: flex !important;
  align-items: center !important;
  gap: 9px !important;
  border-radius: var(--radius) !important;
  color: var(--ds-text-subtitle) !important;
  background: transparent !important;
  border: 1px solid transparent !important;
  transition: color .15s ease, background-color .15s ease, border-color .15s ease;
}
.app-nav-item:hover {
  color: var(--ds-text-title) !important;
  background: var(--muted) !important;
  border-color: var(--border) !important;
}
.app-nav-item--active {
  color: var(--primary) !important;
  background: var(--accent) !important;
  border-color: var(--ds-purple-100) !important;
  font-weight: 600;
  box-shadow: inset 3px 0 0 var(--primary);
}
.app-nav-item .q-icon {
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  border-radius: 6px;
  color: var(--ds-icon-muted);
  transition: color .15s ease, background-color .15s ease;
}
.app-nav-item > .nicegui-label {
  min-width: 0;
  display: flex;
  align-items: center;
  line-height: 20px;
}
.app-nav-item:hover .q-icon {
  color: var(--ds-icon-default);
  background: var(--card);
}
.app-nav-item--active .q-icon {
  color: var(--primary) !important;
  background: var(--card);
}
.app-sidebar .q-expansion-item__container > .q-item {
  min-height: 40px;
  margin: 2px 0;
  padding: 0 12px;
  border-radius: var(--radius);
  color: var(--muted-foreground);
  font-size: 13px;
  font-weight: 500;
}
.app-sidebar .q-expansion-item__container > .q-item:hover {
  color: var(--ds-text-title);
  background: var(--muted);
}
.app-sidebar .q-expansion-item__content { padding-left: 8px; }

/* Compact sidebar status pills */
.app-sidebar-pill {
  width: 100%;
  padding: 8px 10px;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  background: var(--muted);
  color: var(--foreground);
  transition: background-color .15s ease, border-color .15s ease;
}
.app-sidebar-pill--clickable { cursor: pointer; }
.app-sidebar-pill--info {
  background: var(--ds-info-bg);
  border-color: #cfe0ff;
  color: var(--ds-text-info);
}
.app-sidebar-pill--info.app-sidebar-pill--clickable:hover { background: #e3eeff; }
.app-sidebar-pill--ok {
  background: var(--ds-success-bg);
  border-color: #c8f5cd;
  color: var(--ds-text-success);
}
.app-sidebar-pill--ok.app-sidebar-pill--clickable:hover { background: #e3fce5; }
.app-sidebar-pill--warn {
  background: var(--ds-warning-bg);
  border-color: #ffe2a8;
  color: var(--ds-text-warning);
}
.app-sidebar-pill--warn.app-sidebar-pill--clickable:hover { background: #ffefd0; }
.app-sidebar-pill--bad {
  background: var(--ds-error-bg);
  border-color: #fecdd0;
  color: var(--ds-text-error);
}
.app-sidebar-pill--bad.app-sidebar-pill--clickable:hover { background: #ffe5e7; }
.app-sidebar-pill--neutral {
  background: var(--muted);
  border-color: var(--border);
  color: var(--muted-foreground);
}

.app-account {
  min-height: 54px;
  padding: 8px;
  border: 1px solid transparent;
  border-radius: var(--radius);
}
.app-account:hover { background: var(--muted); border-color: var(--border); }
.app-account-avatar {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: var(--radius);
  color: var(--primary);
  background: var(--accent);
  font-size: 12px;
  font-weight: 700;
  overflow: hidden;
}

/* Page hierarchy */
.app-page-header {
  width: 100%;
  min-height: 64px;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}
.app-page-title {
  color: var(--ds-text-title);
  font-size: 24px;
  line-height: 32px;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.app-page-subtitle {
  max-width: 720px;
  color: var(--muted-foreground);
  font-size: 14px;
  line-height: 20px;
}
.app-page-eyebrow {
  color: var(--ds-text-brand);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.app-page-actions { align-items: center; justify-content: flex-end; gap: 10px; }

/* Cards and sections */
.app-card, .q-card.app-card {
  width: 100%;
  padding: 20px;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  background: var(--card) !important;
  box-shadow: none !important;
}
.app-card--compact, .q-card.app-card--compact { padding: 16px 18px; }
.app-section-header {
  width: 100%;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.app-section-title { color: var(--ds-text-title); font-size: 18px; font-weight: 600; line-height: 26px; }
.app-section-copy { color: var(--muted-foreground); font-size: 13px; line-height: 19px; }

/* Buttons */
.app-button-primary, .q-btn.app-button-primary {
  color: var(--primary-foreground) !important;
  background: var(--primary) !important;
}
.app-button-primary:hover { background: var(--ds-primary-hover) !important; }
.app-button-primary:active { background: var(--ds-primary-pressed) !important; }
.app-button-secondary, .q-btn.app-button-secondary {
  color: var(--foreground) !important;
  background: var(--card) !important;
  border: 1px solid var(--ds-neutral-200) !important;
}
.app-button-secondary:hover {
  border-color: var(--ds-neutral-300) !important;
  background: var(--muted) !important;
}
.app-button-danger, .q-btn.app-button-danger {
  color: var(--destructive) !important;
  background: var(--card) !important;
  border: 1px solid #fecdd0 !important;
}
.app-button-danger:hover {
  color: var(--ds-error-hover) !important;
  background: var(--ds-error-bg) !important;
  border-color: var(--ds-border-error) !important;
}
.app-button-danger.disabled, .q-btn.app-button-danger.disabled {
  color: var(--ds-text-disabled) !important;
  border-color: var(--border) !important;
  background: var(--muted) !important;
  opacity: 1 !important;
}
.app-icon-button { color: var(--ds-icon-muted) !important; }
.app-icon-button:hover { color: var(--ds-text-title) !important; background: var(--ds-purple-25) !important; }

/* Workflow */
.app-workflow {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(var(--workflow-count, 3), minmax(0, 1fr));
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--card);
}
.app-workflow-step {
  min-height: 70px;
  padding: 14px 18px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.app-workflow-step:not(:last-child) { border-right: 1px solid var(--border); }
.app-step-marker {
  width: 30px;
  height: 30px;
  flex: 0 0 30px;
  display: grid;
  place-items: center;
  border: 1.5px solid var(--ds-neutral-200);
  border-radius: var(--ds-radius-full);
  color: var(--muted-foreground);
  background: var(--card);
  font-size: 12px;
  font-weight: 600;
}
.app-workflow-step--complete .app-step-marker {
  color: var(--primary-foreground);
  border-color: var(--primary);
  background: var(--primary);
}
.app-workflow-step--current .app-step-marker {
  color: var(--primary);
  border-color: var(--primary);
  background: var(--accent);
}
.app-workflow-step--current { background: var(--ds-purple-25); }
.app-workflow-title { color: var(--ds-text-title); font-size: 13px; font-weight: 600; line-height: 1.4; }
.app-workflow-copy { color: var(--muted-foreground); font-size: 12px; }

.app-metrics {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-top: 1px solid var(--border);
}
.app-metric { min-width: 0; padding: 18px 20px 2px 0; }
.app-metric + .app-metric {
  padding-left: 20px;
  border-left: 1px solid var(--border);
}
.app-metric-label { color: var(--muted-foreground); font-size: 12px; font-weight: 500; }
.app-metric-value { color: var(--ds-text-title); font-size: 15px; font-weight: 600; }

/* Tables and status */
.app-table {
  width: 100%;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--card);
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
  color: var(--muted-foreground);
  background: var(--muted);
  border-bottom: 1px solid var(--border);
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0;
}
.app-table-row { background: var(--card); border-bottom: 1px solid var(--border); }
.app-table-row:last-child { border-bottom: 0; }
.app-table-row:hover { background: var(--ds-purple-25); }
.app-status {
  width: fit-content;
  min-height: 24px;
  padding: 2px 8px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: var(--ds-radius-full);
  font-size: 11px;
  font-weight: 600;
}
.app-status--success { color: var(--ds-text-success); background: var(--ds-success-bg); border: 1px solid #c8f5cd; }
.app-status--warning { color: var(--ds-text-warning); background: var(--ds-warning-bg); border: 1px solid #ffe2a8; }
.app-status--danger { color: var(--ds-text-error); background: var(--ds-error-bg); border: 1px solid #fecdd0; }
.app-status--info { color: var(--ds-text-info); background: var(--ds-info-bg); border: 1px solid #cfe0ff; }
.app-status--neutral { color: var(--ds-text-subtitle); background: var(--muted); border: 1px solid var(--border); }
.app-status-dot { width: 6px; height: 6px; border-radius: var(--ds-radius-full); background: currentColor; }
.app-step-chip {
  width: fit-content !important;
  min-height: 27px;
  padding: 3px 8px;
  border: 1px solid transparent;
  border-radius: 6px;
}
.app-step-chip--pending { color: var(--muted-foreground); background: var(--muted); border-color: var(--border); }
.app-step-chip--processing { color: var(--ds-text-info); background: var(--ds-info-bg); border-color: #cfe0ff; }
.app-step-chip--successful { color: var(--ds-text-success); background: var(--ds-success-bg); border-color: #c8f5cd; }
.app-step-chip--stopped { color: var(--ds-text-warning); background: var(--ds-warning-bg); border-color: #ffe2a8; }
.app-step-chip--unsuccessful,
.app-step-chip--error { color: var(--ds-text-error); background: var(--ds-error-bg); border-color: #fecdd0; }
.app-step-chip--skipped { color: var(--muted-foreground); background: var(--muted); border-color: var(--border); }
.app-empty-state {
  width: 100%;
  min-height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--ds-neutral-200);
  border-radius: var(--radius);
  background: var(--muted);
}

/* Channel selection cards */
.app-channel-card, .q-card.app-channel-card {
  width: 176px;
  min-height: 54px;
  padding: 10px 12px;
  cursor: pointer;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  color: var(--foreground);
  background: var(--muted) !important;
  box-shadow: none !important;
  transition: border-color .15s ease, background-color .15s ease;
}
.app-channel-card:hover {
  border-color: var(--ds-border-brand-soft) !important;
  background: var(--ds-purple-25) !important;
}
.app-channel-card--selected, .q-card.app-channel-card--selected {
  color: var(--primary);
  border-color: var(--ds-purple-500) !important;
  background: var(--accent) !important;
  box-shadow: inset 3px 0 0 var(--primary) !important;
}

/* Add audio page polish */
.audio-add-page { gap: 20px; }
.audio-add-main-card,
.q-card.audio-add-main-card {
  position: relative;
  overflow: hidden;
  border-color: var(--ds-purple-100) !important;
}
.audio-add-main-card::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: var(--primary);
}
.audio-add-section .app-section-title { color: var(--ds-text-title); }
.audio-add-page .audio-add-destructive {
  min-height: 42px;
  color: var(--destructive) !important;
  background: var(--card) !important;
  border: 1px solid #fecdd0 !important;
}
.audio-add-page .audio-add-destructive:hover {
  color: var(--ds-error-hover) !important;
  background: var(--ds-error-bg) !important;
  border-color: var(--ds-border-error) !important;
}
.audio-add-table {
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  gap: 0 !important;
}
.audio-add-table-header { background: var(--muted) !important; }
.audio-add-table-row:hover { background: var(--ds-purple-25) !important; }
.audio-add-table-row:last-child { border-bottom: 0 !important; }

/* Auth, folders, progress */
.app-auth-page {
  width: 100%;
  min-height: 100vh;
  padding: 32px;
  display: grid;
  place-items: center;
  background: var(--app-bg);
}
.app-auth-panel, .q-card.app-auth-panel {
  width: min(440px, 100%);
  padding: 32px;
  border: 1px solid var(--border) !important;
  border-radius: var(--ds-radius-lg) !important;
  background: var(--card) !important;
  box-shadow: var(--ds-shadow-popover) !important;
}
.app-flow-folder, .q-card.app-flow-folder {
  min-height: 76px;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  background: var(--muted) !important;
  box-shadow: none !important;
  transition: border-color .15s ease, background-color .15s ease;
}
.app-flow-folder:hover {
  border-color: var(--ds-border-brand-soft) !important;
  background: var(--ds-purple-25) !important;
}
.app-progress-panel, .q-card.app-progress-panel {
  border: 1px solid #cfe0ff !important;
  border-radius: var(--radius) !important;
  background: var(--ds-info-bg) !important;
  box-shadow: none !important;
}

@media (max-width: 980px) {
  .nicegui-content { padding: 28px 24px 40px; }
  .app-page-header { flex-direction: column; }
  .app-page-actions { width: 100%; justify-content: flex-start; }
  .app-workflow { grid-template-columns: 1fr; }
  .app-workflow-step:not(:last-child) { border-right: 0; border-bottom: 1px solid var(--border); }
  .app-metrics { grid-template-columns: 1fr; }
  .app-metric { padding: 14px 0; }
  .app-metric + .app-metric { padding-left: 0; border-left: 0; border-top: 1px solid var(--border); }
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

THEME_CSS = FONT_CSS + TOKENS_CSS + BASE_CSS


def install_theme() -> None:
    """Register the shared Inter font and DS CSS tokens once at app startup."""
    ui.add_head_html(FONT_LINK, shared=True)
    ui.add_css(THEME_CSS, shared=True)
    apply_page_theme()


def apply_page_theme() -> None:
    """Apply Quasar DS colors for the current page/client."""
    ui.colors(
        primary="#5739f0",    # purple-600
        secondary="#e6e8eb",  # neutral-100
        accent="#f0effe",     # purple-50
        dark="#1a2a45",       # neutral-800
        positive="#00ad14",   # green-600
        negative="#dc0a15",   # red-700
        info="#0062ff",       # blue-600
        warning="#ffad14",    # yellow-500
    )


apply_theme = apply_page_theme


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
            ui.icon(icon).classes("text-3xl text-disabled")
            ui.label(title).classes("text-body-s font-semibold text-ink")
            if description:
                ui.label(description).classes("text-label-m text-muted max-w-md")
            if action_label and on_action:
                ui.button(
                    action_label,
                    icon="add",
                    on_click=on_action,
                ).classes("app-button-primary mt-2")
