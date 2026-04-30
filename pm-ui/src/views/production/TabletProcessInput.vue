<template>
  <div class="tablet-process-input">
    <div class="header">
      <h2>工程作業記録（タブレット）</h2>
    </div>

    <div class="selectors">
      <div class="selector">
        <label>ライン</label>
        <div class="line-select-row">
          <select v-model="selectedLineId">
            <option value="">-- ラインを選択 --</option>
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
            {{ isSupportMode ? '応援ON' : '応援OFF' }}
          </button>
        </div>
      </div>
      <div class="selector">
        <label>主工程</label>
        <select v-model="primaryProcessId">
          <option value="">-- 工程を選択 --</option>
          <option v-for="proc in filteredProcesses" :key="`p-${proc.id}`" :value="String(proc.id)">
            {{ proc.process_code }} - {{ proc.process_name }}
          </option>
        </select>
      </div>
      <div class="selector">
        <label>同時担当工程（任意）</label>
        <select v-model="secondaryProcessId">
          <option value="">-- 工程を選択 --</option>
          <option v-for="proc in filteredProcesses" :key="`s-${proc.id}`" :value="String(proc.id)">
            {{ proc.process_code }} - {{ proc.process_name }}
          </option>
        </select>
      </div>
    </div>

    <div class="panels">
      <section class="panel">
        <div class="panel-title">主工程入力</div>
        <div v-if="primaryProcessId" class="panel-frame-wrap">
          <iframe
            :src="primaryFrameSrc"
            class="panel-frame"
            title="primary-process-input"
          />
        </div>
        <div v-else class="panel-empty">主工程を選択してください。</div>
      </section>

      <section class="panel">
        <div class="panel-title">同時担当工程入力</div>
        <div v-if="secondaryProcessId" class="panel-frame-wrap">
          <iframe
            :src="secondaryFrameSrc"
            class="panel-frame"
            title="secondary-process-input"
          />
        </div>
        <div v-else class="panel-empty">同時担当工程を選択してください。</div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import api from '@/api/client'
import { authState, ensureAuth } from '@/auth'

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
  return processes.value.filter((p) => String(p.line) === String(selectedLineId.value))
})

const frameBasePath = '/production/mobile-process-input'
const primaryFrameSrc = computed(() =>
  primaryProcessId.value
    ? `${frameBasePath}?process_id=${encodeURIComponent(primaryProcessId.value)}&embed=tablet`
    : '',
)
const secondaryFrameSrc = computed(() =>
  secondaryProcessId.value
    ? `${frameBasePath}?process_id=${encodeURIComponent(secondaryProcessId.value)}&embed=tablet`
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
</script>

<style scoped>
.tablet-process-input {
  max-width: 1480px;
  margin: 0 auto;
  padding: 8px;
}

.header {
  background: #fff;
  border: 1px solid #d7dde6;
  border-radius: 8px;
  padding: 8px 12px;
  margin-bottom: 6px;
}

.header h2 {
  margin: 0;
  font-size: 24px;
  line-height: 1.1;
  color: #13315c;
}

.selectors {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
  margin-bottom: 6px;
}

.selector {
  background: #eef2f6;
  border: 1px solid #d1d9e6;
  border-radius: 8px;
  padding: 4px 6px;
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: center;
  column-gap: 6px;
}

.selector select {
  width: 100%;
  height: 34px;
  border: 1px solid #b8c3d6;
  border-radius: 6px;
  padding: 0 8px;
  background: #fff;
  font-size: 16px;
  font-weight: 600;
}

.line-select-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.support-toggle-btn {
  height: 34px;
  min-width: 78px;
  padding: 0 10px;
  border: 1px solid #b8c3d6;
  border-radius: 6px;
  background: #fff;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}

.support-toggle-btn.active {
  border-color: #f59e0b;
  background: #ffedd5;
  color: #9a3412;
}

.selector label {
  font-weight: 700;
  font-size: 12px;
  line-height: 1;
  white-space: nowrap;
}

.panels {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.panel {
  background: #dfe5ec;
  border: 1px solid #c7d0dd;
  border-radius: 8px;
  padding: 6px;
  min-height: calc(100vh - 240px);
}

.panel-title {
  font-weight: 800;
  color: #0f172a;
  margin-bottom: 2px;
  font-size: 16px;
  line-height: 1;
}

.panel-frame {
  width: 100%;
  min-height: calc(100vh - 248px + 76px);
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

@media (max-width: 1200px) {
  .selectors {
    grid-template-columns: 1fr;
  }
  .panels {
    grid-template-columns: 1fr;
  }
  .panel,
  .panel-frame {
    min-height: 560px;
  }
}
</style>
