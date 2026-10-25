const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const { setup } = require('./helpers/browser.cjs');

async function openPreferences(s) {
  const nodes = { seek: { disabled: true }, status: {} };
  await vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../extension/options.js'), 'utf8'), {
    document: { getElementById: id => nodes[id] }, browser: s.browser,
  });
  return nodes;
}

test('seek defaults to enabled and a disabled preference survives reopening', async () => {
  const s = setup();
  const first = await openPreferences(s);
  assert.equal(first.seek.checked, true);
  assert.equal(first.seek.disabled, false);
  first.seek.checked = false;
  await first.seek.onchange();
  const reopened = await openPreferences(s);
  assert.equal(reopened.seek.checked, false);
  reopened.seek.checked = true;
  await reopened.seek.onchange();
  assert.equal((await openPreferences(s)).seek.checked, true);
});

test('failed save restores the stored preference and allows retry', async () => {
  const s = setup();
  const page = await openPreferences(s);
  s.browser.storage.local.set = async () => { throw new Error('Storage unavailable'); };
  page.seek.checked = false;
  await page.seek.onchange();
  assert.equal(page.seek.checked, true);
  assert.equal(page.seek.disabled, false);
  assert.match(page.status.textContent, /Could not save/);
});

test('failed preference load prevents accidentally overwriting an unknown setting', async () => {
  const s = setup();
  s.browser.storage.local.get = async () => { throw new Error('Storage unavailable'); };
  const page = await openPreferences(s);
  assert.equal(page.seek.disabled, true);
  assert.match(page.status.textContent, /Could not load/);
});
