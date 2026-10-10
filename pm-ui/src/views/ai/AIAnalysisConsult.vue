<template>
  <section class="consult" aria-label="AIと目的を整える">
    <button type="button" class="consult-head" :aria-expanded="open" aria-controls="consult-body" @click="open = !open">
      <strong>AIと目的を整える</strong><em>{{ open ? '畳む' : '開く' }}</em>
      <small v-if="!open">目的を書きにくいときに、AIと相談できます（{{ external ? `社外サービス（${providerLabel}）へ、登録名称をコードへ置換して送ります` : 'ローカルAIだけ。社外へ送りません' }}）</small>
    </button>
    <div v-show="open" id="consult-body" class="consult-body">
      <template v-if="external">
        <p class="warning">やり取りは、上で選んだ社外サービス（{{ providerLabel }}）へ送ります。登録名称（社員・顧客・仕入先など）はコードへ置換して送ります。送るのは、あなたの発言・AIの過去の返事・**承認済みテンプレートの名称と目的**・公開ビューの説明・今日の日付です。未登録の人名・社名は置換されません。DBの明細行・数値は送りません。</p>
        <label class="ack"><input v-model="externalAck" type="checkbox" :disabled="!usable || !!busy">社外サービス（{{ providerLabel }}）へ、置換後の内容を送ることを了承します</label>
        <p class="note">送った内容（置換後）は、各発言の下に表示します。やり取りは保存されません（画面を閉じる・分析案を作ると消えます）。AIは数値を知らず、助言と文案だけを出します。</p>
      </template>
      <p v-else class="note">やり取りはローカルAI（Qwen）で行い、社外へ送りません。やり取りは保存されません（画面を閉じる・分析案を作ると消えます）。AIは数値を知らず、助言と文案だけを出します。</p>
      <p v-if="!messages.length" class="note">例: 「先月の出荷を製品別に比べたい」のように、分かる範囲で書いてください。AIが、期間や対象を質問します。</p>
      <ul v-if="messages.length" class="log">
        <li v-for="(item, index) in messages" :key="index" :class="item.role"><b>{{ item.role === 'user' ? (userName || 'あなた') : 'AI' }}:</b> {{ item.content }}
          <small v-if="item.sent" class="sent">社外へ送った内容（置換後）: {{ item.sent }}</small></li>
      </ul>
      <p v-if="error" class="error">{{ error }}</p>
      <div class="send">
        <textarea v-model="input" rows="2" :disabled="!usable || !!busy" placeholder="AIへの相談を入力してください。" aria-label="AIへの相談"></textarea>
        <button type="button" :disabled="!canSend" @click="send">{{ busy === 'send' ? 'AIが考えています…' : '送信' }}</button>
        <button type="button" :disabled="!!busy || !messages.length" @click="reset">やり直す</button>
      </div>
      <section v-if="draft && (draft.purpose || draft.date_from)" class="draft">
        <p><b>AIの文案</b></p>
        <p v-if="draft.purpose">目的: {{ draft.purpose }}</p>
        <p v-if="draft.date_from">期間: {{ draft.date_from }} ～ {{ draft.date_to }}</p>
        <p v-if="external" class="note">社外サービスの文案には、登録名称のコード（例: CUST-001）が含まれることがあります。取り込んだ後、実名へ直してください。</p>
        <button type="button" :disabled="!usable || !!busy" @click="apply">目的欄・期間欄に取り込む</button>
      </section>
      <section v-if="templates.length" class="recommend">
        <p><b>近い承認済みテンプレート（{{ templates.length }}件）</b></p>
        <p v-for="item in templates" :key="item.id">テンプレート{{ item.id }}（版{{ item.version }}） / {{ item.name }} / カテゴリ: {{ item.category_label }} / 目的: {{ item.purpose }} / 期間: {{ item.date_from }} ～ {{ item.date_to }}
          <button type="button" :disabled="!usable || !!busy" @click="useTemplate(item)">このテンプレートで分析案を作る</button>
          <button type="button" :disabled="!canEdit || blocked || !!busy || !Number.isInteger(item.id)" @click="selectReference(item)">このテンプレートを参考に分析する</button></p>
      </section>
      <p v-if="!usable" class="note">{{ unusableReason }}</p>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import api from '../../api/client'

const props = defineProps({
  plan: { type: Object, default: null }, canEdit: Boolean, blocked: Boolean, purpose: { type: String, default: '' }, dateFrom: { type: String, default: '' }, dateTo: { type: String, default: '' },
  // 上部で選んだAI。社外のAIのときは、置換後の内容を送ることを了承してから送る(選び直したら、了承も取り直す)
  provider: { type: String, default: 'qwen' }, model: { type: String, default: '' }, external: Boolean, providerLabel: { type: String, default: '' }, providerAvailable: { type: Boolean, default: true },
  userName: { type: String, default: '' }, // 履歴の発言者の表示(ログイン中の利用者名)。なければ「あなた」
})
const emit = defineEmits(['apply', 'plan-created', 'reference-selected'])
const open = ref(false), input = ref(''), busy = ref(''), error = ref(''), externalAck = ref(false)
const messages = ref([]), draft = ref(null), templates = ref([])
let disposed = false, epoch = 0
// 画面で表示する失敗は固定文だけ。APIの本文は表示しない。
const CONSULT_ERRORS = Object.freeze({
  400: '送る内容、またはAIの選択が正しくありません。上のAIプロバイダ・モデルを確認してください。',
  422: '発言、またはこれまでのAIの返事に、コードへ置換できない名称が含まれます。表現を変えるか、「やり直す」でやり取りを消して、もう一度送ってください（社外へは送っていません）。',
  424: '承認済みテンプレートの名称・目的を、コードへ置換できません。管理者へ、名称の登録の確認を依頼してください（社外へは送っていません）。',
  403: 'AIと相談する権限がありません。「AI分析」の編集権限、または社外サービスへの送信の許可を確認してください。',
  409: '社外サービスへ送ることの了承が必要です。',
  502: 'AIの返答を検証できませんでした。もう一度送ってください。',
  503: 'AIまたはコード置換の処理を使えません。しばらくしてから、もう一度送ってください。（上のAI設定・APIキーも確認してください）',
})
// 502(AIの返答を検証できない)のときだけ付ける、固定の理由の説明。応答のreasonがこの9つのときだけ使う（json_text_afterは読み捨てにより、json_text_beforeは前の3コードに分けたため廃止）
const PARSE_REASONS = Object.freeze({
  empty: '（理由: AIの返答が空でした）',
  code_fence: '（理由: AIの返答がコードブロックで囲まれていました）',
  json_no_object: '（理由: AIの返答に、JSONがありませんでした）',
  json_prefix_brace: '（理由: AIの返答の前の文字に `{` があり、JSONとして取り出せませんでした）',
  json_prefix_truncated: '（理由: AIの返答の前に文字があり、JSONが途中で終わっていました）',
  json_truncated: '（理由: AIの返答が途中で終わっていました）',
  json_syntax: '（理由: AIの返答のJSONに、文法の誤りがありました）',
  json_not_object: '（理由: 返答の形が違いました）',
  reply_missing: '（理由: 返答に本文がありませんでした）',
})
function consultErrorText(e) {
  const status = e.response?.status
  const base = CONSULT_ERRORS[status] || 'AIへ送信できませんでした。'
  const reason = e.response?.data?.reason
  return status === 502 && typeof reason === 'string' && Object.hasOwn(PARSE_REASONS, reason) ? base + PARSE_REASONS[reason] : base
}
const REUSE_ERRORS = Object.freeze({
  403: 'このテンプレートを再利用する権限がありません。',
  404: 'テンプレートが見つかりません。',
  409: 'このテンプレートは再利用できません（却下・置換済み、内容や検査・ビューの公開定義の不一致）。',
})
const usable = computed(() => props.canEdit && !props.plan && !props.blocked && props.providerAvailable)
const unusableReason = computed(() => !props.canEdit ? '「AI分析」の編集権限が必要です。' : !props.providerAvailable ? '選んだAIは、いま使えません。上のAIプロバイダ・モデルを確認してください（自動では切り替えません）。' : props.plan ? '分析案を作った後は使えません。目的を変える場合は「目的・期間を変更して作り直す」を押してください。' : '他の操作の完了後に使えます。')
const canSend = computed(() => usable.value && !busy.value && !!input.value.trim() && (!props.external || externalAck.value))
watch(() => [props.provider, props.model, props.external], () => { externalAck.value = false }, { flush: 'sync' }) // AIを選び直したら、社外へ送る了承を取り直す

onBeforeUnmount(() => { disposed = true; epoch++ })

async function send() {
  if (!canSend.value) return
  const text = input.value.trim(), current = epoch
  const history = [...messages.value, { role: 'user', content: text }]
  const external = props.external, chosen = [props.provider, props.model, props.external].join('|')
  busy.value = 'send'; error.value = ''
  try {
    // やり取りはサーバーに保存しない。毎回、全体を送る
    const body = { messages: history.map(({ role, content }) => ({ role, content })), provider: props.provider }  // 表示用の項目(sent)は送らない
    if (props.model) body.model = props.model
    if (external) body.external_confirmed = true
    const response = await api.aiAnalysis.consult(body)
    if (disposed || current !== epoch) return
    // 送信中にAIを選び直したときは、前のAIの返事を使わない(入力欄は残す。了承は取り直し)
    if ([props.provider, props.model, props.external].join('|') !== chosen) { error.value = 'AIを切り替えたため、前のAIの返事は使いません。もう一度送ってください。'; return }
    const data = response.data || {}
    // 社外へ送った内容(置換後)を、送った発言の下に表示する
    const shown = history.map((item, index) => index === history.length - 1 && data.sent_text ? { ...item, sent: String(data.sent_text) } : item)
    messages.value = [...shown, { role: 'assistant', content: String(data.reply ?? '') }]
    draft.value = data.draft || null
    templates.value = Array.isArray(data.templates) ? data.templates : []
    input.value = ''
  } catch (e) {
    // 失敗したときは、送った発言を履歴へ入れず、入力欄に残す(そのまま再送できる)
    if (!disposed && current === epoch) error.value = consultErrorText(e)
  } finally { if (!disposed && current === epoch) busy.value = '' }
}
function reset() {
  if (busy.value) return
  messages.value = []; draft.value = null; templates.value = []; error.value = ''; input.value = ''
}
function apply() {
  const d = draft.value
  if (!usable.value || busy.value || !d || !(d.purpose || (d.date_from && d.date_to))) return
  const overwrite = (d.purpose && props.purpose.trim()) || (d.date_from && (props.dateFrom || props.dateTo))
  if (overwrite && !window.confirm('目的欄・期間欄の内容を、AIの文案で上書きします。よろしいですか？')) return
  emit('apply', { purpose: d.purpose || null, date_from: d.date_from && d.date_to ? d.date_from : null, date_to: d.date_from && d.date_to ? d.date_to : null })
}
// テンプレートを参考に分析する(2026-10-09、BOSS承認の範囲): 推薦された承認済みテンプレートの識別だけを、分析の画面へ渡す。AIも、APIも、ここでは呼ばない。
// 目的・期間の入力と、社外送信前の確認(参考の全文を含む)は、分析の画面で行う。相談のAIへ、参考を渡すことは、しない(未承認)
function selectReference(item) {
  if (!props.canEdit || props.blocked || busy.value || !item || !Number.isInteger(item.id)) return
  emit('reference-selected', { id: item.id, version: item.version, name: item.name, status: 'approved' })  // 推薦されるのは、承認済みのテンプレートだけ
}
async function useTemplate(item) {
  if (!usable.value || busy.value) return
  const current = epoch
  busy.value = 'reuse'; error.value = ''
  try {
    const response = await api.aiAnalysis.createTemplatePlan(item.id)
    if (!disposed && current === epoch) emit('plan-created', response.data)
  } catch (e) {
    if (!disposed && current === epoch) error.value = REUSE_ERRORS[e.response?.status] || '分析案を作成できませんでした。'
  } finally { if (!disposed && current === epoch) busy.value = '' }
}
</script>

<style scoped>
.consult { margin: 4px 0; border: 1px solid #c9d8d4; border-radius: 6px; background: #f6faf9; }
.consult-head { display: flex; gap: 8px; align-items: baseline; width: 100%; padding: 4px 8px; border: 0; background: transparent; text-align: left; cursor: pointer; flex-wrap: wrap; }
.consult-head em { font-style: normal; color: #4b6b64; font-size: 12px; }
.consult-head small { color: #566; }
.consult-body { padding: 0 8px 6px; }
.consult-body p { margin: 2px 0; }
.note { font-size: 12px; color: #566; }
.warning { color: #7a4b00; background: #fff6e0; padding: 2px 6px; border-radius: 4px; }
.ack { display: block; margin: 2px 0; color: #b00020; font-weight: bold; } /* 社外へ送ることの了承は、見落とさないよう赤字 */
.sent { display: block; color: #566; font-size: 12px; }
.error { color: #b00020; }
.log { list-style: none; margin: 4px 0; padding: 0; max-height: 220px; overflow-y: auto; }
.log li { margin: 2px 0; padding: 2px 6px; border-radius: 4px; white-space: pre-wrap; overflow-wrap: anywhere; }
.log li.user { background: #e3f1ee; }
.log li.assistant { background: #fff; border: 1px solid #dfe8e5; }
.send { display: flex; gap: 6px; align-items: flex-start; flex-wrap: wrap; }
.send textarea { flex: 1 1 260px; min-width: 0; }
.draft, .recommend { margin: 4px 0; padding: 4px 8px; border: 1px solid #bcd; border-radius: 4px; background: #fff; }
.draft p, .recommend p { white-space: pre-wrap; overflow-wrap: anywhere; }
</style>
