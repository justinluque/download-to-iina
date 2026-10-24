const { test } = require('node:test');
const assert = require('node:assert/strict');
const { setup } = require('./helpers/browser.cjs');

test('queue is serial; progress survives reopening; completed downloads are removed; late messages are ignored', async () => {
  const s = setup();
  await s.ui({ type: 'download', url: 'https://example.com/one', title: 'One' });
  await s.ui({ type: 'download', url: 'https://example.com/two', title: 'Two' });
  assert.equal(s.sent.length, 1);
  s.listeners.native({ id: '1', status: 'progress', phase: 'downloading', percent: 42, speed: 100, eta: 8 });
  assert.equal((await s.jobs())[0].percent, 42);
  assert.equal(s.badges.at(-1), '42%');
  s.listeners.native({ id: '1', status: 'done', path: '/tmp/one' });
  assert.equal(s.sent.length, 2);
  assert.equal((await s.jobs()).length, 1);
  assert.equal((await s.jobs())[0].id, '2');
  assert.equal((await s.jobs())[0].status, 'active');
  s.listeners.native({ id: '1', status: 'error', message: 'stale' });
  assert.equal((await s.state()).notice.kind, 'success');
});
test('duplicate URLs do not download twice; invalid URLs never reach helper', async () => {
  const s = setup();
  await s.ui({ type: 'download', url: 'https://example.com/a' });
  await s.ui({ type: 'download', url: 'https://example.com/a' });
  assert.equal((await s.jobs()).length, 1);
  for (const url of ['file:///etc/passwd', 'about:blank', 'javascript:alert(1)', 'bogus']) assert.ok((await s.ui({ type: 'download', url })).error);
  assert.equal(s.sent.length, 1);
});
test('cancel removes queued work immediately and waits for active subprocess cancellation', async () => {
  const s = setup();
  for (const suffix of ['a', 'b', 'c']) await s.ui({ type: 'download', url: `https://example.com/${suffix}` });
  await s.ui({ type: 'cancel', id: '2' });
  assert.equal((await s.jobs()).some(job => job.id === '2'), false);
  await s.ui({ type: 'cancel', id: '1' });
  assert.equal(s.sent.at(-1).action, 'cancel');
  assert.equal((await s.jobs())[0].phase, 'Cancelling…');
  s.listeners.native({ id: '1', status: 'progress', phase: 'downloading', percent: 5 });
  assert.equal((await s.jobs())[0].phase, 'Cancelling…');
  s.listeners.native({ id: '1', status: 'cancelled' });
  assert.equal(s.sent.at(-1).id, '3');
  assert.equal((await s.jobs()).length, 1);
});
test('disconnect clears interrupted requests, exposes setup guidance, and allows retry', async () => {
  const s = setup();
  await s.ui({ type: 'download', url: 'https://example.com/a' });
  await s.ui({ type: 'download', url: 'https://example.com/b' });
  s.listeners.disconnect();
  assert.equal((await s.jobs()).length, 0);
  assert.match((await s.state()).notice.message, /install.sh/);
  await s.ui({ type: 'retry' });
  assert.equal((await s.jobs())[0].status, 'active');
  assert.equal((await s.jobs())[0].url, 'https://example.com/a');
  assert.equal((await s.state()).notice, null);
});
test('no history or saved paths remain after many successful downloads; completion feedback expires', async () => {
  const s = setup();
  for (let i = 0; i < 40; i++) {
    await s.ui({ type: 'download', url: `https://example.com/${i}` });
    s.listeners.native({ id: String(i + 1), status: 'done', path: `/private/${i}.mp4` });
    assert.equal((await s.jobs()).length, 0);
  }
  assert.equal(JSON.stringify(await s.state()).includes('/private'), false);
  for (const fn of [...s.timers.values()]) fn();
  assert.equal((await s.state()).notice, null);
  assert.equal(s.badges.at(-1), '');
});
test('only one actionable error is retained; dismiss removes it; subsequent downloads can finish', async () => {
  const s = setup();
  await s.ui({ type: 'download', url: 'https://example.com/a' });
  await s.ui({ type: 'download', url: 'https://example.com/b' });
  s.listeners.native({ id: '1', status: 'error', message: 'First failed' });
  assert.equal((await s.jobs())[0].id, '2');
  s.listeners.native({ id: '2', status: 'done' });
  assert.equal((await s.state()).notice.message, 'First failed');
  await s.ui({ type: 'dismiss' });
  assert.equal((await s.state()).notice, null);
  assert.equal((await s.jobs()).length, 0);
});
test('outdated native helper displays upgrade guidance', async () => {
  const s = setup();
  await s.ui({ type: 'download', url: 'https://example.com/video' });
  s.listeners.native({ status: 'started' });
  assert.match((await s.jobs())[0].warning, /restart Firefox/);
  assert.equal((await s.jobs())[0].percent, null);
});
