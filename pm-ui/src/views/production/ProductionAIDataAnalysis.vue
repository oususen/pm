<template>
  <main class="workspace">
    <header class="topbar">
      <div class="brand-mark">✦</div>
      <div class="brand-title"><strong>社内AI</strong><span>社内データアシスタント</span></div>
      <div class="local-badge" :class="{ offline: !providerReady() }"><i></i> {{ providerReady() ? `${providerLabel()} · ${providerModel()}` : `${providerLabel()} · 要確認` }}</div>
      <label class="provider-select">AIプロバイダ<select v-model="provider" :disabled="loading"><option value="deepseek">DeepSeek API</option><option value="qwen">ローカルQwen</option><option value="openrouter">OpenRouter（評価用）</option></select></label>
      <label v-if="isExternalProvider" class="provider-select">モデル<select v-model="externalModel[provider]" :disabled="loading"><option v-for="item in externalModels()" :key="item.id" :value="item.id">{{ item.label }}</option></select></label>
      <div class="history-wrap">
        <button class="history-toggle" @click="toggleHistory">🕘 <span>履歴</span></button>
        <div v-if="historyOpen" class="history-panel">
          <div v-if="!historyList.length" class="history-empty">まだ会話履歴がありません。</div>
          <div v-for="item in historyList" :key="item.id" class="history-item" :class="{ active: item.id === conversationId }" @click="openConversation(item.id)">
            <div class="history-item-main">
              <strong>{{ item.title || '無題の会話' }}</strong>
              <small>{{ formatRelativeTime(item.updated_at) }}</small>
            </div>
            <button type="button" class="history-delete" title="削除" @click.stop="deleteConversation(item.id)">×</button>
          </div>
        </div>
      </div>
      <button class="new-chat" @click="clearChat">＋ <span>新しいチャット</span></button>
    </header>

    <div class="layout">
      <section class="chat-area">
        <div v-if="screenInfo && !screenInfo.supported" class="unsupported-note">⚠ {{ screenInfo.label }}画面の業務データには、まだ対応していません。{{ screenInfo.common_coverage }}についての質問には回答できます。</div>
        <div ref="scrollArea" class="conversation" :class="{ welcome: messages.length === 0 }">
          <div v-if="messages.length === 0" class="welcome-card">
            <div class="welcome-icon">✦</div>
            <div class="welcome-eyebrow">YOUR PRIVATE FACTORY ASSISTANT</div>
            <h1>社内データに、<span>聞いてみる。</span></h1>
            <p>このアプリの生産記録を調べ、数字の根拠と一緒に回答します。<br>チャート表示や報告書の下書きも頼めます。</p>
            <p v-if="screenInfo?.supported && screenInfo.coverage" class="coverage-note">対応範囲: {{ screenInfo.coverage }}</p>
            <div class="suggestions">
              <button v-for="item in suggestions" :key="item.title" class="suggestion" @click="ask(item.prompt)">
                <span class="suggestion-icon" :class="item.color">{{ item.icon }}</span>
                <span><strong>{{ item.title }}</strong><small>{{ item.subtitle }}</small></span>
                <b>↗</b>
              </button>
            </div>
          </div>

          <div v-else class="message-list">
            <article v-for="(message, index) in messages" :key="index" class="message" :class="message.role">
              <div v-if="message.role === 'assistant'" class="avatar">✦</div>
              <div class="message-content">
                <div class="sender">{{ message.role === 'user' ? 'あなた' : '社内AI' }}<span v-if="message.role === 'assistant' && message.provider">{{ providerLabel(message.provider) }}<template v-if="message.model"> · {{ modelLabel(message.model) }}</template></span></div>
                <div class="bubble" :class="{ 'user-bubble': message.role === 'user' }">{{ message.content }}</div>
                <button v-if="message.role === 'assistant'" type="button" class="copy-btn" @click="copyMessage(index, message.content)">{{ copiedIndex === index ? '✓ コピーしました' : '⧉ コピー' }}</button>
                <div v-if="message.analysis" class="reasoning-note"><span>✦ Qwenの確認メモ</span><p>{{ message.analysis }}</p></div>
                <div v-if="message.role === 'assistant'" class="evidence-line" :class="evidenceKind(message)"><span>{{ evidenceIcon(message) }}</span> {{ evidenceLabel(message) }}</div>
                <div v-if="message.source" class="source-line"><span>▤</span> 根拠データ: {{ message.source }}<span v-if="message.period" class="source-period">{{ message.period.start_date }} — {{ message.period.end_date }}</span></div>
                <section v-if="message.cross_screen_request" class="cross-screen-request">
                  <strong>横断参照: {{ message.cross_screen_request.source_label }}・{{ message.cross_screen_request.target_label }}</strong>
                  <small>{{ message.cross_screen_request.purpose }}</small>
                  <div><button type="button" @click="approveCrossScreen(message)">今回だけ許可</button><button type="button" class="decline" @click="declineCrossScreen(message)">許可しない</button></div>
                </section>
                <section v-if="message.chart && message.chart.values.length" class="chart-card">
                  <div class="chart-heading"><div><small>DATA VISUALIZATION</small><strong>{{ message.chart.title }}</strong></div><span class="chart-kind">▥ 棒グラフ</span></div>
                  <div class="bar-chart">
                    <div v-for="(value, i) in message.chart.values" :key="i" class="chart-column" :title="`${message.chart.labels[i]}: ${number(value)} ${message.chart.series_label}`">
                      <span class="bar-value">{{ number(value) }}</span><div class="bar-track"><i :style="{ height: `${barHeight(value, message.chart.values)}%` }"></i></div><small>{{ shortLabel(message.chart.labels[i]) }}</small>
                    </div>
                  </div>
                  <div class="chart-axis">単位: {{ message.chart.series_label }}</div>
                </section>
                <button v-if="message.excel_export && hasMarkdownTable(message.content)" class="download" @click="downloadMarkdownTablesAsExcel(message.content)">⇩　回答の表をExcelでダウンロード <small>.xlsx</small></button>
                <button v-if="message.document" class="download" @click="downloadReport(message)">⇩　報告書の下書きをダウンロード <small>.md</small></button>
              </div>
              <div v-if="message.role === 'user'" class="user-avatar">YOU</div>
            </article>
            <article v-if="loading" class="message assistant"><div class="avatar pulse">✦</div><div class="message-content"><div class="sender">社内AI <span>{{ providerLabel() }}</span></div><div class="thinking"><i></i><i></i><i></i><small>{{ providerLabel() }}が回答を作成しています</small></div></div></article>
            <div v-if="voice.error.value" class="error-card">⚠ {{ voice.error.value }}</div>
            <div v-if="error" class="error-card">⚠ {{ error }}<small>案内に従って質問や接続状態を確認し、再度お試しください。</small><button v-if="canRetry" type="button" class="retry-btn" @click="retry">↻ 再送信</button></div>
          </div>
        </div>

        <div class="composer-wrap">
          <div class="composer">
            <textarea v-model="draft" rows="1" :disabled="loading" placeholder="社内データについて質問、または作成したい資料を入力…" @keydown.enter.exact.prevent="send"></textarea>
            <button v-if="voice.supported" class="mic-btn" :class="{ recording: voice.recording.value }" type="button" :disabled="loading || voice.transcribing.value" :title="voiceTitle" :aria-label="voiceTitle" @click="voice.toggle">{{ voiceLabel }}</button>
            <button v-if="loading" class="send stop" type="button" aria-label="応答を中止" title="応答を中止" @click="stopAsk">■</button>
            <button v-else class="send" :disabled="!draft.trim() || overLimit" aria-label="送信" @click="send">↑</button>
          </div>
          <div v-if="historyTruncated" class="history-note">会話が長いため、直近{{ HISTORY_LIMIT - 1 }}件より古い発言は、AIへ渡していません。古い内容が必要なときは、質問し直してください。</div>
          <div class="composer-foot"><span>↳ Enterで送信 · Shift + Enterで改行<template v-if="draft.length"> · <b :class="{ over: overLimit }">{{ draft.length }}/{{ QUESTION_MAX }}文字</b><template v-if="overLimit">（{{ QUESTION_MAX }}文字まで）</template></template></span><span><i></i> {{ isExternalProvider ? `質問・会話・必要な集計結果を${providerLabel()}へ送信` : '質問とデータはこのPC内で処理' }}</span></div>
        </div>
      </section>

      <aside class="side-panel">
        <div class="side-heading">このAIについて <span>ⓘ</span></div>
        <div class="local-card"><div class="local-symbol">✦</div><div><strong>{{ providerLabel() }}</strong><small>{{ providerModel() }}</small></div><div class="online" :class="{ offline: !providerReady() }"><i></i> {{ providerReady() ? '利用可能' : '要確認' }}</div></div>
        <p class="side-description">{{ isExternalProvider ? `質問・会話履歴・回答に必要なDB集計結果を${providerLabel()}へ送信します。` : '質問と回答はPC内のOllamaで処理し、外部AIへ送信しません。' }}</p>
        <div class="side-divider"></div>
        <div class="side-heading">参照できるデータ</div>
        <div class="source-item"><span class="db-icon">▤</span><div><strong>工程の生産実績</strong><small>日付・作業者・工程・数量</small></div></div>
        <div class="source-item"><span class="db-icon coral">▤</span><div><strong>確定仕損の記録</strong><small>品目・数量・登録理由</small></div></div>
        <div class="source-item"><span class="db-icon amber">▤</span><div><strong>工程中断の記録</strong><small>ブレーキ工程・中断理由</small></div></div>
        <div class="source-item"><span class="db-icon violet">▤</span><div><strong>残業申請</strong><small>承認段階別・グループ別時間</small></div></div>
        <div class="side-divider"></div>
        <div class="side-heading">できること</div>
        <ul class="capabilities"><li><span>✓</span>期間・工程・グループを指定して質問</li><li><span>✓</span>集計結果をチャートで表示</li><li><span>✓</span>幹部会向け報告書を下書き</li></ul>
        <div class="safety-note"><span>♧</span><p><strong>安全なデータ利用</strong><br>DBは読み取り専用で集計します。個人の評価・順位付けには使いません。作成した文書はこの画面から端末へダウンロードされ、サーバーには保存されません。</p></div>
        <section v-if="canManageKnowledge" class="knowledge-library">
          <div class="side-divider"></div>
          <div class="side-heading">RAG資料庫</div>
          <p>登録した資料は、以後の社内AIの検索対象になります。</p>
          <select v-model="knowledgeUpload.category" :disabled="knowledgeUploading">
            <option value="manual">マニュアル</option>
            <option value="procedure">手順書</option>
            <option value="pm_structure">PMアプリ構造</option>
            <option value="security">安全・運用規約</option>
          </select>
          <input v-model.trim="knowledgeUpload.name" :disabled="knowledgeUploading" placeholder="資料名" />
          <input ref="knowledgeFileInput" type="file" :disabled="knowledgeUploading" accept=".pdf,.xlsx,.xls,.csv,.tsv,.png,.jpg,.jpeg,.webp,.bmp" @change="selectKnowledgeFile" />
          <button type="button" :disabled="!knowledgeUpload.file || !knowledgeUpload.name || knowledgeUploading" @click="uploadKnowledge">{{ knowledgeUploading ? '登録中…' : '資料庫へ追加' }}</button>
          <small>PDF・Excel・CSV・画像を15MBまで登録できます。</small>
          <div v-if="knowledgeNotice" class="knowledge-notice">{{ knowledgeNotice }}</div>
          <div v-if="knowledgeError" class="knowledge-error">{{ knowledgeError }}</div>
        </section>
      </aside>
    </div>
  </main>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { authState } from '@/auth'
import api from '@/api/client'
import { hasPermission } from '@/router'
import { downloadMarkdownTablesAsExcel, hasMarkdownTable } from '@/utils/aiMarkdownTableExcel'
import { useVoiceInput } from '@/composables/useVoiceInput'

const provider = ref('openrouter')
const route = useRoute()
const providerStatus = ref({})
const EXTERNAL_PROVIDERS = ['deepseek', 'openrouter']
const externalModel = ref({ deepseek: 'deepseek-v4-pro', openrouter: 'qwen/qwen3.8-27b:free' })
const isExternalProvider = computed(() => EXTERNAL_PROVIDERS.includes(provider.value))
const suggestions = [
  { icon: '↗', color: 'teal', title: '生産数の推移', subtitle: '今月の日別生産数をチャートで', prompt: '今月の日別生産数をチャートで見せて' },
  { icon: '◎', color: 'coral', title: '仕損の傾向', subtitle: '仕損の多い理由を教えて', prompt: '今月の確定仕損を理由別に教えて、チャートで見せて' },
  { icon: 'Ⅱ', color: 'amber', title: '工程の中断', subtitle: '中断・強制終了の主な理由', prompt: '今月のブレーキ工程の中断理由を分析して' },
  { icon: '◷', color: 'violet', title: '残業時間を確認', subtitle: 'グループ別・月別の申請時間', prompt: '板金グループの2026年8月の残業時間合計は何時間ですか' },
  { icon: '▤', color: 'violet', title: '報告書を作成', subtitle: '幹部会向けの月次報告を下書き', prompt: '今月の生産・仕損・中断データで幹部会向けの報告書を作成して' },
]
const QUESTION_MAX = 1200
const HISTORY_LIMIT = 15
const messages = ref([])
const draft = ref('')
const loading = ref(false)
const error = ref('')
const failedQuestion = ref('')
const copiedIndex = ref(-1)
const knowledgeFileInput = ref(null)
const knowledgeUpload = ref({ category: 'manual', name: '', file: null })
const knowledgeUploading = ref(false)
const knowledgeNotice = ref('')
const knowledgeError = ref('')
let abortController = null
const overLimit = computed(() => draft.value.length > QUESTION_MAX)
// 音声入力: 文字にした結果を入力欄の末尾へ足す(自動送信はしない)
const voice = useVoiceInput((text) => { draft.value = draft.value ? `${draft.value} ${text}` : text })
const voiceLabel = computed(() => voice.recording.value ? `■ ${voice.seconds.value}秒` : voice.transcribing.value ? `… ${voice.seconds.value}秒` : '🎤')
const voiceTitle = computed(() => voice.recording.value ? '録音を終了して文字にする' : voice.transcribing.value ? '文字にしています' : `音声入力(最大${voice.MAX_SECONDS}秒)`)
// 次の質問では、直近HISTORY_LIMIT-1件までしかAIへ渡さない
const historyTruncated = computed(() => messages.value.length > HISTORY_LIMIT - 1)
const canRetry = computed(() => !!failedQuestion.value && !!error.value && messages.value[messages.value.length - 1]?.role === 'user')
const scrollArea = ref(null)
const conversationId = ref(null)
const historyList = ref([])
const historyOpen = ref(false)
const providerLabel = (value = provider.value) => ({ deepseek: 'DEEPSEEK API', qwen: 'LOCAL QWEN', openrouter: 'OPENROUTER', database: 'DB集計' }[value] || '社内AI')
const DEFAULT_EXTERNAL_MODELS = {
  deepseek: [
    { id: 'deepseek-v4-pro', label: 'DeepSeek V4 Pro（高精度）' },
    { id: 'deepseek-flash', label: 'DeepSeek Flash（高速）' },
  ],
  openrouter: [
    { id: 'qwen/qwen3.8-27b:free', label: 'Qwen3.8 27B（OpenRouter・無料枠）' },
    { id: 'google/gemma-4-26b-a4b-it:free', label: 'Gemma 4 26B A4B（OpenRouter・無料枠）' },
    { id: 'google/gemma-4-26b-a4b-it', label: 'Gemma 4 26B A4B（OpenRouter・有料/要クレジット）' },
  ],
}
const externalModels = () => providerStatus.value[provider.value]?.models || DEFAULT_EXTERNAL_MODELS[provider.value] || []
const modelLabel = (modelId) => {
  if (!modelId) return ''
  for (const key of Object.keys(providerStatus.value)) {
    const found = (providerStatus.value[key]?.models || []).find((item) => item.id === modelId)
    if (found) return found.label
  }
  for (const key of Object.keys(DEFAULT_EXTERNAL_MODELS)) {
    const found = DEFAULT_EXTERNAL_MODELS[key].find((item) => item.id === modelId)
    if (found) return found.label
  }
  return modelId
}
const providerModel = () => isExternalProvider.value ? externalModel.value[provider.value] : (providerStatus.value.qwen?.model || 'qwen3:4b-instruct')
const providerReady = () => Boolean(providerStatus.value[provider.value]?.connected && providerStatus.value[provider.value]?.model_ready)
const canViewPersonalOvertime = computed(() => hasPermission(authState.user, 'overtime.personal_summary', 'view'))
const canManageKnowledge = computed(() => hasPermission(authState.user, 'settings.ai', 'edit'))
const screenContext = computed(() => String(route.query.source || ''))
const screenInfo = ref(null)
const number = (value) => new Intl.NumberFormat('ja-JP', { maximumFractionDigits: 1 }).format(value || 0)
const barHeight = (value, values) => Math.max(3, Math.round((value / Math.max(...values, 1)) * 100))
const shortLabel = (value) => /^\d{4}-\d{2}-\d{2}$/.test(value) ? value.slice(5) : value.length > 8 ? `${value.slice(0, 7)}…` : value
const evidenceKind = (message) => {
  const source = String(message.source || '')
  if (message.provider === 'database' || /AI用DB辞書|工程実績|確定仕損|ブレーキ|残業申請|品番マスタ|マスタ検索|受注明細|仕入れ実績|出荷実績/.test(source)) return 'database'
  if (source.includes('ナレッジ:')) return 'knowledge'
  return 'general'
}
const evidenceLabel = (message) => ({ database: 'DB集計済み', knowledge: '正式ナレッジに基づく', general: '一般回答（PMデータは未確認）' }[evidenceKind(message)])
const evidenceIcon = (message) => ({ database: '✓', knowledge: '▤', general: 'i' }[evidenceKind(message)])
const formatRelativeTime = (value) => {
  if (!value) return ''
  const diffMs = Date.now() - new Date(value).getTime()
  const minutes = Math.floor(diffMs / 60000)
  if (minutes < 1) return 'たった今'
  if (minutes < 60) return `${minutes}分前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}時間前`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}日前`
  return new Date(value).toLocaleDateString('ja-JP')
}

const scrollToBottom = async () => {
  await nextTick()
  if (scrollArea.value) scrollArea.value.scrollTop = scrollArea.value.scrollHeight
}

const ask = async (question, crossScreenAccessIds = []) => {
  if (loading.value || !question?.trim()) return
  error.value = ''
  failedQuestion.value = ''
  messages.value.push({ role: 'user', content: question.trim() })
  loading.value = true
  abortController = new AbortController()
  await scrollToBottom()
  try {
    const history = messages.value.slice(-HISTORY_LIMIT, -1).map(({ role, content, period }) => ({ role, content, period }))
    const { data } = await api.aiChat.chat({
      message: question.trim(), history, provider: provider.value,
      model: isExternalProvider.value ? externalModel.value[provider.value] : undefined,
      allow_personal_overtime: canViewPersonalOvertime.value,
      screen_context: screenContext.value,
      cross_screen_access_ids: crossScreenAccessIds,
    }, { signal: abortController.signal })
    messages.value.push({
      role: 'assistant', content: data.answer, analysis: data.analysis, source: data.source,
      period: data.period, chart: data.chart, document: data.document, excel_export: data.excel_export === true,
      inference: data.inference, provider: data.provider, model: data.model,
      cross_screen_request: data.cross_screen_request ? { ...data.cross_screen_request, question: question.trim() } : null,
    })
    await saveConversation()
  } catch (e) {
    failedQuestion.value = question.trim()
    if (e.code === 'ERR_CANCELED') {
      error.value = '応答を中止しました。'
    } else {
      error.value = e.response?.data?.detail || '社内AIから応答を取得できませんでした。接続と設定を確認してください。'
      void refreshModelStatus()
    }
  } finally {
    abortController = null
    loading.value = false
    await scrollToBottom()
  }
}

const approveCrossScreen = (message) => {
  const request = message.cross_screen_request
  if (!request || loading.value) return
  request.approved = true
  ask(request.question, [request.policy_id])
}

const declineCrossScreen = (message) => {
  const request = message.cross_screen_request
  if (!request) return
  message.content = '横断参照は許可されなかったため、この質問では別画面のデータを参照しません。'
  message.cross_screen_request = null
}

const saveConversation = async () => {
  try {
    const payload = { screen_context: screenContext.value, provider: provider.value, messages: messages.value }
    if (conversationId.value) {
      await api.aiConversations.update(conversationId.value, payload)
    } else {
      const { data } = await api.aiConversations.create(payload)
      conversationId.value = data.id
    }
    await loadHistory()
  } catch {
    // 会話の保存に失敗しても、その場のチャット表示は継続する。
  }
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

const openConversation = async (id) => {
  try {
    const { data } = await api.aiConversations.get(id)
    messages.value = data.messages || []
    conversationId.value = data.id
    if (data.provider) provider.value = data.provider
    error.value = ''
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

const selectKnowledgeFile = (event) => {
  knowledgeUpload.value.file = event.target.files?.[0] || null
  knowledgeNotice.value = ''
  knowledgeError.value = ''
}

const uploadKnowledge = async () => {
  if (!knowledgeUpload.value.file || !knowledgeUpload.value.name || knowledgeUploading.value) return
  const form = new FormData()
  form.append('category', knowledgeUpload.value.category)
  form.append('name', knowledgeUpload.value.name)
  form.append('file', knowledgeUpload.value.file)
  knowledgeUploading.value = true
  knowledgeNotice.value = ''
  knowledgeError.value = ''
  try {
    await api.aiSettings.createKnowledgeDocument(form)
    knowledgeUpload.value = { category: 'manual', name: '', file: null }
    if (knowledgeFileInput.value) knowledgeFileInput.value.value = ''
    knowledgeNotice.value = 'RAG資料庫へ登録しました。以後の質問で検索対象になります。'
  } catch (requestError) {
    knowledgeError.value = requestError.response?.data?.detail || '資料を登録できませんでした。'
  } finally {
    knowledgeUploading.value = false
  }
}

// 画面の待ちを止める。サーバー側の処理は止まらない(応答は捨てる)
const stopAsk = () => { abortController?.abort() }

const retry = () => {
  const question = failedQuestion.value
  if (!question || loading.value) return
  if (messages.value[messages.value.length - 1]?.role === 'user') messages.value.pop()
  ask(question)
}

const copyMessage = async (index, text) => {
  try {
    await navigator.clipboard.writeText(String(text || ''))
    copiedIndex.value = index
    setTimeout(() => { if (copiedIndex.value === index) copiedIndex.value = -1 }, 1500)
  } catch {
    error.value = 'コピーできませんでした。ブラウザの権限を確認してください。'
    failedQuestion.value = ''
  }
}

const send = () => {
  const question = draft.value.trim()
  if (!question || loading.value || overLimit.value) return
  draft.value = ''
  ask(question)
}

const downloadReport = (message) => {
  const period = message.period ? `${message.period.start_date}〜${message.period.end_date}` : '指定なし'
  const markdown = `${message.document}\n\n---\nデータ取得元: ${message.source || 'なし（一般会話）'}\n対象期間: ${period}\n作成: 社内AI（${message.model || message.inference?.model || providerModel()} / ${providerLabel(message.provider)}）\n`
  const url = URL.createObjectURL(new Blob([markdown], { type: 'text/markdown;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = `社内AI報告書_${message.period?.start_date || '会話'}.md`
  link.click()
  URL.revokeObjectURL(url)
}

const clearChat = () => {
  if (loading.value) return
  messages.value = []
  error.value = ''
  draft.value = ''
  conversationId.value = null
}

const refreshModelStatus = async () => {
  try {
    const { data } = await api.aiChat.status({ screen_context: screenContext.value })
    screenInfo.value = data.screen || null
    providerStatus.value = data.providers || {}
    for (const key of EXTERNAL_PROVIDERS) {
      const defaultModel = data.providers?.[key]?.model
      if (defaultModel && (data.providers?.[key]?.models || []).some((item) => item.id === defaultModel)) {
        externalModel.value[key] = defaultModel
      }
    }
  } catch {
    providerStatus.value = {}
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

watch(screenContext, () => { void refreshModelStatus() })

onMounted(() => {
  refreshModelStatus()
  loadHistory()
})
</script>

<style scoped>
.workspace{--ink:#172e3b;--muted:#81929b;--line:#e6ecef;--teal:#168c7e;min-height:calc(100vh - 48px);margin:0 auto;max-width:1600px;background:#fff;border:1px solid #e8edef;border-radius:14px;overflow:hidden;color:var(--ink);font-family:Inter,"Yu Gothic UI",Meiryo,sans-serif;display:flex;flex-direction:column}.topbar{height:62px;flex:none;border-bottom:1px solid var(--line);display:flex;align-items:center;padding:0 25px;gap:11px}.brand-mark{width:30px;height:30px;border-radius:9px;background:#0e786d;color:#fff;display:grid;place-items:center;font-size:16px}.brand-title{display:grid;gap:1px}.brand-title strong{font-size:13px}.brand-title span{font-size:9px;color:var(--muted)}.local-badge{margin-left:10px;border:1px solid #d8ebe6;border-radius:15px;padding:5px 9px;color:#328476;font-size:9px;font-weight:800;letter-spacing:.7px;display:flex;align-items:center;gap:6px}.local-badge i,.online i,.composer-foot i{width:6px;height:6px;background:#34b984;border-radius:50%;box-shadow:0 0 0 3px #34b98420}.provider-select{font-size:9px;color:#72848d;display:flex;align-items:center;gap:5px}.provider-select select{border:1px solid #d8e4e3;border-radius:6px;background:#fff;color:#34515a;font:inherit;padding:5px 7px}.new-chat{border:1px solid #e1e9ec;background:white;border-radius:7px;padding:7px 11px;color:#4b606b;font-size:11px;cursor:pointer}.new-chat:hover{background:#f5f9f8}.history-wrap{position:relative;margin-left:auto}.history-toggle{border:1px solid #e1e9ec;background:white;border-radius:7px;padding:7px 11px;color:#4b606b;font-size:11px;cursor:pointer}.history-toggle:hover{background:#f5f9f8}.history-panel{position:absolute;top:calc(100% + 6px);right:0;width:280px;max-height:360px;overflow-y:auto;background:#fff;border:1px solid #e1e9ec;border-radius:10px;box-shadow:0 10px 28px #1a3b4722;z-index:20;padding:6px}.history-empty{padding:14px 10px;font-size:10px;color:#8a9aa1;text-align:center}.history-item{display:flex;align-items:center;gap:6px;padding:8px 9px;border-radius:7px;cursor:pointer}.history-item:hover{background:#f5f9f8}.history-item.active{background:#e8f3f1}.history-item-main{min-width:0;flex:1;display:grid;gap:2px}.history-item-main strong{font-size:11px;color:#274850;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.history-item-main small{font-size:9px;color:#8a9aa1}.history-delete{flex:none;border:0;background:transparent;color:#aeb9bd;font-size:14px;cursor:pointer;width:20px;height:20px;border-radius:5px}.history-delete:hover{background:#fdeceb;color:#c0564a}.layout{min-height:0;flex:1;display:grid;grid-template-columns:minmax(0,1fr) 270px}.chat-area{min-height:660px;min-width:0;display:flex;flex-direction:column;background:#fbfcfc}.unsupported-note{flex:none;margin:12px clamp(20px,5vw,76px) 0;padding:9px 12px;border:1px solid #f1dcc8;border-radius:8px;background:#fffaf5;color:#9a6941;font-size:11px;line-height:1.6}.welcome-card>p.coverage-note{margin-top:8px;font-size:11px;color:#328476}.conversation{flex:1;overflow:auto;padding:24px clamp(20px,5vw,76px) 20px;scroll-behavior:smooth}.welcome{display:grid;place-items:center}.welcome-card{max-width:650px;width:100%;margin:auto}.welcome-icon{width:48px;height:48px;border-radius:15px;background:linear-gradient(145deg,#e5f6f2,#c7eee4);display:grid;place-items:center;color:#087d70;font-size:25px;box-shadow:0 6px 18px #178c7c1a}.welcome-eyebrow{font-size:9px;letter-spacing:1.7px;font-weight:800;color:#53a395;margin-top:24px}.welcome-card h1{font-size:30px;letter-spacing:-.5px;margin:8px 0 10px;color:#173440}.welcome-card h1 span{color:#108c7c}.welcome-card>p{font-size:12px;color:#72848d;line-height:1.9;margin:0}.suggestions{margin-top:26px;display:grid;grid-template-columns:1fr 1fr;gap:9px}.suggestion{min-width:0;background:#fff;border:1px solid #e5ecee;border-radius:10px;padding:11px;display:flex;align-items:center;gap:10px;text-align:left;cursor:pointer;transition:.15s}.suggestion:hover{border-color:#80c9b7;box-shadow:0 5px 16px #1734400c;transform:translateY(-1px)}.suggestion-icon{width:30px;height:30px;flex:none;border-radius:9px;display:grid;place-items:center;font-size:14px;font-weight:800}.suggestion-icon.teal{color:#168f7e;background:#e7f7f2}.suggestion-icon.coral{color:#d47569;background:#fff0ec}.suggestion-icon.amber{color:#bf8a36;background:#fff6e8}.suggestion-icon.violet{color:#8170bd;background:#f2efff}.suggestion>span:nth-child(2){display:grid;gap:3px;min-width:0}.suggestion strong{font-size:11px}.suggestion small{font-size:9px;color:#8a9aa1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.suggestion>b{margin-left:auto;color:#b0bdc1;font-size:12px}.composer-wrap{flex:none;padding:10px clamp(20px,5vw,76px) 13px;background:linear-gradient(0deg,#fbfcfc 80%,#fbfcfc00)}.composer{display:flex;align-items:end;gap:8px;border:1px solid #dbe5e7;border-radius:12px;background:#fff;padding:9px 10px 9px 14px;box-shadow:0 5px 20px #1a3b4708}.composer:focus-within{border-color:#7eb9ac;box-shadow:0 0 0 3px #47b99a17}.composer textarea{resize:none;border:0;outline:0;flex:1;min-height:24px;max-height:130px;font:inherit;font-size:12px;color:var(--ink);padding:4px 0}.composer textarea::placeholder{color:#a1adb2}.send{width:31px;height:31px;flex:none;border:0;border-radius:9px;background:#087b6e;color:#fff;font-size:19px;line-height:1;cursor:pointer}.send:disabled{background:#dce7e6;color:#aebcba;cursor:default}.composer-foot{display:flex;justify-content:space-between;margin-top:7px;color:#9aa7ac;font-size:9px}.composer-foot>span:last-child{display:flex;align-items:center;gap:6px}.side-panel{border-left:1px solid var(--line);padding:19px 16px;background:#fff}.side-heading{font-size:11px;font-weight:800;color:#334d58;display:flex;justify-content:space-between;align-items:center;margin-bottom:11px}.side-heading span{font-size:14px;color:#a2b0b5}.local-card{border:1px solid #e6edee;background:#fbfdfd;border-radius:9px;padding:10px;display:flex;align-items:center;gap:8px}.local-symbol{width:30px;height:30px;border-radius:9px;display:grid;place-items:center;background:#e5f6f2;color:#168c7e}.local-card>div:nth-child(2){display:grid;gap:3px}.local-card strong{font-size:10px}.local-card small{font-size:9px;color:#8999a1}.online{margin-left:auto;font-size:8px;color:#418977;display:flex;align-items:center;gap:5px}.online i{width:5px;height:5px}.side-description{font-size:9px;line-height:1.7;color:#84939b;margin:8px 1px 14px}.side-divider{height:1px;background:#edf1f2;margin:14px 0}.source-item{display:flex;align-items:center;gap:9px;margin:11px 0}.db-icon{width:24px;height:24px;border-radius:7px;background:#eaf7f3;color:#369a85;display:grid;place-items:center;font-size:11px}.db-icon.coral{background:#fff0ed;color:#d58170}.db-icon.amber{background:#fff6e8;color:#c18a3d}.source-item>div{display:grid;gap:3px}.source-item strong{font-size:9px}.source-item small{font-size:8px;color:#92a0a5}.capabilities{padding:0;margin:0;list-style:none;display:grid;gap:9px}.capabilities li{font-size:9px;color:#667b84}.capabilities span{color:#26a17f;font-weight:900;margin-right:7px}.safety-note{display:flex;gap:8px;background:#f2f8f6;border-radius:8px;padding:10px;margin-top:17px;color:#628079}.safety-note>span{font-size:16px}.safety-note p{font-size:8px;line-height:1.75;margin:0;color:#788e88}.safety-note strong{font-size:9px;color:#477b70}.message-list{max-width:800px;margin:0 auto;display:grid;gap:22px}.message{display:flex;gap:10px;align-items:flex-start}.message.user{justify-content:flex-end}.avatar,.user-avatar{width:27px;height:27px;border-radius:9px;flex:none;display:grid;place-items:center}.avatar{background:#e2f4ef;color:#168875}.user-avatar{background:#eaf0f2;color:#60747c;font-size:8px;font-weight:800}.message-content{min-width:0;max-width:calc(100% - 40px);display:grid;gap:6px}.message.user .message-content{justify-items:end}.sender{font-size:9px;color:#809098;display:flex;align-items:center;gap:8px}.sender span{font-size:7px;letter-spacing:.7px;color:#44a38f;background:#edf8f5;padding:3px 5px;border-radius:5px}.bubble{white-space:pre-wrap;line-height:1.75;font-size:12px;color:#344b55}.user-bubble{background:#e8f3f1;color:#234f4b;border-radius:12px 3px 12px 12px;padding:9px 12px}.source-line{font-size:9px;color:#8a9ba2;margin-top:3px}.source-line span:first-child{color:#329984;margin-right:4px}.source-period{color:#a2afb4;margin-left:8px}.chart-card{width:min(600px,100%);background:#fff;border:1px solid #e6edef;border-radius:11px;margin-top:6px;padding:14px 16px;box-shadow:0 4px 16px #1c3b4808}.chart-heading{display:flex;justify-content:space-between;gap:8px;align-items:center}.chart-heading>div{display:grid;gap:4px}.chart-heading small{font-size:7px;letter-spacing:1.3px;color:#48a38f;font-weight:800}.chart-heading strong{font-size:10px}.chart-kind{font-size:8px;color:#88999f;background:#f4f7f7;border-radius:5px;padding:5px 7px}.bar-chart{height:145px;border-bottom:1px solid #e9eff0;display:flex;align-items:stretch;gap:7px;margin-top:15px;overflow-x:auto;padding:0 2px}.chart-column{flex:1;min-width:32px;max-width:70px;display:flex;flex-direction:column;align-items:center;justify-content:end;gap:4px}.bar-value{font-size:7px;color:#75878e;min-height:10px}.bar-track{height:96px;width:65%;display:flex;align-items:end;background:linear-gradient(0deg,#f8faf9 1px,transparent 1px);background-size:100% 24px}.bar-track i{width:100%;min-height:3px;background:linear-gradient(180deg,#43c3a2,#118777);border-radius:4px 4px 1px 1px;transition:height .3s}.chart-column small{font-size:7px;color:#85969c;white-space:nowrap}.chart-axis{text-align:right;font-size:8px;color:#9ba9ae;margin-top:7px}.download{border:1px solid #d7ebe5;background:#f4faf8;color:#247d6d;border-radius:7px;padding:8px 10px;font-size:9px;cursor:pointer;margin-top:6px}.download:hover{background:#eaf6f2}.download small{color:#86a89f;margin-left:5px}.thinking{height:38px;display:flex;align-items:center;gap:4px;color:#81949a}.thinking i{width:5px;height:5px;background:#43ae98;border-radius:50%;animation:bounce .9s infinite alternate}.thinking i:nth-child(2){animation-delay:.15s}.thinking i:nth-child(3){animation-delay:.3s}.thinking small{font-size:9px;margin-left:6px}@keyframes bounce{to{transform:translateY(-4px);opacity:.35}}.pulse{animation:pulse 1.5s infinite}@keyframes pulse{50%{box-shadow:0 0 0 5px #45ba9d20}}.error-card{margin-left:37px;border:1px solid #f1d9c6;border-radius:8px;background:#fffaf5;color:#9a6941;padding:10px;font-size:10px}.error-card small{display:block;color:#a99584;margin-top:4px}.message-list:has(.error-card){padding-bottom:10px}.mic-btn{flex:none;min-width:31px;height:31px;border:1px solid #dbe5e7;border-radius:9px;background:#fff;color:#4b606b;font-size:14px;padding:0 7px;cursor:pointer}.mic-btn:disabled{opacity:.5;cursor:default}.mic-btn.recording{background:#c0564a;border-color:#c0564a;color:#fff;font-size:11px}.copy-btn,.retry-btn{justify-self:start;border:1px solid #e1e9ec;background:#fff;color:#62757d;border-radius:6px;padding:3px 8px;font-size:9px;cursor:pointer}.copy-btn:hover,.retry-btn:hover{background:#f5f9f8}.retry-btn{margin-top:6px;color:#247d6d;border-color:#d7ebe5}.send.stop{background:#c0564a;font-size:13px}.history-note{margin-top:7px;padding:5px 9px;border-radius:6px;background:#fffaf5;border:1px solid #f1dcc8;color:#9a6941;font-size:9px}.composer-foot b.over{color:#c0564a}
@media(max-width:860px){.layout{grid-template-columns:minmax(0,1fr) 220px}.side-panel{padding:16px 12px}.conversation{padding-left:28px;padding-right:28px}.composer-wrap{padding-left:28px;padding-right:28px}}
@media(max-width:660px){.workspace{min-height:calc(100vh - 16px);border-radius:9px}.layout{display:block;position:relative;flex:1}.chat-area{min-height:calc(100vh - 85px)}.side-panel{display:none}.topbar{padding:0 14px;height:54px}.local-badge{margin-left:2px;font-size:8px}.new-chat{padding:7px}.new-chat span{display:none}.history-toggle{padding:7px}.history-toggle span{display:none}.history-panel{width:240px}.conversation{padding:22px 15px 14px}.composer-wrap{padding:8px 13px 12px}.welcome-card h1{font-size:24px}.welcome-card>p{font-size:11px}.suggestions{grid-template-columns:1fr;gap:7px;margin-top:19px}.suggestion{padding:9px}.suggestion-icon{width:27px;height:27px}.composer-foot{font-size:8px}.message-content{max-width:calc(100% - 38px)}.chart-card{padding:12px 10px}.bar-chart{gap:3px}}
.reasoning-note{border-left:2px solid #a9d8ca;padding:5px 9px;margin:2px 0 4px;color:#748b83}.reasoning-note span{font-size:8px;font-weight:800;letter-spacing:.3px;color:#438c79}.reasoning-note p{font-size:10px;line-height:1.65;margin:3px 0 0}
.local-badge.offline{border-color:#f0e2c5;color:#a37b2f}.local-badge.offline i,.online.offline i{background:#dfa746;box-shadow:0 0 0 3px #dfa74620}.online.offline{color:#a37b2f}
.evidence-line{width:max-content;max-width:100%;padding:3px 7px;border-radius:5px;font-size:9px;font-weight:700}.evidence-line span{display:inline-grid;place-items:center;width:12px;height:12px;margin-right:3px;border-radius:50%;font-size:8px}.evidence-line.database{background:#e9f8f1;color:#207762}.evidence-line.database span{background:#3da68c;color:#fff}.evidence-line.knowledge{background:#eef3ff;color:#4c6296}.evidence-line.knowledge span{background:#7790ca;color:#fff}.evidence-line.general{background:#f5f6f7;color:#77848a}.evidence-line.general span{background:#98a4a8;color:#fff}.knowledge-library{display:grid;gap:7px}.knowledge-library .side-divider{margin:0 0 4px}.knowledge-library p,.knowledge-library small{margin:0;font-size:9px;line-height:1.55;color:#788e88}.knowledge-library select,.knowledge-library input{width:100%;box-sizing:border-box;border:1px solid #d8e4e1;border-radius:6px;background:#fff;padding:6px;font-size:9px;color:#526970}.knowledge-library input[type=file]{padding:4px}.knowledge-library button{border:1px solid #2d9a83;border-radius:6px;background:#168875;color:#fff;padding:6px;font-size:9px;cursor:pointer}.knowledge-library button:disabled{opacity:.55;cursor:default}.knowledge-notice,.knowledge-error{padding:6px;border-radius:6px;font-size:9px;line-height:1.5}.knowledge-notice{background:#e9f8f1;color:#237765}.knowledge-error{background:#fff1ee;color:#ae5146}
.cross-screen-request{display:grid;gap:5px;padding:8px;border:1px solid #b8ded3;border-radius:7px;background:#f1faf7;font-size:10px;color:#176b60}.cross-screen-request small{color:#617b76}.cross-screen-request div{display:flex;gap:6px}.cross-screen-request button{border:0;border-radius:5px;background:#168875;color:#fff;padding:5px 8px;font-size:10px;cursor:pointer}.cross-screen-request button.decline{background:#fff;color:#65777d;border:1px solid #cfdcda}
</style>
