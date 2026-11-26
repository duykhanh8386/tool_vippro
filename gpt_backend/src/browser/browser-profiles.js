import y0 from "node:fs";
import Of from "node:path";
import Mm from "node:crypto";
import w0 from "puppeteer-core";
import { he } from "../config/paths.js";
import { Vn } from "./chrome-launcher.js";
var sr = class extends Error {
    constructor(a) {
      super(`GPT background task ${a}.`), this.kind = a;
    }
    kind;
  },
  lr = new Map();
function _f(e) {
  let a = new AbortController(),
    n = m => {
      try {
        e.onError(m);
      } catch {}
    },
    t,
    r = new Promise((m, c) => {
      t = c;
    }),
    i = () => t(a.signal.reason);
  a.signal.addEventListener("abort", i, {
    once: !0
  });
  let o = setTimeout(() => a.abort(new sr("timeout")), e.timeoutMs ?? 1e4);
  o.unref();
  let l = new Promise(m => setImmediate(m)).then(() => (a.signal.throwIfAborted(), e.run())),
    s = lr.get(e.accountId) ?? new Set();
  lr.set(e.accountId, s);
  let u = {
    stop: () => a.abort(new sr("cancelled")),
    done: Promise.race([l, r]).catch(n).finally(async () => {
      clearTimeout(o), a.signal.removeEventListener("abort", i), await e.release().catch(n);
    }).finally(() => {
      s.delete(u), !s.size && lr.get(e.accountId) === s && lr.delete(e.accountId);
    })
  };
  s.add(u);
}
async function Nl(e) {
  let a = e === void 0 ? [...lr.values()].flatMap(n => [...n]) : [...(lr.get(e) ?? [])];
  a.forEach(n => n.stop()), await Promise.all(a.map(n => n.done));
}
var Ha = class extends Error {
    constructor(a) {
      super(`ChatGPT bootstrap failed (HTTP ${a}).`), this.status = a;
    }
    status;
  },
  pn = class extends Error {
    constructor(a) {
      super(`ChatGPT API transport failed (${a}).`), this.kind = a;
    }
    kind;
  };
function Vf(e) {
  let a = e instanceof Error ? e.message : "";
  return /timeout|timed out|abort/i.test(a) ? "timeout" : /execution context|frame detached|target closed|session closed/i.test(a) ? "context" : /failed to fetch|networkerror|net::|err_/i.test(a) ? "network" : "unknown";
}
var Rm = new WeakMap(),
  Ka = new Map();
function b0(e, a) {
  let n = Of.join(a.profileRoot ?? Of.join(he, "gpt", "browser-profiles"), e);
  return y0.mkdirSync(n, {
    recursive: !0,
    mode: 448
  }), (a.launch ?? w0.launch)({
    executablePath: Vn(),
    headless: !0,
    userDataDir: n,
    args: ["--no-first-run", "--no-default-browser-check", "--disable-blink-features=AutomationControlled"]
  });
}
async function v0(e, a) {
  for (;;) {
    let n = Ka.get(e);
    if (n?.closing) {
      await n.closing;
      continue;
    }
    n || (n = {
      browser: b0(e, a),
      activeContexts: 0
    }, Ka.set(e, n), n.browser.then(t => {
      t.once("disconnected", () => {
        Ka.get(e) === n && Ka.delete(e);
      });
    }).catch(() => {})), n.activeContexts += 1;
    try {
      let t = await n.browser;
      if (Ka.get(e) !== n || n.closing) {
        await Nm(e, n);
        continue;
      }
      return {
        browser: t,
        release: () => Nm(e, n),
        canDefer: () => Ka.get(e) === n && !n.closing
      };
    } catch (t) {
      throw await Nm(e, n), t;
    }
  }
}
async function Nm(e, a) {
  if (a.activeContexts = Math.max(0, a.activeContexts - 1), a.activeContexts || a.closing) return a.closing;
  a.closing = a.browser.then(n => n.close()).catch(() => {}).then(() => {
    Ka.get(e) === a && Ka.delete(e);
  }), await a.closing;
}
async function Uf() {
  let e = [...Ka.entries()];
  Ka.clear(), await Nl(), await Promise.all(e.map(async ([, a]) => {
    a.closing ??= a.browser.then(n => n.close()).catch(() => {}), await a.closing;
  }));
}
async function C0(e) {
  await e.close().catch(() => {});
}
async function Ml(e, a, n = {}) {
  n.signal?.throwIfAborted();
  let t = await v0(e, n),
    r,
    i,
    o = !1,
    l,
    s = () => (i ??= r ? C0(r) : Promise.resolve(), i),
    u = () => {
      s();
    },
    m = () => (l ??= s().then(() => t.release()), l);
  try {
    n.signal?.throwIfAborted(), r = await t.browser.createBrowserContext(), n.signal?.addEventListener("abort", u, {
      once: !0
    }), n.signal?.throwIfAborted();
    let c = await r.newPage();
    Rm.set(c, {
      deviceId: Mm.randomUUID(),
      sessionId: Mm.randomUUID()
    });
    let d = await t.browser.userAgent();
    d.includes("HeadlessChrome") && (await c.setUserAgent(d.replace("HeadlessChrome", "Chrome")));
    let x = await c.goto("https://chatgpt.com/", {
      waitUntil: "domcontentloaded",
      timeout: 45e3
    });
    if (!x || x.status() < 200 || x.status() >= 300) throw new Ha(x?.status() ?? 0);
    if (new URL(c.url()).origin !== "https://chatgpt.com") throw new Ha(401);
    let B = await a(c, await x.text());
    if (n.afterSuccess && t.canDefer()) {
      let f = n.afterSuccess;
      n.signal?.removeEventListener("abort", u), _f({
        accountId: e,
        run: () => f.run(c, B),
        release: m,
        onError: f.onError,
        timeoutMs: f.timeoutMs
      }), o = !0;
    }
    return B;
  } finally {
    n.signal?.removeEventListener("abort", u), o || (await m());
  }
}
async function wa(e, a, n, t = {}) {
  if (!n.startsWith("/backend-api/")) throw new Error("\u0110\u01B0\u1EDDng d\u1EABn ChatGPT kh\xF4ng h\u1EE3p l\u1EC7.");
  if (new URL(e.url()).origin !== "https://chatgpt.com") throw new Ha(401);
  let r = Rm.get(e),
    i = n.split("?")[0];
  try {
    return await e.evaluate(async ({
      token: o,
      pathname: l,
      targetPath: s,
      method: u,
      body: m,
      headers: c,
      session: d,
      timeoutMs: x
    }) => {
      let B = await fetch(l, {
        method: u,
        headers: {
          Authorization: `Bearer ${o}`,
          Accept: "application/json",
          "X-OpenAI-Target-Path": s,
          "X-OpenAI-Target-Route": s,
          "OAI-Client-Version": "prod-be885abbfcfe7b1f511e88b3003d9ee44757fbad",
          "OAI-Client-Build-Number": "5955942",
          "OAI-Language": "zh-CN",
          "Cache-Control": "no-cache",
          Pragma: "no-cache",
          ...(d ? {
            "OAI-Device-Id": d.deviceId,
            "OAI-Session-Id": d.sessionId
          } : {}),
          ...(m === void 0 ? {} : {
            "Content-Type": "application/json"
          }),
          ...c
        },
        body: m === void 0 ? void 0 : JSON.stringify(m),
        credentials: "include",
        signal: AbortSignal.timeout(x)
      });
      return {
        status: B.status,
        contentType: B.headers.get("content-type")?.split(";", 1)[0]?.toLowerCase(),
        body: (await B.text()).slice(0, 1e6)
      };
    }, {
      token: a,
      pathname: n,
      targetPath: i,
      method: t.method ?? "GET",
      body: t.body,
      headers: t.headers ?? {},
      session: r,
      timeoutMs: t.timeoutMs ?? 45e3
    });
  } catch (o) {
    throw new pn(Vf(o));
  }
}
async function jf(e, a, n, t, r, i) {
  if (!n.startsWith("/backend-api/") || new URL(e.url()).origin !== "https://chatgpt.com") throw new Ha(401);
  let o = `gptStream_${Mm.randomUUID().replaceAll("-", "")}`;
  await e.exposeFunction(o, i);
  let l = Rm.get(e);
  try {
    return await e.evaluate(async ({
      token: s,
      pathname: u,
      body: m,
      headers: c,
      session: d,
      callbackName: x
    }) => {
      let B = await fetch(u, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${s}`,
          Accept: "text/event-stream",
          "Content-Type": "application/json",
          "X-OpenAI-Target-Path": u,
          "X-OpenAI-Target-Route": u,
          "OAI-Client-Version": "prod-be885abbfcfe7b1f511e88b3003d9ee44757fbad",
          "OAI-Client-Build-Number": "5955942",
          "OAI-Language": "zh-CN",
          ...(d ? {
            "OAI-Device-Id": d.deviceId,
            "OAI-Session-Id": d.sessionId
          } : {}),
          ...c
        },
        body: JSON.stringify(m),
        credentials: "include"
      });
      if (!B.ok) return B.status;
      let f = B.body?.getReader();
      if (!f) return 502;
      let h = window[x],
        E = new TextDecoder(),
        p = "";
      for (;;) {
        let g = await f.read();
        p += E.decode(g.value, {
          stream: !g.done
        });
        let y = p.split(/\r?\n\r?\n/);
        p = y.pop() ?? "";
        for (let A of y) {
          let S = A.split(/\r?\n/).filter(w => w.startsWith("data:")).map(w => w.slice(5).trimStart()).join(`
`);
          S && (await h(S));
        }
        if (g.done) break;
      }
      return B.status;
    }, {
      token: a,
      pathname: n,
      body: t,
      headers: r,
      session: l,
      callbackName: o
    });
  } catch (s) {
    throw new pn(Vf(s));
  } finally {
    await e.removeExposedFunction(o).catch(() => {});
  }
}
export { Ha, Ml, Nl, Uf, jf, pn, sr, wa };
