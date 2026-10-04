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
const names = Object.keys(script.bindings).filter(n => !['computed', 'onBeforeUnmount', 'onMounted', 'ref', 'watch', 'api', 'plan', 'canEdit', 'blocked'].includes(n))
const create = new Function('ref', 'computed', 'watch', 'onMounted', 'onBeforeUnmount', 'defineProps', 'api', 'AnalysisErrorBanner', 'useAnalysisErrorNotices',
  parsed.descriptor.scriptSetup.content.replace(/^import .*\r?\n/gm, '') + `\nreturn {${names.join(',')}}`)
const render = new Function('Vue', template.code.replace(/import \{([^}]+)\} from "vue"/, (_, s) => `const {${s.replace(/ as /g, ':')}} = Vue`).replace('export function render', 'function render') + '\nreturn render')(Vue)

const PYTHON = "emit_table('日別', ['日'], [['1']])"
function plan(extra = {}) { return { id: 'plan-1', revision: 6, status: 'data_approved', codegen: { status: 'code_approved', executed_code_sha256: 'hash', python: PYTHON, steps: [] }, ...extra } }
function row(id, extra = {}) { return { id, name: `分析${id}`, purpose: `目的${id}`, status: 'pending_admin', status_label: '管理者承認待ち', created_by: 'tester', created_at: '2026-10-04T10:20:30', content_visible: true, ...extra } }
const page = results => ({ results, count: results.length, next: null, previous: null })
async function setup(propsInit = {}, methodsInit = {}) {
  const props = Vue.reactive({ plan: plan(), canEdit: true, blocked: false, ...propsInit }), calls = []
  const methods = {
    templates: async () => ({ data: page([row(1)]) }),
    saveTemplate: async () => ({ data: { ...row(2), version: 1, created: true } }),
    template: async id => ({ data: { ...row(id), date_from: '2026-01-01', date_to: '2026-01-31', conditions: '全行', procedure: ['集計', '表'], sql_steps: [{ name: 'w_a', query: 'SELECT 1' }], python_code: PYTHON, executed_code_sha256: 'hash', wrapper_version: 'w1' } }),
    ...methodsInit,
  }
  const api = { aiAnalysis: Object.fromEntries(Object.keys(methods).map(name => [name, async (...args) => { calls.push([name, ...args]); return methods[name](...args) }])) }
  const scope = Vue.effectScope()
  let mount, unmount
  const state = scope.run(() => create(Vue.ref, Vue.computed, Vue.watch, fn => { mount = fn }, fn => { unmount = fn }, () => props, api, AnalysisErrorBanner, useAnalysisErrorNotices))
  await mount(); await Promise.resolve()
  return { state, props, calls, stop: () => { unmount(); scope.stop() } }
}
function html(f) { return renderToString(Vue.createSSRApp({ props: ['plan', 'canEdit', 'blocked'], setup: () => Object.fromEntries(Object.entries(f.state).map(([k, v]) => [k, Vue.unref(v)])), render }, f.props)) }

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
