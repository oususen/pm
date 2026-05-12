<template>
  <div class="master-menu">
    <h2 class="page-title">B案: 傾向確認・分析</h2>
    <p class="helper-text">工程一体チェックシート実績から集計（直近180日）</p>
    <button class="btn-secondary" @click="loadData" :disabled="loading">{{ loading ? "更新中..." : "更新" }}</button>
    <div v-if="error" class="helper-text" style="color:#b91c1c;">{{ error }}</div>
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
    </div>

    <h3 class="section-title">集計結果（表＋グラフ）</h3>
    <div class="chart-wrap">
      <div class="prepare-form">
        <span class="field-label">対象</span>
        <span>{{ selectedFilterSummary }}</span>
      </div>
      <svg class="trend-svg" viewBox="0 0 920 240" preserveAspectRatio="none">
        <line x1="40" y1="190" x2="900" y2="190" class="axis-line" />
        <line x1="40" y1="20" x2="40" y2="190" class="axis-line" />
        <g v-for="(row, idx) in summaryRows.slice(0, 12)" :key="`s-bar-${row.key}`">
          <rect
            :x="50 + idx * summaryBandWidth + (summaryBandWidth * 0.2)"
            :y="190 - ((row.reworkCount / summaryMaxCount) * 150)"
            :width="summaryBandWidth * 0.6"
            :height="Math.max((row.reworkCount / summaryMaxCount) * 150, 1)"
            class="summary-bar"
          />
        </g>
        <polyline :points="summaryRatePoints" class="trend-line rework-rate" />
      </svg>
      <div class="trend-legend">
        <span class="legend-item"><span class="legend-dot count"></span>修正流動件数（棒）</span>
        <span class="legend-item"><span class="legend-dot rate"></span>修正流動率（折れ線）</span>
      </div>
    </div>
    <div class="table-wrap">
      <div class="table-title">集計表（{{ selectedFilterSummary }}: 修正流動件数 / 修正流動率）</div>
      <table class="data-table compact">
        <thead><tr><th>分類</th><th>判定総数</th><th>修正流動件数</th><th>修正流動率</th><th>NG件数</th><th>NG率</th></tr></thead>
        <tbody>
          <tr v-for="row in summaryRows" :key="`s-row-${row.key}`">
            <td>{{ row.key }}</td>
            <td>{{ row.total }}</td>
            <td>{{ row.reworkCount }}</td>
            <td>{{ row.reworkRate.toFixed(1) }}%</td>
            <td>{{ row.ngCount }}</td>
            <td>{{ row.ngRate.toFixed(1) }}%</td>
          </tr>
        </tbody>
      </table>
    </div>

    <h3 class="section-title">工程別トレンド（NG率）</h3>
    <div class="chart-wrap">
      <div class="chart-title">工程別 今週NG率</div>
      <div v-for="row in processRows" :key="`p-chart-${row.process}`" class="bar-row">
        <span class="bar-label">{{ row.process }}</span>
        <div class="bar-track"><div class="bar-fill" :style="{ width: `${Math.min(Number(row.thisWeek), 100)}%` }"></div></div>
        <span class="bar-value">{{ row.thisWeek }}%</span>
      </div>
    </div>
    <div class="table-wrap">
      <table class="data-table compact">
        <thead><tr><th>工程</th><th>今週</th><th>先週</th><th>前週比</th><th>3か月平均</th></tr></thead>
        <tbody>
          <tr v-for="row in processRows" :key="row.process">
            <td>{{ row.process }}</td>
            <td>{{ row.thisWeek }}%</td>
            <td>{{ row.lastWeek }}%</td>
            <td>{{ row.diff }}pt</td>
            <td>{{ row.ma3m }}%</td>
          </tr>
        </tbody>
      </table>
    </div>

    <h3 class="section-title">上位不良要因（NG件数）</h3>
    <div class="chart-wrap">
      <div class="chart-title">上位不良要因</div>
      <div v-for="row in topFactors.slice(0, 8)" :key="`f-chart-${row.itemName}`" class="bar-row">
        <span class="bar-label">{{ row.itemName }}</span>
        <div class="bar-track"><div class="bar-fill factor" :style="{ width: `${Math.min((row.count / Math.max(...topFactors.map((x) => x.count), 1)) * 100, 100)}%` }"></div></div>
        <span class="bar-value">{{ row.count }}</span>
      </div>
    </div>
    <div class="table-wrap">
      <table class="data-table compact">
        <thead><tr><th>順位</th><th>項目</th><th>件数</th></tr></thead>
        <tbody>
          <tr v-for="(row, idx) in topFactors" :key="row.itemName">
            <td>{{ idx + 1 }}</td>
            <td>{{ row.itemName }}</td>
            <td>{{ row.count }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <h3 class="section-title">ライン比較</h3>
    <div class="table-wrap">
      <table class="data-table compact">
        <thead><tr><th>ライン</th><th>判定総数</th><th>NG件数</th><th>NG率</th></tr></thead>
        <tbody>
          <tr v-for="row in lineRows" :key="row.line">
            <td>{{ row.line }}</td>
            <td>{{ row.total }}</td>
            <td>{{ row.ng }}</td>
            <td>{{ row.rate }}%</td>
          </tr>
        </tbody>
      </table>
    </div>

    <h3 class="section-title">日次 時系列（表＋グラフ）</h3>
    <div class="chart-wrap">
      <div class="chart-title">日次推移（{{ selectedFilterSummary }}: 修正流動件数 / NG件数）</div>
      <svg class="trend-svg" viewBox="0 0 920 220" preserveAspectRatio="none">
        <line x1="40" y1="180" x2="900" y2="180" class="axis-line" />
        <line x1="40" y1="20" x2="40" y2="180" class="axis-line" />
        <polyline :points="dailyReworkPoints" class="trend-line rework" />
        <polyline :points="dailyNgPoints" class="trend-line ng" />
      </svg>
      <div class="trend-legend">
        <span class="legend-item"><span class="legend-dot rework"></span>修正流動件数</span>
        <span class="legend-item"><span class="legend-dot ng"></span>NG件数</span>
      </div>
    </div>
    <div class="table-wrap">
      <div class="table-title">日次表（{{ selectedFilterSummary }}）</div>
      <table class="data-table compact">
        <thead><tr><th>日付</th><th>判定総数</th><th>修正流動件数</th><th>修正流動率</th><th>NG件数</th><th>NG率</th></tr></thead>
        <tbody>
          <tr v-for="row in dailyRows" :key="`d-row-${row.date}`">
            <td>{{ row.date }}</td>
            <td>{{ row.total }}</td>
            <td>{{ row.reworkCount }}</td>
            <td>{{ row.reworkRate.toFixed(1) }}%</td>
            <td>{{ row.ngCount }}</td>
            <td>{{ row.ngRate.toFixed(1) }}%</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue"
import api from "@/api/client"

const loading = ref(false)
const error = ref("")
const processRows = ref([])
const topFactors = ref([])
const lineRows = ref([])
const allRows = ref([])
const selectedLine = ref("")
const selectedProcess = ref("")
const selectedProduct = ref("")
const selectedItem = ref("")
const selectedPerson = ref("")
const selectedUnit = ref("")
const startDate = ref("")
const endDate = ref("")

const toArray = (data) => data?.results || data || []
const toDate = (v) => new Date(v || "")
const ymd = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
const isJudged = (check) => ["OK", "NG", "修正流動"].includes(check?.judgement)
const rate = (ng, total) => total ? ((ng / total) * 100).toFixed(1) : "0.0"
const ngRateFromRows = (rows) => {
  const base = rows.filter((r) => !r.isRework)
  const ng = base.filter((r) => r.isNg).length
  return rate(ng, base.length)
}
const uniqueSorted = (rows, key) => [...new Set(rows.map((r) => r[key] || "未設定"))].sort((a, b) => String(a).localeCompare(String(b), "ja"))
const lineOptions = computed(() => uniqueSorted(allRows.value, "line"))
const processOptions = computed(() => uniqueSorted(allRows.value, "process"))
const productOptions = computed(() => uniqueSorted(allRows.value, "product"))
const isItemSelectable = computed(() => Boolean(selectedProduct.value) && Boolean(selectedProcess.value))
const itemOptions = computed(() => {
  if (!isItemSelectable.value) return []
  const base = allRows.value.filter((r) => r.product === selectedProduct.value && r.process === selectedProcess.value)
  return uniqueSorted(base, "itemName")
})
const personOptions = computed(() => uniqueSorted(allRows.value, "person"))
const unitOptions = computed(() => uniqueSorted(allRows.value, "unit"))

const filteredRows = computed(() => allRows.value.filter((r) => {
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

const summaryRows = computed(() => {
  const map = new Map()
  filteredRows.value.forEach((r) => {
    const key = String(r[summaryAxisKey.value] || "未設定")
    if (!map.has(key)) map.set(key, { key, total: 0, ngCount: 0, reworkCount: 0, ngRate: 0, reworkRate: 0, metricValue: 0 })
    const obj = map.get(key)
    obj.total += 1
    if (r.isNg) obj.ngCount += 1
    if (r.isRework) obj.reworkCount += 1
  })
  const rows = [...map.values()].map((r) => {
    const ngRate = r.total ? (r.ngCount / r.total) * 100 : 0
    const reworkRate = r.total ? (r.reworkCount / r.total) * 100 : 0
    return { ...r, ngRate, reworkRate }
  })
  rows.sort((a, b) => b.reworkCount - a.reworkCount)
  return rows
})

const summaryAxisKey = computed(() => {
  if (selectedItem.value) return "itemName"
  if (selectedPerson.value) return "person"
  if (selectedProduct.value) return "product"
  if (selectedProcess.value) return "process"
  return "line"
})

const summaryAxisLabel = computed(() => {
  const labelMap = {
    itemName: "項目",
    person: "作業者",
    product: "製品",
    process: "工程",
    line: "ライン",
  }
  return labelMap[summaryAxisKey.value] || "ライン"
})

const selectedFilterSummary = computed(() => {
  const parts = []
  if (selectedLine.value) parts.push(selectedLine.value)
  if (selectedProcess.value) parts.push(selectedProcess.value)
  if (selectedProduct.value) parts.push(selectedProduct.value)
  if (selectedItem.value) parts.push(selectedItem.value)
  if (selectedPerson.value) parts.push(selectedPerson.value)
  if (selectedUnit.value) parts.push(`台目:${selectedUnit.value}`)
  return parts.length ? parts.join(" + ") : "全体"
})

const summaryMaxCount = computed(() => Math.max(...summaryRows.value.slice(0, 12).map((r) => r.reworkCount), 1))
const summaryBandWidth = computed(() => 860 / Math.max(summaryRows.value.slice(0, 12).length, 1))
const summaryRatePoints = computed(() => {
  const rows = summaryRows.value.slice(0, 12)
  if (!rows.length) return ""
  return rows.map((r, idx) => {
    const x = 50 + idx * summaryBandWidth.value + (summaryBandWidth.value * 0.5)
    const y = 190 - ((r.reworkRate / 100) * 150)
    return `${x},${y}`
  }).join(" ")
})

const dailyRows = computed(() => {
  const map = new Map()
  filteredRows.value.forEach((r) => {
    const key = r.dateText
    if (!map.has(key)) map.set(key, { date: key, total: 0, ngCount: 0, reworkCount: 0, ngRate: 0, reworkRate: 0 })
    const obj = map.get(key)
    obj.total += 1
    if (r.isNg) obj.ngCount += 1
    if (r.isRework) obj.reworkCount += 1
  })
  return [...map.values()]
    .map((r) => {
      const ngBase = r.total - r.reworkCount
      return {
        ...r,
        ngRate: ngBase > 0 ? (r.ngCount / ngBase) * 100 : 0,
        reworkRate: r.total > 0 ? (r.reworkCount / r.total) * 100 : 0,
      }
    })
    .sort((a, b) => String(a.date).localeCompare(String(b.date), "ja"))
})

const dailyReworkPoints = computed(() => {
  const rows = dailyRows.value
  if (!rows.length) return ""
  const maxY = Math.max(...rows.map((r) => Math.max(r.reworkCount, r.ngCount)), 1)
  return rows.map((r, i) => {
    const x = 40 + ((860 * i) / Math.max(rows.length - 1, 1))
    const y = 180 - ((r.reworkCount / maxY) * 150)
    return `${x},${y}`
  }).join(" ")
})

const dailyNgPoints = computed(() => {
  const rows = dailyRows.value
  if (!rows.length) return ""
  const maxY = Math.max(...rows.map((r) => Math.max(r.reworkCount, r.ngCount)), 1)
  return rows.map((r, i) => {
    const x = 40 + ((860 * i) / Math.max(rows.length - 1, 1))
    const y = 180 - ((r.ngCount / maxY) * 150)
    return `${x},${y}`
  }).join(" ")
})

const loadData = async () => {
  loading.value = true
  error.value = ""
  try {
    const res = await api.integratedChecksheets.listBatches({ page_size: 200 })
    const batches = toArray(res.data)
    const unitsRes = await Promise.all(batches.map((b) => api.integratedChecksheets.getBatchUnits(b.id)))
    const processNameById = new Map()
    const rows = []
    batches.forEach((b) => {
      ;(b.process_progress || []).forEach((p) => processNameById.set(p.process_block_id, p.process_name || p.process_code || `工程${p.process_block_id}`))
    })
    for (let i = 0; i < batches.length; i += 1) {
      const batch = batches[i]
      const units = toArray(unitsRes[i].data)
      const date = toDate(batch.plan_date || batch.created_at)
      for (const unit of units) {
        for (const check of unit.checks || []) {
          if (!isJudged(check)) continue
          rows.push({
            dateText: ymd(date),
            product: batch.product_code || "未設定",
            person: check.checked_by_name || check.worker_name || check.worker_code || "未設定",
            unit: String(unit.unit_no || "未設定"),
            date,
            line: batch.line_code || "未設定",
            process: processNameById.get(check.process_block_id) || `工程${check.process_block_id}`,
            itemName: check.item_name || "未設定項目",
            isNg: check.judgement === "NG",
            isRework: check.judgement === "修正流動",
          })
        }
      }
    }
    allRows.value = rows
    rebuildRows()
  } catch (e) {
    error.value = `集計に失敗しました: ${e.response?.data?.detail || e.message}`
  } finally {
    loading.value = false
  }
}

const rebuildRows = () => {
  const rows = filteredRows.value
  const now = new Date()
  const thisWeekStart = new Date(now); thisWeekStart.setDate(now.getDate() - 6)
  const lastWeekStart = new Date(now); lastWeekStart.setDate(now.getDate() - 13)
  const lastWeekEnd = new Date(now); lastWeekEnd.setDate(now.getDate() - 7)
  const threeMonthStart = new Date(now); threeMonthStart.setMonth(now.getMonth() - 3)

  const byProcess = new Map()
  rows.forEach((r) => {
    if (!byProcess.has(r.process)) byProcess.set(r.process, [])
    byProcess.get(r.process).push(r)
  })
  processRows.value = [...byProcess.entries()].map(([process, list]) => {
    const thisWeek = list.filter((r) => r.date >= thisWeekStart && r.date <= now)
    const lastWeek = list.filter((r) => r.date >= lastWeekStart && r.date <= lastWeekEnd)
    const ma3m = list.filter((r) => r.date >= threeMonthStart && r.date <= now)
    const t = Number(ngRateFromRows(thisWeek))
    const l = Number(ngRateFromRows(lastWeek))
    return {
      process,
      thisWeek: t.toFixed(1),
      lastWeek: l.toFixed(1),
      diff: (t - l).toFixed(1),
      ma3m: ngRateFromRows(ma3m),
    }
  }).sort((a, b) => Number(b.thisWeek) - Number(a.thisWeek))

  const factorMap = new Map()
  rows.filter((r) => r.isNg).forEach((r) => factorMap.set(r.itemName, (factorMap.get(r.itemName) || 0) + 1))
  topFactors.value = [...factorMap.entries()].map(([itemName, count]) => ({ itemName, count })).sort((a, b) => b.count - a.count).slice(0, 10)

  const lineMap = new Map()
  rows.forEach((r) => {
    if (!lineMap.has(r.line)) lineMap.set(r.line, { line: r.line, total: 0, ng: 0 })
    const obj = lineMap.get(r.line)
    if (!r.isRework) obj.total += 1
    if (r.isNg) obj.ng += 1
  })
  lineRows.value = [...lineMap.values()].map((r) => ({ ...r, rate: rate(r.ng, r.total) })).sort((a, b) => Number(b.rate) - Number(a.rate))
}

onMounted(loadData)
watch([selectedProduct, selectedProcess], () => {
  if (!isItemSelectable.value) selectedItem.value = ""
})
watch([selectedLine, selectedProcess, selectedProduct, selectedItem, selectedPerson, selectedUnit, startDate, endDate], rebuildRows)
</script>

<style scoped>
.prepare-form { display: flex; flex-wrap: wrap; align-items: end; gap: 8px; margin: 8px 0 10px; }
.prepare-form label { display: inline-flex; align-items: center; gap: 6px; margin: 0; width: auto; flex: 0 0 auto; }
.field-label { white-space: nowrap; min-width: 56px; }
.prepare-form select, .prepare-form input { padding: 5px 7px; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 13px; }
.filter-form .field-worker select { width: 140px; }
.filter-form .field-unit select { width: 110px; }
.chart-wrap { margin: 8px 0 12px; padding: 10px; border: 1px solid #dbe3ea; border-radius: 6px; background: #fff; }
.chart-title { font-weight: 700; margin-bottom: 8px; color: #1f2937; }
.bar-row { display: grid; grid-template-columns: 220px 1fr 56px; gap: 8px; align-items: center; margin-bottom: 6px; font-size: 12px; }
.bar-track { height: 14px; background: #eef2f7; border-radius: 999px; overflow: hidden; }
.bar-fill { height: 100%; background: #1d4ed8; }
.bar-fill.factor { background: #ea580c; }
.bar-label, .bar-value { color: #334155; }
.table-title { font-weight: 700; margin-bottom: 8px; color: #1f2937; font-size: 13px; }
.trend-svg { width: 100%; height: 220px; background: #fff; border: 1px solid #e2e8f0; border-radius: 6px; }
.axis-line { stroke: #94a3b8; stroke-width: 1; }
.trend-line { fill: none; stroke-width: 2.5; }
.trend-line.rework { stroke: #0ea5a4; }
.trend-line.ng { stroke: #ef4444; }
.trend-legend { display: flex; gap: 14px; margin-top: 6px; font-size: 12px; color: #334155; }
.legend-item { display: inline-flex; align-items: center; gap: 5px; }
.legend-dot { width: 10px; height: 10px; border-radius: 999px; display: inline-block; }
.legend-dot.rework { background: #0ea5a4; }
.legend-dot.ng { background: #ef4444; }
.legend-dot.count { background: #ea580c; }
.legend-dot.rate { background: #2563eb; }
.trend-line.rework-rate { stroke: #2563eb; }
.summary-bar { fill: #ea580c; }
</style>

