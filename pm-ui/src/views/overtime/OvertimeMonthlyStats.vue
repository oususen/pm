<template>
  <div class="stats-page">
    <h1 class="page-title">労働時間統計</h1>

    <div class="filters">
      <div class="filter-item">
        <label>期間</label>
        <input type="date" v-model="dateFrom" class="filter-input" />
        <span>〜</span>
        <input type="date" v-model="dateTo" class="filter-input" />
      </div>
      <button class="btn btn-primary" @click="load">表示</button>
    </div>
    <div v-if="rows.length" class="sub-filters">
      <select v-model="filterTeam" class="filter-select">
        <option value="">全班</option>
        <option v-for="t in teamOptions" :key="t" :value="t">{{ t }}</option>
      </select>
      <select v-model="filterGroup" class="filter-select">
        <option value="">全グループ</option>
        <option v-for="g in groupOptions" :key="g" :value="g">{{ g }}</option>
      </select>
      <input v-model="filterName" type="text" class="filter-input name-filter" placeholder="氏名で絞込" />
    </div>

    <div v-if="loading" class="loading">読み込み中...</div>
    <div v-else-if="!rows.length" class="empty">データがありません</div>
    <template v-else>
      <div class="summary-bar">
        <span>{{ filteredRows.length }}件</span>
        <span class="summary-right">
          <span class="summary-total">労働時間合計: {{ totals.workH }}H　残業合計: {{ totals.overtimeH }}H</span>
          <button class="btn btn-excel" @click="exportExcel">Excel出力</button>
        </span>
      </div>
      <div class="table-wrap">
        <table class="stats-table">
          <thead>
            <tr>
              <th>氏名</th>
              <th>班</th>
              <th>グループ</th>
              <th>日付</th>
              <th>種別</th>
              <th>労働時間(H)</th>
              <th>残業(H)</th>
              <th>休日出勤(H)</th>
              <th>午前半休</th>
              <th>午後半休</th>
              <th>前日有給</th>
              <th>連続有給</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in filteredRows" :key="i">
              <td class="name-cell">{{ row.name }}</td>
              <td class="team-cell">{{ row.team }}</td>
              <td class="team-cell">{{ row.group }}</td>
              <td class="date-cell">{{ row.date }}</td>
              <td class="type-cell">{{ row.typeLabel }}</td>
              <td class="num-cell work">{{ row.workH > 0 ? row.workH : '—' }}</td>
              <td class="num-cell" :class="{ highlight: row.overtimeH > 0 }">{{ row.overtimeH > 0 ? row.overtimeH : '—' }}</td>
              <td class="num-cell" :class="{ highlight: row.holidayH > 0 }">{{ row.holidayH > 0 ? row.holidayH : '—' }}</td>
              <td class="num-cell leave">{{ row.halfDayAm ? '○' : '—' }}</td>
              <td class="num-cell leave">{{ row.halfDayPm ? '○' : '—' }}</td>
              <td class="num-cell leave">{{ row.paidLeave ? '○' : '—' }}</td>
              <td class="num-cell leave">{{ row.paidLeaveConsec ? '○' : '—' }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="total-row">
              <td class="total-label" colspan="5">合計</td>
              <td class="num-cell work">{{ totals.workH }}</td>
              <td class="num-cell highlight">{{ totals.overtimeH || '—' }}</td>
              <td class="num-cell highlight">{{ totals.holidayH || '—' }}</td>
              <td class="num-cell leave">{{ totals.halfDayAm || '—' }}</td>
              <td class="num-cell leave">{{ totals.halfDayPm || '—' }}</td>
              <td class="num-cell leave">{{ totals.paidLeave || '—' }}</td>
              <td class="num-cell leave">{{ totals.paidLeaveConsec || '—' }}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import * as XLSX from 'xlsx'
import api from '@/api/client'

// デフォルト: 今月の1日〜末日
const today = new Date()
const pad = (n) => String(n).padStart(2, '0')
const y = today.getFullYear()
const m = today.getMonth() + 1
const lastDay = new Date(y, m, 0).getDate()
const dateFrom = ref(`${y}-${pad(m)}-01`)
const dateTo = ref(`${y}-${pad(m)}-${pad(lastDay)}`)

const loading = ref(false)
const rows = ref([])

// サブフィルター
const filterTeam = ref('')
const filterGroup = ref('')
const filterName = ref('')

const teamOptions = computed(() => [...new Set(rows.value.map(r => r.team).filter(Boolean))].sort())
const groupOptions = computed(() => [...new Set(rows.value.map(r => r.group).filter(Boolean))].sort())

const filteredRows = computed(() =>
  rows.value.filter(r =>
    (!filterTeam.value || r.team === filterTeam.value) &&
    (!filterGroup.value || r.group === filterGroup.value) &&
    (!filterName.value || r.name.includes(filterName.value))
  )
)

const TYPE_LABELS = {
  overtime: '時間外',
  holiday: '休日出勤',
  half_day_am: '午前半休',
  half_day_pm: '午後半休',
  paid_leave: '有給',
  paid_leave_consec: '連続有給',
}

// 連続有給を日ごとに分解（daisoカレンダーの非稼働日を除外）
function expandDays(app, nonWorkingDates = new Set()) {
  if (app.application_type !== 'paid_leave_consec' || !app.end_date) {
    return [app.work_date]
  }
  const dates = []
  const cur = new Date(app.work_date)
  const end = new Date(app.end_date)
  while (cur <= end) {
    const dateStr = `${cur.getFullYear()}-${pad(cur.getMonth() + 1)}-${pad(cur.getDate())}`
    if (!nonWorkingDates.has(dateStr)) {
      dates.push(dateStr)
    }
    cur.setDate(cur.getDate() + 1)
  }
  return dates
}

const totals = computed(() => {
  const sum = (key) => Math.round(filteredRows.value.reduce((s, r) => s + (r[key] || 0), 0) * 10) / 10
  return {
    workH: sum('workH'),
    overtimeH: sum('overtimeH'),
    holidayH: sum('holidayH'),
    halfDayAm: filteredRows.value.filter(r => r.halfDayAm).length,
    halfDayPm: filteredRows.value.filter(r => r.halfDayPm).length,
    paidLeave: filteredRows.value.filter(r => r.paidLeave).length,
    paidLeaveConsec: filteredRows.value.filter(r => r.paidLeaveConsec).length,
  }
})

const NEEDS_APPROVAL = new Set(['overtime', 'holiday', 'half_day_am'])
const APPROVED_STATUSES = new Set(['approved_manager', 'approved_chief', 'approved_supervisor', 'approved_leader'])

async function load() {
  loading.value = true
  rows.value = []
  try {
    // daisoカレンダーの非稼働日セット
    const nonWorkingDates = new Set()
    try {
      const calRes = await api.calendars.getCalendars({ search: 'daiso', page_size: 10 })
      const calList = calRes.data?.results ?? calRes.data ?? []
      const daisoCal = calList.find(c =>
        c.calendar_code?.toLowerCase() === 'daiso' || c.calendar_name?.includes('ダイソウ')
      )
      if (daisoCal) {
        const dayRes = await api.calendars.getCalendarDays(daisoCal.id, { is_working_day: false })
        const days = dayRes.data?.results ?? dayRes.data ?? []
        for (const d of days) nonWorkingDates.add(d.target_date)
      }
    } catch (e) {
      console.warn('カレンダー取得失敗:', e)
    }

    const res = await api.overtime.getApplications({
      work_date__gte: dateFrom.value,
      work_date__lte: dateTo.value,
      page_size: 1000,
    })
    const apps = res.data?.results ?? res.data ?? []

    const result = []
    for (const app of apps) {
      // 承認種別は承認済みのみ、記録のみは全件
      if (NEEDS_APPROVAL.has(app.application_type) && !APPROVED_STATUSES.has(app.status)) continue

      const name = app.applicant_name || String(app.applicant)
      const team = app.team_name || ''
      const group = app.group_name || ''
      const h = parseFloat(app.hours ?? 0)
      const typeLabel = TYPE_LABELS[app.application_type] || app.application_type

      const dates = expandDays(app, nonWorkingDates)
      for (const date of dates) {
        const row = {
          name,
          team,
          group,
          date,
          typeLabel,
          workH: 0,
          overtimeH: 0,
          holidayH: 0,
          halfDayAm: false,
          halfDayPm: false,
          paidLeave: false,
          paidLeaveConsec: false,
        }
        if (app.application_type === 'overtime') {
          row.workH = Math.round((8 + h) * 10) / 10
          row.overtimeH = h
        } else if (app.application_type === 'half_day_am') {
          row.workH = Math.round((4 + h) * 10) / 10
          row.overtimeH = h
          row.halfDayAm = true
        } else if (app.application_type === 'holiday') {
          row.workH = Math.round((8 + h) * 10) / 10
          row.holidayH = h
        } else if (app.application_type === 'half_day_pm') {
          row.halfDayPm = true
        } else if (app.application_type === 'paid_leave') {
          row.paidLeave = true
        } else if (app.application_type === 'paid_leave_consec') {
          row.paidLeaveConsec = true
        }
        result.push(row)
      }
    }

    // 日付 → 氏名 順でソート
    result.sort((a, b) => {
      if (a.date !== b.date) return a.date < b.date ? -1 : 1
      return a.name.localeCompare(b.name, 'ja')
    })
    rows.value = result
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function exportExcel() {
  const headers = ['氏名', '班', 'グループ', '日付', '種別', '労働時間(H)', '残業(H)', '休日出勤(H)', '午前半休', '午後半休', '前日有給', '連続有給']
  const data = filteredRows.value.map(r => [
    r.name, r.team, r.group, r.date, r.typeLabel,
    r.workH || '', r.overtimeH || '', r.holidayH || '',
    r.halfDayAm ? '○' : '', r.halfDayPm ? '○' : '',
    r.paidLeave ? '○' : '', r.paidLeaveConsec ? '○' : '',
  ])
  // 合計行
  data.push([
    '合計', '', '', '', '',
    totals.value.workH, totals.value.overtimeH || '', totals.value.holidayH || '',
    totals.value.halfDayAm || '', totals.value.halfDayPm || '',
    totals.value.paidLeave || '', totals.value.paidLeaveConsec || '',
  ])

  const ws = XLSX.utils.aoa_to_sheet([headers, ...data])
  // 列幅設定
  ws['!cols'] = [18, 8, 10, 12, 10, 12, 10, 12, 8, 8, 8, 8].map(w => ({ wch: w }))

  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '労働時間統計')
  const filename = `労働時間統計_${dateFrom.value}_${dateTo.value}.xlsx`
  XLSX.writeFile(wb, filename)
}

onMounted(load)
</script>

<style scoped>
.stats-page {
  padding: 24px;
  max-width: 1400px;
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
.sub-filters {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.filter-select {
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 13px;
}
.name-filter { width: 160px; }
.filter-input {
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
.btn-primary { background: #40916c; color: white; }
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
.summary-right { display: flex; align-items: center; gap: 16px; }
.summary-total { font-weight: 700; color: #1f2a44; }
.btn-excel { background: #16a34a; color: white; padding: 5px 14px; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; border: none; }
.btn-excel:hover { background: #15803d; }
.table-wrap { overflow-x: auto; }
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
.date-cell { white-space: nowrap; color: #374151; }
.type-cell { white-space: nowrap; color: #374151; }
.num-cell { text-align: right; white-space: nowrap; }
.num-cell.work { font-weight: 600; color: #1f2a44; }
.num-cell.highlight { color: #dc2626; font-weight: 700; }
.num-cell.leave { text-align: center; color: #2563eb; }
.stats-table tbody tr:hover { background: #f9fafb; }
.total-row { background: #f1f5f9; font-weight: 700; }
.total-row td { border-top: 2px solid #94a3b8; }
.total-label { font-weight: 700; color: #1f2a44; padding-left: 12px; }
</style>
