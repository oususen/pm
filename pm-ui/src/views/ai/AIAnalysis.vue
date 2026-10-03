<template>
  <main class="analysis-workspace">
    <header><h1>AI分析</h1><span>分析案・承認</span></header>
    <p class="notice">分析案とデータ範囲の承認まで対応しています。SQL／Python実行・結果生成・テンプレート保存は未実装です。{{ options?.notice || '' }}</p>
    <p v-if="!canEdit">閲覧のみの権限です。分析案の作成・承認には「AI分析」の編集権限が必要です。</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <label for="analysis-purpose">分析目的</label>
    <textarea id="analysis-purpose" v-model="purpose" rows="3" :readonly="!canEdit || !!busy || !!plan" placeholder="何を調べ、どの判断に使いたいかを入力してください。"></textarea>
    <p v-if="source" class="source">起点画面: {{ source }}（会話履歴・検索結果は引き継ぎません）</p>
    <div class="period">
      <label>開始日 <input v-model="dateFrom" type="date" :disabled="!canEdit || !!busy || !!plan"></label>
      <label>終了日 <input v-model="dateTo" type="date" :disabled="!canEdit || !!busy || !!plan"></label>
    </div>
    <div class="period">
      <label>AI
        <select v-model="provider" :disabled="!canEdit || !!busy || !!plan || !options" @change="onProviderChange">
          <option v-for="item in options?.providers || []" :key="item.provider" :value="item.provider" :disabled="!item.available">
            {{ item.label }}{{ item.available ? '' : '（利用不可）' }}
          </option>
        </select>
      </label>
      <label>モデル
        <select v-model="model" :disabled="!canEdit || !!busy || !!plan || !selectedProvider" @change="onModelChange">
          <option v-for="item in selectedProvider?.models || []" :key="item.id" :value="item.id">{{ item.label }}</option>
        </select>
      </label>
    </div>
    <p v-if="selectedProvider?.external" class="warning">社外サービス（{{ selectedProvider.label }}）へ、名称を登録コードに置換した分析目的・期間・公開ビューの説明を送ります。DBの明細行・件数は送りません。未登録の人名・社名は自動判別できません。送信前の目的文を確認し、名称や機密が残っていれば書き直してください。</p>
    <p v-if="selectedProvider && !selectedProvider.available" class="error">{{ selectedProvider.label }}は利用できません: {{ selectedProvider.reason }}</p>
    <p>対象: 入荷実績・出荷実績の指定期間の全登録行。追加の絞り条件・資料取込み、生産・仕損・中断・残業は未対応です。</p>
    <template v-if="!plan">
      <button v-if="selectedProvider?.external" type="button" :disabled="!canCreate" @click="prepareExternalPreview">{{ busy === 'external-preview' ? '目的文を確認中…' : '社外送信する目的文を確認' }}</button>
      <section v-if="selectedProvider?.external && externalPreview" class="dataset">
        <h2>社外送信前の確認</h2>
        <p>送信先: {{ selectedProvider.label }} / モデル: {{ externalPreview.model }}</p>
        <p>期間: {{ externalPreview.date_from }} ～ {{ externalPreview.date_to }}</p>
        <p class="external-purpose">送信する目的文: {{ externalPreview.purpose }}</p>
        <p>この目的文と期間、公開ビューの説明を送信します。確認だけでは社外AIへ送信しません。</p>
        <label><input v-model="externalAccepted" type="checkbox" :disabled="!!busy || !canEdit">名称ではなく登録コードになっており、未登録の人名・社名・機密を含まないことを確認しました</label>
      </section>
      <button v-if="!selectedProvider?.external || externalPreview" type="button" :disabled="!canCreate || (selectedProvider?.external && !externalAccepted)" @click="createPlan">{{ busy === 'create' ? '分析案を作成中…' : selectedProvider?.external ? '確認した内容を社外AIへ送って分析案を作成' : '分析案を作成' }}</button>
    </template>
    <section v-if="plan" class="plan">
      <div class="plan-heading"><h2>{{ plan.proposal.title }}</h2><span>{{ statusLabel }}</span></div>
      <small>分析案ID: {{ plan.id }} / 版: {{ plan.revision }} / 有効期限: {{ formatDate(plan.expires_at) }} / 作成AI: {{ planProviderLabel }}</small>
      <h3>1. 分析目的・手順</h3>
      <p>目的: {{ plan.proposal.purpose }}</p>
      <p v-if="plan.proposal.external_purpose">社外送信した目的文: {{ plan.proposal.external_purpose }}</p>
      <ol><li v-for="(step, index) in plan.proposal.steps" :key="index">{{ step }}</li></ol>
      <p>出力案: {{ plan.proposal.outputs.join('、') }}</p>
      <p v-if="plan.method_approved_at">手順承認日時: {{ formatDate(plan.method_approved_at) }}</p>
      <button v-if="plan.status === 'awaiting_method'" :disabled="!canEdit || !!busy" @click="approve('method')">分析案・手順を承認</button>
      <template v-if="plan.status !== 'awaiting_method'">
        <h3>2. 必要なデータ範囲</h3>
        <p>期間: {{ plan.proposal.date_from }} ～ {{ plan.proposal.date_to }} / 条件: {{ plan.proposal.conditions }}</p>
        <div v-for="dataset in plan.proposal.datasets" :key="dataset.view" class="dataset">
          <p>ビュー: {{ dataset.view }} / 必要フィールド: {{ dataset.fields.join('、') }}</p>
          <p v-if="plan.preview">対象行数: {{ formatNumber(plan.preview.datasets.find(item => item.view === dataset.view)?.rows) }}行</p>
        </div>
        <p>追加資料: なし（資料の取込みは未実装）</p>
        <template v-if="plan.preview">
          <p>対象行数の合計: {{ formatNumber(plan.preview.total_rows) }}行 / 取得行数の上限: {{ formatNumber(plan.preview.max_fetch_rows) }}行</p>
          <small>件数確認日時: {{ formatDate(plan.preview.counted_at) }}。数量の合計ではありません。実行時には最新スナップショットで再確認が必要です。</small>
          <p v-if="plan.preview.over_limit" class="error">対象が上限を超えました。一部だけを採用せず、期間を絞って分析案を作り直してください。</p>
        </template>
        <div v-if="plan.status === 'awaiting_data'" class="actions">
          <button :disabled="!canEdit || !!busy" @click="preview">{{ busy === 'preview' ? '件数を確認中…' : '対象件数を確認' }}</button>
          <button :disabled="!canEdit || !!busy || !plan.preview || plan.preview.over_limit" @click="approve('data')">データ範囲を承認</button>
        </div>
        <p v-if="plan.data_approved_at" role="status">データ承認日時: {{ formatDate(plan.data_approved_at) }}。承認は完了しましたが、分析はまだ実行していません。</p>
        <button disabled>分析を実行（実行基盤は未実装）</button>
      </template>
      <div class="actions">
        <button :disabled="!!busy" @click="refresh">分析案の状態を再取得</button>
        <button v-if="canEdit" :disabled="!!busy" @click="resetPlan">目的・期間を変更して作り直す</button>
      </div>
    </section>
    <small>タブ切替時は入力・承認状態を保持します。再読込・画面離脱・利用者切替で画面内の状態は消えます。未保存の分析案は設定された期限でRedisから消え、承認しても期限は延長しません。</small>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import api from '../../api/client'

const props = defineProps({ request: { type: Object, default: null }, canEdit: { type: Boolean, default: false } })
const purpose = ref('')
const source = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const options = ref(null)
const provider = ref('')
const model = ref('')
const plan = ref(null)
const busy = ref('')
const error = ref('')
const externalPreview = ref(null)
const externalAccepted = ref(false)
let generation = 0
let disposed = false
let lastSelection = { provider: '', model: '' }
// 有料モデルは、検索AIと同じく選択時に確認し、同じ画面の間は1回の承認で再確認しない。
const OPENROUTER_PAID_MODELS = new Set(['google/gemma-4-26b-a4b-it'])
const paidApproved = new Set()
const selectedProvider = computed(() => options.value?.providers.find(item => item.provider === provider.value) || null)
const canCreate = computed(() => props.canEdit && !busy.value && selectedProvider.value?.available && model.value && purpose.value.trim() && dateFrom.value && dateTo.value && dateFrom.value <= dateTo.value)
const planProviderLabel = computed(() => {
  const proposal = plan.value?.proposal
  const label = options.value?.providers.find(item => item.provider === proposal?.provider)?.label || proposal?.provider || ''
  return proposal?.model ? `${label} / ${proposal.model}` : label
})

function defaultModelFor(key) {
  const current = options.value?.providers.find(item => item.provider === key)
  return current?.models.some(item => item.id === current.default_model) ? current.default_model : (current?.models[0]?.id || '')
}
function paidKey() {
  if (provider.value === 'deepseek') return { key: 'deepseek', message: 'DeepSeekは有料です。使いますか？' }
  if (provider.value === 'openrouter' && OPENROUTER_PAID_MODELS.has(model.value)) {
    return { key: model.value, message: 'このモデル（Gemma 4 26B A4B）は有料です。使いますか？' }
  }
  return null
}
function confirmSelection() {
  const paid = paidKey()
  if (paid && !paidApproved.has(paid.key)) {
    if (window.confirm(paid.message)) paidApproved.add(paid.key)
    else { provider.value = lastSelection.provider; model.value = lastSelection.model; return }
  }
  lastSelection = { provider: provider.value, model: model.value }
}
function onProviderChange() {
  model.value = defaultModelFor(provider.value)
  confirmSelection()
}
function onModelChange() { confirmSelection() }
const statusLabel = computed(() => ({ awaiting_method: '分析案の承認待ち', awaiting_data: 'データ範囲の承認待ち', data_approved: 'データ範囲承認済み・未実行' })[plan.value?.status] || '')
const formatNumber = value => value == null ? '未確認' : Number(value).toLocaleString('ja-JP')
const formatDate = value => value?.replace('T', ' ').slice(0, 19) || ''

function resetPlan() {
  generation += 1
  plan.value = null
  error.value = ''
  busy.value = ''
  externalPreview.value = null
  externalAccepted.value = false
}
// 入力・AI選択を変えたら、以前の送信確認は使い回さない。
watch([purpose, dateFrom, dateTo, provider, model], () => {
  externalPreview.value = null
  externalAccepted.value = false
}, { flush: 'sync' })
watch(() => props.request, (request) => {
  if (!request) return
  resetPlan()
  // 検索結果や会話履歴は受け取らず、質問文と起点だけを画面内で引き継ぐ。
  purpose.value = request.question || ''
  source.value = request.screenContext || ''
}, { immediate: true })
onBeforeUnmount(() => { disposed = true; generation += 1 })
onMounted(async () => {
  try {
    const response = await api.aiAnalysis.options()
    if (disposed) return
    options.value = response.data
    // 初期選択は検索AIと同じ。選べない場合は、選べる先頭のAIへ切り替える。
    const initial = response.data.providers.find(item => item.provider === response.data.default_provider && item.available)
      || response.data.providers.find(item => item.available)
    provider.value = initial?.provider || response.data.default_provider
    model.value = defaultModelFor(provider.value)
    lastSelection = { provider: provider.value, model: model.value }
  } catch (exception) {
    if (!disposed) error.value = exception.response?.data?.detail || '分析用AI設定を確認できませんでした。'
  }
})

async function perform(action, operation) {
  if (busy.value) return
  const current = ++generation
  busy.value = action
  error.value = ''
  try {
    const response = await operation()
    if (!disposed && current === generation) plan.value = response.data
  } catch (exception) {
    if (disposed || current !== generation) return
    error.value = exception.response?.data?.detail || '分析案の操作に失敗しました。'
    if ([404, 410].includes(exception.response?.status)) plan.value = null
    if (exception.response?.status === 409 && plan.value) {
      // 競合した操作を自動再実行せず、利用者が最新の内容を再確認する。
      try {
        const response = await api.aiAnalysis.getPlan(plan.value.id)
        if (!disposed && current === generation) plan.value = response.data
      } catch (refreshError) {
        if (!disposed && current === generation && [404, 410].includes(refreshError.response?.status)) plan.value = null
      }
    }
  } finally {
    if (!disposed && current === generation) busy.value = ''
  }
}
function planningInput() {
  return { purpose: purpose.value.trim(), date_from: dateFrom.value, date_to: dateTo.value, provider: provider.value, model: model.value }
}
async function prepareExternalPreview() {
  if (!canCreate.value || !selectedProvider.value?.external) return
  const current = ++generation
  busy.value = 'external-preview'
  error.value = ''
  externalPreview.value = null
  externalAccepted.value = false
  try {
    const response = await api.aiAnalysis.externalPreview(planningInput())
    if (!disposed && current === generation) externalPreview.value = response.data
  } catch (exception) {
    if (!disposed && current === generation) error.value = exception.response?.data?.detail || '社外送信する目的文を確認できませんでした。社外AIへは送信していません。'
  } finally {
    if (!disposed && current === generation) busy.value = ''
  }
}
function createPlan() {
  if (!canCreate.value) return
  if (selectedProvider.value.external && (!externalPreview.value || !externalAccepted.value)) return
  // 初期選択が有料の場合も、実送信前には料金確認を必ず通す。
  const paid = paidKey()
  if (paid && !paidApproved.has(paid.key)) {
    if (!window.confirm(paid.message)) return
    paidApproved.add(paid.key)
  }
  const data = planningInput()
  if (selectedProvider.value.external) data.external_confirmation = externalPreview.value.confirmation
  perform('create', () => api.aiAnalysis.createPlan(data))
}
function approve(stage) {
  if (!props.canEdit || !plan.value) return
  perform('approve', () => api.aiAnalysis.approve(plan.value.id, { revision: plan.value.revision, stage }))
}
function preview() {
  if (!props.canEdit || !plan.value) return
  perform('preview', () => api.aiAnalysis.preview(plan.value.id, { revision: plan.value.revision }))
}
function refresh() {
  if (!plan.value) return
  perform('refresh', () => api.aiAnalysis.getPlan(plan.value.id))
}
</script>

<style scoped>
.analysis-workspace { padding: 20px; max-width: 980px; margin: auto; color: #334b50; }
header { display: flex; align-items: center; gap: 12px; }
h1 { font-size: 22px; margin: 0; }
header span { background: #fff0d0; color: #805b19; border-radius: 5px; padding: 4px 8px; }
.notice { background: #edf6f5; border-left: 3px solid #168779; padding: 12px; line-height: 1.7; }
label { display: block; font-weight: 700; margin-bottom: 8px; }
textarea { box-sizing: border-box; width: 100%; border: 1px solid #b9cccc; border-radius: 8px; padding: 12px; font: inherit; resize: vertical; }
p { line-height: 1.7; }
button { padding: 10px 16px; border: 1px solid #d4dddd; border-radius: 6px; color: #647777; background: #eef2f2; }
small { display: block; margin-top: 12px; color: #657b80; }
.period, .actions, .plan-heading { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; margin: 10px 0; }
.period label { margin: 0; }
input { padding: 4px; font: inherit; }
.plan { border: 1px solid #d1dddd; border-radius: 6px; padding: 12px; margin-top: 12px; }
.plan h2 { font-size: 18px; margin: 0; }
.plan h3 { font-size: 16px; margin: 14px 0 8px; }
.dataset { background: #f4f8f8; padding: 1px 8px; overflow-wrap: anywhere; }
.external-purpose { white-space: pre-wrap; }
.error { background: #fff0ee; color: #9a362b; padding: 8px; }
.warning { background: #fff8e6; border-left: 3px solid #d9a21b; color: #6f5314; padding: 8px 10px; }
select { padding: 4px; font: inherit; max-width: 100%; }
button:not(:disabled) { border-color: #168779; color: white; background: #168779; cursor: pointer; }
small { overflow-wrap: anywhere; }
</style>
