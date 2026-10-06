<template>
  <main class="analysis-workspace">
    <header class="topbar">
      <div class="brand-mark">✦</div>
      <div class="brand-title"><strong>AI分析</strong><span>分析案・承認</span></div>
      <div class="local-badge" :class="{ offline: !selectedProvider?.available }"><i></i> {{ providerBadge }}</div>
      <label class="provider-select">AIプロバイダ
        <select v-model="provider" :disabled="!canEdit || !!busy || !!plan || !options" @change="onProviderChange">
          <option v-for="item in options?.providers || []" :key="item.provider" :value="item.provider" :disabled="!item.available">
            {{ item.label }}{{ item.available ? '' : '（利用不可）' }}
          </option>
        </select>
      </label>
      <label class="provider-select">モデル
        <select v-model="model" :disabled="!canEdit || !!busy || !!plan || !selectedProvider" @change="onModelChange">
          <option v-for="item in selectedProvider?.models || []" :key="item.id" :value="item.id">{{ item.label }}</option>
        </select>
      </label>
    </header>
    <p v-if="!canEdit">閲覧のみの権限です。分析案の作成・承認、コード生成・SQL試行・コード承認・状態不明の解除には「AI分析」の編集権限が必要です。</p>
    <AnalysisErrorBanner :notices="errorNotices.notices.value" />
    <p v-if="selectedProvider && !selectedProvider.available" class="error">{{ selectedProvider.label }}は利用できません: {{ selectedProvider.reason }}</p>
    <div class="analysis-layout">
      <section class="analysis-main" aria-label="実行・結果・履歴・テンプレート">
        <section class="notes" aria-label="ご利用上の注意">
          <button type="button" class="notes-head" :aria-expanded="notesOpen" aria-controls="notes-body" @click="notesOpen = !notesOpen">
            <strong>ご利用上の注意</strong><em>{{ notesOpen ? '畳む' : '開く' }}</em>
            <small v-if="!notesOpen && selectedProvider?.external">社外サービス（{{ selectedProvider.label }}）へ、分析目的・期間・公開ビューの説明を送ります</small>
          </button>
          <div v-show="notesOpen" id="notes-body" class="notes-body">
            <p class="notice">分析案・データ範囲の承認、コード生成・試行・承認、開発限定の実行・中止・結果・履歴表示に対応します。{{ options?.notice || '' }}</p>
            <p v-if="selectedProvider?.external" class="warning">社外サービス（{{ selectedProvider.label }}）へ、名称を登録コードに置換した分析目的・期間・公開ビューの説明を送ります。DBの明細行・件数は送りません。未登録の人名・社名は自動判別できません。送信前の目的文を確認し、名称や機密が残っていれば書き直してください。</p>
          </div>
        </section>
      <div id="analysis-execution" class="run-target" :class="{ ready: runReady }">
      <AIAnalysisExecution :plan="plan" :can-edit="canEdit" :can-view-all="canViewAll" :visible="visible" :blocked="!!busy || !codeStateFresh" @active="executionActive = $event" @accepted="refresh" @refine="startRefinement" />
      </div>
      <AIAnalysisTemplates :plan="plan" :can-edit="canEdit" :can-review="canViewAll" :blocked="!!busy || !codeStateFresh" :reuse-blocked="executionActive" @plan-created="useTemplatePlan" />
      <small>タブ切替時は入力・承認状態を保持します。再読込・画面離脱・利用者切替で画面内の状態は消えます。未保存の分析案は設定された期限でRedisから消え、承認しても期限は延長しません。</small>
      </section>
      <aside class="analysis-side" aria-label="分析の進め方">
        <h2 class="side-title">分析の進め方</h2>
      <section class="stage" :class="stageState(1)">
        <button type="button" class="stage-head" :aria-expanded="isOpen(1)" aria-controls="stage-body-1" @click="toggleStage(1)">
          <span class="stage-no">①</span><strong>分析目的</strong><em>{{ stageLabel(1) }}</em><small v-if="stageSummary(1)">{{ stageSummary(1) }}</small>
        </button>
        <div v-show="isOpen(1)" id="stage-body-1" class="stage-body">
      <textarea id="analysis-purpose" aria-label="分析目的" v-model="purpose" rows="3" :readonly="!canEdit || !!busy || !!plan" placeholder="何を調べ、どの判断に使いたいかを入力してください。"></textarea>
      <AIAnalysisConsult v-if="canEdit && !plan && !refinement" :plan="plan" :can-edit="canEdit" :blocked="!!busy" :purpose="purpose" :date-from="dateFrom" :date-to="dateTo" :provider="provider" :model="model" :external="!!selectedProvider?.external" :provider-label="selectedProvider?.label || ''" :provider-available="!!selectedProvider?.available" :user-name="userName" @apply="applyConsult" @plan-created="useTemplatePlan" />
      <p v-if="source" class="source">起点画面: {{ source }}（会話履歴・検索結果は引き継ぎません）</p>
      <p v-if="refinement && !plan" class="refine-note" role="status">結果の改良: 追加の指示「{{ refinement.instruction }}」を、上の目的に足して、新しい分析案を作ります（元の実行: {{ refinement.from_run_id ?? '不明' }}）。追加の指示は、実行履歴に保存されます。
        <button type="button" :disabled="!!busy" @click="refinement = null">追加の指示を外す</button></p>
      <div class="period">
        <label>開始日 <input v-model="dateFrom" type="date" :disabled="!canEdit || !!busy || !!plan"></label>
        <label>終了日 <input v-model="dateTo" type="date" :disabled="!canEdit || !!busy || !!plan"></label>
      </div>
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
        </div>
      </section>
        <div v-if="plan" class="plan-head">
        <div class="plan-heading"><h2>{{ plan.proposal.title }}</h2><span>{{ statusLabel }}</span></div>
        <small>分析案ID: {{ plan.id }} / 版: {{ plan.revision }} / 有効期限: {{ formatDate(plan.expires_at) }} / 作成AI: {{ planProviderLabel }}</small>
        <p v-if="plan.template" class="warning" role="status">テンプレート{{ plan.template.id }}（版{{ plan.template.version }}・{{ plan.template.name }}）から作成した分析案です。{{ plan.template.status === 'pending_admin' ? 'システム管理者未承認のテンプレートです。内容を確認してください。' : '正式なテンプレートです。' }}AIは使いません。保存済みのSQL・Pythonは、現行の外枠に組み直しています。</p>
        </div>
      <section v-if="plan" class="stage" :class="stageState(2)">
        <button type="button" class="stage-head" :aria-expanded="isOpen(2)" aria-controls="stage-body-2" @click="toggleStage(2)">
          <span class="stage-no">②</span><strong>目的・手順</strong><em>{{ stageLabel(2) }}</em><small v-if="stageSummary(2)">{{ stageSummary(2) }}</small>
        </button>
        <div v-show="isOpen(2)" id="stage-body-2" class="stage-body">
        <p>目的: {{ plan.proposal.purpose }}</p>
        <p v-if="plan.refinement">結果の改良: 追加の指示「{{ plan.refinement.instruction }}」（元の実行: {{ plan.refinement.from_run_id ?? '不明' }}）</p>
        <p v-if="plan.proposal.external_purpose">社外送信した目的文: {{ plan.proposal.external_purpose }}</p>
        <ol><li v-for="(step, index) in plan.proposal.steps" :key="index">{{ step }}</li></ol>
        <p>出力案: {{ plan.proposal.outputs.join('、') }}</p>
        <template v-if="plan.template && hasCode">
          <h4>保存済みのSQL・Python（承認前から確認できます。試行・コード承認は、承認後に行います）</h4>
          <div v-for="(step, index) in codegen.steps" :key="step.name"><p>手順 {{ index + 1 }} / 中間テーブル: {{ step.name }}</p><pre>{{ step.query }}</pre></div>
          <pre>{{ codegen.python }}</pre>
        </template>
        <p v-if="plan.method_approved_at">手順承認日時: {{ formatDate(plan.method_approved_at) }}</p>
        <button v-if="plan.status === 'awaiting_method'" :disabled="!canEdit || !!busy" @click="approve('method')">分析案・手順を承認</button>
        </div>
      </section>
      <section v-if="plan && plan.status !== 'awaiting_method'" class="stage" :class="stageState(3)">
        <button type="button" class="stage-head" :aria-expanded="isOpen(3)" aria-controls="stage-body-3" @click="toggleStage(3)">
          <span class="stage-no">③</span><strong>必要なデータ範囲</strong><em>{{ stageLabel(3) }}</em><small v-if="stageSummary(3)">{{ stageSummary(3) }}</small>
        </button>
        <div v-show="isOpen(3)" id="stage-body-3" class="stage-body">
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
          <p v-if="plan.data_approved_at" role="status">データ承認日時: {{ formatDate(plan.data_approved_at) }}。{{ plan.execution ? '実行依頼済みです。実行状態・結果は実行欄で確認してください。' : '承認は完了しましたが、分析はまだ実行していません。' }}</p>
        </div>
      </section>
      <section v-if="plan && plan.status === 'data_approved'" class="stage" :class="stageState(4)">
        <button type="button" class="stage-head" :aria-expanded="isOpen(4)" aria-controls="stage-body-4" @click="toggleStage(4)">
          <span class="stage-no">④</span><strong>SQL・Python</strong><em>{{ stageLabel(4) }}</em><small v-if="stageSummary(4)">{{ stageSummary(4) }}</small>
        </button>
        <div v-show="isOpen(4)" id="stage-body-4" class="stage-body">
            <p role="status">コード: {{ codeStatusLabel }} / AI生成回数: {{ codeState?.attempts ?? '未確認' }} / 上限: {{ codeState?.max_attempts ?? '未確認' }}</p>
            <p v-if="!codeStateFresh" class="warning">最新状態を確認できないため操作を止めています。「分析案の状態を再取得」を行ってください。</p>
            <p>失敗した生成も回数に含みます。再生成すると現在のコード・試行・コード承認は置き換わります。</p>
            <p v-if="codeInFlight" class="warning">{{ codeState?.inflight_state === 'unknown' ? '生成が中断した可能性があります（状態不明）。停止したとは断定できません。' : 'コードを生成中です。' }} 自動再送・有効期限の延長はしません。「分析案の状態を再取得」で最新状態を確認してください。</p>
            <button v-if="codeState?.inflight_state === 'unknown'" :disabled="!canReleaseCodegen" @click="releaseCodegen">状態不明の生成を解除（回数は戻りません）</button>
            <p v-if="plan.template">テンプレートから作成した分析案では、AIによるコード生成は行いません。現行の外枠でSQLを試行し、コードを承認してから実行します（コードを変えるときは、新しい分析として作成してください）。</p>
            <template v-if="!codeInFlight && !plan.template">
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
              <p v-if="codeVariables.length">変数（使うときに値を変えられます。コードには、下の値が入っています）: <span v-for="(item, index) in codeVariables" :key="item.name">{{ index ? ' / ' : '' }}{{ item.label }}（{{ item.name }}）= {{ item.default }}</span></p>
              <h4>生成Python</h4><pre>{{ codegen.python }}</pre>
              <small>コード全体のSHA-256: {{ codegen.executed_code_sha256 }} / 固定外枠の版: {{ codegen.wrapper_version }}</small>
              <p v-if="codeState?.wrapper_outdated">外枠が更新されています。保存済みSQL・Pythonが新しい検査に合格すれば、AIを呼ばずに更新・再試行・再承認できます。不合格なら再生成が必要です。</p>
              <button v-if="codeState?.wrapper_outdated" :disabled="!canRefreshWrapper" @click="refreshWrapper">保存済みコードの外枠を更新（AI生成回数は消費しません）</button>
              </template>
        </div>
      </section>
      <section v-if="plan && plan.status === 'data_approved' && hasCode" class="stage" :class="stageState(5)">
        <button type="button" class="stage-head" :aria-expanded="isOpen(5)" aria-controls="stage-body-5" @click="toggleStage(5)">
          <span class="stage-no">⑤</span><strong>試行・コード承認</strong><em>{{ stageLabel(5) }}</em><small v-if="stageSummary(5)">{{ stageSummary(5) }}</small>
        </button>
        <div v-show="isOpen(5)" id="stage-body-5" class="stage-body">
              <template v-if="hasCode">
              <p role="status">SQL試行: {{ trialStatusLabel }}{{ codegen.trial?.at ? ` / 確認日時: ${formatDate(codegen.trial.at)}` : '' }}</p>
              <p v-if="trialFailureLabel" class="error">{{ trialStepLabel ? `${trialStepLabel}: ` : '' }}{{ trialFailureLabel }}</p>
              <p>試行は実DBを使わず、空のテーブルでSQLの構文・参照・中間テーブルの規則だけを確認します。Pythonは静的検査のみです。実データでの成功や分析の正しさは保証しません。試行は実行履歴に残しません。</p>
              <button v-if="codeState?.status === 'generated'" :disabled="!canTrial" @click="trialCode">{{ busy === 'code-trial' ? 'SQLを試行中…' : 'SQLを試行（実データなし）' }}</button>
              <template v-if="codeState?.status === 'generated'">
                <label><input v-model="codeAccepted" type="checkbox" :disabled="!canEdit || !!busy || !trialPassed">表示したSQL・Pythonと分析目的を確認し、このコードを承認します（実行はまだ行いません）</label>
                <button :disabled="!canApproveCode || !codeAccepted" @click="approveCode">確認したSQL・Pythonを承認</button>
              </template>
              <p v-if="codeState?.status === 'code_approved'" role="status">コード承認日時: {{ formatDate(codegen.code_approved_at) }}。{{ plan.execution ? 'コード承認済みです。実行状態・結果は実行欄で確認してください。' : 'コード承認済み・分析未実行です。' }}</p>
              </template>
        </div>
      </section>
      <section v-if="plan" class="stage" :class="[stageState(6), { ready: runReady }]">
        <button type="button" class="stage-head" :aria-expanded="isOpen(6)" aria-controls="stage-body-6" @click="toggleStage(6)">
          <span class="stage-no">⑥</span><strong>実行</strong><em>{{ stageLabel(6) }}</em><small v-if="stageSummary(6)" :class="{ 'run-ready-text': runReady }">{{ runReady ? '◀ ' : '' }}{{ stageSummary(6) }}</small>
        </button>
        <div v-show="isOpen(6)" id="stage-body-6" class="stage-body">
          <p v-if="!codeApproved">コード承認の後に、左の「分析の実行・結果」で実行します。</p>
          <template v-else-if="!plan.execution">
            <p class="run-here" role="status">コード承認が済みました。<strong>左の「分析の実行・結果」で、「分析を実行」を押してください。</strong></p>
            <p>実行基盤が使える状態かは、左の「実行基盤の状態を確認」で確認できます。</p>
            <button type="button" @click="scrollToExecution">実行欄へ移動</button>
          </template>
          <p v-else role="status">実行を依頼済みです。{{ executionActive ? '実行中です。' : '' }}状態・結果は、左の「分析の実行・結果」に表示されます。</p>
        </div>
      </section>
        <div v-if="plan" class="actions">
          <button :disabled="!!busy" @click="refresh">分析案の状態を再取得</button>
          <button v-if="canEdit" :disabled="!!busy || executionActive" @click="resetPlan">目的・期間を変更して作り直す</button>
        </div>
      </aside>
    </div>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import api from '../../api/client'
import AIAnalysisConsult from './AIAnalysisConsult.vue'
import AIAnalysisExecution from './AIAnalysisExecution.vue'
import AIAnalysisTemplates from './AIAnalysisTemplates.vue'
import AnalysisErrorBanner from '../../components/AnalysisErrorBanner.vue'
import { useAnalysisErrorNotices } from '../../composables/analysisErrorNotices'

const props = defineProps({ request: { type: Object, default: null }, canEdit: { type: Boolean, default: false }, canViewAll: Boolean, visible: { type: Boolean, default: true }, userName: { type: String, default: '' } })
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
const OPENROUTER_PAID_MODELS = new Set(['google/gemma-4-26b-a4b-it', 'qwen/qwen3-30b-a3b-instruct-2507'])
const paidApproved = new Set()
const selectedProvider = computed(() => options.value?.providers.find(item => item.provider === provider.value) || null)
const canCreate = computed(() => props.canEdit && !busy.value && selectedProvider.value?.available && model.value && purpose.value.trim() && dateFrom.value && dateTo.value && dateFrom.value <= dateTo.value)
const planProviderLabel = computed(() => {
  const proposal = plan.value?.proposal
  if (proposal?.provider === 'template') return 'テンプレート（AI未使用）'
  const label = options.value?.providers.find(item => item.provider === proposal?.provider)?.label || proposal?.provider || ''
  return proposal?.model ? `${label} / ${proposal.model}` : label
})
// ヘッダのチップ: 選択中のAIとモデル(利用できない場合は「要確認」)
const providerBadge = computed(() => selectedProvider.value?.available ? `${selectedProvider.value.label} · ${model.value || '未選択'}` : `${selectedProvider.value?.label || 'AI'} · 要確認`)
const codegen = computed(() => plan.value?.codegen || null)
const codeState = computed(() => plan.value?.codegen_state || null)
// 変数つきのコード(段階2-B): AIが使った変数の一覧(名前・ラベル・元の値)。保存すると、テンプレートが持つ
const codeVariables = computed(() => Array.isArray(codegen.value?.template_source?.parameters) ? codegen.value.template_source.parameters : [])
const codeExternal = computed(() => !['qwen', 'template'].includes(plan.value?.proposal.provider))
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
  parameters_invalid: 'AIが返した変数の定義が正しくありません(種類・値・元の値の不足、または、登録されていない品番・顧客コード・納入先コード)。',
  parameters_source_invalid: 'コードと変数が合っていません(定義にない変数・使われない変数・固定の値の直書き・変数の前後の引用符)。',
  parameters_unavailable: '変数の値(品番・顧客コード・納入先コード)を確認できませんでした。しばらくしてから、もう一度試してください。',
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

// 段階の状態(pending=未、current=今、done=済)。⑥実行は、左のメインで扱う(R2で右へ移す)
// コード承認済み(実行できる状態の前提)。実行基盤の状態は、左の実行欄で確認する
// 実行できる状態(コード承認済みで、まだ実行を依頼していない)。右の⑥と左の実行欄を強調する
const runReady = computed(() => stageState(6) === 'current' && !plan.value?.execution)
const codeApproved = computed(() => plan.value?.status === 'data_approved' && codeState.value?.status === 'code_approved')
function stageState(n) {
  const p = plan.value
  if (n === 1) return p ? 'done' : 'current'
  if (!p) return 'pending'
  if (n === 2) return p.status === 'awaiting_method' ? 'current' : 'done'
  if (n === 3) return p.status === 'awaiting_method' ? 'pending' : (p.status === 'awaiting_data' ? 'current' : 'done')
  if (p.status !== 'data_approved') return 'pending'
  if (n === 4) return hasCode.value ? 'done' : 'current'
  if (n === 6) return codeApproved.value ? (!p.execution ? 'current' : (executionActive.value ? 'current' : 'done')) : 'pending'
  if (!hasCode.value) return 'pending'
  return codeState.value?.status === 'code_approved' ? 'done' : 'current'
}
const STAGE_LABELS = { pending: '未', current: '今', done: '済' }
const stageLabel = n => STAGE_LABELS[stageState(n)]
// 今の段階を開く。コードの確認のため、試行・コード承認の間は、SQL・Python(④)も開いておく。利用者が開閉した段階は、その操作を優先する
// 左のメインの「ご利用上の注意」(利用者が畳める。外部AIへの送信の注意は、畳んだときも見出しに要点を出す)
const notesOpen = ref(true)
const toggledStages = ref({})
// コードの警告(外枠が古い・最新状態を確認できない・生成中/状態不明・生成失敗)がある間は、④を畳まない(警告・更新ボタンを隠さない)
const codeAttention = computed(() => plan.value?.status === 'data_approved' && (!!codeState.value?.wrapper_outdated || !codeStateFresh.value || codeInFlight.value || codeState.value?.status === 'failed'))
// 外枠が古い間は、再試行・再承認のため、⑤も開く
const wrapperOutdated = computed(() => plan.value?.status === 'data_approved' && hasCode.value && !!codeState.value?.wrapper_outdated)
const isForcedOpen = n => (n === 4 && codeAttention.value) || (n === 5 && wrapperOutdated.value)
const isOpen = n => isForcedOpen(n) || (n in toggledStages.value ? toggledStages.value[n] : (stageState(n) === 'current' || (n === 4 && stageState(5) === 'current')))
function toggleStage(n) {
  if (isForcedOpen(n)) return // 警告で強制的に開いている間は、開閉を保存しない
  toggledStages.value = { ...toggledStages.value, [n]: !isOpen(n) }
}
// 折りたたんだときも分かる要約(承認日時など)
function stageSummary(n) {
  const p = plan.value
  if (!p) return ''
  if (n === 1) return p.proposal.title ? `分析案: ${p.proposal.title}` : ''
  if (n === 2) return p.method_approved_at ? `手順承認 ${formatDate(p.method_approved_at)}` : ''
  if (n === 3) return p.data_approved_at ? `データ承認 ${formatDate(p.data_approved_at)}` : ''
  if (n === 4) return hasCode.value ? (codeAttention.value ? 'コード生成済み・要確認' : 'コード生成済み') : (codeAttention.value ? 'コード・要確認' : '')
  if (n === 6) return !codeApproved.value ? '' : (!p.execution ? '左で実行してください' : (executionActive.value ? '実行中' : '実行依頼済み'))
  return codeState.value?.status === 'code_approved' ? `コード承認 ${formatDate(codegen.value?.code_approved_at)}` : ''
}
function scrollToExecution() {
  window.document?.getElementById?.('analysis-execution')?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
}
watch(() => plan.value?.id, () => { toggledStages.value = {} })

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

// AIの文案を、目的欄・期間欄へ取り込む(分析案は自動では作らない)
function applyConsult(draft) {
  if (draft.purpose) purpose.value = draft.purpose
  if (draft.date_from && draft.date_to) { dateFrom.value = draft.date_from; dateTo.value = draft.date_to }
}
// テンプレートから作成した分析案を、現在の分析案にする(AIは使わない。承認・件数確認・試行・コード承認は、この画面で取り直す)
function useTemplatePlan(created) {
  if (executionActive.value) return
  generation += 1
  error.value = ''
  busy.value = ''
  externalPreview.value = null
  externalAccepted.value = false
  clearCodeConfirmations()
  codeStateFresh.value = true
  plan.value = created
}
function resetPlan() {
  if (executionActive.value) return
  generation += 1
  plan.value = null
  refinement.value = null
  error.value = ''
  busy.value = ''
  externalPreview.value = null
  externalAccepted.value = false
  clearCodeConfirmations()
  codeStateFresh.value = true
}
// 入力・AI選択を変えたら、以前の送信確認は使い回さない。
// 結果の改良(BOSS承認 2026-10-06): 追加の指示と、改良の元の実行。分析案を作ると、分析案(plan.refinement)が持つ
const refinement = ref(null)
watch(plan, value => { if (value) refinement.value = null }, { flush: 'sync' })
function startRefinement({ instruction, run_id: runId } = {}) {
  const proposal = plan.value?.proposal
  if (!props.canEdit || executionActive.value || !proposal || typeof instruction !== 'string' || !instruction.trim()) return
  const base = { purpose: proposal.purpose, from: proposal.date_from, to: proposal.date_to }
  resetPlan() // 古い結果は画面から消える。AIの選択(プロバイダ・モデル)は、そのまま引き継ぐ
  purpose.value = base.purpose; dateFrom.value = base.from; dateTo.value = base.to
  refinement.value = { instruction: instruction.trim(), from_run_id: runId ?? null }
}
watch([purpose, dateFrom, dateTo, provider, model, refinement], () => {
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
  const input = { purpose: purpose.value.trim(), date_from: dateFrom.value, date_to: dateTo.value, provider: provider.value, model: model.value }
  if (refinement.value) input.refinement = { instruction: refinement.value.instruction, from_run_id: refinement.value.from_run_id }
  return input
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
.analysis-workspace { padding: 20px; max-width: 1600px; margin: auto; color: #334b50; }
.analysis-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(340px, 440px); gap: 18px; align-items: start; }
.analysis-main { min-width: 0; }
.notes { border: 1px solid #d1dddd; border-radius: 8px; margin-bottom: 12px; overflow: hidden; background: #fff; }
.notes-head { display: flex; align-items: center; flex-wrap: wrap; gap: 4px 8px; width: 100%; text-align: left; padding: 8px 10px; border: 0; border-radius: 0; }
.notes-head:not(:disabled) { background: #f4f8f8; color: #334b50; border-color: transparent; }
.notes-head em { font-style: normal; font-size: 11px; border-radius: 10px; padding: 1px 8px; background: #e6ecef; color: #647777; }
.notes-head small { display: inline; margin: 0; flex-basis: 100%; color: #6f5314; overflow-wrap: anywhere; }
.notes-body { padding: 4px 12px 10px; }
.notes-body p { margin: 6px 0; }
.analysis-side { min-width: 0; display: grid; gap: 8px; border-left: 1px solid #e6ecef; padding-left: 16px; }
.side-title { font-size: 13px; margin: 0; color: #81929b; letter-spacing: .5px; }
.stage { border: 1px solid #d1dddd; border-radius: 8px; overflow: hidden; background: #fff; }
.stage.current { border-color: #168779; box-shadow: 0 0 0 2px #16877922; }
.stage.pending { opacity: .75; }
.stage-head { display: flex; align-items: center; flex-wrap: wrap; gap: 4px 8px; width: 100%; text-align: left; padding: 8px 10px; border: 0; border-radius: 0; }
.stage-head:not(:disabled) { background: #f4f8f8; color: #334b50; border-color: transparent; }
.stage-head strong { font-size: 14px; }
.stage-head em { font-style: normal; font-size: 11px; border-radius: 10px; padding: 1px 8px; background: #e6ecef; color: #647777; }
.stage.current .stage-head em { background: #168779; color: #fff; }
.stage.done .stage-head em { background: #d8ebe6; color: #328476; }
.stage-head small { display: inline; margin: 0; flex-basis: 100%; color: #81929b; overflow-wrap: anywhere; }
.stage-no { color: #0e786d; font-weight: 700; }
.run-here { background: #fff8e6; border-left: 4px solid #d9a21b; padding: 10px 12px; font-size: 15px; }
.stage.ready { border-color: #d9a21b; box-shadow: 0 0 0 3px #d9a21b44; background: #fffdf5; }
.stage.ready .stage-head em { background: #d9a21b; color: #fff; }
.run-ready-text { color: #8a5a00; font-weight: 700; font-size: 13px; }
.run-target.ready { outline: 3px solid #d9a21b; outline-offset: 6px; border-radius: 6px; animation: run-ready-pulse 1.6s ease-in-out 3; }
@keyframes run-ready-pulse { 50% { outline-color: #d9a21b33; } }
@media (prefers-reduced-motion: reduce) { .run-target.ready { animation: none; } }
.stage-body { padding: 8px 12px 12px; overflow-wrap: anywhere; }
.plan-head { border: 1px solid #d1dddd; border-radius: 8px; padding: 8px 12px; }
@media (max-width: 960px) { .analysis-layout { grid-template-columns: minmax(0, 1fr); } .analysis-side { order: -1; border-left: 0; padding-left: 0; } }
.topbar { display: flex; align-items: center; flex-wrap: wrap; gap: 8px 11px; padding: 0 0 12px; margin-bottom: 12px; border-bottom: 1px solid #e6ecef; }
.brand-mark { width: 30px; height: 30px; border-radius: 9px; background: #0e786d; color: #fff; display: grid; place-items: center; font-size: 16px; }
.brand-title { display: grid; gap: 1px; }
.brand-title strong { font-size: 15px; }
.brand-title span { font-size: 11px; color: #81929b; }
.local-badge { margin-left: 8px; border: 1px solid #d8ebe6; border-radius: 15px; padding: 5px 10px; color: #328476; font-size: 11px; font-weight: 800; display: flex; align-items: center; gap: 6px; overflow-wrap: anywhere; }
.local-badge i { width: 6px; height: 6px; background: #34b984; border-radius: 50%; box-shadow: 0 0 0 3px #34b98420; }
.local-badge.offline { border-color: #f0e2c5; color: #a37b2f; }
.local-badge.offline i { background: #dfa746; box-shadow: 0 0 0 3px #dfa74620; }
.provider-select { display: flex; align-items: center; gap: 5px; margin: 0; font-size: 11px; font-weight: 400; color: #72848d; }
.provider-select select { border: 1px solid #d8e4e3; border-radius: 6px; background: #fff; color: #34515a; padding: 5px 7px; }
.notice { background: #edf6f5; border-left: 3px solid #168779; padding: 12px; line-height: 1.7; }
label { display: block; font-weight: 700; margin-bottom: 8px; }
textarea { box-sizing: border-box; width: 100%; border: 1px solid #b9cccc; border-radius: 8px; padding: 12px; font: inherit; resize: vertical; }
p { line-height: 1.7; }
button { padding: 10px 16px; border: 1px solid #d4dddd; border-radius: 6px; color: #647777; background: #eef2f2; }
small { display: block; margin-top: 12px; color: #657b80; }
.period, .actions, .plan-heading { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; margin: 10px 0; }
.period label { margin: 0; }
input { padding: 4px; font: inherit; }
.plan-head h2 { font-size: 16px; margin: 0; }
.dataset { background: #f4f8f8; padding: 1px 8px; overflow-wrap: anywhere; }
.external-purpose { white-space: pre-wrap; }
.error { background: #fff0ee; color: #9a362b; padding: 8px; }
.warning { background: #fff8e6; border-left: 3px solid #d9a21b; color: #6f5314; padding: 8px 10px; }
select { padding: 4px; font: inherit; max-width: 100%; }
button:not(:disabled) { border-color: #168779; color: white; background: #168779; cursor: pointer; }
small { overflow-wrap: anywhere; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; padding: 8px; background: #f4f8f8; border: 1px solid #d1dddd; font-size: 13px; }
.stage-body h4 { margin: 12px 0 6px; }
</style>
