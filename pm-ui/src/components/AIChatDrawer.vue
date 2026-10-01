<template>
  <aside v-if="aiDrawerOpen" class="ai-drawer" aria-label="社内AIチャット">
    <header class="drawer-header">
      <div>
        <strong>✦ 社内AI</strong>
        <small>起点: {{ sourceLabel }}</small>
      </div>
      <div class="drawer-actions">
        <select v-model="provider" :disabled="loading" aria-label="AIプロバイダ" :title="providerLabel">
          <option v-for="item in availableProviders" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
        <select v-if="currentProviderModels.length > 1" v-model="model" :disabled="loading" aria-label="モデル" class="model-select" :title="modelLabel">
          <option v-for="item in currentProviderModels" :key="item.id" :value="item.id">{{ item.label }}</option>
        </select>
        <button type="button" title="会話履歴" :class="{ active: historyOpen }" @click="toggleHistory">🕘</button>
        <button type="button" title="新しい会話" :disabled="loading" @click="clearChat">＋</button>
        <button type="button" title="閉じる" @click="closeAIDrawer">×</button>
      </div>
    </header>

    <div v-if="historyOpen" class="drawer-history">
      <div v-if="!historyList.length" class="drawer-history-empty">まだ会話履歴がありません。</div>
      <div v-for="item in historyList" :key="item.id" class="drawer-history-item" :class="{ active: item.id === conversationId }" @click="openConversation(item.id)">
        <div>
          <strong>{{ item.title || '無題の会話' }}</strong>
          <small>{{ formatRelativeTime(item.updated_at) }}</small>
        </div>
        <button type="button" title="削除" @click.stop="deleteConversation(item.id)">×</button>
      </div>
    </div>

    <div ref="conversation" class="drawer-conversation">
      <div v-if="screenInfo && !screenInfo.supported" class="drawer-unsupported">
        ⚠ {{ screenInfo.label }}画面の業務データには、まだ対応していません。{{ screenInfo.common_coverage }}についての質問には回答できます。
      </div>
      <div v-if="messages.length === 0" class="drawer-welcome">
        <strong>{{ sourceLabel }}画面のAI支援</strong>
        <p>現在の画面を残したまま質問できます。</p>
        <p v-if="screenInfo?.supported && screenInfo.coverage">対応範囲: {{ screenInfo.coverage }}</p>
      </div>
      <article v-for="(message, index) in messages" :key="index" class="drawer-message" :class="message.role">
        <small>{{ message.role === 'user' ? 'あなた' : '社内AI' }}</small>
        <p>{{ message.content }}</p>
        <button v-if="message.role === 'assistant'" type="button" class="drawer-mini-btn" @click="copyMessage(index, message.content)">{{ copiedIndex === index ? '✓ コピーしました' : '⧉ コピー' }}</button>
        <button v-if="message.excel_export && hasMarkdownTable(message.content)" type="button" class="excel-download" @click="downloadMarkdownTablesAsExcel(message.content)">⇩ 回答の表をExcelでダウンロード (.xlsx)</button>
        <em v-if="message.attachment">▣ 添付資料: {{ message.attachment }}</em>
        <em v-if="message.source">▤ {{ message.source }}<span v-if="message.period"> · {{ message.period.start_date }}<template v-if="message.period.end_date">〜{{ message.period.end_date }}</template><template v-else>以降</template></span></em>
      </article>
      <div v-if="loading" class="drawer-loading">✦ AIが確認しています…</div>
      <div v-if="voice.error.value" class="drawer-error">⚠ {{ voice.error.value }}</div>
      <div v-if="error" class="drawer-error">⚠ {{ error }}<button v-if="canRetry" type="button" class="drawer-mini-btn retry" @click="retry">↻ 再送信</button></div>
    </div>

    <form class="drawer-composer" @submit.prevent="send">
      <input ref="attachmentInput" class="attachment-input" type="file" accept=".pdf,.xlsx,.xls,.csv,.tsv,.png,.jpg,.jpeg,.webp,.bmp" @change="selectAttachment" />
      <div v-if="attachedFile || selectedDocument" class="attachment-state">
        <span>▣ {{ attachedFile?.name || selectedDocument?.name }}</span>
        <button type="button" title="添付資料を外す" :disabled="loading" @click="clearAttachment">×</button>
      </div>
      <div v-if="historyTruncated" class="drawer-note">会話が長いため、直近{{ HISTORY_LIMIT - 1 }}件より古い発言は、AIへ渡していません。</div>
      <textarea v-model="draft" :disabled="loading" rows="2" placeholder="この画面について質問…" @keydown.enter.exact.prevent="send" />
      <button type="button" class="attachment-button" title="資料を添付" :disabled="loading" @click="attachmentInput?.click()">＋</button>
      <button v-if="voice.supported" type="button" class="mic" :class="{ recording: voice.recording.value }" :disabled="loading || voice.transcribing.value" :title="voiceTitle" @click="voice.toggle">{{ voiceLabel }}</button>
      <button v-if="loading" type="button" class="stop" title="応答を中止" @click="stopAsk">■</button>
      <button v-else type="submit" :disabled="!draft.trim() || overLimit">↑</button>
      <div v-if="draft.length" class="drawer-count" :class="{ over: overLimit }">{{ draft.length }}/{{ QUESTION_MAX }}文字<template v-if="overLimit">（{{ QUESTION_MAX }}文字まで）</template></div>
    </form>
  </aside>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { authState } from '@/auth'
import api from '@/api/client'
import { hasPermission } from '@/router'
import { downloadMarkdownTablesAsExcel, hasMarkdownTable } from '@/utils/aiMarkdownTableExcel'
import { useVoiceInput } from '@/composables/useVoiceInput'
import { aiDrawerOpen, aiDrawerSourcePath, closeAIDrawer } from '@/composables/aiDrawer'

const provider = ref('openrouter')
const model = ref('')
const messages = ref([])
const draft = ref('')
const loading = ref(false)
const error = ref('')
const conversation = ref(null)
const QUESTION_MAX = 1200
const HISTORY_LIMIT = 15
const failedRequest = ref(null)
const copiedIndex = ref(-1)
let abortController = null
const attachmentInput = ref(null)
const attachedFile = ref(null)
const selectedDocument = ref(null)
const conversationId = ref(null)
const historyList = ref([])
const historyOpen = ref(false)
const screenInfo = ref(null)
const availableProviders = ref([
  { value: 'openrouter', label: 'OpenRouter' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'qwen', label: 'Qwen' },
])
const canViewPersonalOvertime = computed(() => hasPermission(authState.user, 'overtime.personal_summary', 'view'))
const currentProviderModels = computed(() => availableProviders.value.find((item) => item.value === provider.value)?.item?.models || [])
watch(currentProviderModels, (models) => {
  if (!models.some((item) => item.id === model.value)) model.value = models[0]?.id || ''
}, { immediate: true })
const providerLabel = computed(() => availableProviders.value.find((item) => item.value === provider.value)?.label || '')
const modelLabel = computed(() => currentProviderModels.value.find((item) => item.id === model.value)?.label || '')
const sourceLabel = computed(() => {
  const source = aiDrawerSourcePath.value
  if (source.startsWith('/orders/')) return '受注'
  if (source.startsWith('/production/')) return '生産'
  if (source.startsWith('/quality/')) return '品質'
  if (source.startsWith('/overtime/')) return '勤務'
  if (source.startsWith('/purchase/')) return '仕入'
  if (source.startsWith('/shipping/')) return '出荷'
  if (source.startsWith('/inventory/')) return '在庫'
  return '本社横断'
})

const scrollToBottom = async () => {
  await nextTick()
  if (conversation.value) conversation.value.scrollTop = conversation.value.scrollHeight
}

const clearChat = () => {
  if (loading.value) return
  messages.value = []
  draft.value = ''
  error.value = ''
  conversationId.value = null
  clearAttachment()
}

const formatRelativeTime = (value) => {
  if (!value) return ''
  const minutes = Math.floor((Date.now() - new Date(value).getTime()) / 60000)
  if (minutes < 1) return 'たった今'
  if (minutes < 60) return `${minutes}分前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}時間前`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}日前`
  return new Date(value).toLocaleDateString('ja-JP')
}

const loadHistory = async () => {
  try {
    const { data } = await api.aiConversations.list()
    historyList.value = data.results || data
  } catch {
    historyList.value = []
  }
}

const toggleHistory = () => {
  historyOpen.value = !historyOpen.value
  if (historyOpen.value) void loadHistory()
}

const saveConversation = async () => {
  try {
    const payload = { screen_context: aiDrawerSourcePath.value, provider: provider.value, messages: messages.value }
    if (conversationId.value) {
      await api.aiConversations.update(conversationId.value, payload)
    } else {
      const { data } = await api.aiConversations.create(payload)
      conversationId.value = data.id
    }
    if (historyOpen.value) await loadHistory()
  } catch {
    // 会話の保存に失敗しても、その場のチャット表示は継続する。
  }
}

const openConversation = async (id) => {
  if (loading.value) return
  try {
    const { data } = await api.aiConversations.get(id)
    messages.value = data.messages || []
    conversationId.value = data.id
    if (data.provider && availableProviders.value.some((item) => item.value === data.provider)) provider.value = data.provider
    error.value = ''
    clearAttachment()
    historyOpen.value = false
    await scrollToBottom()
  } catch {
    error.value = '会話を読み込めませんでした。'
  }
}

const deleteConversation = async (id) => {
  if (!window.confirm('この会話を削除しますか？')) return
  try {
    await api.aiConversations.delete(id)
    historyList.value = historyList.value.filter((item) => item.id !== id)
    if (conversationId.value === id) clearChat()
  } catch {
    error.value = '会話を削除できませんでした。'
  }
}

const selectAttachment = (event) => {
  const file = event.target.files?.[0] || null
  if (!file) return
  if (file.size > 15 * 1024 * 1024) {
    error.value = '添付できる資料は15MBまでです。'
    event.target.value = ''
    return
  }
  attachedFile.value = file
  selectedDocument.value = null
  error.value = ''
}

const clearAttachment = () => {
  attachedFile.value = null
  selectedDocument.value = null
  if (attachmentInput.value) attachmentInput.value.value = ''
}

const uploadAttachment = async () => {
  if (!attachedFile.value) return selectedDocument.value
  const file = attachedFile.value
  const form = new FormData()
  form.append('category', 'manual')
  form.append('name', file.name.replace(/\.[^.]+$/, '') || file.name)
  form.append('file', file)
  const { data } = await api.aiSettings.createKnowledgeDocument(form)
  selectedDocument.value = { id: data.id, name: data.name }
  attachedFile.value = null
  if (attachmentInput.value) attachmentInput.value.value = ''
  return selectedDocument.value
}

const loadProviderSettings = async () => {
  try {
    const { data } = await api.aiChat.status({ screen_context: aiDrawerSourcePath.value })
    screenInfo.value = data.screen || null
    const providerLabels = { deepseek: 'DeepSeek', qwen: 'Qwen', openrouter: 'OpenRouter' }
    const nextProviders = Object.entries(data.providers || {})
      .filter(([, item]) => item.is_enabled !== false)
      .map(([value, item]) => ({ value, label: providerLabels[value] || value, item }))
    if (nextProviders.length) {
      availableProviders.value = nextProviders
      if (!nextProviders.some((item) => item.value === provider.value)) provider.value = nextProviders[0].value
    }
  } catch { /* チャット送信時に接続エラーを表示する */ }
}

const overLimit = computed(() => draft.value.length > QUESTION_MAX)
// 音声入力: 文字にした結果を入力欄の末尾へ足す(自動送信はしない)
const voice = useVoiceInput((text) => { draft.value = draft.value ? `${draft.value} ${text}` : text })
const voiceLabel = computed(() => voice.recording.value ? `■ ${voice.seconds.value}秒` : voice.transcribing.value ? `… ${voice.seconds.value}秒` : '🎤')
const voiceTitle = computed(() => voice.recording.value ? '録音を終了して文字にする' : voice.transcribing.value ? '文字にしています' : `音声入力(最大${voice.MAX_SECONDS}秒)`)
// 次の質問では、直近HISTORY_LIMIT-1件までしかAIへ渡さない
const historyTruncated = computed(() => messages.value.length > HISTORY_LIMIT - 1)
const canRetry = computed(() => !!failedRequest.value && !!error.value && messages.value[messages.value.length - 1]?.role === 'user')

const send = async () => {
  const question = draft.value.trim()
  if (!question || loading.value || overLimit.value) return
  error.value = ''
  failedRequest.value = null
  loading.value = true
  let document = null
  try {
    document = await uploadAttachment()
    draft.value = ''
  } catch (requestError) {
    error.value = requestError.response?.data?.detail || '社内AIから応答を取得できませんでした。'
    loading.value = false
    return
  }
  await sendQuestion(question, document)
}

const sendQuestion = async (question, document) => {
  error.value = ''
  failedRequest.value = null
  loading.value = true
  abortController = new AbortController()
  try {
    messages.value.push({ role: 'user', content: question, attachment: document?.name || '' })
    await scrollToBottom()
    const history = messages.value.slice(-HISTORY_LIMIT, -1).map(({ role, content, period }) => ({ role, content, period }))
    const { data } = await api.aiChat.chat({
      message: question,
      history,
      provider: provider.value,
      model: model.value || undefined,
      allow_personal_overtime: canViewPersonalOvertime.value,
      screen_context: aiDrawerSourcePath.value,
      knowledge_document_ids: document ? [document.id] : [],
    }, { signal: abortController.signal })
    messages.value.push({
      role: 'assistant', content: data.answer, source: data.source, period: data.period, excel_export: data.excel_export === true,
    })
    await saveConversation()
  } catch (requestError) {
    failedRequest.value = { question, document }
    error.value = requestError.code === 'ERR_CANCELED'
      ? '応答を中止しました。'
      : (requestError.response?.data?.detail || '社内AIから応答を取得できませんでした。')
  } finally {
    abortController = null
    loading.value = false
    await scrollToBottom()
  }
}

// 画面の待ちを止める。サーバー側の処理は止まらない(応答は捨てる)
const stopAsk = () => { abortController?.abort() }

const retry = () => {
  const request = failedRequest.value
  if (!request || loading.value) return
  if (messages.value[messages.value.length - 1]?.role === 'user') messages.value.pop()
  sendQuestion(request.question, request.document)
}

const copyMessage = async (index, text) => {
  try {
    await navigator.clipboard.writeText(String(text || ''))
    copiedIndex.value = index
    setTimeout(() => { if (copiedIndex.value === index) copiedIndex.value = -1 }, 1500)
  } catch {
    error.value = 'コピーできませんでした。ブラウザの権限を確認してください。'
    failedRequest.value = null
  }
}

// DeepSeekは有料のため、選択時に確認する。同じ画面の間は1回承認すれば再確認しない。
let deepseekConfirmed = false
watch(provider, (next, prev) => {
  if (next !== 'deepseek' || deepseekConfirmed) return
  if (window.confirm('DeepSeekは有料です。使いますか？')) {
    deepseekConfirmed = true
  } else {
    provider.value = prev
  }
})

watch(aiDrawerSourcePath, () => {
  clearChat()
  void loadProviderSettings()
})
onMounted(loadProviderSettings)
</script>

<style scoped>
.ai-drawer{position:fixed;top:74px;right:0;bottom:0;z-index:900;width:min(430px,100vw);display:flex;flex-direction:column;background:#fff;border-left:1px solid #cfe0dc;box-shadow:-8px 0 24px rgba(24,62,57,.16);color:#27454a}.drawer-header{min-height:58px;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px 10px;padding:9px 12px;border-bottom:1px solid #e2ece9;background:#f5fbf9}.drawer-header strong,.drawer-header small{display:block}.drawer-header strong{font-size:14px;color:#087b6e}.drawer-header small{margin-top:3px;font-size:10px;color:#71878b}.drawer-actions{display:flex;flex-wrap:wrap;align-items:center;gap:5px}.drawer-actions select,.drawer-actions button{height:29px;border:1px solid #d1e2dd;border-radius:6px;background:#fff;color:#466169;font-size:11px}.drawer-actions select{max-width:104px;padding:0 5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.drawer-actions select.model-select{max-width:150px}.drawer-actions button{width:29px;cursor:pointer;flex:0 0 29px}.drawer-actions button:disabled{opacity:.5;cursor:default}.drawer-actions button.active{background:#e7f4f0;border-color:#9ccfc2}.drawer-history{flex:none;max-height:45%;overflow:auto;padding:6px;border-bottom:1px solid #e2ece9;background:#fff}.drawer-history-empty{padding:12px;font-size:11px;color:#82969a;text-align:center}.drawer-history-item{display:flex;align-items:center;gap:6px;padding:7px 8px;border-radius:6px;cursor:pointer}.drawer-history-item:hover{background:#f5fbf9}.drawer-history-item.active{background:#e7f4f0}.drawer-history-item>div{min-width:0;flex:1;display:grid;gap:2px}.drawer-history-item strong{font-size:11px;color:#27454a;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.drawer-history-item small{font-size:9px;color:#82969a}.drawer-history-item button{flex:none;width:20px;height:20px;border:0;border-radius:5px;background:transparent;color:#a9b8bb;font-size:13px;cursor:pointer}.drawer-history-item button:hover{background:#fdeceb;color:#c0564a}.drawer-conversation{flex:1;overflow:auto;padding:14px 13px;background:#fbfdfc}.drawer-welcome{margin:18px 2px;color:#547177}.drawer-welcome strong{font-size:13px}.drawer-welcome p{font-size:11px;line-height:1.7}.drawer-unsupported{margin:0 0 12px;padding:8px 10px;border:1px solid #f1dcc8;border-radius:7px;background:#fff7ef;color:#9a6941;font-size:11px;line-height:1.6}.drawer-message{display:grid;gap:4px;margin:0 0 14px;max-width:92%}.drawer-message.user{margin-left:auto;justify-items:end}.drawer-message small{font-size:9px;color:#82969a}.drawer-message p{white-space:pre-wrap;line-height:1.65;margin:0;padding:8px 10px;border-radius:9px;background:#fff;border:1px solid #e3ece9;font-size:12px}.drawer-message.user p{background:#e7f4f0;border-color:#d6ebe5}.excel-download{justify-self:start;padding:5px 9px;border:1px solid #d7ebe5;border-radius:6px;background:#f4faf8;color:#247d6d;font-size:10px;cursor:pointer}.excel-download:hover{background:#eaf6f2}.drawer-composer button.mic{flex:0 0 auto;min-width:34px;width:auto;padding:0 8px;background:#fff;color:#466169;border:1px solid #cfdfdb;font-size:14px}.drawer-composer button.mic:disabled{opacity:.5}.drawer-composer button.mic.recording{background:#c0564a;border-color:#c0564a;color:#fff;font-size:11px}.drawer-mini-btn{justify-self:start;margin:2px 0 0;padding:2px 7px;border:1px solid #d7e5e1;border-radius:5px;background:#fff;color:#5d7a80;font-size:9px;cursor:pointer}.drawer-mini-btn:hover{background:#f5fbf9}.drawer-mini-btn.retry{display:block;margin-top:6px;color:#247d6d}.drawer-composer button.stop{background:#c0564a;font-size:13px}.drawer-note{width:100%;padding:4px 7px;border-radius:5px;background:#fff7ef;border:1px solid #f1dcc8;color:#9a6941;font-size:10px}.drawer-count{width:100%;text-align:right;font-size:9px;color:#82969a}.drawer-count.over{color:#c0564a}.drawer-message em{font-style:normal;font-size:9px;color:#789196}.drawer-loading,.drawer-error{font-size:11px;padding:9px;border-radius:7px}.drawer-loading{color:#438b7c;background:#edf8f5}.drawer-error{color:#a06d43;background:#fff7ef;border:1px solid #f1dcc8}.drawer-composer{display:flex;flex-wrap:wrap;gap:7px;padding:10px;border-top:1px solid #e2ece9;background:#fff}.drawer-composer textarea{flex:1;min-width:0;resize:none;border:1px solid #cfdfdb;border-radius:8px;padding:7px;font:inherit;font-size:12px;outline:none}.drawer-composer textarea:focus{border-color:#56aa99}.drawer-composer button{width:34px;border:0;border-radius:8px;background:#087b6e;color:white;font-size:18px}.drawer-composer button:disabled{background:#cbdad7}.attachment-input{display:none}.attachment-button{flex:0 0 34px}.attachment-state{display:flex;align-items:center;justify-content:space-between;gap:7px;width:100%;padding:4px 7px;border-radius:5px;background:#edf8f5;color:#28796c;font-size:10px}.attachment-state span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.attachment-state button{width:20px;height:20px;font-size:13px;background:transparent;color:#28796c}@media(max-width:768px){.ai-drawer{top:0;width:100%;z-index:1100}}
</style>
