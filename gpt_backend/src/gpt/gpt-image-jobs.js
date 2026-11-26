import aA from "node:crypto";
import { D } from "../logging/logger.js";
import { Ml, sr } from "../browser/browser-profiles.js";
import { Be } from "./gpt-account-store.js";
import { Ol, jm } from "./browser-env-spoof.js";
import { Sn } from "../media/image-type-sniff.js";
import { Km } from "./prompt-composition.js";
import { D7, I7, k7, ka, zl } from "./gpt-image-api.js";
import { M7 } from "../media/image-file-utils.js";
var Kl = class {
  constructor(a, n = 10) {
    this.runner = a, this.maxConcurrentPerAccount = n;
  }
  runner;
  maxConcurrentPerAccount;
  jobs = new Map();
  activeJobsByAccount = new Map();
  queuedJobsByAccount = new Map();
  isBusy(a) {
    return (this.activeJobsByAccount.get(a) ?? 0) > 0 || (this.queuedJobsByAccount.get(a)?.length ?? 0) > 0;
  }
  hasActiveJobs() {
    return this.activeJobsByAccount.size > 0 || this.queuedJobsByAccount.size > 0;
  }
  start(a, n) {
    let t = new Date().toISOString(),
      r = {
        id: aA.randomUUID(),
        accountId: a,
        model: n.model,
        status: "queued",
        stage: "queued",
        createdAt: t,
        updatedAt: t
      },
      i = {
        job: r,
        controller: new AbortController(),
        input: n
      };
    for (let [o, l] of this.jobs) l.job.status !== "running" && Date.now() - Date.parse(l.job.updatedAt) > 1440 * 6e4 && this.jobs.delete(o);
    if (this.jobs.set(r.id, i), (this.activeJobsByAccount.get(a) ?? 0) < this.maxConcurrentPerAccount) this.startRunner(i);else {
      let o = this.queuedJobsByAccount.get(a) ?? [];
      o.push(r.id), this.queuedJobsByAccount.set(a, o);
    }
    return zl(r);
  }
  startRunner(a) {
    let n = a.job.accountId;
    this.activeJobsByAccount.set(n, (this.activeJobsByAccount.get(n) ?? 0) + 1), Promise.resolve().then(() => this.runner(a.input, a)).catch(() => {}).finally(() => {
      let t = (this.activeJobsByAccount.get(n) ?? 1) - 1;
      t > 0 ? this.activeJobsByAccount.set(n, t) : this.activeJobsByAccount.delete(n), this.startQueuedJobs(n);
    });
  }
  startQueuedJobs(a) {
    let n = this.queuedJobsByAccount.get(a);
    for (; n?.length && (this.activeJobsByAccount.get(a) ?? 0) < this.maxConcurrentPerAccount;) {
      let t = n.shift(),
        r = t ? this.jobs.get(t) : void 0;
      r?.job.status === "queued" && this.startRunner(r);
    }
    n?.length || this.queuedJobsByAccount.delete(a);
  }
  get(a) {
    let n = this.jobs.get(a);
    return n ? zl(n.job) : void 0;
  }
  cancel(a) {
    let n = this.jobs.get(a);
    if (n) {
      if (n.job.status === "queued" || n.job.status === "running") {
        let t = n.job.status === "queued";
        if (n.controller.abort(), ka(n.job, {
          status: "cancelled",
          stage: "done"
        }), t) {
          let r = this.queuedJobsByAccount.get(n.job.accountId);
          r && (this.queuedJobsByAccount.set(n.job.accountId, r.filter(i => i !== a)), this.queuedJobsByAccount.get(n.job.accountId)?.length === 0 && this.queuedJobsByAccount.delete(n.job.accountId)), Sn(n.input.images ?? []);
        }
      }
      return zl(n.job);
    }
  }
};
var Hl = D("GPT Image");
function nA(e = {
  getToken: a => Be.getToken(a),
  withPage: Ml,
  generate: I7,
  download: D7,
  persist: M7,
  removeConversation: k7
}) {
  return async function (n, t) {
    let {
        job: r,
        controller: i
      } = t,
      o = "load account credential";
    try {
      Hl.info("[GPT Image] Job started", {
        jobId: r.id,
        model: n.model,
        referenceCount: n.images?.length ?? 0
      });
      let l = e.getToken(r.accountId);
      o = "open ChatGPT page", ka(r, {
        status: "running",
        stage: "preparing"
      }), await e.withPage(r.accountId, async (s, u) => {
        let m = Km();
        await e.generate(s, u, l, n, m, r, i.signal, x => {
          o = x, Hl.info("[GPT Image] Job step", {
            jobId: r.id,
            step: o
          });
        }), i.signal.throwIfAborted(), o = "download generated image", ka(r, {
          stage: "downloading"
        });
        let c = await e.download(s, l, m, i.signal);
        i.signal.throwIfAborted();
        let d = await e.persist(r.id, c);
        return i.signal.throwIfAborted(), ka(r, {
          status: "success",
          stage: "done",
          imageUrl: d
        }), {
          conversationId: m.conversationId
        };
      }, {
        signal: i.signal,
        afterSuccess: n.cleanupAfterGeneration ? {
          run: async (s, u) => {
            if (!u.conversationId) throw new Error("ChatGPT kh\xF4ng tr\u1EA3 m\xE3 h\u1ED9i tho\u1EA1i \u0111\u1EC3 d\u1ECDn d\u1EB9p.");
            await e.removeConversation(s, l, u.conversationId);
          },
          onError: s => Hl.warn("[GPT Image] Conversation cleanup failed", {
            jobId: r.id,
            step: "cleanup generated conversation",
            ...(s instanceof sr ? {
              kind: s.kind
            } : jm(s))
          })
        } : void 0
      });
    } catch (l) {
      if (r.status === "success") return;
      if (i.signal.aborted) ka(r, {
        status: "cancelled",
        stage: "done"
      });else {
        let s = Ol(l);
        Hl.error("[GPT Image] Job failed", {
          jobId: r.id,
          stage: r.stage,
          step: o,
          errorCode: s,
          ...jm(l)
        }), ka(r, {
          status: "error",
          stage: "done",
          errorCode: s
        });
      }
    } finally {
      await Sn(n.images ?? []);
    }
  };
}
var Gi = new Kl(nA());
function R7(e, a) {
  if (!Be.list().some(n => n.id === e)) throw new Error("Kh\xF4ng t\xECm th\u1EA5y t\xE0i kho\u1EA3n GPT.");
  return Gi.start(e, a);
}
function Wl(e) {
  return Gi.get(e);
}
function F7(e) {
  return Gi.cancel(e);
}
function Ti(e) {
  return Gi.isBusy(e);
}
function P7() {
  return Gi.hasActiveJobs();
}
export { F7, P7, R7, Ti, Wl };
