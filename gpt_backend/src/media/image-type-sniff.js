import mr from "node:fs/promises";
import j0 from "node:fs";
import zm from "node:path";
import { he } from "../config/paths.js";
var Vl = zm.join(he, "gpt", "uploads"),
  Jm = new Set();
process.once("exit", () => {
  for (let e of Jm) j0.rmSync(e, {
    force: !0
  });
});
function z0(e) {
  if (e.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])) && e.length >= 24) return {
    mime: "image/png",
    width: e.readUInt32BE(16),
    height: e.readUInt32BE(20)
  };
  if (e.subarray(0, 3).equals(Buffer.from([255, 216, 255]))) {
    let a = 2;
    for (; a + 8 < e.length && e[a] === 255;) {
      let n = e[a + 1],
        t = e.readUInt16BE(a + 2);
      if (t < 2 || a + 2 + t > e.length) break;
      if ([192, 193, 194, 195, 197, 198, 199, 201, 202, 203, 205, 206, 207].includes(n)) return {
        mime: "image/jpeg",
        width: e.readUInt16BE(a + 7),
        height: e.readUInt16BE(a + 5)
      };
      a += t + 2;
    }
  }
  if (e.toString("ascii", 0, 4) === "RIFF" && e.toString("ascii", 8, 12) === "WEBP") {
    let a = e.toString("ascii", 12, 16);
    if (a === "VP8X" && e.length >= 30) return {
      mime: "image/webp",
      width: e.readUIntLE(24, 3) + 1,
      height: e.readUIntLE(27, 3) + 1
    };
    if (a === "VP8 " && e.length >= 30) return {
      mime: "image/webp",
      width: e.readUInt16LE(26) & 16383,
      height: e.readUInt16LE(28) & 16383
    };
    if (a === "VP8L" && e.length >= 25) {
      let n = e.readUInt32LE(21);
      return {
        mime: "image/webp",
        width: (n & 16383) + 1,
        height: (n >>> 14 & 16383) + 1
      };
    }
  }
  throw new Error("\u1EA2nh tham chi\u1EBFu ph\u1EA3i l\xE0 PNG, JPEG ho\u1EB7c WebP h\u1EE3p l\u1EC7.");
}
async function x7(e) {
  let a = await mr.open(e.path, "r"),
    n;
  try {
    n = Buffer.alloc(Math.min(e.size, 256e3));
    let {
      bytesRead: o
    } = await a.read(n, 0, n.length, 0);
    n = n.subarray(0, o);
  } finally {
    await a.close();
  }
  let {
    mime: t,
    width: r,
    height: i
  } = z0(n);
  if (!r || !i || r > 16384 || i > 16384) throw new Error("K\xEDch th\u01B0\u1EDBc \u1EA3nh tham chi\u1EBFu kh\xF4ng h\u1EE3p l\u1EC7.");
  return Jm.add(e.path), {
    path: e.path,
    name: zm.basename(e.originalname).slice(0, 120) || "image",
    size: e.size,
    mime: t,
    width: r,
    height: i
  };
}
async function Sn(e) {
  await Promise.allSettled(e.map(a => mr.rm(a.path, {
    force: !0
  }))), e.forEach(a => Jm.delete(a.path));
}
async function B7(e = Date.now(), a = Vl) {
  await mr.mkdir(a, {
    recursive: !0,
    mode: 448
  });
  for (let n of await mr.readdir(a)) {
    if (!/^[0-9a-f-]{36}$/.test(n)) continue;
    let t = zm.join(a, n),
      r = await mr.stat(t).catch(() => {});
    r?.isFile() && e - r.mtimeMs > 1440 * 6e4 && (await mr.rm(t, {
      force: !0
    }));
  }
}
export { B7, Sn, Vl, x7 };
