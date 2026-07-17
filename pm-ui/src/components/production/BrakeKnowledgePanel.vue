<template>
  <div class="knowledge-panel">
    <div class="knowledge-header">
      <div class="knowledge-title-row">
        <div class="knowledge-title" title="作業のコツ・注意事項">💡</div>
        <button
          class="knowledge-help-btn"
          type="button"
          title="作業のコツ、注意点、不良事例、新人向け確認事項をこの場で確認します"
          aria-label="作業のコツ、注意点、不良事例、新人向け確認事項をこの場で確認します"
        >
          i
        </button>
      </div>
      <button
        class="knowledge-icon-btn"
        type="button"
        title="関連マニュアルを開く"
        aria-label="関連マニュアルを開く"
        @click="openManual(topManualPath)"
      >
        📘
      </button>
    </div>

    <div class="knowledge-toolbar">
      <div class="knowledge-context">
        <span class="context-chip">品番: {{ selectedItem?.product_code || '未選択' }}</span>
        <span class="context-chip">設備: {{ selectedEquipmentLabel || '未選択' }}</span>
      </div>

      <div class="knowledge-actions">
        <button class="subtle-btn icon-only-btn" type="button" title="関連マニュアル" aria-label="関連マニュアル" @click="openManual(currentManualPath)">🔗</button>
        <button
          class="subtle-btn icon-only-btn"
          type="button"
          title="管理画面"
          aria-label="管理画面"
          @click="openManager"
        >
          ✏️
        </button>
      </div>
    </div>

    <div class="knowledge-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="knowledge-tab icon-only-btn"
        :class="{ active: activeTab === tab.key }"
        type="button"
        :title="tab.label"
        :aria-label="tab.label"
        @click="activeTab = tab.key"
      >
        {{ tab.icon }}
      </button>
    </div>

    <div class="knowledge-body">
      <div v-if="docLoading" class="knowledge-state">読込中...</div>
      <div v-else-if="docError" class="knowledge-state error">{{ docError }}</div>
      <article
        v-else
        class="knowledge-rendered"
        v-html="renderedDoc"
        @click="onContentClick"
      ></article>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import {
  PROCESS_KNOWLEDGE_TABS,
  buildProcessKnowledgeDefaultContent,
  buildProcessKnowledgePath,
} from '@/utils/processKnowledge'

const props = defineProps({
  selectedItem: {
    type: Object,
    default: null,
  },
  selectedProcessId: {
    type: [String, Number],
    default: '',
  },
  selectedEquipmentId: {
    type: [String, Number],
    default: '',
  },
  selectedEquipmentLabel: {
    type: String,
    default: '',
  },
})

const router = useRouter()

const topManualPath = '生産/ブレーキベンダー技術伝承トップ.md'
const tabs = PROCESS_KNOWLEDGE_TABS.map((tab) => ({
  ...tab,
  manualPath:
    tab.key === 'common'
      ? '生産/ブレーキベンダー技術伝承_共通手順.md'
      : tab.key === 'defects'
        ? '生産/ブレーキベンダー技術伝承_不良事例.md'
        : tab.key === 'equipment'
          ? '生産/ブレーキベンダー技術伝承_設備別注意.md'
          : '生産/ブレーキベンダー技術伝承_新人チェックリスト.md',
}))

const activeTab = ref('common')
const docLoading = ref(false)
const docError = ref('')
const docText = ref('')

const currentTab = computed(() => tabs.find((tab) => tab.key === activeTab.value) || tabs[0])
const currentManualPath = computed(() => currentTab.value.manualPath)
const processLabel = computed(() => {
  const code = props.selectedItem?.process_code || ''
  const name = props.selectedItem?.process_name || ''
  const merged = `${code} ${name}`.trim()
  return merged || '未選択工程'
})

const currentDocKey = computed(() => {
  return buildProcessKnowledgePath({
    processId: props.selectedProcessId,
    category: activeTab.value,
    equipmentId: props.selectedEquipmentId,
  })
})

const renderer = new marked.Renderer()
renderer.link = (href, title, text) => {
  const path = String(href || '')
  if (path.endsWith('.md')) {
    const encoded = encodeURIComponent(path)
    const titleAttr = title ? ` title="${title}"` : ''
    return `<a href="/manual?path=${encoded}"${titleAttr}>${text}</a>`
  }
  const titleAttr = title ? ` title="${title}"` : ''
  return `<a href="${path}"${titleAttr}>${text}</a>`
}

const renderedDoc = computed(() => {
  if (!docText.value) return ''
  return DOMPurify.sanitize(marked.parse(docText.value, { renderer, breaks: true }))
})

function getDefaultDoc(key) {
  if (!key) return '## 工程を選択すると内容を表示します'
  return buildProcessKnowledgeDefaultContent({
    category: activeTab.value,
    processLabel: processLabel.value,
    equipmentLabel: props.selectedEquipmentLabel || '',
  })
}

async function loadDoc() {
  docLoading.value = true
  docError.value = ''
  try {
    if (!currentDocKey.value) {
      docText.value = getDefaultDoc('')
      return
    }
    const res = await api.manualDocuments.read(currentDocKey.value)
    docText.value = String(res?.data?.content || '').trim() || getDefaultDoc(currentDocKey.value)
  } catch (error) {
    docText.value = getDefaultDoc(currentDocKey.value)
    if (error?.response?.status && error.response.status !== 404) {
      docError.value = error?.message || '読み込みに失敗しました'
    }
  } finally {
    docLoading.value = false
  }
}

function openManual(path) {
  router.push({ path: '/manual', query: { path } })
}

function openManager() {
  router.push({
    name: 'ProcessKnowledgeManager',
    query: {
      process_id: props.selectedProcessId || '',
      equipment_id: props.selectedEquipmentId || '',
      tab: activeTab.value,
    },
  })
}

function onContentClick(event) {
  const anchor = event.target?.closest?.('a')
  if (!anchor) return
  const href = anchor.getAttribute('href') || ''
  if (!href.startsWith('/manual?path=')) return
  event.preventDefault()
  const nextPath = decodeURIComponent(href.replace('/manual?path=', ''))
  openManual(nextPath)
}

watch(
  [activeTab, currentDocKey],
  () => {
    loadDoc()
  },
  { immediate: true }
)
</script>

<style scoped>
.knowledge-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
}

.knowledge-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px 6px;
  border-bottom: 1px solid #e5e7eb;
}

.knowledge-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.knowledge-title {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
  line-height: 1;
}

.knowledge-help-btn {
  width: 20px;
  height: 20px;
  min-width: 20px;
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  background: #f8fafc;
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: help;
  padding: 0;
}

.knowledge-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
  padding: 6px 10px 0;
}

.knowledge-context {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.context-chip {
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  min-width: 0;
  height: 22px;
  padding: 0 6px;
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 10px;
  font-weight: 600;
}

.knowledge-tabs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  padding: 6px 10px 0;
}

.knowledge-tab {
  width: 26px;
  min-width: 26px;
  height: 26px;
  padding: 0;
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.knowledge-tab.active {
  border-color: #2563eb;
  background: #2563eb;
  color: #fff;
}

.knowledge-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.knowledge-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 4px 10px 10px;
}

.knowledge-state {
  padding: 16px 0;
  color: #64748b;
  font-size: 13px;
}

.knowledge-state.error {
  color: #b91c1c;
}

.knowledge-rendered {
  font-size: 13px;
  line-height: 1.7;
  color: #1f2937;
  padding-bottom: 10px;
}

.knowledge-rendered :deep(h1),
.knowledge-rendered :deep(h2),
.knowledge-rendered :deep(h3) {
  margin-top: 16px;
  margin-bottom: 8px;
}

.knowledge-rendered :deep(ul) {
  padding-left: 18px;
}

.knowledge-rendered :deep(code) {
  background: #f1f5f9;
  padding: 2px 4px;
  border-radius: 4px;
}

.knowledge-rendered :deep(a) {
  color: #2563eb;
  text-decoration: underline;
}

.subtle-btn,
.knowledge-icon-btn {
  height: 24px;
  padding: 0 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 11px;
}

.subtle-btn,
.knowledge-icon-btn {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #334155;
}

.knowledge-icon-btn {
  width: 24px;
  min-width: 24px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.icon-only-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.subtle-btn.icon-only-btn,
.knowledge-icon-btn.icon-only-btn {
  width: 24px;
  min-width: 24px;
}
</style>
