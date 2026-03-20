<template>
  <div class="stats-page">
    <h1 class="page-title">月次労働時間統計</h1>

    <div class="filters">
      <div class="filter-item">
        <label>年月</label>
        <select v-model="selectedYear" class="filter-select">
          <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}年</option>
        </select>
        <select v-model="selectedMonth" class="filter-select">
          <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
        </select>
      </div>
      <button class="btn btn-primary" @click="load">表示</button>
    </div>

    <div v-if="loading" class="loading">読み込み中...</div>
    <div v-else-if="!rows.length" class="empty">データがありません</div>
    <template v-else>
      <div class="summary-bar">
        <span>{{ selectedYear }}年{{ selectedMonth }}月 / {{ rows.length }}名</span>
        <span class="summary-total">残業合計: {{ totalOvertimeH }}H</span>
      </div>
      <div class="table-wrap">
        <table class="stats-table">
          <thead>
            <tr>
              <th>氏名</th>
              <th>班</th>
              <th>残業(H)</th>
              <th>深夜(H)</th>
              <th>休日出勤(H)</th>
              <th>午前半休(日)</th>
              <th>午後半休(日)</th>
              <th>前日有給(日)</th>
              <th>連続有給(日)</th>
              <th>申請件数</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.userId">
              <td class="name-cell">{{ row.name }}</td>
              <td class="team-cell">{{ row.team }}</td>
              <td class="num-cell" :class="{ highlight: row.overtimeH > 0 }">{{ row.overtimeH || '—' }}</td>
              <td class="num-cell midnight">{{ row.midnightH > 0 ? row.midnightH : '—' }}</td>
              <td class="num-cell" :class="{ highlight: row.holidayH > 0 }">{{ row.holidayH || '—' }}</td>
              <td class="num-cell leave">{{ row.halfDayAm > 0 ? row.halfDayAm : '—' }}</td>
              <td class="num-cell leave">{{ row.halfDayPm > 0 ? row.halfDayPm : '—' }}</td>
              <td class="num-cell leave">{{ row.paidLeave > 0 ? row.paidLeave : '—' }}</td>
              <td class="num-cell leave">{{ row.paidLeaveConsec > 0 ? row.paidLeaveConsec : '—' }}</td>
              <td class="num-cell">{{ row.count }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api/client'

const today = new Date()
const selectedYear = ref(today.getFullYear())
const selectedMonth = ref(today.getMonth() + 1)
const yearOptions = computed(() => {
  const y = today.getFullYear()
  return [y - 1, y, y + 1]
})

const loading = ref(false)
const rows = ref([])

const totalOvertimeH = computed(() =>
  rows.value.reduce((s, r) => s + r.overtimeH + r.holidayH, 0).toFixed(1)
)

// 連続有給は開始〜終了日の日数を計算
function countDays(app) {
  if (!app.end_date) return 1
  const s = new Date(app.work_date)
  const e = new Date(app.end_date)
  return Math.max(1, Math.round((e - s) / 86400000) + 1)
}

async function load() {
  loading.value = true
  rows.value = []
  try {
    const pad = (n) => String(n).padStart(2, '0')
    const y = selectedYear.value
    const m = selectedMonth.value
    const dateFrom = `${y}-${pad(m)}-01`
    const lastDay = new Date(y, m, 0).getDate()
    const dateTo = `${y}-${pad(m)}-${pad(lastDay)}`

    const res = await api.overtime.getApplications({
      work_date__gte: dateFrom,
      work_date__lte: dateTo,
      page_size: 1000,
    })
    const apps = res.data?.results ?? res.data ?? []

    // ユーザーごとに集計
    const map = new Map()
    for (const app of apps) {
      // 記録のみ種別は承認済みのみ集計、承認種別は全ステータス含む
      const needsApproval = ['overtime', 'holiday', 'half_day_am'].includes(app.application_type)
      if (needsApproval && !['approved_manager', 'approved_chief', 'approved_supervisor', 'approved_leader'].includes(app.status)) continue

      const uid = app.applicant?.id ?? app.applicant
      if (!map.has(uid)) {
        map.set(uid, {
          userId: uid,
          name: app.applicant_name || `${app.applicant?.last_name ?? ''}${app.applicant?.first_name ?? ''}`.trim() || String(uid),
          team: app.team_name || '',
          overtimeH: 0,
          midnightH: 0,
          holidayH: 0,
          halfDayAm: 0,
          halfDayPm: 0,
          paidLeave: 0,
          paidLeaveConsec: 0,
          count: 0,
        })
      }
      const r = map.get(uid)
      r.count++
      const h = parseFloat(app.hours ?? 0)
      const mh = parseFloat(app.midnight_hours ?? 0)
      if (app.application_type === 'overtime' || app.application_type === 'half_day_am') {
        r.overtimeH += h
        r.midnightH += mh
      } else if (app.application_type === 'holiday') {
        r.holidayH += h
        r.midnightH += mh
      } else if (app.application_type === 'half_day_pm') {
        r.halfDayPm += 1
      } else if (app.application_type === 'paid_leave') {
        r.paidLeave += 1
      } else if (app.application_type === 'paid_leave_consec') {
        r.paidLeaveConsec += countDays(app)
      }
    }

    // 数値を小数点1桁に丸める
    for (const r of map.values()) {
      r.overtimeH = Math.round(r.overtimeH * 10) / 10
      r.midnightH = Math.round(r.midnightH * 10) / 10
      r.holidayH = Math.round(r.holidayH * 10) / 10
    }

    rows.value = [...map.values()].sort((a, b) => (a.team > b.team ? 1 : a.team < b.team ? -1 : a.name.localeCompare(b.name, 'ja')))
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.stats-page {
  padding: 24px;
  max-width: 1100px;
  margin: 0 auto;
}
.page-title {
  font-size: 20px;
  font-weight: 700;
  color: #1f2a44;
  margin-bottom: 20px;
}
.filters {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #374151;
}
.filter-select {
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 14px;
}
.btn {
  padding: 7px 18px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
}
.btn-primary {
  background: #40916c;
  color: white;
}
.btn-primary:hover { background: #2d6a4f; }
.loading, .empty {
  padding: 40px;
  text-align: center;
  color: #6b7280;
}
.summary-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #374151;
  margin-bottom: 8px;
  padding: 0 4px;
}
.summary-total {
  font-weight: 700;
  color: #1f2a44;
}
.table-wrap {
  overflow-x: auto;
}
.stats-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.stats-table th {
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  padding: 8px 12px;
  text-align: center;
  font-weight: 600;
  color: #374151;
  white-space: nowrap;
}
.stats-table td {
  border: 1px solid #e5e7eb;
  padding: 7px 12px;
}
.name-cell { font-weight: 600; white-space: nowrap; }
.team-cell { color: #6b7280; white-space: nowrap; }
.num-cell { text-align: right; white-space: nowrap; }
.num-cell.highlight { color: #dc2626; font-weight: 700; }
.num-cell.midnight { color: #7c3aed; }
.num-cell.leave { color: #2563eb; }
.stats-table tbody tr:hover { background: #f9fafb; }
</style>
