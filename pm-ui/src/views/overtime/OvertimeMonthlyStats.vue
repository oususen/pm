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
      <select v-model="filterName" class="filter-select">
        <option value="">全員</option>
        <option v-for="n in nameOptions" :key="n" :value="n">{{ n }}</option>
      </select>
      <select v-model="filterPaidLeave" class="filter-select">
        <option value="">有給：全て</option>
        <option value="any">有給あり</option>
        <option value="none">有給なし</option>
      </select>
    </div>

    <!-- タブ -->
    <div class="tab-bar">
      <button class="tab-btn" :class="{ active: activeTab === 'detail' }" @click="activeTab = 'detail'">詳細</button>
      <button class="tab-btn" :class="{ active: activeTab === 'summary' }" @click="activeTab = 'summary'">集計</button>
    </div>

    <div v-if="loading" class="loading">読み込み中...</div>
    <div v-else-if="!rows.length" class="empty">データがありません</div>
    <template v-else>

      <!-- 詳細タブ -->
      <template v-if="activeTab === 'detail'">
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
                <th>開始時間</th>
                <th>終了時間</th>
                <th>労働時間(H)</th>
                <th>残業(H)</th>
                <th>休日出勤(H)</th>
                <th>所定外(H)</th>
                <th>午前半休</th>
                <th>午後半休</th>
                <th>前日有給</th>
                <th>連続有給</th>
                <th>有給数</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in filteredRows" :key="i">
                <td class="name-cell">{{ row.name }}</td>
                <td class="team-cell">{{ row.team }}</td>
                <td class="team-cell">{{ row.group }}</td>
                <td class="date-cell">{{ row.date }}</td>
                <td class="type-cell">{{ row.typeLabel }}</td>
                <td class="time-cell nowrap">{{ row.startTime || '—' }}</td>
                <td class="time-cell nowrap">{{ row.endTime || '—' }}</td>
                <td class="num-cell work">{{ row.workH > 0 ? row.workH : '—' }}</td>
                <td class="num-cell" :class="{ highlight: row.overtimeH > 0 }">{{ row.overtimeH > 0 ? row.overtimeH : '—' }}</td>
                <td class="num-cell" :class="{ highlight: row.holidayH > 0 }">{{ row.holidayH > 0 ? row.holidayH : '—' }}</td>
                <td class="num-cell" :class="{ highlight: (row.overtimeH + row.holidayH) > 0 }">{{ (row.overtimeH + row.holidayH) > 0 ? Math.round((row.overtimeH + row.holidayH) * 10) / 10 : '—' }}</td>
                <td class="num-cell leave">{{ row.halfDayAm ? '○' : '—' }}</td>
                <td class="num-cell leave">{{ row.halfDayPm ? '○' : '—' }}</td>
                <td class="num-cell leave">{{ row.paidLeave ? '○' : '—' }}</td>
                <td class="num-cell leave">{{ row.paidLeaveConsec ? '○' : '—' }}</td>
                <td class="num-cell leave">{{ row.paidLeaveCount > 0 ? row.paidLeaveCount : '—' }}</td>
              </tr>
            </tbody>
            <tfoot>
              <tr class="total-row">
                <td class="total-label" colspan="7">合計</td>
                <td class="num-cell work">{{ totals.workH }}</td>
                <td class="num-cell highlight">{{ totals.overtimeH || '—' }}</td>
                <td class="num-cell highlight">{{ totals.holidayH || '—' }}</td>
                <td class="num-cell highlight">{{ (totals.overtimeH + totals.holidayH) || '—' }}</td>
                <td class="num-cell leave">{{ totals.halfDayAm || '—' }}</td>
                <td class="num-cell leave">{{ totals.halfDayPm || '—' }}</td>
                <td class="num-cell leave">{{ totals.paidLeave || '—' }}</td>
                <td class="num-cell leave">{{ totals.paidLeaveConsec || '—' }}</td>
                <td class="num-cell leave">{{ totals.paidLeaveCount || '—' }}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </template>

      <!-- 集計タブ -->
      <template v-if="activeTab === 'summary'">
        <div class="summary-bar">
          <span>{{ summaryNames.length }}名</span>
          <span style="font-size:12px;color:#6b7280;">— をクリックして登録</span>
        </div>
        <div class="table-wrap">
          <table class="stats-table summary-table">
            <thead>
              <tr>
                <th class="name-header">氏名</th>
                <th v-for="d in summaryDates" :key="d" class="date-header">{{ formatDateShort(d) }}</th>
                <th class="total-header">合計</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="name in summaryNames" :key="name">
                <td class="name-cell">{{ name }}</td>
                <td
                  v-for="d in summaryDates"
                  :key="d"
                  class="num-cell work"
                  :class="{
                    'cell-empty': !summaryGrid[name]?.[d],
                    'cell-label': summaryGrid[name]?.[d]?.label && !summaryGrid[name]?.[d]?.workH
                  }"
                  @click="summaryGrid[name]?.[d] ? null : openEditModal(name, d)"
                >{{ getSummaryDisplay(summaryGrid[name]?.[d]) }}</td>
                <td class="num-cell total-col">{{ summaryRowTotal(name) }}</td>
              </tr>
            </tbody>
            <tfoot>
              <tr class="total-row">
                <td class="total-label">合計</td>
                <td v-for="d in summaryDates" :key="d" class="num-cell work">
                  {{ summaryColTotal(d) || '—' }}
                </td>
                <td class="num-cell total-col">{{ totals.workH }}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </template>

      <!-- 編集モーダル -->
      <div v-if="editModal.visible" class="modal-overlay" @click.self="editModal.visible = false">
        <div class="modal-box">
          <div class="modal-title">勤務登録</div>
          <div class="modal-info">
            <span class="modal-name">{{ editModal.name }}</span>
            <span class="modal-date">{{ editModal.date }}</span>
          </div>
          <div class="modal-field">
            <label>種別</label>
            <select v-model="editModal.type" class="modal-select">
              <option value="normal">定時（8H）</option>
              <option value="paid_leave">有給</option>
              <option value="half_day_am">午前半休</option>
              <option value="half_day_pm">午後半休</option>
            </select>
          </div>
          <div v-if="editModal.error" class="modal-error">{{ editModal.error }}</div>
          <div class="modal-actions">
            <button class="btn btn-cancel" @click="editModal.visible = false">キャンセル</button>
            <button class="btn btn-primary" :disabled="editModal.saving" @click="saveEdit">
              {{ editModal.saving ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>

    </template>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
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
const allUsers = ref([])  // 全作業者リスト（申請なしの人も含む）
const activeTab = ref('detail')

// サブフィルター
const filterTeam = ref('')
const filterGroup = ref('')
const filterName = ref('')
const filterPaidLeave = ref('')

const teamOptions = computed(() => {
  const fromRows = rows.value.map(r => r.team)
  const fromUsers = allUsers.value.map(u => u.team)
  return [...new Set([...fromRows, ...fromUsers].filter(Boolean))].sort()
})
const groupOptions = computed(() => {
  const fromRows = rows.value.map(r => r.group)
  const fromUsers = allUsers.value.flatMap(u => [u.group, ...u.leaderUnitNames])
  return [...new Set([...fromRows, ...fromUsers].filter(Boolean))].sort()
})
const nameOptions = computed(() => [...new Set(rows.value.map(r => r.name).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'ja')))

const filteredRows = computed(() =>
  rows.value.filter(r =>
    (!filterTeam.value || r.team === filterTeam.value) &&
    (!filterGroup.value || r.group === filterGroup.value) &&
    (!filterName.value || r.name === filterName.value) &&
    (!filterPaidLeave.value ||
      (filterPaidLeave.value === 'any' && r.paidLeaveCount > 0) ||
      (filterPaidLeave.value === 'none' && !r.paidLeaveCount))
  )
)

const TYPE_LABELS = {
  normal: '定時',
  overtime: '時間外',
  holiday: '休日出勤',
  half_day_am: '午前半休',
  half_day_pm: '午後半休',
  paid_leave: '有給',
  paid_leave_consec: '連続有給',
}

// 編集モーダル
const editModal = reactive({
  visible: false,
  name: '',
  date: '',
  applicantId: null,
  type: 'normal',
  saving: false,
  error: '',
})

function openEditModal(name, date) {
  // 氏名からapplicantIdを取得（rows → allUsers の順で探す）
  const row = rows.value.find(r => r.name === name)
  const user = allUsers.value.find(u => u.name === name)
  const applicantId = row?.applicantId ?? user?.id ?? null
  if (!applicantId) return
  editModal.name = name
  editModal.date = date
  editModal.applicantId = applicantId
  editModal.type = 'normal'
  editModal.error = ''
  editModal.saving = false
  editModal.visible = true
}

async function saveEdit() {
  editModal.saving = true
  editModal.error = ''
  try {
    await api.overtime.createApplication({
      applicant: editModal.applicantId,
      work_date: editModal.date,
      application_type: editModal.type,
    })
    const savedType = editModal.type
    const savedName = editModal.name
    const savedDate = editModal.date
    const savedApplicantId = editModal.applicantId
    editModal.visible = false
    // 追加行をローカルに反映
    const baseRow = rows.value.find(r => r.name === savedName)
      || allUsers.value.find(u => u.name === savedName)
    const workH = savedType === 'normal' ? 8
      : (savedType === 'half_day_am' || savedType === 'half_day_pm') ? 4
      : 0
    rows.value.push({
      name: savedName,
      team: baseRow?.team || '',
      group: baseRow?.group || '',
      date: savedDate,
      typeLabel: TYPE_LABELS[savedType],
      startTime: '',
      endTime: '',
      workH,
      overtimeH: 0,
      holidayH: 0,
      halfDayAm: savedType === 'half_day_am',
      halfDayPm: savedType === 'half_day_pm',
      paidLeave: savedType === 'paid_leave',
      paidLeaveConsec: false,
      paidLeaveCount: savedType === 'paid_leave' ? 1
        : (savedType === 'half_day_am' || savedType === 'half_day_pm') ? 0.5 : 0,
      applicantId: savedApplicantId,
    })
  } catch (e) {
    const msg = e.response?.data?.non_field_errors?.[0]
      || e.response?.data?.detail
      || '保存に失敗しました'
    editModal.error = msg
  } finally {
    editModal.saving = false
  }
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
    paidLeaveCount: Math.round(filteredRows.value.reduce((s, r) => s + (r.paidLeaveCount || 0), 0) * 10) / 10,
  }
})

// 集計タブ用
// フィルタ条件に合致する全作業者（申請なしの人も含む）
const filteredUsers = computed(() => {
  let users = allUsers.value
  if (filterTeam.value) users = users.filter(u => u.team === filterTeam.value)
  if (filterGroup.value) users = users.filter(u =>
    u.group === filterGroup.value ||
    u.leaderUnitNames.includes(filterGroup.value)
  )
  if (filterName.value) users = users.filter(u => u.name === filterName.value)
  return users
})

const summaryNames = computed(() => {
  const names = new Set(filteredUsers.value.map(u => u.name))
  // 申請データにいるがallUsersにいない人も念のため含める
  for (const r of filteredRows.value) names.add(r.name)
  return [...names].sort((a, b) => a.localeCompare(b, 'ja'))
})

const summaryDates = computed(() =>
  [...new Set(filteredRows.value.map(r => r.date).filter(Boolean))].sort()
)

// summaryGrid[name][date] = { workH: number, label: string }
const summaryGrid = computed(() => {
  const grid = {}
  for (const row of filteredRows.value) {
    if (!grid[row.name]) grid[row.name] = {}
    const cell = grid[row.name][row.date] || { workH: 0, label: '' }
    if (row.workH) {
      cell.workH = Math.round((cell.workH + row.workH) * 10) / 10
    }
    if (!cell.label) {
      if (row.paidLeave || row.paidLeaveConsec) cell.label = '有給'
      else if (row.halfDayPm || row.halfDayAm) cell.label = '半休'
    }
    grid[row.name][row.date] = cell
  }
  return grid
})

function getSummaryDisplay(cell) {
  if (!cell) return '—'
  if (cell.label) return cell.label  // 「半休」「有給」はラベル優先
  if (cell.workH > 0) return cell.workH
  return '—'
}

function summaryRowTotal(name) {
  const byDate = summaryGrid.value[name] || {}
  const total = Object.values(byDate).reduce((s, c) => s + (c.workH || 0), 0)
  return total ? Math.round(total * 10) / 10 : '—'
}

function summaryColTotal(date) {
  let total = 0
  for (const name of summaryNames.value) {
    total += summaryGrid.value[name]?.[date]?.workH || 0
  }
  return total ? Math.round(total * 10) / 10 : 0
}

// 日付を短縮表示（MM/DD）
function formatDateShort(dateStr) {
  if (!dateStr) return ''
  const parts = dateStr.split('-')
  return `${parts[1]}/${parts[2]}`
}

const NEEDS_APPROVAL = new Set(['overtime', 'holiday', 'half_day_am'])
const APPROVED_STATUSES = new Set(['approved_manager', 'approved_chief', 'approved_supervisor', 'approved_leader'])

async function load() {
  loading.value = true
  rows.value = []
  try {
    // 全作業者リスト取得（申請なしの人も集計に含めるため）
    try {
      const usersRes = await api.accounts.getUsers({ page_size: 1000, is_active: true })
      const userList = usersRes.data?.results ?? usersRes.data ?? []
      allUsers.value = userList.map(u => ({
        id: u.id,
        name: `${u.last_name} ${u.first_name}`.trim() || u.username,
        team: u.profile?.team_name || '',
        // 申請データの group_name は profile.unit_name（ユニット名）と一致させる
        group: u.profile?.unit_name || '',
        // リーダーは担当ユニット名も持つ（unit_nameが空でも leader_unit_names で判定）
        leaderUnitNames: u.profile?.leader_unit_names || [],
      }))
    } catch (e) {
      console.warn('ユーザー一覧取得失敗:', e)
    }

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
      const applicantId = typeof app.applicant === 'object' ? app.applicant?.id : app.applicant
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
          startTime: app.start_time || '',
          endTime: app.end_time || '',
          workH: 0,
          overtimeH: 0,
          holidayH: 0,
          halfDayAm: false,
          halfDayPm: false,
          paidLeave: false,
          paidLeaveConsec: false,
          paidLeaveCount: 0,
          applicantId,
        }
        if (app.application_type === 'normal') {
          row.workH = 8
        } else if (app.application_type === 'overtime') {
          row.workH = Math.round((8 + h) * 10) / 10
          row.overtimeH = h
        } else if (app.application_type === 'half_day_am') {
          row.workH = Math.round((4 + h) * 10) / 10
          row.overtimeH = h
          row.halfDayAm = true
          row.paidLeaveCount = 0.5
        } else if (app.application_type === 'holiday') {
          if (app.work_start_time) {
            // 旧形式: work_start_timeあり → hoursは残業分のみ、パターン基準 + 残業
            const baseH = app.work_pattern_hours != null ? parseFloat(app.work_pattern_hours) : 8
            row.workH = Math.round((baseH + h) * 10) / 10
          } else if (h > 0) {
            // 新形式: 勤務時間帯入力あり → hoursがそのまま総勤務時間
            row.workH = h
          } else {
            // 新形式: 勤務時間帯未入力 → パターン時間 or 8H
            row.workH = app.work_pattern_hours != null ? parseFloat(app.work_pattern_hours) : 8
          }
          row.holidayH = row.workH
        } else if (app.application_type === 'half_day_pm') {
          row.workH = 4
          row.halfDayPm = true
          row.paidLeaveCount = 0.5
        } else if (app.application_type === 'paid_leave') {
          row.paidLeave = true
          row.paidLeaveCount = 1
        } else if (app.application_type === 'paid_leave_consec') {
          row.paidLeaveConsec = true
          row.paidLeaveCount = 1
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
  const headers = ['氏名', '班', 'グループ', '日付', '種別', '開始時間', '終了時間', '労働時間(H)', '残業(H)', '休日出勤(H)', '所定外(H)', '午前半休', '午後半休', '前日有給', '連続有給', '有給数']
  const data = filteredRows.value.map(r => [
    r.name, r.team, r.group, r.date, r.typeLabel,
    r.startTime || '', r.endTime || '',
    r.workH || '', r.overtimeH || '', r.holidayH || '',
    Math.round((r.overtimeH + r.holidayH) * 10) / 10 || '',
    r.halfDayAm ? '○' : '', r.halfDayPm ? '○' : '',
    r.paidLeave ? '○' : '', r.paidLeaveConsec ? '○' : '',
    r.paidLeaveCount || '',
  ])
  // 合計行
  data.push([
    '合計', '', '', '', '', '', '',
    totals.value.workH, totals.value.overtimeH || '', totals.value.holidayH || '',
    (totals.value.overtimeH + totals.value.holidayH) || '',
    totals.value.halfDayAm || '', totals.value.halfDayPm || '',
    totals.value.paidLeave || '', totals.value.paidLeaveConsec || '',
    totals.value.paidLeaveCount || '',
  ])

  const ws = XLSX.utils.aoa_to_sheet([headers, ...data])
  // 列幅設定
  ws['!cols'] = [18, 8, 10, 12, 10, 8, 8, 12, 10, 12, 10, 8, 8, 8, 8, 8].map(w => ({ wch: w }))

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
/* タブ */
.tab-bar {
  display: flex;
  gap: 0;
  margin-bottom: 12px;
  border-bottom: 2px solid #e5e7eb;
}
.tab-btn {
  padding: 8px 24px;
  font-size: 14px;
  font-weight: 600;
  border: none;
  background: none;
  cursor: pointer;
  color: #6b7280;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: color 0.15s, border-color 0.15s;
}
.tab-btn.active {
  color: #40916c;
  border-bottom-color: #40916c;
}
.tab-btn:hover:not(.active) {
  color: #374151;
}
/* サマリーバー */
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
.num-cell.total-col { font-weight: 700; color: #1f2a44; background: #f1f5f9; }
.stats-table tbody tr:hover { background: #f9fafb; }
.total-row { background: #f1f5f9; font-weight: 700; }
.total-row td { border-top: 2px solid #94a3b8; }
.total-label { font-weight: 700; color: #1f2a44; padding-left: 12px; }
/* 集計テーブル */
.summary-table .name-header { text-align: left; min-width: 120px; }
.summary-table .date-header { min-width: 52px; }
.summary-table .total-header { min-width: 60px; background: #e8f5e9; }
.cell-empty {
  cursor: pointer;
  color: #d1d5db;
}
.cell-empty:hover {
  background: #f0fdf4;
  color: #40916c;
}
.cell-label {
  text-align: center;
  color: #2563eb;
  font-weight: 600;
}
/* モーダル */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-box {
  background: white;
  border-radius: 10px;
  padding: 28px 32px;
  min-width: 320px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
}
.modal-title {
  font-size: 16px;
  font-weight: 700;
  color: #1f2a44;
  margin-bottom: 16px;
}
.modal-info {
  display: flex;
  gap: 16px;
  align-items: center;
  margin-bottom: 20px;
  font-size: 14px;
}
.modal-name { font-weight: 700; color: #1f2a44; }
.modal-date { color: #6b7280; }
.modal-field {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  font-size: 14px;
}
.modal-field label { color: #374151; font-weight: 600; width: 40px; }
.modal-select {
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 7px 12px;
  font-size: 14px;
  flex: 1;
}
.modal-error {
  color: #dc2626;
  font-size: 13px;
  margin-bottom: 12px;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.btn-cancel {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
}
.btn-cancel:hover { background: #e5e7eb; }
</style>
