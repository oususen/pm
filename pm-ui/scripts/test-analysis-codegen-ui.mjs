// 画面の操作は模擬APIで検証し、AIや実DBには接続しない。
import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import test from 'node:test'
import * as Vue from 'vue'
import { renderToString } from '@vue/server-renderer'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { useAnalysisErrorNotices } from '../src/composables/analysisErrorNotices.js'
import { AnalysisErrorBanner } from './analysis-error-banner-test-helper.mjs'

const filename = new URL('../src/views/ai/AIAnalysis.vue', import.meta.url)
const source = readFileSync(filename, 'utf8')
const parsed = parse(source, { filename: filename.pathname })
assert.deepEqual(parsed.errors, [])
const script = compileScript(parsed.descriptor, { id: 'codegen-ui-test' })
const template = compileTemplate({ source: parsed.descriptor.template.content, filename: filename.pathname,
  id: 'codegen-ui-test', compilerOptions: { bindingMetadata: script.bindings } })
assert.deepEqual(template.errors, [])
const exposed = 'plan,busy,error,codePreview,codeSendAccepted,codeAccepted,codeStateFresh,codeInFlight,canGenerate,canTrial,canApproveCode,trialPassed,hasCode,prepareCodePreview,generateCode,trialCode,approveCode,releaseCodegen,refresh,resetPlan'
const names = Object.keys(script.bindings).filter(name => !['computed', 'onBeforeUnmount', 'onMounted', 'ref', 'watch', 'api', 'request', 'canEdit', 'canViewAll', 'visible'].includes(name))
const create = new Function('ref', 'computed', 'watch', 'defineProps', 'onMounted', 'onBeforeUnmount', 'api', 'window', 'AIAnalysisConsult', 'AIAnalysisExecution', 'AIAnalysisTemplates', 'AnalysisErrorBanner', 'useAnalysisErrorNotices',
  `${parsed.descriptor.scriptSetup.content.replace(/^import .*\r?\n/gm, '')}\nreturn {${names.join(',')}}`)
const render = new Function('Vue', template.code
  .replace(/import \{([^}]+)\} from "vue"/, (_, imports) => `const {${imports.replace(/ as /g, ':')}} = Vue`)
  .replace('export function render', 'function render') + '\nreturn render')(Vue)

function dataPlan(provider = 'openrouter') {
  return { id: 'test-plan', revision: 3, status: 'data_approved', expires_at: '2026-10-04T23:00:00',
    proposal: { provider, model: 'test-model', title: '出荷分析', purpose: '出荷を見る', steps: ['日別に集計'], outputs: ['表'],
      date_from: '2026-09-01', date_to: '2026-09-30', conditions: '期間内全行', datasets: [{ view: 'v_ai_shipment', fields: ['id', 'quantity'] }] },
    codegen_state: { status: 'none', attempts: 0, max_attempts: 4, inflight_state: null } }
}
function generated(provider = 'openrouter') {
  return { ...dataPlan(provider), revision: 5,
    codegen_state: { status: 'generated', attempts: 1, max_attempts: 4, inflight_state: null },
    codegen: { status: 'generated', attempts: 1, inflight: null, steps: [{ name: 'w_total', query: 'SELECT SUM(quantity) FROM v_ai_shipment' }],
      python: 'emit_report("<script>alert(1)</script>")', executed_code_sha256: 'hash-code', wrapper_version: 'test-wrapper', trial: null } }
}
async function setup(provider = 'openrouter') {
  const scope = Vue.effectScope(), calls = [], confirms = [], consent = { value: true }
  const props = Vue.reactive({ canEdit: true, request: null })
  const responses = { getPlan: dataPlan(provider), generateCode: generated(provider) }
  let mount, unmount
  const methods = {
    options: async () => ({ data: { providers: [], default_provider: provider } }),
    codegenPreview: async () => ({ data: { provider, model: 'test-model', external: true, attempt: 1, max_attempts: 4,
      messages: [{ role: 'system', content: '検査規則全文' }, { role: 'user', content: '000175/000196：目的・手順・出力案・ビュー・列・期間' }],
      not_sent: ['idの値', '承認件数', '実データ'], confirmation: 'once-only' } }),
    generateCode: async () => ({ data: responses.generateCode }), getPlan: async () => ({ data: responses.getPlan }),
    trialCode: async () => ({ data: { ...generated(provider), revision: 6, codegen: { ...generated(provider).codegen,
      trial: { status: 'passed', executed_code_sha256: 'hash-code', at: '2026-10-04T12:00:00' } } } }),
    approveCode: async () => ({ data: { ...generated(provider), revision: 7, codegen_state: { ...generated(provider).codegen_state, status: 'code_approved' },
      codegen: { ...generated(provider).codegen, status: 'code_approved', code_approved_at: '2026-10-04T12:01:00' } } }),
    releaseCodegen: async () => ({ data: { ...dataPlan(provider), revision: 9, codegen_state: { status: 'failed', attempts: 2, max_attempts: 4, inflight_state: null } } }),
    refreshWrapper: async () => ({ data: { ...generated(provider), revision: 10, codegen_state: { ...generated(provider).codegen_state, wrapper_outdated: false }, codegen: { ...generated(provider).codegen, trial: null } } }),
  }
  const api = { aiAnalysis: Object.fromEntries(Object.keys(methods).map(name => [name, async (...args) => {
    calls.push([name, ...args]); return methods[name](...args)
  }])) }
  const state = scope.run(() => create(Vue.ref, Vue.computed, Vue.watch, () => props, fn => { mount = fn }, fn => { unmount = fn }, api,
    { confirm: text => { confirms.push(text); return consent.value } }, { template: '<section>AI相談の専用画面</section>' }, { template: '<section>分析実行の専用画面</section>' }, { template: '<section>テンプレートの専用画面</section>' }, AnalysisErrorBanner, useAnalysisErrorNotices))
  await mount()
  state.plan.value = dataPlan(provider)
  calls.length = 0
  return { state, props, methods, responses, calls, confirms, consent, unmount, stop: () => scope.stop() }
}
const mutationCalls = fixture => fixture.calls.filter(call => call[0] !== 'getPlan')

test('分析エラーは帯・見出し・閉じるボタンを表示し、本文をエスケープ。閉じる／次の操作で消える', async () => {
  const f = await setup('qwen')
  try {
    const html = () => renderToString(Vue.createSSRApp({ setup: () => Object.fromEntries(Object.entries(f.state).map(([key, value]) => [key, Vue.unref(value)])), render }))
    assert.equal((await html()).includes('analysis-error-banner'), false)
    f.state.error.value = '<img src=x onerror=SECRET>'
    let text = await html()
    assert.ok(text.includes('analysis-error-banner')); assert.ok(text.includes('エラー</strong>'))
    assert.ok(text.includes('aria-label="エラーを閉じる"')); assert.ok(text.includes('role="alert"'))
    assert.ok(text.includes('&lt;img')); assert.equal(text.includes('<img'), false)
    f.state.errorNotices.notices.value[0].dismiss()
    assert.equal(f.state.error.value, ''); assert.equal((await html()).includes('analysis-error-banner'), false)
    f.state.error.value = '以前のエラー'
    let resolve
    f.methods.generateCode = () => new Promise(done => { resolve = done })
    const pending = f.state.generateCode()
    assert.equal(f.state.error.value, '')
    resolve({ data: generated('qwen') }); await pending
  } finally { f.stop() }
})

test('外枠の明示更新はAI生成APIを呼ばず旧確認を破棄。閲覧専用・実行中・未確認は禁止', async () => {
  const f = await setup()
  try {
    f.state.plan.value = generated()
    f.state.plan.value.codegen_state.wrapper_outdated = true
    f.state.codeAccepted.value = true
    assert.equal(f.state.canRefreshWrapper.value, true)
    await f.state.refreshWrapper()
    assert.equal(f.calls.length, 1)
    assert.equal(f.calls[0][0], 'refreshWrapper')
    assert.equal(f.state.codeAccepted.value, false)
    assert.equal(f.state.trialPassed.value, false)
    f.state.plan.value = generated(); f.state.plan.value.codegen_state.wrapper_outdated = true
    for (const change of [() => { f.props.canEdit = false }, () => { f.state.codeStateFresh.value = false }, () => { f.state.executionActive.value = true }]) {
      f.props.canEdit = true; f.state.codeStateFresh.value = true; f.state.executionActive.value = false
      change(); await f.state.refreshWrapper()
      assert.equal(f.calls.length, 1)
    }
  } finally { f.stop() }
})

test('社外送信は全文確認後のみ。同時クリックでも1回、確認コードを消費する', async () => {
  const f = await setup()
  try {
    await f.state.generateCode(); assert.equal(f.calls.length, 0)
    await f.state.prepareCodePreview()
    assert.equal(f.state.codePreview.value.messages.length, 2)
    await f.state.generateCode(); assert.equal(f.calls.length, 1)
    f.state.codeSendAccepted.value = true
    await Promise.all([f.state.generateCode(), f.state.generateCode()])
    assert.deepEqual(f.calls.map(call => call[0]), ['codegenPreview', 'generateCode'])
    assert.deepEqual(f.calls[1].slice(1), ['test-plan', { revision: 3, confirmation: 'once-only' }])
    assert.equal(f.state.codePreview.value, null); assert.equal(f.state.codeSendAccepted.value, false)
    await f.state.generateCode(); assert.equal(f.calls.length, 2)
  } finally { f.stop() }
})

test('ローカルQwenは送信確認なし。AIを自動で切り替えない', async () => {
  const f = await setup('qwen')
  try {
    await f.state.generateCode()
    assert.deepEqual(f.calls.map(call => call[0]), ['generateCode'])
    assert.deepEqual(f.calls[0][2], { revision: 3 })
    assert.equal(f.state.plan.value.proposal.provider, 'qwen')
  } finally { f.stop() }
})

test('試行合格・同一ハッシュ・利用者の確認が揃ったコードだけを承認する', async () => {
  const f = await setup()
  try {
    f.state.plan.value = generated()
    f.state.codeAccepted.value = true
    await f.state.approveCode(); assert.equal(f.calls.length, 0)
    await f.state.trialCode(); assert.equal(f.state.trialPassed.value, true)
    await f.state.approveCode(); assert.equal(f.calls.length, 1)
    f.state.codeAccepted.value = true
    await f.state.approveCode()
    assert.deepEqual(f.calls[1], ['approveCode', 'test-plan', { revision: 6, executed_code_sha256: 'hash-code' }])
    assert.equal(f.state.plan.value.codegen_state.status, 'code_approved')
  } finally { f.stop() }
})

test('試行が未検証・不合格・ハッシュ不一致なら承認しない。試行操作は生成APIを呼ばない', async () => {
  const f = await setup()
  try {
    for (const [status, hash] of [['unverified', 'hash-code'], ['failed', 'hash-code'], ['passed', 'other']]) {
      f.state.plan.value = generated()
      f.state.plan.value.codegen.trial = { status, executed_code_sha256: hash }
      f.state.codeAccepted.value = true
      await f.state.approveCode(); assert.equal(f.calls.length, 0)
    }
    await f.state.trialCode()
    assert.deepEqual(f.calls.map(call => call[0]), ['trialCode'])
  } finally { f.stop() }
})

function htmlFor(f) {
  const state = Vue.proxyRefs(f.state)
  return renderToString(Vue.createSSRApp({ render: () => render.call(state, state, [], f.props, state, {}, {}) }))
}

test('生成失敗の理由は固定文だけ表示し、未知の理由やAI本文を表示しない', async () => {
  const f = await setup()
  try {
    f.state.plan.value = { ...dataPlan(), codegen_state: { status: 'failed', attempts: 1, max_attempts: 4 },
      codegen: { reasons: ['python:import_not_allowed', 'ai_unsupported', 'code_too_large', 'SECRET-未知', '__proto__'], unsupported_reason: 'SECRET-AI本文' } }
    const html = await htmlFor(f)
    assert.ok(html.includes('許可されていないライブラリ'))
    assert.ok(html.includes('分析コードを作成できない'))
    assert.ok(html.includes('コード全体のサイズ'))
    assert.ok(html.includes('検査に合格しませんでした'))
    assert.equal(html.includes('SECRET'), false)
  } finally { f.stop() }
})

test('試行の失敗理由と該当手順を表示するが、DuckDB本文・未知の手順は表示しない', async () => {
  const f = await setup()
  try {
    f.state.plan.value = generated()
    f.state.plan.value.codegen.trial = { status: 'failed', reason: 'query_failed', step: 'w_total', message: 'SECRET-DB明細' }
    let html = await htmlFor(f)
    assert.ok(html.includes('SQL手順1（w_total）'))
    assert.ok(html.includes('構文と承認した列・型'))
    assert.equal(html.includes('SECRET'), false)
    Object.assign(f.state.plan.value.codegen.trial, { reason: 'SECRET-未知', step: 'SECRET-手順' })
    html = await htmlFor(f)
    assert.ok(html.includes('検査に合格しませんでした'))
    assert.equal(html.includes('SECRET'), false)
  } finally { f.stop() }
})

test('未検証の未知の理由は実行基盤の確認を案内し、コード修正を促さず本文も表示しない', async () => {
  const f = await setup()
  try {
    f.state.plan.value = generated()
    for (const reason of ['stage_deadline_transfer', 'isolation_unavailable', 'cleanup_pending', 'container_oom_killed',
      'SECRET-未知の理由', '__proto__', null, undefined, { detail: 'SECRET-理由オブジェクト' }]) {
      f.state.plan.value.codegen.trial = { status: 'unverified', reason, step: 'SECRET-手順', message: 'SECRET-DB本文', executed_code_sha256: 'hash-code' }
      const html = await htmlFor(f)
      assert.ok(html.includes('試行の検証が完了していません。実行基盤の状態を確認して試行をやり直してください。'))
      assert.equal(html.includes('分析目的・手順とコードを確認してください'), false)
      assert.equal(html.includes('SECRET'), false)
      if (typeof reason === 'string') assert.equal(html.includes(reason), false)
      assert.equal(f.state.trialPassed.value, false)
      assert.equal(f.state.canApproveCode.value, false)
      assert.equal(f.state.plan.value.codegen_state.attempts, 1)
    }
    assert.equal(f.calls.length, 0)
  } finally { f.stop() }
})

test('未検証の既知の固定文と、不合格の汎用文は従来どおり。合格には失敗文を表示しない', async () => {
  const f = await setup()
  try {
    f.state.plan.value = generated()
    f.state.plan.value.codegen.trial = { status: 'unverified', reason: 'busy' }
    assert.ok((await htmlFor(f)).includes('実行基盤が使用中です。しばらく待って試行をやり直してください。'))
    assert.equal(f.state.trialFailureLabel.value.includes('検証が完了していません'), false)
    f.state.plan.value.codegen.trial = { status: 'failed', reason: 'SECRET-未知' }
    assert.equal(f.state.trialFailureLabel.value, '検査に合格しませんでした。分析目的・手順とコードを確認してください。')
    assert.equal((await htmlFor(f)).includes('SECRET'), false)
    f.state.plan.value.codegen.trial = { status: 'passed', reason: 'SECRET-未知', executed_code_sha256: 'hash-code' }
    assert.equal(f.state.trialFailureLabel.value, '')
    assert.equal(f.state.canApproveCode.value, true)
  } finally { f.stop() }
})

test('最新状態が不明なら解除ボタンも無効で、確認ダイアログもAPIも呼ばない', async () => {
  const f = await setup()
  try {
    f.state.plan.value.codegen_state.inflight_state = 'unknown'
    f.state.codeStateFresh.value = false
    assert.equal(f.state.canReleaseCodegen.value, false)
    await f.state.releaseCodegen()
    assert.equal(f.confirms.length, 0); assert.equal(f.calls.length, 0)
    assert.match(await htmlFor(f), /<button disabled[^>]*>状態不明の生成を解除/)
  } finally { f.stop() }
})

test('送信確認の403は設定による拒否として表示し、状態取得失敗とは表示しない', async () => {
  const f = await setup()
  try {
    f.methods.codegenPreview = async () => { throw { response: { status: 403, data: { detail: '社外送信は許可されていません。' } } } }
    await f.state.prepareCodePreview()
    const html = await htmlFor(f)
    assert.ok(html.includes('社外送信は許可されていません'))
    assert.equal(html.includes('最新状態を確認できない'), false)
    assert.equal(f.state.codePreview.value, null)
    assert.deepEqual(f.calls.map(call => call[0]), ['codegenPreview'])
  } finally { f.stop() }
})

test('送信確認の409は状態だけ再取得。取得に失敗した場合だけ操作を止める', async () => {
  const f = await setup()
  try {
    f.methods.codegenPreview = async () => { throw { response: { status: 409, data: { detail: '版が異なります' } } } }
    f.responses.getPlan = { ...dataPlan(), revision: 12 }
    await f.state.prepareCodePreview()
    assert.equal(f.state.plan.value.revision, 12)
    assert.equal(f.state.codeStateFresh.value, true)
    assert.equal((await htmlFor(f)).includes('最新状態を確認できない'), false)
    f.methods.getPlan = async () => { throw new Error('通信失敗') }
    await f.state.prepareCodePreview()
    assert.equal(f.state.codeStateFresh.value, false)
    assert.equal(f.state.codePreview.value, null)
    assert.deepEqual(f.calls.map(call => call[0]), ['codegenPreview', 'getPlan', 'codegenPreview', 'getPlan'])
  } finally { f.stop() }
})

test('試行・承認・解除の期限切れは案と全確認を破棄し、自動再実行しない', async () => {
  for (const action of ['trialCode', 'approveCode', 'releaseCodegen']) {
    const f = await setup()
    try {
      f.state.plan.value = generated()
      f.state.plan.value.codegen.trial = { status: 'passed', executed_code_sha256: 'hash-code' }
      if (action === 'releaseCodegen') f.state.plan.value.codegen_state.inflight_state = 'unknown'
      f.state.codePreview.value = { confirmation: 'discard' }
      f.state.codeSendAccepted.value = true; f.state.codeAccepted.value = true
      f.methods[action] = async () => { throw { response: { status: 410, data: { detail: '期限切れ' } } } }
      await f.state[action]()
      assert.deepEqual(f.calls.map(call => call[0]), [action])
      assert.equal(f.state.plan.value, null); assert.equal(f.state.codePreview.value, null)
      assert.equal(f.state.codeAccepted.value, false); assert.equal(f.state.codeSendAccepted.value, false)
    } finally { f.stop() }
  }
})

test('コード承認後の再生成も新たな送信確認が必要で、試行と承認を引き継がない', async () => {
  const f = await setup()
  try {
    f.state.plan.value = generated()
    f.state.plan.value.codegen_state.status = f.state.plan.value.codegen.status = 'code_approved'
    f.state.plan.value.codegen.trial = { status: 'passed', executed_code_sha256: 'hash-code' }
    await f.state.generateCode(); assert.equal(f.calls.length, 0)
    await f.state.prepareCodePreview(); f.state.codeSendAccepted.value = true
    await f.state.generateCode()
    assert.deepEqual(f.calls.map(call => call[0]), ['codegenPreview', 'generateCode'])
    assert.equal(f.state.plan.value.codegen.status, 'generated')
    assert.equal(f.state.plan.value.codegen.trial, null)
    assert.equal(f.state.codeAccepted.value, false)
  } finally { f.stop() }
})

test('閲覧専用の案内文にコード生成・試行・承認・解除を含める', async () => {
  const f = await setup()
  try {
    f.props.canEdit = false
    assert.ok((await htmlFor(f)).includes('コード生成・SQL試行・コード承認・状態不明の解除'))
  } finally { f.stop() }
})

test('生成中は再生成・試行・承認・解除できず、状態不明だけ明示確認後に解除する', async () => {
  const f = await setup('qwen')
  try {
    const inflight = { ...dataPlan('qwen'), revision: 8, codegen: { status: 'generating', inflight: { attempt: 2 } },
      codegen_state: { status: 'generating', attempts: 2, max_attempts: 4, inflight_state: 'running' } }
    f.state.plan.value = inflight
    await f.state.generateCode(); await f.state.trialCode(); await f.state.approveCode(); await f.state.releaseCodegen()
    assert.equal(f.calls.length, 0)
    f.state.plan.value.codegen_state.inflight_state = 'unknown'
    f.consent.value = false
    await f.state.releaseCodegen(); assert.equal(f.calls.length, 0)
    f.consent.value = true
    await f.state.releaseCodegen()
    assert.equal(f.confirms.length, 2)
    assert.deepEqual(mutationCalls(f).map(call => call[0]), ['releaseCodegen'])
    assert.equal(f.state.plan.value.codegen_state.attempts, 2)
  } finally { f.stop() }
})

test('AI生成上限でも試行は可能。UIはサーバーの上限値を使う', async () => {
  const f = await setup('qwen')
  try {
    f.state.plan.value = generated('qwen')
    Object.assign(f.state.plan.value.codegen_state, { attempts: 2, max_attempts: 2 })
    await f.state.generateCode(); assert.equal(f.calls.length, 0)
    assert.equal(f.state.canTrial.value, true)
  } finally { f.stop() }
})

test('版・内容・AI・モデル変更時に送信確認とコード確認を消す', async () => {
  const f = await setup()
  try {
    for (const change of [p => p.revision++, p => { p.proposal.title += '変更' }, p => { p.proposal.provider = 'deepseek' }, p => { p.proposal.model += '変更' }]) {
      f.state.plan.value = dataPlan()
      await f.state.prepareCodePreview()
      f.state.codeSendAccepted.value = true; f.state.codeAccepted.value = true
      change(f.state.plan.value)
      assert.equal(f.state.codePreview.value, null)
      assert.equal(f.state.codeSendAccepted.value, false); assert.equal(f.state.codeAccepted.value, false)
    }
  } finally { f.stop() }
})

test('生成要求の通信失敗は再送せず状態だけ再取得。確認コードは再利用しない', async () => {
  const f = await setup()
  try {
    await f.state.prepareCodePreview(); f.state.codeSendAccepted.value = true
    f.methods.generateCode = async () => { throw new Error('通信切断') }
    f.responses.getPlan = { ...dataPlan(), codegen_state: { status: 'generating', attempts: 1, max_attempts: 4, inflight_state: 'running' } }
    await f.state.generateCode()
    assert.deepEqual(f.calls.map(call => call[0]), ['codegenPreview', 'generateCode', 'getPlan'])
    assert.equal(f.state.codeInFlight.value, true)
    assert.equal(f.state.codePreview.value, null)
  } finally { f.stop() }
})

test('競合409では最新の版を取得するだけで、操作と送信を自動再実行しない', async () => {
  const f = await setup()
  try {
    await f.state.prepareCodePreview(); f.state.codeSendAccepted.value = true
    f.methods.generateCode = async () => { throw { response: { status: 409, data: { detail: '別の操作で更新' } } } }
    f.responses.getPlan = { ...generated(), revision: 12 }
    await f.state.generateCode()
    assert.equal(f.state.plan.value.revision, 12)
    assert.equal(f.calls.filter(call => call[0] === 'generateCode').length, 1)
    assert.equal(f.state.codeSendAccepted.value, false)
    await f.state.generateCode()
    assert.equal(f.calls.filter(call => call[0] === 'generateCode').length, 1)
  } finally { f.stop() }
})

test('再生成には新しい全文確認を取り直す', async () => {
  const f = await setup()
  try {
    await f.state.prepareCodePreview(); f.state.codeSendAccepted.value = true
    await f.state.generateCode()
    await f.state.generateCode()
    assert.equal(f.calls.filter(call => call[0] === 'generateCode').length, 1)
    f.methods.codegenPreview = async () => ({ data: { provider: 'openrouter', model: 'test-model', attempt: 2,
      not_sent: [], messages: [{ role: 'user', content: '新しい全文' }], confirmation: 'second-only' } })
    await f.state.prepareCodePreview(); f.state.codeSendAccepted.value = true
    await f.state.generateCode()
    const sends = f.calls.filter(call => call[0] === 'generateCode')
    assert.equal(sends.length, 2)
    assert.deepEqual(sends[1][2], { revision: 5, confirmation: 'second-only' })
  } finally { f.stop() }
})

test('状態再取得にも失敗したら再生成・承認を止める。成功時だけ復帰する', async () => {
  const f = await setup('qwen')
  try {
    f.methods.generateCode = f.methods.getPlan = async () => { throw new Error('通信切断') }
    await f.state.generateCode()
    assert.equal(f.state.canGenerate.value, false); assert.equal(f.state.codeStateFresh.value, false)
    f.methods.getPlan = async () => ({ data: generated('qwen') })
    await f.state.refresh(); assert.equal(f.state.codeStateFresh.value, true)
  } finally { f.stop() }
})

test('期限切れは画面の案と確認を破棄する', async () => {
  const f = await setup()
  try {
    await f.state.prepareCodePreview(); f.state.codeSendAccepted.value = true
    f.methods.generateCode = async () => { throw { response: { status: 410, data: { detail: '期限切れ' } } } }
    await f.state.generateCode()
    assert.equal(f.state.plan.value, null); assert.equal(f.state.codePreview.value, null)
    assert.equal(f.state.error.value, '期限切れ')
  } finally { f.stop() }
})

test('閲覧専用では生成・試行・承認・解除のAPIを呼ばない', async () => {
  const f = await setup()
  try {
    f.props.canEdit = false
    await f.state.prepareCodePreview(); await f.state.generateCode(); await f.state.trialCode(); await f.state.approveCode(); await f.state.releaseCodegen()
    f.state.plan.value = generated()
    await f.state.trialCode()
    f.state.plan.value.codegen.trial = { status: 'passed', executed_code_sha256: 'hash-code' }
    f.state.codeAccepted.value = true
    await f.state.approveCode()
    f.state.plan.value.codegen_state.inflight_state = 'unknown'
    await f.state.releaseCodegen()
    assert.equal(f.calls.length, 0)
  } finally { f.stop() }
})

test('画面破棄・分析案作り直し後に、遅れて返る送信確認を採用しない', async () => {
  const f = await setup()
  try {
    let complete
    f.methods.codegenPreview = () => new Promise(resolve => { complete = resolve })
    const request = f.state.prepareCodePreview()
    f.state.resetPlan()
    complete({ data: { confirmation: 'late' } }); await request
    assert.equal(f.state.plan.value, null); assert.equal(f.state.codePreview.value, null)
    f.state.plan.value = dataPlan()
    const second = f.state.prepareCodePreview()
    f.unmount(); complete({ data: { confirmation: 'late' } }); await second
    assert.equal(f.state.codePreview.value, null)
  } finally { f.stop() }
})

test('VueテンプレートのSSRはコードをエスケープし、実行専用画面を接続する', async () => {
  const f = await setup()
  try {
    f.state.plan.value = generated()
    const setupState = Vue.proxyRefs(f.state)
    const html = () => renderToString(Vue.createSSRApp({ render: () => render.call(setupState, setupState, [], f.props, setupState, {}, {}) }))
    const generatedHTML = await html()
    assert.ok(generatedHTML.includes('&lt;script&gt;alert(1)&lt;/script&gt;'))
    assert.equal(generatedHTML.includes('<script>'), false)
    assert.ok(generatedHTML.includes('分析実行の専用画面'))
    assert.ok(generatedHTML.includes('SQLを試行'))
    f.state.plan.value.codegen_state.status = 'code_approved'
    const approvedHTML = await html()
    assert.ok(approvedHTML.includes('コード承認済み・分析未実行'))
    assert.ok(approvedHTML.includes('分析実行の専用画面'))
  } finally { f.stop() }
})

// 公開する操作一覧が変わったら、意図せず実行APIを追加していないかも確認する。
test('コード生成用APIの5経路と後半の実行APIを接続する', () => {
  const client = readFileSync(new URL('../src/api/client.js', import.meta.url), 'utf8')
  const block = client.slice(client.indexOf('  aiAnalysis: {'), client.indexOf('  aiConversations: {'))
  for (const endpoint of ['codegen/preview/', 'codegen/`', 'codegen/trial/', 'codegen/approve/', 'codegen/release/']) assert.ok(block.includes(endpoint))
  assert.equal(block.includes('/execute/'), true)
  for (const name of exposed.split(',')) assert.ok(names.includes(name))
})

test('テンプレート由来の分析案は、AI生成の操作を出さず、テンプレートの表示と保存済みコードを承認前から表示する', async () => {
  const f = await setup()
  try {
    const proposal = { ...generated().proposal, provider: 'template', model: '' }
    const fromTemplate = (status, template) => ({ ...generated(), proposal, status, template, codegen_state: { status: 'generated', attempts: 0, max_attempts: 4, inflight_state: null } })
    f.state.plan.value = fromTemplate('awaiting_method', { id: 7, version: 2, name: '日別出荷', status: 'pending_admin' })
    let html = await htmlFor(f)
    assert.ok(html.includes('テンプレート7（版2・日別出荷）から作成した分析案です'))
    assert.ok(html.includes('システム管理者未承認のテンプレートです'))
    assert.ok(html.includes('テンプレート（AI未使用）'))
    assert.ok(html.includes('SELECT SUM(quantity) FROM v_ai_shipment'), '手順の承認前から保存済みSQLを表示')
    f.state.plan.value = fromTemplate('data_approved', { id: 7, version: 2, name: '日別出荷', status: 'approved' })
    html = await htmlFor(f)
    assert.ok(html.includes('正式なテンプレートです'))
    assert.ok(html.includes('AIによるコード生成は行いません'))
    for (const word of ['コード生成で社外送信する全文を確認', 'ローカルQwenでコードを生成', '確認した全文を社外AIへ送ってコードを生成', '社外送信']) assert.equal(html.includes(word), false, word)
    // 通常の分析案では、従来どおり生成の操作を出す
    f.state.plan.value = { ...generated('openrouter'), status: 'data_approved' }
    assert.ok((await htmlFor(f)).includes('コード生成で社外送信する全文を確認'))
  } finally { f.stop() }
})

test('ヘッダ行に、タイトル・状態のチップ・AIプロバイダ・モデルの選択を並べ、分析目的の入力欄より上に表示する(BOSS要望 2026-10-05)', async () => {
  const f = await setup()
  try {
    f.state.plan.value = null
    const html = await htmlFor(f)
    const header = html.slice(html.indexOf('<header class="topbar">'), html.indexOf('</header>'))
    for (const part of ['AI分析', '分析案・承認', 'local-badge', 'AIプロバイダ', 'モデル']) assert.ok(header.includes(part), part)
    assert.ok(header.indexOf('AIプロバイダ') < header.indexOf('モデル'), 'AIプロバイダの次にモデル')
    const purpose = html.indexOf('id="analysis-purpose"'), period = html.indexOf('開始日')
    assert.ok(purpose > html.indexOf('</header>'), '目的の入力欄は、ヘッダの下')
    assert.ok(period > purpose, '期間は目的の下')
    assert.equal(html.split('AIプロバイダ').length - 1, 1, 'AIの選択はヘッダの1か所だけ')
  } finally { f.stop() }
})

test('右サイドに段階カード(①〜⑤)を置き、今の段階を開き、済みの段階を畳む。コード確認のため④は⑤の間も開く(R1)', async () => {
  const f = await setup()
  try {
    // 分析案なし: ①が今、ほかは未
    f.state.plan.value = null
    let html = await htmlFor(f)
    assert.ok(html.includes('class="analysis-layout"') && html.includes('class="analysis-side"') && html.includes('分析の進め方'))
    assert.deepEqual([1, 2, 3, 4, 5].map(n => f.state.stageState(n)), ['current', 'pending', 'pending', 'pending', 'pending'])
    assert.equal((html.match(/class="stage[ "]/g) || []).length, 1, '分析案がなければ①だけ')
    // 手順の承認待ち
    f.state.plan.value = { ...dataPlan(), status: 'awaiting_method' }
    assert.deepEqual([1, 2, 3].map(n => f.state.stageState(n)), ['done', 'current', 'pending'])
    assert.deepEqual([1, 2].map(n => f.state.isOpen(n)), [false, true])
    // データ範囲の承認待ち
    f.state.plan.value = { ...dataPlan(), status: 'awaiting_data' }
    assert.deepEqual([2, 3].map(n => f.state.stageState(n)), ['done', 'current'])
    // データ承認済み・コード未生成: ④が今
    f.state.plan.value = dataPlan()
    assert.deepEqual([3, 4, 5].map(n => f.state.stageState(n)), ['done', 'current', 'pending'])
    // コード生成済み(試行・承認待ち): ④は済みだが、コードを確認するため開く。⑤が今
    f.state.plan.value = generated()
    assert.deepEqual([4, 5].map(n => f.state.stageState(n)), ['done', 'current'])
    assert.deepEqual([4, 5].map(n => f.state.isOpen(n)), [true, true])
    html = await htmlFor(f)
    assert.equal((html.match(/class="stage[ "]/g) || []).length, 6, '分析案があれば、⑥実行も出る')
    assert.ok(html.includes('SELECT SUM(quantity) FROM v_ai_shipment'))
    // 利用者の開閉が、初期の開閉より優先される。分析案が変われば初期に戻る
    f.state.toggleStage(4)
    assert.equal(f.state.isOpen(4), false)
    f.state.plan.value = { ...generated(), id: 'other-plan' }
    await Promise.resolve()
    assert.equal(f.state.isOpen(4), true)
    // コード承認済み: ④⑤とも済みで畳み、要約に承認日時を出す
    const approved = generated(); approved.codegen_state = { ...approved.codegen_state, status: 'code_approved' }
    approved.codegen = { ...approved.codegen, status: 'code_approved', code_approved_at: '2026-10-05T11:00:00' }
    f.state.plan.value = approved
    assert.deepEqual([4, 5].map(n => f.state.stageState(n)), ['done', 'done'])
    assert.deepEqual([4, 5].map(n => f.state.isOpen(n)), [false, false])
    assert.ok(f.state.stageSummary(5).includes('コード承認 2026-10-05 11:00:00'))
    assert.ok((await htmlFor(f)).includes('コード承認 2026-10-05 11:00:00'))
  } finally { f.stop() }
})

test('分析案がなければ、再取得・作り直しのボタンを出さない(元の条件)。分析案があれば出す', async () => {
  const f = await setup()
  try {
    f.state.plan.value = null
    let html = await htmlFor(f)
    assert.equal(html.includes('分析案の状態を再取得'), false)
    assert.equal(html.includes('目的・期間を変更して作り直す'), false)
    f.state.plan.value = dataPlan()
    html = await htmlFor(f)
    assert.ok(html.includes('分析案の状態を再取得')); assert.ok(html.includes('目的・期間を変更して作り直す'))
  } finally { f.stop() }
})

test('コードの警告がある間は、コード承認済みでも④を畳まず、利用者の開閉でも畳めない。要約に「要確認」を出す(警告を隠さない)', async () => {
  const f = await setup()
  try {
    const approved = (extra = {}) => {
      const p = generated(); p.codegen_state = { ...p.codegen_state, status: 'code_approved', ...extra }
      p.codegen = { ...p.codegen, status: 'code_approved', code_approved_at: '2026-10-05T11:00:00' }
      return p
    }
    // 通常のコード承認済み: ④⑤とも済みで畳む
    f.state.plan.value = approved()
    assert.deepEqual([4, 5].map(n => f.state.isOpen(n)), [false, false])
    assert.equal(f.state.codeAttention.value, false)
    // 外枠が古い: ④を開き、更新の警告とボタンを見せる。畳む操作をしても開いたまま
    f.state.plan.value = approved({ wrapper_outdated: true })
    assert.equal(f.state.isOpen(4), true); f.state.toggleStage(4); assert.equal(f.state.isOpen(4), true)
    assert.ok(f.state.stageSummary(4).includes('要確認'))
    const html = await htmlFor(f)
    assert.ok(html.includes('外枠が更新されています')); assert.ok(html.includes('保存済みコードの外枠を更新'))
    assert.ok(html.includes('stage-head') && html.includes('コード生成済み・要確認'))
    // 最新状態を確認できない
    f.state.plan.value = approved(); f.state.codeStateFresh.value = false
    assert.equal(f.state.isOpen(4), true)
    f.state.codeStateFresh.value = true
    assert.equal(f.state.isOpen(4), false)
    // 生成中・状態不明、生成失敗は、④が今で開いている(警告を見せる)
    f.state.plan.value = { ...dataPlan(), codegen_state: { status: 'generating', attempts: 1, max_attempts: 4, inflight_state: 'unknown' }, codegen: { inflight: { attempt: 1 } } }
    assert.deepEqual([4, 5].map(n => f.state.stageState(n)), ['current', 'pending']); assert.equal(f.state.isOpen(4), true)
    f.state.plan.value = { ...dataPlan(), codegen_state: { status: 'failed', attempts: 1, max_attempts: 4, inflight_state: null }, codegen: { reasons: ['response_invalid'] } }
    assert.deepEqual([4, 5].map(n => f.state.stageState(n)), ['current', 'pending']); assert.equal(f.state.isOpen(4), true)
    // 実行依頼済み(plan.execution)でも、コード承認済みなら④⑤は済み
    f.state.plan.value = { ...approved(), execution: { job_id: 'job-1' } }
    assert.deepEqual([4, 5].map(n => f.state.stageState(n)), ['done', 'done'])
    assert.deepEqual([4, 5].map(n => f.state.isOpen(n)), [false, false])
  } finally { f.stop() }
})

test('①の要約にラベルを付ける(UI方針: ラベルを省略しない)', async () => {
  const f = await setup()
  try {
    f.state.plan.value = dataPlan()
    assert.equal(f.state.stageSummary(1), '分析案: 出荷分析')
  } finally { f.stop() }
})

test('外枠が古い間は、⑤も開く。畳んだ段階は、画面では非表示(v-show)になる(開閉のテンプレートへの反映)', async () => {
  const f = await setup()
  try {
    const approved = (extra = {}) => {
      const p = generated(); p.codegen_state = { ...p.codegen_state, status: 'code_approved', ...extra }
      p.codegen = { ...p.codegen, status: 'code_approved', code_approved_at: '2026-10-05T11:00:00' }
      return p
    }
    const closed = html => (html.match(/class="stage-body" style="display:none;?"/g) || []).length
    // 通常のコード承認済み: ①〜⑤の5枚とも畳まれ、非表示
    f.state.plan.value = approved()
    assert.equal(closed(await htmlFor(f)), 5)
    // 外枠が古い: ④⑤が開く(非表示は①②③の3枚だけ)
    f.state.plan.value = approved({ wrapper_outdated: true })
    assert.deepEqual([4, 5].map(n => f.state.isOpen(n)), [true, true])
    assert.equal(closed(await htmlFor(f)), 3)
    // コード承認の前(⑤が今)は、④⑤が開く。①②③と、まだ未の⑥は非表示
    f.state.plan.value = generated()
    assert.equal(closed(await htmlFor(f)), 4)
  } finally { f.stop() }
})

test('2つの注意文(利用範囲の案内・社外サービスへの送信の注意)を左のメインの先頭に置き、畳めるようにする(BOSS要望 2026-10-05)', async () => {
  const f = await setup()
  try {
    f.state.plan.value = null
    f.state.options.value = { notice: '追加の案内', providers: [{ provider: 'openrouter', label: 'OpenRouter', external: true, available: true, models: [{ id: 'm1', label: 'M1' }] }] }
    f.state.provider.value = 'openrouter'
    let html = await htmlFor(f)
    const main = html.indexOf('class="analysis-main"'), notes = html.indexOf('class="notes"'), exec = html.indexOf('分析実行の専用画面')
    assert.ok(main >= 0 && notes > main && exec > notes, '左のメインの先頭(実行欄より前)')
    // 上部(ヘッダの直下・レイアウトの前)には、注意文がない
    const beforeLayout = html.slice(0, html.indexOf('class="analysis-layout"'))
    assert.equal(beforeLayout.includes('class="notice"'), false); assert.equal(beforeLayout.includes('名称を登録コードに置換した分析目的'), false)
    // 2つの文面が、そのまま入っている
    for (const part of ['分析案・データ範囲の承認、コード生成・試行・承認、開発限定の実行・中止・結果・履歴表示に対応します', '追加の案内',
      '社外サービス（OpenRouter）へ、名称を登録コードに置換した分析目的・期間・公開ビューの説明を送ります。DBの明細行・件数は送りません。未登録の人名・社名は自動判別できません。']) {
      assert.ok(html.includes(part), part)
    }
    assert.equal(html.includes('テンプレート保存は未対応です'), false, '事実と合わない一文は削除(BOSS指示 2026-10-05)')
    // 開いている間は表示、畳むと非表示(v-show)になり、見出しに外部送信の要点を出す
    assert.equal(f.state.notesOpen.value, true)
    assert.ok(/class="notes-body"(?! style)/.test(html))
    f.state.notesOpen.value = false
    html = await htmlFor(f)
    assert.ok(/class="notes-body" style="display:none;?"/.test(html), '畳むと非表示')
    assert.ok(html.includes('aria-expanded="false"')); assert.ok(html.includes('社外サービス（OpenRouter）へ、分析目的・期間・公開ビューの説明を送ります'))
    // 外部AIでなければ、外部送信の注意とその要点を出さない。利用できないAIのエラーは、上部に残す
    f.state.options.value = { providers: [{ provider: 'qwen', label: 'ローカルQwen', external: false, available: false, reason: '未起動', models: [] }] }
    f.state.provider.value = 'qwen'
    html = await htmlFor(f)
    assert.equal(html.includes('名称を登録コードに置換した分析目的'), false)
    const top = html.slice(0, html.indexOf('class="analysis-layout"'))
    assert.ok(top.includes('ローカルQwenは利用できません: 未起動'))
  } finally { f.stop() }
})

test('警告で強制的に開いている間の見出しの操作は保存しない(警告が解消したとき、押した覚えのない開閉が現れない)。見出しはaria-controlsで本体と対応づける', async () => {
  const f = await setup()
  try {
    const outdated = flag => { const p = generated(); p.codegen_state = { ...p.codegen_state, wrapper_outdated: flag }; return p }
    f.state.plan.value = outdated(true)
    assert.deepEqual([4, 5].map(n => f.state.isOpen(n)), [true, true])
    f.state.toggleStage(4); f.state.toggleStage(5)
    assert.deepEqual(f.state.toggledStages.value, {}, '強制で開いている間は保存しない')
    // 警告が解消すると、初期の規則(⑤が今なら⑤・④が開く)に従い、勝手に閉じない
    f.state.plan.value = outdated(false)
    await Promise.resolve()
    assert.deepEqual([4, 5].map(n => f.state.stageState(n)), ['done', 'current'])
    assert.deepEqual([4, 5].map(n => f.state.isOpen(n)), [true, true])
    // 警告がないときの操作は、従来どおり保存される
    f.state.toggleStage(5); assert.equal(f.state.isOpen(5), false)
    // aria-controls と本体のid
    const html = await htmlFor(f)
    for (const n of [1, 2, 3, 4, 5]) {
      if (n <= 3 && !html.includes(`aria-controls="stage-body-${n}"`)) continue
      assert.ok(html.includes(`aria-controls="stage-body-${n}"`) && html.includes(`id="stage-body-${n}"`), String(n))
    }
    assert.ok(html.includes('aria-controls="notes-body"') && html.includes('id="notes-body"'))
  } finally { f.stop() }
})

test('⑥実行: 実行は左のまま。コード承認が済んで実行できるようになったら、右に「左で実行してください」を出す(BOSS要望 2026-10-05)', async () => {
  const f = await setup()
  try {
    // 分析案なし: ⑥のカードを出さない
    f.state.plan.value = null
    assert.equal((await htmlFor(f)).includes('stage-body-6'), false)
    // コード承認の前: 未。コード承認の後に左で実行する旨だけ(閉じている)
    f.state.plan.value = generated()
    assert.equal(f.state.stageState(6), 'pending'); assert.equal(f.state.isOpen(6), false)
    let html = await htmlFor(f)
    assert.ok(html.includes('コード承認の後に、左の「分析の実行・結果」で実行します'))
    assert.equal(html.includes('分析を実行」を押してください'), false)
    // コード承認済み・未実行: 今。開いて、「左で実行してください」と案内する
    const approved = generated(); approved.codegen_state = { ...approved.codegen_state, status: 'code_approved' }
    approved.codegen = { ...approved.codegen, status: 'code_approved', code_approved_at: '2026-10-05T11:00:00' }
    f.state.plan.value = approved
    assert.equal(f.state.stageState(6), 'current'); assert.equal(f.state.isOpen(6), true); assert.equal(f.state.stageLabel(6), '今')
    assert.equal(f.state.stageSummary(6), '左で実行してください')
    html = await htmlFor(f)
    assert.ok(html.includes('左の「分析の実行・結果」で、「分析を実行」を押してください。'))
    assert.ok(html.includes('実行欄へ移動')); assert.ok(html.includes('id="analysis-execution"'))
    // 実行できるときは、右の⑥と左の実行欄を強調する(気づきやすく)。それ以外では強調しない
    assert.equal(f.state.runReady.value, true)
    assert.ok(html.includes('class="run-target ready"')); assert.ok(html.includes('run-ready-text')); assert.ok(html.includes('◀ 左で実行してください'))
    assert.ok(/class="stage current ready"|class="stage ready current"|class="stage current ready/.test(html) || html.includes('ready'))
    f.state.plan.value = generated()
    assert.equal(f.state.runReady.value, false)
    html = await htmlFor(f)
    assert.equal(html.includes('class="run-target ready"'), false); assert.equal(html.includes('run-ready-text'), false)
    f.state.plan.value = approved
    // 実行依頼済み: 実行中は今、終了後は済み
    f.state.plan.value = { ...approved, execution: { job_id: 'job-1' } }
    f.state.executionActive.value = true
    assert.equal(f.state.stageState(6), 'current'); assert.equal(f.state.stageSummary(6), '実行中')
    assert.ok((await htmlFor(f)).includes('実行を依頼済みです。実行中です。'))
    f.state.executionActive.value = false
    assert.equal(f.state.stageState(6), 'done'); assert.equal(f.state.stageSummary(6), '実行依頼済み'); assert.equal(f.state.isOpen(6), false)
    // 実行欄への移動は、画面の部品がなくても、エラーにならない(window.documentがない場合)
    assert.doesNotThrow(() => f.state.scrollToExecution())
  } finally { f.stop() }
})

test('AIとの相談の欄は、編集権限があり分析案がないときだけ出す。AIの文案は目的欄・期間欄へ取り込み、分析案は作らない', async () => {
  const f = await setup()
  try {
    assert.equal((await htmlFor(f)).includes('AI相談の専用画面'), false, '分析案があるときは出さない')
    f.state.plan.value = null
    assert.equal((await htmlFor(f)).includes('AI相談の専用画面'), true)
    f.props.canEdit = false
    assert.equal((await htmlFor(f)).includes('AI相談の専用画面'), false, '閲覧のみのときは出さない')
    f.props.canEdit = true
    f.calls.length = 0
    f.state.applyConsult({ purpose: '8月と9月の出荷を比較する', date_from: '2026-08-01', date_to: '2026-09-30' })
    assert.deepEqual([f.state.purpose.value, f.state.dateFrom.value, f.state.dateTo.value], ['8月と9月の出荷を比較する', '2026-08-01', '2026-09-30'])
    f.state.applyConsult({ purpose: null, date_from: null, date_to: null })
    assert.deepEqual([f.state.purpose.value, f.state.dateFrom.value, f.state.dateTo.value], ['8月と9月の出荷を比較する', '2026-08-01', '2026-09-30'], '空の項目は上書きしない')
    f.state.applyConsult({ purpose: '目的だけ', date_from: '2026-01-01', date_to: null })
    assert.deepEqual([f.state.purpose.value, f.state.dateFrom.value, f.state.dateTo.value], ['目的だけ', '2026-08-01', '2026-09-30'], '期間は両方そろったときだけ取り込む')
    assert.deepEqual(f.calls, [], '取り込んでも、分析案の作成・AIの呼び出しはしない')
    assert.equal(f.state.plan.value, null)
  } finally { f.stop() }
})

test('結果の改良: 元の目的・期間・AIの選択を引き継いで、古い結果を消し、追加の指示つきで新しい分析案を作る(結果の改良)', async () => {
  const f = await setup('openrouter')
  try {
    f.state.plan.value = { ...dataPlan('openrouter'), proposal: { ...dataPlan('openrouter').proposal, purpose: '9月の製品別出荷量', date_from: '2026-09-01', date_to: '2026-09-30' } }
    const chosen = [f.state.provider.value, f.state.model.value]
    f.state.startRefinement({ instruction: '  品番も付けて  ', run_id: 7 })
    assert.equal(f.state.plan.value, null, '古い分析案・結果は、画面から消える')
    assert.deepEqual([f.state.purpose.value, f.state.dateFrom.value, f.state.dateTo.value], ['9月の製品別出荷量', '2026-09-01', '2026-09-30'])
    assert.deepEqual([f.state.provider.value, f.state.model.value], chosen, 'AIの選択は引き継ぐ')
    assert.deepEqual(f.state.refinement.value, { instruction: '品番も付けて', from_run_id: 7 })
    assert.deepEqual(f.state.planningInput().refinement, { instruction: '品番も付けて', from_run_id: 7 })
    const text = await htmlFor(f)
    assert.ok(text.includes('追加の指示「品番も付けて」を、上の目的に足して')); assert.ok(text.includes('元の実行: 7')); assert.ok(text.includes('実行履歴に保存されます'))
    // 改良の準備中は、AI相談(テンプレートからの分析案の作成)を出さない: 追加の指示が、黙って落ちるのを防ぐ
    assert.equal(text.includes('AI相談の専用画面'), false)
    f.state.refinement.value = null
    assert.ok((await htmlFor(f)).includes('AI相談の専用画面'), '指示を外せば、相談欄が戻る')
  } finally { f.stop() }
})

test('結果の改良: 社外AIの確認・作成の要求に、追加の指示を付ける。作成後は、分析案が指示を持ち、画面の準備状態は消える(結果の改良)', async () => {
  const f = await setup('openrouter')
  try {
    f.state.plan.value = { ...dataPlan('openrouter'), proposal: { ...dataPlan('openrouter').proposal, purpose: '9月の製品別出荷量', date_from: '2026-09-01', date_to: '2026-09-30' } }
    f.state.startRefinement({ instruction: '品番も付けて', run_id: null })
    assert.deepEqual(f.state.planningInput().refinement, { instruction: '品番も付けて', from_run_id: null })
    assert.ok((await htmlFor(f)).includes('元の実行: 不明'))
    f.state.plan.value = { ...dataPlan('openrouter'), refinement: { instruction: '品番も付けて', from_run_id: null } }
    assert.equal(f.state.refinement.value, null, '分析案を作ると、準備状態は消える')
    assert.ok((await htmlFor(f)).includes('結果の改良: 追加の指示「品番も付けて」（元の実行: 不明）'))
  } finally { f.stop() }
})

test('結果の改良: 追加の指示は外せる。作り直し(resetPlan)でも消える。権限なし・実行中・空の指示では始めない(結果の改良)', async () => {
  const f = await setup('openrouter')
  try {
    const base = () => { f.state.plan.value = { ...dataPlan('openrouter'), proposal: { ...dataPlan('openrouter').proposal, purpose: 'P', date_from: '2026-09-01', date_to: '2026-09-30' } } }
    base(); f.state.startRefinement({ instruction: 'x', run_id: 1 })
    f.state.refinement.value = null
    assert.equal(f.state.planningInput().refinement, undefined, '外すと、要求に付けない')
    base(); f.state.startRefinement({ instruction: 'x', run_id: 1 }); f.state.resetPlan()
    assert.equal(f.state.refinement.value, null)
    base(); f.state.startRefinement({ instruction: '   ', run_id: 1 }); f.state.startRefinement({}); f.state.startRefinement()
    assert.notEqual(f.state.plan.value, null, '空の指示では、分析案を消さない')
    f.props.canEdit = false; f.state.startRefinement({ instruction: 'x', run_id: 1 })
    assert.notEqual(f.state.plan.value, null); f.props.canEdit = true
    f.state.executionActive.value = true; f.state.startRefinement({ instruction: 'x', run_id: 1 })
    assert.notEqual(f.state.plan.value, null, '実行中は始めない'); f.state.executionActive.value = false
    assert.equal(f.state.refinement.value, null)
  } finally { f.stop() }
})
