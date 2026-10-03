import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import test from 'node:test'
import { computed, ref } from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const filename = new URL('../src/views/settings/AISettings.vue', import.meta.url)
const parsed = parse(readFileSync(filename, 'utf8'), { filename: filename.pathname })
assert.deepEqual(parsed.errors, [])
const script = compileScript(parsed.descriptor, { id: 'qwen-settings-test' })
assert.deepEqual(compileTemplate({ source: parsed.descriptor.template.content, filename: filename.pathname,
  id: 'qwen-settings-test', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
const source = parsed.descriptor.scriptSetup.content.replace(/^import .*\r?\n/gm, '').replace(/\bload\(\)\s*$/, '')
const create = new Function('ref', 'computed', 'api', 'authState', 'hasPermission', 'setTimeout',
  `${source}\nreturn {load,providers,saveQwenTimeout,saveProvider,savingQwenTimeout,qwenTimeoutError,qwenTimeoutNotice}`)

async function setup(canEdit = true, update) {
  const calls = []
  const item = { id: 2, provider: 'qwen', is_enabled: true, default_model: 'qwen3:4b-instruct', analysis_plan_timeout_seconds: 180 }
  const empty = async () => ({ data: [] })
  const api = { aiSettings: {
    providers: async () => ({ data: [item] }), tools: empty, dataPolicy: empty, knowledgeSources: empty,
    knowledgeDocuments: empty, sqlDictionary: empty, crossScreenAccess: empty, analysisExecutionPolicy: empty,
    updateProvider: async (id, data) => { calls.push([id, data]); return update ? update(id, data) : { data: { ...item, ...data } } },
  }, ocr: { status: async () => ({ data: { tesseract: {} } }) } }
  const state = create(ref, computed, api, { user: {} }, () => canEdit, () => {})
  await state.load()
  return { state, calls, item: state.providers.value[0] }
}

test('Qwenのタイムアウトだけを明示保存する', async () => {
  const { state, calls, item } = await setup()
  assert.equal(item.analysis_plan_timeout_seconds, 180)
  item.analysis_plan_timeout_seconds = 240
  assert.equal(calls.length, 0)
  await state.saveQwenTimeout(item)
  assert.deepEqual(calls, [[2, { analysis_plan_timeout_seconds: 240 }]])
  assert.match(state.qwenTimeoutNotice.value, /次のQwen分析案/)
  await state.saveProvider(item)
  assert.deepEqual(calls[1][1], { is_enabled: true, default_model: item.default_model })
})

test('範囲外・空欄・小数は送信しない', async () => {
  const { state, calls, item } = await setup()
  for (const value of [0, 29, 601, '', null, 180.5, NaN]) {
    item.analysis_plan_timeout_seconds = value
    await state.saveQwenTimeout(item)
    assert.match(state.qwenTimeoutError.value, /30〜600/)
  }
  assert.equal(calls.length, 0)
})

test('閲覧権限だけの場合と社外プロバイダは保存しない', async () => {
  const fixture = await setup(false)
  await fixture.state.saveQwenTimeout(fixture.item)
  assert.equal(fixture.calls.length, 0)
  const editable = await setup()
  await editable.state.saveQwenTimeout({ ...editable.item, provider: 'openrouter' })
  assert.equal(editable.calls.length, 0)
})

test('失敗時は入力を残して再試行できる', async () => {
  let fail = true
  const { state, item } = await setup(true, async (_, data) => {
    if (fail) throw { response: { data: { analysis_plan_timeout_seconds: ['設定を確認してください。'] } } }
    return { data }
  })
  item.analysis_plan_timeout_seconds = 240
  await state.saveQwenTimeout(item)
  assert.equal(item.analysis_plan_timeout_seconds, 240)
  assert.match(state.qwenTimeoutError.value, /設定を確認/)
  assert.equal(state.savingQwenTimeout.value, false)
  fail = false
  await state.saveQwenTimeout(item)
  assert.equal(state.qwenTimeoutError.value, '')
  assert.match(state.qwenTimeoutNotice.value, /保存しました/)
})

test('保存中の二重送信を防止する', async () => {
  let finish
  const { state, calls, item } = await setup(true, () => new Promise(resolve => { finish = resolve }))
  const pending = state.saveQwenTimeout(item)
  await state.saveQwenTimeout(item)
  assert.equal(calls.length, 1)
  finish({ data: { analysis_plan_timeout_seconds: 180 } })
  await pending
  assert.equal(state.savingQwenTimeout.value, false)
})
