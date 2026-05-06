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
const selectedPerson = ref("")
const selectedUnit = ref("")
const startDate = ref("")
const endDate = ref("")

const toArray = (data) => data?.results || data || []
const toDate = (v) => new Date(v || "")
const ymd = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
const isJudged = (check) => check?.judgement === "OK" || check?.judgement === "NG"
const rate = (ng, total) => total ? ((ng / total) * 100).toFixed(1) : "0.0"
const uniqueSorted = (rows, key) => [...new Set(rows.map((r) => r[key] || "未設定"))].sort((a, b) => String(a).localeCompare(String(b), "ja"))
const lineOptions = computed(() => uniqueSorted(allRows.value, "line"))
const processOptions = computed(() => uniqueSorted(allRows.value, "process"))
const productOptions = computed(() => uniqueSorted(allRows.value, "product"))
const personOptions = computed(() => uniqueSorted(allRows.value, "person"))
const unitOptions = computed(() => uniqueSorted(allRows.value, "unit"))

const filteredRows = computed(() => allRows.value.filter((r) => {
  if (selectedLine.value && r.line !== selectedLine.value) return false
  if (selectedProcess.value && r.process !== selectedProcess.value) return false
  if (selectedProduct.value && r.product !== selectedProduct.value) return false
  if (selectedPerson.value && r.person !== selectedPerson.value) return false
  if (selectedUnit.value && r.unit !== selectedUnit.value) return false
  if (startDate.value && r.dateText < startDate.value) return false
  if (endDate.value && r.dateText > endDate.value) return false
  return true
}))

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
    const t = Number(rate(thisWeek.filter((r) => r.isNg).length, thisWeek.length))
    const l = Number(rate(lastWeek.filter((r) => r.isNg).length, lastWeek.length))
    return {
      process,
      thisWeek: t.toFixed(1),
      lastWeek: l.toFixed(1),
      diff: (t - l).toFixed(1),
      ma3m: rate(ma3m.filter((r) => r.isNg).length, ma3m.length),
    }
  }).sort((a, b) => Number(b.thisWeek) - Number(a.thisWeek))

  const factorMap = new Map()
  rows.filter((r) => r.isNg).forEach((r) => factorMap.set(r.itemName, (factorMap.get(r.itemName) || 0) + 1))
  topFactors.value = [...factorMap.entries()].map(([itemName, count]) => ({ itemName, count })).sort((a, b) => b.count - a.count).slice(0, 10)

  const lineMap = new Map()
  rows.forEach((r) => {
    if (!lineMap.has(r.line)) lineMap.set(r.line, { line: r.line, total: 0, ng: 0 })
    const obj = lineMap.get(r.line)
    obj.total += 1
    if (r.isNg) obj.ng += 1
  })
  lineRows.value = [...lineMap.values()].map((r) => ({ ...r, rate: rate(r.ng, r.total) })).sort((a, b) => Number(b.rate) - Number(a.rate))
}

onMounted(loadData)
watch([selectedLine, selectedProcess, selectedProduct, selectedPerson, selectedUnit, startDate, endDate], rebuildRows)
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
</style>

