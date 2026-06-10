<template>
  <div class="tablet-process-input">
    <div class="toolbar">
      <h2 class="toolbar-title">１人２工程入力 <DataSourceDialog title="１人２工程入力" :sources="dsSources" /></h2>
      <label class="toolbar-label">{{ t('processInput.line') }}</label>
      <div class="toolbar-select-row">
        <select v-model="selectedLineId">
          <option value="">{{ t('processInput.selectLine') }}</option>
          <option v-for="line in availableLines" :key="line.id" :value="String(line.id)">
            {{ line.line_code }} - {{ line.line_name }}
          </option>
        </select>
        <button
          v-if="showSupportToggle"
          type="button"
          class="support-toggle-btn"
          :class="{ active: isSupportMode }"
          @click="toggleSupportMode"
        >
          {{ isSupportMode ? t('tabletProcessInput.supportOn') : t('tabletProcessInput.supportOff') }}
        </button>
      </div>
      <label class="toolbar-label">{{ t('tabletProcessInput.primaryProcess') }}</label>
      <select v-model="primaryProcessId" class="toolbar-select">
        <option value="">{{ t('processInput.selectProcess') }}</option>
        <option v-for="proc in filteredProcesses" :key="`p-${proc.id}`" :value="String(proc.id)">
          {{ proc.process_code }} - {{ proc.process_name }}
        </option>
      </select>
      <label class="toolbar-label">{{ t('tabletProcessInput.secondaryProcess') }}</label>
      <select v-model="secondaryProcessId" class="toolbar-select">
        <option value="">{{ t('processInput.selectProcess') }}</option>
        <option v-for="proc in filteredProcesses" :key="`s-${proc.id}`" :value="String(proc.id)">
          {{ proc.process_code }} - {{ proc.process_name }}
        </option>
      </select>
    </div>

    <div class="panels">
      <section class="panel">
        <div class="panel-title-row">
          <span class="panel-title">{{ t('tabletProcessInput.primaryPanel') }}</span>
          <span v-if="primaryProcessingLabel" class="processing-badge" @click="jumpToProcessing('primary')">{{ primaryProcessingLabel }}</span>
        </div>
        <div v-if="primaryProcessId" class="panel-frame-wrap">
          <iframe
            ref="primaryIframe"
            :src="primaryFrameSrc"
            class="panel-frame"
            title="primary-process-input"
          />
        </div>
        <div v-else class="panel-empty">{{ t('tabletProcessInput.selectPrimary') }}</div>
      </section>

      <section class="panel">
        <div class="panel-title-row">
          <span class="panel-title">{{ t('tabletProcessInput.secondaryPanel') }}</span>
          <span v-if="secondaryProcessingLabel" class="processing-badge" @click="jumpToProcessing('secondary')">{{ secondaryProcessingLabel }}</span>
        </div>
        <div v-if="secondaryProcessId" class="panel-frame-wrap">
          <iframe
            ref="secondaryIframe"
            :src="secondaryFrameSrc"
            class="panel-frame"
            title="secondary-process-input"
          />
        </div>
        <div v-else class="panel-empty">{{ t('tabletProcessInput.selectSecondary') }}</div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import api from '@/api/client'
import { authState, ensureAuth } from '@/auth'
import { t } from '@/i18n'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み取り', table: 'm_line', desc: 'ライン選択肢' },
  { op: '読み取り', table: 'm_process', desc: '工程選択肢' },
]

const lines = ref([])
const processes = ref([])

const selectedLineId = ref('')
const primaryProcessId = ref('')
const secondaryProcessId = ref('')
const primaryIframe = ref(null)
const secondaryIframe = ref(null)
const primaryProcessingLabel = ref('')
const secondaryProcessingLabel = ref('')

const onMessage = (e) => {
  if (e.data?.type !== 'processing-status') return
  const pid = e.data.processId
  if (pid === primaryProcessId.value) primaryProcessingLabel.value = e.data.label
  if (pid === secondaryProcessId.value) secondaryProcessingLabel.value = e.data.label
}

const jumpToProcessing = (panel) => {
  const iframe = panel === 'primary' ? primaryIframe.value : secondaryIframe.value
  const processId = panel === 'primary' ? primaryProcessId.value : secondaryProcessId.value
  if (iframe?.contentWindow) {
    iframe.contentWindow.postMessage({ type: 'jump-to-processing', processId }, '*')
  }
}

window.addEventListener('message', onMessage)
const isSupportMode = ref(false)

const userUnitLines = computed(() => {
  const unitLines = authState.user?.profile?.unit_lines
  return Array.isArray(unitLines) ? unitLines : []
})

const userAllowedLineIdSet = computed(
  () =>
    new Set(
      userUnitLines.value
        .map((item) => String(item?.line_id || '').trim())
        .filter(Boolean),
    ),
)

const preferredUserLineId = computed(() => {
  const mappings = userUnitLines.value
  if (!mappings.length) return ''
  const defaultMapping = mappings.find((item) => item?.is_default)
  const target = defaultMapping || mappings[0]
  return target?.line_id ? String(target.line_id) : ''
})

const ownLines = computed(() => {
  const allowedIds = userAllowedLineIdSet.value
  if (!allowedIds.size) return lines.value
  return lines.value.filter((line) => allowedIds.has(String(line.id)))
})

const showSupportToggle = computed(() => {
  const ownCount = ownLines.value.length
  return ownCount > 0 && ownCount < lines.value.length
})

const availableLines = computed(() => {
  if (isSupportMode.value) return lines.value
  return ownLines.value
})

const filteredProcesses = computed(() => {
  if (!selectedLineId.value) return []
  return processes.value.filter((p) => String(p.line) === String(selectedLineId.value))
})

const frameBasePath = '/production/desktop-process-input'
const supportModeParam = computed(() => (isSupportMode.value ? 'on' : 'off'))
const primaryFrameSrc = computed(() =>
  primaryProcessId.value
    ? `${frameBasePath}?process_id=${encodeURIComponent(primaryProcessId.value)}&embed=tablet&support_mode=${supportModeParam.value}`
    : '',
)
const secondaryFrameSrc = computed(() =>
  secondaryProcessId.value
    ? `${frameBasePath}?process_id=${encodeURIComponent(secondaryProcessId.value)}&embed=tablet&support_mode=${supportModeParam.value}`
    : '',
)

watch(selectedLineId, () => {
  const validSet = new Set(filteredProcesses.value.map((p) => String(p.id)))
  if (!validSet.has(primaryProcessId.value)) primaryProcessId.value = ''
  if (!validSet.has(secondaryProcessId.value)) secondaryProcessId.value = ''
})
watch(primaryProcessId, () => { primaryProcessingLabel.value = '' })
watch(secondaryProcessId, () => { secondaryProcessingLabel.value = '' })

watch(
  [availableLines, preferredUserLineId],
  ([nextLines, nextPreferred]) => {
    const candidateList = Array.isArray(nextLines) ? nextLines : []
    const exists = candidateList.some((line) => String(line.id) === String(selectedLineId.value))
    if (exists) return
    if (nextPreferred && candidateList.some((line) => String(line.id) === String(nextPreferred))) {
      selectedLineId.value = String(nextPreferred)
      return
    }
    selectedLineId.value = candidateList.length ? String(candidateList[0].id) : ''
  },
  { immediate: true },
)

const loadLines = async () => {
  const res = await api.lines.getProductionLines()
  lines.value = res.data.results || res.data || []
}

const loadProcesses = async () => {
  const res = await api.processes.getProcesses({ is_active: true })
  processes.value = res.data.results || res.data || []
}

const applyInitialLineSelection = () => {
  const candidateList = Array.isArray(availableLines.value) ? availableLines.value : []
  if (!candidateList.length) {
    selectedLineId.value = ''
    return
  }
  const preferred = preferredUserLineId.value
  if (preferred && candidateList.some((line) => String(line.id) === String(preferred))) {
    selectedLineId.value = String(preferred)
    return
  }
  selectedLineId.value = String(candidateList[0].id)
}

const toggleSupportMode = () => {
  isSupportMode.value = !isSupportMode.value
  if (isSupportMode.value) return
  const ownIds = new Set(ownLines.value.map((line) => String(line.id)))
  if (selectedLineId.value && ownIds.has(String(selectedLineId.value))) return
  const preferred = preferredUserLineId.value
  if (preferred && ownIds.has(String(preferred))) {
    selectedLineId.value = String(preferred)
    return
  }
  selectedLineId.value = ownLines.value.length ? String(ownLines.value[0].id) : ''
}

onMounted(async () => {
  await ensureAuth()
  await Promise.all([loadLines(), loadProcesses()])
  applyInitialLineSelection()
})

onBeforeUnmount(() => {
  window.removeEventListener('message', onMessage)
})
</script>

<style scoped>
.tablet-process-input {
  width: 100%;
  margin: 0 auto;
  padding: 4px;
  box-sizing: border-box;
}

.toolbar {
  background: #fff;
  border: 1px solid #d7dde6;
  border-radius: 8px;
  padding: 3px 10px;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-title {
  margin: 0;
  font-size: 16px;
  line-height: 1;
  color: #13315c;
  white-space: nowrap;
  flex-shrink: 0;
}

.toolbar-label {
  font-weight: 700;
  font-size: 11px;
  white-space: nowrap;
  flex-shrink: 0;
  color: #475569;
}

.toolbar-select,
.toolbar-select-row select {
  height: 30px;
  border: 1px solid #b8c3d6;
  border-radius: 6px;
  padding: 0 6px;
  background: #fff;
  font-size: 13px;
  font-weight: 600;
  min-width: 0;
  flex: 1 1 0;
}

.toolbar-select-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1 1 0;
  min-width: 0;
}

.support-toggle-btn {
  height: 30px;
  min-width: 64px;
  padding: 0 8px;
  border: 1px solid #b8c3d6;
  border-radius: 6px;
  background: #fff;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
}

.support-toggle-btn.active {
  border-color: #f59e0b;
  background: #ffedd5;
  color: #9a3412;
}

.panel-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}

.processing-badge {
  font-size: 12px;
  font-weight: 700;
  color: #166534;
  background: #dcfce7;
  border: 1px solid #86efac;
  border-radius: 4px;
  padding: 1px 8px;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.processing-badge:active { background: #bbf7d0; }

.panels {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
}

.panel {
  background: #dfe5ec;
  border: 1px solid #c7d0dd;
  border-radius: 8px;
  padding: 4px;
  min-height: calc(100vh - 120px);
  min-height: calc(100dvh - 120px);
}

.panel-title {
  font-weight: 800;
  color: #0f172a;
  margin-bottom: 2px;
  font-size: 14px;
  line-height: 1;
}

.panel-frame {
  width: 100%;
  min-height: calc(100vh - 128px);
  min-height: calc(100dvh - 128px);
  border: 1px solid #c7d0dd;
  border-radius: 6px;
  background: #fff;
}

.panel-frame-wrap {
  overflow: hidden;
  border-radius: 6px;
  border: 1px solid #c7d0dd;
}

.panel-empty {
  color: #6b7280;
  padding: 12px;
  background: #fff;
  border: 1px dashed #b8c3d6;
  border-radius: 6px;
}

@media (max-width: 640px) {
  .selectors {
    flex-direction: column;
  }
  .panels {
    grid-template-columns: 1fr;
  }
  .panel {
    min-height: 480px;
  }
  .panel-frame {
    min-height: 480px;
  }
}
</style>
