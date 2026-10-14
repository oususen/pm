import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import test from 'node:test'
import { computed, effectScope, nextTick, reactive, ref, watch } from 'vue'

// 実コンポーネントのscriptを読み、APIと画面外の依存だけ差し替える。
const source = readFileSync(new URL('../src/views/production/LaserWeeklyMaterialOrder.vue', import.meta.url), 'utf8')
  .match(/<script setup>([\s\S]*?)<\/script>/)[1]
  .replace(/^import .*\r?\n/gm, '')
const create = new Function('computed', 'onMounted', 'ref', 'watch', 'useRouter', 'api', 'authState',
  'defineProps', 'defineEmits', `${source}\nreturn { load, entries, manual, entry, demand, automatic, combinedProgress, progress, initials, isDateLocked };`)
const dates = ['2026-10-12', '2026-10-13', '2026-10-14', '2026-10-15', '2026-10-16', '2026-10-19']
const approval = (supplier = 'MEISEI', context = {}) => ({
  status: 'sent', context: { supplier, start_date: '2026-10-05', order_created: true,
    lock_start_date: dates[0], lock_end_date: dates[4], ...context },
})
const row = (day, supplier, order_lots, order_sheets = 0) => ({
  material_id: 1612, required_date: day, supplier, order_lots, order_sheets,
})
const fixture = ({ items = [], overlaps = [], lockedItems = [], current = {}, overlapping = [approval()], code = 'SS400 T6.0X1355X1956' } = {}) => {
  // 需要値・ロット倍数は計算経路を検証する合成データ。実DBへの接続・書き込みは行わない。
  const state = { items, overlaps, lockedItems, current, overlapping, loads: 0, calls: [] }
  const props = reactive({ startDate: dates[0], dates: [...dates], holidayWorkDates: [], materials: [{
    material_id: 1612, material_code: code, order_lot_multiple: 10,
    daily: Object.fromEntries(dates.map(day => [day, 3])),
  }] })
  const api = { laserWeeklyPlans: {
    getMaterialOrderProgress: async (...args) => {
      state.calls.push(args)
      return { data: { items: state.items, overlapping_items: state.overlaps, locked_items: state.lockedItems } }
    },
    getMaterialInitialProgress: async () => ({ data: [{ material_id: 1612, initial_progress: 0, is_locked: false }] }),
    getMaterialOrderApproval: async () => ({ data: { approvals: state.current, overlapping_approvals: state.overlapping } }),
    getMaterialOrderSummary: async () => { state.loads++; return { data: { rows: [], dates: [] } } },
  } }
  const scope = effectScope()
  const component = scope.run(() => create(computed, () => {}, ref, watch, () => ({}), api, { user: null }, () => props, () => () => {}))
  // deep watcherとloadのPromiseを実際のVueスケジューラで完了させる。
  const settle = async () => { await nextTick(); await new Promise(resolve => setImmediate(resolve)); await nextTick() }
  return { state, props, component, settle, material: props.materials[0], close: () => scope.stop() }
}

test('他週ロック中の未保存日14日は、上段変更によるdeep watcher再読込後も0', async () => {
  // plannerがDBで確認した材料1612の保存行（10/13:1L、10/15:1L+5枚、10/14:行なし）の写し。
  const f = fixture({ items: [row(dates[1], 'MEISEI', 1), row(dates[3], 'MEISEI', 1, 5)] })
  try {
    await f.settle()
    assert.equal(f.component.isDateLocked(dates[2], 'MEISEI'), true)
    assert.equal(f.component.manual(f.material, dates[2], 'MEISEI'), 0)
    assert.equal(f.component.entries.value[`1612:${dates[3]}`].meisei_sheets, 5)
    const before = f.state.loads
    const oldProgress = f.component.combinedProgress(f.material, dates[2])
    f.material.daily[dates[2]] = 13
    await f.settle()
    assert.ok(f.state.loads > before, 'materialsのdeep watcherでloadが再実行される')
    assert.deepEqual(f.state.calls.at(-1), [dates[0], dates[0], dates[5]])
    assert.equal(f.component.manual(f.material, dates[2], 'MEISEI'), 0)
    assert.equal(f.component.manual(f.material, dates[1], 'MEISEI'), 1)
    assert.equal(f.component.entries.value[`1612:${dates[1]}`].meisei_sheets, 0)
    assert.equal(f.component.manual(f.material, dates[3], 'MEISEI'), 1)
    assert.equal(f.component.entries.value[`1612:${dates[3]}`].meisei_sheets, 5)
    assert.equal(f.component.demand(f.material, dates[2]), 1.3)
    assert.equal(f.component.automatic(f.material, dates[2], 'MEISEI'), 1.3)
    assert.ok(Math.abs(f.component.combinedProgress(f.material, dates[2]) - (oldProgress - 1)) < 1e-9)
    assert.ok(Math.abs(f.component.progress(f.material, dates[2], 'MEISEI') - f.component.combinedProgress(f.material, dates[2])) < 1e-9)
    assert.equal(f.component.manual(f.material, dates[5], 'MEISEI'), 1)
    f.material.daily[dates[5]] = 23
    await f.settle()
    assert.equal(f.component.manual(f.material, dates[5], 'MEISEI'), 3)
  } finally { f.close() }
})

test('保存済み0・正数・端数を維持し、既存API配列の優先順を維持', async () => {
  const f = fixture({
    overlaps: [row(dates[0], 'MEISEI', 9, 9), row(dates[2], 'MEISEI', 2, 3)],
    items: [row(dates[0], 'MEISEI', 0, 4), row(dates[1], 'MEISEI', 7, 8)],
    lockedItems: [row(dates[1], 'MEISEI', 6, 5)],
  })
  try {
    await f.settle()
    f.material.daily[dates[0]] = 100
    f.material.daily[dates[1]] = 100
    await f.settle()
    assert.equal(f.component.manual(f.material, dates[0], 'MEISEI'), 0)
    assert.equal(f.component.entries.value[`1612:${dates[0]}`].meisei_sheets, 4)
    assert.equal(f.component.manual(f.material, dates[1], 'MEISEI'), 6)
    assert.equal(f.component.entries.value[`1612:${dates[1]}`].meisei_sheets, 5)
    assert.equal(f.component.manual(f.material, dates[2], 'MEISEI'), 2)
    assert.equal(f.component.entries.value[`1612:${dates[2]}`].meisei_sheets, 3)
  } finally { f.close() }
})

test('未ロックは従来の自動設定と佐藤商事配分を維持', async () => {
  const f = fixture({ overlapping: [], code: 'SPHC T2.3X1524X3048', items: [row(dates[2], 'SATO', 1, 2)] })
  try {
    await f.settle()
    f.material.daily[dates[2]] = 23
    await f.settle()
    assert.equal(f.component.manual(f.material, dates[2], 'SATO'), 1)
    assert.equal(f.component.entries.value[`1612:${dates[2]}`].sato_sheets, 2)
    assert.ok(Math.abs(f.component.automatic(f.material, dates[2], 'MEISEI') - 1.3) < 1e-9)
    assert.equal(f.component.manual(f.material, dates[2], 'MEISEI'), 2)
    f.material.daily[dates[2]] = 3
    await f.settle()
    assert.equal(f.component.manual(f.material, dates[2], 'MEISEI'), 0)
  } finally { f.close() }
})

test('納期調整中は期間内だけ自動設定し、保存後は再ロック', async () => {
  const adjustment = { editing: true, lock_start_date: dates[2], lock_end_date: dates[2] }
  const f = fixture({ overlapping: [], current: { MEISEI: approval('MEISEI', { material_order_adjustments: { MEISEI: adjustment } }) } })
  try {
    await f.settle()
    assert.equal(f.component.manual(f.material, dates[1], 'MEISEI'), 0)
    assert.equal(f.component.manual(f.material, dates[2], 'MEISEI'), 1)
    f.material.daily[dates[2]] = 23
    await f.settle()
    assert.equal(f.component.manual(f.material, dates[2], 'MEISEI'), 3)
    adjustment.editing = false
    await f.component.load()
    assert.equal(f.component.manual(f.material, dates[2], 'MEISEI'), 0)
  } finally { f.close() }
})

test('他週・他仕入先のoverlapロック条件を維持し、別承認ロックがあれば調整中でも0', async () => {
  const f = fixture({ overlapping: [approval('SATO')], current: { MEISEI: approval('MEISEI', {
    material_order_adjustments: { MEISEI: { editing: true, lock_start_date: dates[0], lock_end_date: dates[4] } },
  }) } })
  try {
    await f.settle()
    assert.equal(f.component.isDateLocked(dates[2], 'MEISEI'), true)
    assert.equal(f.component.manual(f.material, dates[2], 'MEISEI'), 0)
  } finally { f.close() }
})

test('entry未生成とmanual未定義の直接経路でもロックを適用し、保存値は保持', async () => {
  const f = fixture()
  try {
    await f.settle()
    delete f.component.entries.value[`1612:${dates[2]}`]
    assert.equal(f.component.entry(f.material, dates[2]).meisei_lots, 0)
    f.component.entries.value[`1612:${dates[2]}`] = { sato_lots: 1, meisei_sheets: 4 }
    assert.equal(f.component.manual(f.material, dates[2], 'MEISEI'), 0)
    f.component.entries.value[`1612:${dates[2]}`].meisei_lots = 2
    assert.equal(f.component.manual(f.material, dates[2], 'MEISEI'), 2)
    assert.equal(f.component.entry(f.material, dates[2]).meisei_sheets, 4)
    delete f.component.entries.value[`1612:${dates[5]}`]
    assert.equal(f.component.entry(f.material, dates[5]).meisei_lots, 1)
    f.component.entries.value[`1612:${dates[5]}`] = { sato_lots: 1 }
    f.material.daily[dates[5]] = 23
    // watcher実行前のmanual未定義経路。
    assert.equal(f.component.manual(f.material, dates[5], 'MEISEI'), 2)
    assert.equal(f.component.manual(f.material, dates[5], 'SATO'), 1)
  } finally { f.close() }
})
