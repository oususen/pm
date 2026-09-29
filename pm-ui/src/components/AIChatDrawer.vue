<template>
  <aside v-if="aiDrawerOpen" class="ai-drawer" aria-label="社内AIチャット">
    <header class="drawer-header">
      <div>
        <strong>✦ 社内AI</strong>
        <small>起点: {{ sourceLabel }}</small>
      </div>
      <div class="drawer-actions">
        <select v-model="provider" :disabled="loading" aria-label="AIプロバイダ">
          <option v-for="item in availableProviders" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
        <button type="button" title="新しい会話" :disabled="loading" @click="clearChat">＋</button>
        <button type="button" title="閉じる" @click="closeAIDrawer">×</button>
      </div>
    </header>

    <div ref="conversation" class="drawer-conversation">
      <div v-if="messages.length === 0" class="drawer-welcome">
        <strong>{{ sourceLabel }}画面のAI支援</strong>
        <p>現在の画面を残したまま質問できます。</p>
      </div>
      <article v-for="(message, index) in messages" :key="index" class="drawer-message" :class="message.role">
        <small>{{ message.role === 'user' ? 'あなた' : '社内AI' }}</small>
        <p>{{ message.content }}</p>
        <em v-if="message.source">▤ {{ message.source }}<span v-if="message.period"> · {{ message.period.start_date }}<template v-if="message.period.end_date">〜{{ message.period.end_date }}</template><template v-else>以降</template></span></em>
      </article>
      <div v-if="loading" class="drawer-loading">✦ AIが確認しています…</div>
      <div v-if="error" class="drawer-error">⚠ {{ error }}</div>
    </div>

    <form class="drawer-composer" @submit.prevent="send">
      <textarea v-model="draft" :disabled="loading" rows="2" placeholder="この画面について質問…" @keydown.enter.exact.prevent="send" />
      <button type="submit" :disabled="loading || !draft.trim()">↑</button>
    </form>
  </aside>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { authState } from '@/auth'
import api from '@/api/client'
import { hasPermission } from '@/router'
import { aiDrawerOpen, aiDrawerSourcePath, closeAIDrawer } from '@/composables/aiDrawer'

const provider = ref('deepseek')
const messages = ref([])
const draft = ref('')
const loading = ref(false)
const error = ref('')
const conversation = ref(null)
const availableProviders = ref([
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'qwen', label: 'Qwen' },
])
const canViewPersonalOvertime = computed(() => hasPermission(authState.user, 'overtime.personal_summary', 'view'))

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
}

const loadProviderSettings = async () => {
  try {
    const { data } = await api.aiChat.status()
    const nextProviders = Object.entries(data.providers || {})
      .filter(([, item]) => item.is_enabled !== false)
      .map(([value, item]) => ({ value, label: value === 'deepseek' ? 'DeepSeek' : 'Qwen', item }))
    if (nextProviders.length) {
      availableProviders.value = nextProviders
      if (!nextProviders.some((item) => item.value === provider.value)) provider.value = nextProviders[0].value
    }
  } catch { /* チャット送信時に接続エラーを表示する */ }
}

const send = async () => {
  const question = draft.value.trim()
  if (!question || loading.value) return
  draft.value = ''
  error.value = ''
  messages.value.push({ role: 'user', content: question })
  loading.value = true
  await scrollToBottom()
  try {
    const history = messages.value.slice(-15, -1).map(({ role, content, period }) => ({ role, content, period }))
    const { data } = await api.aiChat.chat({
      message: question,
      history,
      provider: provider.value,
      allow_personal_overtime: canViewPersonalOvertime.value,
      screen_context: aiDrawerSourcePath.value,
    })
    messages.value.push({
      role: 'assistant', content: data.answer, source: data.source, period: data.period,
    })
  } catch (requestError) {
    error.value = requestError.response?.data?.detail || '社内AIから応答を取得できませんでした。'
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

watch(aiDrawerSourcePath, clearChat)
onMounted(loadProviderSettings)
</script>

<style scoped>
.ai-drawer{position:fixed;top:74px;right:0;bottom:0;z-index:900;width:min(430px,100vw);display:flex;flex-direction:column;background:#fff;border-left:1px solid #cfe0dc;box-shadow:-8px 0 24px rgba(24,62,57,.16);color:#27454a}.drawer-header{min-height:58px;display:flex;align-items:center;justify-content:space-between;gap:10px;padding:9px 12px;border-bottom:1px solid #e2ece9;background:#f5fbf9}.drawer-header strong,.drawer-header small{display:block}.drawer-header strong{font-size:14px;color:#087b6e}.drawer-header small{margin-top:3px;font-size:10px;color:#71878b}.drawer-actions{display:flex;align-items:center;gap:5px}.drawer-actions select,.drawer-actions button{height:29px;border:1px solid #d1e2dd;border-radius:6px;background:#fff;color:#466169;font-size:11px}.drawer-actions select{max-width:92px;padding:0 5px}.drawer-actions button{width:29px;cursor:pointer}.drawer-actions button:disabled{opacity:.5;cursor:default}.drawer-conversation{flex:1;overflow:auto;padding:14px 13px;background:#fbfdfc}.drawer-welcome{margin:18px 2px;color:#547177}.drawer-welcome strong{font-size:13px}.drawer-welcome p{font-size:11px;line-height:1.7}.drawer-message{display:grid;gap:4px;margin:0 0 14px;max-width:92%}.drawer-message.user{margin-left:auto;justify-items:end}.drawer-message small{font-size:9px;color:#82969a}.drawer-message p{white-space:pre-wrap;line-height:1.65;margin:0;padding:8px 10px;border-radius:9px;background:#fff;border:1px solid #e3ece9;font-size:12px}.drawer-message.user p{background:#e7f4f0;border-color:#d6ebe5}.drawer-message em{font-style:normal;font-size:9px;color:#789196}.drawer-loading,.drawer-error{font-size:11px;padding:9px;border-radius:7px}.drawer-loading{color:#438b7c;background:#edf8f5}.drawer-error{color:#a06d43;background:#fff7ef;border:1px solid #f1dcc8}.drawer-composer{display:flex;gap:7px;padding:10px;border-top:1px solid #e2ece9;background:#fff}.drawer-composer textarea{flex:1;resize:none;border:1px solid #cfdfdb;border-radius:8px;padding:7px;font:inherit;font-size:12px;outline:none}.drawer-composer textarea:focus{border-color:#56aa99}.drawer-composer button{width:34px;border:0;border-radius:8px;background:#087b6e;color:white;font-size:18px}.drawer-composer button:disabled{background:#cbdad7}@media(max-width:768px){.ai-drawer{top:0;width:100%;z-index:1100}}
</style>
