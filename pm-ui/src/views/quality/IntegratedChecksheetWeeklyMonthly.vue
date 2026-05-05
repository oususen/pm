<template>
  <div class="master-menu">
    <h2 class="page-title">B案: 週・月確認</h2>
    <p class="helper-text">工程一体チェックシート実績から集計（直近180日）</p>
    <button class="btn-secondary" @click="loadData" :disabled="loading">{{ loading ? "更新中..." : "更新" }}</button>

    <div v-if="error" class="helper-text" style="color:#b91c1c;">{{ error }}</div>

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
        <thead><tr><th>週</th><th>不良率</th><th>指摘件数</th><th>再発件数</th><th>未完了是正件数</th></tr></thead>
        <tbody>
          <tr v-for="row in weeklyRows" :key="row.label">
            <td>{{ row.label }}</td>
            <td>{{ row.defectRate }}%</td>
            <td>{{ row.ngCount }}</td>
            <td>{{ row.recurrenceCount }}</td>
            <td>{{ row.openCorrectiveCount }}</td>
          </tr>
        </tbody>
      </table>
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
        <thead><tr><th>月</th><th>不良率</th><th>指摘件数</th><th>再発件数</th><th>未完了是正件数</th></tr></thead>
        <tbody>
          <tr v-for="row in monthlyRows" :key="row.label">
            <td>{{ row.label }}</td>
            <td>{{ row.defectRate }}%</td>
            <td>{{ row.ngCount }}</td>
            <td>{{ row.recurrenceCount }}</td>
            <td>{{ row.openCorrectiveCount }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue"
import api from "@/api/client"

const loading = ref(false)
const error = ref("")
const weeklyRows = ref([])
const monthlyRows = ref([])

const toArray = (data) => data?.results || data || []
const isJudged = (check) => check?.judgement === "OK" || check?.judgement === "NG"
const toDate = (v) => new Date(v || "")
const ymd = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
const ym = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`

const loadData = async () => {
  loading.value = true
  error.value = ""
  try {
    const res = await api.integratedChecksheets.listBatches({ page_size: 200 })
    const batches = toArray(res.data)
    const unitsRes = await Promise.all(batches.map((b) => api.integratedChecksheets.getBatchUnits(b.id)))
    const unitsByBatch = new Map(batches.map((b, i) => [b.id, toArray(unitsRes[i].data)]))
    const records = []
    for (const batch of batches) {
      const date = toDate(batch.plan_date || batch.created_at)
      const units = unitsByBatch.get(batch.id) || []
      let hasNg = false
      for (const unit of units) {
        for (const check of unit.checks || []) {
          if (!isJudged(check)) continue
          const isNg = check.judgement === "NG"
          if (isNg) hasNg = true
          records.push({
            batchId: batch.id,
            date,
            itemName: check.item_name || "未設定項目",
            isNg,
            status: batch.status,
          })
        }
      }
      if (hasNg && !records.some((r) => r.batchId === batch.id && r.itemName === "__BATCH_NG__")) {
        records.push({ batchId: batch.id, date, itemName: "__BATCH_NG__", isNg: true, status: batch.status })
      }
    }

    const makeRow = (label, fromDate, toDateObj) => {
      const scoped = records.filter((r) => r.date >= fromDate && r.date <= toDateObj)
      const judged = scoped.filter((r) => r.itemName !== "__BATCH_NG__")
      const ngs = judged.filter((r) => r.isNg)
      const defectRate = judged.length ? ((ngs.length / judged.length) * 100).toFixed(1) : "0.0"
      const seen = new Set()
      let recurrenceCount = 0
      for (const r of ngs.sort((a, b) => a.date - b.date)) {
        if (seen.has(r.itemName)) recurrenceCount += 1
        else seen.add(r.itemName)
      }
      const openCorrectiveSet = new Set(
        scoped.filter((r) => r.itemName === "__BATCH_NG__" && !["SUPERVISOR_CONFIRMED"].includes(r.status)).map((r) => r.batchId)
      )
      return { label, defectRate, ngCount: ngs.length, recurrenceCount, openCorrectiveCount: openCorrectiveSet.size }
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
  } catch (e) {
    error.value = `集計に失敗しました: ${e.response?.data?.detail || e.message}`
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.chart-wrap { margin: 8px 0 12px; padding: 10px; border: 1px solid #dbe3ea; border-radius: 6px; background: #fff; }
.chart-title { font-weight: 700; margin-bottom: 8px; color: #1f2937; }
.bar-row { display: grid; grid-template-columns: 180px 1fr 56px; gap: 8px; align-items: center; margin-bottom: 6px; font-size: 12px; }
.bar-track { height: 14px; background: #eef2f7; border-radius: 999px; overflow: hidden; }
.bar-fill { height: 100%; background: #2563eb; }
.bar-fill.month { background: #0ea5a4; }
.bar-label, .bar-value { color: #334155; }
</style>
