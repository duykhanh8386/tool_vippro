import qm from "node:fs/promises";
import Ym from "node:path";
import { he } from "../config/paths.js";
var N7 = Ym.join(he, "gpt", "images");
function $0(e) {
  if (e.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))) return "png";
  if (e.subarray(0, 3).equals(Buffer.from([255, 216, 255]))) return "jpg";
  if (e.toString("ascii", 0, 4) === "RIFF" && e.toString("ascii", 8, 12) === "WEBP") return "webp";
  throw new Error("K\u1EBFt qu\u1EA3 ChatGPT kh\xF4ng ph\u1EA3i file \u1EA3nh h\u1EE3p l\u1EC7.");
}
async function M7(e, a, n = N7) {
  let t = $0(a);
  await qm.mkdir(n, {
    recursive: !0,
    mode: 448
  });
  let r = `${e}.${t}`;
  return await qm.writeFile(Ym.join(n, r), a, {
    mode: 384,
    flag: "wx"
  }), `/__browser/gpt-accounts/images/${r}`;
}
async function cr(e) {
  if (!/^[0-9a-f-]{36}\.(png|jpg|webp)$/i.test(e)) return;
  let a = Ym.join(N7, e);
  try {
    return await qm.access(a), a;
  } catch {
    return;
  }
}
export { M7, cr };
