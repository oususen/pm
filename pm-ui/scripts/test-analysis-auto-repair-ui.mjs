// 追加送信の連鎖・同意・離脱停止を、両画面と模擬APIで確認する。実AIは呼ばない。
import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import test from 'node:test'
import * as Vue from 'vue'
import { parse } from '@vue/compiler-sfc'
import { useAnalysisErrorNotices } from '../src/composables/analysisErrorNotices.js'

function plan(attempts = 0, token = null, status = 'none') {
  return { id: 'repair-ui-test', revision: attempts * 2 + 3, status: 'data_approved',
    proposal: { provider: 'anthropic', model: 'test', title: '工程分析', purpose: '工程別に集計',
      steps: ['集計'], outputs: ['表'], datasets: [], date_from: '2026-09-01', date_to: '2026-09-30' },
    codegen_state: { status, attempts, max_attempts: 4, inflight_state: null, repair_token: token },
    codegen: { status, attempts, reasons: token ? ['python_unpack_mismatch'] : [] } }
}

function setup(name) {
  const { descriptor } = parse(readFileSync(new URL(`../src/views/ai/${name}.vue`, import.meta.url), 'utf8'))
  const props = Vue.reactive({ canEdit: true, canViewAll: false, request: null, visible: true, userName: 'test' })
  const scope = Vue.effectScope(), cleanup = [], calls = []
  const methods = {
    codegenPreview: async (_id, body) => ({ data: { confirmation: 'signed', auto_repair: body.auto_repair } }),
    generateCode: async () => ({ data: plan(1, null, 'generated') }),
    getPlan: async () => ({ data: plan(1, null, 'failed') }),
  }
  const api = { aiAnalysis: Object.fromEntries(Object.keys(methods).map(key => [key, async (...args) => {
    calls.push([key, ...args]); return methods[key](...args)
  }])) }
  const injections = { ref: Vue.ref, computed: Vue.computed, watch: Vue.watch,
    onMounted: () => {}, onBeforeUnmount: fn => cleanup.push(fn), defineProps: () => props,
    api, window: { confirm: () => true }, useAnalysisErrorNotices, openRequestDialog: () => {} }
  const create = new Function(...Object.keys(injections), descriptor.scriptSetup.content.replace(/^import .*\r?\n/gm, '')
    + '\nreturn {plan,busy,error,autoRepair,codePreview,codeSendAccepted,prepareCodePreview,generateCode};')
  const state = scope.run(() => create(...Object.values(injections)))
  state.plan.value = plan()
  return { state, props, calls, methods, stop() { cleanup.forEach(fn => fn()); scope.stop() } }
}

async function consent(f, auto = true) {
  f.state.autoRepair.value = auto
  await f.state.prepareCodePreview()
  f.state.codeSendAccepted.value = true
}

for (const name of ['AIAnalysis', 'AIAnalysisUser']) {
  test(`${name}: 同意した不一致のみ修正し、次の版・tokenで送る`, async () => {
    const f = setup(name)
    try {
      await consent(f)
      let count = 0
      f.methods.generateCode = async () => ({ data: ++count === 1 ? plan(1, 'repair-token', 'failed') : plan(2, null, 'generated') })
      await f.state.generateCode()
      const sends = f.calls.filter(c => c[0] === 'generateCode')
      assert.equal(sends.length, 2)
      assert.deepEqual(sends[1][2], { revision: 5, auto_repair: true, repair_token: 'repair-token' })
      assert.equal(f.state.plan.value.codegen_state.status, 'generated')
      assert.equal(f.state.busy.value, '')
    } finally { f.stop() }
  })

  test(`${name}: 単発同意は追加送信を許可せず、同意後の設定変更も送信しない`, async () => {
    const f = setup(name)
    try {
      await consent(f, false)
      f.methods.generateCode = async () => ({ data: plan(1, 'unexpected-token', 'failed') })
      await f.state.generateCode()
      assert.equal(f.calls.filter(c => c[0] === 'generateCode').length, 1)
      f.state.plan.value = plan()
      await consent(f, false)
      f.state.autoRepair.value = true
      await f.state.generateCode()
      assert.equal(f.calls.filter(c => c[0] === 'generateCode').length, 1)
    } finally { f.stop() }
  })

  test(`${name}: 送信中のタブ離脱・復帰後は旧応答から修正を再開しない`, async () => {
    const f = setup(name)
    try {
      await consent(f)
      let resolve
      f.methods.generateCode = () => new Promise(done => { resolve = done })
      const pending = f.state.generateCode()
      f.props.visible = false
      f.props.visible = true
      resolve({ data: plan(1, 'repair-token', 'failed') })
      await pending
      assert.equal(f.calls.filter(c => c[0] === 'generateCode').length, 1)
    } finally { f.stop() }
  })

  test(`${name}: 修正通信失敗で停止し、同じ要求を再送しない`, async () => {
    const f = setup(name)
    try {
      await consent(f)
      let count = 0
      f.methods.generateCode = async () => {
        if (++count === 1) return { data: plan(1, 'repair-token', 'failed') }
        throw { response: { status: 503, data: { detail: '通信失敗' } } }
      }
      await f.state.generateCode()
      assert.equal(f.calls.filter(c => c[0] === 'generateCode').length, 2)
      assert.equal(f.state.error.value, '通信失敗')
      assert.equal(f.state.busy.value, '')
    } finally { f.stop() }
  })

  test(`${name}: 編集権限の喪失・復帰後も旧応答から修正を再開しない`, async () => {
    const f = setup(name)
    try {
      await consent(f)
      let resolve
      f.methods.generateCode = () => new Promise(done => { resolve = done })
      const pending = f.state.generateCode()
      f.props.canEdit = false
      f.props.canEdit = true
      resolve({ data: plan(1, 'repair-token', 'failed') })
      await pending
      assert.equal(f.calls.filter(c => c[0] === 'generateCode').length, 1)
    } finally { f.stop() }
  })
}
