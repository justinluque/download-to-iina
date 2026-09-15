const HOST_NAME = "io.iina.ytdlp_host";

let port = null;

function setBadge(text, color) {
  browser.browserAction.setBadgeText({ text });
  if (color) browser.browserAction.setBadgeBackgroundColor({ color });
}

function connect() {
  port = browser.runtime.connectNative(HOST_NAME);

  port.onMessage.addListener((msg) => {
    const { status, message } = msg;
    if (status === "started") {
      setBadge("…", "#f0ad4e"); // …
    } else if (status === "done") {
      setBadge("✓", "#5cb85c"); // ✓
      setTimeout(() => setBadge(""), 3000);
    } else if (status === "error") {
      setBadge("!", "#d9534f");
      console.error("iina-ytdlp-host error:", message);
    }
  });

  port.onDisconnect.addListener(() => {
    port = null;
    if (browser.runtime.lastError) {
      console.error("Native host disconnected:", browser.runtime.lastError.message);
      setBadge("!", "#d9534f");
    }
  });
}

function downloadAndOpen(url) {
  if (!url) return;
  if (!port) connect();
  port.postMessage({ url });
}

const dict = {
  page: "pageUrl",
  link: "linkUrl",
  video: "srcUrl",
  audio: "srcUrl",
};

Object.keys(dict).forEach((item) => {
  browser.contextMenus.create({
    title: `Download this ${item} (yt-dlp) & open in IINA`,
    id: `ytdlp_open_${item}`,
    contexts: [item],
  });
});

browser.contextMenus.onClicked.addListener((info) => {
  if (info.menuItemId.startsWith("ytdlp_open_")) {
    const key = info.menuItemId.slice("ytdlp_open_".length);
    const url = info[dict[key]];
    downloadAndOpen(url);
  }
});

browser.browserAction.onClicked.addListener((tab) => {
  downloadAndOpen(tab.url);
});
