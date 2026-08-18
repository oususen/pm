<template>
  <div class="master-menu daily-review-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ pageTitle }}</h2>
        <p class="helper-text">{{ pageHelperText }}</p>
      </div>
      <button class="btn-secondary" @click="loadData" :disabled="loading">{{ loading ? "更新中..." : "更新" }}</button>
    </div>

    <div v-if="error" class="helper-text error-text">{{ error }}</div>

    <div class="tab-bar">
      <button type="button" class="tab-button" :class="{ active: activeTab === 'daily' }" @click="activeTab = 'daily'">日次</button>
      <button type="button" class="tab-button" :class="{ active: activeTab === 'weekly' }" @click="activeTab = 'weekly'">週次</button>
      <button type="button" class="tab-button" :class="{ active: activeTab === 'monthly' }" @click="activeTab = 'monthly'">月次</button>
    </div>

    <div class="prepare-form filter-form">
      <label>
        <span class="field-label">ライン</span>
        <select v-model="selectedLine">
          <option value="">すべて</option>
          <option v-for="v in lineOptions" :key="`line-opt-${v}`" :value="v">{{ v }}</option>
        </select>
      </label>
      <label>
        <span class="field-label">工程</span>
        <select v-model="selectedProcess">
          <option value="">すべて</option>
          <option v-for="v in processOptions" :key="`proc-opt-${v}`" :value="v">{{ v }}</option>
        </select>
      </label>
      <label>
        <span class="field-label">製品</span>
        <select v-model="selectedProduct">
          <option value="">すべて</option>
          <option v-for="v in productOptions" :key="`prod-opt-${v}`" :value="v">{{ v }}</option>
        </select>
      </label>
      <label>
        <span class="field-label">項目</span>
        <select v-model="selectedItem" :disabled="!isItemSelectable">
          <option value="">すべて</option>
          <option v-for="v in itemOptions" :key="`item-opt-${v}`" :value="v">{{ v }}</option>
        </select>
      </label>
      <label class="field-worker">
        <span class="field-label">作業者</span>
        <select v-model="selectedPerson">
          <option value="">すべて</option>
          <option v-for="v in personOptions" :key="`person-opt-${v}`" :value="v">{{ v }}</option>
        </select>
      </label>
      <label class="field-unit">
        <span class="field-label">台目</span>
        <select v-model="selectedUnit">
          <option value="">すべて</option>
          <option v-for="v in unitOptions" :key="`unit-opt-${v}`" :value="v">{{ v }}</option>
        </select>
      </label>
      <label>
        <span class="field-label">開始日</span>
        <input v-model="startDate" type="date" />
      </label>
      <label>
        <span class="field-label">終了日</span>
        <input v-model="endDate" type="date" />
      </label>
      <label class="check-label">
        <input v-model="showOnlyReworkRows" type="checkbox" />
        <span>修正流動ありのみ表示</span>
      </label>
      <label>
        <span class="field-label">集計種別</span>
        <select v-model="aggregationMode">
          <option value="record">件数別</option>
          <option value="unit">台数別</option>
        </select>
      </label>
      <label>
        <span class="field-label">お気に入り</span>
        <select v-model="selectedFavoriteId" @change="applyFavorite">
          <option value="">-- 選択 --</option>
          <option v-for="fav in favorites" :key="fav.id" :value="String(fav.id)">{{ fav.name }}</option>
        </select>
      </label>
      <label>
        <span class="field-label">登録名</span>
        <input v-model.trim="favoriteName" type="text" placeholder="お気に入り名" />
      </label>
      <button class="btn favorite-star-btn" title="お気に入り登録" :disabled="loading" @click="saveFavorite">★</button>
    </div>

    <section class="summary-grid">
      <div class="summary-card">
        <div class="summary-label">{{ totalLabel }}</div>
        <div class="summary-value">{{ summaryCards.total }}</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">判定台数</div>
        <div class="summary-value">{{ summaryCards.unitCount }}</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">{{ reworkLabel }}</div>
        <div class="summary-value accent-rework">{{ summaryCards.rework }}</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">修正流動率</div>
        <div class="summary-value accent-rework">{{ summaryCards.reworkRate }}%</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">{{ ngLabel }}</div>
        <div class="summary-value accent-ng">{{ summaryCards.ng }}</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">NG率</div>
        <div class="summary-value accent-ng">{{ summaryCards.ngRate }}%</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">修正流動発生日数</div>
        <div class="summary-value">{{ summaryCards.reworkDays }}</div>
      </div>
    </section>

    <section class="panel">
      <div class="section-head">
        <h3 class="section-title">{{ chartTitle }}</h3>
        <span class="section-note">{{ chartNote }}</span>
      </div>
      <div class="chart-wrap">
        <canvas ref="dailyTrendChartRef"></canvas>
      </div>
      <div v-if="!currentTrendRows.length" class="empty-cell">対象データがありません。</div>
    </section>

    <section class="panel">
      <div class="section-head">
        <h3 class="section-title">{{ summarySectionTitle }}</h3>
        <span class="section-note">修正流動率の高い{{ periodLabel }}が上に来ます</span>
      </div>
      <div class="table-wrap">
        <table class="data-table compact">
          <thead>
            <tr>
              <th>{{ periodLabel }}</th>
              <th>{{ totalLabel }}</th>
              <th>{{ reworkLabel }}</th>
              <th>修正流動率</th>
              <th>{{ ngLabel }}</th>
              <th>NG率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in currentSummaryRows" :key="`summary-${activeTab}-${row.periodKey}`">
              <td>{{ row.periodLabel }}</td>
              <td>{{ row.total }}</td>
              <td>{{ row.reworkCount }}</td>
              <td :class="rateClass(row.reworkRate)">{{ row.reworkRate.toFixed(1) }}%</td>
              <td>{{ row.ngCount }}</td>
              <td>{{ row.ngRate.toFixed(1) }}%</td>
            </tr>
            <tr v-if="!currentSummaryRows.length">
              <td colspan="6" class="empty-cell">対象データがありません。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <div class="section-head">
        <h3 class="section-title">ワースト製品</h3>
        <span class="section-note">修正流動率が高い製品順です</span>
      </div>
      <div class="table-wrap">
        <table class="data-table compact">
          <thead>
            <tr>
              <th>順位</th>
              <th>製品</th>
              <th>{{ periodLabel }}</th>
              <th>{{ totalLabel }}</th>
              <th>{{ reworkLabel }}</th>
              <th>修正流動率</th>
              <th>{{ ngLabel }}</th>
              <th>NG率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in currentWorstProductRows" :key="`worst-${activeTab}-${row.periodKey}-${row.product}`">
              <td>{{ index + 1 }}</td>
              <td>{{ row.product }}</td>
              <td>{{ row.periodLabel }}</td>
              <td>{{ row.total }}</td>
              <td>{{ row.reworkCount }}</td>
              <td :class="rateClass(row.reworkRate)">{{ row.reworkRate.toFixed(1) }}%</td>
              <td>{{ row.ngCount }}</td>
              <td>{{ row.ngRate.toFixed(1) }}%</td>
            </tr>
            <tr v-if="!currentWorstProductRows.length">
              <td colspan="8" class="empty-cell">対象データがありません。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <div class="section-head">
        <h3 class="section-title">ライン / 工程 / 製品 / {{ periodLabel }} 別詳細</h3>
        <span class="section-note">{{ detailSectionNote }}</span>
      </div>
      <div class="table-wrap">
        <table class="data-table compact detailed-table">
          <thead>
            <tr>
              <th>{{ periodLabel }}</th>
              <th>ライン</th>
              <th>工程</th>
              <th>製品</th>
              <th>{{ totalLabel }}</th>
              <th>{{ reworkLabel }}</th>
              <th>修正流動率</th>
              <th>{{ ngLabel }}</th>
              <th>NG率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in currentDetailRows" :key="detailKey(row)">
              <td>{{ row.periodLabel }}</td>
              <td>{{ row.line }}</td>
              <td>{{ row.process }}</td>
              <td>{{ row.product }}</td>
              <td>{{ row.total }}</td>
              <td>{{ row.reworkCount }}</td>
              <td :class="rateClass(row.reworkRate)">{{ row.reworkRate.toFixed(1) }}%</td>
              <td>{{ row.ngCount }}</td>
              <td>{{ row.ngRate.toFixed(1) }}%</td>
            </tr>
            <tr v-if="!currentDetailRows.length">
              <td colspan="9" class="empty-cell">対象データがありません。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue"
import {
  BarController,
  BarElement,
  CategoryScale,
  Chart,
  Legend,
  LineController,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
} from "chart.js"
import api from "@/api/client"

Chart.register(
  BarController,
  BarElement,
  CategoryScale,
  LineController,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
  Legend,
)

const loading = ref(false)
const error = ref("")
const allRecords = ref([])
const templateDefinitions = ref([])
const TEMPLATE_FETCH_CHUNK_SIZE = 10
const selectedLine = ref("")
const selectedProcess = ref("")
const selectedProduct = ref("")
const selectedItem = ref("")
const selectedPerson = ref("")
const selectedUnit = ref("")
const startDate = ref("")
const endDate = ref("")
const showOnlyReworkRows = ref(true)
const aggregationMode = ref("unit")
const favorites = ref([])
const selectedFavoriteId = ref("")
const favoriteName = ref("")
const activeTab = ref("daily")
const dailyTrendChartRef = ref(null)
let dailyTrendChart = null

const FAVORITE_SCREEN_KEY = "quality.product_checksheet_integrated_weekly_monthly"

const toArray = (data) => data?.results || data || []
const isValidDateText = (value) => /^\d{4}-\d{2}-\d{2}$/.test(String(value || ""))
const uniqueSorted = (rows, key) => [...new Set(rows.map((r) => r[key] || "未設定"))].sort((a, b) => String(a).localeCompare(String(b), "ja"))
const buildMonthStartText = () => {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, "0")
  return `${year}-${month}-01`
}
const parseDateText = (value) => {
  const [year, month, day] = String(value || "").split("-").map(Number)
  if (!year || !month || !day) return null
  return new Date(year, month - 1, day)
}
const formatDate = (date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}
const buildPeriodInfo = (dateText, tab) => {
  const date = parseDateText(dateText)
  if (!date) {
    return { key: String(dateText || ""), label: String(dateText || ""), sortKey: String(dateText || "") }
  }
  if (tab === "monthly") {
    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`
    return { key, label: key, sortKey: key }
  }
  if (tab === "weekly") {
    const day = date.getDay()
    const diffToMonday = day === 0 ? -6 : 1 - day
    const weekStart = new Date(date)
    weekStart.setDate(date.getDate() + diffToMonday)
    const weekEnd = new Date(weekStart)
    weekEnd.setDate(weekStart.getDate() + 6)
    const startText = formatDate(weekStart)
    const endText = formatDate(weekEnd)
    return { key: startText, label: `${startText}～${endText}`, sortKey: startText }
  }
  return { key: String(dateText || ""), label: String(dateText || ""), sortKey: String(dateText || "") }
}
const buildUnitKey = (record) => {
  if (record.unitId) return `unit:${record.unitId}`
  return `${record.dateText}-${record.line}-${record.process}-${record.product}-${record.unit}`
}
const totalLabel = computed(() => aggregationMode.value === "unit" ? "判定台数" : "判定総数")
const reworkLabel = computed(() => aggregationMode.value === "unit" ? "修正流動台数" : "修正流動件数")
const ngLabel = computed(() => aggregationMode.value === "unit" ? "NG台数" : "NG件数")
const tabName = computed(() => {
  if (activeTab.value === "weekly") return "週次"
  if (activeTab.value === "monthly") return "月次"
  return "日次"
})
const periodLabel = computed(() => {
  if (activeTab.value === "weekly") return "週"
  if (activeTab.value === "monthly") return "月"
  return "日付"
})
const pageTitle = computed(() => `${tabName.value}修正流動確認`)
const pageHelperText = computed(() => `工程一体チェックシート実績から、ライン / 工程 / 製品 / ${periodLabel.value}単位で修正流動を確認します。`)
const chartTitle = computed(() => `${tabName.value}修正流動率推移`)
const chartNote = computed(() => `横軸は${activeTab.value === "daily" ? "稼働日" : periodLabel.value}、左軸は台数、右軸は修正流動率です`)
const summarySectionTitle = computed(() => `${tabName.value}サマリー`)
const detailSectionNote = computed(() => `${tabName.value}の発生源をそのまま見ます`)

const filteredTemplateDefinitions = computed(() => templateDefinitions.value.filter((row) => {
  if (selectedLine.value && row.line !== selectedLine.value) return false
  if (selectedProduct.value && row.product !== selectedProduct.value) return false
  if (selectedProcess.value && row.process !== selectedProcess.value) return false
  return true
}))

const selectedTemplateIds = computed(() => {
  const ids = new Set(filteredTemplateDefinitions.value.map((row) => Number(row.templateId || 0)).filter((id) => id > 0))
  return ids
})

const lineOptions = computed(() => uniqueSorted(templateDefinitions.value, "line"))
const processOptions = computed(() => uniqueSorted(
  templateDefinitions.value.filter((row) => {
    if (selectedLine.value && row.line !== selectedLine.value) return false
    if (selectedProduct.value && row.product !== selectedProduct.value) return false
    return true
  }),
  "process",
))
const productOptions = computed(() => uniqueSorted(
  templateDefinitions.value.filter((row) => {
    if (selectedLine.value && row.line !== selectedLine.value) return false
    if (selectedProcess.value && row.process !== selectedProcess.value) return false
    return true
  }),
  "product",
))
const personOptions = computed(() => uniqueSorted(allRecords.value, "person"))
const unitOptions = computed(() => uniqueSorted(allRecords.value, "unit"))
const isItemSelectable = computed(() => Boolean(selectedProduct.value) && Boolean(selectedProcess.value))
const itemOptions = computed(() => {
  if (!isItemSelectable.value) return []
  return uniqueSorted(filteredTemplateDefinitions.value, "itemName")
})

const filteredRecords = computed(() => allRecords.value.filter((r) => {
  if (startDate.value && r.dateText < startDate.value) return false
  if (endDate.value && r.dateText > endDate.value) return false
  if (selectedLine.value && r.line !== selectedLine.value) return false
  if (selectedProcess.value && r.process !== selectedProcess.value) return false
  if (selectedProduct.value && r.product !== selectedProduct.value) return false
  if (selectedItem.value && r.itemName !== selectedItem.value) return false
  if (selectedPerson.value && r.person !== selectedPerson.value) return false
  if (selectedUnit.value && r.unit !== selectedUnit.value) return false
  return true
}))

const buildGroupedRows = (records, keyBuilder, seedBuilder) => {
  const map = new Map()
  records.forEach((r) => {
    const key = keyBuilder(r)
    if (!map.has(key)) map.set(key, seedBuilder(r))
    const obj = map.get(key)
    if (aggregationMode.value === "unit") {
      obj.totalUnits.add(buildUnitKey(r))
      if (r.isRework) obj.reworkUnits.add(buildUnitKey(r))
      if (r.isNg) obj.ngUnits.add(buildUnitKey(r))
    } else {
      obj.total += 1
      if (r.isRework) obj.reworkCount += 1
      if (r.isNg) obj.ngCount += 1
    }
  })
  return [...map.values()].map((row) => {
    if (aggregationMode.value === "unit") {
      row.total = row.totalUnits.size
      row.reworkCount = row.reworkUnits.size
      row.ngCount = row.ngUnits.size
    }
    const ngBase = row.total - row.reworkCount
    return {
      ...row,
      reworkRate: row.total > 0 ? (row.reworkCount / row.total) * 100 : 0,
      ngRate: ngBase > 0 ? (row.ngCount / ngBase) * 100 : 0,
    }
  })
}

const groupedDetailRows = computed(() => buildGroupedRows(
  filteredRecords.value,
  (r) => `${buildPeriodInfo(r.dateText, activeTab.value).key}__${r.line}__${r.process}__${r.product}`,
  (r) => ({
    periodKey: buildPeriodInfo(r.dateText, activeTab.value).key,
    periodLabel: buildPeriodInfo(r.dateText, activeTab.value).label,
    sortKey: buildPeriodInfo(r.dateText, activeTab.value).sortKey,
    line: r.line,
    process: r.process,
    product: r.product,
    total: 0,
    reworkCount: 0,
    ngCount: 0,
    totalUnits: new Set(),
    reworkUnits: new Set(),
    ngUnits: new Set(),
  }),
))

const detailRows = computed(() => {
  const rows = groupedDetailRows.value
    .filter((row) => !showOnlyReworkRows.value || row.reworkCount > 0)
    .sort((a, b) => {
      if (b.reworkRate !== a.reworkRate) return b.reworkRate - a.reworkRate
      if (b.reworkCount !== a.reworkCount) return b.reworkCount - a.reworkCount
      if (a.sortKey !== b.sortKey) return String(b.sortKey).localeCompare(String(a.sortKey), "ja")
      if (a.line !== b.line) return String(a.line).localeCompare(String(b.line), "ja")
      if (a.process !== b.process) return String(a.process).localeCompare(String(b.process), "ja")
      return String(a.product).localeCompare(String(b.product), "ja")
    })
  return rows
})

const dailySummaryBaseRows = computed(() => {
  const rows = buildGroupedRows(
    filteredRecords.value,
    (r) => buildPeriodInfo(r.dateText, activeTab.value).key,
    (r) => ({
      periodKey: buildPeriodInfo(r.dateText, activeTab.value).key,
      periodLabel: buildPeriodInfo(r.dateText, activeTab.value).label,
      sortKey: buildPeriodInfo(r.dateText, activeTab.value).sortKey,
      total: 0,
      reworkCount: 0,
      ngCount: 0,
      totalUnits: new Set(),
      reworkUnits: new Set(),
      ngUnits: new Set(),
    }),
  )
  return rows.sort((a, b) => {
    if (b.reworkRate !== a.reworkRate) return b.reworkRate - a.reworkRate
    if (b.reworkCount !== a.reworkCount) return b.reworkCount - a.reworkCount
    return String(b.sortKey).localeCompare(String(a.sortKey), "ja")
  })
})

const dailySummaryRows = computed(() => {
  return dailySummaryBaseRows.value
    .filter((row) => !showOnlyReworkRows.value || row.reworkCount > 0)
})

const groupedProductRows = computed(() => buildGroupedRows(
  filteredRecords.value,
  (r) => `${buildPeriodInfo(r.dateText, activeTab.value).key}__${r.product}`,
  (r) => ({
    periodKey: buildPeriodInfo(r.dateText, activeTab.value).key,
    periodLabel: buildPeriodInfo(r.dateText, activeTab.value).label,
    sortKey: buildPeriodInfo(r.dateText, activeTab.value).sortKey,
    product: r.product,
    total: 0,
    reworkCount: 0,
    ngCount: 0,
    totalUnits: new Set(),
    reworkUnits: new Set(),
    ngUnits: new Set(),
  }),
))

const worstProductRows = computed(() => groupedProductRows.value
  .filter((row) => !showOnlyReworkRows.value || row.reworkCount > 0)
  .sort((a, b) => {
    if (b.reworkRate !== a.reworkRate) return b.reworkRate - a.reworkRate
    if (b.reworkCount !== a.reworkCount) return b.reworkCount - a.reworkCount
    if (a.sortKey !== b.sortKey) return String(b.sortKey).localeCompare(String(a.sortKey), "ja")
    if (b.total !== a.total) return b.total - a.total
    return String(a.product).localeCompare(String(b.product), "ja")
  })
  .slice(0, 10))

const dailyTrendRows = computed(() => {
  const dayMap = new Map()
  filteredRecords.value.forEach((record) => {
    const period = buildPeriodInfo(record.dateText, activeTab.value)
    const key = period.key
    if (!key) return
    if (!dayMap.has(key)) {
      dayMap.set(key, {
        periodKey: period.key,
        periodLabel: period.label,
        sortKey: period.sortKey,
        totalUnits: new Set(),
        reworkUnits: new Set(),
      })
    }
    const row = dayMap.get(key)
    const unitKey = buildUnitKey(record)
    row.totalUnits.add(unitKey)
    if (record.isRework) row.reworkUnits.add(unitKey)
  })
  return [...dayMap.values()]
    .map((row) => {
      const total = row.totalUnits.size
      const rework = row.reworkUnits.size
      return {
        periodKey: row.periodKey,
        periodLabel: row.periodLabel,
        sortKey: row.sortKey,
        total,
        rework,
        rate: total > 0 ? (rework / total) * 100 : 0,
      }
    })
    .filter((row) => row.total > 0)
    .sort((a, b) => String(a.sortKey).localeCompare(String(b.sortKey), "ja"))
})

const summarySourceRecords = computed(() => {
  if (!showOnlyReworkRows.value) return filteredRecords.value
  const visiblePeriods = new Set(dailySummaryRows.value.map((row) => row.periodKey))
  return filteredRecords.value.filter((record) => visiblePeriods.has(buildPeriodInfo(record.dateText, activeTab.value).key))
})

const currentSummaryRows = computed(() => dailySummaryRows.value)
const currentWorstProductRows = computed(() => worstProductRows.value)
const currentDetailRows = computed(() => detailRows.value)
const currentTrendRows = computed(() => dailyTrendRows.value)

const summaryCards = computed(() => {
  const records = summarySourceRecords.value
  const unitKeys = records.map((record) => buildUnitKey(record))
  const unitCount = new Set(unitKeys).size
  const total = aggregationMode.value === "unit" ? unitCount : records.length
  const rework = aggregationMode.value === "unit"
    ? new Set(records.filter((r) => r.isRework).map((r) => buildUnitKey(r))).size
    : records.filter((r) => r.isRework).length
  const ng = aggregationMode.value === "unit"
    ? new Set(records.filter((r) => r.isNg).map((r) => buildUnitKey(r))).size
    : records.filter((r) => r.isNg).length
  const ngBase = total - rework
  const reworkDays = new Set(records.filter((r) => r.isRework).map((r) => r.dateText)).size
  return {
    total,
    unitCount,
    rework,
    reworkRate: total > 0 ? ((rework / total) * 100).toFixed(1) : "0.0",
    ng,
    ngRate: ngBase > 0 ? ((ng / ngBase) * 100).toFixed(1) : "0.0",
    reworkDays,
  }
})

const toFavoritePayload = () => ({
  selectedLine: String(selectedLine.value || ""),
  selectedProcess: String(selectedProcess.value || ""),
  selectedProduct: String(selectedProduct.value || ""),
  selectedItem: String(selectedItem.value || ""),
  selectedPerson: String(selectedPerson.value || ""),
  selectedUnit: String(selectedUnit.value || ""),
  startDate: isValidDateText(startDate.value) ? String(startDate.value) : "",
  endDate: isValidDateText(endDate.value) ? String(endDate.value) : "",
  showOnlyReworkRows: Boolean(showOnlyReworkRows.value),
  aggregationMode: String(aggregationMode.value || "unit"),
  activeTab: String(activeTab.value || "daily"),
})

const applyFavoritePayload = (payload) => {
  selectedLine.value = String(payload?.selectedLine || "")
  selectedProcess.value = String(payload?.selectedProcess || "")
  selectedProduct.value = String(payload?.selectedProduct || "")
  selectedItem.value = String(payload?.selectedItem || "")
  selectedPerson.value = String(payload?.selectedPerson || "")
  selectedUnit.value = String(payload?.selectedUnit || "")
  startDate.value = isValidDateText(payload?.startDate) ? String(payload.startDate) : ""
  endDate.value = isValidDateText(payload?.endDate) ? String(payload.endDate) : ""
  showOnlyReworkRows.value = payload?.showOnlyReworkRows !== false
  aggregationMode.value = payload?.aggregationMode === "record" ? "record" : "unit"
  activeTab.value = payload?.activeTab === "weekly" || payload?.activeTab === "monthly" ? payload.activeTab : "daily"
}

const loadFavorites = async () => {
  try {
    const res = await api.accounts.getFavorites({ screen_key: FAVORITE_SCREEN_KEY, page_size: 200 })
    favorites.value = Array.isArray(res.data) ? res.data : res.data?.results || []
  } catch (e) {
    console.error("お気に入り取得失敗:", e)
  }
}

const applyFavorite = () => {
  const id = Number(selectedFavoriteId.value || 0)
  if (!id) return
  const target = favorites.value.find((item) => Number(item.id) === id)
  if (!target) return
  favoriteName.value = target.name || ""
  applyFavoritePayload(target.payload || {})
}

const saveFavorite = async () => {
  const name = String(favoriteName.value || "").trim()
  if (!name) {
    window.alert("お気に入り名を入力してください。")
    return
  }
  const payload = { screen_key: FAVORITE_SCREEN_KEY, name, payload: toFavoritePayload() }
  try {
    const id = Number(selectedFavoriteId.value || 0)
    if (id) await api.accounts.updateFavorite(id, payload)
    else await api.accounts.createFavorite(payload)
    await loadFavorites()
    const found = favorites.value.find((item) => item.name === name)
    selectedFavoriteId.value = found ? String(found.id) : ""
    window.alert("お気に入りを保存しました。")
  } catch (e) {
    const detail = e?.response?.data?.detail || e?.message || "保存に失敗しました。"
    window.alert(`お気に入り保存エラー: ${detail}`)
  }
}

const loadTemplatesChunked = async (templateIds) => {
  const results = []
  for (let i = 0; i < templateIds.length; i += TEMPLATE_FETCH_CHUNK_SIZE) {
    const chunk = templateIds.slice(i, i + TEMPLATE_FETCH_CHUNK_SIZE)
    const chunkResults = await Promise.all(chunk.map((id) => api.integratedChecksheets.getTemplate(id)))
    results.push(...chunkResults)
  }
  return results
}

const loadTemplateDefinitions = async () => {
  try {
    const res = await api.integratedChecksheets.listTemplates({ page_size: 500 })
    const templates = toArray(res.data)
    const templateIds = templates.map((template) => Number(template.id || 0)).filter((id) => id > 0)
    const templateResList = await loadTemplatesChunked(templateIds)
    const rows = []
    templateResList.forEach((response) => {
      const template = response.data
      const line = template?.line_code || "未設定"
      const product = template?.product_code || "未設定"
      ;(template?.process_blocks || []).forEach((block) => {
        const process = block.process_name || block.process_code || `工程${block.id}`
        if (!block.items?.length) {
          rows.push({
            templateId: Number(template.id || 0),
            line,
            lineId: template?.line || null,
            product,
            productId: template?.product || null,
            process,
            itemName: "未設定項目",
          })
          return
        }
        block.items.forEach((item) => {
          rows.push({
            templateId: Number(template.id || 0),
            line,
            lineId: template?.line || null,
            product,
            productId: template?.product || null,
            process,
            itemName: item.item_name || "未設定項目",
          })
        })
      })
    })
    templateDefinitions.value = rows
  } catch (e) {
    console.error("テンプレート定義取得失敗:", e)
  }
}

const loadData = async () => {
  loading.value = true
  error.value = ""
  try {
    if ((selectedLine.value || selectedProduct.value || selectedProcess.value) && !selectedTemplateIds.value.size) {
      allRecords.value = []
      return
    }

    const matchedDefinitions = filteredTemplateDefinitions.value
    const batchParams = { page_size: 200 }
    if (startDate.value) batchParams.plan_date__gte = startDate.value
    if (endDate.value) batchParams.plan_date__lte = endDate.value
    if (selectedLine.value) {
      const lineId = matchedDefinitions.find((row) => row.line === selectedLine.value)?.lineId
      if (lineId) batchParams.line = lineId
    }
    if (selectedProduct.value) {
      const productId = matchedDefinitions.find((row) => row.product === selectedProduct.value)?.productId
      if (productId) batchParams.product = productId
    }

    if (selectedProcess.value) batchParams.process_name = selectedProcess.value
    if (selectedItem.value) batchParams.item_name = selectedItem.value
    if (selectedPerson.value) batchParams.checked_by_name = selectedPerson.value
    if (selectedUnit.value) batchParams.unit_sequence_no = selectedUnit.value
    batchParams.business_date__gte = startDate.value || ""
    batchParams.business_date__lte = endDate.value || ""

    const res = await api.integratedChecksheets.getAnalyticsRecords(batchParams)
    allRecords.value = toArray(res.data).map((row) => ({
      dateText: row.date_text || "",
      line: row.line || "未設定",
      process: row.process || "未設定",
      product: row.product || "未設定",
      person: row.person || "未設定",
      unitId: Number(row.unit_id || 0),
      unit: String(row.unit || "未設定"),
      itemName: row.item_name || "未設定項目",
      isNg: Boolean(row.is_ng),
      isRework: Boolean(row.is_rework),
    }))
  } catch (e) {
    error.value = `集計に失敗しました: ${e.response?.data?.detail || e.message}`
  } finally {
    loading.value = false
  }
}

const renderDailyTrendChart = async () => {
  await nextTick()
  if (!dailyTrendChartRef.value) return
  if (dailyTrendChart) {
    dailyTrendChart.destroy()
    dailyTrendChart = null
  }
  if (!currentTrendRows.value.length) return

  dailyTrendChart = new Chart(dailyTrendChartRef.value, {
    data: {
      labels: currentTrendRows.value.map((row) => row.periodLabel),
      datasets: [
        {
          type: "bar",
          label: "総台数",
          data: currentTrendRows.value.map((row) => row.total),
          backgroundColor: "#2563ebcc",
          borderColor: "#2563eb",
          borderWidth: 1,
          yAxisID: "yUnits",
          order: 2,
        },
        {
          type: "bar",
          label: "修正流動数",
          data: currentTrendRows.value.map((row) => row.rework),
          backgroundColor: "#dc2626cc",
          borderColor: "#dc2626",
          borderWidth: 1,
          yAxisID: "yUnits",
          order: 2,
        },
        {
          type: "line",
          label: "修正流動率",
          data: currentTrendRows.value.map((row) => row.rate),
          borderColor: "#7c3aed",
          backgroundColor: "#7c3aed",
          pointBackgroundColor: "#7c3aed",
          pointRadius: 3,
          tension: 0.2,
          yAxisID: "yRate",
          order: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false,
      },
      plugins: {
        legend: {
          position: "top",
        },
      },
      scales: {
        x: {
          ticks: {
            maxRotation: 45,
            minRotation: 45,
          },
        },
        yUnits: {
          type: "linear",
          position: "left",
          beginAtZero: true,
          title: {
            display: true,
            text: "台数",
          },
        },
        yRate: {
          type: "linear",
          position: "right",
          beginAtZero: true,
          grid: {
            drawOnChartArea: false,
          },
          title: {
            display: true,
            text: "修正流動率(%)",
          },
          ticks: {
            callback: (value) => `${value}%`,
          },
        },
      },
    },
  })
}

const detailKey = (row) => `${row.periodKey}-${row.line}-${row.process}-${row.product}`
const rateClass = (rateValue) => {
  if (rateValue >= 10) return "rate-danger"
  if (rateValue >= 3) return "rate-warn"
  if (rateValue > 0) return "rate-has"
  return ""
}

onMounted(async () => {
  startDate.value = buildMonthStartText()
  await Promise.all([loadFavorites(), loadTemplateDefinitions()])
})

watch([selectedProduct, selectedProcess], () => {
  if (!isItemSelectable.value) selectedItem.value = ""
})

watch(currentTrendRows, () => {
  renderDailyTrendChart()
}, { deep: true })

watch(activeTab, () => {
  renderDailyTrendChart()
})

onUnmounted(() => {
  if (dailyTrendChart) {
    dailyTrendChart.destroy()
    dailyTrendChart = null
  }
})
</script>

<style scoped>
.daily-review-page {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.error-text {
  color: #b91c1c;
  font-weight: 700;
}

.tab-bar {
  display: flex;
  gap: 8px;
}

.tab-button {
  padding: 8px 14px;
  border: 1px solid #cbd5e1;
  border-radius: 8px 8px 0 0;
  background: #f8fafc;
  color: #334155;
  font-weight: 700;
  cursor: pointer;
}

.tab-button.active {
  border-color: #2563eb;
  background: #2563eb;
  color: #fff;
}

.prepare-form {
  display: flex;
  flex-wrap: wrap;
  align-items: end;
  gap: 8px;
}

.prepare-form label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.field-label {
  white-space: nowrap;
  min-width: 56px;
}

.prepare-form select,
.prepare-form input {
  padding: 5px 7px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 13px;
}

.filter-form .field-worker select {
  width: 140px;
}

.filter-form .field-unit select {
  width: 110px;
}

.check-label {
  padding: 4px 8px;
  border: 1px solid #dbe3ea;
  border-radius: 6px;
  background: #fff;
}

.favorite-star-btn {
  border: 1px solid #eab308;
  background: #facc15;
  color: #78350f;
  min-width: 34px;
  height: 31px;
  border-radius: 4px;
  cursor: pointer;
}

.favorite-star-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.btn-secondary {
  border: 1px solid #2563eb;
  background: #2563eb;
  color: #fff;
}

.btn-secondary:hover:not(:disabled) {
  background: #1d4ed8;
  border-color: #1d4ed8;
}

.btn-secondary:disabled {
  opacity: 0.7;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px;
}

.summary-card {
  padding: 12px 14px;
  border: 1px solid #dbe3ea;
  border-radius: 8px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
}

.summary-label {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}

.summary-value {
  font-size: 26px;
  font-weight: 800;
  color: #0f172a;
}

.accent-rework {
  color: #7c3aed;
}

.accent-ng {
  color: #dc2626;
}

.panel {
  padding: 12px;
  border: 1px solid #dbe3ea;
  border-radius: 8px;
  background: #fff;
}

.section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.section-title {
  margin: 0;
}

.section-note {
  font-size: 12px;
  color: #64748b;
}

.table-wrap {
  overflow: auto;
}

.chart-wrap {
  position: relative;
  min-height: 320px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 6px 8px;
  border: 1px solid #e2e8f0;
  text-align: left;
  white-space: nowrap;
}

.data-table th {
  background: #f8fafc;
  font-size: 12px;
}

.data-table.compact td {
  font-size: 12px;
}

.empty-cell {
  text-align: center;
  color: #64748b;
  padding: 18px 8px;
}

.rate-has {
  color: #1d4ed8;
  font-weight: 700;
}

.rate-warn {
  color: #b45309;
  font-weight: 800;
  background: #fff7ed;
}

.rate-danger {
  color: #b91c1c;
  font-weight: 800;
  background: #fef2f2;
}

@media (max-width: 900px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
