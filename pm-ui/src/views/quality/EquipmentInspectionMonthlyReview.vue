<template>
  <div class="page-container inspection-monthly-review" v-if="canView">
    <div class="page-header">
      <h2 class="page-title">月間確認 <DataSourceDialog title="月間確認" :sources="dsSources" /></h2>
      <div class="page-actions">
        <button class="btn-secondary" @click="loadTemplates" :disabled="loadingOptions || loadingOverview">
          テンプレート更新
        </button>
        <button class="btn-secondary" @click="loadOverview" :disabled="loadingOverview || !selectedSheetCode || !selectedMonth">
          再読込
        </button>
      </div>
    </div>

    <section class="panel filter-panel">
      <label>
        ライン
        <select
          v-model="selectedLineId"
          :disabled="loadingOptions || loadingOverview || isFilterLockedForWorker"
        >
          <option value="">すべて</option>
          <option v-for="line in lineOptions" :key="line.id" :value="String(line.id)">
            {{ formatLineOptionLabel(line) }}
          </option>
        </select>
      </label>
      <label>
        工程
        <select v-model="selectedProcessId" :disabled="loadingOptions || loadingOverview || isFilterLockedForWorker">
          <option value="">すべて</option>
          <option v-for="process in filteredProcessOptions" :key="process.id" :value="String(process.id)">
            {{ formatProcessOptionLabel(process) }}
          </option>
        </select>
      </label>
      <label>
        設備
        <select v-model="selectedSheetCode" :disabled="loadingOptions || loadingOverview || isFilterLockedForWorker">
          <option value="">選択してください</option>
          <option v-for="option in templateOptions" :key="option.sheet_code" :value="option.sheet_code">
            {{ option.sheet_code }} - {{ option.sheet_name }}
          </option>
        </select>
      </label>
      <label>
        対象月
        <input type="month" v-model="selectedMonth" :disabled="loadingOverview" />
      </label>
      <div class="favorite-controls">
        <select v-model="selectedFavoriteId" @change="applyFavorite">
          <option value="">お気に入り選択</option>
          <option v-for="fav in favorites" :key="fav.id" :value="String(fav.id)">
            {{ fav.name }}
          </option>
        </select>
        <input type="text" v-model.trim="favoriteName" placeholder="お気に入り名" class="favorite-name-input" />
        <button class="btn-favorite" title="お気に入り登録" @click="saveFavorite" :disabled="loadingOverview">★</button>
      </div>
      <div class="header-status">
        <div>設備名: <strong>{{ overview?.sheet_name || "-" }}</strong></div>
        <div>現行版: <strong>v{{ overview?.current_template?.version || "-" }}</strong></div>
        <div>月間状態: <strong>{{ overview?.is_locked ? "班長確認済み" : "未確定" }}</strong></div>
      </div>
    </section>

    <section class="panel" v-if="selectedSheetCode && overview">
      <div class="week-grid">
        <div v-for="week in overview.weeks" :key="week.week_index" class="week-card">
          <div class="week-card-header">
            <div>
              <div class="week-title">週間リーダ確認 {{ week.week_index }}</div>
              <div class="week-range">{{ week.label }}</div>
            </div>
            <button
              class="btn-primary btn-sm"
              @click="upsertConfirmation('WEEKLY_LEADER', week.week_index)"
              :disabled="!canEdit || overview.is_locked"
            >
              確認登録
            </button>
          </div>
          <div class="week-stats">
            <div>完了 {{ weekCompletedCount(week) }} / {{ weekRecordCount(week) }} 件</div>
            <div>NG {{ weekNgCount(week) }} 件</div>
          </div>
          <div class="week-confirmation">
            <template v-if="findConfirmation('WEEKLY_LEADER', week.week_index)">
              <div>確認者: {{ findConfirmation('WEEKLY_LEADER', week.week_index).confirmed_by_name || "-" }}</div>
              <div>確認日時: {{ formatDateTime(findConfirmation('WEEKLY_LEADER', week.week_index).confirmed_at) }}</div>
              <div>コメント: {{ findConfirmation('WEEKLY_LEADER', week.week_index).comment || "-" }}</div>
            </template>
            <div v-else class="no-data">未確認</div>
          </div>
        </div>
      </div>

      <div class="month-confirm-card">
        <div>
          <div class="week-title">月間班長確認</div>
          <div class="week-range">{{ selectedMonth }}</div>
        </div>
        <div class="month-confirm-actions">
          <button class="btn-approve btn-sm" @click="upsertConfirmation('MONTHLY_CHIEF', 0)" :disabled="!canEdit">
            班長確認登録
          </button>
        </div>
        <div class="week-confirmation">
          <template v-if="findConfirmation('MONTHLY_CHIEF', 0)">
            <div>確認者: {{ findConfirmation('MONTHLY_CHIEF', 0).confirmed_by_name || "-" }}</div>
            <div>確認日時: {{ formatDateTime(findConfirmation('MONTHLY_CHIEF', 0).confirmed_at) }}</div>
            <div>コメント: {{ findConfirmation('MONTHLY_CHIEF', 0).comment || "-" }}</div>
          </template>
          <div v-else class="no-data">未確認</div>
        </div>
      </div>
    </section>

    <section class="panel" v-if="selectedSheetCode && overview">
      <div class="section-header">
        <h3 class="panel-title">日次点検実績</h3>
      </div>
      <div class="table-wrap">
        <table class="data-table compact">
          <thead>
            <tr>
              <th>点検日</th>
              <th>状態</th>
              <th>実施者</th>
              <th>総合判定</th>
              <th>必須未入力</th>
              <th>NG件数</th>
              <th>完了日時</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in overview.daily_records" :key="row.id">
              <td>{{ row.operation_date }}</td>
              <td>{{ statusLabel(row.status) }}</td>
              <td>{{ row.operator_name || "-" }}</td>
              <td>{{ row.overall_result || "-" }}</td>
              <td>{{ row.missing_required_count ?? 0 }}</td>
              <td>{{ row.ng_count ?? 0 }}</td>
              <td>{{ formatDateTime(row.completed_at) }}</td>
              <td>
                <RouterLink
                  class="btn-secondary btn-sm action-link"
                  :to="{
                    path: '/quality/equipment-inspection/operation',
                    query: { sheet_code: selectedSheetCode, date: row.operation_date, section_type: row.section_type },
                  }"
                >
                  開く
                </RouterLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="!overview.daily_records.length" class="no-data">日次点検実績はありません。</div>
    </section>

    <section class="panel" v-if="selectedSheetCode && overview">
      <div class="section-header">
        <h3 class="panel-title">定期実測実績</h3>
      </div>
      <div class="table-wrap">
        <table class="data-table compact">
          <thead>
            <tr>
              <th>点検日</th>
              <th>状態</th>
              <th>実施者</th>
              <th>総合判定</th>
              <th>完了日時</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in overview.quarterly_records" :key="row.id">
              <td>{{ row.operation_date }}</td>
              <td>{{ statusLabel(row.status) }}</td>
              <td>{{ row.operator_name || "-" }}</td>
              <td>{{ row.overall_result || "-" }}</td>
              <td>{{ formatDateTime(row.completed_at) }}</td>
              <td>
                <RouterLink
                  class="btn-secondary btn-sm action-link"
                  :to="{
                    path: '/quality/equipment-inspection/operation',
                    query: { sheet_code: selectedSheetCode, date: row.operation_date, section_type: row.section_type },
                  }"
                >
                  開く
                </RouterLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="!overview.quarterly_records.length" class="no-data">定期実測実績はありません。</div>
    </section>
  </div>

  <div class="page-container" v-else>
    <h2 class="page-title">月間確認</h2>
    <p class="no-data">品質の閲覧権限がありません。</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue"
import { RouterLink, useRoute, useRouter } from "vue-router"
import api from "@/api/client"
import { authState } from "@/auth"
import { hasPermission } from "@/router"
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: 't_equipment_inspection', desc: '設備点検記録・月間確認' },
]

const route = useRoute()
const router = useRouter()

const loadingOptions = ref(false)
const loadingOverview = ref(false)
const templateOptions = ref([])
const lineOptions = ref([])
const processOptions = ref([])
const overview = ref(null)

const isLeaderOrAbove = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const role = user.profile?.role || ''
  return ['leader', 'supervisor', 'chief', 'manager'].includes(role)
})
const isFilterLockedForWorker = computed(() => !isLeaderOrAbove.value)
const resolveInitialLineId = () => {
  if (route.query.line_id) return String(route.query.line_id)
  if (isLeaderOrAbove.value) return ""
  const unitLines = authState.user?.profile?.unit_lines
  if (!Array.isArray(unitLines) || !unitLines.length) return ""
  const defaultMapping = unitLines.find((item) => item?.is_default)
  const target = defaultMapping || unitLines[0]
  return target?.line_id ? String(target.line_id) : ""
}

const selectedSheetCode = ref(String(route.query.sheet_code || ""))
const selectedMonth = ref(String(route.query.month || new Date().toISOString().slice(0, 7)))
const selectedLineId = ref(resolveInitialLineId())
const selectedProcessId = ref(route.query.process_id ? String(route.query.process_id) : "")

const FAVORITE_SCREEN_KEY = 'quality.equipment_inspection_monthly_review'
const favorites = ref([])
const selectedFavoriteId = ref('')
const favoriteName = ref('')

const canAccessQuality = (resource, level = "view", aliases = []) => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  const candidates = [resource, ...aliases]
  const hasSpecific = permissions.some((item) => candidates.includes(item.resource))
  if (hasSpecific) {
    return candidates.some((candidate) => hasPermission(user, candidate, level))
  }
  return hasPermission(user, "quality", level)
}
const canView = computed(() =>
  canAccessQuality("quality.equipment_inspection_monthly_review", "view", ["quality.equipment_inspection"])
)
const canEdit = computed(() =>
  canAccessQuality("quality.equipment_inspection_monthly_review", "edit", ["quality.equipment_inspection"])
)

const filteredProcessOptions = computed(() => {
  if (!selectedLineId.value) return processOptions.value
  return processOptions.value.filter((process) => {
    const processLineId = process?.line ?? process?.line_id ?? ""
    return String(processLineId) === String(selectedLineId.value)
  })
})

const formatLineOptionLabel = (line) => {
  const code = String(line?.line_code || "").trim()
  const name = String(line?.line_name || "").trim()
  if (code && name) return `${code} - ${name}`
  return name || code || `ID:${line?.id ?? ""}`
}

const formatProcessOptionLabel = (process) => {
  const code = String(process?.process_code || "").trim()
  const name = String(process?.process_name || "").trim()
  if (code && name) return `${code} - ${name}`
  return name || code || `ID:${process?.id ?? ""}`
}

const statusLabel = (value) => {
  if (value === "COMPLETED") return "完了"
  return "下書き"
}

const formatDateTime = (value) => {
  if (!value) return "-"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString("ja-JP")
}

const syncQuery = () => {
  router.replace({
    query: {
      ...route.query,
      sheet_code: selectedSheetCode.value || undefined,
      month: selectedMonth.value || undefined,
      line_id: selectedLineId.value || undefined,
      process_id: selectedProcessId.value || undefined,
    },
  })
}

const loadFilterOptions = async () => {
  try {
    const [linesRes, processesRes] = await Promise.all([
      api.lines.getProductionLines(),
      api.processes.getProcesses(),
    ])
    lineOptions.value = Array.isArray(linesRes.data) ? linesRes.data : linesRes.data?.results || []
    processOptions.value = Array.isArray(processesRes.data) ? processesRes.data : processesRes.data?.results || []
  } catch (error) {
    console.warn("ライン/工程候補の取得に失敗:", error)
    lineOptions.value = []
    processOptions.value = []
  }
}

const loadTemplates = async () => {
  loadingOptions.value = true
  try {
    const fetchOptions = async (params) => {
      const response = await api.qualityEquipmentInspections.list({ for_operation: true, ...params })
      return response.data?.results || response.data || []
    }

    let rows = []
    if (selectedProcessId.value) {
      rows = await fetchOptions({ process_id: selectedProcessId.value })
      if (!rows.length && selectedLineId.value) {
        rows = await fetchOptions({ line_id: selectedLineId.value })
      }
    } else if (selectedLineId.value) {
      rows = await fetchOptions({ line_id: selectedLineId.value })
    } else {
      rows = await fetchOptions({})
    }

    templateOptions.value = [...rows].sort((a, b) => {
      return String(a.sheet_code || "").localeCompare(String(b.sheet_code || ""), "ja")
    })
    if (!selectedSheetCode.value && templateOptions.value.length && (selectedLineId.value || selectedProcessId.value)) {
      selectedSheetCode.value = templateOptions.value[0].sheet_code
    }
  } catch (error) {
    console.error("承認済みテンプレート取得に失敗:", error)
    alert("承認済みテンプレートの取得に失敗しました。")
  } finally {
    loadingOptions.value = false
  }
}

const loadOverview = async () => {
  if (!selectedSheetCode.value || !selectedMonth.value) return
  loadingOverview.value = true
  try {
    const response = await api.qualityEquipmentInspections.monthlyOverview({
      sheet_code: selectedSheetCode.value,
      month: selectedMonth.value,
    })
    overview.value = response.data
  } catch (error) {
    console.error("月間確認データ取得に失敗:", error)
    overview.value = null
    alert("月間確認データの取得に失敗しました。")
  } finally {
    loadingOverview.value = false
  }
}

const loadFavorites = async () => {
  try {
    const res = await api.accounts.getFavorites({ screen_key: FAVORITE_SCREEN_KEY, page_size: 200 })
    favorites.value = Array.isArray(res.data) ? res.data : res.data?.results || []
  } catch (e) {
    console.error('お気に入り取得エラー:', e)
  }
}

const toFavoritePayload = () => ({
  lineId: String(selectedLineId.value || ''),
  processId: String(selectedProcessId.value || ''),
  sheetCode: String(selectedSheetCode.value || ''),
})

const applyFavorite = async () => {
  const id = Number(selectedFavoriteId.value || 0)
  if (!id) return
  const target = favorites.value.find((item) => Number(item.id) === id)
  if (!target) return
  favoriteName.value = target.name || ''
  const payload = target.payload || {}
  selectedLineId.value = String(payload.lineId || '')
  await loadTemplates()
  selectedProcessId.value = String(payload.processId || '')
  selectedSheetCode.value = String(payload.sheetCode || '')
}

const saveFavorite = async () => {
  const name = String(favoriteName.value || '').trim()
  if (!name) {
    alert('お気に入り名を入力してください。')
    return
  }
  try {
    const id = Number(selectedFavoriteId.value || 0)
    const data = { screen_key: FAVORITE_SCREEN_KEY, name, payload: toFavoritePayload() }
    if (id) {
      await api.accounts.updateFavorite(id, data)
    } else {
      await api.accounts.createFavorite(data)
    }
    await loadFavorites()
    const found = favorites.value.find((item) => item.name === name)
    selectedFavoriteId.value = found ? String(found.id) : ''
    alert('お気に入りを保存しました。')
  } catch (e) {
    alert(`お気に入り保存エラー: ${e?.response?.data?.detail || e?.message || '保存に失敗しました。'}`)
  }
}

const findConfirmation = (type, weekIndex) => {
  if (!overview.value?.confirmations?.length) return null
  return (
    overview.value.confirmations.find(
      (item) => item.confirm_type === type && Number(item.week_index || 0) === Number(weekIndex || 0)
    ) || null
  )
}

const dateInWeek = (value, week) => {
  if (!value || !week) return false
  return value >= week.start_date && value <= week.end_date
}

const weekRecords = (week) => {
  return (overview.value?.daily_records || []).filter((row) => dateInWeek(row.operation_date, week))
}

const weekRecordCount = (week) => weekRecords(week).length
const weekCompletedCount = (week) => weekRecords(week).filter((row) => row.status === "COMPLETED").length
const weekNgCount = (week) => weekRecords(week).reduce((sum, row) => sum + Number(row.ng_count || 0), 0)

const upsertConfirmation = async (type, weekIndex) => {
  if (!selectedSheetCode.value || !selectedMonth.value) return
  const current = findConfirmation(type, weekIndex)
  const label = type === "MONTHLY_CHIEF" ? "月間班長確認" : `週間リーダ確認 ${weekIndex}`
  const comment = window.prompt(`${label}コメントを入力してください。`, current?.comment || "")
  if (comment === null) return

  try {
    await api.qualityEquipmentInspections.upsertConfirmation({
      sheet_code: selectedSheetCode.value,
      sheet_name: overview.value?.sheet_name || "",
      target_month: selectedMonth.value,
      confirm_type: type,
      week_index: weekIndex,
      comment,
    })
    await loadOverview()
    alert(`${label}を登録しました。`)
  } catch (error) {
    console.error("確認登録に失敗:", error)
    alert(error.response?.data?.detail || "確認登録に失敗しました。")
  }
}

watch([selectedSheetCode, selectedMonth], async () => {
  if (!canView.value) return
  syncQuery()
  if (selectedSheetCode.value && selectedMonth.value) {
    await loadOverview()
  }
})

watch([selectedLineId, selectedProcessId], async () => {
  if (!canView.value) return
  syncQuery()
  selectedSheetCode.value = ""
  overview.value = null
  await loadTemplates()
})

watch(selectedLineId, (lineId) => {
  if (!lineId) return
  if (!selectedProcessId.value) return
  const exists = filteredProcessOptions.value.some((process) => String(process.id) === String(selectedProcessId.value))
  if (!exists) {
    selectedProcessId.value = ""
  }
})

onMounted(async () => {
  if (!canView.value) return
  await loadFilterOptions()
  loadFavorites()
  await loadTemplates()
  if (selectedSheetCode.value && selectedMonth.value) {
    await loadOverview()
  }
})
</script>

<style scoped>
.inspection-monthly-review {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.panel {
  background: #fff;
  border: 1px solid #d5d8dc;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.filter-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
  align-items: end;
}
.filter-panel label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: #334155;
}
.favorite-controls {
  display: flex;
  gap: 6px;
  align-items: end;
}
.favorite-controls select {
  flex: 1;
  min-width: 100px;
}
.favorite-name-input {
  width: 100px !important;
}
.btn-favorite {
  padding: 5px 10px;
  background: #facc15;
  color: #78350f;
  border: 1px solid #eab308;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 700;
  min-width: 34px;
  white-space: nowrap;
}
.btn-favorite:hover {
  background: #eab308;
}
.btn-favorite:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.header-status {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: #0f172a;
  font-size: 13px;
}
.week-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}
.week-card,
.month-confirm-card {
  border: 1px solid #d7dde7;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.week-card-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}
.week-title {
  font-weight: 700;
  color: #0f172a;
}
.week-range {
  color: #64748b;
  font-size: 12px;
  margin-top: 4px;
}
.week-stats {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: #334155;
}
.week-confirmation {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: #334155;
}
.month-confirm-card {
  background: #f8fafc;
}
.month-confirm-actions {
  display: flex;
  justify-content: flex-end;
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.table-wrap {
  overflow: auto;
  border: 1px solid #dde2ea;
  border-radius: 6px;
}
.data-table.compact {
  width: 100%;
  border-collapse: collapse;
}
.data-table.compact th,
.data-table.compact td {
  border: 1px solid #dde2ea;
  padding: 6px 8px;
  vertical-align: top;
  font-size: 13px;
  color: #0f172a;
}
.data-table.compact thead th {
  background: #f8fafc;
}
.action-link {
  text-decoration: none;
  display: inline-block;
}
input,
select {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 5px 6px;
  font-size: 13px;
  background: #fff;
}
.btn-primary,
.btn-secondary,
.btn-approve {
  border: 1px solid transparent;
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 12px;
  cursor: pointer;
}
.btn-primary {
  background: #2563eb;
  color: #fff;
}
.btn-secondary {
  background: #f1f5f9;
  color: #334155;
  border-color: #cbd5e1;
}
.btn-approve {
  background: #16a34a;
  color: #fff;
}
.btn-sm {
  padding: 4px 8px;
}
button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
@media (max-width: 1100px) {
  .filter-panel {
    grid-template-columns: repeat(3, minmax(140px, 1fr));
  }
}
@media (max-width: 720px) {
  .filter-panel {
    grid-template-columns: 1fr;
  }
}
</style>

