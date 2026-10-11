/*!
 * Property Chat widget: a real-estate advice chat box that can be embedded in any website.
 *
 * To embed it (paste before the </body> tag):
 *   <script src="https://YOUR-SERVER/widget.js"
 *           data-title="Tư vấn nhà đất"
 *           data-color="#0f766e"
 *           defer></script>
 *
 * See README.md for every data-* option.
 */
(function () {
  "use strict";
  if (window.PropertyChat) return; // avoid embedding twice

  var script = document.currentScript;
  var ds = (script && script.dataset) || {};
  // Default texts are in Vietnamese because they are shown to the site's visitors
  var cfg = {
    api: (ds.api || (script ? new URL(script.src).origin : "")).replace(/\/$/, ""),
    title: ds.title || "Tư vấn bất động sản",
    subtitle: ds.subtitle || "Thường trả lời ngay",
    color: ds.color || "#0f766e",
    position: ds.position === "left" ? "left" : "right",
    greeting:
      ds.greeting ||
      "Xin chào! Mình có thể giúp bạn tìm căn hộ, nhà phố phù hợp hoặc giải đáp thủ tục mua nhà. Bạn đang quan tâm khu vực nào?",
    suggestions: (ds.suggestions ||
      "Căn 2 phòng ngủ dưới 3 tỷ ở Quận 7|Dự án nào gần metro?|Mua nhà phải đóng thuế phí gì?")
      .split("|").filter(Boolean),
    contact: ds.contact || "",          // e.g. tel:0900000000 or https://zalo.me/0900000000
    contactLabel: ds.contactLabel || "Gọi môi giới",
    open: ds.open === "true",
  };
  var TEXT = {
    reset: "Làm mới",
    resetTitle: "Bắt đầu cuộc trò chuyện mới",
    close: "Đóng",
    placeholder: "Nhập câu hỏi...",
    inputLabel: "Câu hỏi",
    send: "Gửi",
    disclaimer: "Thông tin chỉ mang tính tham khảo",
    openChat: "Mở chat tư vấn",
    askAboutListing: "Hỏi thêm về căn này",
    listingDetails: "Cho mình xem chi tiết tin ",
    httpError: "Có lỗi xảy ra",
    offline: "Không kết nối được tới máy chủ, vui lòng thử lại.",
    billion: " tỷ",
    million: " triệu",
    bedrooms: " PN",
  };

  var KEY = "property-chat:" + cfg.api;
  var history = [];
  try { history = JSON.parse(sessionStorage.getItem(KEY) || "[]"); } catch (e) { history = []; }
  function save() {
    try { sessionStorage.setItem(KEY, JSON.stringify(history.slice(-30))); } catch (e) { /* ignore */ }
  }

  // ---------- UI (Shadow DOM so the host site's CSS cannot touch it, and vice versa) ----------
  var host = document.createElement("div");
  host.id = "property-chat";
  var root = host.attachShadow({ mode: "open" });
  root.innerHTML =
    "<style>" +
    ":host{all:initial;--c:" + cfg.color + "}" +
    "*{box-sizing:border-box;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}" +
    ".btn{position:fixed;bottom:20px;" + cfg.position + ":20px;width:60px;height:60px;border-radius:50%;border:0;background:var(--c);color:#fff;cursor:pointer;box-shadow:0 6px 20px rgba(0,0,0,.25);z-index:2147483646;display:flex;align-items:center;justify-content:center;transition:transform .2s}" +
    ".btn:hover{transform:scale(1.06)}" +
    ".btn svg{width:28px;height:28px}" +
    ".panel{position:fixed;bottom:92px;" + cfg.position + ":20px;width:380px;max-width:calc(100vw - 32px);height:600px;max-height:calc(100vh - 112px);background:#fff;color:#1f2937;border-radius:16px;box-shadow:0 12px 40px rgba(0,0,0,.25);display:none;flex-direction:column;overflow:hidden;z-index:2147483647}" +
    ".panel.on{display:flex}" +
    "@media(max-width:480px){.panel{inset:0;width:100%;max-width:none;height:100%;max-height:none;border-radius:0}.panel.on~.btn{display:none}}" +
    ".hd{background:var(--c);color:#fff;padding:14px 16px;display:flex;align-items:center;gap:10px}" +
    ".hd .t{font-weight:600;font-size:16px}.hd .s{font-size:12px;opacity:.85}" +
    ".hd .x{margin-left:auto;background:none;border:0;color:#fff;font-size:24px;cursor:pointer;line-height:1;padding:4px}" +
    ".hd .r{background:none;border:0;color:#fff;opacity:.85;cursor:pointer;font-size:12px;text-decoration:underline}" +
    ".body{flex:1;overflow-y:auto;padding:16px;background:#f7f7f8;display:flex;flex-direction:column;gap:10px}" +
    ".m{flex-shrink:0;max-width:85%;padding:10px 13px;border-radius:14px;font-size:14px;line-height:1.5;word-wrap:break-word}" +
    ".m.u{align-self:flex-end;background:var(--c);color:#fff;border-bottom-right-radius:4px;white-space:pre-wrap}" +
    ".m.a{align-self:flex-start;background:#fff;border:1px solid #e5e7eb;border-bottom-left-radius:4px}" +
    ".m.a p{margin:0 0 6px}.m.a p:last-child{margin:0}.m.a ul{margin:4px 0;padding-left:18px}" +
    ".m.err{background:#fef2f2;border-color:#fecaca;color:#991b1b}" +
    ".typing span{display:inline-block;width:6px;height:6px;margin:0 2px;border-radius:50%;background:#9ca3af;animation:b 1s infinite}" +
    ".typing span:nth-child(2){animation-delay:.15s}.typing span:nth-child(3){animation-delay:.3s}" +
    "@keyframes b{0%,60%,100%{opacity:.3}30%{opacity:1}}" +
    ".cards{flex-shrink:0;display:flex;gap:8px;overflow-x:auto;padding-bottom:4px;align-self:stretch}" +
    ".card{flex:0 0 200px;background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:10px;font-size:13px}" +
    ".card .id{font-size:11px;color:#6b7280}.card .n{font-weight:600;margin:2px 0 6px;line-height:1.3}" +
    ".card .p{color:var(--c);font-weight:700;font-size:15px}.card .meta{color:#4b5563;margin-top:4px}" +
    ".card button{margin-top:8px;width:100%;border:1px solid var(--c);color:var(--c);background:#fff;border-radius:8px;padding:5px;cursor:pointer;font-size:12px}" +
    ".sug{flex-shrink:0;display:flex;flex-wrap:wrap;gap:6px}" +
    ".sug button{border:1px solid var(--c);color:var(--c);background:#fff;border-radius:999px;padding:6px 11px;font-size:13px;cursor:pointer}" +
    ".ft{border-top:1px solid #e5e7eb;padding:10px;display:flex;gap:8px;background:#fff}" +
    ".ft textarea{flex:1;resize:none;border:1px solid #d1d5db;border-radius:10px;padding:9px 11px;font-size:14px;max-height:100px;outline:none;color:#1f2937;background:#fff}" +
    ".ft textarea:focus{border-color:var(--c)}" +
    ".ft button{border:0;background:var(--c);color:#fff;border-radius:10px;padding:0 14px;cursor:pointer;font-size:14px}" +
    ".ft button:disabled{opacity:.5;cursor:default}" +
    ".note{font-size:11px;color:#9ca3af;text-align:center;padding:0 10px 8px;background:#fff}" +
    ".note a{color:var(--c)}" +
    "</style>" +
    '<div class="panel" role="dialog" aria-label="' + esc(cfg.title) + '">' +
    '<div class="hd"><div><div class="t">' + esc(cfg.title) + '</div><div class="s">' + esc(cfg.subtitle) + "</div></div>" +
    '<button class="r" title="' + esc(TEXT.resetTitle) + '">' + esc(TEXT.reset) + "</button>" +
    '<button class="x" aria-label="' + esc(TEXT.close) + '">&times;</button></div>' +
    '<div class="body"></div>' +
    '<form class="ft"><textarea rows="1" placeholder="' + esc(TEXT.placeholder) + '" aria-label="' + esc(TEXT.inputLabel) + '"></textarea><button type="submit">' + esc(TEXT.send) + "</button></form>" +
    '<div class="note">' + esc(TEXT.disclaimer) +
    (cfg.contact ? ' · <a href="' + esc(cfg.contact) + '" target="_blank" rel="noopener">' + esc(cfg.contactLabel) + "</a>" : "") +
    "</div></div>" +
    '<button class="btn" aria-label="' + esc(TEXT.openChat) + '"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></button>';

  var panel = root.querySelector(".panel");
  var body = root.querySelector(".body");
  var form = root.querySelector("form");
  var input = root.querySelector("textarea");
  var sendBtn = form.querySelector("button");
  var busy = false;

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  // Minimal, safe Markdown: escape HTML first, then add tags
  function md(text) {
    var out = [], list = false;
    esc(text).split("\n").forEach(function (line) {
      line = line.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/^#{1,6}\s+(.*)$/, "<b>$1</b>");
      var li = line.match(/^\s*(?:[-*•]|\d+\.)\s+(.*)$/);
      if (li) {
        if (!list) { out.push("<ul>"); list = true; }
        out.push("<li>" + li[1] + "</li>");
        return;
      }
      if (list) { out.push("</ul>"); list = false; }
      if (line.trim()) out.push("<p>" + line + "</p>");
    });
    if (list) out.push("</ul>");
    return out.join("");
  }

  function scroll() { body.scrollTop = body.scrollHeight; }

  function bubble(role, text) {
    var d = document.createElement("div");
    d.className = "m " + (role === "user" ? "u" : "a");
    if (role === "user") d.textContent = text; else d.innerHTML = md(text);
    body.appendChild(d);
    scroll();
    return d;
  }

  function formatPrice(billions) {
    return billions >= 1
      ? String(billions).replace(".", ",") + TEXT.billion
      : Math.round(billions * 1000) + TEXT.million;
  }

  function cards(items) {
    var wrap = document.createElement("div");
    wrap.className = "cards";
    items.forEach(function (t) {
      var c = document.createElement("div");
      c.className = "card";
      c.innerHTML =
        '<div class="id">' + esc(t.id) + " · " + esc(t.type_label) + "</div>" +
        '<div class="n">' + esc(t.title) + "</div>" +
        '<div class="p">' + esc(formatPrice(t.price_billion_vnd)) + "</div>" +
        '<div class="meta">' + esc(t.area_m2) + " m² · " +
        (t.bedrooms ? esc(t.bedrooms) + esc(TEXT.bedrooms) + " · " : "") + esc(t.district) + "</div>" +
        '<div class="meta">' + esc(t.legal_status) + "</div>" +
        "<button>" + esc(TEXT.askAboutListing) + "</button>";
      c.querySelector("button").onclick = function () {
        send(TEXT.listingDetails + t.id);
      };
      wrap.appendChild(c);
    });
    body.appendChild(wrap);
    scroll();
  }

  function suggestions() {
    if (!cfg.suggestions.length) return;
    var s = document.createElement("div");
    s.className = "sug";
    cfg.suggestions.forEach(function (q) {
      var b = document.createElement("button");
      b.textContent = q;
      b.onclick = function () { s.remove(); send(q); };
      s.appendChild(b);
    });
    body.appendChild(s);
  }

  function render() {
    body.innerHTML = "";
    bubble("assistant", cfg.greeting);
    history.forEach(function (m) { bubble(m.role, m.content); });
    if (!history.length) suggestions();
  }

  // ---------- Send a question and read the streamed answer (SSE) ----------
  function send(text) {
    text = (text || "").trim();
    if (!text || busy) return;
    busy = true;
    sendBtn.disabled = true;
    var sug = body.querySelector(".sug");
    if (sug) sug.remove();

    bubble("user", text);
    history.push({ role: "user", content: text });
    save();

    var out = bubble("assistant", "");
    out.innerHTML = '<span class="typing"><span></span><span></span><span></span></span>';
    var answer = "";

    function finish(errMsg) {
      if (errMsg) {
        if (!answer) out.remove();
        var e = bubble("assistant", errMsg);
        e.classList.add("err");
        history.pop(); // drop the failed question so resending it does not duplicate it
      } else if (answer.trim()) {
        history.push({ role: "assistant", content: answer.trim() });
      }
      save();
      busy = false;
      sendBtn.disabled = false;
      input.focus();
    }

    fetch(cfg.api + "/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: history.slice(-20) }),
    })
      .then(function (res) {
        if (!res.ok) {
          return res.json().catch(function () { return {}; }).then(function (j) {
            throw new Error(typeof j.detail === "string" ? j.detail : TEXT.httpError + " (" + res.status + ").");
          });
        }
        var reader = res.body.getReader();
        var dec = new TextDecoder();
        var buf = "";
        var errMsg = null;

        function handle(block) {
          var ev = "message", data = "";
          block.split("\n").forEach(function (l) {
            if (l.indexOf("event:") === 0) ev = l.slice(6).trim();
            else if (l.indexOf("data:") === 0) data += l.slice(5).trim();
          });
          if (!data) return;
          var d = JSON.parse(data);
          if (ev === "text") {
            answer += d.text;
            out.innerHTML = md(answer) || out.innerHTML;
            scroll();
          } else if (ev === "listings") {
            cards(d.items);
            // move the answer bubble below the listing cards
            body.appendChild(out);
            scroll();
          } else if (ev === "error") {
            errMsg = d.message;
          }
        }

        function pump() {
          return reader.read().then(function (r) {
            if (r.done) {
              if (buf.trim()) handle(buf);
              if (!answer.trim() && !errMsg) out.remove();
              return finish(errMsg);
            }
            buf += dec.decode(r.value, { stream: true });
            var parts = buf.split("\n\n");
            buf = parts.pop();
            parts.forEach(handle);
            return pump();
          });
        }
        return pump();
      })
      .catch(function (err) {
        finish(err && err.message && err.message.indexOf("Failed to fetch") === -1
          ? err.message
          : TEXT.offline);
      });
  }

  // ---------- Events ----------
  function toggle(on) {
    panel.classList.toggle("on", on);
    if (on) { scroll(); input.focus(); }
  }
  root.querySelector(".btn").onclick = function () { toggle(!panel.classList.contains("on")); };
  root.querySelector(".x").onclick = function () { toggle(false); };
  root.querySelector(".r").onclick = function () {
    if (busy) return;
    history = [];
    save();
    render();
  };
  form.onsubmit = function (e) {
    e.preventDefault();
    var t = input.value;
    input.value = "";
    input.style.height = "";
    send(t);
  };
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      form.requestSubmit ? form.requestSubmit() : form.onsubmit(e);
    }
  });
  input.addEventListener("input", function () {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 100) + "px";
  });

  function mount() {
    document.body.appendChild(host);
    render();
    if (cfg.open) toggle(true);
  }
  if (document.body) mount(); else document.addEventListener("DOMContentLoaded", mount);

  // API for the host website: PropertyChat.open(), .close(), .ask("question")
  window.PropertyChat = {
    open: function () { toggle(true); },
    close: function () { toggle(false); },
    ask: function (q) { toggle(true); send(q); },
  };
})();
