import s7 from "node:crypto";
import e7 from "node:crypto";
import { performance as Gl } from "node:perf_hooks";
import { sha3_512 as M0 } from "@noble/hashes/sha3.js";
var R0 = "https://chatgpt.com/backend-api/sentinel/sdk.js",
  F0 = ["registerProtocolHandler\u2212function registerProtocolHandler() { [native code] }", "storage\u2212[object StorageManager]", "locks\u2212[object LockManager]", "appCodeName\u2212Mozilla", "permissions\u2212[object Permissions]", "share\u2212function share() { [native code] }", "webdriver\u2212false", "managed\u2212[object NavigatorManagedData]", "canShare\u2212function canShare() { [native code] }", "vendor\u2212Google Inc.", "mediaDevices\u2212[object MediaDevices]", "vibrate\u2212function vibrate() { [native code] }", "storageBuckets\u2212[object StorageBucketManager]", "mediaCapabilities\u2212[object MediaCapabilities]", "cookieEnabled\u2212true", "virtualKeyboard\u2212[object VirtualKeyboard]", "product\u2212Gecko", "presentation\u2212[object Presentation]", "onLine\u2212true", "mimeTypes\u2212[object MimeTypeArray]", "credentials\u2212[object CredentialsContainer]", "serviceWorker\u2212[object ServiceWorkerContainer]", "keyboard\u2212[object Keyboard]", "gpu\u2212[object GPU]", "doNotTrack", "serial\u2212[object Serial]", "pdfViewerEnabled\u2212true", "language\u2212zh-CN", "geolocation\u2212[object Geolocation]", "userAgentData\u2212[object NavigatorUAData]", "getUserMedia\u2212function getUserMedia() { [native code] }", "sendBeacon\u2212function sendBeacon() { [native code] }", "hardwareConcurrency\u221232", "windowControlsOverlay\u2212[object WindowControlsOverlay]"],
  P0 = ["0", "window", "self", "document", "name", "location", "customElements", "history", "navigation", "innerWidth", "innerHeight", "scrollX", "scrollY", "visualViewport", "screenX", "screenY", "outerWidth", "outerHeight", "devicePixelRatio", "screen", "chrome", "navigator", "onresize", "performance", "crypto", "indexedDB", "sessionStorage", "localStorage", "scheduler", "alert", "atob", "btoa", "fetch", "matchMedia", "postMessage", "queueMicrotask", "requestAnimationFrame", "setInterval", "setTimeout", "caches", "__NEXT_DATA__", "__BUILD_MANIFEST", "__NEXT_PRELOADREADY"],
  G0 = ["_reactListeningo743lnnpvdg", "location"],
  vt = class extends Error {
    constructor(a, n) {
      super("Legacy requirements proof generation failed."), this.phase = a, this.name = "LegacyProofGenerationError", this.causeName = n instanceof Error ? n.name : "unknown", this.causeCode = n && typeof n == "object" && "code" in n && typeof n.code == "string" && /^[A-Z][A-Z0-9_]+$/.test(n.code) ? n.code : void 0;
    }
    phase;
    causeName;
    causeCode;
  };
function a7(e) {
  let a = [...e.matchAll(/<script[^>]+src=["']([^"']+)["']/gi)].map(t => t[1]),
    n = a.map(t => t.match(/c\/[^/]*\/_/)?.[0]).find(Boolean) ?? e.match(/<html[^>]*data-build=["']([^"']*)["']/i)?.[1] ?? "";
  return {
    scripts: a.length ? a : [R0],
    dataBuild: n
  };
}
function ur(e) {
  return e[e7.randomInt(e.length)];
}
function T0() {
  let e = new Date(Date.now() - 18e6),
    a = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][e.getUTCDay()],
    n = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][e.getUTCMonth()],
    t = r => String(r).padStart(2, "0");
  return `${a} ${n} ${t(e.getUTCDate())} ${e.getUTCFullYear()} ${t(e.getUTCHours())}:${t(e.getUTCMinutes())}:${t(e.getUTCSeconds())} GMT-0500 (Eastern Standard Time)`;
}
function n7(e, a) {
  let n = Gl.timeOrigin + Gl.now(),
    t = [ur([3e3, 4e3, 5e3]), T0(), 4294705152, 0, e, ur(a.scripts), a.dataBuild, "en-US", "en-US,es-US,en,es", 0, ur(F0), ur(G0), ur(P0), n, e7.randomUUID(), "", ur([8, 16, 24, 32])];
  return t.push(n - (Gl.timeOrigin + Gl.now())), t;
}
function t7(e, a, n, t = 5e5) {
  let r = /^[0-9a-f]+$/i.test(a) && a.length % 2 === 0 ? a : "0fffff",
    i = Buffer.from(r, "hex"),
    o = JSON.stringify(n.slice(0, 3)).slice(0, -1) + ",",
    l = "," + JSON.stringify(n.slice(4, 9)).slice(1, -1) + ",",
    s = "," + JSON.stringify(n.slice(10)).slice(1);
  for (let u = 0; u < t; u++) {
    let m = Buffer.from(`${o}${u}${l}${u >> 1}${s}`).toString("base64"),
      c = Buffer.from(M0.create().update(e).update(m).digest());
    if (Buffer.compare(c.subarray(0, i.length), i) <= 0) return m;
  }
  return null;
}
function r7(e, a) {
  let n = Math.random().toFixed(6),
    t;
  try {
    t = n7(e, a);
  } catch (i) {
    throw new vt("config", i);
  }
  let r;
  try {
    r = t7(n, "0fffff", t);
  } catch (i) {
    throw new vt("solve", i);
  }
  try {
    return `gAAAAAC${r ?? `wQ8Lk5FbGpA2NcR9dShT6gYjU7VxZ4D${Buffer.from(JSON.stringify(n)).toString("base64")}`}`;
  } catch (i) {
    throw new vt("encode", i);
  }
}
function i7(e, a, n, t) {
  let r = t7(e, a, n7(n, t));
  if (!r) throw new Error("Kh\xF4ng gi\u1EA3i \u0111\u01B0\u1EE3c y\xEAu c\u1EA7u proof-of-work c\u1EE7a ChatGPT.");
  return `gAAAAAB${r}`;
}
export { a7, i7, r7, vt };
