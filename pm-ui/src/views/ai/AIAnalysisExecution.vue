<template>
  <section class="execution">
    <AnalysisErrorBanner v-if="errorNotices.renderBanner" :notices="errorNotices.notices.value" />
    <h2>分析の実行・結果</h2>
    <p>{{ availability?.notice || '実行基盤の状態を確認してください。' }}</p>
    <button :disabled="!!busy" @click="checkAvailability">実行基盤の状態を確認</button>
    <template v-if="plan?.template?.status === 'pending_admin'">
      <p class="template-unapproved" role="alert">システム管理者未承認のテンプレート（テンプレート{{ plan.template.id }}・版{{ plan.template.version }}）から作成した分析案です。</p>
      <label><input v-model="templateConfirmed" type="checkbox" :disabled="!!busy">管理者の承認前であることと、保存済みのSQL・Pythonの内容を確認したうえで、実行します</label>
    </template>
    <p v-else-if="plan?.template">テンプレート{{ plan.template.id }}（版{{ plan.template.version }}）から作成した分析案です。</p>
    <button :disabled="!canExecute" @click="execute">分析を実行</button>
    <p v-if="!canEdit">閲覧のみです。実行・中止にはAI分析の編集権限が必要です。</p>
    <div v-if="!job && plan?.execution?.job_id">
      <p>{{ monitor.message.value || '実行情報を確認しています。まだ実行状態・後始末は確認できていません。' }}</p>
      <button :disabled="!!busy" @click="refreshJob">実行状態・結果を再取得</button>
    </div>
    <template v-if="job">
      <p role="status" :class="{ 'execution-failed': job.status === 'failed' }">実行: {{ statusLabel }} / 開始受付: {{ formatDate(job.created_at) }} / 終了: {{ formatDate(job.finished_at) || '未確認' }}</p>
      <p v-if="jobDetail" :class="{ 'execution-failed': job.status === 'failed' }">{{ jobDetail }}</p>
      <small>この実行のコード全体SHA-256: {{ job.executed_code_sha256 }}</small>
      <p v-if="plan?.codegen?.executed_code_sha256 && plan.codegen.executed_code_sha256 !== job.executed_code_sha256">現在表示されているSQL・Pythonは、この実行のコードとは異なります。上の実行ハッシュで区別してください。</p>
      <p v-if="monitor.message.value" class="monitor-message">{{ monitor.message.value }}</p>
      <p v-else>進行中の実行状態だけを自動更新します（暫定3秒間隔・上限20分）。実行・中止・再送は自動で行いません。</p>
      <button :disabled="!!busy" @click="refreshJob">実行状態・結果を再取得</button>
      <button :disabled="!canCancel" @click="cancel">実行を中止</button>
      <p v-if="job.status === 'cancel_requested'">中止を要求しました。停止・削除の完了はまだ確認していません。</p>
      <p v-if="job.status === 'unknown'">状態不明です。自動再実行はしません。管理者が実行基盤・履歴・後始末を確認してください。</p>
      <p>後始末: DB接続={{ job.cleanup?.db_connection || '未確認' }} / コンテナ={{ job.cleanup?.container || '未確認' }}</p>
      <p v-if="job.status === 'cancelled' && !cleanupComplete">中止後の後始末は未完了／未確認です。中止完了とは扱いません。</p>
      <p>実行時の期間: {{ job.scope?.date_from }} ～ {{ job.scope?.date_to }} / 条件: {{ job.scope?.conditions }}</p>
      <p v-for="dataset in job.scope?.datasets || []" :key="dataset.view">{{ dataset.view }} / 取得行数: {{ job.counts?.[dataset.view] ?? '未確認' }}行（分析のために取り出した行数。絞り込み前で、結果の行数ではありません）</p>
      <p>行数は数量の合計ではありません。入荷はqty、出荷はquantityの集計結果を数量として確認してください。</p>
      <div :class="{ 'completion-notice': !!completionText, 'completion-success': monitor.notice.value?.status === 'success', 'completion-failed': monitor.notice.value?.status === 'failed', 'completion-attention': !!completionText && !['success', 'failed'].includes(monitor.notice.value?.status), 'completion-pulse': monitor.notice.value?.status === 'success' && !monitor.acknowledged.value }">
        <div class="completion-live" aria-live="polite" aria-atomic="true">
          <strong v-if="completionText">{{ completionText }}</strong>
        </div>
        <button v-if="monitor.notice.value?.status === 'success' && !monitor.acknowledged.value" @click="monitor.acknowledge">確認しました</button>
      </div>
      <template v-if="job.status === 'success' && job.result">
        <p>結果保持期限: {{ formatDate(job.result_expires_at) }}。結果本文はRedisに一時保持し、履歴には保存しません。</p>
        <article v-for="(table, index) in job.result.tables || []" :key="`table-${index}`">
          <h3>{{ table.name }}</h3>
          <p v-if="!(table.rows && table.rows.length)" class="empty-result" role="status">該当するデータがありません（0行）。条件に合う行がなかったため、表は空です。</p>
          <div class="scroll"><table><thead><tr><th v-for="(column, i) in table.columns" :key="i">{{ column }}</th></tr></thead>
            <tbody><tr v-for="(row, r) in table.rows" :key="r"><td v-for="(cell, c) in row" :key="c">{{ cell ?? 'NULL' }}</td></tr></tbody></table></div>
        </article>
        <article v-for="({ chart, plot }, index) in plottedCharts" :key="`chart-${index}`">
          <h3>{{ chart.title }}</h3>
          <p v-if="plot.nonNumeric">数値として描画できない値があります。元の値は下の表で確認してください。</p>
          <p v-if="!chart.x.length" class="empty-result" role="status">グラフにするデータがありません。</p>
          <svg v-if="chart.x.length" viewBox="0 0 640 240" role="img" :aria-label="chart.title">
            <line x1="40" x2="620" :y1="plot.baseline" :y2="plot.baseline" stroke="#667" />
            <text x="0" y="20">{{ plot.max }}</text><text x="0" y="210">{{ plot.min }}</text>
            <text x="40" y="235">{{ chart.x[0] }}</text><text x="620" y="235" text-anchor="end">{{ chart.x.at(-1) }}</text>
            <g v-for="(series, s) in chart.series" :key="s" :fill="colors[s % colors.length]" :stroke="colors[s % colors.length]">
              <template v-if="chart.kind === 'bar'"><rect v-for="(point, i) in plot.series[s].filter(Boolean)" :key="i" :x="point.x + s * plot.barWidth" :y="Math.min(point.y, plot.baseline)" :width="plot.barWidth" :height="Math.abs(point.y - plot.baseline)" /></template>
              <template v-else><polyline v-for="(segment, i) in plot.segments[s]" :key="i" :points="segment" fill="none" stroke-width="2" /></template>
            </g>
          </svg>
          <p v-for="(series, s) in chart.series" :key="s" :style="{ color: colors[s % colors.length] }">{{ series.name }}</p>
          <div class="scroll"><table><thead><tr><th>横軸</th><th v-for="(series, s) in chart.series" :key="s">{{ series.name }}</th></tr></thead><tbody><tr v-for="(x, i) in chart.x" :key="i"><td>{{ x }}</td><td v-for="(series, s) in chart.series" :key="s">{{ series.values[i] ?? 'NULL' }}</td></tr></tbody></table></div>
        </article>
        <h3 v-if="job.result.report">報告書</h3><pre v-if="job.result.report">{{ job.result.report }}</pre>
        <section v-if="canEdit" class="refine" aria-label="結果を改良する">
          <h3>結果を改良する</h3>
          <p>結果を見て、追加の指示を出せます（例: 「品番も付けて」「上位3件だけ」）。元の目的に追加の指示を足した、新しい分析案を作ります。手順・データ範囲・コードの承認は、もう一度行います。追加の指示は、実行履歴に保存されます。</p>
          <textarea v-model="refineText" rows="2" :disabled="!!busy" aria-label="追加の指示" placeholder="追加の指示を入力してください。"></textarea>
          <button :disabled="!canRefine" @click="refine">改良して新しい分析案を作る</button>
        </section>
      </template>
    </template>
    <h2>実行履歴</h2>
    <label v-if="canViewAll"><input v-model="includeAll" type="checkbox" :disabled="!!busy" @change="loadHistory(1)">全利用者の履歴（管理者表示）</label>
    <button :disabled="!!busy" @click="loadHistory(1)">履歴を取得</button>
    <p>履歴にはコード・結果・明細の本文はありません。保持期限後の結果は再表示できません。</p>
    <article v-for="run in history.results" :key="run.id">
      <h3>実行{{ run.id }} / {{ run.status_label }} / {{ run.executed_by }}</h3>
      <p>{{ run.started_at }} ～ {{ run.finished_at || '未確定' }} / {{ run.detail }}</p>
      <p>期間: {{ run.date_from }} ～ {{ run.date_to }} / 条件: {{ run.conditions }}</p>
      <p v-if="run.refinement_instruction">追加の指示: {{ run.refinement_instruction }}<template v-if="run.refined_from_run_id"> / 改良の元の実行: {{ run.refined_from_run_id }}</template></p>
      <p>取得行数（数量合計ではありません）: {{ run.fetched_rows }} / 承認時: {{ run.approved_counts }} / COUNT: {{ run.snapshot_counts }} / 送信: {{ run.sent_rows }} / 投入: {{ run.loaded_rows }}</p>
      <p>後始末: {{ run.cleanup }} / 投入完了: {{ run.loaded_at || '未記録' }}</p>
      <details><summary>利用ビュー・照合・コードのハッシュ・実行設定</summary><pre>{{ { views: run.views, unique_key_check: run.unique_key_check, sql_sha256: run.sql_sha256, python_sha256: run.python_sha256, executed_code_sha256: run.executed_code_sha256, wrapper_version: run.wrapper_version, settings: run.settings } }}</pre></details>
    </article>
    <p v-if="historyLoaded">{{ history.count }}件 / {{ page }}ページ</p>
    <button :disabled="!!busy || !history.previous" @click="loadHistory(page - 1)">前のページ</button>
    <button :disabled="!!busy || !history.next" @click="loadHistory(page + 1)">次のページ</button>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import api from '../../api/client'
import AnalysisErrorBanner from '../../components/AnalysisErrorBanner.vue'
import { useAnalysisErrorNotices } from '../../composables/analysisErrorNotices'
import { createAnalysisStatusMonitor } from '../../composables/analysisStatusMonitor'

const props = defineProps({ plan: { type: Object, default: null }, canEdit: Boolean, canViewAll: Boolean, blocked: Boolean, visible: { type: Boolean, default: true } })
const emit = defineEmits(['active', 'accepted', 'refine'])
const job = ref(null), busy = ref(''), error = ref(''), availability = ref(null)
const history = ref({ results: [], count: 0, next: null, previous: null }), historyError = ref(''), historyLoaded = ref(false)
const errorNotices = useAnalysisErrorNotices([['execution', error], ['history', historyError]])
const page = ref(1), includeAll = ref(false), fresh = ref(true), templateConfirmed = ref(false)
const uncertain = ref(false)
let disposed = false, epoch = 0
const monitor = createAnalysisStatusMonitor({
  request: async (id, signal) => (await api.aiAnalysis.getJob(id, { signal })).data,
  apply: data => { job.value = data; fresh.value = true; uncertain.value = false },
  manualError: () => { fresh.value = false; error.value = '実行状態・結果を取得できません。期限切れの場合は履歴を確認してください。' },
  canRead: () => !busy.value,
})
const completionText = computed(() => {
  const notification = monitor.notice.value
  if (!notification) return ''
  return ({ success: '結果が出ました（成功）。', failed: '実行に失敗しました。理由と後始末を確認してください。',
    cancelled: notification.cleanupComplete ? '中止されました。後始末の完了を確認しました。' : '中止状態になりましたが、後始末は未完了／未確認です。中止完了とは扱いません。',
    expired: '実行は期限切れになりました。履歴と後始末を確認してください。', unknown: '実行は状態不明です。停止・後始末完了とは断定できません。' })[notification.status] || ''
})
const terminal = ['success', 'failed', 'cancelled', 'expired']
const active = computed(() => uncertain.value || (!job.value && !!props.plan?.execution?.job_id) || (!!job.value && (!terminal.includes(job.value.status) || !cleanupComplete.value)))
// 結果の改良(BOSS承認 2026-10-06): 成功した結果の下で、追加の指示から、新しい分析案を作る(親が、元の目的・期間・AIの選択を引き継いで準備する)
const refineText = ref('')
const canRefine = computed(() => props.canEdit && !busy.value && !props.blocked && !active.value && job.value?.status === 'success' && !!job.value.result && !!refineText.value.trim())
function refine() {
  if (!canRefine.value) return
  if (!window.confirm('新しい分析案を作ると、この結果は画面から消えます（実行履歴には残ります）。手順・データ範囲・コードの承認は、もう一度行います。よろしいですか？')) return
  emit('refine', { instruction: refineText.value.trim(), run_id: job.value.run_id ?? null })
  refineText.value = ''
}
const cleanupComplete = computed(() => ['db_connection', 'container'].every(k => ['closed', 'not_started'].includes(job.value?.cleanup?.[k])))
const canExecute = computed(() => props.canEdit && !props.blocked && !busy.value && fresh.value && !active.value && availability.value?.ready && props.plan?.status === 'data_approved' && props.plan?.codegen?.status === 'code_approved' && props.plan.codegen.trial?.status === 'passed' && props.plan.codegen.trial.executed_code_sha256 === props.plan.codegen.executed_code_sha256 && (props.plan.template?.status !== 'pending_admin' || templateConfirmed.value))
const canCancel = computed(() => props.canEdit && !busy.value && fresh.value && !!job.value && !terminal.includes(job.value.status) && job.value.status !== 'cancel_requested')
const statusLabel = computed(() => ({ pending: '受付済み', running: '実行中', cancel_requested: '中止要求中', cancelled: '中止', expired: '期限切れ', failed: '失敗', success: '成功', unknown: '生存確認失敗・状態不明' })[job.value?.status] || '未確認')
// 失敗の説明は理由コードから固定文を引く。APIの理由本文・AI・DuckDBの文面は表示しない。
const FAILURE_LABELS = Object.freeze({
  result_invalid: '結果の形式が正しくありません。グラフの横軸(x)は値のリストで、各系列の値の個数をxと同じにしてください。',
  child_exit_nonzero: 'Pythonの実行に失敗しました。出力関数の引数の型・個数やコードを確認してください。',
  history_failed: '実行履歴の保存に失敗したため、結果を返しません。',
  launcher_unreachable: 'launcherとの通信に失敗しました。',
  execution_failed: '実行を開始・継続できませんでした。',
  cleanup_pending: '前回のコンテナを削除できていません。',
  stage_deadline_fetch: '取得の期限を超えました。',
  stage_deadline_transfer: '転送の期限を超えました。',
  stage_deadline_load: '投入の期限を超えました。',
  stage_deadline_python: 'Pythonの実行時間を超えました。',
  result_too_large: '結果の容量上限を超えました。',
  template_unavailable: 'テンプレートが再利用できない状態になったため、実行しませんでした。',
})
// 子のPythonの異常終了では、サーバーが足した「(例外: 種類名)」だけを追記する(データは含まない)
const childException = computed(() => job.value?.reason === 'child_exit_nonzero' && typeof job.value.detail === 'string' ? (job.value.detail.match(/\((例外: [A-Za-z0-9_()]+)\)\s*$/)?.[1] || '') : '')
const jobDetail = computed(() => job.value?.status === 'failed'
  ? (typeof job.value.reason === 'string' && Object.hasOwn(FAILURE_LABELS, job.value.reason) ? FAILURE_LABELS[job.value.reason] + (childException.value ? ` (${childException.value})` : '') : '失敗しました。詳細は理由コードを参照してください。')
  : job.value?.detail || '')
const formatDate = value => typeof value === 'string' ? value.replace('T', ' ').slice(0, 19) : ''
const colors = ['#168779', '#ad5d17', '#5366b1', '#923f73']
const plottedCharts = computed(() => (job.value?.result?.charts || []).map(chart => ({ chart, plot: geometry(chart) })))
function geometry(chart) {
  const numeric = v => typeof v === 'number' || (typeof v === 'string' && v.trim()) ? Number(v) : NaN
  const values = chart.series.flatMap(s => s.values)
  const numbers = values.map(numeric).filter(Number.isFinite)
  const nonNumeric = values.some(v => v !== null && !Number.isFinite(numeric(v)))
  const min = numbers.reduce((m, v) => Math.min(m, v), 0), max = numbers.reduce((m, v) => Math.max(m, v), 0) || 1, span = max - min || 1
  const y = v => 210 - (v - min) / span * 180, stride = 580 / Math.max(1, chart.x.length)
  const series = chart.series.map(s => s.values.map((v, i) => !Number.isFinite(numeric(v)) ? null : { x: 40 + i * stride, y: y(numeric(v)) }))
  const segments = series.map(points => { const groups = []; let current = []; for (const p of [...points, null]) { if (p) current.push(`${p.x},${p.y}`); else if (current.length) { groups.push(current.join(' ')); current = [] } } return groups })
  return { min, max, baseline: y(0), series, segments, nonNumeric, barWidth: stride * 0.8 / Math.max(1, chart.series.length) }
}
watch(active, value => emit('active', value), { immediate: true })
// 分析案・版・テンプレートが変われば、管理者未承認の確認を取り直す(別のテンプレートの確認を転用しない)
watch(() => [props.plan?.id, props.plan?.revision, props.plan?.template?.id], () => { templateConfirmed.value = false }, { flush: 'sync' })
watch(() => props.plan?.id, () => { epoch++; monitor.track(null); busy.value = ''; job.value = null; fresh.value = true; uncertain.value = false; error.value = '' }, { flush: 'sync' })
watch(() => [job.value?.id || props.plan?.execution?.job_id, job.value?.status], ([id, status]) => monitor.track(id, status ?? null), { immediate: true, flush: 'sync' })
watch(() => props.plan?.execution?.job_id, id => {
  if (id && id !== job.value?.id) { job.value = null; monitor.track(id) }
}, { flush: 'sync' })
watch(() => props.visible, visible => monitor.setVisible(visible !== false), { immediate: true, flush: 'sync' })
watch(() => props.canViewAll, allowed => { if (!allowed && includeAll.value) { includeAll.value = false; history.value = { results: [] }; loadHistory(1) } })
onBeforeUnmount(() => { disposed = true; epoch++; monitor.dispose() })
onMounted(() => { monitor.mount(typeof document === 'undefined' ? null : document); return checkAvailability() })
async function operation(name, call, apply, message) {
  if (busy.value) return
  const current = epoch
  busy.value = name; error.value = ''
  try { const response = await call(); if (!disposed && current === epoch) { apply(response.data); if (['execute', 'refresh', 'cancel'].includes(name)) fresh.value = true; if (['execute', 'refresh'].includes(name)) uncertain.value = false } }
  catch (e) {
    if (!disposed && current === epoch) {
      const staleWorker = name === 'execute' && e.response?.data?.reason === 'worker_stale'
      const rejected = name === 'execute' && (staleWorker || [400, 403, 404, 409, 410, 429].includes(e.response?.status))
      error.value = staleWorker ? '専用ワーカーを再起動してください。' : (rejected ? '実行は受け付けられませんでした。分析案・実行基盤の状態を確認してください。' : message)
      if (['execute', 'refresh', 'cancel'].includes(name)) fresh.value = rejected
      if (name === 'execute') {
        uncertain.value = !rejected
        if (rejected) { availability.value = null; emit('accepted') } // 状態の再取得だけ。実行を再送しない。
      }
    }
  }
  finally { if (!disposed && current === epoch) busy.value = '' }
}
function checkAvailability() { if (busy.value) return; availability.value = null; return operation('availability', () => api.aiAnalysis.executionOptions(), data => { availability.value = data }, '実行基盤を確認できません。実行していません。') }
function execute() {
  if (!canExecute.value) return
  const plan = props.plan
  const body = { revision: plan.revision, executed_code_sha256: plan.codegen.executed_code_sha256 }
  if (plan.template?.status === 'pending_admin') body.template_confirmed = plan.template.id // 確認したテンプレートのIDに結び付ける
  return operation('execute', () => api.aiAnalysis.execute(plan.id, body), data => { job.value = data; emit('accepted') }, '実行受付を確認できません。自動再送せず、分析案・実行状態を再取得してください。')
}
function refreshJob(id = job.value?.id || props.plan?.execution?.job_id) {
  // @clickのMouseEventをIDとして送らない。
  if (typeof id !== 'string') id = job.value?.id || props.plan?.execution?.job_id
  if (!id || busy.value) return
  error.value = ''; monitor.acknowledge()
  monitor.track(id, job.value?.status ?? null)
  return monitor.read(true)
}
function cancel() {
  if (!canCancel.value || !window.confirm('実行を中止しますか？ 途中結果は採用しません。後始末の確認まで中止完了とは扱いません。')) return
  monitor.invalidate() // 中止より前に開始したGETの古い応答で状態を戻さない。
  return operation('cancel', () => api.aiAnalysis.cancelJob(job.value.id), data => { job.value = data }, '中止の受付を確認できません。状態を再取得してください。')
}
async function loadHistory(target = 1) {
  if (busy.value) return
  const current = epoch
  const all = props.canViewAll && includeAll.value
  busy.value = 'history'; historyError.value = ''
  try {
    const response = await api.aiAnalysis.runs({ page: target, include_all: all ? 'true' : 'false' })
    if (!disposed && current === epoch && (!all || props.canViewAll)) { history.value = response.data; page.value = target; historyLoaded.value = true }
  } catch { if (!disposed && current === epoch) historyError.value = '実行履歴を取得できませんでした。' }
  finally { if (!disposed && current === epoch) busy.value = '' }
}
</script>

<style scoped>
.execution { border-top: 1px solid #ccc; margin-top: 20px; } .template-unapproved { font-weight: bold; color: #7a4b00; background: #fff4d6; padding: 6px; } button { margin: 4px; padding: 8px; } article { margin: 16px 0; padding: 10px; background: #f5f9f8; }
.empty-result { background: #fff8e6; border-left: 3px solid #d9a21b; color: #6f5314; padding: 6px 10px; }
.scroll { overflow: auto; } table { border-collapse: collapse; width: 100%; } th, td { border: 1px solid #ccd; padding: 5px; text-align: left; } pre { white-space: pre-wrap; overflow-wrap: anywhere; } svg { width: 100%; max-height: 300px; } [role=alert], .execution-failed { color: #a22; }
.completion-notice { border: 2px solid currentColor; padding: 10px; margin: 12px 0; }
.completion-success { color: #126d63; background: #edf6f5; }
.completion-failed { color: #a22; background: #fff0ee; }
.completion-attention { color: #6f5314; background: #fff8e6; }
.completion-pulse { animation: completion-emphasis 1.5s ease-in-out infinite; }
@keyframes completion-emphasis { 50% { box-shadow: 0 0 0 3px #168779; } }
@media (prefers-reduced-motion: reduce) { .completion-pulse { animation: none; } }
</style>
