const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const { setup } = require('./helpers/browser.cjs');

class Element {
  constructor(tag) { this.tagName = tag; this.children = []; this.dataset = {}; this.attributes = {}; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  setAttribute(name, value) { this.attributes[name] = value; }
  focus() {}
}
async function openPanel(s, tab, hasMedia = true, player = null) {
  const nodes = Object.fromEntries(['jobs', 'notice', 'empty', 'error', 'preferences'].map(id => [id, new Element('div')]));
  const requests = [];
  const document = {
    activeElement: null,
    getElementById(id) { assert.ok(nodes[id], `Unknown element ${id}`); return nodes[id]; },
    createElement(tag) { return new Element(tag); },
    querySelectorAll() { return []; },
  };
  await vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../extension/popup.js'), 'utf8'), {
    document, URL,
    browser: {
      storage: s.browser.storage,
      tabs: {
        query: async () => tab ? [tab] : [],
        executeScript: async (id, { code }) => [vm.runInNewContext(code, {
          document: { querySelector: selector => selector === 'video' ? player : hasMedia },
        })],
      },
      runtime: {
        openOptionsPage: s.browser.runtime.openOptionsPage,
        onMessage: { addListener(fn) { s.subscribers.push(fn); } },
        async sendMessage(message) { requests.push(message); return s.ui(message); },
      },
    },
  });
  return { nodes, requests };
}
const media = { url: 'https://www.youtube.com/watch?v=example', title: 'Example video' };
test('disabling seek starts from the beginning without reading the player position', async () => {
  const s = setup({ seekToCurrentPosition: false });
  let reads = 0;
  await openPanel(s, media, true, { get currentTime() { reads++; return 93.125; } });
  assert.equal(reads, 0);
  assert.equal(s.sent[0].start, null);
});
test('popup preferences button opens the extension options page', async () => {
  const s = setup();
  const panel = await openPanel(s, { url: 'about:blank' });
  await panel.nodes.preferences.onclick();
  assert.equal(s.listeners.optionsOpened, true);
});
test('current video position reaches the helper and survives retry', async () => {
  const s = setup();
  await openPanel(s, media, true, { currentTime: 93.125 });
  assert.equal(s.sent[0].start, 93.125);
  s.listeners.native({ id: '1', status: 'error', message: 'Try again' });
  await s.ui({ type: 'retry' });
  assert.equal(s.sent[1].start, 93.125);
});
test('URL timestamps are ignored when no player position is available', async () => {
  const s = setup();
  await openPanel(s, { ...media, url: media.url + '&t=90' });
  assert.equal(s.sent[0].start, null);
});
test('opening the toolbar panel starts the download without another click', async () => {
  const s = setup();
  const panel = await openPanel(s, media);
  assert.equal(s.sent.length, 1);
  assert.equal(s.sent[0].url, media.url);
  assert.equal(panel.requests[0].type, 'download');
  assert.equal(panel.nodes.jobs.children.length, 1);
  assert.equal(panel.nodes.empty.hidden, true);
});
test('reopening the popup preserves the active download and displays live updates', async () => {
  const s = setup();
  await openPanel(s, media);
  const reopened = await openPanel(s, media);
  assert.equal(s.sent.length, 1);
  s.listeners.native({ id: '1', status: 'progress', phase: 'downloading', percent: 64, downloaded: 64, total: 100, speed: 10, eta: 4 });
  const row = reopened.nodes.jobs.children[0];
  assert.equal(row.children.find(node => node.tagName === 'progress').value, 64);
  assert.match(row.children.find(node => node.className === 'detail').textContent, /4s left/);
});
test('toolbar click on another media page queues it once', async () => {
  const s = setup();
  await openPanel(s, media);
  await openPanel(s, { url: 'https://example.com/video', title: 'Second video' });
  assert.equal(s.sent.length, 1);
  assert.equal((await s.jobs()).length, 2);
});
test('browser pages show active progress without trying to download an unsupported URL', async () => {
  const s = setup();
  const panel = await openPanel(s, { url: 'about:debugging', title: 'Debugging' });
  assert.equal(s.sent.length, 0);
  assert.equal(panel.requests[0].type, 'getState');
  assert.equal(panel.nodes.empty.hidden, false);
});
test('finished download leaves a brief confirmation and no history row', async () => {
  const s = setup();
  const panel = await openPanel(s, media);
  s.listeners.native({ id: '1', status: 'done', path: '/tmp/video.mp4' });
  assert.equal(panel.nodes.jobs.children.length, 0);
  assert.equal(panel.nodes.notice.children[0].textContent, 'Opened in IINA');
  for (const fn of [...s.timers.values()]) fn();
  assert.equal(panel.nodes.notice.hidden, true);
  assert.equal(panel.nodes.empty.hidden, false);
});
test('failure has retry and dismiss controls without a failed-download history list', async () => {
  const s = setup();
  const panel = await openPanel(s, media);
  s.listeners.native({ id: '1', status: 'error', message: 'Network failed' });
  assert.equal(panel.nodes.jobs.children.length, 0);
  const actions = panel.nodes.notice.children.find(node => node.className === 'notice-actions');
  assert.equal(actions.children[0].textContent, 'Retry');
  await actions.children[0].onclick();
  assert.equal(s.sent.length, 2);
  assert.equal(panel.nodes.jobs.children.length, 1);
  assert.equal(panel.nodes.notice.hidden, true);
});

test('opening progress on a non-media web page does not enqueue that page', async () => {
  const s = setup();
  await openPanel(s, media);
  const panel = await openPanel(s, {id: 2, url: 'https://github.com/justinluque/download-to-iina'}, false);
  assert.equal(s.sent.length, 1);
  assert.equal((await s.jobs()).length, 1);
  assert.equal(panel.nodes.jobs.children.length, 1);
});
test('a generic page containing a media element starts downloading on toolbar click', async () => {
  const s = setup();
  await openPanel(s, {id: 2, url: 'https://example.com/player', title: 'Embedded video'}, true);
  assert.equal(s.sent[0].url, 'https://example.com/player');
});
