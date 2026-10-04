<template>
  <section class="ai-workspace" :key="authState.user?.id">
    <nav class="ai-tabs" role="tablist" aria-label="社内AI">
      <button v-for="tab in tabs" :id="`ai-tab-${tab.id}`" :key="tab.id" type="button" role="tab"
        :aria-selected="activeTab === tab.id" :aria-controls="`ai-panel-${tab.id}`"
        :tabindex="activeTab === tab.id ? 0 : -1" :class="{ active: activeTab === tab.id }"
        @click="activate(tab.id)" @keydown="moveTab($event, tab.id)">{{ tab.label }}</button>
    </nav>
    <div v-if="canSearch && visited.search" v-show="activeTab === 'search'" id="ai-panel-search" role="tabpanel" aria-labelledby="ai-tab-search">
      <ProductionAIDataAnalysis :can-analyze="canAnalyze" @analyze="openAnalysis" />
    </div>
    <div v-if="canAnalyze && visited.analysis" v-show="activeTab === 'analysis'" id="ai-panel-analysis" role="tabpanel" aria-labelledby="ai-tab-analysis">
      <AIAnalysis :request="analysisRequest" :can-edit="canEditAnalysis" :can-view-all="canViewAllAnalysisRuns" :visible="activeTab === 'analysis'" />
    </div>
    <p v-if="!tabs.length">社内AIの閲覧権限がありません。</p>
  </section>
</template>

<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { authState } from '@/auth'
import { hasPermission } from '@/router'
import ProductionAIDataAnalysis from '@/views/production/ProductionAIDataAnalysis.vue'
import AIAnalysis from './AIAnalysis.vue'

const canSearch = computed(() => hasPermission(authState.user, 'ai.chat'))
const canAnalyze = computed(() => hasPermission(authState.user, 'ai.analysis'))
const canEditAnalysis = computed(() => hasPermission(authState.user, 'ai.analysis', 'edit'))
const canViewAllAnalysisRuns = computed(() => hasPermission(authState.user, 'settings.ai', 'edit'))
const tabs = computed(() => [
  ...(canSearch.value ? [{ id: 'search', label: '検索' }] : []),
  ...(canAnalyze.value ? [{ id: 'analysis', label: '分析' }] : []),
])
const activeTab = ref('')
const visited = reactive({ search: false, analysis: false })
const analysisRequest = ref(null)

function activate(id) {
  if (!tabs.value.some(tab => tab.id === id)) return
  visited[id] = true
  activeTab.value = id
}
watch(tabs, (available) => {
  if (!available.some(tab => tab.id === activeTab.value)) activate(available[0]?.id)
}, { immediate: true })
// 利用者切替時は前の利用者の入力・会話を引き継がない。
watch(() => authState.user?.id, () => {
  visited.search = false
  visited.analysis = false
  analysisRequest.value = null
  activeTab.value = ''
  activate(tabs.value[0]?.id)
})
function openAnalysis(request) {
  if (!canAnalyze.value) return
  analysisRequest.value = request
  activate('analysis')
}
async function moveTab(event, id) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
  event.preventDefault()
  const index = tabs.value.findIndex(tab => tab.id === id)
  const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.value.length - 1
    : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.value.length) % tabs.value.length
  activate(tabs.value[next].id)
  await nextTick()
  document.getElementById(`ai-tab-${activeTab.value}`)?.focus()
}
</script>

<style scoped>
.ai-tabs { display: flex; gap: 4px; padding: 8px 16px 0; border-bottom: 1px solid #dce6e6; background: #fff; }
.ai-tabs button { border: 0; border-bottom: 3px solid transparent; background: transparent; padding: 10px 24px; color: #586b70; cursor: pointer; font: inherit; }
.ai-tabs button.active { border-bottom-color: #168779; color: #126d63; font-weight: 700; }
.ai-tabs button:focus-visible { outline: 2px solid #168779; outline-offset: -2px; }
</style>
