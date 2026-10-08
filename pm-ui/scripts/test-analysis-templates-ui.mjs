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
function plan(extra = {}) { return { id: 'plan-1', revision: 6, status: 'data_approved', proposal: { title: '日別出荷の分析' }, codegen: { status: 'code_approved', executed_code_sha256: 'hash', python: PYTHON, steps: [] }, ...extra } }
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
  state.category.value = 'shipment' // 保存のテストは、カテゴリを選んだ状態から始める(必須の確認は別のテスト)
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
    assert.deepEqual(f.calls[0][1], { plan_id: 'plan-1', revision: 6, category: 'shipment', name: '日別出荷の分析' })
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

test('テンプレートから作成した分析案では、保存の欄を出さず、保存も呼ばない(重複の防止)', async () => {
  const f = await setup({ plan: plan({ template: { id: 7, version: 1, status: 'approved' } }) })
  try {
    f.calls.length = 0
    assert.equal(f.state.savable.value, false)
    f.state.accepted.value = true; f.state.acceptedCorrection.value = true
    await f.state.save(); await f.state.saveCorrection(1)
    assert.deepEqual(f.calls, [])
    const text = await html(f)
    assert.ok(text.includes('テンプレートから作成した分析案は、テンプレートとして保存できません'))
    assert.equal(text.includes('テンプレートとして保存</button>'), false)
    assert.equal(text.includes('コードを確認し、管理者承認待ちのテンプレートとして保存します'), false)
    // 通常の分析案では、従来どおり保存の欄が出る
    f.props.plan = plan()
    assert.equal(f.state.savable.value, true)
    assert.ok((await html(f)).includes('テンプレートとして保存</button>'))
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
    assert.deepEqual(f.calls[0].slice(1), [{ plan_id: 'plan-1', revision: 6, category: 'shipment', name: '日別出荷の分析', replaces: 1 }])
    assert.equal(f.state.acceptedCorrection.value, false); assert.equal(f.state.accepted.value, true, '訂正版の保存は通常の確認を消費しない')
    // 通常の保存には、置き換え元を含めない。訂正版の確認は通常の保存にならない
    f.state.acceptedCorrection.value = true; f.state.accepted.value = false; f.calls.length = 0; await f.state.save(); assert.deepEqual(f.calls, [])
    f.state.category.value = 'shipment' // 保存の後はカテゴリを選び直す
    f.state.accepted.value = true; await f.state.save()
    assert.deepEqual(f.calls[0].slice(1), [{ plan_id: 'plan-1', revision: 6, category: 'shipment', name: '日別出荷の分析' }])
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

test('左のメインの見出しは、右の段階(①〜⑤)と紛らわしい番号を付けない(BOSS指摘 2026-10-05)', async () => {
  const f = await setup()
  try {
    const text = await html(f)
    assert.ok(text.includes('<h2>テンプレート</h2>'))
    assert.equal(/<h2>\d+\. /.test(text), false, '番号つきの見出しがない')
  } finally { f.stop() }
})

test('通知の記録は、詳細に、種別・手段・宛先・結果・理由つきで1行ずつ表示する。記録がなければ案内、作成者・管理者以外(notificationsなし)には出さない(3-C)', async () => {
  const records = [
    { id: 1, kind_label: '確認依頼', channel_label: 'メール', recipient: 'rv-admin', status_label: '送信済み', reason_label: '', created_at: '2026-10-05T15:00:01' },
    { id: 2, kind_label: '確認依頼', channel_label: 'メール', recipient: 'rv-admin2', status_label: '送れない', reason_label: 'メールアドレスが未登録です', created_at: '2026-10-05T15:00:02' },
    { id: 3, kind_label: '承認', channel_label: 'PM通知', recipient: '<b>x</b>', status_label: '送信済み', reason_label: '', created_at: '2026-10-05T15:10:00' },
  ]
  const f = await setup({ canReview: true }, { template: async id => ({ data: { ...pending(id), notifications: records } }) })
  const none = await setup({ canReview: true }, { template: async id => ({ data: { ...pending(id), notifications: [] } }) })
  const hidden = await setup({ canReview: false }, { template: async id => ({ data: pending(id) }) })
  try {
    await f.state.showDetail(1); await none.state.showDetail(1); await hidden.state.showDetail(1)
    const text = (await html(f)).replace(/<!--.*?-->/g, '') // SSRの条件分岐の目印(コメント)を除いて比べる
    assert.ok(text.includes('確認依頼 / メール / 宛先: rv-admin / 結果: 送信済み / 記録: 2026-10-05 15:00:01'))
    assert.ok(text.includes('宛先: rv-admin2 / 結果: 送れない / 理由: メールアドレスが未登録です'))
    assert.ok(text.includes('承認 / PM通知 / 宛先: &lt;b&gt;x&lt;/b&gt;')); assert.equal(text.includes('<b>x</b>'), false)
    assert.ok((await html(none)).includes('まだ通知の記録はありません'))
    assert.equal((await html(hidden)).includes('通知（メール・PM通知'), false)
  } finally { f.stop(); none.stop(); hidden.stop() }
})

test('管理者の確認欄に、通知について事実と合わない文言(まだ送りません)を出さない(3-C)', async () => {
  const f = await setup({ canReview: true }, { template: async id => ({ data: pending(id) }) })
  try {
    await f.state.showDetail(1)
    const text = await html(f)
    assert.ok(text.includes('管理者の確認:')); assert.equal(text.includes('まだ送りません'), false)
  } finally { f.stop() }
})

test('通知の再送: 再送できる行(can_resend)にだけボタンを出し、確認の後に1回だけ送り、記録を取り直す。入力中の却下理由は消さない', async () => {
  const records = [
    { id: 11, kind_label: '確認依頼', channel_label: 'メール', recipient: 'rv-admin', status_label: '失敗', reason_label: '送信に失敗、または結果が不明です', created_at: '2026-10-05T15:00:01', can_resend: true },
    { id: 12, kind_label: '確認依頼', channel_label: 'メール', recipient: 'rv-admin2', status_label: '送信済み', reason_label: '', created_at: '2026-10-05T15:00:02', can_resend: false },
  ]
  let current = records
  const f = await setup({ canReview: true }, { template: async id => ({ data: { ...pending(id), notifications: current } }), resendTemplateNotification: async () => { current = [{ ...records[0], can_resend: false }, { ...records[1] }]; return { data: {} } } })
  try {
    await f.state.showDetail(1)
    f.state.reason.value = '入力中の理由'
    const text = (await html(f)).replace(/<!--.*?-->/g, '')
    assert.equal((text.match(/再送（同じ宛先へ1回だけ）/g) || []).length, 1)
    f.consent.value = false
    await f.state.resendNotice(records[1]); await f.state.resendNotice(records[0])
    assert.equal(f.calls.some(c => c[0] === 'resendTemplateNotification'), false, '再送できない行・確認を断った場合は送らない')
    f.consent.value = true
    await f.state.resendNotice(records[0])
    assert.deepEqual(f.calls.filter(c => c[0] === 'resendTemplateNotification'), [['resendTemplateNotification', 11]])
    assert.equal(f.state.reason.value, '入力中の理由')
    assert.equal(((await html(f)).match(/再送（同じ宛先へ1回だけ）/g) || []).length, 0, '再送後は、同じ行に再送ボタンを出さない')
  } finally { f.stop() }
})

test('通知の再送: 編集権限がなければボタンを出さず送らない。409は固定文を出し、状態を取り直す', async () => {
  const records = [{ id: 21, kind_label: '承認', channel_label: 'メール', recipient: 'a', status_label: '失敗', reason_label: '', created_at: '2026-10-05T15:00:01', can_resend: true }]
  const view = await setup({ canEdit: false }, { template: async id => ({ data: { ...pending(id), notifications: records } }) })
  const f = await setup({}, {
    template: async id => ({ data: { ...pending(id), notifications: records } }),
    resendTemplateNotification: async () => { const e = new Error('SECRET'); e.response = { status: 409, data: { detail: 'SECRET' } }; throw e },
  })
  try {
    await view.state.showDetail(1); await f.state.showDetail(1)
    assert.equal((await html(view)).includes('再送（同じ宛先'), false)
    await view.state.resendNotice(records[0])
    assert.equal(view.calls.some(c => c[0] === 'resendTemplateNotification'), false)
    await f.state.resendNotice(records[0])
    assert.ok(f.state.error.value.includes('再送できません')); assert.equal(f.state.error.value.includes('SECRET'), false)
    assert.equal(f.calls.filter(c => c[0] === 'template').length, 2, '失敗でも記録を取り直す')
  } finally { f.stop(); view.stop() }
})

test('カテゴリは必須: 選ぶまで保存できず、選んだ値を送る。保存後は選び直しになる(カテゴリ)', async () => {
  const f = await setup()
  try {
    f.state.category.value = ''
    f.state.accepted.value = true
    await f.state.save()
    assert.equal(f.calls.some(c => c[0] === 'saveTemplate'), false, 'カテゴリ未選択では送らない')
    f.state.category.value = 'quality'
    await f.state.save()
    assert.deepEqual(f.calls.find(c => c[0] === 'saveTemplate')[1], { plan_id: 'plan-1', revision: 6, category: 'quality', name: '日別出荷の分析' })
    assert.equal(f.state.category.value, '', '保存後は、次の保存のために選び直す')
    const text = await html(f)
    for (const label of ['カテゴリ（必須）', '入荷', '出荷', '在庫', '生産', '品質', 'その他']) assert.ok(text.includes(label), label)
  } finally { f.stop() }
})

test('テンプレート名: 初期値は分析案の題名。書き換えた名前(前後の空白は除く)を送り、空では保存できない(2026-10-08)', async () => {
  const f = await setup()
  try {
    assert.equal(f.state.templateName.value, '日別出荷の分析')
    const text = await html(f)
    assert.ok(text.includes('テンプレート名（必須・300文字以内）')); assert.ok(text.includes('maxlength="300"'))
    f.state.accepted.value = true
    f.state.templateName.value = '   '
    await f.state.save()
    assert.equal(f.calls.some(c => c[0] === 'saveTemplate'), false, '空の名前では送らない')
    f.state.templateName.value = '  8月の日別出荷  '; f.state.nameEdited.value = true
    await f.state.save()
    assert.equal(f.calls.find(c => c[0] === 'saveTemplate')[1].name, '8月の日別出荷')
    // 同じ分析案の間は、書き換えた名前を残す。別の分析案になったら、その題名へ戻す
    f.state.templateName.value = '書き換え'; f.state.nameEdited.value = true
    f.props.plan = plan({ id: 'plan-2', proposal: { title: '別の題名' } }); await Promise.resolve()
    assert.equal(f.state.templateName.value, '別の題名')
  } finally { f.stop() }
})

test('同じ名前の警告: 名前を確定したとき、一覧(見える範囲)の完全一致を確認し、件数を出す。確認できなくても保存は止めない', async () => {
  const f = await setup({}, { templates: async params => ({ data: params?.name ? { ...page([row(7), row(8)]), count: 2 } : page([row(1)]) }) })
  try {
    f.state.templateName.value = '重複する名前'; f.state.nameEdited.value = true
    await f.state.checkName()
    assert.deepEqual(f.calls.filter(c => c[0] === 'templates').at(-1)[1], { name: '重複する名前' })
    assert.equal(f.state.duplicateCount.value, 2)
    let text = await html(f)
    assert.ok(text.includes('同じ名前のテンプレートが2件あります')); assert.ok(text.includes('そのまま保存もできます')); assert.ok(text.includes('class="name-warning"'))
    f.state.accepted.value = true
    await f.state.save()
    assert.equal(f.calls.some(c => c[0] === 'saveTemplate'), true, '警告があっても保存できる')
  } finally { f.stop() }
  const g = await setup({}, { templates: async params => { if (params?.name) throw new Error('boom'); return { data: page([row(1)]) } } })
  try {
    g.state.templateName.value = '確認できない'; g.state.nameEdited.value = true
    await g.state.checkName()
    assert.equal(g.state.duplicateCount.value, null)
    assert.equal((await html(g)).includes('同じ名前のテンプレートが'), false)
  } finally { g.stop() }
})

test('保存の応答の same_name_count が1以上なら、保存後にも警告を出す', async () => {
  const f = await setup({}, { saveTemplate: async () => ({ data: { ...row(2), version: 1, created: true, same_name_count: 3 } }) })
  try {
    f.state.accepted.value = true
    await f.state.save()
    assert.ok((await html(f)).includes('同じ名前のテンプレートが、ほかに3件あります'))
  } finally { f.stop() }
})

test('名称の変更: 管理者承認前(can_rename)だけ入力欄を出し、変更後に一覧・詳細を取り直す。失敗は固定文だけ', async () => {
  const detailOf = (id, extra = {}) => ({ data: { ...row(id), date_from: '2026-01-01', date_to: '2026-01-31', conditions: '全行', procedure: ['集計'], sql_steps: [{ name: 'w_a', query: 'SELECT 1' }], python_code: PYTHON, can_change_category: true, ...extra } })
  const f = await setup({}, { template: async id => detailOf(id, { can_rename: true }), renameTemplate: async () => ({ data: { same_name_count: 1 } }) })
  try {
    await f.state.showDetail(1)
    let text = await html(f)
    assert.ok(text.includes('名称を変更（管理者承認前だけ）')); assert.equal(f.state.newName.value, '分析1')
    await f.state.renameTemplate()
    assert.equal(f.calls.some(c => c[0] === 'renameTemplate'), false, '名前が変わっていなければ送らない')
    f.state.newName.value = '  新しい名前  '
    await f.state.renameTemplate()
    assert.deepEqual(f.calls.find(c => c[0] === 'renameTemplate').slice(1), [1, { name: '新しい名前' }])
    assert.equal(f.calls.filter(c => c[0] === 'template').length >= 2, true, '変更後に詳細を取り直す')
    assert.equal(f.state.renameWarning.value, 1)
    assert.ok((await html(f)).includes('同じ名前のテンプレートが、ほかに1件あります'))
  } finally { f.stop() }
  const g = await setup({}, { template: async id => detailOf(id, { can_rename: false }) })
  try {
    await g.state.showDetail(1)
    assert.equal((await html(g)).includes('名称を変更（管理者承認前だけ）'), false, '承認後は出さない')
  } finally { g.stop() }
  for (const [status, part] of [[400, 'テンプレート名を入力してください'], [403, '名称を変更する権限がありません'], [404, 'テンプレートが見つかりません'], [409, '管理者承認前のテンプレートだけです'], [500, '名称を変更できませんでした']]) {
    const h = await setup({}, { template: async id => detailOf(id, { can_rename: true }), renameTemplate: async () => { throw { response: { status, data: { detail: 'SECRET-INTERNAL' } } } } })
    try {
      await h.state.showDetail(1); h.state.newName.value = '別の名前'
      await h.state.renameTemplate()
      const text = await html(h)
      assert.ok(text.includes(part), String(status)); assert.equal(text.includes('SECRET-INTERNAL'), false)
    } finally { h.stop() }
  }
})

const PARAMS = [
  { name: 'product_code', type: 'product_code', label: '品番', default: 'P-001' },
  { name: 'period_from', type: 'date', label: '開始日', default: '2026-01-01' },
  { name: 'period_to', type: 'date', label: '終了日', default: '2026-01-31' },
]
const paramRow = (extra = {}) => row(5, { status: 'approved', parameters: PARAMS, ...extra })

test('再利用(2-C): 変数のあるテンプレートは、入力欄を出してから作る。変数のないテンプレートは、従来どおり、すぐ作る', async () => {
  const f = await setup({ plan: null })
  try {
    f.calls.length = 0
    await f.state.openReuse(row(1, { status: 'approved' }))
    assert.equal(f.state.reuseRow.value, null)
    assert.deepEqual(f.calls, [['createTemplatePlan', 1]], '変数がなければ、入力欄なしで作る')
    f.calls.length = 0
    f.state.openReuse(paramRow())
    assert.equal(f.calls.length, 0, '変数があれば、入力欄を出すだけで、まだ作らない')
    assert.deepEqual({ ...f.state.reuseValues.value }, { product_code: 'P-001', period_from: '2026-01-01', period_to: '2026-01-31' })
    const text = await html(f)
    for (const part of ['今回使う値', '品番（product_code）', '開始日（period_from）', '終了日（period_to）', 'type="date"', 'この値で分析案を作成', '取消（現在の分析案はそのまま）',
      'テンプレートを保存したときのものです', '比べる期間・除く期間は、自動では動きません']) assert.ok(text.includes(part), part)
  } finally { f.stop() }
})

test('再利用(2-C): 変えた値だけを送る。変えていなければ値を送らない。空にした値は、空のまま送る(保存済みの値へ戻さない)', async () => {
  const f = await setup({ plan: null })
  try {
    f.state.openReuse(paramRow())
    assert.deepEqual(f.state.changedValues(), {})
    f.calls.length = 0
    await f.state.startPlan(paramRow(), f.state.changedValues())
    assert.deepEqual(f.calls, [['createTemplatePlan', 5]], '変更なし: 従来どおり値を送らない')
    f.state.openReuse(paramRow())
    f.state.reuseValues.value.product_code = 'P-002'; f.state.reuseValues.value.period_to = ''
    assert.deepEqual(f.state.changedValues(), { product_code: 'P-002', period_to: '' })
    assert.ok((await html(f)).includes('（変更あり。保存済みの値: P-001）'))
    f.state.reuseValues.value.product_code = 'P-001'
    assert.deepEqual(f.state.changedValues(), { period_to: '' }, '保存済みの値へ戻したら、差分に含めない')
    f.calls.length = 0
    await f.state.startPlan(paramRow(), f.state.changedValues())
    assert.deepEqual(f.calls, [['createTemplatePlan', 5, { period_to: '' }]])
  } finally { f.stop() }
})

test('再利用(2-C): 取消では何も変えない。作成に成功した後だけ入力欄を閉じ、失敗では入力値と現在の分析案を残す', async () => {
  const f = await setup({ plan: plan() })
  try {
    f.state.openReuse(paramRow())
    f.state.reuseValues.value.period_from = '2026-01-10'
    f.state.closeReuse()
    assert.equal(f.state.reuseRow.value, null); assert.deepEqual(f.events, [], '取消では、分析案を作らず・置き換えない')
    f.state.openReuse(paramRow())
    assert.equal(f.state.reuseValues.value.period_from, '2026-01-01', '開き直すと、保存済みの値から')
    f.state.reuseValues.value.period_from = '2026-01-10'
    f.consent.value = true
    await f.state.startPlan(paramRow(), f.state.changedValues())
    assert.equal(f.events.length, 1); assert.equal(f.events[0][0], 'plan-created')
    assert.equal(f.state.reuseRow.value, null, '成功したら閉じる')
  } finally { f.stop() }
  const g = await setup({ plan: plan() }, { createTemplatePlan: async () => { throw { response: { status: 400, data: { reasons: ['parameters_def_date'], names: { parameters_def_date: ['period_from'] } } } } } })
  try {
    g.state.openReuse(paramRow()); g.state.reuseValues.value.period_from = 'abc'
    g.consent.value = true
    await g.state.startPlan(paramRow(), g.state.changedValues())
    assert.deepEqual(g.events, [], '失敗したら、分析案を渡さない')
    assert.ok(g.state.reuseRow.value, '失敗しても、入力欄は残る'); assert.equal(g.state.reuseValues.value.period_from, 'abc', '入力した値も残る')
    assert.equal(g.state.busy.value, '')
  } finally { g.stop() }
})

test('再利用(2-C): 400は、理由コードごとの固定文と、該当する変数のラベルを出す。未知の理由・名前・本文は出さない', async () => {
  const fail = (status, data) => async () => { throw { response: { status, data } } }
  for (const [reason, part] of [['parameters_def_date', 'YYYY-MM-DDの形'], ['parameters_def_value', '英数字・アンダースコア・ハイフン'], ['parameters_def_unregistered', '登録されていない'],
    ['parameters_def_order', '開始日は、終了日以前'], ['parameters_def_outside', '全体の期間の中に収めてください']]) {
    const f = await setup({ plan: null }, { createTemplatePlan: fail(400, { detail: 'SECRET-DETAIL', reasons: [reason], names: { [reason]: ['product_code', 'period_from', '<img onerror=SECRET>', 'unknown_x'] } }) })
    try {
      await f.state.startPlan(paramRow(), { product_code: 'x' })
      const text = await html(f)
      assert.ok(text.includes(part), reason)
      assert.ok(text.includes('該当: 品番、開始日、unknown_x'), reason)   // ラベルに直す。識別子の形でない名前は出さない
      assert.equal(text.includes('SECRET'), false, reason)
    } finally { f.stop() }
  }
  for (const [status, data, part] of [[400, { detail: 'SECRET-DETAIL' }, '分析案の作成の指定が正しくありません'], [400, { reasons: ['unknown_reason'], names: {} }, '分析案の作成の指定が正しくありません'],
    [403, {}, '作成者と管理者だけ'], [404, {}, 'テンプレートが見つかりません'], [409, {}, '再利用できません'], [503, { detail: 'SECRET-DETAIL' }, '分析案を作成できませんでした']]) {
    const f = await setup({ plan: null }, { createTemplatePlan: fail(status, data) })
    try {
      await f.state.startPlan(paramRow(), {})
      const text = await html(f)
      assert.ok(text.includes(part), String(status)); assert.equal(text.includes('SECRET'), false)
    } finally { f.stop() }
  }
})

function deferred() { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b }); return { promise, resolve, reject } }

test('再利用(2-C): 応答を待つ間に分析案が切り替わる・編集権限を失うと、古い応答(成功・失敗)を採用せず、新しい入力・分析案を壊さない(Codex P2)', async () => {
  for (const change of ['plan', 'roundtrip', 'permission']) {
    for (const outcome of ['success', 'failure']) {
      const wait = deferred()
      const f = await setup({ plan: plan() }, { createTemplatePlan: async () => wait.promise })
      try {
        f.state.openReuse(paramRow()); f.state.reuseValues.value.product_code = 'P-002'
        f.consent.value = true
        const pending = f.state.startPlan(paramRow(), f.state.changedValues())
        assert.equal(f.state.busy.value, 'reuse')
        if (change === 'plan') f.props.plan = plan({ id: 'plan-2' })
        else if (change === 'roundtrip') { f.props.plan = plan({ id: 'plan-2' }); f.props.plan = plan() }  // 別の分析案へ替えて、元へ戻っても、古い要求は採用しない
        else f.props.canEdit = false
        await Promise.resolve()
        if (outcome === 'success') wait.resolve({ data: { id: 'late-plan', template: { id: 5 } } }); else wait.reject({ response: { status: 400, data: { reasons: ['parameters_def_date'] } } })
        await pending
        assert.deepEqual(f.events, [], `${change}/${outcome}: 古い応答は、親へ渡さない`)
        assert.equal(f.state.error.value, '', `${change}/${outcome}: 古い失敗は、表示しない`)
        assert.equal(f.state.busy.value, '')
        if (change !== 'permission') { assert.ok(f.state.reuseRow.value, '分析案が替わっても、入力欄は残る'); assert.equal(f.state.reuseValues.value.product_code, 'P-002', '入力値も残る') }
        else assert.equal(f.state.reuseRow.value, null, '編集権限を失ったら、入力欄を閉じる')
      } finally { f.stop() }
    }
  }
})

test('再利用(2-C): 二重クリックは1要求だけ。画面を破棄した後の応答は、採用しない', async () => {
  const wait = deferred()
  const f = await setup({ plan: null }, { createTemplatePlan: async () => wait.promise })
  try {
    f.state.openReuse(paramRow()); f.state.reuseValues.value.product_code = 'P-002'
    f.calls.length = 0
    const first = f.state.startPlan(paramRow(), f.state.changedValues()), second = f.state.startPlan(paramRow(), f.state.changedValues())
    assert.equal(f.calls.filter(c => c[0] === 'createTemplatePlan').length, 1)
    f.stop(); wait.resolve({ data: { id: 'late' } }); await first; await second
    assert.deepEqual(f.events, [])
  } finally { f.stop() }
})

test('再利用(2-C): 同じテンプレートを押し直しても入力を残す。別のテンプレートへの切替は、変更があるときだけ破棄を確認する(Codex P3)', async () => {
  const f = await setup({ plan: null })
  try {
    f.state.openReuse(paramRow()); f.state.reuseValues.value.product_code = 'P-002'
    f.confirms.length = 0
    f.state.openReuse(paramRow())
    assert.equal(f.state.reuseValues.value.product_code, 'P-002', '同じテンプレートは、入力を残す'); assert.equal(f.confirms.length, 0)
    const other = row(6, { status: 'approved', parameters: [{ name: 'product_code', type: 'product_code', label: '品番', default: 'P-009' }] })
    f.consent.value = false
    f.state.openReuse(other)
    assert.equal(f.confirms.length, 1); assert.equal(f.state.reuseRow.value.id, 5, '断ったら、今の入力のまま'); assert.equal(f.state.reuseValues.value.product_code, 'P-002')
    f.consent.value = true
    f.state.openReuse(other)
    assert.equal(f.state.reuseRow.value.id, 6); assert.equal(f.state.reuseValues.value.product_code, 'P-009')
    f.confirms.length = 0
    f.state.openReuse(paramRow())   // 変更がなければ、確認なしで切り替える
    assert.equal(f.confirms.length, 0); assert.equal(f.state.reuseRow.value.id, 5)
  } finally { f.stop() }
})

test('再利用(2-C): ラベルにHTMLが含まれても、入力欄・エラー文では、テキストとして表示する(エスケープされる)', async () => {
  const evil = [{ name: 'product_code', type: 'product_code', label: '<img src=x onerror=SECRET>', default: 'P-001' }]
  const fail = async () => { throw { response: { status: 400, data: { reasons: ['parameters_def_unregistered'], names: { parameters_def_unregistered: ['product_code'] } } } } }
  const f = await setup({ plan: null }, { createTemplatePlan: fail })
  try {
    const target = paramRow({ parameters: evil })
    f.state.openReuse(target); f.state.reuseValues.value.product_code = 'P-002'
    await f.state.startPlan(target, f.state.changedValues())
    const text = await html(f)
    assert.equal(text.includes('<img src=x onerror=SECRET>'), false, '生のタグを出さない')
    assert.ok(text.includes('&lt;img src=x onerror=SECRET&gt;'), 'テキストとして出す')
  } finally { f.stop() }
})

test('一覧にカテゴリを表示し、絞り込みは選んだカテゴリを送る(すべてのときは送らない)', async () => {
  const f = await setup({}, { templates: async () => ({ data: page([row(1, { category: 'shipment', category_label: '出荷' })]) }) })
  try {
    assert.ok((await html(f)).includes('カテゴリ: 出荷'))
    assert.deepEqual(f.calls.filter(c => c[0] === 'templates')[0][1], { page: 1 })
    f.state.categoryFilter.value = 'receipt'
    await Promise.resolve(); await Promise.resolve()
    assert.deepEqual(f.calls.filter(c => c[0] === 'templates').pop()[1], { page: 1, category: 'receipt' })
    assert.ok((await html(f)).includes('カテゴリの絞り込み'))
  } finally { f.stop() }
})

test('カテゴリの変更は、作成者・管理者(can_change_category)で編集権限があるときだけ。変更後に一覧と詳細を取り直し、失敗は固定文', async () => {
  let current = 'shipment'
  const detailOf = id => ({ data: { ...row(id, { status: 'approved', category: current, category_label: current === 'shipment' ? '出荷' : '品質' }), can_change_category: true, date_from: '2026-01-01', date_to: '2026-01-31', conditions: 'c', procedure: [], sql_steps: [], python_code: PYTHON } })
  const f = await setup({}, { template: async id => detailOf(id), changeTemplateCategory: async (id, body) => { current = body.category; return { data: {} } } })
  const view = await setup({ canEdit: false }, { template: async id => detailOf(id) })
  const other = await setup({}, { template: async id => ({ data: { ...row(id, { status: 'approved' }), date_from: '2026-01-01', date_to: '2026-01-31', conditions: 'c', procedure: [], sql_steps: [], python_code: PYTHON } }) })
  const bad = await setup({}, { template: async id => detailOf(id), changeTemplateCategory: async () => { const e = new Error('x'); e.response = { status: 403, data: { detail: 'SECRET' } }; throw e } })
  try {
    await f.state.showDetail(1); await view.state.showDetail(1); await other.state.showDetail(1); await bad.state.showDetail(1)
    assert.ok((await html(f)).includes('カテゴリを変更'))
    assert.equal((await html(view)).includes('カテゴリを変更'), false, '閲覧のみでは出さない')
    assert.equal((await html(other)).includes('カテゴリを変更'), false, '作成者・管理者以外には出さない')
    await f.state.changeCategory()
    assert.equal(f.calls.some(c => c[0] === 'changeTemplateCategory'), false, '同じカテゴリでは送らない')
    f.state.newCategory.value = 'quality'
    await f.state.changeCategory()
    assert.deepEqual(f.calls.filter(c => c[0] === 'changeTemplateCategory'), [['changeTemplateCategory', 1, { category: 'quality' }]])
    assert.equal(f.state.detail.value.category, 'quality', '変更後に詳細を取り直す')
    await view.state.changeCategory()
    assert.equal(view.calls.some(c => c[0] === 'changeTemplateCategory'), false)
    bad.state.newCategory.value = 'quality'
    await bad.state.changeCategory()
    assert.ok(bad.state.error.value.includes('権限がありません')); assert.equal(bad.state.error.value.includes('SECRET'), false)
  } finally { f.stop(); view.stop(); other.stop(); bad.stop() }
})

test('却下された版を開くと、訂正版のカテゴリの初期値を、元の版のカテゴリにする(変えてもよい)', async () => {
  const f = await setup({ canReview: true }, { template: async id => ({ data: { ...row(id, { status: 'rejected', category: 'inventory', category_label: '在庫' }), date_from: '2026-01-01', date_to: '2026-01-31', conditions: 'c', procedure: [], sql_steps: [], python_code: PYTHON } }) })
  try {
    f.state.category.value = ''
    await f.state.showDetail(1)
    assert.equal(f.state.category.value, 'inventory')
    f.state.category.value = 'quality'
    await f.state.showDetail(1)
    assert.equal(f.state.category.value, 'quality', '選び済みの値は上書きしない')
    // 初期値として入れた値は、別の却下版を開いたときに入れ替える。利用者が選んだ値は残す
    const g = await setup({ canReview: true }, { template: async id => ({ data: { ...row(id, { status: 'rejected', category: id === 1 ? 'inventory' : 'receipt', category_label: 'x' }), date_from: '2026-01-01', date_to: '2026-01-31', conditions: 'c', procedure: [], sql_steps: [], python_code: PYTHON } }) })
    try {
      g.state.category.value = ''
      await g.state.showDetail(1); assert.equal(g.state.category.value, 'inventory')
      await g.state.showDetail(2); assert.equal(g.state.category.value, 'receipt', '自動で入れた値は、次の版の値に入れ替える')
      g.state.category.value = 'quality'
      await g.state.showDetail(1); assert.equal(g.state.category.value, 'quality', '利用者が選んだ値は残す')
      g.state.category.value = ''
      assert.ok((await html(g)).includes('カテゴリを選んでください'), '未選択のときは、訂正版の保存が無効な理由を出す')
    } finally { g.stop() }
  } finally { f.stop() }
})
