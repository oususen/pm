<template>
  <main class="analysis-workspace">
    <header><h1>AI分析</h1><span>分析案・承認</span></header>
    <p class="notice">分析案とデータ範囲の承認まで対応しています。SQL／Python実行・結果生成・テンプレート保存は未実装です。外部AIへは送信しません。</p>
    <p v-if="!canEdit">閲覧のみの権限です。分析案の作成・承認には「AI分析」の編集権限が必要です。</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <label for="analysis-purpose">分析目的</label>
    <textarea id="analysis-purpose" v-model="purpose" rows="3" :readonly="!canEdit || !!busy || !!plan" placeholder="何を調べ、どの判断に使いたいかを入力してください。"></textarea>
    <p v-if="source" class="source">起点画面: {{ source }}（会話履歴・検索結果は引き継ぎません）</p>
    <div class="period">
      <label>開始日 <input v-model="dateFrom" type="date" :disabled="!canEdit || !!busy || !!plan"></label>
      <label>終了日 <input v-model="dateTo" type="date" :disabled="!canEdit || !!busy || !!plan"></label>
      <span>利用AI: {{ options ? options.model : '確認中' }}（ローカルQwen）</span>
    </div>
    <p>対象: 入荷実績・出荷実績の指定期間の全登録行。追加の絞り条件・資料取込み、生産・仕損・中断・残業は未対応です。</p>
    <p v-if="options && !options.available" class="error">ローカルQwenが無効、またはモデル設定が一致していません。AI設定を確認してください。</p>
    <button v-if="!plan" type="button" :disabled="!canCreate" @click="createPlan">{{ busy === 'create' ? '分析案を作成中…' : '分析案を作成' }}</button>
    <section v-if="plan" class="plan">
      <div class="plan-heading"><h2>{{ plan.proposal.title }}</h2><span>{{ statusLabel }}</span></div>
      <small>分析案ID: {{ plan.id }} / 版: {{ plan.revision }} / 有効期限: {{ formatDate(plan.expires_at) }}</small>
      <h3>1. 分析目的・手順</h3>
      <p>目的: {{ plan.proposal.purpose }}</p>
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
const plan = ref(null)
const busy = ref('')
const error = ref('')
let generation = 0
let disposed = false
const canCreate = computed(() => props.canEdit && !busy.value && options.value?.available && purpose.value.trim() && dateFrom.value && dateTo.value && dateFrom.value <= dateTo.value)
const statusLabel = computed(() => ({ awaiting_method: '分析案の承認待ち', awaiting_data: 'データ範囲の承認待ち', data_approved: 'データ範囲承認済み・未実行' })[plan.value?.status] || '')
const formatNumber = value => value == null ? '未確認' : Number(value).toLocaleString('ja-JP')
const formatDate = value => value?.replace('T', ' ').slice(0, 19) || ''

function resetPlan() {
  generation += 1
  plan.value = null
  error.value = ''
  busy.value = ''
}
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
    if (!disposed) options.value = response.data
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
function createPlan() {
  if (!canCreate.value) return
  perform('create', () => api.aiAnalysis.createPlan({ purpose: purpose.value.trim(), date_from: dateFrom.value, date_to: dateTo.value }))
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
.error { background: #fff0ee; color: #9a362b; padding: 8px; }
button:not(:disabled) { border-color: #168779; color: white; background: #168779; cursor: pointer; }
small { overflow-wrap: anywhere; }
</style>
