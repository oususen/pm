<template>
  <div class="master-menu">
    <h2 class="page-title">B案: 品質問題時ツール</h2>
    <p class="helper-text">直近90日のNG履歴からQC七つ道具を表示</p>
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

    <h3 class="section-title">1. チェックシート（要対応NG一覧）</h3>
    <div class="chart-wrap">
      <div class="chart-title">日別NG件数（直近表示分）</div>
      <div v-for="row in dailyNgChart" :key="`d-chart-${row.date}`" class="bar-row">
        <span class="bar-label">{{ row.date }}</span>
        <div class="bar-track"><div class="bar-fill" :style="{ width: `${Math.min((row.count / Math.max(...dailyNgChart.map((x) => x.count), 1)) * 100, 100)}%` }"></div></div>
        <span class="bar-value">{{ row.count }}</span>
      </div>
    </div>
    <div class="table-wrap">
      <table class="data-table compact">
        <thead><tr><th>発生日</th><th>ライン</th><th>製品</th><th>工程</th><th>項目</th><th>作業者</th><th>台目</th><th>バッチ</th></tr></thead>
        <tbody>
          <tr v-for="row in incidents" :key="row.key">
            <td>{{ row.date }}</td>
            <td>{{ row.line }}</td>
            <td>{{ row.product }}</td>
            <td>{{ row.process }}</td>
            <td>{{ row.item }}</td>
            <td>{{ row.person }}</td>
            <td>{{ row.unit }}</td>
            <td>#{{ row.batchId }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <h3 class="section-title">2. パレート図（上位不良要因）</h3>
    <div class="chart-wrap">
      <div class="chart-title">要因別累積比率</div>
      <div v-for="row in paretoRows" :key="`p-${row.item}`" class="bar-row">
        <span class="bar-label">{{ row.item }}</span>
        <div class="bar-track"><div class="bar-fill pareto" :style="{ width: `${Math.min(row.ratio, 100)}%` }"></div></div>
        <span class="bar-value">{{ row.ratio.toFixed(1) }}%</span>
      </div>
    </div>

    <h3 class="section-title">3. ヒストグラム（日別NG件数分布）</h3>
    <div class="chart-wrap">
      <div class="chart-title">日別件数の頻度</div>
      <div v-for="row in histogramRows" :key="`h-${row.bucket}`" class="bar-row">
        <span class="bar-label">{{ row.bucket }}</span>
        <div class="bar-track"><div class="bar-fill hist" :style="{ width: `${Math.min((row.days / Math.max(...histogramRows.map((x) => x.days), 1)) * 100, 100)}%` }"></div></div>
        <span class="bar-value">{{ row.days }}日</span>
      </div>
    </div>

    <h3 class="section-title">4. 散布図（台目とNG傾向）</h3>
    <div class="chart-wrap">
      <svg :viewBox="`0 0 ${svgWidth} ${svgHeight}`" class="plot-svg">
        <line :x1="plot.left" :y1="plot.bottom" :x2="plot.right" :y2="plot.bottom" class="axis" />
        <line :x1="plot.left" :y1="plot.top" :x2="plot.left" :y2="plot.bottom" class="axis" />
        <circle
          v-for="row in scatterRows"
          :key="`sc-${row.unit}`"
          :cx="scaleX(row.unit, scatterXMax)"
          :cy="scaleY(row.count, scatterYMax)"
          r="4"
          class="dot"
        />
      </svg>
    </div>

    <h3 class="section-title">5. 管理図（日別NG件数）</h3>
    <div class="chart-wrap">
      <svg :viewBox="`0 0 ${svgWidth} ${svgHeight}`" class="plot-svg">
        <line :x1="plot.left" :y1="plot.bottom" :x2="plot.right" :y2="plot.bottom" class="axis" />
        <line :x1="plot.left" :y1="plot.top" :x2="plot.left" :y2="plot.bottom" class="axis" />
        <polyline :points="controlLinePoints" class="line-main" />
        <line :x1="plot.left" :y1="scaleY(controlAvg, controlYMax)" :x2="plot.right" :y2="scaleY(controlAvg, controlYMax)" class="line-avg" />
        <line :x1="plot.left" :y1="scaleY(controlUcl, controlYMax)" :x2="plot.right" :y2="scaleY(controlUcl, controlYMax)" class="line-ucl" />
      </svg>
    </div>

    <h3 class="section-title">6. 層別（ライン別・工程別・人別・製品別）</h3>
    <div class="table-wrap">
      <table class="data-table compact">
        <thead><tr><th>ライン</th><th>NG件数</th><th>構成比</th></tr></thead>
        <tbody>
          <tr v-for="row in stratificationRows" :key="`st-${row.line}`">
            <td>{{ row.line }}</td><td>{{ row.count }}</td><td>{{ row.ratio.toFixed(1) }}%</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="table-wrap" style="margin-top:8px;">
      <table class="data-table compact">
        <thead><tr><th>工程</th><th>NG件数</th><th>構成比</th></tr></thead>
        <tbody>
          <tr v-for="row in stratificationProcessRows" :key="`sp-${row.process}`">
            <td>{{ row.process }}</td><td>{{ row.count }}</td><td>{{ row.ratio.toFixed(1) }}%</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="table-wrap" style="margin-top:8px;">
      <table class="data-table compact">
        <thead><tr><th>人</th><th>NG件数</th><th>構成比</th></tr></thead>
        <tbody>
          <tr v-for="row in stratificationPeopleRows" :key="`sr-${row.person}`">
            <td>{{ row.person }}</td><td>{{ row.count }}</td><td>{{ row.ratio.toFixed(1) }}%</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="table-wrap" style="margin-top:8px;">
      <table class="data-table compact">
        <thead><tr><th>製品</th><th>NG件数</th><th>構成比</th></tr></thead>
        <tbody>
          <tr v-for="row in stratificationProductRows" :key="`spr-${row.product}`">
            <td>{{ row.product }}</td><td>{{ row.count }}</td><td>{{ row.ratio.toFixed(1) }}%</td>
          </tr>
        </tbody>
      </table>
    </div>

    <h3 class="section-title">7. 特性要因図（入力補助）</h3>
    <div class="chart-wrap">
      <div class="fishbone-grid">
        <div><strong>人</strong><p>{{ fishbone.people }}</p></div>
        <div><strong>機械</strong><p>{{ fishbone.machine }}</p></div>
        <div><strong>方法</strong><p>{{ fishbone.method }}</p></div>
        <div><strong>材料</strong><p>{{ fishbone.material }}</p></div>
      </div>
    </div>

    <h3 class="section-title">再発候補（同一項目の発生回数）</h3>
    <div class="table-wrap">
      <table class="data-table compact">
        <thead><tr><th>項目</th><th>発生回数</th><th>最新発生日</th></tr></thead>
        <tbody>
          <tr v-for="row in recurrenceItems" :key="row.item">
            <td>{{ row.item }}</td>
            <td>{{ row.count }}</td>
            <td>{{ row.latestDate }}</td>
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
const incidentRowsAll = ref([])
const incidents = ref([])
const recurrenceItems = ref([])
const dailyNgChart = ref([])
const paretoRows = ref([])
const histogramRows = ref([])
const scatterRows = ref([])
const controlRows = ref([])
const stratificationRows = ref([])
const stratificationProcessRows = ref([])
const stratificationPeopleRows = ref([])
const stratificationProductRows = ref([])
const fishbone = ref({ people: "-", machine: "-", method: "-", material: "-" })
const svgWidth = 820
const svgHeight = 260
const plot = { left: 44, right: 792, top: 20, bottom: 228 }
const controlAvg = ref(0)
const controlUcl = ref(0)
const scatterXMax = ref(1)
const scatterYMax = ref(1)
const controlYMax = ref(1)
const controlLinePoints = ref("")
const selectedLine = ref("")
const selectedProcess = ref("")
const selectedProduct = ref("")
const selectedPerson = ref("")
const selectedUnit = ref("")
const startDate = ref("")
const endDate = ref("")

const uniqueSorted = (rows, key) => [...new Set(rows.map((r) => r[key] || "未設定"))].sort((a, b) => String(a).localeCompare(String(b), "ja"))
const lineOptions = computed(() => uniqueSorted(incidentRowsAll.value, "line"))
const processOptions = computed(() => uniqueSorted(incidentRowsAll.value, "process"))
const productOptions = computed(() => uniqueSorted(incidentRowsAll.value, "product"))
const personOptions = computed(() => uniqueSorted(incidentRowsAll.value, "person"))
const unitOptions = computed(() => uniqueSorted(incidentRowsAll.value, "unit"))

const filteredRows = computed(() => incidentRowsAll.value.filter((r) => {
  if (selectedLine.value && r.line !== selectedLine.value) return false
  if (selectedProcess.value && r.process !== selectedProcess.value) return false
  if (selectedProduct.value && r.product !== selectedProduct.value) return false
  if (selectedPerson.value && r.person !== selectedPerson.value) return false
  if (selectedUnit.value && String(r.unit) !== String(selectedUnit.value)) return false
  if (startDate.value && r.date < startDate.value) return false
  if (endDate.value && r.date > endDate.value) return false
  return true
}))

const scaleX = (x, max) => {
  const span = Math.max(Number(max || 1), 1)
  return plot.left + ((x / span) * (plot.right - plot.left))
}
const scaleY = (y, max) => {
  const span = Math.max(Number(max || 1), 1)
  return plot.bottom - ((y / span) * (plot.bottom - plot.top))
}

const toArray = (data) => data?.results || data || []
const toDate = (v) => new Date(v || "")
const fmt = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`

const recomputeByRows = (rows) => {
  incidents.value = [...rows].sort((a, b) => b.ts - a.ts).slice(0, 100)
  const dayMap = new Map()
  rows.forEach((r) => dayMap.set(r.date, (dayMap.get(r.date) || 0) + 1))
  dailyNgChart.value = [...dayMap.entries()].map(([date, count]) => ({ date, count })).sort((a, b) => (a.date < b.date ? 1 : -1)).slice(0, 14)

  const factorMap = new Map()
  rows.forEach((r) => {
    if (!factorMap.has(r.item)) factorMap.set(r.item, { item: r.item, count: 0, latestDate: r.date, latestTs: r.ts })
    const v = factorMap.get(r.item)
    v.count += 1
    if (r.ts > v.latestTs) {
      v.latestTs = r.ts
      v.latestDate = r.date
    }
  })
  recurrenceItems.value = [...factorMap.values()].filter((v) => v.count >= 2).sort((a, b) => b.count - a.count).slice(0, 20)

  const totalNg = rows.length || 1
  const sortedFactors = [...factorMap.values()].sort((a, b) => b.count - a.count)
  let cum = 0
  paretoRows.value = sortedFactors.slice(0, 10).map((v) => {
    cum += v.count
    return { item: v.item, ratio: (cum / totalNg) * 100 }
  })
  const histMap = new Map()
  for (const [, count] of dayMap.entries()) {
    const bucket = count <= 2 ? "1-2件" : count <= 5 ? "3-5件" : count <= 10 ? "6-10件" : "11件以上"
    histMap.set(bucket, (histMap.get(bucket) || 0) + 1)
  }
  histogramRows.value = ["1-2件", "3-5件", "6-10件", "11件以上"].map((bucket) => ({ bucket, days: histMap.get(bucket) || 0 }))
  const scatterMap = new Map()
  rows.forEach((r) => scatterMap.set(r.unit, (scatterMap.get(r.unit) || 0) + 1))
  scatterRows.value = [...scatterMap.entries()].map(([unit, count]) => ({ unit, count })).sort((a, b) => a.unit - b.unit).slice(0, 50)
  scatterXMax.value = Math.max(...scatterRows.value.map((r) => r.unit), 1)
  scatterYMax.value = Math.max(...scatterRows.value.map((r) => r.count), 1)
  const dayCounts = [...dayMap.entries()].map(([date, count]) => ({ date, count })).sort((a, b) => (a.date < b.date ? -1 : 1))
  const avg = dayCounts.reduce((s, r) => s + r.count, 0) / (dayCounts.length || 1)
  const variance = dayCounts.reduce((s, r) => s + ((r.count - avg) ** 2), 0) / (dayCounts.length || 1)
  const sigma = Math.sqrt(variance)
  const ucl = avg + (3 * sigma)
  controlRows.value = dayCounts.slice(-30).map((r) => ({ ...r, judge: r.count > ucl ? "要注意" : "管理内" }))
  controlAvg.value = avg
  controlUcl.value = ucl
  controlYMax.value = Math.max(...controlRows.value.map((r) => r.count), Math.ceil(ucl), 1)
  controlLinePoints.value = controlRows.value.map((r, idx) => `${scaleX(idx + 1, controlRows.value.length)} ${scaleY(r.count, controlYMax.value)}`).join(" ")
  const lineMap = new Map()
  rows.forEach((r) => lineMap.set(r.line, (lineMap.get(r.line) || 0) + 1))
  stratificationRows.value = [...lineMap.entries()].map(([line, count]) => ({ line, count, ratio: (count / totalNg) * 100 })).sort((a, b) => b.count - a.count)
  const processMap = new Map()
  rows.forEach((r) => processMap.set(r.process, (processMap.get(r.process) || 0) + 1))
  stratificationProcessRows.value = [...processMap.entries()].map(([process, count]) => ({ process, count, ratio: (count / totalNg) * 100 })).sort((a, b) => b.count - a.count)
  const peopleMap = new Map()
  rows.forEach((r) => peopleMap.set(r.person, (peopleMap.get(r.person) || 0) + 1))
  stratificationPeopleRows.value = [...peopleMap.entries()].map(([person, count]) => ({ person, count, ratio: (count / totalNg) * 100 })).sort((a, b) => b.count - a.count)
  const productMap = new Map()
  rows.forEach((r) => productMap.set(r.product, (productMap.get(r.product) || 0) + 1))
  stratificationProductRows.value = [...productMap.entries()].map(([product, count]) => ({ product, count, ratio: (count / totalNg) * 100 })).sort((a, b) => b.count - a.count)
  fishbone.value = {
    people: recurrenceItems.value[0]?.item || "作業者要因を確認",
    machine: incidents.value[0]?.process || "設備要因を確認",
    method: "工程手順・検査頻度を確認",
    material: incidents.value[0]?.product || "材料・品番を確認",
  }
}

const loadData = async () => {
  loading.value = true
  error.value = ""
  try {
    const now = new Date()
    const from = new Date(now); from.setDate(now.getDate() - 90)
    const res = await api.integratedChecksheets.listBatches({ page_size: 200 })
    const batches = toArray(res.data).filter((b) => toDate(b.plan_date || b.created_at) >= from)
    const unitsRes = await Promise.all(batches.map((b) => api.integratedChecksheets.getBatchUnits(b.id)))
    const processNameById = new Map()
    batches.forEach((b) => (b.process_progress || []).forEach((p) => processNameById.set(p.process_block_id, p.process_name || p.process_code || `工程${p.process_block_id}`)))

    const incidentRows = []
    for (let i = 0; i < batches.length; i += 1) {
      const batch = batches[i]
      const units = toArray(unitsRes[i].data)
      const date = toDate(batch.plan_date || batch.created_at)
      for (const unit of units) {
        for (const check of unit.checks || []) {
          if (check.judgement !== "NG") continue
          incidentRows.push({
            key: `${batch.id}-${unit.id}-${check.id}`,
            ts: date,
            date: fmt(date),
            line: batch.line_code || "未設定",
            product: batch.product_code || "未設定",
            process: processNameById.get(check.process_block_id) || `工程${check.process_block_id}`,
            item: check.item_name || "未設定項目",
            person: check.checked_by_name || "未設定",
            unit: unit.sequence_no,
            batchId: batch.id,
          })
        }
      }
    }
    incidentRowsAll.value = incidentRows
    recomputeByRows(filteredRows.value)
  } catch (e) {
    error.value = `集計に失敗しました: ${e.response?.data?.detail || e.message}`
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
watch(filteredRows, (rows) => {
  recomputeByRows(rows)
})
</script>

<style scoped>
.prepare-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  margin-bottom: 10px;
}
.prepare-form label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  width: auto;
  flex: 0 0 auto;
}
.field-label {
  white-space: nowrap;
  min-width: 40px;
  font-size: 12px;
  color: #334155;
}
.prepare-form select,
.prepare-form input {
  padding: 5px 7px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  background: #fff;
  font-size: 12px;
  width: 180px;
  max-width: 42vw;
}
.prepare-form input[type="date"] {
  width: 165px;
}
.filter-form .field-worker select,
.filter-form .field-unit select {
  width: 120px;
}
.chart-wrap { margin: 8px 0 12px; padding: 10px; border: 1px solid #dbe3ea; border-radius: 6px; background: #fff; }
.chart-title { font-weight: 700; margin-bottom: 8px; color: #1f2937; }
.bar-row { display: grid; grid-template-columns: 120px 1fr 56px; gap: 8px; align-items: center; margin-bottom: 6px; font-size: 12px; }
.bar-track { height: 14px; background: #eef2f7; border-radius: 999px; overflow: hidden; }
.bar-fill { height: 100%; background: #dc2626; }
.bar-fill.pareto { background: #7c3aed; }
.bar-fill.hist { background: #0ea5a4; }
.bar-label, .bar-value { color: #334155; }
.fishbone-grid { display: grid; grid-template-columns: repeat(2, minmax(180px, 1fr)); gap: 10px; }
.fishbone-grid p { margin: 4px 0 0; color: #475569; font-size: 12px; }
.plot-svg { width: 100%; height: 260px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; }
.axis { stroke: #94a3b8; stroke-width: 1; }
.dot { fill: #2563eb; opacity: 0.85; }
.line-main { fill: none; stroke: #0f766e; stroke-width: 2; }
.line-avg { stroke: #2563eb; stroke-width: 1.5; stroke-dasharray: 5 4; }
.line-ucl { stroke: #dc2626; stroke-width: 1.5; stroke-dasharray: 5 4; }
@media (max-width: 900px) {
  .prepare-form select,
  .prepare-form input {
    width: 150px;
    max-width: 40vw;
  }
  .filter-form .field-worker select,
  .filter-form .field-unit select {
    width: 110px;
  }
}
</style>
