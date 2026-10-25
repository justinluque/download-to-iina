const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
function setup(initialSettings = {}) {
  const settings = { ...initialSettings };
  const listeners = {};
  const subscribers = [];
  const sent = [];
  const badges = [];
  const timers = new Map();
  let timerId = 0;
  const connection = {
    onMessage: { addListener(fn) { listeners.native = fn; } },
    onDisconnect: { addListener(fn) { listeners.disconnect = fn; } },
    postMessage(message) { sent.push(message); },
  };
  const browser = {
    runtime: {
      async openOptionsPage() { listeners.optionsOpened = true; },
      connectNative() { return connection; },
      onMessage: { addListener(fn) { listeners.ui = fn; } },
      sendMessage(message) { for (const fn of subscribers) fn(message); return Promise.resolve(); },
    },
    storage: { local: {
      async get(defaults) { return { ...defaults, ...settings }; },
      async set(values) { Object.assign(settings, values); },
    } },
    browserAction: { setBadgeText({ text }) { badges.push(text); }, setBadgeBackgroundColor() {}, setTitle() {} },
    contextMenus: { create() {}, onClicked: { addListener(fn) { listeners.context = fn; } } },
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../../extension/background.js'), 'utf8'), {
    browser, URL, console,
    setTimeout(fn) { timers.set(++timerId, fn); return timerId; },
    clearTimeout(id) { timers.delete(id); },
  });
  const ui = message => listeners.ui(message);
  const state = () => ui({ type: 'getState' });
  const jobs = async () => (await state()).jobs;
  return { listeners, subscribers, sent, badges, ui, jobs, state, browser, timers };
}
module.exports = { setup };
