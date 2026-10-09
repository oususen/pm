<template>
  <section class="templates">
    <AnalysisErrorBanner v-if="errorNotices.renderBanner" :notices="errorNotices.notices.value" />
    <h2>テンプレート</h2>
    <p>保存済みのテンプレートから、新しい分析案を作れます（AIは使いません。手順・データ範囲の承認、SQL試行、コード承認は、毎回行います）。</p>
    <p>承認したコードを、管理者承認待ちのテンプレートとして保存します。保存するのは、名称・目的・手順・条件・承認済みSQL・Python・期間・ハッシュです。実データ・結果・AIへ送った本文は保存しません。</p>
    <p v-if="canEdit && plan?.template" role="status">テンプレートから作成した分析案は、テンプレートとして保存できません（保存済みのコードをそのまま使うため、内容が同じで重複します）。コードを変えた新しい分析を作成したときに、保存できます。</p>
    <template v-else-if="canEdit">
      <p v-if="savable && plan?.codegen?.literal_values?.length" class="name-warning" role="alert"><span class="warn-mark" aria-hidden="true">⚠！</span> コードに直接書かれた値があります（{{ plan.codegen.literal_values.join('、') }}）。このテンプレートを再利用しても、これらの値は変えられません（保存はできます）。</p>
      <p v-if="!savable">保存には、手順・データ範囲・コードの承認が必要です（現在: {{ saveHint }}）。</p>
      <label>テンプレート名（必須・300文字以内）:
        <input v-model="templateName" type="text" maxlength="300" size="50" :disabled="!savable || !!busy" aria-label="保存するテンプレートの名前" @input="nameEdited = true; duplicateCount = null" @change="checkName"></label>
      <p v-if="duplicateCount > 0" class="name-warning" role="alert"><span class="warn-mark" aria-hidden="true">⚠！</span> 同じ名前のテンプレートが{{ duplicateCount }}件あります。区別しやすい名前に変えることをお勧めします（そのまま保存もできます）。</p>
      <label>カテゴリ（必須）:
        <select v-model="category" :disabled="!savable || !!busy" aria-label="保存するテンプレートのカテゴリ">
          <option value="">選択してください</option>
          <option v-for="item in CATEGORIES" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select></label>
      <label><input v-model="accepted" type="checkbox" :disabled="!savable || !!busy">コードを確認し、管理者承認待ちのテンプレートとして保存します（作成者と管理者以外には、名称・目的・状態・カテゴリだけが表示されます）</label>
      <button :disabled="!canSave || !accepted" @click="save">{{ busy === 'save' ? '保存中…' : 'テンプレートとして保存' }}</button>
    </template>
    <p v-else>閲覧のみです。保存にはAI分析の編集権限が必要です。</p>
    <p v-if="saved?.same_name_count > 0" class="name-warning" role="alert"><span class="warn-mark" aria-hidden="true">⚠！</span> 同じ名前のテンプレートが、ほかに{{ saved.same_name_count }}件あります。区別しやすい名前に変えることをお勧めします（管理者承認前は、一覧の詳細から名称を変えられます）。</p>
    <p v-if="saved" role="status">{{ saved.created ? '保存しました' : '保存済みです（同じ内容は重複して保存しません）' }}: テンプレート{{ saved.id }} / 版{{ saved.version }} / {{ saved.status_label }} / カテゴリ: {{ saved.category_label }}</p>
    <section v-if="reuseRow" class="reuse-panel" aria-label="変数の値の入力">
      <h3>テンプレート{{ reuseRow.id }}「{{ reuseRow.name }}」: 今回使う値</h3>
      <p>変数の値を、変えられます。変えた値だけがサーバーへ送られ、サーバーが検査します。値を空にすると、不備として拒否されます（保存済みの値には、戻しません）。</p>
      <p class="reuse-note">目的・手順・出力案の説明は、テンプレートを保存したときのものです。日付・品番などを変えても、説明の文は、自動では書き換わりません。全体の期間を変えても、比べる期間・除く期間は、自動では動きません（必要なら、一緒に直してください）。</p>
      <p v-for="item in reuseRow.parameters" :key="item.name">
        <label>{{ item.label }}（{{ item.name }}）:
          <input v-model="reuseValues[item.name]" :type="item.type === 'date' ? 'date' : 'text'" :maxlength="item.type === 'date' ? 10 : 40" :disabled="!!busy" :aria-label="item.label"></label>
        <span v-if="reuseValues[item.name] !== item.default">（変更あり。保存済みの値: {{ item.default }}）</span>
      </p>
      <p role="status">今回使う値: <span v-for="(item, index) in reuseRow.parameters" :key="item.name">{{ index ? ' / ' : '' }}{{ item.label }} = {{ reuseValues[item.name] === '' ? '（空）' : reuseValues[item.name] }}</span></p>
      <button :disabled="!canStartPlan" @click="startPlan(reuseRow, changedValues())">この値で分析案を作成</button>
      <button :disabled="!!busy" @click="closeReuse">取消（現在の分析案はそのまま）</button>
    </section>
    <h3>保存済みテンプレート</h3>
    <label>カテゴリの絞り込み:
      <select v-model="categoryFilter" :disabled="!!busy" aria-label="カテゴリの絞り込み">
        <option value="">すべて</option>
        <option v-for="item in CATEGORIES" :key="item.value" :value="item.value">{{ item.label }}</option>
      </select></label>
    <label v-if="canReview">状態の絞り込み:
      <select v-model="statusFilter" :disabled="!!busy">
        <option value="">すべて</option><option value="pending_admin">管理者承認待ち</option><option value="approved">正式</option>
        <option value="rejected">却下</option><option value="superseded">置換済み</option>
      </select></label>
    <button :disabled="!!busy" @click="load(1)">一覧を更新</button>
    <p v-if="loaded && !list.results.length">保存済みのテンプレートはありません。</p>
    <article v-for="row in list.results" :key="row.id">
      <p><strong>テンプレート{{ row.id }}: {{ row.name }}</strong> / カテゴリ: {{ row.category_label }} / 状態: {{ row.status_label }} / 作成者: {{ row.created_by }} / 保存日時: {{ formatDate(row.created_at) }} / 目的: {{ row.purpose }}
        <span v-if="!row.content_visible"> / SQL・Python・条件・期間は、作成者と管理者だけが確認できます。</span>
        <button v-else :disabled="!!busy" @click="showDetail(row.id)">{{ detail?.id === row.id ? '詳細を再取得' : '詳細を表示' }}</button>
        <button v-if="canReuse(row)" :disabled="!canStartPlan" @click="openReuse(row)">このテンプレートで分析案を作る</button>
        <button v-if="canReuse(row)" :disabled="!canStartReference" @click="selectReference(row)">このテンプレートを参考に分析する</button>
        <span v-if="row.status === 'pending_admin' && row.content_visible"> / システム管理者未承認</span></p>
      <div v-if="detail?.id === row.id">
        <p>期間: {{ detail.date_from }} ～ {{ detail.date_to }} / 条件: {{ detail.conditions }}</p>
        <p>手順: {{ (detail.procedure || []).join(' → ') }}</p>
        <h4>SQL（中間テーブル作成の手順）</h4>
        <pre v-for="step in detail.sql_steps || []" :key="step.name">{{ step.name }}: {{ step.query }}</pre>
        <h4>Python</h4><pre>{{ detail.python_code }}</pre>
        <small>コード全体のSHA-256: {{ detail.executed_code_sha256 }} / 固定外枠の版: {{ detail.wrapper_version }}</small>
        <p v-if="detail.reviewed_at">確認: {{ detail.status_label }} / 確認者: {{ detail.reviewed_by }} / 確認日時: {{ formatDate(detail.reviewed_at) }}</p>
        <p v-if="detail.rejection_reason">却下理由: {{ detail.rejection_reason }}</p>
        <p v-if="detail.replaces">この版は、テンプレート{{ detail.replaces }}（却下）の訂正版です。承認すると、元の版は置換済みになります。</p>
        <p v-if="detail.replacement_id">置換先: テンプレート{{ detail.replacement_id }}</p>
        <p v-if="detail.can_rename && canEdit">名称: <input v-model="newName" type="text" maxlength="300" size="50" :disabled="!!busy" aria-label="変更後のテンプレート名">
          <button :disabled="!!busy || !newName.trim() || newName.trim() === detail.name" @click="renameTemplate">名称を変更（管理者承認前だけ）</button></p>
        <p v-if="renameWarning > 0" class="name-warning" role="alert"><span class="warn-mark" aria-hidden="true">⚠！</span> 同じ名前のテンプレートが、ほかに{{ renameWarning }}件あります。</p>
        <p v-if="detail.can_change_category && canEdit">カテゴリ: {{ detail.category_label }} →
          <select v-model="newCategory" :disabled="!!busy" aria-label="変更後のカテゴリ">
            <option v-for="item in CATEGORIES" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
          <button :disabled="!!busy || newCategory === detail.category" @click="changeCategory">カテゴリを変更</button></p>
        <template v-if="detail.notifications">
          <p>通知（メール・PM通知。宛先のメールアドレス・本文は保存しません）: {{ detail.notifications.length ? '' : 'まだ通知の記録はありません。' }}</p>
          <ul v-if="detail.notifications.length" class="notice-records">
            <li v-for="item in detail.notifications" :key="item.id">{{ item.kind_label }} / {{ item.channel_label }} / 宛先: {{ item.recipient || 'なし' }} / 結果: {{ item.status_label }}<template v-if="item.reason_label"> / 理由: {{ item.reason_label }}</template> / 記録: {{ formatDate(item.created_at) }}<button v-if="canEdit && item.can_resend" :disabled="!!busy" @click="resendNotice(item)">再送（同じ宛先へ1回だけ）</button></li>
          </ul>
        </template>
        <template v-if="canReview && detail.status === 'pending_admin'">
          <p>管理者の確認: 上のSQL・Pythonと手順を確認してから、承認または却下してください。</p>
          <label>却下理由（却下のときだけ必須・{{ REASON_MAX }}文字以内）: <input v-model="reason" type="text" :maxlength="REASON_MAX" :disabled="!!busy" size="60"></label>
          <button :disabled="!!busy" @click="approve">承認（正式にする）</button>
          <button :disabled="!!busy || !reason.trim()" @click="reject">却下</button>
        </template>
        <template v-if="canReview && detail.status === 'rejected'">
          <p>訂正版: 現在の分析案（コード承認済み）を、この版の訂正版として保存できます（元の版は変わりません）。</p>
          <p v-if="savable && !category">カテゴリを選んでください（上の保存欄の「カテゴリ（必須）」。却下された版を開くと、元の版のカテゴリが初期値で入ります）。</p>
          <label><input v-model="acceptedCorrection" type="checkbox" :disabled="!savable || !!busy">コードを確認し、訂正版として保存します</label>
          <button :disabled="!canSave || !acceptedCorrection" @click="saveCorrection(detail.id)">この版の訂正版として保存</button>
        </template>
      </div>
    </article>
    <p v-if="loaded">{{ list.count }}件 / {{ page }}ページ</p>
    <button :disabled="!!busy || !list.previous" @click="load(page - 1)">前のページ</button>
    <button :disabled="!!busy || !list.next" @click="load(page + 1)">次のページ</button>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import api from '../../api/client'
import AnalysisErrorBanner from '../../components/AnalysisErrorBanner.vue'
import { useAnalysisErrorNotices } from '../../composables/analysisErrorNotices'

const props = defineProps({ plan: { type: Object, default: null }, canEdit: Boolean, canReview: Boolean, blocked: Boolean, reuseBlocked: Boolean, referenceBlocked: Boolean })
const emit = defineEmits(['plan-created', 'reference-selected'])
const busy = ref(''), error = ref(''), saved = ref(null), accepted = ref(false), acceptedCorrection = ref(false), detail = ref(null), reason = ref(''), statusFilter = ref('')
const CATEGORIES = Object.freeze([
  { value: 'receipt', label: '入荷' }, { value: 'shipment', label: '出荷' }, { value: 'inventory', label: '在庫' },
  { value: 'production', label: '生産' }, { value: 'quality', label: '品質' }, { value: 'other', label: 'その他' },
])
const category = ref(''), categoryFilter = ref(''), newCategory = ref('')
// テンプレート名(2026-10-08、BOSS承認)。初期値は分析案の題名。同じ名前の警告は、保存を止めない。名称の変更は、管理者承認前だけ(サーバーでも確認する)
const reuseRow = ref(null), reuseValues = ref({}) // 変数の値の入力(2-C、2026-10-08)。変えた値だけを送る。取消では、現在の分析案を変えない
const templateName = ref(''), nameEdited = ref(false), duplicateCount = ref(null), newName = ref(''), renameWarning = ref(0)
let nameToken = 0, reuseToken = 0 // reuseToken: 再利用の要求ごとの識別番号。分析案の切替・権限の喪失で進め、古い応答を採用しない(Codex P2)
let autoCategory = '' // 却下された版を開いたときに、初期値として入れた値(利用者が変えていなければ、次の版を開いたとき入れ替える)
const REASON_MAX = 500 // 却下理由の最大長(BOSS承認)。超える入力は送らない
const list = ref({ results: [], count: 0, next: null, previous: null }), page = ref(1), loaded = ref(false)
const errorNotices = useAnalysisErrorNotices([['template', error]])
let disposed = false, epoch = 0, saveToken = 0
// 画面で表示する失敗は固定文だけ。APIの本文は表示しない。
const SAVE_ERRORS = Object.freeze({
  400: '保存の指定が正しくありません。',
  403: 'テンプレートを保存する権限がありません。',
  404: '分析案が見つかりません。',
  409: '保存できる状態ではありません。承認・コード・版が最新か確認してください。',
  410: '分析案の期限が切れました。分析案を作り直してください。',
})
const REUSE_ERRORS = Object.freeze({
  400: '分析案の作成の指定が正しくありません。',
  403: '管理者承認前のテンプレートを再利用できるのは、作成者と管理者だけです。',
  404: 'テンプレートが見つかりません。',
  409: 'このテンプレートは再利用できません（却下・置換済み、内容や検査・ビューの公開定義の不一致）。新しい分析として作成してください。',
})
const CATEGORY_ERRORS = Object.freeze({
  400: 'カテゴリを入荷・出荷・在庫・生産・品質・その他から選んでください。',
  403: 'カテゴリを変更する権限がありません。',
  404: 'テンプレートが見つかりません。',
})
const REVIEW_ERRORS = Object.freeze({
  400: '入力が正しくありません。却下理由は必須で、500文字以内です。',
  403: 'テンプレートを確認する権限がありません。',
  404: 'テンプレートが見つかりません。',
  409: 'テンプレートの状態が変わりました。一覧を更新して、最新の内容を確認してください。',
})
const RESEND_ERRORS = Object.freeze({
  400: '再送の指定が正しくありません。',
  403: '再送する権限がありません。',
  404: '通知の記録が見つかりません。',
  409: 'この通知は再送できません（送信済み・再送済み・宛先なし、またはテンプレートの状態が変わりました）。',
})
const hasCode = computed(() => props.plan?.codegen?.status === 'code_approved' && !!props.plan.codegen.executed_code_sha256)
const savable = computed(() => props.plan?.status === 'data_approved' && hasCode.value && !props.plan?.template)
const canSave = computed(() => props.canEdit && !props.blocked && !busy.value && savable.value && !!category.value && !!templateName.value.trim())
const saveHint = computed(() => !props.plan ? '分析案なし' : props.plan.status !== 'data_approved' ? 'データ範囲が未承認' : 'コードが未承認')
// 再利用できるのは、全文を見られる正式・管理者承認待ちの行だけ(サーバーでも状態・権限を確認する)
const canReuse = row => props.canEdit && row.content_visible && ['approved', 'pending_admin'].includes(row.status)
const canStartPlan = computed(() => props.canEdit && !props.blocked && !props.reuseBlocked && !busy.value)
const formatDate = value => typeof value === 'string' ? value.replace('T', ' ').slice(0, 19) : ''

// 分析案・版が変われば、保存の確認を取り直す。保存結果と詳細は、別の分析案へ持ち越さない。
// 分析案または版が変わったら、確認・保存結果・未完了の保存の応答を取り直す(古い応答を新しい分析案の下に表示しない)
watch(() => [props.plan?.id, props.plan?.revision], () => { accepted.value = false; acceptedCorrection.value = false; saved.value = null; saveToken++ }, { flush: 'sync' })
// 分析案が替わったら、名前の初期値を、その分析案の題名にする(利用者が書き換えた名前は、同じ分析案の間だけ残す)
watch(() => [props.plan?.id, props.plan?.proposal?.title], ([id], [oldId] = []) => {
  if (id !== oldId) nameEdited.value = false
  if (!nameEdited.value) { templateName.value = typeof props.plan?.proposal?.title === 'string' ? props.plan.proposal.title : ''; duplicateCount.value = null }
}, { flush: 'sync', immediate: true })
watch(() => props.plan?.id, () => { error.value = ''; reuseToken++ }, { flush: 'sync' })
watch(() => props.canEdit, value => { if (!value) { accepted.value = false; acceptedCorrection.value = false; reuseToken++; reuseRow.value = null; reuseValues.value = {} } }, { flush: 'sync' })
watch([statusFilter, categoryFilter], () => load(1))
onBeforeUnmount(() => { disposed = true; epoch++ })
onMounted(() => load(1))

function save() { return doSave(null) }
function saveCorrection(id) { return props.canReview && typeof id === 'number' ? doSave(id) : undefined }
async function doSave(replaces) {
  // 通常の保存と訂正版の保存は、別々の確認チェックを使う(片方の確認をもう一方へ持ち越さない)
  const confirmed = replaces === null ? accepted : acceptedCorrection
  if (!canSave.value || !confirmed.value) return
  const target = props.plan, current = epoch, token = saveToken
  busy.value = 'save'; error.value = ''
  let done = false
  try {
    const body = { plan_id: target.id, revision: target.revision, category: category.value, name: templateName.value.trim() }
    if (replaces !== null) body.replaces = replaces
    const response = await api.aiAnalysis.saveTemplate(body)
    if (!disposed && current === epoch && token === saveToken) { saved.value = response.data; confirmed.value = false; category.value = ''; done = true }
  } catch (e) {
    if (!disposed && current === epoch && token === saveToken) error.value = SAVE_ERRORS[e.response?.status] || 'テンプレートを保存できませんでした。保存されたか一覧で確認してください。'
  } finally { if (!disposed && current === epoch) busy.value = '' }
  // 保存は成立している可能性があるため、分析案が切り替わっても一覧は取り直す
  if (!disposed && current === epoch && (done || token !== saveToken)) return load(1)
}
async function checkName() {
  const name = templateName.value.trim(), token = ++nameToken
  if (!name) { duplicateCount.value = null; return }
  try {
    const response = await api.aiAnalysis.templates({ name })
    if (!disposed && token === nameToken) duplicateCount.value = Number.isInteger(response.data?.count) ? response.data.count : null
  } catch { if (!disposed && token === nameToken) duplicateCount.value = null }  // 確認できなくても、保存は止めない(警告が出ないだけ)
}
const NAME_ERRORS = Object.freeze({
  400: 'テンプレート名を入力してください(300文字以内。改行は使えません)。',
  403: '名称を変更する権限がありません。',
  404: 'テンプレートが見つかりません。',
  409: '名称を変えられるのは、管理者承認前のテンプレートだけです。状態が変わった可能性があります。一覧を更新してください。',
})
async function renameTemplate() {
  if (!props.canEdit || busy.value || !detail.value?.can_rename || !newName.value.trim() || newName.value.trim() === detail.value.name) return
  const current = epoch, target = detail.value, value = newName.value.trim()
  busy.value = 'rename'; error.value = ''; renameWarning.value = 0
  let count = 0
  try {
    const response = await api.aiAnalysis.renameTemplate(target.id, { name: value })
    count = Number.isInteger(response.data?.same_name_count) ? response.data.same_name_count : 0
  } catch (e) {
    if (!disposed && current === epoch) error.value = NAME_ERRORS[e.response?.status] || '名称を変更できませんでした。'
  } finally { if (!disposed && current === epoch) busy.value = '' }
  // 成否にかかわらず、最新の一覧・詳細を取り直す(状態の版が進むため、承認などの操作も最新の内容になる)
  if (!disposed && current === epoch) { const failure = error.value; await load(page.value); await showDetail(target.id); if (!disposed && current === epoch) { if (failure) error.value = failure; else renameWarning.value = count } }
}
async function load(target = 1) {
  if (busy.value) return
  const current = epoch
  busy.value = 'list'; error.value = ''
  try {
    const params = { page: target }
    if (statusFilter.value) params.status = statusFilter.value
    if (categoryFilter.value) params.category = categoryFilter.value
    const response = await api.aiAnalysis.templates(params)
    if (!disposed && current === epoch) { list.value = response.data; page.value = target; loaded.value = true; detail.value = null }
  } catch { if (!disposed && current === epoch) error.value = 'テンプレートの一覧を取得できませんでした。' }
  finally { if (!disposed && current === epoch) busy.value = '' }
}
async function review(call, message) {
  if (!props.canReview || busy.value || !detail.value) return
  const current = epoch, target = detail.value
  busy.value = 'review'; error.value = ''
  let done = false
  try {
    await call(target)
    done = true
  } catch (e) {
    if (!disposed && current === epoch) error.value = REVIEW_ERRORS[e.response?.status] || message
  } finally { if (!disposed && current === epoch) busy.value = '' }
  // 成否にかかわらず、最新の状態を取り直す(成立した可能性・他の管理者の操作を反映する)
  if (!disposed && current === epoch && (done || error.value)) {
    const failure = error.value // 取り直しで失敗の表示と、入力した却下理由を消さない(成功したときだけ理由を消す)
    const typed = reason.value
    await load(page.value)
    if (detail.value === null) await showDetail(target.id)
    if (failure && !disposed && current === epoch) { error.value = failure; reason.value = typed } else reason.value = ''
  }
}
function approve() {
  if (!props.canReview || !detail.value || detail.value.status !== 'pending_admin') return
  if (!window.confirm('このテンプレートを正式にします。コードを確認しましたか？（訂正版の場合、元の却下版は置換済みになります）')) return
  return review(target => api.aiAnalysis.approveTemplate(target.id, { state_revision: target.state_revision }), 'テンプレートを承認できませんでした。一覧で状態を確認してください。')
}
function reject() {
  if (!props.canReview || !detail.value || detail.value.status !== 'pending_admin' || !reason.value.trim() || reason.value.length > REASON_MAX) return
  if (!window.confirm('このテンプレートを却下します。却下理由は作成者と管理者だけが確認できます。')) return
  const text = reason.value
  return review(target => api.aiAnalysis.rejectTemplate(target.id, { state_revision: target.state_revision, reason: text }), 'テンプレートを却下できませんでした。一覧で状態を確認してください。')
}
async function resendNotice(item) {
  if (!props.canEdit || busy.value || !detail.value || !item?.can_resend) return
  if (!window.confirm('このメールを、同じ宛先へ再送します。再送は1回だけです。よろしいですか？')) return
  const current = epoch, target = detail.value
  busy.value = 'resend'; error.value = ''
  try {
    await api.aiAnalysis.resendTemplateNotification(item.id)
  } catch (e) {
    if (!disposed && current === epoch) error.value = RESEND_ERRORS[e.response?.status] || '再送できませんでした。'
  } finally { if (!disposed && current === epoch) busy.value = '' }
  // 成否にかかわらず、最新の通知の記録を取り直す(再送の結果・他の人の再送を反映する)
  if (!disposed && current === epoch) {
    const failure = error.value, typed = reason.value // 取り直しで、失敗の表示と、入力中の却下理由を消さない
    await showDetail(target.id)
    if (!disposed && current === epoch) { reason.value = typed; if (failure) error.value = failure }
  }
}
async function changeCategory() {
  if (!props.canEdit || busy.value || !detail.value?.can_change_category || !newCategory.value || newCategory.value === detail.value.category) return
  const current = epoch, target = detail.value, value = newCategory.value
  busy.value = 'category'; error.value = ''
  try {
    await api.aiAnalysis.changeTemplateCategory(target.id, { category: value })
  } catch (e) {
    if (!disposed && current === epoch) error.value = CATEGORY_ERRORS[e.response?.status] || 'カテゴリを変更できませんでした。'
  } finally { if (!disposed && current === epoch) busy.value = '' }
  // 成否にかかわらず、最新の一覧・詳細を取り直す
  if (!disposed && current === epoch) { const failure = error.value; await load(page.value); await showDetail(target.id); if (failure && !disposed && current === epoch) error.value = failure }
}
const REUSE_REASONS = Object.freeze({
  parameters_def_date: '日付は、YYYY-MM-DDの形で入力してください。',
  parameters_def_value: 'コードは、英数字・アンダースコア・ハイフンだけで入力してください。',
  parameters_def_unregistered: '登録されていない品番・顧客コード・納入先コードです。',
  parameters_def_order: '開始日は、終了日以前にしてください。',
  parameters_def_outside: '比べる期間・除く期間は、全体の期間の中に収めてください。全体の期間を変えたときは、これらも一緒に直してください。',
})
// 400の理由コードがあれば、項目別の固定文(と、該当する変数のラベル)を出す。理由コードがなければ、ステータスごとの固定文
function reuseFailure(e, row) {
  const data = e.response?.data, reason = Array.isArray(data?.reasons) ? data.reasons.find(item => typeof item === 'string' && Object.hasOwn(REUSE_REASONS, item)) : null
  if (e.response?.status !== 400 || !reason) return REUSE_ERRORS[e.response?.status] || '分析案を作成できませんでした。'
  const names = Array.isArray(data.names?.[reason]) ? data.names[reason].filter(name => typeof name === 'string' && /^[a-z][a-z0-9_]*$/.test(name)) : []
  const labels = names.map(name => row.parameters?.find(item => item.name === name)?.label || name)
  return labels.length ? `${REUSE_REASONS[reason]}（該当: ${labels.join('、')}）` : REUSE_REASONS[reason]
}
// テンプレートを参考にした生成(2026-10-09、BOSS承認 段階C): 参考にするテンプレートを、親(分析の画面)へ渡す。AIは、ここでは呼ばない。
// 目的・期間の入力と、社外送信前の確認(参考の全文を含む)は、親の画面で行う。再利用(保存済みコードをそのまま使う)とは別の操作
const canStartReference = computed(() => props.canEdit && !props.blocked && !props.referenceBlocked && !busy.value)  // 実行中は、押せない(親が黙って無視しない)
function selectReference(row) {
  if (!canReuse(row) || !canStartReference.value) return
  emit('reference-selected', { id: row.id, version: row.version, name: row.name, status: row.status })
}
function openReuse(row) {
  if (!canReuse(row) || !canStartPlan.value) return
  if (!Array.isArray(row.parameters) || !row.parameters.length) return startPlan(row) // 変数のないテンプレートは、入力欄なしで、従来どおり作る
  if (reuseRow.value?.id === row.id) return // 同じテンプレートを押し直しても、入力した値を残す
  if (reuseRow.value && Object.keys(changedValues()).length && !window.confirm('入力した値を破棄して、別のテンプレートの入力欄を開きます。よろしいですか？')) return
  reuseRow.value = row; reuseValues.value = Object.fromEntries(row.parameters.map(item => [item.name, item.default]))
}
function closeReuse() { if (!busy.value) { reuseRow.value = null; reuseValues.value = {} } }
// 保存済みの値(default)から変えた値だけを返す。空にした値は、変えた値として送る(サーバーが拒否する。勝手に、保存済みの値へ戻さない)
function changedValues() {
  const changed = {}
  for (const item of reuseRow.value?.parameters || []) { const value = reuseValues.value[item.name]; if (value !== item.default) changed[item.name] = value ?? '' }
  return changed
}
async function startPlan(row, parameters) {
  if (!canReuse(row) || !canStartPlan.value) return
  if (props.plan && !window.confirm('現在の分析案を破棄して、このテンプレートから新しい分析案を作ります。よろしいですか？')) return
  const current = epoch, token = ++reuseToken, startedPlan = props.plan?.id ?? null
  // 応答を採用してよいのは、この要求が最新で、開始時と同じ分析案・編集権限のとき(切替後の応答で、新しい分析案・入力を壊さない)
  const stale = () => disposed || current !== epoch || token !== reuseToken || !props.canEdit || (props.plan?.id ?? null) !== startedPlan
  busy.value = 'reuse'; error.value = ''
  try {
    const changed = parameters && Object.keys(parameters).length ? parameters : undefined  // 変えた値がなければ、値を送らない(従来どおり)
    const response = changed ? await api.aiAnalysis.createTemplatePlan(row.id, changed) : await api.aiAnalysis.createTemplatePlan(row.id)
    if (!stale()) { emit('plan-created', response.data); reuseRow.value = null; reuseValues.value = {} }  // 作成に成功した後だけ、入力欄を閉じる
  } catch (e) {
    if (!stale()) error.value = reuseFailure(e, row)  // 失敗しても、入力した値と現在の分析案は、そのまま
  } finally { if (!disposed && current === epoch) busy.value = '' }
}
async function showDetail(id) {
  if (busy.value) return
  const current = epoch
  busy.value = 'detail'; error.value = ''
  try {
    const response = await api.aiAnalysis.template(id)
    if (!disposed && current === epoch) {
      detail.value = response.data.content_visible ? response.data : null; reason.value = ''
      newCategory.value = detail.value?.category || ''
      newName.value = detail.value?.name || ''; renameWarning.value = 0
      // 却下された版の訂正版を保存するときの初期値は、元の版のカテゴリ(変えてもよい)。利用者が選んだ値は上書きしない
      if (detail.value?.status === 'rejected' && (!category.value || category.value === autoCategory)) {
        category.value = detail.value.category || ''; autoCategory = category.value
      }
    }
  } catch { if (!disposed && current === epoch) error.value = 'テンプレートの詳細を取得できませんでした。' }
  finally { if (!disposed && current === epoch) busy.value = '' }
}
</script>

<style scoped>
.templates { border-top: 1px solid #ccc; margin-top: 20px; } button { margin: 4px; padding: 8px; } article { margin: 12px 0; padding: 8px; background: #f5f9f8; }
article p { margin: 2px 0; } .notice-records { margin: 2px 0 6px; padding-left: 1.4em; font-size: 13px; } pre { white-space: pre-wrap; overflow-wrap: anywhere; margin: 4px 0; }
.reuse-panel { margin: 12px 0; padding: 8px; background: #eef6f4; border: 1px solid #8fb9b0; } .reuse-note { color: #6f5314; }
.name-warning { background: #fdecea; border-left: 3px solid #d32f2f; color: #b3120c; font-weight: 600; padding: 8px 10px; }
.warn-mark { display: inline-block; animation: warn-blink 1s steps(2, start) infinite; }
@keyframes warn-blink { to { visibility: hidden; } }
@media (prefers-reduced-motion: reduce) { .warn-mark { animation: none; } }
</style>
