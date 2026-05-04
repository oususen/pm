<template>
  <div class="simultaneous-process-input">
    <div class="header">
      <h2>{{ t('simultaneousInput.title') }}</h2>
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
        <label>{{ t('simultaneousInput.primaryProcess') }}</label>
        <select v-model="primaryProcessId">
          <option value="">{{ t('processInput.selectProcess') }}</option>
          <option v-for="proc in filteredProcesses" :key="`p-${proc.id}`" :value="String(proc.id)">
            {{ proc.process_code }} - {{ proc.process_name }}
          </option>
        </select>
      </div>
      <div class="selector">
        <label>{{ t('simultaneousInput.secondaryProcess') }}</label>
        <select v-model="secondaryProcessId">
          <option value="">{{ t('simultaneousInput.noSecondary') }}</option>
          <option v-for="proc in filteredProcesses" :key="`s-${proc.id}`" :value="String(proc.id)">
            {{ proc.process_code }} - {{ proc.process_name }}
          </option>
        </select>
      </div>
      <div class="selector secondary-worker-selector" :class="{ disabled: !secondaryProcessId }">
        <label>{{ t('simultaneousInput.secondaryWorker') }}</label>
        <div class="worker-lookup">
          <input
            type="text"
            v-model="secondaryWorkerInput"
            :placeholder="t('simultaneousInput.secondaryWorkerPlaceholder')"
            :disabled="!secondaryProcessId"
            class="worker-id-input"
            @blur="resolveWorkerName"
            @keydown.enter="resolveWorkerName"
          />
          <span class="worker-resolved-name" :class="{ found: secondaryWorkerResolved, 'not-found': secondaryWorkerInput && !secondaryWorkerResolved }">
            {{ secondaryWorkerResolved || (secondaryWorkerInput ? t('simultaneousInput.workerNotFound') : '') }}
          </span>
        </div>
      </div>
    </div>

    <div class="panels">
      <section class="panel primary-panel">
        <div class="panel-title">{{ t('simultaneousInput.primaryPanel') }}</div>
        <div v-if="primaryProcessId" class="panel-frame-wrap">
          <iframe
            :src="primaryFrameSrc"
            class="panel-frame"
            title="primary-process-input"
          />
        </div>
        <div v-else class="panel-empty">{{ t('simultaneousInput.selectPrimary') }}</div>
      </section>

      <section class="panel secondary-panel" :class="{ inactive: !secondaryProcessId }">
        <div class="panel-title">
          {{ t('simultaneousInput.secondaryPanel') }}
          <span v-if="!secondaryProcessId" class="optional-badge">{{ t('simultaneousInput.optional') }}</span>
        </div>
        <div v-if="secondaryProcessId && secondaryWorkerResolved" class="panel-frame-wrap">
          <iframe
            :key="secondaryIframeKey"
            :src="secondaryFrameSrc"
            class="panel-frame"
            title="secondary-process-input"
          />
        </div>
        <div v-else-if="secondaryProcessId && !secondaryWorkerResolved" class="panel-empty worker-required">
          {{ t('simultaneousInput.workerRequired') }}
        </div>
        <div v-else class="panel-empty">{{ t('simultaneousInput.secondaryInactive') }}</div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import { authState, ensureAuth } from '@/auth'
import { t } from '@/i18n'
const router = useRouter()

const lines = ref([])
const processes = ref([])

const selectedLineId = ref('')
const primaryProcessId = ref('')
const secondaryProcessId = ref('')
const secondaryWorkerInput = ref('')
const secondaryWorkerResolved = ref('')
const isSupportMode = ref(false)
const users = ref([])

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

const frameBasePath = '/production/mobile-process-input'
const supportModeParam = computed(() => (isSupportMode.value ? 'on' : 'off'))

const primaryFrameSrc = computed(() =>
  primaryProcessId.value
    ? `${frameBasePath}?process_id=${encodeURIComponent(primaryProcessId.value)}&embed=tablet&support_mode=${supportModeParam.value}`
    : '',
)

const secondaryIframeKey = computed(() =>
  `${secondaryProcessId.value}_${secondaryWorkerResolved.value}`
)

const secondaryFrameSrc = computed(() => {
  if (!secondaryProcessId.value) return ''
  let url = `${frameBasePath}?process_id=${encodeURIComponent(secondaryProcessId.value)}&embed=tablet&support_mode=${supportModeParam.value}`
  if (secondaryWorkerResolved.value) {
    url += `&operator_name=${encodeURIComponent(secondaryWorkerResolved.value)}`
  } else {
    url += '&clear_operator=1'
  }
  return url
})

const userMap = computed(() => {
  const map = new Map()
  for (const u of users.value) {
    const name = `${u.last_name || ''} ${u.first_name || ''}`.trim() || u.username
    map.set(u.username.toLowerCase(), name)
  }
  return map
})

const resolveWorkerName = () => {
  const input = (secondaryWorkerInput.value || '').trim().toLowerCase()
  if (!input) {
    secondaryWorkerResolved.value = ''
    return
  }
  secondaryWorkerResolved.value = userMap.value.get(input) || ''
}

const loadUsers = async () => {
  const res = await api.accounts.getUsers({ is_active: true })
  users.value = res.data.results || res.data || []
}

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
      source: 'simultaneous_process_input',
      ...(lineId ? { line_id: String(lineId) } : {}),
      ...(processId ? { process_id: String(processId) } : {}),
    },
  })
}

onMounted(async () => {
  await ensureAuth()
  await Promise.all([loadLines(), loadProcesses(), loadUsers()])
  applyInitialLineSelection()
})
</script>

<style scoped>
.simultaneous-process-input {
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

.selector select,
.worker-input {
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

.worker-lookup {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  min-width: 0;
}

.worker-id-input {
  width: 100px;
  min-width: 80px;
  height: 32px;
  border: 1px solid #b8c3d6;
  border-radius: 6px;
  padding: 0 6px;
  background: #fff;
  font-size: 14px;
  font-weight: 600;
}

.worker-resolved-name {
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.worker-resolved-name.found {
  color: #166534;
}

.worker-resolved-name.not-found {
  color: #dc2626;
  font-weight: 600;
}

.secondary-worker-selector.disabled {
  opacity: 0.5;
}

.secondary-worker-selector.disabled .worker-id-input {
  background: #f0f0f0;
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

.secondary-panel.inactive {
  background: #f0f2f5;
  border-style: dashed;
}

.panel-title {
  font-weight: 800;
  color: #0f172a;
  margin-bottom: 2px;
  font-size: 14px;
  line-height: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.optional-badge {
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  background: #e5e7eb;
  padding: 1px 6px;
  border-radius: 4px;
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

.panel-empty.worker-required {
  color: #dc2626;
  background: #fef2f2;
  border-color: #fca5a5;
  font-weight: 700;
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
