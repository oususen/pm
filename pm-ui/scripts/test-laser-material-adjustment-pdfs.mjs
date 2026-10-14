import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import test from 'node:test'
import { computed, effectScope, nextTick, reactive, ref, watch } from 'vue'
import { compileTemplate, parse } from '@vue/compiler-sfc'

// 実コンポーネントのscriptを使用し、API・ブラウザだけを差し替える。DBへの書き込みは行わない。
const sfc = readFileSync(new URL('../src/views/production/LaserWeeklyMaterialOrder.vue', import.meta.url), 'utf8')
const source = sfc.match(/<script setup>([\s\S]*?)<\/script>/)[1].replace(/^import .*\r?\n/gm, '')
const create = new Function('computed', 'onMounted', 'ref', 'watch', 'useRouter', 'api', 'authState',
  'defineProps', 'defineEmits', 'window', `${source}\nreturn { adjustmentPdfDialog, adjustmentPdfSupplier, adjustmentPdfOptions, adjustmentPdfSelection, adjustmentPdfLoading, adjustmentPdfError, selectedAdjustmentPdf, closeAdjustmentPdfDialog, openAdjustmentPdfDialog, openAdjustmentPdf };`)
const pdf = (id = 14, start = '2026-10-12', end = '2026-10-16') => ({
  approval_id: id, start_date: start, end_date: end,
  saved_at: '2026-10-14T09:30:00', url: `/media/adjustment-${id}.pdf`,
})
const deferred = () => { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no }); return { promise, resolve, reject } }
const fixture = async (handler = async () => ({ data: { items: [] } })) => {
  const calls = [], opened = []
  const props = reactive({ startDate: '2026-10-12', dates: ['2026-10-12', '2026-10-16'], materials: [], holidayWorkDates: [] })
  const methods = {
    getMaterialOrderProgress: { items: [], overlapping_items: [], locked_items: [] },
    getMaterialInitialProgress: [], getMaterialOrderApproval: { approvals: {}, overlapping_approvals: [] },
    getMaterialOrderSummary: { rows: [], dates: [] },
  }
  const api = { laserWeeklyPlans: new Proxy({}, { get: (_, method) => async (...args) => {
    calls.push([method, ...args])
    if (method === 'getMaterialOrderAdjustmentPdfs') return handler(...args)
    assert.ok(method in methods, `想定外のAPI呼び出し: ${method}`)
    return { data: methods[method] }
  } }) }
  const scope = effectScope()
  const component = scope.run(() => create(computed, () => {}, ref, watch, () => ({}), api,
    { user: null }, () => props, () => () => {}, { open: (...args) => opened.push(args) }))
  await nextTick(); await new Promise(resolve => setImmediate(resolve)); await nextTick()
  return { component, calls, opened, close: () => scope.stop() }
}

test('表示週外を含む全期間GETを仕入先ごとに呼び、明示選択を待つ', async () => {
  const rows = [pdf(), pdf(8, '2026-09-28', '2026-10-02')]
  const f = await fixture(async supplier => ({ data: { items: supplier === 'MEISEI' ? rows : [] } }))
  try {
    await f.component.openAdjustmentPdfDialog('MEISEI')
    assert.deepEqual(f.component.adjustmentPdfOptions.value, rows)
    assert.equal(f.component.selectedAdjustmentPdf.value, undefined)
    f.component.openAdjustmentPdf()
    assert.equal(f.opened.length, 0)
    f.component.adjustmentPdfSelection.value = 8
    assert.equal(f.component.selectedAdjustmentPdf.value.saved_at, rows[1].saved_at)
    f.component.openAdjustmentPdf()
    assert.deepEqual(f.opened, [[rows[1].url, '_blank', 'noopener']])
    await f.component.openAdjustmentPdfDialog('SATO')
    assert.deepEqual(f.component.adjustmentPdfOptions.value, [])
    assert.equal(f.component.adjustmentPdfSelection.value, '')
    assert.deepEqual(f.calls.filter(([method]) => method === 'getMaterialOrderAdjustmentPdfs'), [
      ['getMaterialOrderAdjustmentPdfs', 'MEISEI'], ['getMaterialOrderAdjustmentPdfs', 'SATO'],
    ])
    assert.equal(f.calls.some(([method]) => /export|save|post/i.test(method)), false)
  } finally { f.close() }
})

test('読込中・取得失敗・空状態を分離し、閉じて再開すると再取得する', async () => {
  const pending = deferred()
  let count = 0
  const f = await fixture(() => ++count === 1 ? pending.promise : Promise.resolve({ data: { items: [] } }))
  try {
    const load = f.component.openAdjustmentPdfDialog('SATO')
    assert.equal(f.component.adjustmentPdfLoading.value, true)
    f.component.openAdjustmentPdf()
    pending.reject(new Error('network'))
    await load
    assert.equal(f.component.adjustmentPdfLoading.value, false)
    assert.ok(f.component.adjustmentPdfError.value)
    f.component.openAdjustmentPdf()
    assert.equal(f.opened.length, 0)
    f.component.closeAdjustmentPdfDialog()
    assert.equal(f.component.adjustmentPdfError.value, '')
    await f.component.openAdjustmentPdfDialog('SATO')
    assert.deepEqual(f.component.adjustmentPdfOptions.value, [])
    assert.equal(f.component.adjustmentPdfError.value, '')
    assert.equal(count, 2)
  } finally { f.close() }
})

for (const staleFailure of [false, true]) {
  test(`仕入先切替後の古い${staleFailure ? '失敗' : '成功'}応答を破棄する`, async () => {
    const pending = deferred()
    const f = await fixture(supplier => supplier === 'MEISEI' ? pending.promise : Promise.resolve({ data: { items: [pdf(9)] } }))
    try {
      const old = f.component.openAdjustmentPdfDialog('MEISEI')
      await f.component.openAdjustmentPdfDialog('SATO')
      if (staleFailure) pending.reject(new Error('stale')); else pending.resolve({ data: { items: [pdf(8)] } })
      await old
      assert.deepEqual(f.component.adjustmentPdfOptions.value.map(row => row.approval_id), [9])
      assert.equal(f.component.adjustmentPdfError.value, '')
      assert.equal(f.component.adjustmentPdfLoading.value, false)
    } finally { f.close() }
  })
}

test('閉じた後の応答と同仕入先再開前の応答を破棄し、選択を消す', async () => {
  const pending = [deferred(), deferred()]
  let count = 0
  const f = await fixture(() => pending[count++].promise)
  try {
    const old = f.component.openAdjustmentPdfDialog('MEISEI')
    f.component.closeAdjustmentPdfDialog()
    const latest = f.component.openAdjustmentPdfDialog('MEISEI')
    pending[0].resolve({ data: { items: [pdf(8)] } }); await old
    assert.deepEqual(f.component.adjustmentPdfOptions.value, [])
    assert.equal(f.component.adjustmentPdfLoading.value, true)
    pending[1].resolve({ data: { items: [pdf(14)] } }); await latest
    f.component.adjustmentPdfSelection.value = 14
    f.component.closeAdjustmentPdfDialog()
    assert.deepEqual(f.component.adjustmentPdfOptions.value, [])
    assert.equal(f.component.selectedAdjustmentPdf.value, undefined)
  } finally { f.close() }
})

test('templateは期間select・保存日時・状態別表示・開く無効化を備えVueコンパイルが通る', () => {
  const template = parse(sfc).descriptor.template.content
  assert.match(template, /openAdjustmentPdfDialog\('SATO'\)/)
  assert.match(template, /openAdjustmentPdfDialog\('MEISEI'\)/)
  assert.match(template, /select v-model="adjustmentPdfSelection"/)
  assert.match(template, /保存日時: {{ selectedAdjustmentPdf.saved_at }}/)
  assert.match(template, /v-if="adjustmentPdfLoading"/)
  assert.match(template, /v-else-if="adjustmentPdfError"/)
  assert.match(template, /保存済みの納期変更PDFはありません/)
  assert.match(template, /:disabled="!selectedAdjustmentPdf \|\| adjustmentPdfLoading \|\| !!adjustmentPdfError"/)
  assert.match(template, /@click.self="closeAdjustmentPdfDialog"/)
  const compiled = compileTemplate({ source: template, filename: 'LaserWeeklyMaterialOrder.vue', id: 'adjustment-pdf-test' })
  assert.deepEqual(compiled.errors, [])
})
