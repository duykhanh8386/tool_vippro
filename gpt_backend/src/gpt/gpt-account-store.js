import bt from "node:path";
import Ri from "node:crypto";
import Ke from "node:fs";
import { he } from "../config/paths.js";
function Zf(e) {
  let a = e.trim();
  if (!a) throw new Error("H\xE3y nh\u1EADp Session JSON ho\u1EB7c access token.");
  if (!a.startsWith("{")) {
    let i = a.replace(/^Bearer\s+/i, "").trim();
    if (!i || /\s/.test(i)) throw new Error("Access token kh\xF4ng h\u1EE3p l\u1EC7.");
    return i;
  }
  let n;
  try {
    n = JSON.parse(a);
  } catch {
    throw new Error("Session JSON kh\xF4ng h\u1EE3p l\u1EC7.");
  }
  if (!n || typeof n != "object" || Array.isArray(n)) throw new Error("Session JSON kh\xF4ng h\u1EE3p l\u1EC7.");
  let t = n,
    r = t.accessToken ?? t.access_token;
  if (typeof r != "string" || !r.trim() || /\s/.test(r.trim())) throw new Error("Session JSON kh\xF4ng c\xF3 accessToken h\u1EE3p l\u1EC7.");
  return r.trim();
}
function Gm(e) {
  return {
    id: e.id,
    name: e.name,
    email: e.email,
    plan: e.plan,
    reportedImageRemaining: e.reportedImageRemaining,
    status: e.status,
    active: e.active,
    checkedAt: e.checkedAt,
    createdAt: e.createdAt
  };
}
var Tm = class {
    file;
    credentialsDir;
    profilesDir;
    constructor(a = bt.join(he, "gpt")) {
      this.file = bt.join(a, "accounts.json"), this.credentialsDir = bt.join(a, "credentials"), this.profilesDir = bt.join(a, "browser-profiles");
    }
    list() {
      return this.read().accounts.map(Gm);
    }
    import(a, n) {
      let t = Zf(a),
        r = Ri.createHash("sha256").update(t).digest("hex"),
        i = this.read(),
        o = i.accounts.find(s => s.tokenHash === r);
      if (o) return Gm(o);
      let l = {
        id: Ri.randomUUID(),
        name: n?.trim().slice(0, 80) || `GPT ${i.accounts.length + 1}`,
        status: "unchecked",
        active: i.accounts.length === 0,
        createdAt: new Date().toISOString(),
        tokenHash: r
      };
      this.writeCredential(l.id, t);
      try {
        i.accounts.push(l), this.write(i);
      } catch (s) {
        throw Ke.rmSync(this.credentialPath(l.id), {
          force: !0
        }), s;
      }
      return Gm(l);
    }
    select(a) {
      let n = this.read();
      if (!n.accounts.some(t => t.id === a)) throw new Error("Kh\xF4ng t\xECm th\u1EA5y t\xE0i kho\u1EA3n GPT.");
      for (let t of n.accounts) t.active = t.id === a;
      this.write(n);
    }
    rename(a, n) {
      let t = n.trim().slice(0, 80);
      if (!t) throw new Error("T\xEAn t\xE0i kho\u1EA3n kh\xF4ng \u0111\u01B0\u1EE3c \u0111\u1EC3 tr\u1ED1ng.");
      let r = this.read(),
        i = r.accounts.find(o => o.id === a);
      if (!i) throw new Error("Kh\xF4ng t\xECm th\u1EA5y t\xE0i kho\u1EA3n GPT.");
      i.name = t, this.write(r);
    }
    replaceSession(a, n, t) {
      let r = Zf(n),
        i = Ri.createHash("sha256").update(r).digest("hex"),
        o = this.read(),
        l = o.accounts.find(m => m.id === a);
      if (!l) throw new Error("Kh\xF4ng t\xECm th\u1EA5y t\xE0i kho\u1EA3n GPT.");
      if (o.accounts.some(m => m.id !== a && m.tokenHash === i)) throw new Error("Session n\xE0y \u0111\xE3 \u0111\u01B0\u1EE3c th\xEAm v\xE0o t\xE0i kho\u1EA3n GPT kh\xE1c.");
      let s = this.credentialPath(a),
        u = `${s}.${Ri.randomUUID()}.tmp`;
      Ke.writeFileSync(u, r, {
        mode: 384,
        flag: "wx"
      });
      try {
        Ke.renameSync(u, s), l.tokenHash = i, t?.trim() && (l.name = t.trim().slice(0, 80)), l.email = void 0, l.plan = void 0, l.reportedImageRemaining = void 0, l.checkedAt = void 0, l.status = "unchecked", this.write(o);
      } finally {
        Ke.rmSync(u, {
          force: !0
        });
      }
    }
    remove(a) {
      let n = this.read(),
        t = n.accounts.find(r => r.id === a);
      if (!t) throw new Error("Kh\xF4ng t\xECm th\u1EA5y t\xE0i kho\u1EA3n GPT.");
      n.accounts = n.accounts.filter(r => r.id !== a), t.active && n.accounts.length > 0 && (n.accounts[0].active = !0), this.write(n), Ke.rmSync(this.credentialPath(a), {
        force: !0
      }), Ke.rmSync(bt.join(this.profilesDir, a), {
        recursive: !0,
        force: !0
      });
    }
    updateCheck(a, n) {
      let t = this.read(),
        r = t.accounts.find(i => i.id === a);
      if (!r) throw new Error("Kh\xF4ng t\xECm th\u1EA5y t\xE0i kho\u1EA3n GPT.");
      r.status = n.status, r.checkedAt = new Date().toISOString(), n.email && (r.email = n.email), n.plan && (r.plan = n.plan), "reportedImageRemaining" in n && (r.reportedImageRemaining = n.reportedImageRemaining), this.write(t);
    }
    getToken(a) {
      if (!this.read().accounts.some(t => t.id === a)) throw new Error("Kh\xF4ng t\xECm th\u1EA5y t\xE0i kho\u1EA3n GPT.");
      let n = Ke.readFileSync(this.credentialPath(a), "utf8").trim();
      if (!n) throw new Error("T\xE0i kho\u1EA3n GPT kh\xF4ng c\xF3 access token.");
      return n;
    }
    credentialPath(a) {
      return bt.join(this.credentialsDir, `${a}.token`);
    }
    writeCredential(a, n) {
      Ke.mkdirSync(this.credentialsDir, {
        recursive: !0,
        mode: 448
      }), Ke.writeFileSync(this.credentialPath(a), n, {
        mode: 384,
        flag: "wx"
      });
    }
    read() {
      if (!Ke.existsSync(this.file)) return {
        accounts: []
      };
      let a = JSON.parse(Ke.readFileSync(this.file, "utf8"));
      if (!Array.isArray(a.accounts)) throw new Error("D\u1EEF li\u1EC7u t\xE0i kho\u1EA3n GPT kh\xF4ng h\u1EE3p l\u1EC7.");
      return a;
    }
    write(a) {
      Ke.mkdirSync(bt.dirname(this.file), {
        recursive: !0,
        mode: 448
      });
      let n = `${this.file}.${Ri.randomUUID()}.tmp`;
      try {
        Ke.writeFileSync(n, JSON.stringify(a), {
          mode: 384,
          flag: "wx"
        }), Ke.renameSync(n, this.file);
      } finally {
        Ke.rmSync(n, {
          force: !0
        });
      }
    }
  },
  Be = new Tm();
export { Be };
