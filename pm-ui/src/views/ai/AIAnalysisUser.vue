<template>
  <main class="analysis-workspace">
    <header class="topbar">
      <div class="brand-mark">✦</div>
      <div class="brand-title"><strong>AI分析</strong><span>相談から実行まで</span></div>
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
      <button type="button" class="boss-question" @click="askBoss('分析の相談')">システム管理者へ質問する</button>
    </header>
    <p v-if="!canEdit">閲覧のみの権限です。分析案の作成・承認、コード生成・SQL試行・コード承認・状態不明の解除には「AI分析」の編集権限が必要です。</p>
    <AnalysisErrorBanner :notices="errorNotices.notices.value" />
    <section v-if="error || codeState?.status === 'failed' || trialFailureLabel" class="boss-help" role="alert">
      <strong>うまくいかないときはシステム管理者へ相談できます。</strong>
      <p>現在の目的と失敗した段階を入力した状態で、問い合わせ画面を開きます。送信前に内容を編集できます。</p>
      <button type="button" @click="askBoss(codeState?.status === 'failed' ? '分析処理の作成' : trialFailureLabel ? '実行前の安全確認' : '分析案の作成', error || trialFailureLabel)">システム管理者へ質問する</button>
    </section>
    <p v-if="selectedProvider && !selectedProvider.available" class="error">{{ selectedProvider.label }}は利用できません: {{ selectedProvider.reason }}</p>
    <div ref="analysisLayout" class="analysis-layout" :class="{ resizing: isResizing }" :style="{ '--left-pane-percent': `${leftPanePercent}%` }">
      <section class="analysis-main" aria-label="成果物・実行結果・テンプレート">
        <section class="notes" aria-label="ご利用上の注意">
          <button type="button" class="notes-head" :aria-expanded="notesOpen" aria-controls="notes-body" @click="notesOpen = !notesOpen">
            <strong>ご利用上の注意</strong><em>{{ notesOpen ? '畳む' : '開く' }}</em>
            <small v-if="!notesOpen && selectedProvider?.external">社外サービス（{{ selectedProvider.label }}）へ、分析目的・期間・公開ビューの説明を送ります</small>
          </button>
          <div v-show="notesOpen" id="notes-body" class="notes-body">
            <p class="notice">分析案・データ範囲の承認、コード生成・試行・承認、開発限定の実行・中止・結果・履歴表示に対応します。{{ options?.notice || '' }}</p>
            <p v-if="selectedProvider?.external" class="warning">社外サービス（{{ selectedProvider.label }}）へ、名称を登録コードに置換した分析目的・期間・公開ビューの説明を送ります。DBの明細行・件数は送りません。未伏字の人名・社名は自動判別できません。送信前の目的文を確認し、名称や機密が残っていれば書き直してください。</p>
          </div>
        </section>
      <details v-if="plan" class="artifact-card" open>
        <summary>分析案（目的・手順・出力案）</summary>
        <section class="artifact-body">
          <h3>{{ plan.proposal.title }}</h3>
          <p><strong>目的:</strong> {{ plan.proposal.purpose }}</p>
          <p><strong>手順:</strong></p>
          <ol><li v-for="(step, index) in plan.proposal.steps" :key="index">{{ step }}</li></ol>
          <p><strong>出力案:</strong> {{ plan.proposal.outputs.join('、') }}</p>
          <p v-if="plan.proposal.conditions"><strong>条件:</strong> {{ plan.proposal.conditions }}</p>
          <p v-for="(warning, index) in (plan.warnings || [])" :key="'artifact-warning-' + index" class="warning plan-warning" role="alert"><span class="warn-mark" aria-hidden="true">⚠！</span> 確認してください: {{ warning }}</p>
        </section>
      </details>
      <details v-if="recommendedTemplates.length" class="artifact-card" open>
        <summary>テンプレート推薦（{{ recommendedTemplates.length }}件）</summary>
        <section class="artifact-body">
          <article v-for="item in recommendedTemplates" :key="item.id" class="recommendation">
            <strong>テンプレート{{ item.id }}（版{{ item.version }}） {{ item.name }}</strong>
            <p>カテゴリ: {{ item.category_label }} / 目的: {{ item.purpose }} / 期間: {{ item.date_from }} ～ {{ item.date_to }}</p>
            <button type="button" :disabled="!canEdit || !!busy || !!plan" @click="useRecommendedTemplate(item)">このテンプレートで分析案を作る</button>
            <button type="button" :disabled="!canEdit || !!busy || !!plan" @click="startReference({ ...item, status: 'approved' })">このテンプレートを参考に分析する</button>
          </article>
        </section>
      </details>
      <details class="artifact-card" open>
      <summary>分析結果・実行履歴</summary>
      <div id="analysis-execution" class="run-target" :class="{ ready: runReady }">
      <AIAnalysisUserExecution :plan="plan" :can-edit="canEdit" :can-view-all="false" :visible="visible" :blocked="!!busy || !codeStateFresh" @active="executionActive = $event" @accepted="refresh" @refine="startRefinement" />
      </div>
      </details>
      <section class="template-management" aria-label="テンプレート管理">
        <button type="button" class="templates-head" :aria-expanded="templatesOpen" aria-controls="templates-body" @click="templatesOpen = !templatesOpen">
          <strong>{{ templatesOpen ? '▼' : '▶' }} テンプレート管理</strong>
          <span v-if="!templatesOpen && canViewAll && pendingTemplateCount !== null">承認待ち {{ pendingTemplateCount }} 件</span>
          <span v-if="!templatesOpen && templateSavable">保存できます</span>
        </button>
        <div v-show="templatesOpen" id="templates-body" class="templates-body">
      <AIAnalysisUserTemplates :plan="plan" :can-edit="canEdit" :can-review="false" :blocked="!!busy || !codeStateFresh" :reuse-blocked="executionActive || !!refinement" :reference-blocked="executionActive" @plan-created="useTemplatePlan" @reference-selected="startReference" @pending-count="pendingTemplateCount = $event" />
        </div>
      </section>
      <small>タブ切替時は入力・承認状態を保持します。再読込・画面離脱・利用者切替で画面内の状態は消えます。未保存の分析案は設定された期限でRedisから消え、承認しても期限は延長しません。</small>
      </section>
      <div
        ref="analysisDivider"
        class="analysis-divider"
        role="separator"
        aria-label="相談欄と成果物欄の幅を変更"
        aria-orientation="vertical"
        aria-valuemin="35"
        aria-valuemax="75"
        :aria-valuenow="Math.round(leftPanePercent)"
        tabindex="0"
        @keydown="resizeWithKeyboard"
        @pointerdown="startResize"
        @pointermove="resizeWithPointer"
        @pointerup="stopResize"
        @pointercancel="stopResize"
        @lostpointercapture="stopResize"
      ><span aria-hidden="true"></span></div>
      <aside class="analysis-side" aria-label="AIとの相談と分析の進め方">
        <h2 class="side-title">AIと相談して分析を進める</h2>
      <section class="stage" :class="stageState(1)">
        <button type="button" class="stage-head" :aria-expanded="isOpen(1)" aria-controls="stage-body-1" @click="toggleStage(1)">
          <span class="stage-no">①</span><strong>分析目的</strong><span class="stage-resources">{{ stageResources(1) }}</span><em>{{ stageLabel(1) }}</em><small v-if="stageSummary(1)">{{ stageSummary(1) }}</small>
        </button>
        <div v-show="isOpen(1)" id="stage-body-1" class="stage-body">
      <textarea id="analysis-purpose" aria-label="分析目的" v-model="purpose" rows="5" :readonly="!canEdit || !!busy || !!plan" placeholder="何を調べ、どの判断に使いたいかを入力してください。"></textarea>
      <AIAnalysisUserConsult v-if="canEdit && !plan && !refinement" :plan="plan" :can-edit="canEdit" :blocked="!!busy" :purpose="purpose" :date-from="dateFrom" :date-to="dateTo" :provider="provider" :model="model" :external="!!selectedProvider?.external" :provider-label="selectedProvider?.label || ''" :provider-available="!!selectedProvider?.available" :user-name="userName" @apply="applyConsult" @plan-created="useTemplatePlan" @reference-selected="startReference" @recommendations="recommendedTemplates = $event" />
      <p v-if="source" class="source">起点画面: {{ source }}（会話履歴・検索結果は引き継ぎません）</p>
      <section v-if="referenceTemplate && !plan" id="reference-note" class="refine-note reference-note" role="status">
        <p>参考にするテンプレート: テンプレート{{ referenceTemplate.id }}「{{ referenceTemplate.name }}」（版{{ referenceTemplate.version }}）。このテンプレートの目的・手順・出力案・データ範囲を、AIが参考にして、今回の目的に合わせた新しい分析案とコードを作ります。承認は引き継がず、手順・データ範囲・コード・試行・コード承認を、取り直します。</p>
        <p class="warning plan-warning" role="alert"><span class="warn-mark" aria-hidden="true">⚠！</span> 参考のテンプレートの品番・顧客コード・日付などは、参考の値です。今回の値は、目的の欄に、はっきり書いてください（書かれていない値は、AIが、参考の値を使う恐れがあります）。</p>
        <p class="next-action"><strong>次の操作:</strong> 上の欄に、今回の目的を入力し、期間を選んで、「社外送信する目的文を確認」を押してください（社外のAIを選んでいる場合。参考のテンプレートの内容も、置換後の全文を、確認できます）。</p>
        <p v-if="referenceTemplate.status === 'pending_admin'" class="warning plan-warning" role="alert"><span class="warn-mark" aria-hidden="true">⚠！</span> 管理者承認前のテンプレートを参考にしています（まだ、システム管理者に確認されていません。作成者と管理者だけが使えます）。</p>
        <p v-if="selectedProvider && !selectedProvider.external" class="warning plan-warning" role="alert"><span class="warn-mark" aria-hidden="true">⚠！</span> ローカルQwenでは、テンプレートを参考にできません。社外のAIを選ぶか、参考を外してください。</p>
        <button type="button" :disabled="!!busy" @click="referenceTemplate = null">参考を外す</button></section>
      <p v-if="refinement && !plan" class="refine-note" role="status">結果の改良: 追加の指示「{{ refinement.instruction }}」を、上の目的に足して、新しい分析案を作ります（元の実行: {{ refinement.from_run_id ?? '不明' }}）。追加の指示は、実行履歴に保存されます。改良の準備中は、テンプレートから分析案を作れません(追加の指示を外すと、作れます)。
        <button type="button" :disabled="!!busy" @click="refinement = null">追加の指示を外す</button></p>
      <div class="period">
        <label>開始日 <input v-model="dateFrom" type="date" :disabled="!canEdit || !!busy || !!plan || noPeriod"></label>
        <label>終了日 <input v-model="dateTo" type="date" :disabled="!canEdit || !!busy || !!plan || noPeriod"></label>
        <button type="button" :disabled="!canEdit || !!busy || !!plan" :aria-pressed="noPeriod" @click="toggleNoPeriod">{{ noPeriod ? '期間なし（解除する）' : '期間なし' }}</button>
        <small v-if="noPeriod">期間なし: 日付のないビュー（マスタなど）専用です。期間は今日（{{ dateFrom }}）の1日に固定されます。日付のあるビューは今日の分だけになります。</small>
      </div>
      <template v-if="!plan">
        <button v-if="selectedProvider?.external && !externalPreview" type="button" :disabled="!canCreate" @click="prepareExternalPreview">{{ busy === 'external-preview' ? '目的文を確認中…' : '社外送信する目的文を確認' }}</button>
        <section v-if="selectedProvider?.external && externalPreview" class="dataset">
          <h2>社外サービス利用の確認</h2>
          <p>送信先: {{ selectedProvider.label }} / モデル: {{ externalPreview.model }}</p>
          <p>分析目的・期間・公開ビューの説明を、名称を登録コードへ置換して送ります。DBの明細行・件数は送りません。一般使用者向け画面では送信文そのものは表示しません。</p>
          <label><input v-model="externalAccepted" type="checkbox" :disabled="!!busy || !canEdit">目的欄に、社外へ送ってはいけない人名・社名・機密情報が残っていないことを確認しました</label>
        </section>
        <p v-if="busy === 'create'" class="generating" role="status" aria-live="polite">⏳ AIが分析案を作成しています。返事を待っています（{{ selectedProvider?.external ? '通常 10〜60秒、最大 90秒' : 'AI設定のタイムアウトまで' }}）。経過 {{ elapsedSeconds }}秒。この画面を閉じずに、お待ちください。</p>
        <button v-if="!selectedProvider?.external || externalPreview" type="button" :disabled="!canCreate || (selectedProvider?.external && !externalAccepted)" @click="createPlan">{{ busy === 'create' ? '分析案を作成中…' : selectedProvider?.external ? '確認した内容を社外AIへ送って分析案を作成' : '分析案を作成' }}</button>
      </template>
        </div>
      </section>
        <div v-if="plan" class="plan-head">
        <div class="plan-heading"><h2>{{ plan.proposal.title }}</h2><span>{{ statusLabel }}</span></div>
        <small>分析案ID: {{ plan.id }} / 版: {{ plan.revision }} / 有効期限: {{ formatDate(plan.expires_at) }} / 作成AI: {{ planProviderLabel }}</small>
        <p v-if="plan.template?.values && Object.keys(plan.template.values).length" role="status">今回使う変数の値: <span v-for="(value, name, index) in plan.template.values" :key="name">{{ index ? ' / ' : '' }}{{ name }} = {{ value }}</span>（下の目的・手順の説明は、テンプレート保存時のものです。日付・コードは、自動では書き換えていません）</p>
        <p v-if="plan.template" class="warning" role="status">テンプレート{{ plan.template.id }}（版{{ plan.template.version }}・{{ plan.template.name }}）から作成した分析案です。{{ plan.template.status === 'pending_admin' ? 'システム管理者未承認のテンプレートです。内容を確認してください。' : '正式なテンプレートです。' }}AIは使わず、保存済みの分析処理を現在の実行環境に合わせます。</p>
        </div>
      <section v-if="plan" class="stage" :class="stageState(2)">
        <button type="button" class="stage-head" :aria-expanded="isOpen(2)" aria-controls="stage-body-2" @click="toggleStage(2)">
          <span class="stage-no">②</span><strong>目的・手順</strong><span class="stage-resources">{{ stageResources(2) }}</span><em>{{ stageLabel(2) }}</em><small v-if="stageSummary(2)">{{ stageSummary(2) }}</small>
        </button>
        <div v-show="isOpen(2)" id="stage-body-2" class="stage-body">
        <p>右側の「分析案（目的・手順・出力案）」を確認してください。</p>
        <p v-if="plan.template_reference" role="status">参考にしたテンプレート: テンプレート{{ plan.template_reference.id }}「{{ plan.template_reference.name }}」（版{{ plan.template_reference.version }}）。目的・手順・データ範囲は、今回の分析案として、取り直しています。</p>
        <p v-if="plan.template_reference?.status === 'pending_admin'" class="warning plan-warning" role="alert"><span class="warn-mark" aria-hidden="true">⚠！</span> 管理者承認前のテンプレートを参考にしています（まだ、システム管理者に確認されていません）。</p>
        <p v-if="plan.refinement">結果の改良: 追加の指示「{{ plan.refinement.instruction }}」（元の実行: {{ plan.refinement.from_run_id ?? '不明' }}）</p>
        <p v-if="plan.template && hasCode">保存済みの分析処理があります。一般使用者向け画面ではSQL・Pythonの内容を表示しません。</p>
        <p v-if="plan.method_approved_at">手順承認日時: {{ formatDate(plan.method_approved_at) }}</p>
        <button v-if="plan.status === 'awaiting_method'" :disabled="!canEdit || !!busy" @click="approve('method')">分析案・手順を承認</button>
        </div>
      </section>
      <section v-if="plan && plan.status !== 'awaiting_method'" class="stage" :class="stageState(3)">
        <button type="button" class="stage-head" :aria-expanded="isOpen(3)" aria-controls="stage-body-3" @click="toggleStage(3)">
          <span class="stage-no">③</span><strong>必要なデータ範囲</strong><span class="stage-resources">{{ stageResources(3) }}</span><em>{{ stageLabel(3) }}</em><small v-if="stageSummary(3)">{{ stageSummary(3) }}</small>
        </button>
        <div v-show="isOpen(3)" id="stage-body-3" class="stage-body">
          <p>期間: {{ plan.proposal.date_from }} ～ {{ plan.proposal.date_to }} / 条件: {{ plan.proposal.conditions }}</p>
          <div v-for="dataset in plan.proposal.datasets" :key="dataset.view" class="dataset">
            <p>ビュー: {{ dataset.view }} / 必要フィールド: {{ dataset.fields.join('、') }}</p>
            <p v-if="plan.preview">対象行数: {{ formatNumber(plan.preview.datasets.find(item => item.view === dataset.view)?.rows) }}行</p>
            <p v-if="plan.preview && plan.preview.datasets.find(item => item.view === dataset.view)?.period_applied === false">期間: 適用しない（全行）</p>
            <p v-if="noPeriod && plan.preview && plan.preview.datasets.find(item => item.view === dataset.view)?.period_applied === true" class="warning plan-warning" role="alert"><span class="warn-mark" aria-hidden="true">⚠！</span> 「期間なし」を選びましたが、このビューは日付があり、今日（{{ plan.proposal.date_from }}）の1日だけに絞られます。全期間ではありません。「目的・期間を変更して作り直す」で期間を指定してください。</p>
          </div>
          <small>id: 重複・欠落の確認用に、分析用コンテナへ必ず送ります。社外AIには送りません。</small>
          <p>追加資料: なし（資料の取込みは未実装）</p>
          <template v-if="plan.preview">
            <p>対象行数の合計: {{ formatNumber(plan.preview.total_rows) }}行 / 取得行数の上限: {{ formatNumber(plan.preview.max_fetch_rows) }}行</p>
            <small>件数確認日時: {{ formatDate(plan.preview.counted_at) }}。数量の合計ではありません。実行時には最新スナップショットで再確認が必要です。</small>
            <p v-if="plan.preview.over_limit" class="error">対象が上限を超えました。一部だけを採用せず、条件（日付のあるビューは期間も）を絞って分析案を作り直してください。</p>
          </template>
          <div v-if="plan.status === 'awaiting_data'" class="actions">
            <button v-if="!plan.preview" :disabled="!canEdit || !!busy" @click="preview">{{ busy === 'preview' ? '件数を確認中…' : '対象件数を確認' }}</button>
            <button :disabled="!canEdit || !!busy || !plan.preview || plan.preview.over_limit" @click="approve('data')">データ範囲を承認</button>
          </div>
          <p v-if="plan.data_approved_at" role="status">データ承認日時: {{ formatDate(plan.data_approved_at) }}。{{ plan.execution ? '実行依頼済みです。実行状態・結果は実行欄で確認してください。' : '承認は完了しましたが、分析はまだ実行していません。' }}</p>
        </div>
      </section>
      <section v-if="plan && plan.status === 'data_approved'" class="stage" :class="stageState(4)">
        <button type="button" class="stage-head" :aria-expanded="isOpen(4)" aria-controls="stage-body-4" @click="toggleStage(4)">
          <span class="stage-no">④</span><strong>分析処理の準備</strong><span class="stage-resources">{{ stageResources(4) }}</span><em>{{ stageLabel(4) }}</em><small v-if="stageSummary(4)">{{ stageSummary(4) }}</small>
        </button>
        <div v-show="isOpen(4)" id="stage-body-4" class="stage-body">
            <p v-if="busy === 'code-generate'" class="generating" role="status" aria-live="polite">⏳ AIが分析処理を作成しています。返事を待っています（{{ selectedProvider?.external ? '通常 10〜60秒、最大 90秒' : 'AI設定のタイムアウトまで' }}）。経過 {{ elapsedSeconds }}秒。この画面を閉じずに、お待ちください。生成回数は、すでに数えています。</p>
            <p v-if="codegen?.literal_values?.length" class="warning plan-warning" role="alert"><span class="warn-mark" aria-hidden="true">⚠！</span> 目的・手順に書かれた値が、変数にされず、コードに直接書かれています: {{ codegen.literal_values.join('、') }}。この分析だけなら、そのまま実行できます。テンプレートとして保存しても、再利用で、これらの値を変えられません。変えたいときは、再生成してください。</p>
            <p v-if="normalizedValues.length" class="warning plan-warning" role="alert"><span class="warn-mark" aria-hidden="true">⚠！</span> <template v-for="(item, index) in normalizedValues" :key="item.name"><template v-if="index">　</template>変数 {{ item.name }}: {{ item.from }} を、マスタの表記 {{ item.to }} に直しました。</template></p>
            <p role="status">コード: {{ codeStatusLabel }} / AI生成回数: {{ codeState?.attempts ?? '未確認' }} / 上限: {{ codeState?.max_attempts ?? '未確認' }}</p>
            <p v-if="!codeStateFresh" class="warning">最新状態を確認できないため操作を止めています。「最新状態を確認する」を押してください。</p>
            <p>失敗した生成も回数に含みます。再生成すると現在のコード・試行・コード承認は置き換わります。</p>
            <p v-if="codeInFlight" class="warning">{{ codeState?.inflight_state === 'unknown' ? '生成が中断した可能性があります（状態不明）。停止したとは断定できません。' : 'コードを生成中です。' }} 自動再送・有効期限の延長はしません。「最新状態を確認する」で最新状態を確認してください。</p>
            <button v-if="codeState?.inflight_state === 'unknown'" :disabled="!canReleaseCodegen" @click="releaseCodegen">状態不明の生成を解除（回数は戻りません）</button>
            <p v-if="plan.template">テンプレートから作成した分析案では、AIによるコード生成は行いません。現行の外枠でSQLを試行し、コードを承認してから実行します（コードを変えるときは、新しい分析として作成してください）。</p>
            <template v-if="!codeInFlight && !plan.template">
              <button v-if="hasCode && !codeRebuildOpen" :disabled="!canGenerate" @click="codeRebuildOpen = true">分析処理を作り直す</button>
              <template v-if="!hasCode || codeRebuildOpen">
                <p v-if="codeExternal" class="warning">作成AIは {{ planProviderLabel }} です。コード生成は、分析案作成とは別の社外送信です。再生成のたびに全文を確認してください。未伏字の名称・機密は自動判別できません。</p>
                <button v-if="hasCode" :disabled="!!busy" @click="cancelCodeRebuild">作り直しをやめる</button>
                <button v-if="codeExternal" :disabled="!canGenerate" @click="prepareCodePreview">{{ codePreview ? '最新の内容でもう一度確認する' : '社外サービスに送る内容を確認する' }}</button>
                <button v-if="codeExternal && codePreview" :disabled="!!busy" @click="closeCodePreview">確認を閉じる（まだ送信していません）</button>
                <section v-if="codeExternal && codePreview" class="dataset">
                  <h4>分析処理作成の社外送信前確認（まだ送信していません）</h4>
                  <p>送信先: {{ codePreview.provider }} / モデル: {{ codePreview.model }} / 生成: {{ codePreview.attempt }}回目</p>
                  <p>送らないもの: {{ codePreview.not_sent.join('、') }}</p>
                  <p>分析案・公開ビューの説明を送ります。一般使用者向け画面では送信文そのものは表示しません。</p>
                  <label><input v-model="codeSendAccepted" type="checkbox" :disabled="!canEdit || !!busy">分析目的に、社外へ送ってはいけない人名・社名・機密情報が残っていないことを確認しました</label>
                  <small class="next-hint">チェックすると、下のボタンで分析処理を作成できます。</small>
                </section>
                <button v-if="!codeExternal || codePreview" class="next-action-btn" :class="{ ready: canGenerate && (!codeExternal || codeSendAccepted) }" :disabled="!canGenerate || (codeExternal && !codeSendAccepted)" @click="generateCode"><template v-if="busy === 'code-generate'">分析処理を作成中…</template><template v-else-if="codeExternal">{{ codeSendAccepted ? '▶ ' : '' }}確認した内容を社外AIへ送って分析処理を作成</template><template v-else>ローカルQwenで分析処理を作成</template></button>
              </template>
              <p v-if="codeState && codeState.attempts >= codeState.max_attempts">AI生成回数の上限に達しました。試行のやり直しは生成回数に含みません。再生成が必要なら分析案を作り直してください。</p>
            </template>
            <p v-if="codeState?.status === 'failed'" class="error">コード生成に失敗したか、状態不明の生成を解除しました。採用できるコードはありません。再生成には新しい送信確認が必要です。</p>
            <ul v-if="codeState?.status === 'failed' && codeFailureLabels.length" class="error"><li v-for="label in codeFailureLabels" :key="label">{{ label }}</li></ul>
            <template v-if="hasCode">
              <h4>分析処理を作成しました</h4>
              <p>一般使用者向け画面では、生成されたSQL・Pythonの内容を表示しません。次の「実行前の承認」で、分析案の目的・手順・出力案をもう一度確認してください。</p>
              <p v-if="codeVariables.length">変数（使うときに値を変えられます。コードには、下の値が入っています）: <span v-for="(item, index) in codeVariables" :key="item.name">{{ index ? ' / ' : '' }}{{ item.label }}（{{ item.name }}）= {{ item.default }}</span></p>
              <p v-if="codeState?.wrapper_outdated" class="wrapper-notice" role="alert">⚠ 保存済みコードの外枠が古くなっています。下のボタンで更新してください。AIは呼ばず、生成回数も消費しません。更新後、試行とコード承認をやり直します。保存済みSQL・Pythonが新しい検査に合格しない場合は、再生成が必要です。</p>
              <button v-if="codeState?.wrapper_outdated" :disabled="!canRefreshWrapper" @click="refreshWrapper">保存済みコードの外枠を更新（AI生成回数は消費しません）</button>
              </template>
        </div>
      </section>
      <section v-if="plan && plan.status === 'data_approved' && hasCode" class="stage" :class="stageState(5)">
        <button type="button" class="stage-head" :aria-expanded="isOpen(5)" aria-controls="stage-body-5" @click="toggleStage(5)">
          <span class="stage-no">⑤</span><strong>実行前の承認</strong><span class="stage-resources">{{ stageResources(5) }}</span><em>{{ stageLabel(5) }}</em><small v-if="stageSummary(5)">{{ stageSummary(5) }}</small>
        </button>
        <div v-show="isOpen(5)" id="stage-body-5" class="stage-body">
              <template v-if="hasCode">
              <section class="approval-summary" aria-label="承認する分析案">
                <h4>{{ plan.proposal.title }}</h4>
                <p><strong>目的:</strong> {{ plan.proposal.purpose }}</p>
                <p><strong>手順:</strong></p>
                <ol><li v-for="(step, index) in plan.proposal.steps" :key="index">{{ step }}</li></ol>
                <p><strong>出力案:</strong> {{ plan.proposal.outputs.join('、') }}</p>
              </section>
              <p role="status">SQL試行: {{ trialStatusLabel }}{{ codegen.trial?.at ? ` / 確認日時: ${formatDate(codegen.trial.at)}` : '' }}</p>
              <p v-if="trialFailureLabel" class="error">{{ trialStepLabel ? `${trialStepLabel}: ` : '' }}{{ trialFailureLabel }}</p>
              <p>実行前の安全確認は実データを使わずに行います。実データでの成功や分析の正しさは保証しません。</p>
              <button v-if="codeState?.status === 'generated'" :disabled="!canTrial" @click="trialCode">{{ busy === 'code-trial' ? '安全確認中…' : '実行前の安全確認を行う' }}</button>
              <template v-if="codeState?.status === 'generated'">
                <label><input v-model="codeAccepted" type="checkbox" :disabled="!canEdit || !!busy || !trialPassed">上の目的・手順・出力案を確認し、この分析処理の実行を承認します（実行はまだ行いません）</label>
                <small v-if="trialPassed" class="next-hint">チェックすると、下のボタンで分析処理を承認できます。</small>
                <button class="next-action-btn" :class="{ ready: canApproveCode && codeAccepted }" :disabled="!canApproveCode || !codeAccepted" @click="approveCode">{{ canApproveCode && codeAccepted ? '▶ ' : '' }}分析処理を承認</button>
              </template>
              <p v-if="codeState?.status === 'code_approved'" role="status">コード承認日時: {{ formatDate(codegen.code_approved_at) }}。{{ plan.execution ? 'コード承認済みです。実行状態・結果は実行欄で確認してください。' : 'コード承認済み・分析未実行です。' }}</p>
              </template>
        </div>
      </section>
      <section v-if="plan" class="stage" :class="[stageState(6), { ready: runReady }]">
        <button type="button" class="stage-head" :aria-expanded="isOpen(6)" aria-controls="stage-body-6" @click="toggleStage(6)">
          <span class="stage-no">⑥</span><strong>実行</strong><span class="stage-resources">{{ stageResources(6) }}</span><em>{{ stageLabel(6) }}</em><small v-if="stageSummary(6)" :class="{ 'run-ready-text': runReady }">{{ runReady ? '◀ ' : '' }}{{ stageSummary(6) }}</small>
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
          <button v-if="!codeStateFresh || codeInFlight" :disabled="!!busy" @click="refresh">最新状態を確認する</button>
          <button v-if="canEdit" :disabled="!!busy || executionActive" @click="restartPlan">目的・期間を変更して作り直す</button>
        </div>
      </aside>
    </div>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import api from '../../api/client'
import AIAnalysisUserConsult from './AIAnalysisUserConsult.vue'
import AIAnalysisUserExecution from './AIAnalysisUserExecution.vue'
import AIAnalysisUserTemplates from './AIAnalysisUserTemplates.vue'
import AnalysisErrorBanner from '../../components/AnalysisErrorBanner.vue'
import { useAnalysisErrorNotices } from '../../composables/analysisErrorNotices'
import { openRequestDialog } from '../../composables/requestDialog'

const props = defineProps({ request: { type: Object, default: null }, canEdit: { type: Boolean, default: false }, canViewAll: Boolean, visible: { type: Boolean, default: true }, userName: { type: String, default: '' } })
const executionActive = ref(false)
const analysisLayout = ref(null)
const analysisDivider = ref(null)
const leftPanePercent = ref(66.7)
const isResizing = ref(false)
const LEFT_PANE_MIN = 35
const LEFT_PANE_MAX = 75
const KEYBOARD_RESIZE_STEP = 2
let resizePointerId = null
let previousBodyUserSelect = ''
let previousBodyCursor = ''

function clampLeftPanePercent(value) {
  return Math.min(LEFT_PANE_MAX, Math.max(LEFT_PANE_MIN, value))
}
function updateLeftPaneFromPointer(event) {
  const bounds = analysisLayout.value?.getBoundingClientRect()
  if (!bounds?.width) return
  leftPanePercent.value = clampLeftPanePercent(((event.clientX - bounds.left) / bounds.width) * 100)
}
function startResize(event) {
  if (isResizing.value || event.button !== 0 || typeof window === 'undefined' || window.matchMedia('(max-width: 960px)').matches) return
  resizePointerId = event.pointerId
  isResizing.value = true
  analysisDivider.value?.setPointerCapture?.(event.pointerId)
  if (document.body) {
    previousBodyUserSelect = document.body.style.userSelect
    previousBodyCursor = document.body.style.cursor
    document.body.style.userSelect = 'none'
    document.body.style.cursor = 'col-resize'
  }
  updateLeftPaneFromPointer(event)
  event.preventDefault()
}
function resizeWithPointer(event) {
  if (!isResizing.value || event.pointerId !== resizePointerId) return
  updateLeftPaneFromPointer(event)
}
function stopResize(event) {
  if (!isResizing.value && resizePointerId === null) return
  if (resizePointerId !== null && event?.pointerId !== undefined && event.pointerId !== resizePointerId) return
  const pointerId = resizePointerId
  resizePointerId = null
  isResizing.value = false
  if (pointerId !== null && analysisDivider.value?.hasPointerCapture?.(pointerId)) analysisDivider.value.releasePointerCapture(pointerId)
  if (typeof document !== 'undefined' && document.body) {
    document.body.style.userSelect = previousBodyUserSelect
    document.body.style.cursor = previousBodyCursor
  }
}
function resizeWithKeyboard(event) {
  if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return
  leftPanePercent.value = clampLeftPanePercent(leftPanePercent.value + (event.key === 'ArrowRight' ? KEYBOARD_RESIZE_STEP : -KEYBOARD_RESIZE_STEP))
  event.preventDefault()
}
const purpose = ref('')
const source = ref('')
const dateFrom = ref('')
const dateTo = ref('')
// 期間なし(日付のないビュー用、BOSS承認 2026-10-10 案1): 期間は今日(日替わり8時)の1日に固定し、日付ありのビューが選ばれたら分析案で警告する
const noPeriod = ref(false)
function businessDateString() {
  const now = new Date()
  if (now.getHours() < 8) now.setDate(now.getDate() - 1)  // 日替わりは8:00
  const pad = value => String(value).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`  // toISOString()はUTCへずれるため使わない
}
function toggleNoPeriod() {
  noPeriod.value = !noPeriod.value
  if (noPeriod.value) { dateFrom.value = businessDateString(); dateTo.value = dateFrom.value } else { dateFrom.value = ''; dateTo.value = '' }
}
const options = ref(null)
const provider = ref('')
const model = ref('')
const plan = ref(null)
const recommendedTemplates = ref([])
const busy = ref('')
const error = ref('')
const errorNotices = useAnalysisErrorNotices([['analysis', error]], true)
const externalPreview = ref(null)
const externalAccepted = ref(false)
const codePreview = ref(null)
const codeSendAccepted = ref(false)
const codeAccepted = ref(false)
const codeRebuildOpen = ref(false)
const codeStateFresh = ref(true)
let generation = 0
let disposed = false
let lastSelection = { provider: '', model: '' }

function askBoss(stage, detail = '') {
  const currentPurpose = typeof plan.value?.proposal?.purpose === 'string' ? plan.value.proposal.purpose : purpose.value
  openRequestDialog({
    requestType: 'question',
    subject: `AI分析について質問（${stage}）`,
    body: `AI分析について質問があります。\n\n【段階】\n${stage}\n\n【エラー・状況】\n${detail || '詳細をここに追記してください。'}\n\n【現在の目的】\n${currentPurpose}`,
  })
}
// 有料モデルは、検索AIと同じく選択時に確認し、同じ画面の間は1回の承認で再確認しない。
const OPENROUTER_PAID_MODELS = new Set(['google/gemma-4-26b-a4b-it', 'qwen/qwen3-30b-a3b-instruct-2507', 'qwen/qwen3-14b', 'qwen/qwen3-coder-30b-a3b-instruct', 'deepseek/deepseek-v4.1-flash'])
const OPENROUTER_PAID_LABELS = Object.freeze({ 'google/gemma-4-26b-a4b-it': 'Gemma 4 26B A4B', 'qwen/qwen3-30b-a3b-instruct-2507': 'Qwen3 30B A3B Instruct 2507', 'qwen/qwen3-14b': 'Qwen3 14B', 'qwen/qwen3-coder-30b-a3b-instruct': 'Qwen3 Coder 30B A3B Instruct', 'deepseek/deepseek-v4.1-flash': 'DeepSeek V4.1 Flash' })
const paidApproved = new Set()
const selectedProvider = computed(() => options.value?.providers.find(item => item.provider === provider.value) || null)
const canCreate = computed(() => props.canEdit && !busy.value && selectedProvider.value?.available && model.value && purpose.value.trim() && dateFrom.value && dateTo.value && dateFrom.value <= dateTo.value
  && !(referenceTemplate.value && !selectedProvider.value?.external))  // ローカルQwenでは、参考を使えない(サーバーも409。参考なしで続けない)
const planProviderLabel = computed(() => {
  const proposal = plan.value?.proposal
  if (proposal?.provider === 'template') return 'テンプレート（AI未使用）'
  const label = options.value?.providers.find(item => item.provider === proposal?.provider)?.label || proposal?.provider || ''
  return proposal?.model ? `${label} / ${proposal.model}` : label
})
// ヘッダのチップ: 選択中のAIとモデル(利用できない場合は「要確認」)
const providerBadge = computed(() => selectedProvider.value?.available ? `${selectedProvider.value.label} · ${model.value || '未選択'}` : `${selectedProvider.value?.label || 'AI'} · 要確認`)
const codegen = computed(() => plan.value?.codegen || null)
// マスタの表記へ直した変数。サーバーが固定の形(name・from・to)だけを返す。形が合わないものは表示しない
const CODE_TEXT = /^[A-Za-z0-9_-]{1,40}$/
const normalizedValues = computed(() => (Array.isArray(codegen.value?.normalized_values) ? codegen.value.normalized_values : [])
  .filter(item => item && /^[a-z][a-z0-9_]*$/.test(item.name) && typeof item.from === 'string' && CODE_TEXT.test(item.from) && typeof item.to === 'string' && CODE_TEXT.test(item.to)))
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
  ai_timeout: 'AIから制限時間内に返事がありませんでした(最大90秒)。時間をおいて、再生成してください。生成回数は消費されています。',
  ai_auth: 'AIのAPIキーが未設定、または正しくありません。管理者へ、AI設定の確認を依頼してください。生成回数は消費されています。',
  ai_http: 'AIのAPIがエラーを返しました(残高・利用制限など)。管理者へ、AIの契約・残高の確認を依頼してください。生成回数は消費されています。',
  ai_connect: 'AIのAPIに接続できませんでした。ネットワークを確認し、時間をおいて、再生成してください。生成回数は消費されています。',
  ai_empty: 'AIから空の返事が返りました。時間をおいて、再生成してください。生成回数は消費されています。',
  sql_validation_failed: '生成SQLが承認列・中間テーブルの検査に合格しませんでした。必要列が承認範囲にあるか、分析案とコードを確認してください。生成回数は消費されています。',
  sql_validation_busy: 'SQL検査の実行基盤が使用中です。終了後に再生成してください。生成回数は消費されています。',
  sql_validation_unavailable: 'SQL検査の実行基盤を利用できません。管理者へ確認を依頼してください。生成回数は消費されています。',
  sql_validation_report_invalid: 'SQL検査の応答を確認できませんでした。管理者へ実行基盤の確認を依頼してください。生成回数は消費されています。',
  response_invalid: 'AIの応答が指定された形式ではありません。',
  ai_unsupported: 'AIが、このデータ範囲では分析コードを作成できないと判定しました。',
  parameters_invalid: 'AIが返した変数の定義が正しくありません(種類・値・元の値の不足、日付の組(名前_from・名前_to)の不備、比べる期間が全体の期間の外・開始日が終了日より後、または、登録されていない品番・顧客コード・納入先コード)。',
  parameters_undeclared: '変数を宣言していません(コードに {{名前}} があるのに、変数の一覧にない、または、一覧なしで {{…}} が書かれています)。',
  parameters_unused: '宣言した変数が、コードで使われていません。',
  parameters_quoted: '変数の前後に引用符が付いています({{名前}} だけを書くと、値が引用符つきで入ります)。',
  parameters_literal: '固定の値(日付・品番などの元の値)が、コードに直接書かれています。変数を使う必要があります。',
  parameters_def_format: '変数の定義の形式が正しくありません。',
  parameters_def_name: '変数の名前が正しくありません(英小文字・数字・アンダースコア。日付は「名前_from」「名前_to」の形)。',
  parameters_def_type: '変数の種類が正しくありません。',
  parameters_def_label: '変数のラベルがありません。',
  parameters_def_default: '変数の元の値(default)がありません。',
  parameters_def_pair: '日付の変数が、「名前_from」と「名前_to」の組になっていません。',
  parameters_def_date: '日付の形が正しくありません(YYYY-MM-DD)。',
  parameters_def_value: '品番・顧客コード・納入先コードの値の形が正しくありません(英数字・アンダースコア・ハイフン)。',
  parameters_def_unregistered: '登録されていない品番・顧客コード・納入先コードです。',
  parameters_def_ambiguous: '大文字小文字だけが違う値が複数あり、どれが正しい表記か決められません。',
  parameters_def_order: '比べる期間の開始日が、終了日より後です。',
  parameters_def_outside: '比べる期間が、全体の期間の外です。',
  python_syntax_after_substitution: '変数を値に置き換えたあとで、構文が壊れました(Pythonの文字列の中に変数を書くと、引用符がぶつかります)。',
  python_syntax_in_source: '変数を置き換える前から、構文に誤りがあります。',
  python_syntax_string: '構文の種類: 文字列が閉じていません。',
  python_syntax_bracket: '構文の種類: 括弧が閉じていない、または余分です。',
  python_syntax_indent: '構文の種類: 字下げ(インデント)が正しくありません。',
  python_syntax_character: '構文の種類: 使えない文字があります。',
  python_syntax_other: '構文の種類: 文法の誤りです。',
  parameters_literal_sql: '場所: SQL(中間テーブルの問い合わせ)',
  parameters_literal_python: '場所: Python(グラフ・表のタイトルや文字列を含む)',
  parameters_literal_date: '種類: 日付(YYYY-MM-DD)',
  parameters_literal_value: '種類: 変数の元の値(品番・顧客コード・納入先コード)',
  parameters_source_invalid: 'コードと変数が合っていません(中間テーブル名の変数・読めない {{…}} の表記)。',
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
// 変数名は、サーバーが固定の形(英小文字・数字・アンダースコア)の識別子だけを返す。それ以外の値は表示しない
const variableNames = reason => {
  const names = codegen.value?.reason_names?.[reason]
  return Array.isArray(names) ? names.filter(name => typeof name === 'string' && /^[a-z][a-z0-9_]*$/.test(name)) : []
}
const NAMED_REASONS = Object.freeze({
  parameters_undeclared: '宣言されていない変数', parameters_unused: '使われていない変数',
  parameters_def_format: '該当する変数', parameters_def_name: '該当する変数', parameters_def_type: '該当する変数', parameters_def_label: '該当する変数',
  parameters_def_default: '該当する変数', parameters_def_pair: '該当する変数', parameters_def_date: '該当する変数', parameters_def_value: '該当する変数',
  parameters_def_unregistered: '該当する変数', parameters_def_ambiguous: '該当する変数', parameters_def_order: '該当する変数', parameters_def_outside: '該当する変数',
})
const codeFailureLabels = computed(() => [...new Set((Array.isArray(codegen.value?.reasons) ? codegen.value.reasons : []).map(reason => {
  const names = Object.hasOwn(NAMED_REASONS, reason) ? variableNames(reason) : []
  return names.length ? `${failureLabel(reason)}（${NAMED_REASONS[reason]}: ${names.join('、')}）` : failureLabel(reason)
}))])
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
// 作成済みの案では、その案のAIを表示する。テンプレート再利用ではAIを呼ばない。
function stageResources(n) {
  if (n === 1 || n === 4) {
    const source = plan.value ? plan.value.proposal.provider : provider.value
    if (plan.value?.template || source === 'template') return '社内サーバー'
    const ai = source === 'qwen' ? 'ローカルLLM' : '社外AI'
    return n === 4 ? `${ai}＋社内サーバー` : ai
  }
  return { 2: '社内サーバー', 3: '社内サーバー＋社内DB', 5: '社内の安全確認', 6: '社内の分析実行環境' }[n]
}
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
const notesOpen = ref(false)
const templatesOpen = ref(false), pendingTemplateCount = ref(null)
// 保存欄と同じ条件。偽から真へ変わった瞬間だけ開き、手動で閉じた状態は保持する。
const templateSavable = computed(() => plan.value?.status === 'data_approved' && plan.value?.codegen?.status === 'code_approved' && !!plan.value.codegen.executed_code_sha256 && !plan.value?.template)
watch(templateSavable, (value, previous) => { if (value && !previous) templatesOpen.value = true }, { flush: 'sync' })
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
  if (n === 4 && busy.value === 'code-generate') return `生成中… ${elapsedSeconds.value}秒`
  if (n === 4) return hasCode.value ? (codeAttention.value ? '分析処理作成済み・要確認' : '分析処理作成済み') : (codeAttention.value ? '分析処理・要確認' : '')
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
function closeCodePreview() {
  if (busy.value) return
  codePreview.value = null
  codeSendAccepted.value = false
}
function cancelCodeRebuild() {
  if (busy.value) return
  codeRebuildOpen.value = false
  codePreview.value = null
  codeSendAccepted.value = false
}
// 版・コード・状態が変われば、送信確認もコード確認も取り直す。
watch(plan, () => { clearCodeConfirmations(); codeRebuildOpen.value = false }, { flush: 'sync', deep: true })
watch(() => props.canEdit, value => { if (!value) { clearCodeConfirmations(); codeRebuildOpen.value = false } }, { flush: 'sync' })

function defaultModelFor(key) {
  const current = options.value?.providers.find(item => item.provider === key)
  return current?.models.some(item => item.id === current.default_model) ? current.default_model : (current?.models[0]?.id || '')
}
function paidKey() {
  if (provider.value === 'deepseek') return { key: 'deepseek', message: 'DeepSeekは有料です。使いますか？' }
  if (provider.value === 'anthropic') return { key: 'anthropic', message: 'Claude（Anthropic）は有料です。クレジットを消費します。使いますか？' }
  if (provider.value === 'openrouter' && OPENROUTER_PAID_MODELS.has(model.value)) {
    return { key: model.value, message: `このモデル（${OPENROUTER_PAID_LABELS[model.value] || model.value}）は有料です。使いますか？` }
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
  if (draft.date_from && draft.date_to) { noPeriod.value = false; dateFrom.value = draft.date_from; dateTo.value = draft.date_to }
}
// テンプレートから作成した分析案を、現在の分析案にする(AIは使わない。承認・件数確認・試行・コード承認は、この画面で取り直す)
function useTemplatePlan(created) {
  // 結果の改良の準備中は、受け付けない(新しい分析案を作ると、追加の指示と元の実行の対応が、消えてしまうため)
  if (executionActive.value || refinement.value) return
  generation += 1
  error.value = ''
  busy.value = ''
  externalPreview.value = null
  externalAccepted.value = false
  clearCodeConfirmations()
  codeStateFresh.value = true
  plan.value = created
  recommendedTemplates.value = []
  if (typeof created?.proposal?.purpose === 'string') purpose.value = created.proposal.purpose
}

async function useRecommendedTemplate(item) {
  if (!props.canEdit || busy.value || plan.value || !Number.isInteger(item?.id)) return
  const current = generation
  busy.value = 'template-reuse'
  error.value = ''
  try {
    const response = await api.aiAnalysis.createTemplatePlan(item.id)
    if (!disposed && current === generation && !plan.value) useTemplatePlan(response.data)
  } catch (exception) {
    if (!disposed && current === generation) error.value = exception.response?.status === 403
      ? 'このテンプレートを利用する権限がありません。'
      : 'テンプレートから分析案を作成できませんでした。'
  } finally {
    if (!disposed && current === generation && busy.value === 'template-reuse') busy.value = ''
  }
}
// 「目的・期間を変更して作り直す」: 参考にしたテンプレートがある分析案は、同じテンプレートを参考にしたまま、作り直す(参考を外したいときは、「参考を外す」)
function restartPlan() {
  const reference = plan.value?.template_reference
  resetPlan()
  if (reference && !plan.value) referenceTemplate.value = { id: reference.id, version: reference.version, name: reference.name, status: reference.status }
}
function resetPlan() {
  if (executionActive.value) return
  generation += 1
  plan.value = null
  refinement.value = null
  referenceTemplate.value = null
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
// テンプレートを参考にした生成(2026-10-09、BOSS承認 段階C): 参考にするテンプレートの識別だけを持つ。分析案を作ると、分析案(plan.template_reference)が持つ。改良との併用は可
const referenceTemplate = ref(null)
watch(plan, value => { if (value) { refinement.value = null; referenceTemplate.value = null } }, { flush: 'sync' })
function startReference(template) {
  if (!props.canEdit || executionActive.value || !template || !Number.isInteger(template.id)) return
  if (plan.value && !window.confirm('現在の分析案を破棄して、このテンプレートを参考に、新しい分析を始めます。よろしいですか？')) return
  const keepRefinement = !plan.value ? refinement.value : null  // 分析案がなければ、準備中の追加の指示は残す(併用)
  if (plan.value) resetPlan()
  refinement.value = keepRefinement
  referenceTemplate.value = { id: template.id, version: template.version, name: template.name, status: template.status }
  // 参考を選んだことが分かるよう、参考の表示へ移動する(画面の上部にあるため)
  if (typeof document !== 'undefined') setTimeout(() => document.getElementById('reference-note')?.scrollIntoView?.({ block: 'nearest' }), 0)  // 画面の描画の後に移動する(ブラウザだけ)
}
function startRefinement({ instruction, run_id: runId } = {}) {
  const proposal = plan.value?.proposal
  if (!props.canEdit || executionActive.value || !proposal || typeof instruction !== 'string' || !instruction.trim()) return
  const base = { purpose: proposal.purpose, from: proposal.date_from, to: proposal.date_to }
  resetPlan() // 古い結果は画面から消える。AIの選択(プロバイダ・モデル)は、そのまま引き継ぐ
  noPeriod.value = false
  purpose.value = base.purpose; dateFrom.value = base.from; dateTo.value = base.to
  refinement.value = { instruction: instruction.trim(), from_run_id: runId ?? null }
}
watch([purpose, dateFrom, dateTo, provider, model, refinement, referenceTemplate], () => {
  externalPreview.value = null
  externalAccepted.value = false
}, { flush: 'sync' })
watch(() => props.request, (request) => {
  if (!request || executionActive.value) return
  // 結果の改良の準備中(追加の指示がある)に、検索から新しい分析が来たとき: 破棄の確認を取る。断れば、そのまま(追加の指示も、目的も残る)
  if (refinement.value && !window.confirm('結果の改良の準備中です。新しい分析を始めると、追加の指示は破棄されます。よろしいですか？')) return
  resetPlan()
  // 検索結果や会話履歴は受け取らず、質問文と起点だけを画面内で引き継ぐ。
  purpose.value = request.question || ''
  source.value = request.screenContext || ''
}, { immediate: true })
// 経過時間(秒)。AIの返事を待つ間(分析案の作成・コード生成)だけ、1秒ごとに数える。止まっていないことが分かるようにする(BOSS承認 2026-10-08)
const elapsedSeconds = ref(0)
let elapsedTimer = null
function stopElapsedTimer() {
  if (elapsedTimer !== null) { clearInterval(elapsedTimer); elapsedTimer = null }
}
watch(busy, value => {
  stopElapsedTimer()
  elapsedSeconds.value = 0
  if (value !== 'code-generate' && value !== 'create') return
  const startedAt = Date.now()
  elapsedTimer = setInterval(() => { elapsedSeconds.value = Math.floor((Date.now() - startedAt) / 1000) }, 1000)
  elapsedTimer.unref?.()  // Node(試験)では、タイマーが、プロセスの終了を妨げないようにする。ブラウザでは、数値が返るため、何もしない
})
onBeforeUnmount(() => { disposed = true; generation += 1; stopElapsedTimer(); stopResize() })
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
  if (referenceTemplate.value) input.reference_template_id = referenceTemplate.value.id
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
.analysis-workspace { width: 100%; box-sizing: border-box; padding: 20px; margin: 0; color: #334b50; }
.analysis-layout { --left-pane-percent: 66.7%; display: grid; grid-template-columns: minmax(0, calc(var(--left-pane-percent) - 6px)) 12px minmax(0, calc(100% - var(--left-pane-percent) - 6px)); gap: 0; align-items: start; }
.analysis-main { min-width: 0; order: 3; position: sticky; top: 8px; max-height: calc(100vh - 24px); overflow: auto; padding-left: 12px; }
.analysis-divider { order: 2; align-self: stretch; min-height: 180px; display: flex; justify-content: center; cursor: col-resize; touch-action: none; outline: none; }
.analysis-divider span { width: 4px; border-radius: 4px; background: #cbd8d7; transition: background-color .15s, box-shadow .15s; }
.analysis-divider:hover span, .analysis-divider:focus-visible span, .analysis-layout.resizing .analysis-divider span { background: #168779; box-shadow: 0 0 0 3px #16877922; }
.template-management { min-width: 0; border: 1px solid #d6dede; margin: 8px 0; }
.templates-head { display: flex; flex-wrap: wrap; gap: 4px 12px; width: 100%; text-align: left; padding: 6px 8px; }
.templates-body { min-width: 0; padding: 6px 8px; }
.notes { border: 1px solid #d1dddd; border-radius: 8px; margin-bottom: 12px; overflow: hidden; background: #fff; }
.notes-head { display: flex; align-items: center; flex-wrap: wrap; gap: 4px 8px; width: 100%; text-align: left; padding: 8px 10px; border: 0; border-radius: 0; }
.notes-head:not(:disabled) { background: #f4f8f8; color: #334b50; border-color: transparent; }
.notes-head em { font-style: normal; font-size: 11px; border-radius: 10px; padding: 1px 8px; background: #e6ecef; color: #647777; }
.notes-head small { display: inline; margin: 0; flex-basis: 100%; color: #6f5314; overflow-wrap: anywhere; }
.notes-body { padding: 4px 12px 10px; }
.notes-body p { margin: 6px 0; }
.analysis-side { min-width: 0; order: 1; display: grid; gap: 8px; border-right: 1px solid #e6ecef; padding-right: 16px; }
.side-title { font-size: 13px; margin: 0; color: #81929b; letter-spacing: .5px; }
.stage { border: 1px solid #d1dddd; border-radius: 8px; overflow: hidden; background: #fff; }
.stage.current { border-color: #168779; box-shadow: 0 0 0 2px #16877922; }
.stage.pending { opacity: .75; }
.stage-head { display: flex; align-items: center; flex-wrap: wrap; gap: 4px 8px; width: 100%; text-align: left; padding: 8px 10px; border: 0; border-radius: 0; }
.stage-head:not(:disabled) { background: #f4f8f8; color: #334b50; border-color: transparent; }
.stage-head strong { font-size: 14px; }
.stage-resources { font-size: 10px; font-weight: 400; color: #657b80; overflow-wrap: anywhere; }
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
.next-hint { display: block; color: #8a5a00; font-weight: 600; margin: 4px 0 0; }
.next-action-btn.ready { outline: 3px solid #d9a21b; outline-offset: 3px; font-weight: 700; animation: run-ready-pulse 1.6s ease-in-out 3; }
@media (prefers-reduced-motion: reduce) { .next-action-btn.ready { animation: none; } }
.stage-body { padding: 8px 12px 12px; overflow-wrap: anywhere; }
.plan-head { border: 1px solid #d1dddd; border-radius: 8px; padding: 8px 12px; }
@media (max-width: 960px) { .analysis-layout { grid-template-columns: minmax(0, 1fr); } .analysis-main { order: 2; position: static; max-height: none; overflow: visible; padding-left: 0; } .analysis-divider { display: none; } .analysis-side { order: 1; border-right: 0; padding-right: 0; } }
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
.boss-question { margin-left: auto; }
.artifact-card { border: 1px solid #d1dddd; border-radius: 8px; margin-bottom: 8px; background: #fff; }
.artifact-card > summary { padding: 8px 10px; cursor: pointer; font-weight: 700; background: #f4f8f8; }
.artifact-card > .run-target { padding: 0 10px 10px; }
.artifact-body { padding: 8px 12px 12px; overflow-wrap: anywhere; }
.recommendation { padding: 8px; border: 1px solid #d6dede; border-radius: 6px; background: #f7faf9; }
.recommendation + .recommendation { margin-top: 8px; }
.boss-help { margin: 8px 0; padding: 10px 12px; border: 2px solid #d9a21b; border-radius: 8px; background: #fff8e6; color: #6f5314; }
.boss-help p { margin: 4px 0; }
.approval-summary { padding: 8px 12px; border: 1px solid #8fb9b0; border-radius: 8px; background: #eef6f4; }
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
.generating { background: #e8f4fd; border-left: 3px solid #2a7fc1; color: #123c5a; padding: 8px 10px; font-weight: 600; }
.warning { background: #fff8e6; border-left: 3px solid #d9a21b; color: #6f5314; padding: 8px 10px; }
/* 分析案の警告(目的と期間・列の食い違いなど)は、見落とさないよう、赤字にして、「⚠！」を点滅させる(BOSS指示 2026-10-08)。動きを減らす設定の人には、点滅させない */
.reference-note { background: #eef6f4; border-left: 3px solid #168779; padding: 8px 10px; margin: 8px 0; }
.reference-note .next-action { font-weight: 600; }
.wrapper-notice { color: #b3120c; font-weight: 600; }  /* 外枠の更新は、操作が必要な案内。赤字・太字(点滅はしない。BOSS承認 2026-10-08) */
.plan-warning { background: #fdecea; border-left-color: #d32f2f; color: #b3120c; font-weight: 600; }
.warn-mark { display: inline-block; animation: warn-blink 1s steps(2, start) infinite; }
@keyframes warn-blink { to { visibility: hidden; } }
@media (prefers-reduced-motion: reduce) { .warn-mark { animation: none; } }
select { padding: 4px; font: inherit; max-width: 100%; }
button:not(:disabled) { border-color: #168779; color: white; background: #168779; cursor: pointer; }
small { overflow-wrap: anywhere; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; padding: 8px; background: #f4f8f8; border: 1px solid #d1dddd; font-size: 13px; }
.stage-body h4 { margin: 12px 0 6px; }
</style>
