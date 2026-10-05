<template>
  <section class="consult" aria-label="AIと目的を整える">
    <button type="button" class="consult-head" :aria-expanded="open" aria-controls="consult-body" @click="open = !open">
      <strong>AIと目的を整える</strong><em>{{ open ? '畳む' : '開く' }}</em>
      <small v-if="!open">目的を書きにくいときに、AIと相談できます（ローカルAIだけ。社外へ送りません）</small>
    </button>
    <div v-show="open" id="consult-body" class="consult-body">
      <p class="note">やり取りはローカルAI（Qwen）で行い、社外へ送りません。やり取りは保存されません（画面を閉じる・分析案を作ると消えます）。AIは数値を知らず、助言と文案だけを出します。</p>
      <p v-if="!messages.length" class="note">例: 「先月の出荷を製品別に比べたい」のように、分かる範囲で書いてください。AIが、期間や対象を質問します。</p>
      <ul v-if="messages.length" class="log">
        <li v-for="(item, index) in messages" :key="index" :class="item.role"><b>{{ item.role === 'user' ? 'あなた' : 'AI' }}:</b> {{ item.content }}</li>
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
        <button type="button" :disabled="!usable || !!busy" @click="apply">目的欄・期間欄に取り込む</button>
      </section>
      <section v-if="templates.length" class="recommend">
        <p><b>近い承認済みテンプレート（{{ templates.length }}件）</b></p>
        <p v-for="item in templates" :key="item.id">テンプレート{{ item.id }}（版{{ item.version }}） / {{ item.name }} / カテゴリ: {{ item.category_label }} / 目的: {{ item.purpose }} / 期間: {{ item.date_from }} ～ {{ item.date_to }}
          <button type="button" :disabled="!usable || !!busy" @click="useTemplate(item)">このテンプレートで分析案を作る</button></p>
      </section>
      <p v-if="!usable" class="note">{{ unusableReason }}</p>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import api from '../../api/client'

const props = defineProps({ plan: { type: Object, default: null }, canEdit: Boolean, blocked: Boolean, purpose: { type: String, default: '' }, dateFrom: { type: String, default: '' }, dateTo: { type: String, default: '' } })
const emit = defineEmits(['apply', 'plan-created'])
const open = ref(false), input = ref(''), busy = ref(''), error = ref('')
const messages = ref([]), draft = ref(null), templates = ref([])
let disposed = false, epoch = 0
// 画面で表示する失敗は固定文だけ。APIの本文は表示しない。
const CONSULT_ERRORS = Object.freeze({
  400: '送る内容が正しくありません。',
  403: 'AIと相談する権限がありません（「AI分析」の編集権限が必要です）。',
  502: 'AIの返答を検証できませんでした。もう一度送ってください。',
  503: 'ローカルAIを使えません。しばらくしてから、もう一度送ってください。',
})
const REUSE_ERRORS = Object.freeze({
  403: 'このテンプレートを再利用する権限がありません。',
  404: 'テンプレートが見つかりません。',
  409: 'このテンプレートは再利用できません（却下・置換済み、内容や検査・ビューの公開定義の不一致）。',
})
const usable = computed(() => props.canEdit && !props.plan && !props.blocked)
const unusableReason = computed(() => !props.canEdit ? '「AI分析」の編集権限が必要です。' : props.plan ? '分析案を作った後は使えません。目的を変える場合は「目的・期間を変更して作り直す」を押してください。' : '他の操作の完了後に使えます。')
const canSend = computed(() => usable.value && !busy.value && !!input.value.trim())

onBeforeUnmount(() => { disposed = true; epoch++ })

async function send() {
  if (!canSend.value) return
  const text = input.value.trim(), current = epoch
  const history = [...messages.value, { role: 'user', content: text }]
  busy.value = 'send'; error.value = ''
  try {
    // やり取りはサーバーに保存しない。毎回、全体を送る
    const response = await api.aiAnalysis.consult({ messages: history })
    if (disposed || current !== epoch) return
    const data = response.data || {}
    messages.value = [...history, { role: 'assistant', content: String(data.reply ?? '') }]
    draft.value = data.draft || null
    templates.value = Array.isArray(data.templates) ? data.templates : []
    input.value = ''
  } catch (e) {
    // 失敗したときは、送った発言を履歴へ入れず、入力欄に残す(そのまま再送できる)
    if (!disposed && current === epoch) error.value = CONSULT_ERRORS[e.response?.status] || 'AIへ送信できませんでした。'
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
