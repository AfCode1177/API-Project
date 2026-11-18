// All model output is rendered with textContent / text nodes, never innerHTML,
// so a malicious reply cannot inject HTML or scripts (XSS defense).
const log = document.getElementById("log");
const empty = document.getElementById("empty");
const form = document.getElementById("composer");
const box = document.getElementById("msg");
const send = document.getElementById("send");
const count = document.getElementById("count");

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
}

function inline(node, text) {
  text.split(/(\*\*[^*]+\*\*)/).forEach(part => {
    if (/^\*\*[^*]+\*\*$/.test(part)) node.append(el("strong", "", part.slice(2, -2)));
    else node.append(document.createTextNode(part));
  });
}

function renderRich(container, text) {
  let list = null;
  for (const raw of text.split("\n")) {
    const line = raw.trimEnd();
    const bullet = line.match(/^\s*[-*\u2022]\s+(.*)$/);
    if (bullet) {
      if (!list) { list = el("ul"); container.append(list); }
      const li = el("li"); inline(li, bullet[1]); list.append(li);
      continue;
    }
    list = null;
    if (!line.trim()) continue;
    const p = el("p");
    const head = line.match(/^#{1,4}\s+(.*)$/);
    if (head) p.append(el("strong", "", head[1])); else inline(p, line);
    container.append(p);
  }
}

function addUser(text) {
  empty.hidden = true;
  log.append(el("div", "msg user", text));
  log.scrollTop = log.scrollHeight;
}

function addBot(text, steps) {
  const m = el("div", "msg bot");
  renderRich(m, text);
  if (steps && steps.length) {
    const d = el("details", "steps");
    d.append(el("summary", "", `Agent steps (${steps.length} tool call${steps.length > 1 ? "s" : ""})`));
    const ol = el("ol");
    steps.forEach(s => {
      const li = el("li");
      li.append(el("code", "", `${s.tool}(${JSON.stringify(s.args).slice(0, 220)})`));
	  li.append(document.createElement("br"));
      li.append(el("code", "", "returned: " + JSON.stringify(s.result).slice(0, 300)));
      ol.append(li);
    });
    d.append(ol);
    m.append(d);
  }
  log.append(m);
  log.scrollTop = log.scrollHeight;
}

async function submit() {
  const text = box.value.trim();
  if (!text) return;
  addUser(text);
  box.value = ""; count.textContent = "0 / 2000";
  send.disabled = true;
  const pending = el("div", "msg bot pending", "Checking your routine…");
  log.append(pending); log.scrollTop = log.scrollHeight;
  try {
    const r = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const data = await r.json().catch(() => ({}));
    pending.remove();
    if (!r.ok) log.append(el("div", "msg error", data.error || "Something went wrong. Please try again."));
    else addBot(data.reply, data.steps);
  } catch {
    pending.remove();
    log.append(el("div", "msg error", "Couldn't reach the server. Check your connection and try again."));
  }
  send.disabled = false;
  log.scrollTop = log.scrollHeight;
  box.focus();
}

form.addEventListener("submit", e => { e.preventDefault(); submit(); });
box.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
});
box.addEventListener("input", () => { count.textContent = `${box.value.length} / 2000`; });
document.querySelectorAll(".example").forEach(b =>
  b.addEventListener("click", () => { box.value = b.textContent; box.dispatchEvent(new Event("input")); box.focus(); }));
document.getElementById("reset").addEventListener("click", async () => {
  await fetch("/reset", { method: "POST" }).catch(() => {});
  log.querySelectorAll(".msg").forEach(n => n.remove());
  empty.hidden = false;
});
