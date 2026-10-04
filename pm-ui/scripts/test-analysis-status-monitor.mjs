// 偽タイマー・模擬GETだけで停止条件と競合を確認する。
import assert from 'node:assert/strict'
import test from 'node:test'
import { createAnalysisStatusMonitor, STATUS_LIMIT_MS } from '../src/composables/analysisStatusMonitor.js'
import { fakeClock, fakeDocument } from './analysis-status-test-helper.mjs'

function fixture() {
  const clock = fakeClock(), doc = fakeDocument(), calls = [], applied = [], errors = []
  const f = { response: async id => ({ id, status: 'running' }) }
  const monitor = createAnalysisStatusMonitor({ now: clock.now, later: clock.later, clear: clock.clear,
    request: (id, signal) => { calls.push({ id, signal, at: clock.now() }); return f.response(id, signal) },
    apply: data => applied.push(data), manualError: () => errors.push(true) })
  monitor.mount(doc)
  return { ...f, clock, doc, calls, applied, errors, monitor, setResponse: fn => { f.response = fn } }
}

test('進行中だけ3秒。応答完了後から待ち、GETを重ねない', async () => {
  for (const status of ['pending', 'running', 'cancel_requested']) {
    const f = fixture()
    try {
      let resolve
      f.setResponse(() => new Promise(r => { resolve = r }))
      f.monitor.track('job', status)
      await f.clock.advance(2999); assert.equal(f.calls.length, 0)
      await f.clock.advance(1); assert.equal(f.calls.length, 1)
      await f.clock.advance(15000); assert.equal(f.calls.length, 1)
      resolve({ id: 'job', status }); await f.clock.flush()
      await f.clock.advance(2999); assert.equal(f.calls.length, 1)
      await f.clock.advance(1); assert.equal(f.calls.length, 2)
    } finally { f.monitor.dispose() }
    assert.equal(f.clock.size(), 0); assert.equal(f.doc.listeners.size, 0)
  }
})

test('終了・unknownは停止。自動取得の変化だけ通知、初期終了は通知しない', async () => {
  for (const status of ['success', 'failed', 'cancelled', 'expired', 'unknown']) {
    const f = fixture()
    try {
      f.monitor.track('job', status); await f.clock.advance(6000)
      assert.equal(f.calls.length, 0); assert.equal(f.monitor.notice.value, null)
      f.monitor.track('other', 'running')
      f.setResponse(id => ({ id, status, cleanup: { db_connection: 'closed', container: 'closed' } }))
      await f.clock.advance(3000)
      assert.equal(f.monitor.notice.value.status, status)
      assert.equal(f.monitor.notice.value.cleanupComplete, true)
      assert.notEqual(f.monitor.message.value, '')
      await f.clock.advance(6000); assert.equal(f.calls.length, 1); assert.equal(f.clock.size(), 0)
    } finally { f.monitor.dispose() }
  }
})

test('3→6→12秒の失敗で停止。本文を出さず、手動成功だけ上限内で復帰する', async () => {
  const f = fixture()
  try {
    f.setResponse(() => { throw Error('SECRET') }); f.monitor.track('job', 'running')
    await f.clock.advance(3000); assert.equal(f.calls.length, 1)
    await f.clock.advance(5999); assert.equal(f.calls.length, 1)
    await f.clock.advance(1); assert.equal(f.calls.length, 2)
    await f.clock.advance(12000); assert.equal(f.calls.length, 3)
    assert.ok(f.monitor.message.value.includes('3回')); assert.equal(f.monitor.message.value.includes('SECRET'), false)
    assert.equal(f.errors.length, 0); assert.equal(f.clock.size(), 0)
    f.doc.hide(true); f.doc.hide(false); await f.clock.advance(3000); assert.equal(f.calls.length, 3)
    f.setResponse(id => ({ id, status: 'running' })); await f.monitor.read(true)
    await f.clock.advance(3000); assert.equal(f.calls.length, 5)
  } finally { f.monitor.dispose() }
})

test('404/410/401/403は即停止し、手動案内を表示する。枠・承認の変更はしない', async () => {
  for (const status of [404, 410, 401, 403]) {
    const f = fixture()
    try {
      f.monitor.track('job', 'running'); f.setResponse(() => { throw { response: { status } } })
      await f.clock.advance(3000); await f.clock.advance(30000)
      assert.equal(f.calls.length, 1); assert.equal(f.clock.size(), 0); assert.equal(f.applied.length, 0)
      assert.ok(f.monitor.message.value.includes('停止'))
    } finally { f.monitor.dispose() }
  }
})

test('document非表示と検索タブは一時停止、同じジョブを再表示時に1回取得する', async () => {
  const f = fixture()
  try {
    f.monitor.track('job', 'running'); f.doc.hide(true)
    assert.equal(f.clock.size(), 0); await f.clock.advance(6000); assert.equal(f.calls.length, 0)
    f.monitor.setVisible(false); f.doc.hide(false); await f.clock.advance(3000); assert.equal(f.calls.length, 0)
    f.monitor.setVisible(true); await f.clock.advance(0); assert.equal(f.calls.length, 1)
    f.monitor.setVisible(false); await f.clock.advance(3000); assert.equal(f.calls.length, 1)
    f.monitor.setVisible(true); await f.clock.advance(0); assert.equal(f.calls.length, 2)
  } finally { f.monitor.dispose() }
})

test('20分は非表示時間も含む。再表示・手動取得で上限を延ばさず、ジョブは中止しない', async () => {
  const f = fixture()
  try {
    f.monitor.track('job', 'pending'); await f.clock.advance(1000); f.doc.hide(true)
    await f.clock.advance(STATUS_LIMIT_MS - 1000); f.doc.hide(false); await f.clock.advance(0)
    assert.equal(f.calls.length, 0); assert.equal(f.clock.size(), 0)
    assert.ok(f.monitor.message.value.includes('上限20分'))
    await f.monitor.read(true); assert.equal(f.calls.length, 1)
    await f.clock.advance(3000); assert.equal(f.calls.length, 1)
    assert.ok(f.monitor.message.value.includes('実行を中止したわけではありません'))
  } finally { f.monitor.dispose() }
})

test('応答が止まっても20分で取得を中断し、遅い結果を採用しない', async () => {
  const f = fixture()
  try {
    let resolve; f.setResponse(() => new Promise(r => { resolve = r }))
    f.monitor.track('job', 'running'); await f.clock.advance(3000)
    await f.clock.advance(STATUS_LIMIT_MS - 3000)
    assert.equal(f.calls[0].signal.aborted, true); assert.equal(f.clock.size(), 0)
    resolve({ id: 'job', status: 'success' }); await f.clock.flush()
    assert.equal(f.applied.length, 0); assert.equal(f.monitor.notice.value, null)
  } finally { f.monitor.dispose() }
})

test('手動・自動は同じGETを共有し、確認操作の後は成功強調を始めない', async () => {
  const f = fixture()
  try {
    let resolve; f.setResponse(() => new Promise(r => { resolve = r }))
    f.monitor.track('job', 'running'); await f.clock.advance(3000)
    const manual = f.monitor.read(true); assert.equal(f.calls.length, 1)
    resolve({ id: 'job', status: 'success' }); await manual
    assert.equal(f.monitor.acknowledged.value, true); assert.equal(f.monitor.notice.value.status, 'success')
    assert.equal(f.clock.size(), 0)
  } finally { f.monitor.dispose() }
})

test('破棄・ジョブ切替・非表示・中止開始後の古い応答は適用しない', async () => {
  for (const action of ['dispose', 'switch', 'hide', 'cancel']) {
    const f = fixture()
    try {
      let resolve; f.setResponse(() => new Promise(r => { resolve = r }))
      f.monitor.track('job', 'running'); await f.clock.advance(3000)
      if (action === 'dispose') f.monitor.dispose()
      if (action === 'switch') f.monitor.track('other', 'pending')
      if (action === 'hide') f.doc.hide(true)
      if (action === 'cancel') { f.monitor.invalidate(); f.monitor.track('job', 'cancel_requested') }
      resolve({ id: 'job', status: 'success' }); await f.clock.flush()
      assert.equal(f.calls[0].signal.aborted, true); assert.equal(f.applied.length, 0); assert.equal(f.monitor.notice.value, null)
    } finally { f.monitor.dispose() }
    assert.equal(f.clock.size(), 0)
  }
})

test('ID不一致・未知の状態は停止し、未確認を成功扱いしない', async () => {
  for (const data of [{ id: 'wrong', status: 'success' }, { id: 'job', status: 'not_known' }]) {
    const f = fixture()
    try {
      f.setResponse(() => data); f.monitor.track('job', 'running'); await f.clock.advance(3000)
      assert.equal(f.monitor.notice.value, null); assert.equal(f.clock.size(), 0)
      assert.ok(f.monitor.message.value.includes('確認できない'))
    } finally { f.monitor.dispose() }
  }
})

test('取得予約直後の破棄は、GET送信前にも止める', async () => {
  const f = fixture()
  f.monitor.track('job', 'pending')
  const request = f.monitor.read(true)
  f.monitor.dispose(); await request
  assert.equal(f.calls.length, 0); assert.equal(f.clock.size(), 0)
})

test('自動GETへ合流した手動取得の失敗も手動エラーを返し、古い通知は状態変更時に消す', async () => {
  const f = fixture()
  try {
    let reject; f.setResponse(() => new Promise((_, r) => { reject = r }))
    f.monitor.track('job', 'running'); await f.clock.advance(3000)
    const manual = f.monitor.read(true); reject(Error('SECRET')); await manual
    assert.equal(f.errors.length, 1)
    f.setResponse(id => ({ id, status: 'unknown' })); await f.clock.advance(6000)
    assert.equal(f.monitor.notice.value.status, 'unknown')
    f.setResponse(id => ({ id, status: 'running' })); await f.monitor.read(true)
    assert.equal(f.monitor.notice.value, null)
    await f.clock.advance(3000); assert.equal(f.calls.length, 4)
  } finally { f.monitor.dispose() }
})

test('復元したジョブIDの初回照合に失敗したら、進行中と推測せず取得を停止する', async () => {
  const f = fixture()
  try {
    f.setResponse(() => { throw Error('未確認') }); f.monitor.track('job')
    await f.clock.advance(0); await f.clock.advance(30000)
    assert.equal(f.calls.length, 1); assert.equal(f.clock.size(), 0)
    assert.ok(f.monitor.message.value.includes('実行状態を確認できない'))
  } finally { f.monitor.dispose() }
})
