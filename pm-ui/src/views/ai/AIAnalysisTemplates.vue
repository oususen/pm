<template>
  <section class="templates">
    <AnalysisErrorBanner v-if="errorNotices.renderBanner" :notices="errorNotices.notices.value" />
    <h2>5. テンプレート</h2>
    <p>承認したコードを、管理者承認待ちのテンプレートとして保存します。保存するのは、名称・目的・手順・条件・承認済みSQL・Python・期間・ハッシュです。実データ・結果・AIへ送った本文は保存しません。</p>
    <template v-if="canEdit">
      <p v-if="!savable">保存には、手順・データ範囲・コードの承認が必要です（現在: {{ saveHint }}）。</p>
      <label><input v-model="accepted" type="checkbox" :disabled="!savable || !!busy">コードを確認し、管理者承認待ちのテンプレートとして保存します（作成者と管理者以外には、名称・目的・状態だけが表示されます）</label>
      <button :disabled="!canSave || !accepted" @click="save">{{ busy === 'save' ? '保存中…' : 'テンプレートとして保存' }}</button>
    </template>
    <p v-else>閲覧のみです。保存にはAI分析の編集権限が必要です。</p>
    <p v-if="saved" role="status">{{ saved.created ? '保存しました' : '保存済みです（同じ内容は重複して保存しません）' }}: テンプレート{{ saved.id }} / 版{{ saved.version }} / {{ saved.status_label }}</p>
    <h3>保存済みテンプレート</h3>
    <button :disabled="!!busy" @click="load(1)">一覧を更新</button>
    <p v-if="loaded && !list.results.length">保存済みのテンプレートはありません。</p>
    <article v-for="row in list.results" :key="row.id">
      <p><strong>テンプレート{{ row.id }}: {{ row.name }}</strong> / 状態: {{ row.status_label }} / 作成者: {{ row.created_by }} / 保存日時: {{ formatDate(row.created_at) }} / 目的: {{ row.purpose }}
        <span v-if="!row.content_visible"> / SQL・Python・条件・期間は、作成者と管理者だけが確認できます。</span>
        <button v-else :disabled="!!busy" @click="showDetail(row.id)">{{ detail?.id === row.id ? '詳細を再取得' : '詳細を表示' }}</button></p>
      <div v-if="detail?.id === row.id">
        <p>期間: {{ detail.date_from }} ～ {{ detail.date_to }} / 条件: {{ detail.conditions }}</p>
        <p>手順: {{ (detail.procedure || []).join(' → ') }}</p>
        <h4>SQL（中間テーブル作成の手順）</h4>
        <pre v-for="step in detail.sql_steps || []" :key="step.name">{{ step.name }}: {{ step.query }}</pre>
        <h4>Python</h4><pre>{{ detail.python_code }}</pre>
        <small>コード全体のSHA-256: {{ detail.executed_code_sha256 }} / 固定外枠の版: {{ detail.wrapper_version }}</small>
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

const props = defineProps({ plan: { type: Object, default: null }, canEdit: Boolean, blocked: Boolean })
const busy = ref(''), error = ref(''), saved = ref(null), accepted = ref(false), detail = ref(null)
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
const hasCode = computed(() => props.plan?.codegen?.status === 'code_approved' && !!props.plan.codegen.executed_code_sha256)
const savable = computed(() => props.plan?.status === 'data_approved' && hasCode.value)
const canSave = computed(() => props.canEdit && !props.blocked && !busy.value && savable.value)
const saveHint = computed(() => !props.plan ? '分析案なし' : props.plan.status !== 'data_approved' ? 'データ範囲が未承認' : 'コードが未承認')
const formatDate = value => typeof value === 'string' ? value.replace('T', ' ').slice(0, 19) : ''

// 分析案・版が変われば、保存の確認を取り直す。保存結果と詳細は、別の分析案へ持ち越さない。
// 分析案または版が変わったら、確認・保存結果・未完了の保存の応答を取り直す(古い応答を新しい分析案の下に表示しない)
watch(() => [props.plan?.id, props.plan?.revision], () => { accepted.value = false; saved.value = null; saveToken++ }, { flush: 'sync' })
watch(() => props.plan?.id, () => { error.value = '' }, { flush: 'sync' })
watch(() => props.canEdit, value => { if (!value) accepted.value = false }, { flush: 'sync' })
onBeforeUnmount(() => { disposed = true; epoch++ })
onMounted(() => load(1))

async function save() {
  if (!canSave.value || !accepted.value) return
  const target = props.plan, current = epoch, token = saveToken
  busy.value = 'save'; error.value = ''
  let done = false
  try {
    const response = await api.aiAnalysis.saveTemplate({ plan_id: target.id, revision: target.revision })
    if (!disposed && current === epoch && token === saveToken) { saved.value = response.data; accepted.value = false; done = true }
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
    const response = await api.aiAnalysis.templates({ page: target })
    if (!disposed && current === epoch) { list.value = response.data; page.value = target; loaded.value = true; detail.value = null }
  } catch { if (!disposed && current === epoch) error.value = 'テンプレートの一覧を取得できませんでした。' }
  finally { if (!disposed && current === epoch) busy.value = '' }
}
async function showDetail(id) {
  if (busy.value) return
  const current = epoch
  busy.value = 'detail'; error.value = ''
  try {
    const response = await api.aiAnalysis.template(id)
    if (!disposed && current === epoch) detail.value = response.data.content_visible ? response.data : null
  } catch { if (!disposed && current === epoch) error.value = 'テンプレートの詳細を取得できませんでした。' }
  finally { if (!disposed && current === epoch) busy.value = '' }
}
</script>

<style scoped>
.templates { border-top: 1px solid #ccc; margin-top: 20px; } button { margin: 4px; padding: 8px; } article { margin: 12px 0; padding: 8px; background: #f5f9f8; }
article p { margin: 2px 0; } pre { white-space: pre-wrap; overflow-wrap: anywhere; margin: 4px 0; }
</style>
