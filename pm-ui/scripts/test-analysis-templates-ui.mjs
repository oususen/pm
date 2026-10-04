// テンプレートの保存・一覧・詳細の操作とVue SSR。AI・DB・Dockerへの接続は行わない。
import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import test from 'node:test'
import * as Vue from 'vue'
import { renderToString } from '@vue/server-renderer'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { useAnalysisErrorNotices } from '../src/composables/analysisErrorNotices.js'
import { AnalysisErrorBanner } from './analysis-error-banner-test-helper.mjs'

const filename = new URL('../src/views/ai/AIAnalysisTemplates.vue', import.meta.url)
const parsed = parse(readFileSync(filename, 'utf8'), { filename: filename.pathname })
assert.deepEqual(parsed.errors, [])
const script = compileScript(parsed.descriptor, { id: 'templates-test' })
const template = compileTemplate({ source: parsed.descriptor.template.content, filename: filename.pathname, id: 'templates-test', compilerOptions: { bindingMetadata: script.bindings } })
assert.deepEqual(template.errors, [])
const names = Object.keys(script.bindings).filter(n => !['computed', 'onBeforeUnmount', 'onMounted', 'ref', 'watch', 'api', 'plan', 'canEdit', 'canReview', 'blocked', 'reuseBlocked'].includes(n))
const create = new Function('ref', 'computed', 'watch', 'onMounted', 'onBeforeUnmount', 'defineProps', 'defineEmits', 'api', 'window', 'AnalysisErrorBanner', 'useAnalysisErrorNotices',
  parsed.descriptor.scriptSetup.content.replace(/^import .*\r?\n/gm, '') + `\nreturn {${names.join(',')}}`)
const render = new Function('Vue', template.code.replace(/import \{([^}]+)\} from "vue"/, (_, s) => `const {${s.replace(/ as /g, ':')}} = Vue`).replace('export function render', 'function render') + '\nreturn render')(Vue)

const PYTHON = "emit_table('日別', ['日'], [['1']])"
function plan(extra = {}) { return { id: 'plan-1', revision: 6, status: 'data_approved', codegen: { status: 'code_approved', executed_code_sha256: 'hash', python: PYTHON, steps: [] }, ...extra } }
function row(id, extra = {}) { return { id, name: `分析${id}`, purpose: `目的${id}`, status: 'pending_admin', status_label: '管理者承認待ち', created_by: 'tester', created_at: '2026-10-04T10:20:30', content_visible: true, ...extra } }
const page = results => ({ results, count: results.length, next: null, previous: null })
async function setup(propsInit = {}, methodsInit = {}) {
  const props = Vue.reactive({ plan: plan(), canEdit: true, canReview: false, blocked: false, reuseBlocked: false, ...propsInit }), calls = [], confirms = [], consent = { value: true }, events = []
  const methods = {
    templates: async () => ({ data: page([row(1)]) }),
    saveTemplate: async () => ({ data: { ...row(2), version: 1, created: true } }),
    createTemplatePlan: async id => ({ data: { id: 'new-plan', template: { id, version: 1, status: 'approved' }, proposal: { provider: 'template' } } }),
    approveTemplate: async id => ({ data: { ...row(id), status: 'approved' } }),
    rejectTemplate: async id => ({ data: { ...row(id), status: 'rejected' } }),
    template: async id => ({ data: { ...row(id), date_from: '2026-01-01', date_to: '2026-01-31', conditions: '全行', procedure: ['集計', '表'], sql_steps: [{ name: 'w_a', query: 'SELECT 1' }], python_code: PYTHON, executed_code_sha256: 'hash', wrapper_version: 'w1' } }),
    ...methodsInit,
  }
  const api = { aiAnalysis: Object.fromEntries(Object.keys(methods).map(name => [name, async (...args) => { calls.push([name, ...args]); return methods[name](...args) }])) }
  const scope = Vue.effectScope()
  let mount, unmount
  const state = scope.run(() => create(Vue.ref, Vue.computed, Vue.watch, fn => { mount = fn }, fn => { unmount = fn }, () => props, () => (...args) => events.push(args), api, { confirm: text => { confirms.push(text); return consent.value } }, AnalysisErrorBanner, useAnalysisErrorNotices))
  await mount(); await Promise.resolve()
  return { state, props, calls, confirms, consent, events, stop: () => { unmount(); scope.stop() } }
}
function html(f) { return renderToString(Vue.createSSRApp({ props: ['plan', 'canEdit', 'canReview', 'blocked', 'reuseBlocked'], setup: () => Object.fromEntries(Object.entries(f.state).map(([k, v]) => [k, Vue.unref(v)])), render }, f.props)) }

test('表示時に一覧を取得し、保存済みがなければ空の案内を出す', async () => {
  const f = await setup({}, { templates: async () => ({ data: page([]) }) })
  try {
    assert.deepEqual(f.calls.map(c => c[0]), ['templates'])
    assert.ok((await html(f)).includes('保存済みのテンプレートはありません'))
  } finally { f.stop() }
})

test('保存は確認チェック後だけ。送るのは分析案IDと版だけで、コード・承認者は送らない。保存後に一覧を取り直す', async () => {
  const f = await setup()
  try {
    f.calls.length = 0
    await f.state.save()
    assert.deepEqual(f.calls, [], '確認前は保存しない')
    f.state.accepted.value = true
    await f.state.save()
    assert.deepEqual(f.calls.map(c => c[0]), ['saveTemplate', 'templates'])
    assert.deepEqual(f.calls[0][1], { plan_id: 'plan-1', revision: 6 })
    assert.equal(f.state.accepted.value, false)
    const text = await html(f)
    assert.ok(text.includes('保存しました')); assert.ok(text.includes('テンプレート2 / 版1 / 管理者承認待ち'))
  } finally { f.stop() }
})

test('既存の保存結果(created=false)は「保存済み」と表示する', async () => {
  const f = await setup({}, { saveTemplate: async () => ({ data: { ...row(5), version: 1, created: false } }) })
  try {
    f.state.accepted.value = true; await f.state.save()
    assert.ok((await html(f)).includes('保存済みです'))
  } finally { f.stop() }
})

test('承認前・権限なし・操作中は保存できず、画面に理由を出す', async () => {
  for (const [init, expected] of [
    [{ plan: plan({ status: 'awaiting_data' }) }, 'データ範囲が未承認'],
    [{ plan: plan({ codegen: { status: 'generated' } }) }, 'コードが未承認'],
    [{ plan: null }, '分析案なし'],
  ]) {
    const f = await setup(init)
    try {
      f.calls.length = 0; f.state.accepted.value = true; await f.state.save()
      assert.deepEqual(f.calls, []); assert.ok((await html(f)).includes(expected))
    } finally { f.stop() }
  }
  const viewOnly = await setup({ canEdit: false })
  try {
    viewOnly.calls.length = 0; viewOnly.state.accepted.value = true; await viewOnly.state.save()
    assert.deepEqual(viewOnly.calls, [])
    const text = await html(viewOnly)
    assert.ok(text.includes('閲覧のみです')); assert.equal(text.includes('テンプレートとして保存</button>'), false)
  } finally { viewOnly.stop() }
  const blocked = await setup({ blocked: true })
  try { blocked.calls.length = 0; blocked.state.accepted.value = true; await blocked.state.save(); assert.deepEqual(blocked.calls, []) } finally { blocked.stop() }
})

test('保存失敗はステータスごとの固定文だけを表示し、APIの本文・内部情報を出さない', async () => {
  for (const [status, text] of [[403, '権限がありません'], [409, '保存できる状態ではありません'], [410, '期限が切れました'], [500, '保存されたか一覧で確認してください']]) {
    const f = await setup({}, { saveTemplate: async () => { throw { response: { status, data: { detail: 'SECRET-DETAIL <b>' } } } } })
    try {
      f.state.accepted.value = true; await f.state.save()
      assert.ok(f.state.error.value.includes(text), String(status))
      assert.equal(f.state.error.value.includes('SECRET'), false)
      assert.equal(f.state.busy.value, '')
      assert.equal(f.state.saved.value, null)
    } finally { f.stop() }
  }
})

test('分析案または版が変わると、確認と保存結果を取り直す', async () => {
  const f = await setup()
  try {
    f.state.accepted.value = true; await f.state.save(); f.state.accepted.value = true
    assert.ok(f.state.saved.value)
    f.props.plan = plan({ revision: 7 }); assert.equal(f.state.accepted.value, false); assert.equal(f.state.saved.value, null)
    f.state.saved.value = { id: 1 }
    f.props.plan = plan({ id: 'plan-2' }); assert.equal(f.state.saved.value, null)
    f.state.accepted.value = true; f.props.canEdit = false; assert.equal(f.state.accepted.value, false)
  } finally { f.stop() }
})

test('保存中に分析案が切り替わったら、前の分析案の保存結果を新しい分析案の下に出さない(一覧は取り直す)', async () => {
  let release
  const gate = new Promise(resolve => { release = resolve })
  const f = await setup({}, { saveTemplate: async () => { await gate; return { data: { ...row(8), version: 1, created: true } } } })
  try {
    f.calls.length = 0
    f.state.accepted.value = true
    const pending = f.state.save()
    f.props.plan = plan({ id: 'plan-2' })
    release(); await pending
    assert.equal(f.state.saved.value, null)
    assert.equal(f.state.error.value, '')
    assert.deepEqual(f.calls.map(c => c[0]), ['saveTemplate', 'templates'])
    // 同じ分析案で版だけが変わった場合も同じ
    const g = await setup({}, { saveTemplate: async () => { await gate; return { data: { ...row(9), version: 1, created: true } } } })
    try {
      g.state.accepted.value = true
      const second = g.state.save()
      g.props.plan = plan({ revision: 7 })
      await second
      assert.equal(g.state.saved.value, null)
    } finally { g.stop() }
  } finally { f.stop() }
})

test('他の利用者のテンプレートは名称・目的・状態だけ。全文は作成者・管理者の行だけ詳細表示できる', async () => {
  const f = await setup({}, { templates: async () => ({ data: page([row(1), row(2, { content_visible: false })]) }) })
  try {
    const text = await html(f)
    assert.ok(text.includes('分析1')); assert.ok(text.includes('分析2'))
    assert.equal((text.match(/詳細を表示/g) || []).length, 1)
    assert.equal((text.match(/作成者と管理者だけが確認できます/g) || []).length, 1)
    // 1件につき段落は1つ(UIは1行にまとめる)。ラベル(状態・作成者・保存日時・目的)は省略しない
    assert.equal((text.match(/<article>/g) || []).length, 2)
    const articles = text.split('<article>').slice(1)
    for (const article of articles) {
      assert.equal((article.split('</article>')[0].match(/<p>/g) || []).length, 1)
      for (const label of ['状態: ', '作成者: ', '保存日時: ', '目的: ']) assert.ok(article.includes(label), label)
    }
    assert.equal(text.includes('emit_table'), false)
    await f.state.showDetail(1)
    const shown = await html(f)
    for (const part of ['emit_table', 'w_a: SELECT 1', '全行', '集計 → 表', '2026-01-01', 'w1']) assert.ok(shown.includes(part), part)
  } finally { f.stop() }
  // 全文が返らなかった(内容を見られない)応答は表示しない
  const hidden = await setup({}, { template: async id => ({ data: row(id, { content_visible: false }) }) })
  try { await hidden.state.showDetail(1); assert.equal(hidden.state.detail.value, null) } finally { hidden.stop() }
})

test('名称・目的にHTMLがあっても解釈しない', async () => {
  const f = await setup({}, { templates: async () => ({ data: page([row(1, { name: '<img src=x onerror=SECRET>', purpose: '<script>alert(1)</script>' })]) }) })
  try {
    const text = await html(f)
    assert.equal(text.includes('<img'), false); assert.equal(text.includes('<script>'), false)
    assert.ok(text.includes('&lt;img'))
  } finally { f.stop() }
})

test('一覧・詳細の取得失敗は固定文で、ページ番号は失敗したページへ進まない', async () => {
  const f = await setup({}, { templates: async params => { if (params.page === 3) throw new Error('SECRET'); return { data: { results: [row(params.page)], count: 61, next: 'n', previous: params.page > 1 ? 'p' : null } } } })
  try {
    await f.state.load(2); assert.equal(f.state.page.value, 2)
    const text = await html(f); assert.ok(text.includes('61件 / 2ページ'))
    await f.state.load(3)
    assert.equal(f.state.error.value, 'テンプレートの一覧を取得できませんでした。'); assert.equal(f.state.page.value, 2)
  } finally { f.stop() }
  const g = await setup({}, { template: async () => { throw new Error('SECRET') } })
  try { await g.state.showDetail(1); assert.equal(g.state.error.value, 'テンプレートの詳細を取得できませんでした。') } finally { g.stop() }
})

const pending = (id, extra = {}) => ({ ...row(id), state_revision: 3, status: 'pending_admin', replaces: null, date_from: '2026-01-01', date_to: '2026-01-31', conditions: '全行', procedure: ['集計'], sql_steps: [{ name: 'w_a', query: 'SELECT 1' }], python_code: PYTHON, executed_code_sha256: 'hash', wrapper_version: 'w1', reviewed_by: null, reviewed_at: null, rejection_reason: '', replacement_id: null, ...extra })

test('管理者だけが承認・却下の操作を見られる。一般の利用者には出ない', async () => {
  const admin = await setup({ canReview: true }, { template: async id => ({ data: pending(id) }) })
  const user = await setup({ canReview: false }, { template: async id => ({ data: pending(id) }) })
  try {
    await admin.state.showDetail(1); await user.state.showDetail(1)
    const adminText = await html(admin), userText = await html(user)
    assert.ok(adminText.includes('承認（正式にする）')); assert.ok(adminText.includes('>却下<')); assert.ok(adminText.includes('状態の絞り込み'))
    for (const word of ['承認（正式にする）', '>却下<', '状態の絞り込み', '却下理由（']) assert.equal(userText.includes(word), false, word)
    // 一般の利用者の画面からは、操作しても何も呼ばない
    user.calls.length = 0; await user.state.approve(); await user.state.reject()
    assert.deepEqual(user.calls, [])
  } finally { admin.stop(); user.stop() }
})

test('承認は確認後に、詳細で見た状態の版つきで呼び、成否にかかわらず一覧と詳細を取り直す', async () => {
  const f = await setup({ canReview: true }, { template: async id => ({ data: pending(id) }) })
  try {
    await f.state.showDetail(1)
    f.calls.length = 0
    f.consent.value = false; await f.state.approve()
    assert.deepEqual(f.calls, [], '確認を断ったら何も呼ばない'); assert.equal(f.confirms.length, 1)
    f.consent.value = true; await f.state.approve()
    assert.deepEqual(f.calls.map(c => c[0]), ['approveTemplate', 'templates', 'template'])
    assert.deepEqual(f.calls[0].slice(1), [1, { state_revision: 3 }])
    assert.equal(f.state.busy.value, '')
  } finally { f.stop() }
})

test('却下は理由が必須で、最大長を超える入力は送らない。理由は却下の呼び出しにだけ使う', async () => {
  const f = await setup({ canReview: true }, { template: async id => ({ data: pending(id) }) })
  try {
    await f.state.showDetail(1); f.calls.length = 0
    f.state.reason.value = '   '; await f.state.reject(); assert.deepEqual(f.calls, [])
    f.state.reason.value = 'あ'.repeat(501); await f.state.reject(); assert.deepEqual(f.calls, [])
    f.state.reason.value = '内容が不十足'; await f.state.reject()
    assert.deepEqual(f.calls.map(c => c[0]), ['rejectTemplate', 'templates', 'template'])
    assert.deepEqual(f.calls[0].slice(1), [1, { state_revision: 3, reason: '内容が不十足' }])
    assert.equal(f.state.reason.value, '')
  } finally { f.stop() }
})

test('承認・却下の失敗は固定文で、状態の競合(409)でも最新の状態を取り直す', async () => {
  for (const [status, text] of [[403, '権限がありません'], [409, '状態が変わりました'], [400, '却下理由は必須'], [500, '一覧で状態を確認してください']]) {
    const f = await setup({ canReview: true }, { template: async id => ({ data: pending(id) }), approveTemplate: async () => { throw { response: { status, data: { detail: 'SECRET-DETAIL' } } } } })
    try {
      await f.state.showDetail(1); f.calls.length = 0
      await f.state.approve()
      assert.ok(f.state.error.value.includes(text), String(status)); assert.equal(f.state.error.value.includes('SECRET'), false)
      assert.deepEqual(f.calls.map(c => c[0]), ['approveTemplate', 'templates', 'template'])
      assert.equal(f.state.busy.value, '')
    } finally { f.stop() }
  }
})

test('却下された版の訂正版は、確認チェック後に、置き換え元つきで保存できる。管理者以外には出ない', async () => {
  const rejected = id => pending(id, { status: 'rejected', status_label: '却下', rejection_reason: '<b>理由</b>', reviewed_by: 'admin', reviewed_at: '2026-10-05T01:02:03' })
  const f = await setup({ canReview: true }, { template: async id => ({ data: rejected(id) }) })
  const user = await setup({ canReview: false }, { template: async id => ({ data: rejected(id) }) })
  try {
    await f.state.showDetail(1); await user.state.showDetail(1)
    const text = await html(f)
    assert.ok(text.includes('この版の訂正版として保存')); assert.ok(text.includes('却下理由: &lt;b&gt;理由&lt;/b&gt;')); assert.equal(text.includes('<b>理由'), false)
    assert.equal((await html(user)).includes('この版の訂正版として保存'), false)
    f.calls.length = 0
    await f.state.saveCorrection(4); assert.deepEqual(f.calls, [], '確認チェック前は保存しない')
    f.state.accepted.value = true // 通常の保存の確認は、訂正版の保存の確認にならない
    await f.state.saveCorrection(1); assert.deepEqual(f.calls, [], '通常の確認チェックで訂正版を保存しない')
    f.state.acceptedCorrection.value = true
    await f.state.saveCorrection(MouseEventLike()); assert.deepEqual(f.calls, [], 'イベントを置き換え元として送らない')
    await f.state.saveCorrection(1)
    assert.deepEqual(f.calls[0].slice(1), [{ plan_id: 'plan-1', revision: 6, replaces: 1 }])
    assert.equal(f.state.acceptedCorrection.value, false); assert.equal(f.state.accepted.value, true, '訂正版の保存は通常の確認を消費しない')
    // 通常の保存には、置き換え元を含めない。訂正版の確認は通常の保存にならない
    f.state.acceptedCorrection.value = true; f.state.accepted.value = false; f.calls.length = 0; await f.state.save(); assert.deepEqual(f.calls, [])
    f.state.accepted.value = true; await f.state.save()
    assert.deepEqual(f.calls[0].slice(1), [{ plan_id: 'plan-1', revision: 6 }])
  } finally { f.stop(); user.stop() }
})

function MouseEventLike() { return { type: 'click' } }

test('状態の絞り込みは、一覧の取得に状態を渡す(管理者)', async () => {
  const f = await setup({ canReview: true })
  try {
    f.calls.length = 0
    f.state.statusFilter.value = 'rejected'
    await new Promise(resolve => setTimeout(resolve, 0))
    assert.deepEqual(f.calls[0], ['templates', { page: 1, status: 'rejected' }])
  } finally { f.stop() }
})

test('確認済みの版では、承認・却下の操作を出さず、置換先と確認情報を表示する', async () => {
  const f = await setup({ canReview: true }, { template: async id => ({ data: pending(id, { status: 'superseded', status_label: '置換済み', replacement_id: 9, reviewed_by: 'admin', reviewed_at: '2026-10-05T01:02:03' }) }) })
  try {
    await f.state.showDetail(1)
    const text = await html(f)
    assert.equal(text.includes('承認（正式にする）'), false); assert.ok(text.includes('置換先: テンプレート9')); assert.ok(text.includes('確認者: admin'))
  } finally { f.stop() }
})

test('承認・却下に失敗したときは入力した却下理由を残し、成功したときだけ消す', async () => {
  const f = await setup({ canReview: true }, { template: async id => ({ data: pending(id) }), rejectTemplate: async () => { throw { response: { status: 409, data: {} } } } })
  try {
    await f.state.showDetail(1)
    f.state.reason.value = '入力した理由'
    await f.state.reject()
    assert.equal(f.state.reason.value, '入力した理由'); assert.ok(f.state.error.value.includes('状態が変わりました'))
  } finally { f.stop() }
  const g = await setup({ canReview: true }, { template: async id => ({ data: pending(id) }) })
  try {
    await g.state.showDetail(1)
    g.state.reason.value = '入力した理由'
    await g.state.reject()
    assert.equal(g.state.reason.value, ''); assert.equal(g.state.error.value, '')
  } finally { g.stop() }
})

test('分析案が変わると、通常の保存と訂正版の保存の確認チェックを両方取り直す', async () => {
  const f = await setup({ canReview: true })
  try {
    f.state.accepted.value = true; f.state.acceptedCorrection.value = true
    f.props.plan = plan({ revision: 8 })
    assert.equal(f.state.accepted.value, false); assert.equal(f.state.acceptedCorrection.value, false)
    f.state.accepted.value = true; f.state.acceptedCorrection.value = true; f.props.canEdit = false
    assert.equal(f.state.accepted.value, false); assert.equal(f.state.acceptedCorrection.value, false)
  } finally { f.stop() }
})

test('再利用: 全文を見られる正式・管理者承認待ちの行だけに「分析案を作る」を出し、未承認には警告を出す', async () => {
  const f = await setup({ plan: null }, { templates: async () => ({ data: page([
    row(1, { status: 'approved', status_label: '正式' }), row(2, { status: 'pending_admin' }), row(3, { status: 'rejected', status_label: '却下' }),
    row(4, { content_visible: false }), row(5, { status: 'superseded', status_label: '置換済み' })]) }) })
  try {
    const text = await html(f)
    assert.equal((text.match(/このテンプレートで分析案を作る/g) || []).length, 2, '正式と管理者承認待ち(全文を見られる行)だけ')
    assert.equal((text.match(/システム管理者未承認/g) || []).length, 1)
    f.props.canEdit = false
    assert.equal((await html(f)).includes('このテンプレートで分析案を作る</button>'), false, '閲覧のみでは出さない')
  } finally { f.stop() }
})

test('再利用: 分析案を作ると親へ渡し、AIは使わない。現在の分析案があれば確認し、断れば何もしない', async () => {
  const f = await setup({ plan: null })
  try {
    f.calls.length = 0
    await f.state.startPlan(row(1, { status: 'approved' }))
    assert.deepEqual(f.calls, [['createTemplatePlan', 1]])
    assert.equal(f.events.length, 1); assert.equal(f.events[0][0], 'plan-created'); assert.equal(f.events[0][1].template.id, 1)
    assert.equal(f.state.busy.value, '')
  } finally { f.stop() }
  const g = await setup({ plan: plan() })
  try {
    g.calls.length = 0; g.consent.value = false
    await g.state.startPlan(row(1)); assert.deepEqual(g.calls, []); assert.equal(g.confirms.length, 1)
    g.consent.value = true
    await g.state.startPlan(row(1)); assert.deepEqual(g.calls, [['createTemplatePlan', 1]])
  } finally { g.stop() }
})

test('再利用: 実行中・権限なし・全文が見えない・却下の行では作らない。失敗は固定文で、APIの本文を出さない', async () => {
  for (const [init, target] of [[{ reuseBlocked: true }, row(1)], [{ canEdit: false }, row(1)], [{ blocked: true }, row(1)], [{}, row(1, { content_visible: false })], [{}, row(1, { status: 'rejected' })]]) {
    const f = await setup(init)
    try { f.calls.length = 0; await f.state.startPlan(target); assert.deepEqual(f.calls, []); assert.deepEqual(f.events, []) } finally { f.stop() }
  }
  for (const [status, text] of [[403, '作成者と管理者だけ'], [404, '見つかりません'], [409, '再利用できません'], [500, '作成できませんでした']]) {
    const f = await setup({ plan: null }, { createTemplatePlan: async () => { throw { response: { status, data: { detail: 'SECRET-DETAIL' } } } } })
    try {
      await f.state.startPlan(row(1))
      assert.ok(f.state.error.value.includes(text), String(status)); assert.equal(f.state.error.value.includes('SECRET'), false)
      assert.deepEqual(f.events, []); assert.equal(f.state.busy.value, '')
    } finally { f.stop() }
  }
})
