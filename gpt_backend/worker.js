import { createInterface } from "node:readline";
import { randomUUID } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

// Keep stdout reserved for the private request/response protocol.
for (const name of ["log", "info", "debug", "warn"]) console[name] = console.error;

const { Be: accounts } = await import("./src/gpt/gpt-account-store.js");
const { R7: startJob, Wl: getJob, F7: cancelJob, Ti: isBusy } = await import("./src/gpt/gpt-image-jobs.js");
const { c7: refreshAccount, d7: checkAccount, Ol: errorCode } = await import("./src/gpt/browser-env-spoof.js");
const { Nl: stopAccountTasks, Uf: closeBrowsers } = await import("./src/browser/browser-profiles.js");
const { Vl: uploadDir, x7: inspectImage, Sn: removeImages } = await import("./src/media/image-type-sniff.js");

function assertIdle(id) {
  if (isBusy(id)) throw new Error("Tài khoản đang tạo ảnh.");
}

async function dispatch(request) {
  const { action, id } = request;
  switch (action) {
    case "accounts":
      return accounts.list();
    case "add":
      return accounts.import(request.session, request.name);
    case "rename":
      assertIdle(id);
      accounts.rename(id, request.name);
      return accounts.list();
    case "replace":
      assertIdle(id);
      accounts.replaceSession(id, request.session, request.name);
      return accounts.list();
    case "select":
      accounts.select(id);
      return accounts.list();
    case "remove":
      assertIdle(id);
      await stopAccountTasks(id);
      accounts.remove(id);
      return accounts.list();
    case "check":
    case "refresh": {
      assertIdle(id);
      const result = await (action === "check" ? checkAccount(id) : refreshAccount(id));
      accounts.updateCheck(id, {
        status: action === "check" ? "ready" : "verified",
        email: result.email,
        plan: result.plan,
        ...(action === "refresh" ? { reportedImageRemaining: result.reportedImageRemaining } : {}),
      });
      return accounts.list();
    }
    case "start": {
      if (typeof request.prompt !== "string" || !request.prompt.trim() || request.prompt.length > 10000)
        throw new Error("Prompt phải có từ 1 đến 10.000 ký tự.");
      if (!["gpt-image-2", "gpt-6", "gpt-6-medium", "gpt-6-high"].includes(request.model))
        throw new Error("Model không hợp lệ.");
      if (typeof request.size !== "string" || request.size.length > 40)
        throw new Error("Tỷ lệ ảnh không hợp lệ.");
      if (!Array.isArray(request.images) || request.images.length > 5)
        throw new Error("Tối đa 5 ảnh tham chiếu.");
      const files = [];
      try {
        await mkdir(uploadDir, { recursive: true, mode: 0o700 });
        for (const image of request.images) {
          const bytes = Buffer.from(image.content, "base64");
          if (!bytes.length || bytes.length > 15000000) throw new Error("Ảnh tham chiếu phải nhỏ hơn 15 MB.");
          const file = { path: path.join(uploadDir, randomUUID()), originalname: path.basename(image.name), size: bytes.length };
          await writeFile(file.path, bytes, { flag: "wx", mode: 0o600 });
          files.push(file);
        }
        const images = await Promise.all(files.map(inspectImage));
        return startJob(id, { prompt: request.prompt.trim(), model: request.model, size: request.size, cleanupAfterGeneration: request.cleanup === true, images });
      } catch (error) {
        await removeImages(files);
        throw error;
      }
    }
    case "job": {
      const job = getJob(id);
      if (!job) throw Object.assign(new Error("Không tìm thấy tác vụ GPT. Backend có thể đã khởi động lại."), { code: "job_missing" });
      return job;
    }
    case "cancel": {
      const job = cancelJob(id);
      if (!job) throw new Error("Không tìm thấy tác vụ GPT.");
      return job;
    }
    default:
      throw new Error("Lệnh GPT không hợp lệ.");
  }
}

const input = createInterface({ input: process.stdin });
for await (const line of input) {
  let request;
  try {
    request = JSON.parse(line);
    const result = await dispatch(request);
    process.stdout.write(JSON.stringify({ result }) + "\n");
  } catch (error) {
    console.error("[GPT worker]", error);
    process.stdout.write(JSON.stringify({
      error: error instanceof Error ? error.message : "Lỗi bộ xử lý GPT.",
      code: error.code === "job_missing" ? "job_missing" : errorCode(error),
    }) + "\n");
  }
}
await closeBrowsers();
