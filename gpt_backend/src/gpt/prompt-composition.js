import Ul from "node:crypto";
function Km() {
  return {
    generatedImages: [],
    streamCompleted: !1,
    blocked: !1
  };
}
var J0 = {
  "1:1": "Use a centered square composition with a 1:1 aspect ratio.",
  "3:2": "Use a 3:2 landscape composition suited to photography, product displays, and wide scenes.",
  "2:3": "Use a 2:3 portrait composition suited to posters, people, and vertical scenes.",
  "16:9": "Use a 16:9 landscape composition for a widescreen display.",
  "9:16": "Use a 9:16 portrait composition for a vertical display.",
  "4:3": "Use a balanced 4:3 composition with room for visual detail.",
  "3:4": "Use a 3:4 portrait composition suited to people and vertical scenes.",
  "1080p": "Prefer a square composition corresponding to 1080 x 1080 pixels; the returned pixel dimensions may vary.",
  "2k": "Prefer a square composition corresponding to 2048 x 2048 pixels; the returned pixel dimensions may vary.",
  "4k": "Prefer a square composition corresponding to 2880 x 2880 pixels; the returned pixel dimensions may vary."
};
function f7(e, a) {
  let n = a.toLowerCase().replaceAll("\xD7", "x").replaceAll(" ", "").trim();
  if (!n || n === "auto") return e.trim();
  let t = J0[n] ?? (/^\d+x\d+$/.test(n) ? `Prefer an aspect ratio corresponding to ${n.replace("x", " x ")} pixels; the returned pixel dimensions may vary.` : `Create the image with a target size or aspect ratio of ${n}.`);
  return `${e.trim()}

${t}`;
}
function h7(e) {
  return e === "gpt-image-2" ? "gpt-5-5" : e === "gpt-6" ? "gpt-6" : e === "gpt-6-medium" || e === "gpt-6-high" ? "gpt-6-thinking" : "gpt-5-5";
}
function jl(e) {
  if (e === "gpt-6-medium") return "standard";
  if (e === "gpt-6-high") return "extended";
}
function E7(e) {
  return {
    action: "next",
    fork_from_shared_post: !1,
    parent_message_id: Ul.randomUUID(),
    model: h7(e.model),
    ...(jl(e.model) ? {
      thinking_effort: jl(e.model)
    } : {}),
    client_prepare_state: "success",
    timezone_offset_min: -480,
    timezone: "Asia/Shanghai",
    conversation_mode: {
      kind: "primary_assistant"
    },
    system_hints: ["picture_v2"],
    partial_query: {
      id: Ul.randomUUID(),
      author: {
        role: "user"
      },
      content: {
        content_type: "text",
        parts: [f7(e.prompt, e.size)]
      }
    },
    supports_buffering: !0,
    supported_encodings: ["v1"],
    client_contextual_info: {
      app_name: "chatgpt.com"
    }
  };
}
function g7(e) {
  return typeof e != "string" || !e.trim() ? {} : {
    "X-Conduit-Token": e.trim()
  };
}
function p7(e, a = []) {
  let n = f7(e.prompt, e.size),
    t = a.length ? {
      content_type: "multimodal_text",
      parts: [...a.map(r => ({
        content_type: "image_asset_pointer",
        asset_pointer: `file-service://${r.fileId}`,
        width: r.width,
        height: r.height,
        size_bytes: r.size
      })), n]
    } : {
      content_type: "text",
      parts: [n]
    };
  return {
    action: "next",
    turn_attribution: {
      turn_trigger: "composer"
    },
    is_do_not_remember: !1,
    messages: [{
      id: Ul.randomUUID(),
      author: {
        role: "user"
      },
      create_time: Date.now() / 1e3,
      content: t,
      metadata: {
        developer_mode_connector_ids: [],
        selected_github_repos: [],
        selected_all_github_repos: !1,
        system_hints: ["picture_v2"],
        serialization_metadata: {
          custom_symbol_offsets: []
        },
        ...(a.length ? {
          attachments: a.map(r => ({
            id: r.fileId,
            mimeType: r.mime,
            name: r.name,
            size: r.size,
            width: r.width,
            height: r.height
          }))
        } : {})
      }
    }],
    parent_message_id: Ul.randomUUID(),
    model: h7(e.model),
    ...(jl(e.model) ? {
      thinking_effort: jl(e.model)
    } : {}),
    client_prepare_state: "sent",
    timezone_offset_min: -480,
    timezone: "Asia/Shanghai",
    conversation_mode: {
      kind: "primary_assistant"
    },
    enable_message_followups: !0,
    system_hints: ["picture_v2"],
    supports_buffering: !0,
    supported_encodings: ["v1"],
    paragen_cot_summary_display_override: "allow",
    force_parallel_switch: "auto",
    client_contextual_info: {
      is_dark_mode: !1,
      time_since_loaded: 1200,
      page_height: 1072,
      page_width: 1724,
      pixel_ratio: 1.2,
      screen_height: 1440,
      screen_width: 2560,
      app_name: "chatgpt.com"
    }
  };
}
function Ge(e) {
  return e && typeof e == "object" && !Array.isArray(e) ? e : {};
}
function yn(e) {
  return typeof e == "string" && e.trim() ? e.trim() : void 0;
}
function K0(e, a) {
  let n = JSON.stringify(e ?? {}),
    t = [];
  for (let r of n.matchAll(/(file-service|sediment):\/\/([A-Za-z0-9_-]+)/g)) {
    let i = r[1],
      o = r[2];
    o !== "file_upload" && !t.some(l => l.scheme === i && l.id === o) && t.push({
      id: o,
      scheme: i,
      source: a
    });
  }
  return t;
}
function H0(e) {
  let a = Ge(e.metadata);
  return a.async_task_type === "image_gen" || !!yn(a.image_gen_title);
}
function A7(e, a, n) {
  if (yn(Ge(a.author).role) !== "tool") return;
  let t = K0(a.content, n);
  if (!(!H0(a) && t.length === 0)) for (let r of t) e.generatedImages.some(i => i.id === r.id && i.scheme === r.scheme) || e.generatedImages.push(r);
}
function S7(e) {
  let a = Ge(e.content).parts;
  return Array.isArray(a) && a.map(t => typeof t == "string" ? t : yn(Ge(t).text) ?? "").filter(Boolean).join(`
`).trim() || void 0;
}
function y7(e, a) {
  if (a === "[DONE]") return;
  let n;
  try {
    n = Ge(JSON.parse(a));
  } catch {
    return;
  }
  if (e.conversationId = yn(n.conversation_id) ?? yn(Ge(n.v).conversation_id) ?? e.conversationId, n.type === "message_stream_complete" && (e.streamCompleted = !0), n.type === "error") {
    e.error = "ChatGPT tr\u1EA3 v\u1EC1 l\u1ED7i khi t\u1EA1o \u1EA3nh.";
    return;
  }
  if (n.type === "moderation" && Ge(n.moderation_response).blocked === !0 && (e.blocked = !0), n.type === "server_ste_metadata") {
    let i = Ge(n.metadata);
    typeof i.tool_invoked == "boolean" && (e.toolInvoked = i.tool_invoked), e.turnUseCase = yn(i.turn_use_case) ?? e.turnUseCase;
  }
  let t = Ge(n.message ?? Ge(n.v).message),
    r = yn(Ge(t.author).role);
  A7(e, t, "stream"), (r === "assistant" || r === "tool") && (e.text = S7(t) ?? e.text), r === "assistant" && C7(t) && (t.end_turn === !0 || Ge(t.metadata).is_error === !0) && (e.streamCompleted = !0);
}
function w7(e) {
  let a = Ge(Ge(e).mapping),
    n = Km(),
    t;
  for (let i of Object.values(a)) {
    let o = Ge(Ge(i).message),
      l = yn(Ge(o.author).role);
    A7(n, o, "poll"), l === "assistant" && o.recipient !== "tool" && C7(o) && (t = S7(o) ?? t);
  }
  let r = b7(t);
  return {
    images: n.generatedImages,
    text: r ? void 0 : t
  };
}
function b7(e) {
  return /creating your image|working on your image|image is ready|we(?:'|’)ll notify you|we will notify you|正在处理图片|图片准备好后/i.test(e ?? "");
}
function v7(e) {
  if (!(!e.streamCompleted || !e.text || b7(e.text))) return e.text;
}
function C7(e) {
  return ["finished_successfully", "finished_partial", "incomplete"].includes(yn(e.status) ?? "");
}
export { E7, Km, g7, p7, v7, w7, y7 };
