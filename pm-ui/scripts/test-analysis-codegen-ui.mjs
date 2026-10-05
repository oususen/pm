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
const create = new Function('ref', 'computed', 'watch', 'defineProps', 'onMounted', 'onBeforeUnmount', 'api', 'window', 'AIAnalysisExecution', 'AIAnalysisTemplates', 'AnalysisErrorBanner', 'useAnalysisErrorNotices',
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
    { confirm: text => { confirms.push(text); return consent.value } }, { template: '<section>分析実行の専用画面</section>' }, { template: '<section>テンプレートの専用画面</section>' }, AnalysisErrorBanner, useAnalysisErrorNotices))
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
