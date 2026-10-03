import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import test from 'node:test'
import { computed, effectScope, ref, watch } from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const filename = new URL('../src/views/ai/AIAnalysis.vue', import.meta.url)
const text = readFileSync(filename, 'utf8')
const parsed = parse(text, { filename: filename.pathname })
assert.deepEqual(parsed.errors, [])
const script = compileScript(parsed.descriptor, { id: 'analysis-test' })
assert.deepEqual(compileTemplate({ source: parsed.descriptor.template.content, filename: filename.pathname,
  id: 'analysis-test', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
const source = parsed.descriptor.scriptSetup.content.replace(/^import .*\r?\n/gm, '')
const exposed = 'purpose,dateFrom,dateTo,provider,model,externalPreview,externalAccepted,plan,prepareExternalPreview,createPlan,resetPlan'
const create = new Function('ref', 'computed', 'watch', 'defineProps', 'onMounted', 'onBeforeUnmount', 'api', 'window',
  `${source}\nreturn {${exposed}}`)

async function setup(provider = 'openrouter', model = 'test:free', paidConsent = true) {
  const scope = effectScope()
  let mount
  const calls = [], confirms = []
  const api = { aiAnalysis: {
    options: async () => ({ data: { default_provider: 'openrouter', providers: [
      { provider, label: provider, external: provider !== 'qwen', available: true, default_model: model, models: [{ id: model }] },
    ] } }),
    externalPreview: async data => { calls.push(['preview', data]); return { data: {
      ...data, purpose: '000175が000196の出荷傾向を見る', confirmation: 'signed-preview',
    } } },
    createPlan: async data => { calls.push(['create', data]); return { data: { status: 'awaiting_method' } } },
  } }
  const state = scope.run(() => create(ref, computed, watch, () => ({ canEdit: true, request: null }),
    fn => { mount = fn }, () => {}, api, { confirm: message => { confirms.push(message); return paidConsent } }))
  await mount()
  state.purpose.value = '王崇栓がクボタの出荷傾向を見る'
  state.dateFrom.value = '2026-09-01'
  state.dateTo.value = '2026-09-30'
  return { state, calls, confirms, stop: () => scope.stop() }
}

test('社外送信は目的文の表示と確認後だけ。プレビューは案を作成しない', async () => {
  const fixture = await setup()
  try {
    const { state, calls } = fixture
    state.createPlan()
    assert.equal(calls.length, 0)
    await state.prepareExternalPreview()
    assert.equal(state.plan.value, null)
    assert.equal(state.externalPreview.value.purpose, '000175が000196の出荷傾向を見る')
    state.createPlan()
    assert.equal(calls.length, 1)
    state.externalAccepted.value = true
    state.createPlan()
    await Promise.resolve()
    assert.equal(calls[1][0], 'create')
    assert.equal(calls[1][1].external_confirmation, 'signed-preview')
  } finally { fixture.stop() }
})

test('目的・期間・AI・モデルの変更で送信確認を失効させる', async () => {
  const fixture = await setup()
  try {
    for (const field of ['purpose', 'dateFrom', 'dateTo', 'provider', 'model']) {
      fixture.state.externalPreview.value = { confirmation: 'old' }
      fixture.state.externalAccepted.value = true
      fixture.state[field].value += 'changed'
      assert.equal(fixture.state.externalPreview.value, null)
      assert.equal(fixture.state.externalAccepted.value, false)
    }
  } finally { fixture.stop() }
})

test('初期選択が有料でも送信前に確認し、拒否なら送信しない', async () => {
  for (const [provider, model] of [['deepseek', 'deepseek-v4-pro'], ['openrouter', 'google/gemma-4-26b-a4b-it']]) {
    const fixture = await setup(provider, model, false)
    try {
      await fixture.state.prepareExternalPreview()
      fixture.state.externalAccepted.value = true
      fixture.state.createPlan()
      assert.equal(fixture.confirms.length, 1)
      assert.deepEqual(fixture.calls.map(call => call[0]), ['preview'])
    } finally { fixture.stop() }
  }
})

test('ローカルQwenは社外送信確認なしで従来どおり作成する', async () => {
  const fixture = await setup('qwen', 'qwen3:4b-instruct')
  try {
    fixture.state.createPlan()
    await Promise.resolve()
    assert.deepEqual(fixture.calls.map(call => call[0]), ['create'])
    assert.equal('external_confirmation' in fixture.calls[0][1], false)
  } finally { fixture.stop() }
})
