<template>
  <div class="master-menu">
    <h2 class="page-title">B案: 週・月確認</h2>
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

    <h3 class="section-title">週次（直近4週）</h3>
    <div class="chart-wrap">
      <div class="chart-title">週次 不良率推移</div>
      <div v-for="row in weeklyRows" :key="`w-chart-${row.label}`" class="bar-row">
        <span class="bar-label">{{ row.label }}</span>
        <div class="bar-track"><div class="bar-fill" :style="{ width: `${Math.min(Number(row.defectRate), 100)}%` }"></div></div>
        <span class="bar-value">{{ row.defectRate }}%</span>
      </div>
    </div>
    <div class="table-wrap">
      <table class="data-table compact">
        <thead><tr><th>週</th><th>不良率</th><th>指摘件数</th><th>再発件数</th><th>班長未確認件数</th><th>リーダ未確認件数</th><th>実施中件数</th></tr></thead>
        <tbody>
          <tr v-for="row in weeklyRows" :key="row.label">
            <td>{{ row.label }}</td>
            <td>{{ row.defectRate }}%</td>
            <td>{{ row.ngCount }}</td>
            <td>{{ row.recurrenceCount }}</td>
            <td>{{ row.supervisorUnconfirmedCount }}</td>
            <td>{{ row.leaderUnconfirmedCount }}</td>
            <td>{{ row.inProgressCount }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="definition-wrap">
      <div class="definition-title">列の定義（週次・月次共通）</div>
      <ul class="definition-list">
        <li><strong>期間（週/月）</strong>: その行の集計対象期間</li>
        <li><strong>不良率</strong>: NG判定数 ÷ 判定済みチェック数（OK+NG）×100</li>
        <li><strong>指摘件数</strong>: NG判定の件数（チェック項目単位）</li>
        <li><strong>再発件数</strong>: 同一項目の2回目以降のNG発生件数</li>
        <li><strong>班長未確認件数</strong>: 期間内バッチのうち、ステータスが「班長確認済み（SUPERVISOR_CONFIRMED）」以外のバッチ数</li>
        <li><strong>リーダ未確認件数</strong>: 期間内バッチのうち、ステータスが「リーダ確認済み / 班長確認済み」以外のバッチ数</li>
        <li><strong>実施中件数</strong>: 期間内バッチのうち、ステータスが「実施中（OPEN または IN_PROGRESS）」のバッチ数（NG有無は不問）</li>
      </ul>
    </div>

    <h3 class="section-title">月次（直近6か月）</h3>
    <div class="chart-wrap">
      <div class="chart-title">月次 不良率推移</div>
      <div v-for="row in monthlyRows" :key="`m-chart-${row.label}`" class="bar-row">
        <span class="bar-label">{{ row.label }}</span>
        <div class="bar-track"><div class="bar-fill month" :style="{ width: `${Math.min(Number(row.defectRate), 100)}%` }"></div></div>
        <span class="bar-value">{{ row.defectRate }}%</span>
      </div>
    </div>
    <div class="table-wrap">
      <table class="data-table compact">
        <thead><tr><th>月</th><th>不良率</th><th>指摘件数</th><th>再発件数</th><th>班長未確認件数</th><th>リーダ未確認件数</th><th>実施中件数</th></tr></thead>
        <tbody>
          <tr v-for="row in monthlyRows" :key="row.label">
            <td>{{ row.label }}</td>
            <td>{{ row.defectRate }}%</td>
            <td>{{ row.ngCount }}</td>
            <td>{{ row.recurrenceCount }}</td>
            <td>{{ row.supervisorUnconfirmedCount }}</td>
            <td>{{ row.leaderUnconfirmedCount }}</td>
            <td>{{ row.inProgressCount }}</td>
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
const weeklyRows = ref([])
const monthlyRows = ref([])
const allRecords = ref([])
const allBatchSnapshots = ref([])
const selectedLine = ref("")
const selectedProcess = ref("")
const selectedProduct = ref("")
const selectedPerson = ref("")
const selectedUnit = ref("")
const startDate = ref("")
const endDate = ref("")

const toArray = (data) => data?.results || data || []
const isJudged = (check) => check?.judgement === "OK" || check?.judgement === "NG"
const toDate = (v) => new Date(v || "")
const ymd = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
const ym = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`
const uniqueSorted = (rows, key) => [...new Set(rows.map((r) => r[key] || "未設定"))].sort((a, b) => String(a).localeCompare(String(b), "ja"))
const lineOptions = computed(() => uniqueSorted(allRecords.value, "line"))
const processOptions = computed(() => uniqueSorted(allRecords.value, "process"))
const productOptions = computed(() => uniqueSorted(allRecords.value, "product"))
const personOptions = computed(() => uniqueSorted(allRecords.value, "person"))
const unitOptions = computed(() => uniqueSorted(allRecords.value, "unit"))

const filteredRecords = computed(() => allRecords.value.filter((r) => {
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
    const unitsByBatch = new Map(batches.map((b, i) => [b.id, toArray(unitsRes[i].data)]))
    const records = []
    const batchSnapshots = []
    for (const batch of batches) {
      const date = toDate(batch.plan_date || batch.created_at)
      const units = unitsByBatch.get(batch.id) || []
      let hasNg = false
      const processNameById = new Map((batch.process_progress || []).map((p) => [p.process_block_id, p.process_name || p.process_code || `工程${p.process_block_id}`]))
      for (const unit of units) {
        for (const check of unit.checks || []) {
          if (!isJudged(check)) continue
          const isNg = check.judgement === "NG"
          if (isNg) hasNg = true
          records.push({
            batchId: batch.id,
            date,
            dateText: ymd(date),
            line: batch.line_code || "未設定",
            product: batch.product_code || "未設定",
            process: processNameById.get(check.process_block_id) || `工程${check.process_block_id}`,
            person: check.checked_by_name || check.worker_name || check.worker_code || "未設定",
            unit: String(unit.unit_no || "未設定"),
            itemName: check.item_name || "未設定項目",
            isNg,
            status: batch.status,
          })
        }
      }
      if (hasNg && !records.some((r) => r.batchId === batch.id && r.itemName === "__BATCH_NG__")) {
        records.push({
          batchId: batch.id,
          date,
          dateText: ymd(date),
          line: batch.line_code || "未設定",
          product: batch.product_code || "未設定",
          process: "未設定",
          person: "未設定",
          unit: "未設定",
          itemName: "__BATCH_NG__",
          isNg: true,
          status: batch.status,
        })
      }
      batchSnapshots.push({ batchId: batch.id, date, dateText: ymd(date), status: batch.status })
    }
    allRecords.value = records
    allBatchSnapshots.value = batchSnapshots
    rebuildRows()
  } catch (e) {
    error.value = `集計に失敗しました: ${e.response?.data?.detail || e.message}`
  } finally {
    loading.value = false
  }
}

const rebuildRows = () => {
    const rows = filteredRecords.value
    const filteredBatchIds = new Set(rows.map((r) => r.batchId))
    const batchSnapshots = allBatchSnapshots.value.filter((b) => {
      if (!filteredBatchIds.has(b.batchId)) return false
      if (startDate.value && b.dateText < startDate.value) return false
      if (endDate.value && b.dateText > endDate.value) return false
      return true
    })
    const makeRow = (label, fromDate, toDateObj) => {
      const scoped = rows.filter((r) => r.date >= fromDate && r.date <= toDateObj)
      const scopedBatches = batchSnapshots.filter((b) => b.date >= fromDate && b.date <= toDateObj)
      const judged = scoped.filter((r) => r.itemName !== "__BATCH_NG__")
      const ngs = judged.filter((r) => r.isNg)
      const defectRate = judged.length ? ((ngs.length / judged.length) * 100).toFixed(1) : "0.0"
      const seen = new Set()
      let recurrenceCount = 0
      for (const r of ngs.sort((a, b) => a.date - b.date)) {
        if (seen.has(r.itemName)) recurrenceCount += 1
        else seen.add(r.itemName)
      }
      const supervisorUnconfirmedSet = new Set(
        scopedBatches.filter((b) => b.status !== "SUPERVISOR_CONFIRMED").map((b) => b.batchId)
      )
      const leaderUnconfirmedSet = new Set(
        scopedBatches.filter((b) => !["LEADER_CONFIRMED", "SUPERVISOR_CONFIRMED"].includes(b.status)).map((b) => b.batchId)
      )
      const inProgressSet = new Set(
        scopedBatches.filter((b) => ["OPEN", "IN_PROGRESS"].includes(b.status)).map((b) => b.batchId)
      )
      return {
        label,
        defectRate,
        ngCount: ngs.length,
        recurrenceCount,
        supervisorUnconfirmedCount: supervisorUnconfirmedSet.size,
        leaderUnconfirmedCount: leaderUnconfirmedSet.size,
        inProgressCount: inProgressSet.size,
      }
    }

    const now = new Date()
    const ws = []
    for (let i = 3; i >= 0; i -= 1) {
      const end = new Date(now); end.setDate(now.getDate() - (i * 7))
      const start = new Date(end); start.setDate(end.getDate() - 6)
      ws.push(makeRow(`${ymd(start)}〜${ymd(end)}`, start, end))
    }
    weeklyRows.value = ws

    const ms = []
    for (let i = 5; i >= 0; i -= 1) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
      const start = new Date(d.getFullYear(), d.getMonth(), 1)
      const end = new Date(d.getFullYear(), d.getMonth() + 1, 0)
      ms.push(makeRow(ym(d), start, end))
    }
    monthlyRows.value = ms
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
.bar-row { display: grid; grid-template-columns: 180px 1fr 56px; gap: 8px; align-items: center; margin-bottom: 6px; font-size: 12px; }
.bar-track { height: 14px; background: #eef2f7; border-radius: 999px; overflow: hidden; }
.bar-fill { height: 100%; background: #2563eb; }
.bar-fill.month { background: #0ea5a4; }
.bar-label, .bar-value { color: #334155; }
.definition-wrap { margin: 6px 0 14px; padding: 8px 10px; border: 1px solid #dbe3ea; border-radius: 6px; background: #fff; }
.definition-title { font-weight: 700; margin-bottom: 4px; color: #1f2937; font-size: 12px; }
.definition-list { margin: 0; padding-left: 18px; color: #334155; font-size: 12px; line-height: 1.5; }
</style>
