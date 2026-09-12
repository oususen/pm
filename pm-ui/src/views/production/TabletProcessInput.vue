<template>
  <div class="tablet-process-input">
    <div class="header">
      <h2>{{ t('tabletProcessInput.title') }} <DataSourceDialog title="タブレット工程入力" :sources="dsSources" /></h2>
      <button class="btn-inspection-nav" @click="openIntegratedChecksheetOperation">チェックシート実施</button>
    </div>

    <div class="selectors">
      <div class="selector">
        <label>{{ t('processInput.line') }}</label>
        <div class="line-select-row">
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
      </div>
      <div class="selector">
        <label>{{ t('tabletProcessInput.primaryProcess') }}</label>
        <select v-model="primaryProcessId">
          <option value="">{{ t('processInput.selectProcess') }}</option>
          <option v-for="proc in filteredProcesses" :key="`p-${proc.id}`" :value="String(proc.id)">
            {{ proc.process_code }} - {{ proc.process_name }}
          </option>
        </select>
      </div>
      <div class="selector">
        <label>{{ t('tabletProcessInput.secondaryProcess') }}</label>
        <select v-model="secondaryProcessId">
          <option value="">{{ t('processInput.selectProcess') }}</option>
          <option v-for="proc in filteredProcesses" :key="`s-${proc.id}`" :value="String(proc.id)">
            {{ proc.process_code }} - {{ proc.process_name }}
          </option>
        </select>
      </div>
    </div>

    <div class="panels">
      <section class="panel">
        <div class="panel-title">{{ t('tabletProcessInput.primaryPanel') }}</div>
        <div v-if="primaryProcessId" class="panel-frame-wrap">
          <iframe
            :src="primaryFrameSrc"
            class="panel-frame"
            title="primary-process-input"
          />
        </div>
        <div v-else class="panel-empty">{{ t('tabletProcessInput.selectPrimary') }}</div>
      </section>

      <section class="panel">
        <div class="panel-title">{{ t('tabletProcessInput.secondaryPanel') }}</div>
        <div v-if="secondaryProcessId" class="panel-frame-wrap">
          <iframe
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
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import { authState, ensureAuth } from '@/auth'
import { t } from '@/i18n'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み取り', table: 'm_line', desc: 'ライン選択肢' },
  { op: '読み取り', table: 'm_process', desc: '工程選択肢' },
]

const router = useRouter()
const route = useRoute()

const lines = ref([])
const processes = ref([])

const selectedLineId = ref('')
const primaryProcessId = ref('')
const secondaryProcessId = ref('')
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
  return processes.value.filter((p) => String(p.line) === String(selectedLineId.value) && !p.two_person_only)
})

const frameBasePath = '/production/mobile-process-input'
const supportModeParam = computed(() => (isSupportMode.value ? 'on' : 'off'))
const primaryFrameSrc = computed(() =>
  primaryProcessId.value
    ? `${frameBasePath}?process_id=${encodeURIComponent(primaryProcessId.value)}&embed=tablet&support_mode=${supportModeParam.value}&parent_source=tablet_process_input&parent_panel=primary`
    : '',
)
const secondaryFrameSrc = computed(() =>
  secondaryProcessId.value
    ? `${frameBasePath}?process_id=${encodeURIComponent(secondaryProcessId.value)}&embed=tablet&support_mode=${supportModeParam.value}&parent_source=tablet_process_input&parent_panel=secondary`
    : '',
)

watch(selectedLineId, () => {
  const validSet = new Set(filteredProcesses.value.map((p) => String(p.id)))
  if (!validSet.has(primaryProcessId.value)) primaryProcessId.value = ''
  if (!validSet.has(secondaryProcessId.value)) secondaryProcessId.value = ''
})

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

const applyInitialSelectionFromRoute = () => {
  const lineId = route.query?.line_id ? String(route.query.line_id) : ''
  if (lineId && availableLines.value.some((line) => String(line.id) === lineId)) {
    selectedLineId.value = lineId
  } else {
    applyInitialLineSelection()
  }
  const processId = route.query?.process_id ? String(route.query.process_id) : ''
  const returnPanel = route.query?.return_panel ? String(route.query.return_panel) : 'primary'
  if (!processId) return
  if (returnPanel === 'secondary') secondaryProcessId.value = processId
  else primaryProcessId.value = processId
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

const openIntegratedChecksheetOperation = () => {
  const lineId = selectedLineId.value || undefined
  const processId = primaryProcessId.value || undefined
  router.push({
    path: '/quality/product-checksheet/integrated/operation',
    query: {
      source: 'tablet_process_input',
      ...(lineId ? { line_id: String(lineId) } : {}),
      ...(processId ? { process_id: String(processId) } : {}),
    },
  })
}

onMounted(async () => {
  await ensureAuth()
  await Promise.all([loadLines(), loadProcesses()])
  applyInitialSelectionFromRoute()
})
</script>

<style scoped>
.tablet-process-input {
  width: 100%;
  margin: 0 auto;
  padding: 4px;
  box-sizing: border-box;
}

.header {
  background: #fff;
  border: 1px solid #d7dde6;
  border-radius: 8px;
  padding: 4px 12px;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.header h2 {
  margin: 0;
  font-size: 20px;
  line-height: 1.1;
  color: #13315c;
}
.btn-inspection-nav {
  height: 30px;
  padding: 0 12px;
  border: 1px solid #2563eb;
  background: #fff;
  color: #2563eb;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
  flex-shrink: 0;
}

.selectors {
  display: flex;
  gap: 4px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.selector {
  background: #eef2f6;
  border: 1px solid #d1d9e6;
  border-radius: 8px;
  padding: 3px 6px;
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1 1 0;
  min-width: 0;
}

.selector select {
  width: 100%;
  min-width: 0;
  height: 32px;
  border: 1px solid #b8c3d6;
  border-radius: 6px;
  padding: 0 6px;
  background: #fff;
  font-size: 14px;
  font-weight: 600;
}

.line-select-row {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  min-width: 0;
}

.line-select-row select {
  flex: 1;
  min-width: 0;
}

.support-toggle-btn {
  height: 32px;
  min-width: 72px;
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

.selector label {
  font-weight: 700;
  font-size: 11px;
  line-height: 1;
  white-space: nowrap;
  flex-shrink: 0;
}

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
  min-height: calc(100vh - 160px);
  min-height: calc(100dvh - 160px);
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
  min-height: calc(100vh - 168px + 76px);
  min-height: calc(100dvh - 168px + 76px);
  border: 1px solid #c7d0dd;
  border-radius: 6px;
  background: #fff;
  margin-top: -76px;
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
    min-height: calc(480px + 76px);
  }
}
</style>
