import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import test from 'node:test'
import { effectScope, ref, watch } from 'vue'

// APIのみ差し替え、画面共通の数量処理とVueのリアクティビティを検証する。
const source = readFileSync(new URL('../src/composables/usePlanQuantityLocks.js', import.meta.url), 'utf8')
  .replace(/^import .*\r?\n/gm, '').replace('export function', 'function')
const create = new Function('ref', 'watch', 'api', `${source}\nreturn usePlanQuantityLocks`)

test('保存済み全ロット合計を固定し、解除・保存前の再ロックを制御する', async () => {
  const alerts = []
  globalThis.alert = message => alerts.push(message)
  const calls = []
  let savedQty = 30
  const day = '2026-09-14'
  const daily = { plan: 10, extraLots: [{ plan_qty: 20 }], plan_base: 30 }
  const rows = ref([{ product_id: 1, daily: { [day]: daily } }])
  const lineId = ref(1)
  const api = { productionLock: {
    list: async () => ({ data: [] }),
    lock: async payload => {
      if (payload.locked_qty !== savedQty) throw { response: { data: { detail: '計画を保存してください。' } } }
      calls.push(payload)
      return { data: { locked_qty: payload.locked_qty } }
    },
    unlock: async () => {},
  } }
  const scope = effectScope()
  const locks = scope.run(() => create(ref, watch, api)({
    lineId, startDate: ref(day), endDate: ref(day), rows, processing: ref(false),
  }))
  try {
    await locks.fetchLocks()
    await locks.toggleLock(day, 1)
    assert.equal(calls[0].locked_qty, 30)
    assert.equal(locks.isLocked(day, 1), true)
    rows.value[0].daily[day].plan = 100
    locks.applyQuantities()
    assert.equal(rows.value[0].daily[day].plan, 30)
    assert.deepEqual(rows.value[0].daily[day].extraLots, [])
    await locks.toggleLock(day, 1)
    rows.value[0].daily[day].plan = 40
    await locks.toggleLock(day, 1)
    assert.equal(calls.length, 1)
    assert.match(alerts[0], /保存/)
    savedQty = 40
    await locks.toggleLock(day, 1)
    assert.equal(calls[1].locked_qty, 40)
    lineId.value = 2
    assert.equal(locks.locksReady.value, false)
    assert.equal(locks.isLocked(day, 1), false)
  } finally { scope.stop(); delete globalThis.alert }
})

test('ゼロ固定・対象期間・取得失敗を扱う', async () => {
  const day = '2026-09-14'
  const next = '2026-09-15'
  const rows = ref([{ product_id: 1, daily: { [day]: { plan: 10 }, [next]: { plan: 20 } } }])
  let fail = false
  const api = { productionLock: { list: async () => {
    if (fail) throw new Error('通信失敗')
    return { data: [{ plan_date: day, product_id: 1, locked_qty: '0.00' },
      { plan_date: next, product_id: 1, locked_qty: '40.00' }] }
  } } }
  const scope = effectScope()
  const locks = scope.run(() => create(ref, watch, api)({
    lineId: ref(1), startDate: ref(day), endDate: ref(next), rows, processing: ref(false),
  }))
  try {
    await locks.fetchLocks()
    locks.applyQuantities(day, day)
    assert.equal(rows.value[0].daily[day].plan, 0)
    assert.equal(rows.value[0].daily[next].plan, 20)
    assert.equal(locks.hasLocksOnDate(day), true)
    fail = true
    await assert.rejects(locks.fetchLocks(), /通信失敗/)
    assert.equal(locks.locksReady.value, false)
    assert.throws(() => locks.applyQuantities(), /再取得/)
  } finally { scope.stop() }
})
