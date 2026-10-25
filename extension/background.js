/* global browser */
const HOST_NAME = "io.iina.ytdlp_host";
let nativePort = null;
const jobs = [];
let nextId = 0;
let notice = null;
let noticeTimer = null;

function snapshot() { return { jobs: jobs.map(job => ({ ...job })), notice: notice && { ...notice } }; }
function publish() {
  const active = jobs.find(job => job.status === "active") || jobs[0];
  const text = active ? (Number.isFinite(active.percent) ? `${Math.floor(active.percent)}%` : "…")
    : notice?.kind === "error" ? "!" : notice?.kind === "success" ? "✓" : "";
  browser.browserAction.setBadgeText({ text });
  browser.browserAction.setBadgeBackgroundColor({ color: active ? "#3478f6" : notice?.kind === "error" ? "#c33d48" : "#25825d" });
  browser.browserAction.setTitle({ title: active ? `${active.title} — ${active.phase}` : "Download to IINA" });
  browser.runtime.sendMessage({ type: "state", ...snapshot() }).catch(() => {});
}
function setNotice(value) {
  clearTimeout(noticeTimer);
  notice = value;
  if (value && value.kind !== "error") {
    noticeTimer = setTimeout(() => { notice = null; publish(); }, 3000);
  }
}
function removeJob(job) {
  const index = jobs.indexOf(job);
  if (index >= 0) jobs.splice(index, 1);
}
function pump() {
  if (jobs.some(job => job.status === "active")) return;
  const job = jobs[0];
  if (!job) return;
  job.status = "active";
  job.phase = "Preparing…";
  try {
    if (!nativePort) connect();
    nativePort.postMessage({ id: job.id, url: job.url, start: job.start });
  } catch (error) {
    removeJob(job);
    setNotice({ kind: "error", url: job.url, title: job.title,
      message: `Could not start the helper. Run native-host/install.sh, then retry. ${error.message}` });
    pump();
  }
  publish();
}
function connect() {
  const connection = browser.runtime.connectNative(HOST_NAME);
  nativePort = connection;
  connection.onMessage.addListener(message => {
    const job = jobs.find(item => item.status === "active" && (!message.id || item.id === message.id));
    if (!job) return;
    if (message.title) job.title = message.title;
    if (message.status === "started" || message.status === "progress") {
      if (job.cancelling) return;
      if (message.status === "started" && !message.phase && !message.id) {
        job.warning = "Update the native helper and restart Firefox to see progress.";
      }
      Object.assign(job, {
        phase: { preparing: "Preparing…", downloading: "Downloading", processing: "Merging…", opening: "Opening in IINA…" }[message.phase] || "Downloading…",
        percent: Number.isFinite(message.percent) ? Math.max(0, Math.min(100, message.percent)) : null,
        speed: message.speed, eta: message.eta, downloaded: message.downloaded, total: message.total,
      });
    } else if (["done", "error", "cancelled"].includes(message.status)) {
      removeJob(job);
      if (message.status === "error") {
        setNotice({ kind: "error", url: job.url, title: job.title, start: job.start, message: message.message || "Download failed. Try again." });
      } else if (notice?.kind !== "error") {
        setNotice({ kind: message.status === "done" ? "success" : "info", message: message.status === "done" ? "Opened in IINA" : "Cancelled" });
      }
      pump();
    }
    publish();
  });
  connection.onDisconnect.addListener(() => {
    if (nativePort !== connection) return;
    nativePort = null;
    const error = browser.runtime.lastError;
    const job = jobs.find(item => item.status === "active");
    if (job) {
      const waiting = jobs.length - 1;
      setNotice({ kind: "error", url: job.url, title: job.title, start: job.start,
        message: `The helper disconnected. Run native-host/install.sh and restart Firefox, then retry. ${error?.message || ""}${waiting ? ` ${waiting} queued request(s) also stopped.` : ""}`.trim() });
      jobs.length = 0;
    }
    publish();
  });
}
function downloadAndOpen(url, title, start) {
  let parsed;
  try { parsed = new URL(url); } catch { throw new Error("Open an HTTP or HTTPS video page first."); }
  if (!["http:", "https:"].includes(parsed.protocol)) throw new Error("Open an HTTP or HTTPS video page first.");
  if (jobs.some(job => job.url === url)) return;
  if (jobs.length >= 20) throw new Error("The queue is full. Wait for a download to finish.");
  setNotice(null);
  jobs.push({ id: String(++nextId), url, title: title || parsed.hostname, start: Number.isFinite(start) && start > 0 ? start : null, status: "queued", phase: "Queued", percent: null });
  pump();
  publish();
}
function cancelJob(id) {
  const job = jobs.find(item => item.id === id);
  if (!job) return;
  if (job.status === "queued") {
    removeJob(job);
  } else {
    if (!nativePort) throw new Error("The helper is disconnected.");
    nativePort.postMessage({ action: "cancel", id });
    job.cancelling = true;
    job.phase = "Cancelling…";
  }
  publish();
}
browser.runtime.onMessage.addListener(message => {
  try {
    if (message.type === "getState") return Promise.resolve(snapshot());
    if (message.type === "download") downloadAndOpen(message.url, message.title, message.start);
    else if (message.type === "cancel") cancelJob(message.id);
    else if (message.type === "retry") {
      if (notice?.kind === "error" && notice.url) downloadAndOpen(notice.url, notice.title, notice.start);
    } else if (message.type === "dismiss") { setNotice(null); publish(); }
    else return undefined;
    return Promise.resolve(snapshot());
  } catch (error) { return Promise.resolve({ error: error.message }); }
});
const contexts = { page: "pageUrl", link: "linkUrl", video: "srcUrl", audio: "srcUrl" };
for (const context of Object.keys(contexts)) browser.contextMenus.create({
  id: `ytdlp_open_${context}`, title: `Download this ${context} & open in IINA`, contexts: [context],
});
browser.contextMenus.onClicked.addListener((info, tab) => {
  const context = info.menuItemId.replace("ytdlp_open_", "");
  if (!contexts[context]) return;
  try { downloadAndOpen(info[contexts[context]], context === "page" ? tab?.title : undefined); }
  catch (error) { setNotice({ kind: "error", message: error.message }); publish(); }
});
