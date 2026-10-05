<template>
  <section class="templates">
    <AnalysisErrorBanner v-if="errorNotices.renderBanner" :notices="errorNotices.notices.value" />
    <h2>テンプレート</h2>
    <p>保存済みのテンプレートから、新しい分析案を作れます（AIは使いません。手順・データ範囲の承認、SQL試行、コード承認は、毎回行います）。</p>
    <p>承認したコードを、管理者承認待ちのテンプレートとして保存します。保存するのは、名称・目的・手順・条件・承認済みSQL・Python・期間・ハッシュです。実データ・結果・AIへ送った本文は保存しません。</p>
    <p v-if="canEdit && plan?.template" role="status">テンプレートから作成した分析案は、テンプレートとして保存できません（保存済みのコードをそのまま使うため、内容が同じで重複します）。コードを変えた新しい分析を作成したときに、保存できます。</p>
    <template v-else-if="canEdit">
      <p v-if="!savable">保存には、手順・データ範囲・コードの承認が必要です（現在: {{ saveHint }}）。</p>
      <label><input v-model="accepted" type="checkbox" :disabled="!savable || !!busy">コードを確認し、管理者承認待ちのテンプレートとして保存します（作成者と管理者以外には、名称・目的・状態だけが表示されます）</label>
      <button :disabled="!canSave || !accepted" @click="save">{{ busy === 'save' ? '保存中…' : 'テンプレートとして保存' }}</button>
    </template>
    <p v-else>閲覧のみです。保存にはAI分析の編集権限が必要です。</p>
    <p v-if="saved" role="status">{{ saved.created ? '保存しました' : '保存済みです（同じ内容は重複して保存しません）' }}: テンプレート{{ saved.id }} / 版{{ saved.version }} / {{ saved.status_label }}</p>
    <h3>保存済みテンプレート</h3>
    <label v-if="canReview">状態の絞り込み:
      <select v-model="statusFilter" :disabled="!!busy">
        <option value="">すべて</option><option value="pending_admin">管理者承認待ち</option><option value="approved">正式</option>
        <option value="rejected">却下</option><option value="superseded">置換済み</option>
      </select></label>
    <button :disabled="!!busy" @click="load(1)">一覧を更新</button>
    <p v-if="loaded && !list.results.length">保存済みのテンプレートはありません。</p>
    <article v-for="row in list.results" :key="row.id">
      <p><strong>テンプレート{{ row.id }}: {{ row.name }}</strong> / 状態: {{ row.status_label }} / 作成者: {{ row.created_by }} / 保存日時: {{ formatDate(row.created_at) }} / 目的: {{ row.purpose }}
        <span v-if="!row.content_visible"> / SQL・Python・条件・期間は、作成者と管理者だけが確認できます。</span>
        <button v-else :disabled="!!busy" @click="showDetail(row.id)">{{ detail?.id === row.id ? '詳細を再取得' : '詳細を表示' }}</button>
        <button v-if="canReuse(row)" :disabled="!canStartPlan" @click="startPlan(row)">このテンプレートで分析案を作る</button>
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
        <template v-if="detail.notifications">
          <p>通知（メール・PM通知。宛先のメールアドレス・本文は保存しません）: {{ detail.notifications.length ? '' : 'まだ通知の記録はありません。' }}</p>
          <ul v-if="detail.notifications.length" class="notice-records">
            <li v-for="item in detail.notifications" :key="item.id">{{ item.kind_label }} / {{ item.channel_label }} / 宛先: {{ item.recipient || 'なし' }} / 結果: {{ item.status_label }}<template v-if="item.reason_label"> / 理由: {{ item.reason_label }}</template> / 記録: {{ formatDate(item.created_at) }}</li>
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

const props = defineProps({ plan: { type: Object, default: null }, canEdit: Boolean, canReview: Boolean, blocked: Boolean, reuseBlocked: Boolean })
const emit = defineEmits(['plan-created'])
const busy = ref(''), error = ref(''), saved = ref(null), accepted = ref(false), acceptedCorrection = ref(false), detail = ref(null), reason = ref(''), statusFilter = ref('')
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
const REVIEW_ERRORS = Object.freeze({
  400: '入力が正しくありません。却下理由は必須で、500文字以内です。',
  403: 'テンプレートを確認する権限がありません。',
  404: 'テンプレートが見つかりません。',
  409: 'テンプレートの状態が変わりました。一覧を更新して、最新の内容を確認してください。',
})
const hasCode = computed(() => props.plan?.codegen?.status === 'code_approved' && !!props.plan.codegen.executed_code_sha256)
const savable = computed(() => props.plan?.status === 'data_approved' && hasCode.value && !props.plan?.template)
const canSave = computed(() => props.canEdit && !props.blocked && !busy.value && savable.value)
const saveHint = computed(() => !props.plan ? '分析案なし' : props.plan.status !== 'data_approved' ? 'データ範囲が未承認' : 'コードが未承認')
// 再利用できるのは、全文を見られる正式・管理者承認待ちの行だけ(サーバーでも状態・権限を確認する)
const canReuse = row => props.canEdit && row.content_visible && ['approved', 'pending_admin'].includes(row.status)
const canStartPlan = computed(() => props.canEdit && !props.blocked && !props.reuseBlocked && !busy.value)
const formatDate = value => typeof value === 'string' ? value.replace('T', ' ').slice(0, 19) : ''

// 分析案・版が変われば、保存の確認を取り直す。保存結果と詳細は、別の分析案へ持ち越さない。
// 分析案または版が変わったら、確認・保存結果・未完了の保存の応答を取り直す(古い応答を新しい分析案の下に表示しない)
watch(() => [props.plan?.id, props.plan?.revision], () => { accepted.value = false; acceptedCorrection.value = false; saved.value = null; saveToken++ }, { flush: 'sync' })
watch(() => props.plan?.id, () => { error.value = '' }, { flush: 'sync' })
watch(() => props.canEdit, value => { if (!value) { accepted.value = false; acceptedCorrection.value = false } }, { flush: 'sync' })
watch(statusFilter, () => load(1))
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
    const body = { plan_id: target.id, revision: target.revision }
    if (replaces !== null) body.replaces = replaces
    const response = await api.aiAnalysis.saveTemplate(body)
    if (!disposed && current === epoch && token === saveToken) { saved.value = response.data; confirmed.value = false; done = true }
  } catch (e) {
    if (!disposed && current === epoch && token === saveToken) error.value = SAVE_ERRORS[e.response?.status] || 'テンプレートを保存できませんでした。保存されたか一覧で確認してください。'
  } finally { if (!disposed && current === epoch) busy.value = '' }
  // 保存は成立している可能性があるため、分析案が切り替わっても一覧は取り直す
  if (!disposed && current === epoch && (done || token !== saveToken)) return load(1)
}
async function load(target = 1) {
  if (busy.value) return
  const current = epoch
  busy.value = 'list'; error.value = ''
  try {
    const response = await api.aiAnalysis.templates(statusFilter.value ? { page: target, status: statusFilter.value } : { page: target })
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
async function startPlan(row) {
  if (!canReuse(row) || !canStartPlan.value) return
  if (props.plan && !window.confirm('現在の分析案を破棄して、このテンプレートから新しい分析案を作ります。よろしいですか？')) return
  const current = epoch
  busy.value = 'reuse'; error.value = ''
  try {
    const response = await api.aiAnalysis.createTemplatePlan(row.id)
    if (!disposed && current === epoch) emit('plan-created', response.data)
  } catch (e) {
    if (!disposed && current === epoch) error.value = REUSE_ERRORS[e.response?.status] || '分析案を作成できませんでした。'
  } finally { if (!disposed && current === epoch) busy.value = '' }
}
async function showDetail(id) {
  if (busy.value) return
  const current = epoch
  busy.value = 'detail'; error.value = ''
  try {
    const response = await api.aiAnalysis.template(id)
    if (!disposed && current === epoch) { detail.value = response.data.content_visible ? response.data : null; reason.value = '' }
  } catch { if (!disposed && current === epoch) error.value = 'テンプレートの詳細を取得できませんでした。' }
  finally { if (!disposed && current === epoch) busy.value = '' }
}
</script>

<style scoped>
.templates { border-top: 1px solid #ccc; margin-top: 20px; } button { margin: 4px; padding: 8px; } article { margin: 12px 0; padding: 8px; background: #f5f9f8; }
article p { margin: 2px 0; } .notice-records { margin: 2px 0 6px; padding-left: 1.4em; font-size: 13px; } pre { white-space: pre-wrap; overflow-wrap: anywhere; margin: 4px 0; }
</style>
