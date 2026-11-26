import { isDeepStrictEqual as L0 } from "node:util";
import s7 from "node:crypto";
import { D } from "../logging/logger.js";
import { Ha, Ml, pn, wa } from "../browser/browser-profiles.js";
import { Be } from "./gpt-account-store.js";
import { a7, i7, r7, vt } from "./sentinel-pow.js";
var _0 = {
  "window.Math": "[object Math]",
  "window.Reflect": "[object Reflect]",
  "window.performance": "[object Performance]",
  "window.localStorage": "[object Storage]",
  "window.Object": "function Object() { [native code] }",
  "window.Reflect.set": "function set() { [native code] }",
  "window.performance.now": "function () { [native code] }",
  "window.Object.create": "function create() { [native code] }",
  "window.Object.keys": "function keys() { [native code] }",
  "window.Math.random": "function random() { [native code] }"
};
function Wa(e) {
  return e == null ? "undefined" : typeof e == "number" ? Number.isInteger(e) ? e.toFixed(1) : String(e) : typeof e == "string" ? _0[e] ?? e : Array.isArray(e) && e.every(a => typeof a == "string") ? e.join(",") : String(e);
}
function o7(e, a) {
  if (!a) return e;
  let n = Array.from(a, r => r.codePointAt(0) ?? 0),
    t = 0;
  return Array.from(e, r => {
    let i = String.fromCodePoint((r.codePointAt(0) ?? 0) ^ n[t % n.length]);
    return t += Buffer.byteLength(r), i;
  }).join("");
}
function Lm(e) {
  let a = Number.parseInt(Wa(e), 10);
  return Number.isNaN(a) ? 0 : a;
}
function l7(e, a = "") {
  let n;
  try {
    n = JSON.parse(o7(Buffer.from(e, "base64").toString("utf8"), a));
  } catch {
    return "";
  }
  if (!Array.isArray(n) || !n.every(Array.isArray)) return "";
  let t = new Map(),
    r = performance.now(),
    i = "",
    o = m => t.get(Lm(m)),
    l = (m, c) => t.set(Lm(m), c),
    s = (m, c) => {
      typeof m == "function" && m(...c);
    },
    u = (m, c) => t.set(m, c);
  u(1, (m, c) => l(m, o7(Wa(o(m)), Wa(o(c))))), u(2, (m, c) => l(m, c)), u(3, m => {
    i = Buffer.from(Wa(m)).toString("base64");
  }), u(5, (m, c) => {
    let d = o(m),
      x = o(c);
    Array.isArray(d) ? l(m, [...d, x]) : typeof d == "string" || typeof d == "number" || typeof x == "string" || typeof x == "number" ? l(m, Wa(d) + Wa(x)) : l(m, "NaN");
  }), u(6, (m, c, d) => {
    let x = o(c),
      B = o(d);
    if (typeof x != "string" || typeof B != "string") return;
    let f = `${x}.${B}`;
    l(m, f === "window.document.location" ? "https://chatgpt.com/" : f);
  }), u(7, (m, ...c) => {
    let d = o(m),
      x = c.map(o);
    if (d === "window.Reflect.set" && x[0] instanceof Map) {
      x[0].set(Wa(x[1]), x[2]);
      return;
    }
    s(d, x);
  }), u(8, (m, c) => l(m, o(c))), t.set(9, n), t.set(10, "window"), u(14, (m, c) => {
    try {
      l(m, JSON.parse(Wa(o(c))));
    } catch {}
  }), u(15, (m, c) => l(m, JSON.stringify(o(c), (d, x) => x instanceof Map ? Object.fromEntries(x) : x))), t.set(16, a), u(17, (m, c, ...d) => {
    let x = o(c),
      B = d.map(o);
    x === "window.performance.now" ? l(m, performance.now() - r + Math.random() / 1e6) : x === "window.Object.create" ? l(m, new Map()) : x === "window.Object.keys" && B[0] === "window.localStorage" ? l(m, ["STATSIG_LOCAL_STORAGE_INTERNAL_STORE_V4", "STATSIG_LOCAL_STORAGE_STABLE_ID", "client-correlated-secret", "oai/apps/capExpiresAt", "oai-did", "STATSIG_LOCAL_STORAGE_LOGGING_REQUEST", "UiState.isNavigationCollapsed.1"]) : x === "window.Math.random" ? l(m, Math.random()) : s(x, B);
  }), u(18, m => {
    try {
      l(m, Buffer.from(Wa(o(m)), "base64").toString("utf8"));
    } catch {}
  }), u(19, m => l(m, Buffer.from(Wa(o(m))).toString("base64"))), u(20, (m, c, d, ...x) => {
    L0(o(m), o(c)) && s(o(d), x.map(o));
  }), u(21, () => {}), u(23, (m, c, ...d) => {
    o(m) != null && s(o(c), d);
  }), u(24, (m, c, d) => {
    let x = o(c),
      B = o(d);
    typeof x == "string" && typeof B == "string" && l(m, `${x}.${B}`);
  });
  try {
    for (let m of n) m.length > 0 && s(t.get(Lm(m[0])), m.slice(1));
  } catch {
    return "";
  }
  return i;
}
var Tl = D("GPT Image"),
  be = class extends Error {
    constructor(a, n) {
      super(n), this.code = a;
    }
    code;
  };
function Ll(e) {
  try {
    let a = JSON.parse(e);
    if (a && typeof a == "object" && !Array.isArray(a)) return a;
  } catch {}
  throw new be("challenge_error", "ChatGPT tr\u1EA3 v\u1EC1 challenge ho\u1EB7c d\u1EEF li\u1EC7u kh\xF4ng h\u1EE3p l\u1EC7.");
}
function u7(e) {
  return e === 401 ? new be("auth_error", "Access token ChatGPT \u0111\xE3 h\u1EBFt h\u1EA1n ho\u1EB7c kh\xF4ng h\u1EE3p l\u1EC7.") : e === 400 || e === 403 || e === 429 ? new be("challenge_error", `ChatGPT t\u1EEB ch\u1ED1i ki\u1EC3m tra (HTTP ${e}).`) : new be("network_error", `ChatGPT kh\xF4ng ph\u1EA3n h\u1ED3i nh\u01B0 mong \u0111\u1EE3i (HTTP ${e}).`);
}
function _l(e) {
  if (e < 200 || e >= 300) throw u7(e);
}
function qa(e, a) {
  return typeof e[a] == "string" ? e[a] : void 0;
}
function _m(e, a) {
  let n = e[a];
  return n && typeof n == "object" && !Array.isArray(n) ? n : {};
}
function O0(e) {
  if (!Array.isArray(e)) return;
  let n = e.find(r => r && typeof r == "object" && !Array.isArray(r) && r.feature_name === "image_gen")?.remaining,
    t = typeof n == "number" ? n : typeof n == "string" && /^\d+$/.test(n.trim()) ? Number(n) : NaN;
  return Number.isSafeInteger(t) && t >= 0 ? t : void 0;
}
async function Om(e, a, n, t = () => {}) {
  t("read browser fingerprint");
  let r = await e.evaluate(() => navigator.userAgent);
  t("parse bootstrap proof resources");
  let i = a7(n);
  t("generate legacy requirements proof"), Tl.info("[GPT Image] Chat requirements proof inputs", {
    scriptCount: i.scripts.length,
    hasDataBuild: i.dataBuild.length > 0,
    userAgentAvailable: r.length > 0
  });
  let o = r7(r, i);
  Tl.info("[GPT Image] Chat requirements proof generated", {
    proofLength: o.length
  }), t("send chat requirements request");
  let l = await wa(e, a, "/backend-api/sentinel/chat-requirements", {
    method: "POST",
    body: {
      p: o
    }
  });
  Tl.info("[GPT Image] Chat requirements response", {
    status: l.status,
    contentType: l.contentType ?? "unknown",
    responseBytes: Buffer.byteLength(l.body)
  }), t("validate chat requirements response"), _l(l.status);
  let s = Ll(l.body),
    u = qa(s, "token");
  if (!u) throw new be("challenge_error", "ChatGPT kh\xF4ng c\u1EA5p chat requirements token.");
  if (_m(s, "arkose").required === !0) throw new be("challenge_error", "ChatGPT y\xEAu c\u1EA7u Arkose, ch\u01B0a th\u1EC3 chu\u1EA9n b\u1ECB t\u1EA1o \u1EA3nh.");
  let m = _m(s, "proofofwork"),
    c = _m(s, "turnstile"),
    d;
  if (m.required === !0) {
    t("solve chat requirements challenge");
    let B = qa(m, "seed"),
      f = qa(m, "difficulty");
    if (!B || !f) throw new be("challenge_error", "Thi\u1EBFu d\u1EEF li\u1EC7u proof-of-work.");
    try {
      d = i7(B, f, r, i);
    } catch {
      throw new be("challenge_error", "Kh\xF4ng gi\u1EA3i \u0111\u01B0\u1EE3c proof-of-work c\u1EE7a ChatGPT.");
    }
  }
  let x;
  if (c.required === !0) {
    let B = qa(c, "dx");
    x = B ? l7(B) : void 0;
  }
  return {
    token: u,
    proofToken: d,
    turnstileToken: x,
    soToken: qa(s, "so_token")
  };
}
function Vm(e) {
  let a = {
    "OpenAI-Sentinel-Chat-Requirements-Token": e.token
  };
  return e.proofToken && (a["OpenAI-Sentinel-Proof-Token"] = e.proofToken), e.turnstileToken && (a["OpenAI-Sentinel-Turnstile-Token"] = e.turnstileToken), e.soToken && (a["OpenAI-Sentinel-SO-Token"] = e.soToken), a;
}
async function V0(e, a, n) {
  let t = Vm(n),
    r = await wa(e, a, "/backend-api/f/conversation/prepare", {
      method: "POST",
      headers: {
        ...t,
        Accept: "*/*"
      },
      body: {
        action: "next",
        fork_from_shared_post: !1,
        parent_message_id: s7.randomUUID(),
        model: "gpt-5-5",
        client_prepare_state: "success",
        timezone_offset_min: -480,
        timezone: "Asia/Shanghai",
        conversation_mode: {
          kind: "primary_assistant"
        },
        system_hints: ["picture_v2"],
        partial_query: {
          id: s7.randomUUID(),
          author: {
            role: "user"
          },
          content: {
            content_type: "text",
            parts: ["Ki\u1EC3m tra kh\u1EA3 n\u0103ng chu\u1EA9n b\u1ECB t\u1EA1o \u1EA3nh."]
          }
        },
        supports_buffering: !0,
        supported_encodings: ["v1"],
        client_contextual_info: {
          app_name: "chatgpt.com"
        }
      }
    });
  Tl.info("[GPT Image] Account prepare response", {
    status: r.status,
    contentType: r.contentType ?? "unknown",
    responseBytes: Buffer.byteLength(r.body)
  }), _l(r.status), Ll(r.body);
}
async function m7(e, a) {
  let n = Be.getToken(e),
    t = "browser";
  try {
    return await Ml(e, async (r, i) => {
      t = "profile";
      let o = await wa(r, n, "/backend-api/me");
      _l(o.status);
      let l = Ll(o.body);
      if (!a) {
        t = "init";
        let u = await wa(r, n, "/backend-api/conversation/init", {
          method: "POST",
          body: {
            gizmo_id: null,
            requested_default_model: null,
            conversation_id: null,
            timezone_offset_min: -480
          }
        });
        _l(u.status);
        let m = Ll(u.body);
        return {
          email: qa(l, "email"),
          plan: qa(l, "plan_type") ?? qa(m, "plan_type"),
          reportedImageRemaining: O0(m.limits_progress),
          prepareReady: !1
        };
      }
      t = "requirements";
      let s = await Om(r, n, i);
      return t = "prepare", await V0(r, n, s), {
        email: qa(l, "email"),
        plan: qa(l, "plan_type"),
        prepareReady: !0
      };
    });
  } catch (r) {
    if (r instanceof be) throw r;
    if (r instanceof Ha) throw u7(r.status);
    if (r instanceof pn) {
      let o = {
        timeout: "h\u1EBFt th\u1EDDi gian ch\u1EDD",
        network: "Chromium kh\xF4ng g\u1EEDi \u0111\u01B0\u1EE3c y\xEAu c\u1EA7u",
        context: "trang ChatGPT \u0111\xE3 t\u1EA3i l\u1EA1i ho\u1EB7c \u0111\xF3ng",
        unknown: "l\u1ED7i khi th\u1EF1c thi y\xEAu c\u1EA7u trong Chromium"
      }[r.kind];
      throw new be("network_error", `Kh\xF4ng ho\xE0n t\u1EA5t b\u01B0\u1EDBc ${t}: ${o}.`);
    }
    if (r instanceof Error && r.message === "Chrome not found. Install Google Chrome or Chromium.") throw new be("network_error", "Kh\xF4ng t\xECm th\u1EA5y Chrome ho\u1EB7c Chromium tr\xEAn m\xE1y.");
    let i = {
      browser: "Chromium kh\xF4ng m\u1EDF \u0111\u01B0\u1EE3c trang ChatGPT. Ki\u1EC3m tra k\u1EBFt n\u1ED1i m\u1EA1ng v\xE0 th\u1EED l\u1EA1i.",
      profile: "Chromium kh\xF4ng g\u1ECDi \u0111\u01B0\u1EE3c API h\u1ED3 s\u01A1 ChatGPT.",
      init: "Kh\xF4ng l\xE0m m\u1EDBi \u0111\u01B0\u1EE3c th\xF4ng tin t\xE0i kho\u1EA3n ChatGPT.",
      requirements: "Kh\xF4ng ho\xE0n t\u1EA5t \u0111\u01B0\u1EE3c b\u01B0\u1EDBc chat requirements c\u1EE7a ChatGPT.",
      prepare: "Kh\xF4ng ho\xE0n t\u1EA5t \u0111\u01B0\u1EE3c b\u01B0\u1EDBc chu\u1EA9n b\u1ECB t\u1EA1o \u1EA3nh c\u1EE7a ChatGPT."
    };
    throw new be("network_error", i[t]);
  }
}
function c7(e) {
  return m7(e, !1);
}
function d7(e) {
  return m7(e, !0);
}
var Fi = class extends Error {
  operation;
  status;
  constructor(a, n) {
    super(`${a} th\u1EA5t b\u1EA1i (HTTP ${n}).`), this.operation = a, this.status = n;
  }
};
function Ya(e, a) {
  if (e < 200 || e >= 300) throw new Fi(a, e);
}
function Ol(e) {
  if (e instanceof Error && /Chrome not found/.test(e.message)) return "chrome_missing";
  return e instanceof be ? e.code === "auth_error" ? "account_auth" : e.code === "challenge_error" ? "account_challenge" : "network" : e instanceof Fi ? U0(e.status, e.operation) : e instanceof pn || e instanceof TypeError ? "network" : e instanceof Error ? /từ chối nội dung/i.test(e.message) ? "prompt_rejected" : /đạt giới hạn tạo ảnh/i.test(e.message) ? "rate_limited" : /hết thời gian chờ/i.test(e.message) ? "timeout" : /ảnh tham chiếu|upload ảnh/i.test(e.message) ? "reference_image" : /không phải file ảnh|chưa trả file ảnh|không trả ảnh/i.test(e.message) ? "invalid_output" : "unknown" : "unknown";
}
function U0(e, a = "") {
  return e === 401 || e === 403 ? "app_access" : (e === 413 || e === 415) && /ảnh tham chiếu|tham chiếu/i.test(a) ? "reference_image" : e === 429 ? "rate_limited" : e >= 500 ? "upstream_unavailable" : "unknown";
}
function Um(e) {
  let a = e.normalize("NFKC").replace(/[’‘]/g, "'").replace(/\s+/g, " ").toLowerCase(),
    n = /\b(?:may|might|could) violate\b.{0,120}\b(?:guardrails?|content policies?|safety policies|policies)\b/.test(a) || /\b(?:content|safety) polic(?:y|ies)\b.{0,100}\b(?:violation|violat\w*|block\w*|restrict\w*)\b/.test(a) || /\bguardrails?\b.{0,100}\b(?:violation|violat\w*|block\w*|restrict\w*)\b/.test(a) || /\b(?:can't|cannot|unable to) (?:create|generate) (?:this|the) image\b.{0,100}\b(?:policy|policies|guardrails?|safety)\b/.test(a),
    t = /\b(?:insufficient_quota|limit reached|usage limit|image generation limit|you've reached|you have reached)\b/.test(a) || /限流|额度已用尽|生成上限|已达上限/.test(a),
    r = n ? "ChatGPT t\u1EEB ch\u1ED1i n\u1ED9i dung t\u1EA1o \u1EA3nh." : t ? "ChatGPT \u0111\xE3 \u0111\u1EA1t gi\u1EDBi h\u1EA1n t\u1EA1o \u1EA3nh." : "ChatGPT ch\u01B0a tr\u1EA3 file \u1EA3nh.";
  return new Error(r);
}
function jm(e) {
  return e instanceof Fi ? {
    kind: "upstream_http",
    operation: e.operation,
    status: e.status
  } : e instanceof be ? {
    kind: "connection",
    code: e.code
  } : e instanceof vt ? {
    kind: "proof_generation",
    proofPhase: e.phase,
    causeName: e.causeName,
    ...(e.causeCode ? {
      causeCode: e.causeCode
    } : {})
  } : e instanceof Ha ? {
    kind: "bootstrap_http",
    status: e.status
  } : e instanceof pn ? {
    kind: "chromium_transport",
    transport: e.kind
  } : e instanceof Error && "code" in e && typeof e.code == "string" && /^(E[A-Z]+|ERR_[A-Z0-9_]+)$/.test(e.code) ? {
    kind: "runtime",
    code: e.code
  } : {
    kind: e instanceof Error ? e.name : "unknown"
  };
}
export { Ol, Om, Um, Vm, Ya, be, c7, d7, jm };
