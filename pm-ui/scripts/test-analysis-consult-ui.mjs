// 分析の前のAIとの相談(目的を整える・テンプレートの推薦)の操作とVue SSR。AI・DB・Dockerへの接続は行わない。
import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import test from 'node:test'
import * as Vue from 'vue'
import { renderToString } from '@vue/server-renderer'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const filename = new URL('../src/views/ai/AIAnalysisConsult.vue', import.meta.url)
const parsed = parse(readFileSync(filename, 'utf8'), { filename: filename.pathname })
assert.deepEqual(parsed.errors, [])
const script = compileScript(parsed.descriptor, { id: 'consult-test' })
const template = compileTemplate({ source: parsed.descriptor.template.content, filename: filename.pathname, id: 'consult-test', compilerOptions: { bindingMetadata: script.bindings } })
assert.deepEqual(template.errors, [])
const names = Object.keys(script.bindings).filter(n => !['computed', 'onBeforeUnmount', 'ref', 'watch', 'api', 'plan', 'canEdit', 'blocked', 'purpose', 'dateFrom', 'dateTo', 'provider', 'model', 'external', 'providerLabel', 'providerAvailable', 'userName'].includes(n))
const create = new Function('ref', 'computed', 'onBeforeUnmount', 'watch', 'defineProps', 'defineEmits', 'api', 'window',
  parsed.descriptor.scriptSetup.content.replace(/^import .*\r?\n/gm, '') + `\nreturn {${names.join(',')}}`)
const render = new Function('Vue', template.code.replace(/import \{([^}]+)\} from "vue"/, (_, s) => `const {${s.replace(/ as /g, ':')}} = Vue`).replace('export function render', 'function render') + '\nreturn render')(Vue)

const reply = (extra = {}) => ({ data: { reply: '製品は絞りますか？', draft: { purpose: null, date_from: null, date_to: null }, templates: [], provider: 'qwen', model: 'm', ...extra } })
function setup(propsInit = {}, methodsInit = {}) {
  const props = Vue.reactive({ plan: null, canEdit: true, blocked: false, purpose: '', dateFrom: '', dateTo: '', provider: 'qwen', model: '', external: false, providerLabel: '', providerAvailable: true, userName: '', ...propsInit }), calls = [], confirms = [], events = [], consent = { value: true }
  const methods = { consult: async () => reply(), createTemplatePlan: async id => ({ data: { id: 'new-plan', template: { id } } }), ...methodsInit }
  const api = { aiAnalysis: Object.fromEntries(Object.keys(methods).map(name => [name, async (...args) => { calls.push([name, ...args]); return methods[name](...args) }])) }
  const scope = Vue.effectScope()
  let state
  scope.run(() => { state = create(Vue.ref, Vue.computed, () => {}, Vue.watch, () => props, () => (...args) => events.push(args), api, { confirm: text => { confirms.push(text); return consent.value } }) })
  const unmountFn = () => scope.stop()
  return { state, props, calls, confirms, events, consent, stop: unmountFn }
}
const html = f => renderToString(Vue.createSSRApp({ props: ['plan', 'canEdit', 'blocked', 'purpose', 'dateFrom', 'dateTo', 'provider', 'model', 'external', 'providerLabel', 'providerAvailable', 'userName'], setup: () => Object.fromEntries(Object.entries(f.state).map(([k, v]) => [k, Vue.unref(v)])), render }, f.props))
const sends = f => f.calls.filter(c => c[0] === 'consult')

test('送信すると、やり取り全体をAPIへ送り、AIの返事を履歴に足す。入力欄は空になる', async () => {
  const f = setup()
  try {
    f.state.input.value = '先月の出荷を比べたい'
    await f.state.send()
    f.state.input.value = '製品は全部です'
    await f.state.send()
    assert.deepEqual(sends(f)[0][1], { messages: [{ role: 'user', content: '先月の出荷を比べたい' }], provider: 'qwen' })
    assert.deepEqual(sends(f)[1][1].messages.map(m => [m.role, m.content]), [['user', '先月の出荷を比べたい'], ['assistant', '製品は絞りますか？'], ['user', '製品は全部です']])
    assert.equal(f.state.input.value, '')
    const text = await html(f)
    assert.ok(text.includes('あなた:') && text.includes('製品は絞りますか？'))
  } finally { f.stop() }
})

test('送れない状態(権限なし・分析案あり・他の操作中・空入力)では送らない', async () => {
  const cases = [{ canEdit: false }, { plan: { id: 'p' } }, { blocked: true }]
  for (const init of cases) {
    const f = setup(init)
    try { f.state.input.value = '相談'; await f.state.send(); assert.equal(sends(f).length, 0, JSON.stringify(init)) } finally { f.stop() }
  }
  const f = setup()
  try { f.state.input.value = '   '; await f.state.send(); assert.equal(sends(f).length, 0) } finally { f.stop() }
})

test('失敗したときは、固定文を出し、送った発言を履歴へ入れず入力欄に残す(再送できる)。APIの本文は出さない', async () => {
  const f = setup({}, { consult: async () => { const e = new Error('SECRET'); e.response = { status: 503, data: { detail: 'SECRET-OLLAMA' } }; throw e } })
  try {
    f.state.input.value = '相談'
    await f.state.send()
    assert.deepEqual(f.state.messages.value, [])
    assert.equal(f.state.input.value, '相談')
    assert.ok(f.state.error.value.includes('AIまたはコード置換の処理を使えません')); assert.equal(f.state.error.value.includes('SECRET'), false)
    assert.equal(f.state.busy.value, '')
  } finally { f.stop() }
})

test('AIの文案は、取り込みを押したときだけ親へ渡す。目的欄・期間欄に内容があれば確認し、断れば渡さない', async () => {
  const draft = { purpose: '8月と9月の出荷を比較する', date_from: '2026-08-01', date_to: '2026-09-30' }
  const f = setup({}, { consult: async () => reply({ draft }) })
  try {
    f.state.input.value = '相談'; await f.state.send()
    assert.deepEqual(f.events, [], '文案を受け取っただけでは、親へ渡さない')
    f.state.apply()
    assert.deepEqual(f.events, [['apply', { purpose: '8月と9月の出荷を比較する', date_from: '2026-08-01', date_to: '2026-09-30' }]])
    assert.equal(f.confirms.length, 0, '空の欄には確認なしで入れる')
    f.props.purpose = '既存の目的'
    f.consent.value = false
    f.state.apply()
    assert.equal(f.confirms.length, 1); assert.equal(f.events.length, 1, '確認を断れば渡さない')
    f.consent.value = true
    f.state.apply()
    assert.equal(f.events.length, 2)
  } finally { f.stop() }
})

test('期間だけ・目的だけの文案は、ある方だけを渡す。どちらもなければ取り込みボタンを出さない', async () => {
  const f = setup({}, { consult: async () => reply({ draft: { purpose: '目的だけ', date_from: null, date_to: null } }) })
  const none = setup()
  try {
    f.state.input.value = '相談'; await f.state.send(); f.state.apply()
    assert.deepEqual(f.events[0][1], { purpose: '目的だけ', date_from: null, date_to: null })
    none.state.input.value = '相談'; await none.state.send()
    assert.equal((await html(none)).includes('取り込む'), false)
    assert.equal((await html(f)).includes('取り込む'), true)
  } finally { f.stop(); none.stop() }
})

test('推薦されたテンプレートを1行ずつ表示し、押すとテンプレートから分析案を作って親へ渡す(AIは使わない)', async () => {
  const templates = [{ id: 7, version: 2, name: '<b>月別</b>', category_label: '出荷', purpose: '目的7', date_from: '2026-08-01', date_to: '2026-09-30' }, { id: 9, version: 1, name: '製品別', purpose: '目的9', date_from: '2026-01-01', date_to: '2026-01-31' }]
  const f = setup({}, { consult: async () => reply({ templates }) })
  try {
    f.state.input.value = '相談'; await f.state.send()
    const text = (await html(f)).replace(/<!--.*?-->/g, '')
    assert.ok(text.includes('近い承認済みテンプレート（2件）'))
    assert.ok(text.includes('テンプレート7（版2） / &lt;b&gt;月別&lt;/b&gt; / カテゴリ: 出荷 / 目的: 目的7 / 期間: 2026-08-01 ～ 2026-09-30')); assert.equal(text.includes('<b>月別</b>'), false)
    await f.state.useTemplate(templates[0])
    assert.deepEqual(f.calls.filter(c => c[0] === 'createTemplatePlan'), [['createTemplatePlan', 7]])
    assert.deepEqual(f.events, [['plan-created', { id: 'new-plan', template: { id: 7 } }]])
  } finally { f.stop() }
})

test('テンプレートの再利用が失敗したときは、固定文を出す(409)', async () => {
  const f = setup({}, { createTemplatePlan: async () => { const e = new Error('x'); e.response = { status: 409, data: { detail: 'SECRET' } }; throw e } })
  try {
    await f.state.useTemplate({ id: 1 })
    assert.ok(f.state.error.value.includes('再利用できません')); assert.equal(f.state.error.value.includes('SECRET'), false)
    assert.deepEqual(f.events, [])
  } finally { f.stop() }
})

test('やり直すと、履歴・文案・推薦・エラーを消す。送信中は消さない', async () => {
  const f = setup({}, { consult: async () => reply({ draft: { purpose: '文案', date_from: null, date_to: null }, templates: [{ id: 1, version: 1, name: 'n', purpose: 'p', date_from: '2026-01-01', date_to: '2026-01-31' }] }) })
  try {
    f.state.input.value = '相談'; await f.state.send()
    f.state.busy.value = 'send'; f.state.reset(); assert.equal(f.state.messages.value.length, 2)
    f.state.busy.value = ''; f.state.reset()
    assert.deepEqual([f.state.messages.value, f.state.draft.value, f.state.templates.value], [[], null, []])
  } finally { f.stop() }
})

test('案内文: 社外へ送らないこと・保存されないこと・数値を知らないことを明記し、分析案がある間は使えない理由を出す', async () => {
  const f = setup()
  const planned = setup({ plan: { id: 'p' } })
  const viewer = setup({ canEdit: false })
  try {
    const text = await html(f)
    for (const part of ['社外へ送りません', '保存されません', 'AIは数値を知らず']) assert.ok(text.includes(part), part)
    assert.ok((await html(planned)).includes('分析案を作った後は使えません'))
    assert.ok((await html(viewer)).includes('編集権限が必要です'))
  } finally { f.stop(); planned.stop(); viewer.stop() }
})

const EXT = { provider: 'openrouter', model: 'qwen/qwen3.8-27b:free', external: true, providerLabel: 'OpenRouter' }

test('社外のAIを選んでいるときは、了承するまで送れない。了承後は、選んだAI・モデルと了承を付けて送る(社外)', async () => {
  const f = setup(EXT)
  try {
    f.state.input.value = 'ACMEの件'
    await f.state.send()
    assert.equal(sends(f).length, 0, '了承前は送らない')
    f.state.externalAck.value = true
    await f.state.send()
    assert.deepEqual(sends(f)[0][1], { messages: [{ role: 'user', content: 'ACMEの件' }], provider: 'openrouter', model: 'qwen/qwen3.8-27b:free', external_confirmed: true })
  } finally { f.stop() }
})

test('ローカルQwenのときは、了承なしで送れ、了承の印は付けない(社外の欄も出さない)', async () => {
  const f = setup({ provider: 'qwen' })
  try {
    f.state.input.value = '相談'
    await f.state.send()
    assert.deepEqual(sends(f)[0][1], { messages: [{ role: 'user', content: '相談' }], provider: 'qwen' })
    const text = await html(f)
    assert.equal(text.includes('了承します'), false); assert.ok(text.includes('社外へ送りません'))
  } finally { f.stop() }
})

test('社外のAIを選び直したら、了承を取り直す(AI・モデルが変わったとき)', async () => {
  const f = setup(EXT)
  try {
    f.state.externalAck.value = true
    f.props.model = 'other/model'
    assert.equal(f.state.externalAck.value, false)
    f.state.externalAck.value = true
    f.props.provider = 'deepseek'
    assert.equal(f.state.externalAck.value, false)
    f.state.externalAck.value = true
    f.props.external = false
    assert.equal(f.state.externalAck.value, false)
  } finally { f.stop() }
})

test('社外へ送った内容(置換後)を、送った発言の下に表示する。履歴をAPIへ送るときは、表示用の項目を含めない(社外)', async () => {
  const f = setup(EXT, { consult: async () => reply({ sent_text: 'CUST-001の件', external: true }) })
  try {
    f.state.externalAck.value = true
    f.state.input.value = 'ACMEの件'
    await f.state.send()
    f.state.input.value = '続き'
    await f.state.send()
    const text = (await html(f)).replace(/<!--.*?-->/g, '')
    assert.ok(text.includes('社外へ送った内容（置換後）: CUST-001の件'))
    assert.deepEqual(sends(f)[1][1].messages.map(m => Object.keys(m).sort()), [['content', 'role'], ['content', 'role'], ['content', 'role']], 'sentなどの表示用の項目は送らない')
  } finally { f.stop() }
})

test('社外のときは、文案にコードが含まれ得る注意と、置換して送る案内を出す。選んだAIが使えないときは、送れず理由を出す(代替しない)', async () => {
  const draft = { purpose: 'CUST-001の出荷', date_from: null, date_to: null }
  const f = setup(EXT, { consult: async () => reply({ draft, sent_text: 'x', external: true }) })
  const down = setup({ ...EXT, providerAvailable: false })
  try {
    f.state.externalAck.value = true; f.state.input.value = '相談'; await f.state.send()
    const text = await html(f)
    for (const part of ['登録名称をコードへ置換して送ります', '置換後の内容を送ることを了承します', '実名へ直してください']) assert.ok(text.includes(part), part)
    down.state.externalAck.value = true; down.state.input.value = '相談'; await down.state.send()
    assert.equal(sends(down).length, 0)
    assert.ok((await html(down)).includes('選んだAIは、いま使えません')); assert.ok((await html(down)).includes('自動では切り替えません'))
  } finally { f.stop(); down.stop() }
})

test('了承が必要という409は、固定文を出す(社外)', async () => {
  const f = setup(EXT, { consult: async () => { const e = new Error('x'); e.response = { status: 409, data: { detail: 'SECRET' } }; throw e } })
  try {
    f.state.externalAck.value = true; f.state.input.value = '相談'; await f.state.send()
    assert.ok(f.state.error.value.includes('了承が必要')); assert.equal(f.state.error.value.includes('SECRET'), false)
    assert.equal(f.state.input.value, '相談')
  } finally { f.stop() }
})

test('置換できない発言(422)・テンプレート(424)・AI設定(400)・処理の障害(503)は、固定文を出す。入力は残し、APIの本文は出さない(社外)', async () => {
  const expectations = { 400: 'AIの選択が正しくありません', 422: '置換できない名称が含まれます', 424: '管理者へ、名称の登録の確認', 503: 'コード置換の処理を使えません' }
  for (const [status, part] of Object.entries(expectations)) {
    const f = setup(EXT, { consult: async () => { const e = new Error('x'); e.response = { status: Number(status), data: { detail: 'SECRET-名称' } }; throw e } })
    try {
      f.state.externalAck.value = true; f.state.input.value = '相談'; await f.state.send()
      assert.ok(f.state.error.value.includes(part), `${status}: ${part}`); assert.equal(f.state.error.value.includes('SECRET'), false)
      assert.equal(f.state.input.value, '相談'); assert.deepEqual(f.state.messages.value, [])
    } finally { f.stop() }
  }
})

test('送信中にAIを選び直したら、前のAIの返事は使わない(履歴に入れず、入力を残す)(社外)', async () => {
  let release
  const gate = new Promise(resolve => { release = resolve })
  const f = setup(EXT, { consult: async () => { await gate; return reply({ sent_text: 'x', external: true }) } })
  try {
    f.state.externalAck.value = true; f.state.input.value = '相談'
    const sending = f.state.send()
    f.props.model = 'other/model'
    release(); await sending
    assert.deepEqual(f.state.messages.value, [])
    assert.equal(f.state.input.value, '相談')
    assert.ok(f.state.error.value.includes('AIを切り替えたため'))
    assert.equal(f.state.busy.value, '')
  } finally { f.stop() }
})

test('社外へ送る内容として、承認済みテンプレートの名称と目的も案内する(社外)', async () => {
  const f = setup(EXT)
  try { assert.ok((await html(f)).includes('承認済みテンプレートの名称と目的')) } finally { f.stop() }
})

test('履歴の発言者は、ログイン中の利用者名で表示する。名前がなければ「あなた」。AIは「AI」(利用者名)', async () => {
  const named = setup({ userName: '王 惟楨' })
  const anonymous = setup()
  try {
    for (const f of [named, anonymous]) { f.state.input.value = '8月と9月の入荷を比較して'; await f.state.send() }
    const text = (await html(named)).replace(/<!--.*?-->/g, '')
    assert.ok(text.includes('王 惟楨:')); assert.equal(text.includes('あなた:'), false); assert.ok(text.includes('AI:'))
    const plain = (await html(anonymous)).replace(/<!--.*?-->/g, '')
    assert.ok(plain.includes('あなた:'))
    // 名前は表示だけ。AIへ送る内容には含めない
    assert.equal(JSON.stringify(sends(named)[0][1]).includes('王'), false)
  } finally { named.stop(); anonymous.stop() }
})

test('履歴をAPIへ送るときは、role・contentだけ(表示用の項目sent・返事の追加情報は含めない)。返事に署名があっても、付けない', async () => {
  const f = setup(EXT, { consult: async () => reply({ reply_signature: 'ignored', sent_text: 'x', external: true }) })
  try {
    f.state.externalAck.value = true
    f.state.input.value = '一回目'; await f.state.send()
    f.state.input.value = '二回目'; await f.state.send()
    assert.deepEqual(sends(f)[1][1].messages.map(m => Object.keys(m).sort()), [['content', 'role'], ['content', 'role'], ['content', 'role']])
  } finally { f.stop() }
})

test('推薦されたテンプレートを参考に分析する: 識別だけを分析の画面へ渡し、AIもAPIも呼ばない。再利用のボタンは残る(2026-10-09)', async () => {
  const templates = [{ id: 7, version: 2, name: '<b>月別</b>', category_label: '出荷', purpose: '目的7', date_from: '2026-08-01', date_to: '2026-09-30', python_code: '渡さない' }]
  const f = setup({}, { consult: async () => reply({ templates }) })
  try {
    f.state.input.value = '月別の出荷'
    await f.state.send()
    const text = await html(f)
    assert.ok(text.includes('このテンプレートを参考に分析する')); assert.ok(text.includes('このテンプレートで分析案を作る'))
    assert.equal(text.includes('<b>月別</b>'), false, 'HTMLは解釈しない')
    f.calls.length = 0
    f.state.selectReference(templates[0])
    assert.deepEqual(f.calls, [], 'AIもAPIも呼ばない')
    assert.deepEqual(f.events.at(-1), ['reference-selected', { id: 7, version: 2, name: '<b>月別</b>', status: 'approved' }], '識別だけを渡す(目的・コードは渡さない)')
  } finally { f.stop() }
})

test('テンプレートを参考に分析する(相談画面): 編集権限がない・操作中・不正な指定では、渡さない', async () => {
  const templates = [{ id: 7, version: 2, name: 'n', category_label: '出荷', purpose: 'p', date_from: '2026-08-01', date_to: '2026-09-30' }]
  for (const [label, propsInit, item] of [['権限なし', { canEdit: false }, templates[0]], ['操作中', { blocked: true }, templates[0]], ['不正', {}, { id: '7' }], ['空', {}, null]]) {
    const f = setup(propsInit)
    try {
      f.state.selectReference(item)
      assert.deepEqual(f.events, [], label)
    } finally { f.stop() }
  }
})

test('参考のボタンは、idが整数でない推薦では、無効になる(関数の拒否条件と一致。Codex P3)', async () => {
  const f = setup({}, { consult: async () => reply({ templates: [{ id: '7', version: 1, name: 'n', category_label: '出荷', purpose: 'p', date_from: '2026-08-01', date_to: '2026-09-30' }] }) })
  try {
    f.state.input.value = '出荷'
    await f.state.send()
    assert.match(await html(f), /<button[^>]*disabled[^>]*>このテンプレートを参考に分析する/)
  } finally { f.stop() }
})

