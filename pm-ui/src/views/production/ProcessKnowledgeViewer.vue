<template>
  <div class="knowledge-viewer">
    <div class="page-header">
      <div>
        <h2 class="page-title">工程別コツ・注意事項</h2>
        <p class="page-note">入力画面とは分けて、工程ごとのコツ・注意点・不良事例・新人確認事項を確認します。</p>
      </div>
      <div class="header-actions">
        <button class="subtle-btn" type="button" @click="reloadDoc" :disabled="loadingDoc || !selectedProcessId">再読込</button>
        <button v-if="canEditKnowledge" class="primary-btn" type="button" @click="openManager" :disabled="!selectedProcessId">編集する</button>
      </div>
    </div>

    <div class="filters">
      <label class="filter-field">
        <span class="filter-label">工程</span>
        <select v-model="selectedProcessId" class="filter-select">
          <option value="">選択してください</option>
          <option v-for="process in processes" :key="process.id" :value="String(process.id)">
            {{ process.process_code }} {{ process.process_name }}
          </option>
        </select>
      </label>

      <label class="filter-field">
        <span class="filter-label">設備</span>
        <select v-model="selectedEquipmentId" class="filter-select" :disabled="!selectedProcessId">
          <option value="">共通メモ</option>
          <option v-for="equipment in filteredEquipments" :key="equipment.id" :value="String(equipment.id)">
            {{ buildEquipmentLabel(equipment) }}
          </option>
        </select>
      </label>
    </div>

    <div class="context-bar">
      <span class="context-chip">工程: {{ selectedProcessLabel || '未選択' }}</span>
      <span class="context-chip">設備: {{ selectedEquipmentLabel || '共通メモ' }}</span>
    </div>

    <div class="category-tabs">
      <button
        v-for="tab in PROCESS_KNOWLEDGE_TABS"
        :key="tab.key"
        class="tab-btn"
        :class="{ active: activeTab === tab.key }"
        type="button"
        @click="activeTab = tab.key"
      >
        <span class="tab-icon">{{ tab.icon }}</span>
        <span>{{ tab.label }}</span>
      </button>
    </div>

    <div v-if="errorMessage" class="status-message error">{{ errorMessage }}</div>
    <div v-else-if="infoMessage" class="status-message">{{ infoMessage }}</div>

    <section class="preview-card">
      <div v-if="loadingDoc" class="knowledge-state">読込中...</div>
      <div v-else class="preview-body" v-html="renderedDoc"></div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import api from '@/api/client'
import { authState } from '@/auth'
import { canAccessRouteResource } from '@/router'
import {
  PROCESS_KNOWLEDGE_TABS,
  buildProcessKnowledgeDefaultContent,
  buildProcessKnowledgePath,
} from '@/utils/processKnowledge'

const route = useRoute()
const router = useRouter()

const processes = ref([])
const equipments = ref([])
const selectedProcessId = ref('')
const selectedEquipmentId = ref('')
const activeTab = ref('common')
const docText = ref('')
const loadingDoc = ref(false)
const errorMessage = ref('')
const infoMessage = ref('工程を選択すると内容を表示します。')

const selectedProcess = computed(() =>
  processes.value.find((process) => String(process.id) === String(selectedProcessId.value)) || null
)

const selectedProcessLabel = computed(() => {
  if (!selectedProcess.value) return ''
  return `${selectedProcess.value.process_code} ${selectedProcess.value.process_name}`.trim()
})

const filteredEquipments = computed(() =>
  equipments.value
    .filter((equipment) => String(equipment.process ?? '') === String(selectedProcessId.value))
    .sort((a, b) => buildEquipmentLabel(a).localeCompare(buildEquipmentLabel(b), 'ja'))
)

const selectedEquipment = computed(() =>
  filteredEquipments.value.find((equipment) => String(equipment.id) === String(selectedEquipmentId.value)) || null
)

const selectedEquipmentLabel = computed(() => buildEquipmentLabel(selectedEquipment.value))
const canEditKnowledge = computed(() =>
  canAccessRouteResource(authState.user, 'production.process_knowledge', 'edit', null, false)
)
const currentDocPath = computed(() =>
  buildProcessKnowledgePath({
    processId: selectedProcessId.value,
    category: activeTab.value,
    equipmentId: selectedEquipmentId.value,
  })
)

const renderedDoc = computed(() => {
  const source = docText.value || buildFallbackDoc()
  return DOMPurify.sanitize(marked.parse(source, { breaks: true }))
})

function buildEquipmentLabel(equipment) {
  if (!equipment) return ''
  const code = equipment.equipment_code || ''
  const name = equipment.equipment_name || ''
  return `${code} ${name}`.trim()
}

function buildFallbackDoc() {
  if (!selectedProcessId.value) return '## 工程を選択すると内容を表示します'
  return buildProcessKnowledgeDefaultContent({
    category: activeTab.value,
    processLabel: selectedProcessLabel.value || '未選択工程',
    equipmentLabel: selectedEquipmentLabel.value || '共通メモ',
  })
}

async function fetchMasterData() {
  const [processResponse, equipmentResponse] = await Promise.all([
    api.processes.getProcesses({ ordering: 'process_code', is_active: true, page_size: 500 }),
    api.equipments.getEquipments({ ordering: 'display_order,equipment_code', is_active: true, page_size: 500 }),
  ])
  processes.value = processResponse.data.results || processResponse.data || []
  equipments.value = equipmentResponse.data.results || equipmentResponse.data || []
}

async function loadDoc() {
  errorMessage.value = ''

  if (!selectedProcessId.value) {
    docText.value = ''
    infoMessage.value = '工程を選択すると内容を表示します。'
    return
  }

  loadingDoc.value = true
  infoMessage.value = ''
  try {
    const response = await api.manualDocuments.read(currentDocPath.value)
    docText.value = String(response?.data?.content || '').trim() || buildFallbackDoc()
  } catch (error) {
    docText.value = buildFallbackDoc()
    if (error?.response?.status === 404) {
      infoMessage.value = '未登録のため初期テンプレートを表示しています。'
      return
    }
    errorMessage.value = error?.message || '読み込みに失敗しました'
  } finally {
    loadingDoc.value = false
  }
}

function reloadDoc() {
  loadDoc()
}

function openManager() {
  router.push({
    name: 'ProcessKnowledgeManager',
    query: {
      process_id: selectedProcessId.value || '',
      equipment_id: selectedEquipmentId.value || '',
      tab: activeTab.value,
    },
  })
}

watch(selectedProcessId, () => {
  if (!filteredEquipments.value.some((equipment) => String(equipment.id) === String(selectedEquipmentId.value))) {
    selectedEquipmentId.value = ''
  }
})

watch([selectedProcessId, selectedEquipmentId, activeTab], () => {
  loadDoc()
  router.replace({
    query: {
      ...route.query,
      process_id: selectedProcessId.value || undefined,
      equipment_id: selectedEquipmentId.value || undefined,
      tab: activeTab.value || undefined,
    },
  })
})

onMounted(async () => {
  selectedProcessId.value = String(route.query.process_id || '')
  activeTab.value = PROCESS_KNOWLEDGE_TABS.some((tab) => tab.key === route.query.tab) ? String(route.query.tab) : 'common'
  selectedEquipmentId.value = String(route.query.equipment_id || '')

  try {
    await fetchMasterData()
  } catch (error) {
    errorMessage.value = error?.message || '工程・設備の取得に失敗しました'
  }

  if (!selectedProcessId.value && processes.value.length === 1) {
    selectedProcessId.value = String(processes.value[0].id)
  }

  if (selectedProcessId.value) {
    loadDoc()
  }
})
</script>

<style scoped>
.knowledge-viewer {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.page-title {
  margin: 0;
  font-size: 22px;
  color: #0f172a;
}

.page-note {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 13px;
}

.header-actions,
.filters,
.context-bar,
.category-tabs {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.filter-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 260px;
}

.filter-label {
  font-size: 12px;
  font-weight: 700;
  color: #475569;
}

.filter-select {
  height: 36px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #fff;
  padding: 0 10px;
  font-size: 13px;
}

.context-chip {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 600;
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 12px;
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  background: #fff;
  color: #334155;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
}

.tab-btn.active {
  border-color: #2563eb;
  background: #2563eb;
  color: #fff;
}

.status-message {
  padding: 10px 12px;
  border-radius: 8px;
  background: #f8fafc;
  color: #475569;
  font-size: 13px;
}

.status-message.error {
  background: #fef2f2;
  color: #b91c1c;
}

.preview-card {
  min-height: 480px;
  padding: 16px;
  border: 1px solid #dbe2ea;
  border-radius: 12px;
  background: #fff;
}

.knowledge-state {
  padding: 16px 0;
  color: #64748b;
  font-size: 13px;
}

.preview-body {
  color: #1f2937;
  line-height: 1.8;
  font-size: 14px;
}

.preview-body :deep(h1),
.preview-body :deep(h2),
.preview-body :deep(h3) {
  margin-top: 18px;
  margin-bottom: 8px;
}

.preview-body :deep(ul),
.preview-body :deep(ol) {
  padding-left: 20px;
}

.preview-body :deep(code) {
  background: #f1f5f9;
  padding: 2px 4px;
  border-radius: 4px;
}

.subtle-btn,
.primary-btn {
  height: 36px;
  padding: 0 14px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
}

.subtle-btn {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #334155;
}

.primary-btn {
  border: 1px solid #2563eb;
  background: #2563eb;
  color: #fff;
}

.subtle-btn:disabled,
.primary-btn:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>
