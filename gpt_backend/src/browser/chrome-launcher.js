import Df from "fs";
import Ni from "puppeteer-core";
import On from "fs";
import Yg from "http";
import Ux from "path";
import { spawn as zx } from "child_process";
import { Bt, Fx, Ta } from "../config/paths.js";
import { D } from "../logging/logger.js";
function Vn() {
  for (let e of Fx) if (On.existsSync(e)) return e;
  throw new Error("Chrome not found. Install Google Chrome or Chromium.");
}
function _a(e = Ta) {
  return new Promise(a => {
    let n = Yg.get(`http://127.0.0.1:${e}/json/version`, t => {
      a(t.statusCode === 200);
    });
    n.on("error", () => a(!1)), n.setTimeout(1500, () => {
      n.destroy(), a(!1);
    });
  });
}
function Pu(e = 3e4, a = Ta) {
  return new Promise((n, t) => {
    let r = Date.now(),
      i = async () => {
        if (await _a(a)) return n();
        if (Date.now() - r > e) return t(new Error("CDP timeout"));
        setTimeout(i, 400);
      };
    i();
  });
}
function jx(e) {
  try {
    if (!On.existsSync(e)) return;
    let a = On.readFileSync(e, "utf8"),
      n = JSON.parse(a);
    if (!n || typeof n != "object") return;
    n.profile = n.profile && typeof n.profile == "object" ? n.profile : {};
    let t = !1;
    n.profile.exit_type === "Crashed" && (n.profile.exit_type = "Normal", t = !0), n.profile.exited_cleanly === !1 && (n.profile.exited_cleanly = !0, t = !0), t && On.writeFileSync(e, JSON.stringify(n));
  } catch {}
}
function Jx(e) {
  try {
    if (jx(Ux.join(e, "Local State")), !On.existsSync(e)) return;
    for (let a of On.readdirSync(e, {
      withFileTypes: !0
    })) a.isDirectory() && jx(Ux.join(e, a.name, "Preferences"));
  } catch {}
}
function Uo(e, a = {}) {
  let n = a.port ?? Ta,
    t = a.userDataDir ?? Bt,
    r = a.startUrl ?? (a.background ? "about:blank" : "https://grok.com/"),
    i = process.platform === "win32",
    o = a.background ? ["--start-minimized", "--window-size=1440,1000", ...(i ? ["--window-position=-32000,-32000"] : []), "--disable-backgrounding-occluded-windows", "--disable-renderer-backgrounding"] : i ? ["--window-position=100,100"] : [];
  return On.mkdirSync(t, {
    recursive: !0
  }), Jx(t), zx(e, [`--remote-debugging-port=${n}`, "--remote-debugging-address=127.0.0.1", `--user-data-dir=${t}`, "--remote-allow-origins=*", "--no-first-run", "--no-default-browser-check", "--disable-session-crashed-bubble", "--disable-sync", ...(a.proxyServer ? [`--proxy-server=${a.proxyServer}`] : []), ...o, ...(a.background && a.noStartupWindow ? ["--no-startup-window"] : r ? [r] : [])], {
    stdio: "ignore",
    detached: !1
  });
}
function Kx(e, a) {
  return On.mkdirSync(a.userDataDir, {
    recursive: !0
  }), Jx(a.userDataDir), zx(e, [`--user-data-dir=${a.userDataDir}`, "--no-first-run", "--no-default-browser-check", "--disable-session-crashed-bubble", "--disable-sync", "--new-window", ...(a.proxyServer ? [`--proxy-server=${a.proxyServer}`] : []), a.startUrl], {
    stdio: "ignore",
    detached: !0
  });
}
var Gu = new WeakSet(),
  Hx = D("Browser");
function jo(e, a) {
  a ? Gu.add(e) : Gu.delete(e);
}
async function Wx(e) {
  if (!Gu.has(e)) return e.newPage();
  let a, n;
  try {
    a = await e.target().createCDPSession();
    let t = !(await e.pages()).some(l => !l.isClosed()),
      r = {
        url: "about:blank",
        background: !0,
        ...(t ? {
          newWindow: !0,
          width: 1440,
          height: 1e3
        } : {})
      };
    try {
      ({
        targetId: n
      } = await a.send("Target.createTarget", {
        ...r,
        ...(t ? {
          windowState: "minimized"
        } : {})
      }));
    } catch (l) {
      if (!t || !/invalid param|windowState|unsupported.*minimiz/i.test(l.message)) throw l;
      Hx.warn("Chrome kh\xF4ng h\u1ED7 tr\u1EE3 t\u1EA1o c\u1EEDa s\u1ED5 thu nh\u1ECF qua CDP; s\u1EBD thu nh\u1ECF sau khi t\u1EA1o n\u1EC1n."), {
        targetId: n
      } = await a.send("Target.createTarget", r);
    }
    let o = await (await e.waitForTarget(async l => {
      if (l.type() !== "page") return !1;
      let s = await l.createCDPSession().catch(() => null);
      if (!s) return !1;
      try {
        let {
          targetInfo: u
        } = await s.send("Target.getTargetInfo");
        return u.targetId === n;
      } catch {
        return !1;
      } finally {
        await s.detach().catch(() => {});
      }
    }, {
      timeout: 1e4
    })).page();
    if (!o) throw new Error("Chrome ch\u01B0a tr\u1EA3 tab m\u1EDBi.");
    if (t) try {
      let {
        windowId: l,
        bounds: s
      } = await a.send("Browser.getWindowForTarget", {
        targetId: n
      });
      s.windowState !== "minimized" && (await a.send("Browser.setWindowBounds", {
        windowId: l,
        bounds: {
          windowState: "minimized"
        }
      }));
    } catch (l) {
      if (!e.isConnected() || o.isClosed()) throw l;
      Hx.warn("Kh\xF4ng thu nh\u1ECF \u0111\u01B0\u1EE3c c\u1EEDa s\u1ED5 Veo 3 qua CDP; s\u1EBD d\xF9ng b\u01B0\u1EDBc \u1EA9n c\u1EEDa s\u1ED5 c\u1EE7a h\u1EC7 \u0111i\u1EC1u h\xE0nh.");
    }
    return o;
  } catch (t) {
    throw n && (await a?.send("Target.closeTarget", {
      targetId: n
    }).catch(() => {})), new Error("Kh\xF4ng th\u1EC3 chu\u1EA9n b\u1ECB tab n\u1EC1n Veo 3. Vui l\xF2ng th\u1EED l\u1EA1i.", {
      cause: t
    });
  } finally {
    await a?.detach().catch(() => {});
  }
}
async function sn(e, a = 5e3) {
  let n = Date.now();
  for (; Date.now() - n < a;) {
    if (!(await _a(e))) return !0;
    await new Promise(t => setTimeout(t, 150));
  }
  return !1;
}
function qx(e) {
  return e.exitCode !== null || e.signalCode !== null;
}
async function zo(e, a) {
  return qx(e) ? !0 : await new Promise(n => {
    let t = o => {
        clearTimeout(i), e.off("exit", r), n(o);
      },
      r = () => t(!0),
      i = setTimeout(() => t(!1), a);
    e.once("exit", r);
  });
}
async function Un(e, a) {
  return !e || qx(e) || (await zo(e, 3e3)) || (await sn(a, 1e3)) && (await zo(e, 1500)) || (e.kill("SIGTERM"), await zo(e, 1500)) ? !0 : (e.kill("SIGKILL"), await zo(e, 500));
}
export { Kx, Pu, Un, Uo, Vn, Wx, _a, jo, sn };
