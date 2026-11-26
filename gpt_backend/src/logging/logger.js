import _o from "fs";
import qg from "path";
import { Dx, Po, Rx } from "../config/paths.js";
var Qr = globalThis.__APP_RAW_CONSOLE__,
  Px = "browser-server",
  Gg = {
    debug: Qr?.debug ?? console.debug.bind(console),
    info: Qr?.info ?? console.info.bind(console),
    warn: Qr?.warn ?? console.warn.bind(console),
    error: Qr?.error ?? console.error.bind(console)
  },
  Gx = Qr?.log ?? console.log.bind(console),
  Zt = [],
  Tx = !1,
  Tg = 0,
  Yt = {
    reset: "\x1B[0m",
    dim: "\x1B[2m",
    debug: "\x1B[36m",
    info: "\x1B[34m",
    success: "\x1B[32m",
    warn: "\x1B[33m",
    error: "\x1B[31m"
  };
function Lg(e) {
  let a = new Date(e);
  return Number.isNaN(a.getTime()) ? e : a.toLocaleTimeString("vi-VN", {
    hour12: !1
  });
}
function _g(e) {
  Zt.push(e);
  let a = Math.max(100, Dx);
  Zt.length > a && Zt.splice(0, Zt.length - a);
}
function Og(e) {
  return !!e && typeof e == "object" && Object.getPrototypeOf(e) === Object.prototype;
}
function Vg(e) {
  if (e instanceof Error) return {
    name: e.name,
    message: e.message,
    stack: e.stack
  };
  if (Og(e) || Array.isArray(e)) try {
    return JSON.parse(JSON.stringify(e));
  } catch {
    return String(e);
  }
  return e;
}
function Ug(e) {
  let a = e.match(/^\[([^\]]+)\]\s*/);
  if (!a) return null;
  let n = a[1].trim();
  return /browser/i.test(n) ? "Browser" : /veo\s*3|veo3/i.test(n) ? "Veo 3" : /grok/i.test(n) ? "Grok" : /urban/i.test(n) ? "UrbanVPN" : /project/i.test(n) ? "Project" : /account/i.test(n) ? "Account" : /download/i.test(n) ? "Download" : /api/i.test(n) ? "API" : /main|electron/i.test(n) ? "Electron" : n.slice(0, 36) || null;
}
function jg(e) {
  return e.replace(/^\[[^\]]+\]\s*/, "").trim();
}
function zg(e, a) {
  return /Browser/i.test(a) ? "\u{1F310}" : /Veo/i.test(a) ? "\u2728" : /Grok/i.test(a) ? "\u{1F916}" : /Urban/i.test(a) ? "\u{1F6E1}\uFE0F" : /Project/i.test(a) ? "\u{1F4C1}" : /Account/i.test(a) ? "\u{1F464}" : /Download/i.test(a) ? "\u{1F4E5}" : /API/i.test(a) ? "\u{1F50C}" : /Electron/i.test(a) ? "\u{1F5A5}\uFE0F" : e === "success" ? "\u2705" : e === "error" ? "\u274C" : e === "warn" ? "\u26A0\uFE0F" : e === "debug" ? "\u{1F9E9}" : "\u2139\uFE0F";
}
function Jg(e) {
  return e === "error" ? "\u274C" : e === "warn" ? "\u26A0\uFE0F" : e === "success" ? "\u2705" : e === "debug" ? "\u{1F9E9}" : "\u2139\uFE0F";
}
function Kg(e) {
  let a = Yt[e.level],
    n = Po && e.source ? ` ${Yt.dim}[${e.source}]${Yt.reset}` : "";
  return `${Yt.dim}[${Lg(e.time)}]${Yt.reset} ${Jg(e.level)} ${a}${e.level.toUpperCase()}${Yt.reset} ${e.emoji}${n} ${e.message}`;
}
function Hg() {
  let a = (new Error().stack?.split(`
`).slice(1) ?? []).find(o => {
    let l = o.replace(/\\/g, "/");
    return !l.includes("/utils/logger.") && !l.includes("node:internal") && !l.includes("node_modules");
  });
  if (!a) return;
  let n = a.match(/(?:\()?(.*?)(?::(\d+):(\d+))\)?$/);
  return n ? `${n[1].replace(/\\/g, "/").split("/").slice(-2).join("/")}:${n[2]}` : void 0;
}
function Wg(e, a, n) {
  let t = typeof n[0] == "string" ? n[0] : "",
    i = (t ? Ug(t) : null) || a || "App",
    o = [],
    l = [];
  n.forEach((u, m) => {
    if (typeof u == "string") {
      let c = m === 0 ? jg(u) : u;
      c && o.push(c);
      return;
    }
    if (typeof u == "number" || typeof u == "boolean" || u == null) {
      o.push(String(u));
      return;
    }
    l.push(Vg(u));
  });
  let s = o.join(" ").trim() || "(kh\xF4ng c\xF3 n\u1ED9i dung log)";
  return {
    id: `${Px}-${Date.now()}-${++Tg}`,
    time: new Date().toISOString(),
    level: e,
    runtime: Px,
    scope: i,
    source: Hg(),
    emoji: zg(e, i),
    message: s,
    data: l.length ? l : void 0
  };
}
function La(e, a, n) {
  let t = Wg(e, a, n);
  _g(t);
  let r = Kg(t),
    i = t.data?.length ? [r, ...t.data] : [r];
  if (e === "success") {
    Gx(...i);
    return;
  }
  if (e === "info") {
    Gx(...i);
    return;
  }
  Gg[e](...i);
}
function D(e) {
  return {
    debug: (...a) => La("debug", e, a),
    info: (...a) => La("info", e, a),
    success: (...a) => La("success", e, a),
    warn: (...a) => La("warn", e, a),
    error: (...a) => La("error", e, a)
  };
}
function Lx() {
  Tx || (Tx = !0, console.log = (...e) => La("info", "App", e), console.info = (...e) => La("info", "App", e), console.debug = (...e) => La("debug", "App", e), console.warn = (...e) => La("warn", "App", e), console.error = (...e) => La("error", "App", e));
}
function _x(e = 500) {
  let a = Math.max(1, Math.min(5e3, Number(e) || 500));
  return Zt.slice(-a);
}
function Ox() {
  Zt.length = 0;
}
var Vx = D("Cache"),
  $r = Rx,
  se = {
    statsigIdMedia: "",
    statsigIdChat: ""
  };
function Oo(e) {
  $r = e;
}
function Fu() {
  se.statsigIdMedia = "", se.statsigIdChat = "";
}
function Xt() {
  try {
    if (Fu(), _o.existsSync($r)) {
      let e = JSON.parse(_o.readFileSync($r, "utf-8"));
      Object.assign(se, e), Vx.info("[Cache] Loaded:", JSON.stringify({
        hasStatsigMedia: !!se.statsigIdMedia,
        hasStatsigChat: !!se.statsigIdChat
      }));
    }
  } catch (e) {
    Vx.error("[Cache] Load error:", e.message);
  }
}
function Vo() {
  _o.mkdirSync(qg.dirname($r), {
    recursive: !0
  }), _o.writeFileSync($r, JSON.stringify(se, null, 2));
}
export { D, Fu, Lx, Oo, Ox, Vo, Xt, _x, se };
