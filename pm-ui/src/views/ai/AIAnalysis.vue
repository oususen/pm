<template>
  <main class="analysis-workspace">
    <header><h1>AI分析</h1><span>分析案・承認</span></header>
    <p class="notice">分析案・データ範囲の承認、コード生成・試行・承認、開発限定の実行・中止・結果・履歴表示に対応します。テンプレート保存は未対応です。{{ options?.notice || '' }}</p>
    <p v-if="!canEdit">閲覧のみの権限です。分析案の作成・承認、コード生成・SQL試行・コード承認・状態不明の解除には「AI分析」の編集権限が必要です。</p>
    <AnalysisErrorBanner :notices="errorNotices.notices.value" />
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
        <small>id: 重複・欠落の確認用に、分析用コンテナへ必ず送ります。社外AIには送りません。</small>
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
        <p v-if="plan.data_approved_at" role="status">データ承認日時: {{ formatDate(plan.data_approved_at) }}。{{ plan.execution ? '実行依頼済みです。実行状態・結果は下の実行欄で確認してください。' : '承認は完了しましたが、分析はまだ実行していません。' }}</p>
        <section v-if="plan.status === 'data_approved'" class="codegen">
          <h3>3. SQL・Pythonの生成と承認</h3>
          <p role="status">コード: {{ codeStatusLabel }} / AI生成回数: {{ codeState?.attempts ?? '未確認' }} / 上限: {{ codeState?.max_attempts ?? '未確認' }}</p>
          <p v-if="!codeStateFresh" class="warning">最新状態を確認できないため操作を止めています。「分析案の状態を再取得」を行ってください。</p>
          <p>失敗した生成も回数に含みます。再生成すると現在のコード・試行・コード承認は置き換わります。</p>
          <p v-if="codeInFlight" class="warning">{{ codeState?.inflight_state === 'unknown' ? '生成が中断した可能性があります（状態不明）。停止したとは断定できません。' : 'コードを生成中です。' }} 自動再送・有効期限の延長はしません。「分析案の状態を再取得」で最新状態を確認してください。</p>
          <button v-if="codeState?.inflight_state === 'unknown'" :disabled="!canReleaseCodegen" @click="releaseCodegen">状態不明の生成を解除（回数は戻りません）</button>
          <template v-if="!codeInFlight">
            <p v-if="codeExternal" class="warning">作成AIは {{ planProviderLabel }} です。コード生成は、分析案作成とは別の社外送信です。再生成のたびに全文を確認してください。未登録の名称・機密は自動判別できません。</p>
            <button v-if="codeExternal" :disabled="!canGenerate" @click="prepareCodePreview">コード生成で社外送信する全文を確認</button>
            <section v-if="codeExternal && codePreview" class="dataset">
              <h4>コード生成の社外送信前確認（まだ送信していません）</h4>
              <p>送信先: {{ codePreview.provider }} / モデル: {{ codePreview.model }} / 生成: {{ codePreview.attempt }}回目</p>
              <p>送らないもの: {{ codePreview.not_sent.join('、') }}</p>
              <div v-for="(message, index) in codePreview.messages" :key="index">
                <p>送信文 {{ index + 1 }}（{{ message.role }}）</p><pre>{{ message.content }}</pre>
              </div>
              <label><input v-model="codeSendAccepted" type="checkbox" :disabled="!canEdit || !!busy">置換後の全文を確認し、未登録の人名・社名・機密が残っていないことを確認しました</label>
            </section>
            <button v-if="!codeExternal || codePreview" :disabled="!canGenerate || (codeExternal && !codeSendAccepted)" @click="generateCode">{{ busy === 'code-generate' ? 'SQL・Pythonを生成中…' : codeExternal ? '確認した全文を社外AIへ送ってコードを生成' : 'ローカルQwenでコードを生成' }}</button>
            <p v-if="codeState && codeState.attempts >= codeState.max_attempts">AI生成回数の上限に達しました。試行のやり直しは生成回数に含みません。再生成が必要なら分析案を作り直してください。</p>
          </template>
          <p v-if="codeState?.status === 'failed'" class="error">コード生成に失敗したか、状態不明の生成を解除しました。採用できるコードはありません。再生成には新しい送信確認が必要です。</p>
          <ul v-if="codeState?.status === 'failed' && codeFailureLabels.length" class="error"><li v-for="label in codeFailureLabels" :key="label">{{ label }}</li></ul>
          <template v-if="hasCode">
            <h4>生成SQL（中間テーブル作成の手順）</h4>
            <p v-if="!codegen.steps.length">SQLの中間テーブル作成なし。</p>
            <div v-for="(step, index) in codegen.steps" :key="step.name"><p>手順 {{ index + 1 }} / 中間テーブル: {{ step.name }}</p><pre>{{ step.query }}</pre></div>
            <h4>生成Python</h4><pre>{{ codegen.python }}</pre>
            <small>コード全体のSHA-256: {{ codegen.executed_code_sha256 }} / 固定外枠の版: {{ codegen.wrapper_version }}</small>
            <p v-if="codeState?.wrapper_outdated">外枠が更新されています。保存済みSQL・Pythonが新しい検査に合格すれば、AIを呼ばずに更新・再試行・再承認できます。不合格なら再生成が必要です。</p>
            <button v-if="codeState?.wrapper_outdated" :disabled="!canRefreshWrapper" @click="refreshWrapper">保存済みコードの外枠を更新（AI生成回数は消費しません）</button>
            <p role="status">SQL試行: {{ trialStatusLabel }}{{ codegen.trial?.at ? ` / 確認日時: ${formatDate(codegen.trial.at)}` : '' }}</p>
            <p v-if="trialFailureLabel" class="error">{{ trialStepLabel ? `${trialStepLabel}: ` : '' }}{{ trialFailureLabel }}</p>
            <p>試行は実DBを使わず、空のテーブルでSQLの構文・参照・中間テーブルの規則だけを確認します。Pythonは静的検査のみです。実データでの成功や分析の正しさは保証しません。試行は実行履歴に残しません。</p>
            <button v-if="codeState?.status === 'generated'" :disabled="!canTrial" @click="trialCode">{{ busy === 'code-trial' ? 'SQLを試行中…' : 'SQLを試行（実データなし）' }}</button>
            <template v-if="codeState?.status === 'generated'">
              <label><input v-model="codeAccepted" type="checkbox" :disabled="!canEdit || !!busy || !trialPassed">表示したSQL・Pythonと分析目的を確認し、このコードを承認します（実行はまだ行いません）</label>
              <button :disabled="!canApproveCode || !codeAccepted" @click="approveCode">確認したSQL・Pythonを承認</button>
            </template>
            <p v-if="codeState?.status === 'code_approved'" role="status">コード承認日時: {{ formatDate(codegen.code_approved_at) }}。{{ plan.execution ? 'コード承認済みです。実行状態・結果は下の実行欄で確認してください。' : 'コード承認済み・分析未実行です。' }}</p>
          </template>
        </section>
      </template>
      <div class="actions">
        <button :disabled="!!busy" @click="refresh">分析案の状態を再取得</button>
        <button v-if="canEdit" :disabled="!!busy || executionActive" @click="resetPlan">目的・期間を変更して作り直す</button>
      </div>
    </section>
    <AIAnalysisExecution :plan="plan" :can-edit="canEdit" :can-view-all="canViewAll" :visible="visible" :blocked="!!busy || !codeStateFresh" @active="executionActive = $event" @accepted="refresh" />
    <small>タブ切替時は入力・承認状態を保持します。再読込・画面離脱・利用者切替で画面内の状態は消えます。未保存の分析案は設定された期限でRedisから消え、承認しても期限は延長しません。</small>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import api from '../../api/client'
import AIAnalysisExecution from './AIAnalysisExecution.vue'
import AnalysisErrorBanner from '../../components/AnalysisErrorBanner.vue'
import { useAnalysisErrorNotices } from '../../composables/analysisErrorNotices'

const props = defineProps({ request: { type: Object, default: null }, canEdit: { type: Boolean, default: false }, canViewAll: Boolean, visible: { type: Boolean, default: true } })
const executionActive = ref(false)
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
const errorNotices = useAnalysisErrorNotices([['analysis', error]], true)
const externalPreview = ref(null)
const externalAccepted = ref(false)
const codePreview = ref(null)
const codeSendAccepted = ref(false)
const codeAccepted = ref(false)
const codeStateFresh = ref(true)
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
const codegen = computed(() => plan.value?.codegen || null)
const codeState = computed(() => plan.value?.codegen_state || null)
const codeExternal = computed(() => plan.value?.proposal.provider !== 'qwen')
const codeInFlight = computed(() => !!codegen.value?.inflight || !!codeState.value?.inflight_state || codeState.value?.status === 'generating')
const canGenerate = computed(() => props.canEdit && !executionActive.value && !busy.value && codeStateFresh.value && plan.value?.status === 'data_approved' && codeState.value && !codeInFlight.value && codeState.value.attempts < codeState.value.max_attempts)
const hasCode = computed(() => ['generated', 'code_approved'].includes(codeState.value?.status) && Array.isArray(codegen.value?.steps) && typeof codegen.value?.python === 'string')
const trialPassed = computed(() => codegen.value?.trial?.status === 'passed' && !!codegen.value?.executed_code_sha256 && codegen.value.trial.executed_code_sha256 === codegen.value.executed_code_sha256)
const canTrial = computed(() => props.canEdit && !executionActive.value && !busy.value && codeStateFresh.value && plan.value?.status === 'data_approved' && hasCode.value && !codeInFlight.value && !codeState.value?.wrapper_outdated && codeState.value?.status === 'generated')
const canApproveCode = computed(() => canTrial.value && trialPassed.value)
const canRefreshWrapper = computed(() => props.canEdit && !executionActive.value && !busy.value && codeStateFresh.value && hasCode.value && !codeInFlight.value && !!codeState.value?.wrapper_outdated)
const canReleaseCodegen = computed(() => props.canEdit && !executionActive.value && !busy.value && codeStateFresh.value && codeState.value?.inflight_state === 'unknown')
const codeStatusLabel = computed(() => ({ none: '未生成', generating: '生成中', generated: '生成済み・承認待ち', code_approved: plan.value?.execution ? '承認済み・実行依頼あり' : '承認済み・未実行', failed: '生成失敗／解除済み' })[codeState.value?.status] || '状態未確認')
const trialStatusLabel = computed(() => ({ passed: '合格', failed: '不合格', unverified: '未検証（実行基盤の状態を確認して試行をやり直してください）' })[codegen.value?.trial?.status] || '未実施')
// 理由コードだけを固定文へ変換する。AI・DuckDBの説明文や未知の理由の本文は表示しない。
const FAILURE_LABELS = Object.freeze({
  ai_request_failed: 'AIとの通信に失敗しました。生成回数は消費されています。',
  response_invalid: 'AIの応答が指定された形式ではありません。',
  ai_unsupported: 'AIが、このデータ範囲では分析コードを作成できないと判定しました。',
  inflight_released: '状態不明の生成を利用者の操作で解除しました。生成回数は戻りません。',
  steps_invalid: 'SQL手順の形式が正しくありません。',
  step_name_invalid: '中間テーブル名が規則に合っていません。',
  query_empty: 'SQLの問い合わせが空です。',
  python_empty: 'Pythonのコードが空です。',
  too_many_steps: 'SQL手順の数が上限を超えています。',
  sql_too_large: 'SQLのサイズが上限を超えています。',
  python_too_large: 'Pythonのサイズが上限を超えています。',
  code_too_large: '固定外枠を含むコード全体のサイズが上限を超えています。',
  'python:syntax_error': 'Pythonの構文に誤りがあります。',
  'python:import_not_allowed': 'Pythonが許可されていないライブラリを使用しています。',
  'python:forbidden_name': 'Pythonが禁止された操作を使用しています。',
  'python:private_attribute': 'Pythonが禁止された属性へアクセスしています。',
  'python:con_method_not_allowed': 'Pythonが許可されていないDB接続の操作を使用しています。',
  'python:construct_not_allowed': 'Pythonが許可されていない構文を使用しています。',
  'python:no_output': 'Pythonに表・グラフ・報告書の出力処理がありません。',
  'python:chart_x_not_list': 'グラフの横軸(x)は値のリストにしてください。文字列や数値1つは使えません。',
  'python:table_columns_not_list': '表の列名(columns)は文字列のリストにしてください。',
  'python:table_rows_not_list': '表の行(rows)は行(リスト)のリストにしてください。',
  reference_not_allowed: 'SQLが承認されていないテーブル・参照先を使用しています。',
  table_function_not_allowed: 'SQLが許可されていないテーブル関数を使用しています。',
  function_not_allowed: 'SQLが禁止された関数を使用しています。',
  syntax_not_supported: 'SQLに対応していない構文が含まれています。',
  query_unparseable: 'SQLの構文を解析できませんでした。',
  query_not_single_select: 'SQLは単一の読み取り問い合わせにしてください。',
  query_not_select: 'SQLに読み取り以外の操作が含まれています。',
  query_too_deep: 'SQLの構文が複雑すぎるため検査を中止しました。',
  query_failed: 'SQLの実行に失敗しました。構文と承認した列・型を確認してください。',
  source_modified: '承認ビューの値の変更を検出したため、結果を採用しません。',
  trial_report_invalid: '試行結果の形式が正しくありません。',
  launcher_disabled: '開発用の実行基盤が有効になっていません。',
  launcher_unreachable: '実行基盤に接続できませんでした。',
  launcher_failed: '実行基盤で試行に失敗しました。',
  busy: '実行基盤が使用中です。しばらく待って試行をやり直してください。',
})
function failureLabel(reason) {
  return typeof reason === 'string' && Object.hasOwn(FAILURE_LABELS, reason)
    ? FAILURE_LABELS[reason] : '検査に合格しませんでした。分析目的・手順とコードを確認してください。'
}
const codeFailureLabels = computed(() => [...new Set((Array.isArray(codegen.value?.reasons) ? codegen.value.reasons : []).map(failureLabel))])
const trialFailureLabel = computed(() => {
  const trial = codegen.value?.trial
  if (!['failed', 'unverified'].includes(trial?.status)) return ''
  // 未検証はコード不合格と区別する。未知の理由本文は表示せず、実行基盤の確認を案内する。
  if (trial.status === 'unverified' && !(typeof trial.reason === 'string' && Object.hasOwn(FAILURE_LABELS, trial.reason))) {
    return '試行の検証が完了していません。実行基盤の状態を確認して試行をやり直してください。'
  }
  return failureLabel(trial.reason)
})
const trialStepLabel = computed(() => {
  const step = codegen.value?.trial?.step
  // 診断情報の任意文字列を表示せず、現在の検証済み手順と一致する名前だけを使う。
  const index = typeof step === 'string' && /^w_[a-z0-9_]+$/.test(step)
    ? (codegen.value?.steps || []).findIndex(item => item.name === step) : -1
  return index >= 0 ? `SQL手順${index + 1}（${step}）` : ''
})

function clearCodeConfirmations() {
  codePreview.value = null
  codeSendAccepted.value = false
  codeAccepted.value = false
}
// 版・コード・状態が変われば、送信確認もコード確認も取り直す。
watch(plan, clearCodeConfirmations, { flush: 'sync', deep: true })
watch(() => props.canEdit, value => { if (!value) clearCodeConfirmations() }, { flush: 'sync' })

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
const statusLabel = computed(() => ({ awaiting_method: '分析案の承認待ち', awaiting_data: 'データ範囲の承認待ち', data_approved: plan.value?.execution ? 'データ範囲承認済み・実行依頼あり' : 'データ範囲承認済み・未実行' })[plan.value?.status] || '')
const formatNumber = value => value == null ? '未確認' : Number(value).toLocaleString('ja-JP')
const formatDate = value => value?.replace('T', ' ').slice(0, 19) || ''

function resetPlan() {
  if (executionActive.value) return
  generation += 1
  plan.value = null
  error.value = ''
  busy.value = ''
  externalPreview.value = null
  externalAccepted.value = false
  clearCodeConfirmations()
  codeStateFresh.value = true
}
// 入力・AI選択を変えたら、以前の送信確認は使い回さない。
watch([purpose, dateFrom, dateTo, provider, model], () => {
  externalPreview.value = null
  externalAccepted.value = false
}, { flush: 'sync' })
watch(() => props.request, (request) => {
  if (!request || executionActive.value) return
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
    if (!disposed && current === generation) { plan.value = response.data; codeStateFresh.value = true }
  } catch (exception) {
    if (disposed || current !== generation) return
    if (action === 'refresh') codeStateFresh.value = false
    error.value = exception.response?.data?.detail || '分析案の操作に失敗しました。'
    if ([404, 410].includes(exception.response?.status)) plan.value = null
    clearCodeConfirmations()
    if ((exception.response?.status === 409 || action.startsWith('code-')) && plan.value) {
      codeStateFresh.value = false
      // 競合した操作を自動再実行せず、利用者が最新の内容を再確認する。
      try {
        const response = await api.aiAnalysis.getPlan(plan.value.id)
        if (!disposed && current === generation) { plan.value = response.data; codeStateFresh.value = true }
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
  return perform('refresh', () => api.aiAnalysis.getPlan(plan.value.id))
}
async function prepareCodePreview() {
  if (!canGenerate.value || !codeExternal.value) return
  clearCodeConfirmations()
  const current = ++generation
  const target = { id: plan.value.id, revision: plan.value.revision }
  busy.value = 'code-preview'
  error.value = ''
  try {
    const response = await api.aiAnalysis.codegenPreview(target.id, { revision: target.revision })
    if (!disposed && props.canEdit && current === generation && plan.value?.id === target.id && plan.value?.revision === target.revision) {
      codePreview.value = { ...response.data, planId: target.id, revision: target.revision }
    }
  } catch (exception) {
    if (!disposed && current === generation) {
      error.value = exception.response?.data?.detail || '送信内容を確認できませんでした。社外AIへは送信していません。'
      if ([404, 410].includes(exception.response?.status)) plan.value = null
      if (exception.response?.status === 409 && plan.value) {
        codeStateFresh.value = false
        // 確認要求は送信・生成をしない。競合時は状態だけ取得し、要求を再実行しない。
        try {
          const response = await api.aiAnalysis.getPlan(target.id)
          if (!disposed && current === generation) { plan.value = response.data; codeStateFresh.value = true }
        } catch (refreshError) {
          if (!disposed && current === generation && [404, 410].includes(refreshError.response?.status)) plan.value = null
        }
      }
    }
  } finally {
    if (!disposed && current === generation) busy.value = ''
  }
}
function generateCode() {
  if (!canGenerate.value) return
  const target = { id: plan.value.id, revision: plan.value.revision }
  const data = { revision: target.revision }
  if (codeExternal.value) {
    if (!codeSendAccepted.value || !codePreview.value?.confirmation || codePreview.value.planId !== target.id || codePreview.value.revision !== target.revision) return
    data.confirmation = codePreview.value.confirmation
  }
  // 通信失敗でも使い回さず、再生成には必ず新しい送信確認が必要。
  clearCodeConfirmations()
  return perform('code-generate', () => api.aiAnalysis.generateCode(target.id, data))
}
function refreshWrapper() {
  if (!canRefreshWrapper.value || !window.confirm('外枠を更新し、現在の試行とコード承認を破棄しますか？ AIは呼びません。再試行・再承認が必要です。')) return
  const target = { id: plan.value.id, revision: plan.value.revision }
  clearCodeConfirmations()
  return perform('code-refresh-wrapper', () => api.aiAnalysis.refreshWrapper(target.id, { revision: target.revision }))
}
function trialCode() {
  if (!canTrial.value) return
  const target = { id: plan.value.id, revision: plan.value.revision }
  clearCodeConfirmations()
  return perform('code-trial', () => api.aiAnalysis.trialCode(target.id, { revision: target.revision }))
}
function approveCode() {
  if (!canApproveCode.value || !codeAccepted.value) return
  const target = { id: plan.value.id, revision: plan.value.revision, hash: codegen.value.executed_code_sha256 }
  clearCodeConfirmations()
  return perform('code-approve', () => api.aiAnalysis.approveCode(target.id, { revision: target.revision, executed_code_sha256: target.hash }))
}
function releaseCodegen() {
  if (!canReleaseCodegen.value) return
  if (!window.confirm('状態不明の生成を解除しますか？ 停止したとは断定できません。回数は戻らず、有効期限は延長しません。解除後も自動で再送しません。')) return
  const target = { id: plan.value.id, revision: plan.value.revision }
  clearCodeConfirmations()
  return perform('code-release', () => api.aiAnalysis.releaseCodegen(target.id, { revision: target.revision }))
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
pre { white-space: pre-wrap; overflow-wrap: anywhere; padding: 8px; background: #f4f8f8; border: 1px solid #d1dddd; font-size: 13px; }
.codegen h4 { margin: 12px 0 6px; }
</style>
