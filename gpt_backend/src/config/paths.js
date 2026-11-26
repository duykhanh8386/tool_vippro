import { pathToFileURL as N3, fileURLToPath as Dg } from "url";
import Ue from "path";
import kg from "os";
var Ig = import.meta.url,
  Ng = Dg(Ig),
  Cx = Ue.resolve(Ue.dirname(Ng), "..");
var H3 = process.env.APP_RESOURCES_PATH ? Ue.join(process.env.APP_RESOURCES_PATH, ".env") : Ue.resolve(Cx, "..", ".env"),
  Ix = process.env.NODE_ENV === "development" || !process.env.NODE_ENV;
function je(e) {
  if (!e) return null;
  let a = e.trim().toLowerCase();
  return ["1", "true", "yes", "on"].includes(a) ? !0 : ["0", "false", "no", "off"].includes(a) ? !1 : null;
}
var Wt = je(process.env.APP_BACKGROUND_BROWSER) ?? !Ix,
  Mg = je(process.env.GROK_EMBEDDED_BROWSER) ?? !0,
  Rg = je(process.env.GROK_EXTERNAL_BROWSER_HIDE) ?? !0,
  Fg = je(process.env.VEO3_EMBEDDED_BROWSER) ?? !1,
  Pg = je(process.env.VEO3_EXTERNAL_BROWSER_HIDE) ?? !1,
  Pa = je(process.env.VEO3_DEBUG_WORKER_WINDOW) ?? !1;
function L(e) {
  return e === "grok" ? Mg : Fg;
}
function Ea(e) {
  return e === "grok" ? Rg : Pg;
}
var Kr = je(process.env.APP_SHOW_LOG_VIEWER_BUTTON) ?? je(process.env.GROK_SHOW_LOG_VIEWER_BUTTON) ?? !1,
  Po = je(process.env.APP_SHOW_LOG_SOURCE) ?? je(process.env.GROK_SHOW_LOG_SOURCE) ?? !1,
  W3 = je(process.env.VEO3_FAKE_RECAPTCHA_ON_DIRECT) ?? !1,
  ku = je(process.env.VEO3_RECYCLE_AFTER_SUCCESS) ?? L("veo3"),
  vu = Number(process.env.VEO3_RECYCLE_DELAY_MS || 500),
  Hr = Number.isFinite(vu) && vu >= 0 ? vu : 500,
  Wr = je(process.env.APP_EXTERNAL_BROWSER_HIDE_STRICT) ?? !1,
  qr = je(process.env.GROK_UI_DEBUG_WORKER_WINDOW) ?? !1,
  Nu = je(process.env.GROK_UI_SKIP_SUBMIT) ?? !1,
  Cu = Number(process.env.GROK_UI_SUBMIT_DEBUG_DELAY_MS || 0),
  Yr = Number.isFinite(Cu) && Cu > 0 ? Cu : 0,
  Iu = Number(process.env.GROK_UI_PRE_SUBMIT_DEBUG_DELAY_MS || 0),
  Go = Number.isFinite(Iu) && Iu > 0 ? Iu : 0,
  Du = Number(process.env.APP_LOG_BUFFER_SIZE || 2e3),
  Dx = Number.isFinite(Du) && Du > 0 ? Du : 2e3,
  Ga = process.env.TVA_GPT_DATA_ROOT || (Ix ? Ue.resolve(Cx, "..") : Ue.join(kg.homedir(), ".phoma")),
  he = Ue.join(Ga, "app"),
  Mu = Number(process.env.APP_BROWSER_SERVER_PORT || 3001),
  kx = process.env.LICENSE_API_ORIGIN || "http://127.0.0.1:4000";
var Nx = process.env.GENERATION_LEASE_PUBLIC_KEY?.replace(/\\n/g, `
`).trim() || "",
  _n = Mu,
  ga = `http://127.0.0.1:${_n}`;
function Mx(e) {
  _n = e, ga = `http://127.0.0.1:${e}`;
}
var Ta = 9223,
  Ru = Number(process.env.APP_ELECTRON_CDP_PORT || 9333),
  To = "chrome_user_data_phoma",
  Bt = Ue.join(Ga, To),
  Rx = Ue.join(Ga, "phoma-session.json"),
  Zr = Ue.join(he, "accounts"),
  qt = Ue.join(he, "accounts.json"),
  Ye = Ue.join(Ga, "downloads"),
  $ = Ue.join(he, "projects"),
  Xr = Ue.join(he, "settings.json"),
  ln = Ue.join(Ga, "grok-images"),
  Ze = Ue.join(Ga, "veo3-images");
var Lo = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  Fx = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Chromium.app/Contents/MacOS/Chromium", "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe", "/usr/bin/google-chrome", "/usr/bin/chromium-browser"];
export { $, Bt, Dx, Ea, Fx, Ga, Go, Hr, Kr, L, Lo, Mu, Mx, Nu, Nx, Pa, Po, Ru, Rx, Ta, To, Wr, Wt, Xr, Ye, Yr, Ze, Zr, _n, ga, he, ku, kx, ln, qr, qt };
