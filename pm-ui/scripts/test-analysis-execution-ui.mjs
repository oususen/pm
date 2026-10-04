// 実行・中止・結果・履歴の操作とVue SSR。AI・DB・Dockerへの接続は行わない。
import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import test from 'node:test'
import * as Vue from 'vue'
import { renderToString } from '@vue/server-renderer'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const filename = new URL('../src/views/ai/AIAnalysisExecution.vue', import.meta.url)
const parsed = parse(readFileSync(filename, 'utf8'), { filename: filename.pathname })
assert.deepEqual(parsed.errors, [])
const script = compileScript(parsed.descriptor, { id: 'execution-test' })
const template = compileTemplate({ source: parsed.descriptor.template.content, filename: filename.pathname, id: 'execution-test', compilerOptions: { bindingMetadata: script.bindings } })
assert.deepEqual(template.errors, [])
const names = Object.keys(script.bindings).filter(n => !['computed', 'onBeforeUnmount', 'onMounted', 'ref', 'watch', 'api', 'plan', 'canEdit', 'canViewAll', 'blocked'].includes(n))
const create = new Function('ref', 'computed', 'watch', 'onMounted', 'onBeforeUnmount', 'defineProps', 'defineEmits', 'api', 'window',
  parsed.descriptor.scriptSetup.content.replace(/^import .*\r?\n/gm, '') + `\nreturn {${names.join(',')}}`)
const render = new Function('Vue', template.code.replace(/import \{([^}]+)\} from "vue"/, (_, s) => `const {${s.replace(/ as /g, ':')}} = Vue`).replace('export function render', 'function render') + '\nreturn render')(Vue)
function plan() { return { id: 'plan', revision: 4, status: 'data_approved', codegen: { status: 'code_approved', executed_code_sha256: 'hash', trial: { status: 'passed', executed_code_sha256: 'hash' } } } }
function job(status = 'running') { return { id: 'job', executed_code_sha256: 'hash', status, scope: { date_from: '2026-09-01', date_to: '2026-09-30', conditions: '全行', datasets: [{ view: 'v_ai_shipment' }] }, counts: { v_ai_shipment: 3 }, cleanup: { db_connection: 'closed', container: 'closed' } } }
async function setup() {
  const props = Vue.reactive({ plan: plan(), canEdit: true, canViewAll: false, blocked: false }), calls = [], events = [], confirms = []
  const methods = {
    executionOptions: async () => ({ data: { ready: true, enabled: true } }), execute: async () => ({ data: job('pending') }),
    getJob: async () => ({ data: job() }), cancelJob: async () => ({ data: job('cancel_requested') }),
    runs: async () => ({ data: { results: [], count: 0, next: null, previous: null } }),
  }
  const api = { aiAnalysis: Object.fromEntries(Object.keys(methods).map(name => [name, async (...args) => { calls.push([name, ...args]); return methods[name](...args) }])) }
  const scope = Vue.effectScope()
  let mount, unmount
  const state = scope.run(() => create(Vue.ref, Vue.computed, Vue.watch, fn => { mount = fn }, fn => { unmount = fn }, () => props, () => (...args) => events.push(args), api, { confirm: text => { confirms.push(text); return true } }))
  await mount(); calls.length = 0
  return { state, props, calls, events, methods, confirms, unmount, stop: () => scope.stop() }
}
function html(f) { return renderToString(Vue.createSSRApp({ props: ['plan', 'canEdit', 'canViewAll', 'blocked'], setup: () => Object.fromEntries(Object.entries(f.state).map(([k, v]) => [k, Vue.unref(v)])), render }, f.props)) }

test('失敗だけ状態行・理由が同じ赤のクラス。固定文は維持しAPI理由本文を表示しない', async () => {
  const f = await setup()
  try {
    f.state.job.value = { ...job('failed'), reason: 'history_failed', detail: '<img src=x onerror=SECRET>' }
    const text = await html(f)
    assert.equal((text.match(/class="execution-failed"/g) || []).length, 2)
    assert.ok(text.includes('実行: 失敗'))
    assert.ok(text.includes('実行履歴の保存に失敗したため、結果を返しません。'))
    assert.equal(text.includes('SECRET'), false)
    for (const status of ['success', 'cancelled', 'running', 'pending', 'cancel_requested', 'unknown']) {
      f.state.job.value = { ...job(status), detail: '<b>注意</b>' }
      const other = await html(f)
      assert.equal(other.includes('class="execution-failed"'), false, status)
      assert.ok(other.includes('&lt;b&gt;注意&lt;/b&gt;'))
    }
  } finally { f.stop() }
})
test('結果形式の固定文・未知理由の汎用文、日時のローカル整形をSSRで確認', async () => {
  const f = await setup()
  try {
    f.state.job.value = { ...job('failed'), reason:'result_invalid', detail:'SECRET', created_at:'2026-10-04T09:10:11.123', finished_at:'2026-10-04T09:11:12' }
    let text = await html(f)
    assert.ok(text.includes('グラフの横軸(x)は値のリスト'))
    assert.ok(text.includes('開始受付: 2026-10-04 09:10:11 / 終了: 2026-10-04 09:11:12'))
    for (const reason of ['SECRET', '__proto__', null, {}]) {
      f.state.job.value.reason = reason
      text = await html(f)
      assert.ok(text.includes('失敗しました。詳細は理由コードを参照してください。'))
      assert.equal(text.includes('SECRET'), false)
    }
    f.state.job.value = { ...job('success'), result_expires_at:'2026-10-04T10:11:12', result:{tables:[],charts:[]} }
    assert.ok((await html(f)).includes('結果保持期限: 2026-10-04 10:11:12'))
  } finally { f.stop() }
})

test('承認・試行・ハッシュ・基盤・編集権限の前提が欠ければ実行しない', async () => {
  const f = await setup()
  try {
    for (const change of [() => { f.props.canEdit = false }, () => { f.props.blocked = true }, () => { f.state.availability.value.ready = false }, () => { f.props.plan.codegen.status = 'generated' }, () => { f.props.plan.codegen.trial.status = 'unverified' }, () => { f.props.plan.codegen.trial.executed_code_sha256 = 'wrong' }]) {
      f.props.plan = plan(); f.props.canEdit = true; f.props.blocked = false; f.state.availability.value.ready = true
      change(); await f.state.execute(); assert.equal(f.calls.length, 0)
    }
  } finally { f.stop() }
})
test('同時クリックでも実行要求1回。実行中は再生成禁止を親へ通知する', async () => {
  const f = await setup()
  try {
    await Promise.all([f.state.execute(), f.state.execute()]); await Vue.nextTick()
    assert.deepEqual(f.calls, [['execute', 'plan', { revision: 4, executed_code_sha256: 'hash' }]])
    assert.equal(f.state.active.value, true); assert.ok(f.events.some(e => e[0] === 'active' && e[1] === true))
    await f.state.execute(); assert.equal(f.calls.length, 1)
  } finally { f.stop() }
})
test('中止は明示確認後に1回だけ。受付後も中止完了とは表示しない', async () => {
  const f = await setup()
  try {
    f.state.job.value = job(); await Promise.all([f.state.cancel(), f.state.cancel()])
    assert.deepEqual(f.calls, [['cancelJob', 'job']]); assert.equal(f.confirms.length, 1)
    assert.ok((await html(f)).includes('停止・削除の完了はまだ確認していません'))
    assert.equal(f.state.active.value, true)
  } finally { f.stop() }
})
test('閲覧専用は実行・中止不可だが自分の履歴を取得できる', async () => {
  const f = await setup()
  try {
    f.props.canEdit = false; f.state.job.value = job(); f.state.includeAll.value = true
    await f.state.execute(); await f.state.cancel(); await f.state.loadHistory(1)
    assert.deepEqual(f.calls, [['runs', { page: 1, include_all: 'false' }]])
    assert.equal(f.confirms.length, 0)
  } finally { f.stop() }
})
test('管理者表示とページ送りは既存のページ番号方式。権限撤回後は全員表示を要求しない', async () => {
  const f = await setup()
  try {
    f.props.canViewAll = true; f.state.includeAll.value = true; await f.state.loadHistory(2)
    assert.deepEqual(f.calls[0], ['runs', { page: 2, include_all: 'true' }])
    f.props.canViewAll = false; await Vue.nextTick(); await new Promise(resolve => setImmediate(resolve))
    assert.equal(f.state.includeAll.value, false); assert.equal(f.calls.at(-1)[1].include_all, 'false')
  } finally { f.stop() }
})
test('実行要求の通信失敗は自動再送せず、状態未確認として親の操作も止める', async () => {
  const f = await setup()
  try {
    f.methods.execute = async () => { throw Error('SECRET') }; await f.state.execute(); await f.state.execute()
    assert.equal(f.calls.length, 1); assert.equal(f.state.active.value, true); assert.equal(f.state.fresh.value, false)
    assert.equal((await html(f)).includes('SECRET'), false)
  } finally { f.stop() }
})

test('基盤の確認成功だけでは実行状態の未確認を解除しない', async () => {
  const f = await setup()
  try {
    f.state.job.value = job(); f.state.fresh.value = false
    await f.state.checkAvailability()
    assert.equal(f.state.fresh.value, false); assert.equal(f.state.canCancel.value, false)
  } finally { f.stop() }
})

test('実行中による429の明示拒否は受付不明にせず、自動再送もしない', async () => {
  const f = await setup()
  try {
    f.methods.execute = async () => { throw { response: { status: 429 } } }
    await f.state.execute(); await f.state.execute()
    assert.equal(f.calls.length, 1); assert.equal(f.state.active.value, false)
    assert.equal(f.state.fresh.value, true); assert.equal(f.state.availability.value, null)
    assert.ok((await html(f)).includes('実行は受け付けられませんでした'))
  } finally { f.stop() }
})

test('管理者権限撤回後に遅れた全利用者の履歴が届いても表示しない', async () => {
  const f = await setup()
  try {
    let resolve
    f.props.canViewAll = true; f.state.includeAll.value = true
    f.methods.runs = () => new Promise(r => { resolve = r })
    const pending = f.state.loadHistory(1)
    f.props.canViewAll = false; await Vue.nextTick()
    resolve({ data: { results: [{ detail: 'OTHER-USER' }], count: 1 } }); await pending
    assert.deepEqual(f.state.history.value.results, [])
  } finally { f.stop() }
})
test('成功時だけ結果を表示。表・報告書はエスケープし、期間・条件・取得行数を併記', async () => {
  const f = await setup()
  try {
    const result = { tables: [{ name: '合計', columns: ['数量'], rows: [['<script>SECRET</script>']] }], charts: [], report: '<img src=x onerror=SECRET>' }
    f.state.job.value = { ...job('success'), result }
    const success = await html(f)
    assert.ok(success.includes('&lt;script&gt;')); assert.ok(success.includes('&lt;img')); assert.ok(success.includes('2026-09-01'))
    assert.ok(success.includes('取得行数: 3行')); assert.ok(success.includes('行数は数量の合計ではありません'))
    for (const status of ['failed', 'cancelled', 'unknown']) { f.state.job.value.status = status; assert.equal((await html(f)).includes('SECRET'), false) }
  } finally { f.stop() }
})
test('棒・折れ線をSVGで表示し、NULLは線をつながず、大きい配列でも上限の引数展開をしない', async () => {
  const f = await setup()
  try {
    const chart = { kind: 'bar', title: '数量', x: ['a', 'b', 'c'], series: [{ name: 's', values: [1, null, -2] }] }
    f.state.job.value = { ...job('success'), result: { tables: [], charts: [chart], report: null } }
    assert.ok((await html(f)).includes('<rect'))
    chart.kind = 'line'; f.state.job.value.result.charts = [chart]
    assert.equal(f.state.geometry(chart).segments[0].length, 2); assert.ok((await html(f)).includes('<polyline'))
    assert.equal(f.state.geometry({ ...chart, x: Array(150000), series: [{ values: Array(150000).fill(2) }] }).max, 2)
  } finally { f.stop() }
})
test('後始末未確認・状態不明は実行枠が開いたとは表示しない', async () => {
  const f = await setup()
  try {
    f.state.job.value = { ...job('cancelled'), cleanup: { db_connection: 'pending', container: 'unconfirmed' } }
    assert.equal(f.state.canExecute.value, false); assert.ok((await html(f)).includes('中止完了とは扱いません'))
    f.state.job.value = job('unknown'); assert.equal(f.state.canExecute.value, false)
  } finally { f.stop() }
})

test('再生成後のコードと過去の結果は、実行時のハッシュと不一致表示で区別する', async () => {
  const f = await setup()
  try {
    f.state.job.value = job('success'); f.props.plan.codegen.executed_code_sha256 = 'new-code'
    assert.ok((await html(f)).includes('現在表示されているSQL・Pythonは、この実行のコードとは異なります'))
  } finally { f.stop() }
})
test('画面破棄・案変更後に遅れて返った結果は採用しない', async () => {
  for (const dispose of [false, true]) {
    const f = await setup()
    try {
      let resolve
      f.state.job.value = job(); f.methods.getJob = () => new Promise(r => { resolve = r })
      const pending = f.state.refreshJob()
      if (dispose) f.unmount(); else { f.props.plan = { ...plan(), id: 'other' }; await Vue.nextTick() }
      resolve({ data: { ...job('success'), result: { report: 'LATE' } } }); await pending
      assert.notEqual(f.state.job.value?.status, 'success')
    } finally { f.stop() }
  }
})
