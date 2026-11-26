import W0 from "node:crypto";
import q0 from "node:fs/promises";
import { setTimeout as Hm } from "node:timers/promises";
import { D } from "../logging/logger.js";
import { jf, wa } from "../browser/browser-profiles.js";
import { Om, Um, Vm, Ya } from "./browser-env-spoof.js";
import { E7, g7, p7, v7, w7, y7 } from "./prompt-composition.js";
function zl(e) {
  return {
    ...e
  };
}
function ka(e, a) {
  Object.assign(e, a, {
    updatedAt: new Date().toISOString()
  });
}
var Pi = D("GPT Image");
function Jl(e) {
  try {
    let a = JSON.parse(e);
    if (a && typeof a == "object" && !Array.isArray(a)) return a;
  } catch {}
  throw new Error("ChatGPT tr\u1EA3 v\u1EC1 d\u1EEF li\u1EC7u kh\xF4ng h\u1EE3p l\u1EC7.");
}
function Y0(e) {
  let a = Buffer.byteLength(e);
  try {
    let n = JSON.parse(e);
    if (!n || typeof n != "object" || Array.isArray(n)) return {
      responseBytes: a,
      jsonObject: !1,
      hasConduitToken: !1,
      hasErrorField: !1
    };
    let t = n;
    return {
      responseBytes: a,
      jsonObject: !0,
      hasConduitToken: typeof t.conduit_token == "string" && !!t.conduit_token.trim(),
      hasErrorField: Object.hasOwn(t, "error")
    };
  } catch {
    return {
      responseBytes: a,
      jsonObject: !1,
      hasConduitToken: !1,
      hasErrorField: !1
    };
  }
}
async function Z0(e, a, n, t) {
  t.throwIfAborted();
  let r = await wa(e, a, "/backend-api/files", {
    method: "POST",
    body: {
      file_name: n.name,
      file_size: n.size,
      use_case: "multimodal",
      width: n.width,
      height: n.height
    }
  });
  Ya(r.status, "Chu\u1EA9n b\u1ECB t\u1EA3i \u1EA3nh tham chi\u1EBFu");
  let i = Jl(r.body);
  if (typeof i.upload_url != "string" || typeof i.file_id != "string" || !/^[\w-]+$/.test(i.file_id)) throw new Error("ChatGPT kh\xF4ng tr\u1EA3 th\xF4ng tin upload \u1EA3nh.");
  let o = new URL(i.upload_url);
  if (o.protocol !== "https:" || !/^[a-z0-9.-]+\.(blob\.core\.windows\.net|oaiusercontent\.com)$/i.test(o.hostname)) throw new Error("URL upload \u1EA3nh ChatGPT kh\xF4ng h\u1EE3p l\u1EC7.");
  let l = await e.evaluate(() => navigator.userAgent),
    s = await fetch(o, {
      method: "PUT",
      signal: t,
      body: await q0.readFile(n.path),
      headers: {
        "Content-Type": n.mime,
        "x-ms-blob-type": "BlockBlob",
        "x-ms-version": "2020-04-08",
        Origin: "https://chatgpt.com",
        Referer: "https://chatgpt.com/",
        "User-Agent": l,
        Accept: "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7"
      }
    });
  Ya(s.status, "T\u1EA3i \u1EA3nh tham chi\u1EBFu"), await Hm(500, void 0, {
    signal: t
  });
  let u = await wa(e, a, `/backend-api/files/${encodeURIComponent(i.file_id)}/uploaded`, {
    method: "POST",
    body: {}
  });
  return Ya(u.status, "Ho\xE0n t\u1EA5t \u1EA3nh tham chi\u1EBFu"), {
    fileId: i.file_id,
    name: n.name,
    mime: n.mime,
    size: n.size,
    width: n.width,
    height: n.height
  };
}
function Wm(e) {
  return {
    candidates: e.length,
    fileService: e.filter(a => a.scheme === "file-service").length,
    sediment: e.filter(a => a.scheme === "sediment").length
  };
}
async function X0(e, a, n, t = {}) {
  if (!e.conversationId) throw new Error("ChatGPT k\u1EBFt th\xFAc stream m\xE0 kh\xF4ng tr\u1EA3 conversation ID.");
  let r = t.now ?? Date.now,
    i = t.wait ?? ((l, s) => Hm(l, void 0, {
      signal: s
    })),
    o = r() + (t.timeoutMs ?? 5 * 6e4);
  for (; r() < o;) {
    a.throwIfAborted();
    let l = await n();
    if (l.status !== 429) {
      Ya(l.status, "Theo d\xF5i k\u1EBFt qu\u1EA3 ChatGPT");
      let s = w7(Jl(l.body));
      for (let u of s.images) e.generatedImages.some(m => m.id === u.id && m.scheme === u.scheme) || e.generatedImages.push(u);
      if (s.images.length) {
        Pi.info("[GPT Image] Generated image candidates found while polling", {
          source: "poll",
          ...Wm(s.images),
          selectedScheme: s.images[0]?.scheme
        });
        return;
      }
      if (s.text) throw Um(s.text);
    }
    await i(t.intervalMs ?? 4e3, a);
  }
  throw new Error("H\u1EBFt th\u1EDDi gian ch\u1EDD \u1EA3nh t\u1EEB ChatGPT.");
}
function Q0(e, a, n, t) {
  return X0(n, t, () => wa(e, a, `/backend-api/conversation/${encodeURIComponent(n.conversationId)}`));
}
async function I7(e, a, n, t, r, i, o, l) {
  l("request chat requirements");
  let s = await Om(e, n, a, l),
    u = Vm(s),
    m = [];
  for (let B of t.images ?? []) l("upload reference image"), m.push(await Z0(e, n, B, o));
  l("request conversation prepare"), Pi.info("[GPT Image] Sending prepare request", {
    jobId: i.id,
    model: t.model
  });
  let c = await wa(e, n, "/backend-api/f/conversation/prepare", {
    method: "POST",
    body: E7(t),
    headers: {
      ...u,
      Accept: "*/*"
    }
  });
  Pi.info("[GPT Image] Prepare response", {
    jobId: i.id,
    model: t.model,
    status: c.status,
    contentType: c.contentType ?? "unknown",
    ...Y0(c.body)
  }), Ya(c.status, "Chu\u1EA9n b\u1ECB t\u1EA1o \u1EA3nh");
  let d = g7(Jl(c.body).conduit_token);
  l("start image conversation"), ka(i, {
    stage: "streaming"
  });
  let x = await jf(e, n, "/backend-api/f/conversation", p7(t, m), {
    ...u,
    ...d,
    "X-Oai-Turn-Trace-Id": W0.randomUUID()
  }, B => y7(r, B));
  if (Ya(x, "T\u1EA1o \u1EA3nh ChatGPT"), r.error) throw new Error(r.error);
  if (r.blocked) throw new Error("ChatGPT t\u1EEB ch\u1ED1i n\u1ED9i dung t\u1EA1o \u1EA3nh.");
  if (Pi.info("[GPT Image] Stream generated image candidates", {
    source: "stream",
    ...Wm(r.generatedImages)
  }), !r.generatedImages.length) {
    let B = v7(r);
    if (B) throw Um(B);
    l("poll image conversation"), ka(i, {
      stage: "polling"
    }), await Q0(e, n, r, o);
  }
  if (!r.generatedImages.length) throw new Error("ChatGPT ch\u01B0a tr\u1EA3 file \u1EA3nh.");
}
async function D7(e, a, n, t) {
  let r = n.generatedImages[0];
  if (!r || !n.conversationId) throw new Error("Thi\u1EBFu \u0111\u1ECBnh danh \u1EA3nh ChatGPT.");
  Pi.info("[GPT Image] Downloading generated image candidate", {
    source: r.source,
    scheme: r.scheme,
    ...Wm(n.generatedImages)
  });
  let i = await e.evaluate(() => navigator.userAgent),
    o;
  for (let l = 0; l < 3; l += 1) {
    t.throwIfAborted();
    try {
      let s = `conversation_id=${encodeURIComponent(n.conversationId)}&inline=false`,
        u = await wa(e, a, `/backend-api/files/download/${encodeURIComponent(r.id)}?${s}`);
      Ya(u.status, "L\u1EA5y URL \u1EA3nh");
      let m = Jl(u.body),
        c = m.download_url ?? m.url;
      if (typeof c != "string") throw new Error("ChatGPT kh\xF4ng tr\u1EA3 URL \u1EA3nh.");
      let d = new URL(c, "https://chatgpt.com");
      if (d.protocol !== "https:" || !/^(chatgpt\.com|[a-z0-9.-]+\.(oaiusercontent\.com|blob\.core\.windows\.net))$/i.test(d.hostname)) throw new Error("URL \u1EA3nh ChatGPT kh\xF4ng h\u1EE3p l\u1EC7.");
      let x = d.hostname === "chatgpt.com" && /^\/backend-(api|anon)\//.test(d.pathname),
        B = await fetch(d, {
          signal: t,
          headers: x ? {
            Authorization: `Bearer ${a}`,
            "User-Agent": i,
            Origin: "https://chatgpt.com",
            Referer: "https://chatgpt.com/",
            Accept: "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "X-OpenAI-Target-Path": d.pathname,
            "X-OpenAI-Target-Route": d.pathname
          } : {
            "User-Agent": i
          }
        });
      if (Ya(B.status, x ? "T\u1EA3i \u1EA3nh t\u1EEB ChatGPT" : "T\u1EA3i \u1EA3nh t\u1EEB CDN"), Number(B.headers.get("content-length")) > 3e7) throw new Error("\u1EA2nh ChatGPT v\u01B0\u1EE3t gi\u1EDBi h\u1EA1n 30 MB.");
      let h = Buffer.from(await B.arrayBuffer());
      if (h.length > 3e7) throw new Error("\u1EA2nh ChatGPT v\u01B0\u1EE3t gi\u1EDBi h\u1EA1n 30 MB.");
      return h;
    } catch (s) {
      o = s, l < 2 && (await Hm(750, void 0, {
        signal: t
      }));
    }
  }
  throw o;
}
async function k7(e, a, n, t = wa) {
  let r = await t(e, a, `/backend-api/conversation/${encodeURIComponent(n)}`, {
    method: "PATCH",
    body: {
      is_visible: !1
    },
    timeoutMs: 1e4
  });
  Ya(r.status, "D\u1ECDn d\u1EB9p h\u1ED9i tho\u1EA1i GPT");
}
export { D7, I7, k7, ka, zl };
