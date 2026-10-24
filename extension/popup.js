/* global browser */
const $ = id => document.getElementById(id);
let initialized = false;
function bytes(value) {
  if (!Number.isFinite(value)) return "";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) { value /= 1024; unit++; }
  return `${value.toFixed(unit ? 1 : 0)} ${units[unit]}`;
}
function showError(text) { $("error").textContent = text || ""; $("error").hidden = !text; }
function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
async function command(message) {
  try {
    const response = await browser.runtime.sendMessage(message);
    if (response?.error) showError(response.error);
    else { showError(""); if (response?.jobs) render(response); }
  } catch { showError("Could not connect. Close this panel and try again."); }
}
function render({ jobs, notice }) {
  const focused = document.activeElement?.dataset?.action;
  const container = $("jobs");
  container.replaceChildren();
  for (const job of jobs) {
    const row = element("article", "job");
    const heading = element("div", "job-heading");
    heading.append(element("h2", "job-title", job.title));
    const cancel = element("button", "cancel", "×");
    cancel.dataset.action = `cancel-${job.id}`;
    cancel.disabled = !!job.cancelling;
    cancel.setAttribute("aria-label", `Cancel ${job.title}`);
    cancel.title = "Cancel download";
    cancel.onclick = () => command({ type: "cancel", id: job.id });
    heading.append(cancel);
    row.append(heading);
    const status = element("div", "job-status");
    status.append(element("span", "", job.phase));
    if (Number.isFinite(job.percent)) status.append(element("span", "percent", `${Math.floor(job.percent)}%`));
    row.append(status);
    if (job.status === "active") {
      const progress = element(Number.isFinite(job.percent) ? "progress" : "div", Number.isFinite(job.percent) ? "" : "activity");
      progress.setAttribute("aria-label", `Download progress for ${job.title}`);
      if (Number.isFinite(job.percent)) { progress.max = 100; progress.value = job.percent; }
      else {
        progress.setAttribute("role", "progressbar");
        progress.setAttribute("aria-valuetext", job.phase);
        progress.append(element("span"));
      }
      row.append(progress);
      const details = [];
      if (Number.isFinite(job.downloaded)) details.push(`${bytes(job.downloaded)}${job.total ? ` / ${bytes(job.total)}` : ""}`);
      if (job.speed) details.push(`${bytes(job.speed)}/s`);
      if (Number.isFinite(job.eta)) details.push(job.eta < 60 ? `${Math.ceil(job.eta)}s left` : `${Math.ceil(job.eta / 60)}m left`);
      if (details.length && job.phase === "Downloading") row.append(element("p", "detail", details.join(" · ")));
    }
    if (job.warning) row.append(element("p", "warning", job.warning));
    container.append(row);
  }
  const noticeElement = $("notice");
  noticeElement.replaceChildren();
  noticeElement.hidden = !notice;
  noticeElement.className = notice ? `notice-${notice.kind}` : "";
  if (notice) {
    noticeElement.append(element("p", "notice-label", notice.kind === "error" ? "Download failed" : notice.message));
    if (notice.kind === "error") {
      noticeElement.append(element("p", "notice-message", notice.message));
      const actions = element("div", "notice-actions");
      for (const type of notice.url ? ["retry", "dismiss"] : ["dismiss"]) {
        const button = element("button", "", type === "retry" ? "Retry" : "Dismiss");
        button.dataset.action = type;
        button.onclick = () => command({ type });
        actions.append(button);
      }
      noticeElement.append(actions);
    }
  }
  $("empty").hidden = !!(jobs.length || notice || !initialized);
  $("empty").textContent = "Open a video page, then click the toolbar button.";
  if (focused) [...document.querySelectorAll("button")].find(button => button.dataset.action === focused)?.focus({ preventScroll: true });
}
async function isMediaPage(tab) {
  const url = new URL(tab.url);
  const host = url.hostname.replace(/^www\./, "");
  if ((/(^|\.)youtube\.com$/.test(host) && ((url.pathname === "/watch" && url.searchParams.has("v")) || /^\/(shorts|live|embed)\//.test(url.pathname))) ||
      (host === "youtu.be" && url.pathname.length > 1) ||
      (/(^|\.)vimeo\.com$/.test(host) && /\/\d+(?:\/|$)/.test(url.pathname)) ||
      /\.(mp4|webm|mkv|mov|mp3|m4a|ogg|wav|m3u8|mpd)$/i.test(url.pathname)) return true;
  try {
    const [found] = await browser.tabs.executeScript(tab.id, {
      code: `Boolean(document.querySelector('video, audio, meta[property="og:video"], meta[property="og:video:url"], meta[property="og:video:secure_url"]'))`,
    });
    return found === true;
  } catch { return false; }
}
// Opening the toolbar popup is the download action. Background deduplication
// makes reopening it safe while the same URL is already downloading or queued.
browser.runtime.onMessage.addListener(message => { if (message.type === "state") render(message); });
(async () => {
  try {
    const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
    initialized = true;
    $("empty").hidden = true;
    if (tab && /^https?:\/\//i.test(tab.url || "") && await isMediaPage(tab)) {
      await command({ type: "download", url: tab.url, title: tab.title });
    } else {
      await command({ type: "getState" });
    }
  } catch { initialized = true; showError("Could not read this tab. Open a video page and try again."); $("empty").hidden = true; }
})();
