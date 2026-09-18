<template>
  <div class="stats-page">
    <h1 class="page-title">労働時間統計 <DataSourceDialog title="労働時間統計" :sources="dsSources" /></h1>

    <div class="filters">
      <div class="filter-item">
        <label>期間</label>
        <input type="date" v-model="dateFrom" class="filter-input" />
        <span>〜</span>
        <input type="date" v-model="dateTo" class="filter-input" />
      </div>
      <button class="btn btn-primary" @click="load">表示</button>
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
      <button class="tab-btn" :class="{ active: activeTab === 'monthly' }" @click="activeTab = 'monthly'">月別</button>
    </div>

    <div v-if="hasSearched && loading" class="loading">読み込み中...</div>
    <div v-else-if="hasSearched && !rows.length" class="empty">データがありません</div>
    <template v-else-if="hasSearched">

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
                <th class="name-header">氏名</th>
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
          <span style="font-size:12px;color:#6b7280;">— をクリックして登録／定時をクリックして取消</span>
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
                    'cell-label': summaryGrid[name]?.[d]?.label && !summaryGrid[name]?.[d]?.workH,
                    'cell-record': summaryGrid[name]?.[d]?.normalApplicationId,
                  }"
                  @click="summaryGrid[name]?.[d] ? openExistingRecordModal(name, d) : openEditModal(name, d)"
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

      <!-- 月別タブ -->
      <template v-if="activeTab === 'monthly'">
        <div class="summary-bar">
          <span>{{ summaryNames.length }}名</span>
          <span class="summary-right">
            <span class="summary-total">
              労働時間合計: {{ totals.workH }}H　残業合計: {{ totals.overtimeH }}H　有給合計: {{ totals.paidLeaveCount }}回
            </span>
            <button class="btn btn-excel" @click="exportExcel">Excel出力</button>
          </span>
        </div>
        <div class="table-wrap">
          <table class="stats-table summary-table monthly-table">
            <thead>
              <tr>
                <th class="name-header" rowspan="2">氏名</th>
                <th v-for="month in monthlyColumns" :key="month" class="date-header" colspan="3">{{ formatMonthLabel(month) }}</th>
                <th class="total-header" colspan="4">合計</th>
              </tr>
              <tr>
                <template v-for="month in monthlyColumns" :key="`${month}-metrics`">
                  <th class="metric-header">残業(H)</th>
                  <th class="metric-header">労働(H)</th>
                  <th class="metric-header">有給(回)</th>
                </template>
                <th class="metric-header total-header">残業(H)</th>
                <th class="metric-header total-header">労働(H)</th>
                <th class="metric-header total-header">有給(回)</th>
                <th class="metric-header total-header">42H超え回数</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="name in summaryNames" :key="name">
                <td class="name-cell">{{ name }}</td>
                <template v-for="month in monthlyColumns" :key="`${name}-${month}`">
                  <td class="num-cell">{{ monthlyGrid[name]?.[month]?.overtimeH || '—' }}</td>
                  <td class="num-cell work">{{ monthlyGrid[name]?.[month]?.workH || '—' }}</td>
                  <td class="num-cell leave">{{ monthlyGrid[name]?.[month]?.paidLeaveCount || '—' }}</td>
                </template>
                <td class="num-cell total-col">{{ monthlyRowTotal(name, 'overtimeH') }}</td>
                <td class="num-cell total-col">{{ monthlyRowTotal(name, 'workH') }}</td>
                <td class="num-cell total-col">{{ monthlyRowTotal(name, 'paidLeaveCount') }}</td>
                <td class="num-cell total-col">{{ monthlyOver42Count(name) || '—' }}</td>
              </tr>
            </tbody>
            <tfoot>
              <tr class="total-row">
                <td class="total-label">合計</td>
                <template v-for="month in monthlyColumns" :key="`total-${month}`">
                  <td class="num-cell highlight">{{ monthlyColTotal(month, 'overtimeH') || '—' }}</td>
                  <td class="num-cell work">{{ monthlyColTotal(month, 'workH') || '—' }}</td>
                  <td class="num-cell leave">{{ monthlyColTotal(month, 'paidLeaveCount') || '—' }}</td>
                </template>
                <td class="num-cell total-col">{{ totals.overtimeH || '—' }}</td>
                <td class="num-cell total-col">{{ totals.workH }}</td>
                <td class="num-cell total-col">{{ totals.paidLeaveCount || '—' }}</td>
                <td class="num-cell total-col">{{ totalOver42Count || '—' }}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </template>

      <!-- 編集モーダル -->
      <div v-if="editModal.visible" class="modal-overlay" @click.self="editModal.visible = false">
        <div class="modal-box">
          <div class="modal-title">{{ editModal.mode === 'delete' ? '勤務記録の取消' : '勤務登録' }}</div>
          <div class="modal-info">
            <span class="modal-name">{{ editModal.name }}</span>
            <span class="modal-date">{{ editModal.date }}</span>
          </div>
          <div v-if="editModal.mode === 'create'" class="modal-field">
            <label>種別</label>
            <select v-model="editModal.type" class="modal-select">
              <option value="normal">定時（8H）</option>
              <option value="paid_leave">有給</option>
              <option value="half_day_am">午前半休</option>
              <option value="half_day_pm">午後半休</option>
            </select>
          </div>
          <p v-else class="modal-message">この日の定時（8H）勤務記録を取り消します。取消後は「—」に戻ります。</p>
          <div v-if="editModal.error" class="modal-error">{{ editModal.error }}</div>
          <div class="modal-actions">
            <button class="btn btn-cancel" @click="editModal.visible = false">キャンセル</button>
            <button class="btn" :class="editModal.mode === 'delete' ? 'btn-danger' : 'btn-primary'" :disabled="editModal.saving" @click="editModal.mode === 'delete' ? deleteNormalRecord() : saveEdit()">
              {{ editModal.saving ? '処理中...' : editModal.mode === 'delete' ? '取消' : '保存' }}
            </button>
          </div>
        </div>
      </div>

    </template>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: 't_overtime_application', desc: '残業・有給申請データの取得・勤務登録' },
  { op: '読み取り', table: 'auth_user / accounts_userprofile', desc: '作業者一覧・所属の取得' },
  { op: '読み取り', table: 'accounts_department', desc: '所属組織による絞り込み' },
  { op: '読み取り', table: 'm_calendar / m_calendar_day', desc: 'DAISOカレンダー非稼働日の取得' },
]

// デフォルト: 今月の1日〜末日
const today = new Date()
const pad = (n) => String(n).padStart(2, '0')
const y = today.getFullYear()
const m = today.getMonth() + 1
const lastDay = new Date(y, m, 0).getDate()
const dateFrom = ref(`${y}-${pad(m)}-01`)
const dateTo = ref(`${y}-${pad(m)}-${pad(lastDay)}`)

const loading = ref(false)
const hasSearched = ref(false)
const rows = ref([])
const allUsers = ref([])  // 全作業者リスト（申請なしの人も含む）
const activeTab = ref('detail')
const productionSessions = ref([])
const unitPriceByCode = ref({})

// サブフィルター
const filterTeam = ref('')
const filterGroup = ref('')
const filterName = ref('')
const filterPaidLeave = ref('')

const teamOptions = computed(() =>
  [...new Set(allUsers.value.map(u => u.team).filter(Boolean))].sort()
)
const groupOptions = computed(() => {
  const targetUsers = filterTeam.value
    ? allUsers.value.filter((u) => u.team === filterTeam.value)
    : allUsers.value
  return [...new Set(targetUsers.flatMap(u => [u.group, ...u.leaderUnitNames]).filter(Boolean))].sort()
})
const nameOptions = computed(() =>
  [...new Set(allUsers.value.map(u => u.name).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'ja'))
)

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

const normalizePersonName = (value) => String(value || '').replace(/\s+/g, '').toLowerCase()

const userMetaByName = computed(() => {
  const map = new Map()
  for (const user of allUsers.value) {
    const key = normalizePersonName(user.name)
    if (!key) continue
    map.set(key, { team: user.team || '', group: user.group || '' })
  }
  for (const row of rows.value) {
    const key = normalizePersonName(row.name)
    if (!key || map.has(key)) continue
    map.set(key, { team: row.team || '', group: row.group || '' })
  }
  return map
})

const attendanceHoursByPersonDate = computed(() => {
  const map = new Map()
  for (const row of rows.value) {
    const key = `${normalizePersonName(row.name)}|${row.date}`
    map.set(key, (map.get(key) || 0) + Number(row.workH || 0))
  }
  return map
})

const productivityRows = computed(() => {
  const aggregate = new Map()
  for (const session of productionSessions.value) {
    const nameRaw = String(session?.operator_name || '').trim()
    const nameKey = normalizePersonName(nameRaw)
    const date = String(session?.plan_date || session?.work_date || '').slice(0, 10)
    if (!nameKey || !date) continue
    const qty = Number(session?.production_qty || 0)
    if (qty === 0) continue
    const seconds = Math.max(Number(session?.effective_work_seconds || 0), 0)
    const productCode = String(session?.product_code || '').trim()
    const unitPrice = Number(unitPriceByCode.value[productCode] || 0)
    const amount = qty * unitPrice
    const key = `${nameKey}|${date}`
    if (!aggregate.has(key)) {
      aggregate.set(key, {
        nameKey,
        name: nameRaw || '—',
        date,
        qtyTotal: 0,
        amountTotal: 0,
        sessionSeconds: 0,
      })
    }
    const target = aggregate.get(key)
    target.qtyTotal += qty
    target.amountTotal += amount
    target.sessionSeconds += seconds
    if (nameRaw && target.name === '—') target.name = nameRaw
  }

  const rowsOut = []
  for (const item of aggregate.values()) {
    const meta = userMetaByName.value.get(item.nameKey) || {}
    const sessionHours = item.sessionSeconds / 3600
    const attendanceHours = Number(attendanceHoursByPersonDate.value.get(`${item.nameKey}|${item.date}`) || 0)
    rowsOut.push({
      name: item.name,
      team: meta.team || '',
      group: meta.group || '',
      date: item.date,
      qtyTotal: Math.round(item.qtyTotal * 1000) / 1000,
      amountTotal: Math.round(item.amountTotal * 100) / 100,
      sessionHours: Math.round(sessionHours * 1000) / 1000,
      attendanceHours: Math.round(attendanceHours * 1000) / 1000,
      sessionRate: sessionHours > 0 ? Math.round((item.amountTotal / sessionHours) * 100) / 100 : null,
      attendanceRate: attendanceHours > 0 ? Math.round((item.amountTotal / attendanceHours) * 100) / 100 : null,
    })
  }

  // 日付別ランキング（出来高、時間当たり加工費）
  const byDate = new Map()
  for (const row of rowsOut) {
    if (!byDate.has(row.date)) byDate.set(row.date, [])
    byDate.get(row.date).push(row)
  }
  for (const dateRows of byDate.values()) {
    const qtySorted = [...dateRows].sort((a, b) => b.qtyTotal - a.qtyTotal)
    let prevQty = null
    let qtyRank = 0
    qtySorted.forEach((row, idx) => {
      if (prevQty === null || row.qtyTotal !== prevQty) qtyRank = idx + 1
      row.qtyRank = qtyRank
      prevQty = row.qtyTotal
    })

    const rateSorted = [...dateRows]
      .filter((row) => row.sessionRate != null)
      .sort((a, b) => b.sessionRate - a.sessionRate)
    let prevRate = null
    let rateRank = 0
    rateSorted.forEach((row, idx) => {
      if (prevRate === null || row.sessionRate !== prevRate) rateRank = idx + 1
      row.rateRank = rateRank
      prevRate = row.sessionRate
    })
    dateRows.forEach((row) => {
      if (row.rateRank == null) row.rateRank = null
    })

    const attendanceRateSorted = [...dateRows]
      .filter((row) => row.attendanceRate != null)
      .sort((a, b) => b.attendanceRate - a.attendanceRate)
    let prevAttendanceRate = null
    let attendanceRateRank = 0
    attendanceRateSorted.forEach((row, idx) => {
      if (prevAttendanceRate === null || row.attendanceRate !== prevAttendanceRate) attendanceRateRank = idx + 1
      row.attendanceRateRank = attendanceRateRank
      prevAttendanceRate = row.attendanceRate
    })
    dateRows.forEach((row) => {
      if (row.attendanceRateRank == null) row.attendanceRateRank = null
    })

    const maxQty = Math.max(...dateRows.map((r) => Number(r.qtyTotal || 0)), 0)
    const maxRate = Math.max(...dateRows.map((r) => Number(r.sessionRate || 0)), 0)
    const maxAttendanceRate = Math.max(...dateRows.map((r) => Number(r.attendanceRate || 0)), 0)
    dateRows.forEach((row) => {
      row.qtyIntensity = maxQty > 0 ? Number(row.qtyTotal || 0) / maxQty : 0
      row.rateIntensity = maxRate > 0 && row.sessionRate != null ? Number(row.sessionRate || 0) / maxRate : 0
      row.attendanceRateIntensity = maxAttendanceRate > 0 && row.attendanceRate != null
        ? Number(row.attendanceRate || 0) / maxAttendanceRate
        : 0
    })
  }

  rowsOut.sort((a, b) => {
    if (a.date !== b.date) return a.date < b.date ? -1 : 1
    return a.name.localeCompare(b.name, 'ja')
  })
  return rowsOut
})

const filteredProductivityRows = computed(() =>
  {
    const filtered = productivityRows.value
      .filter((row) =>
        (!filterTeam.value || row.team === filterTeam.value) &&
        (!filterGroup.value || row.group === filterGroup.value) &&
        (!filterName.value || row.name === filterName.value),
      )
      .map((row) => ({ ...row }))

    // 表示条件で絞り込んだ後に、日別順位と濃淡を再計算する
    const byDate = new Map()
    for (const row of filtered) {
      if (!byDate.has(row.date)) byDate.set(row.date, [])
      byDate.get(row.date).push(row)
    }
    for (const dateRows of byDate.values()) {
      const qtySorted = [...dateRows].sort((a, b) => b.qtyTotal - a.qtyTotal)
      let prevQty = null
      let qtyRank = 0
      qtySorted.forEach((row, idx) => {
        if (prevQty === null || row.qtyTotal !== prevQty) qtyRank = idx + 1
        row.qtyRank = qtyRank
        prevQty = row.qtyTotal
      })

      const rateSorted = [...dateRows]
        .filter((row) => row.sessionRate != null)
        .sort((a, b) => b.sessionRate - a.sessionRate)
      let prevRate = null
      let rateRank = 0
      rateSorted.forEach((row, idx) => {
        if (prevRate === null || row.sessionRate !== prevRate) rateRank = idx + 1
        row.rateRank = rateRank
        prevRate = row.sessionRate
      })
      dateRows.forEach((row) => {
        if (row.rateRank == null) row.rateRank = null
      })

      const attendanceRateSorted = [...dateRows]
        .filter((row) => row.attendanceRate != null)
        .sort((a, b) => b.attendanceRate - a.attendanceRate)
      let prevAttendanceRate = null
      let attendanceRateRank = 0
      attendanceRateSorted.forEach((row, idx) => {
        if (prevAttendanceRate === null || row.attendanceRate !== prevAttendanceRate) attendanceRateRank = idx + 1
        row.attendanceRateRank = attendanceRateRank
        prevAttendanceRate = row.attendanceRate
      })
      dateRows.forEach((row) => {
        if (row.attendanceRateRank == null) row.attendanceRateRank = null
      })

      const maxQty = Math.max(...dateRows.map((r) => Number(r.qtyTotal || 0)), 0)
      const maxRate = Math.max(...dateRows.map((r) => Number(r.sessionRate || 0)), 0)
      const maxAttendanceRate = Math.max(...dateRows.map((r) => Number(r.attendanceRate || 0)), 0)
      dateRows.forEach((row) => {
        row.qtyIntensity = maxQty > 0 ? Number(row.qtyTotal || 0) / maxQty : 0
        row.rateIntensity = maxRate > 0 && row.sessionRate != null ? Number(row.sessionRate || 0) / maxRate : 0
        row.attendanceRateIntensity = maxAttendanceRate > 0 && row.attendanceRate != null
          ? Number(row.attendanceRate || 0) / maxAttendanceRate
          : 0
      })
    }

    return filtered
  },
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
  mode: 'create',
  name: '',
  date: '',
  applicantId: null,
  applicationId: null,
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
  editModal.mode = 'create'
  editModal.date = date
  editModal.applicantId = applicantId
  editModal.applicationId = null
  editModal.type = 'normal'
  editModal.error = ''
  editModal.saving = false
  editModal.visible = true
}

function openExistingRecordModal(name, date) {
  const cell = summaryGrid.value[name]?.[date]
  if (!cell?.normalApplicationId) return
  editModal.name = name
  editModal.mode = 'delete'
  editModal.date = date
  editModal.applicantId = cell.applicantId
  editModal.applicationId = cell.normalApplicationId
  editModal.error = ''
  editModal.saving = false
  editModal.visible = true
}

async function saveEdit() {
  editModal.saving = true
  editModal.error = ''
  try {
    const res = await api.overtime.createApplication({
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
      applicationId: res.data?.id,
      applicationType: savedType,
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

async function deleteNormalRecord() {
  if (!editModal.applicationId) return
  if (!confirm(`${editModal.name}さんの${editModal.date}の定時勤務記録を取り消しますか？`)) return
  editModal.saving = true
  editModal.error = ''
  try {
    await api.overtime.deleteApplication(editModal.applicationId)
    editModal.visible = false
    await load()
  } catch (e) {
    editModal.error = e.response?.data?.detail || '取消に失敗しました'
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

const monthlyColumns = computed(() => {
  const start = dateFrom.value ? new Date(dateFrom.value) : null
  const end = dateTo.value ? new Date(dateTo.value) : null
  if (!start || !end || Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || start > end) return []
  const months = []
  const cursor = new Date(start.getFullYear(), start.getMonth(), 1)
  const last = new Date(end.getFullYear(), end.getMonth(), 1)
  while (cursor <= last) {
    months.push(`${cursor.getFullYear()}-${pad(cursor.getMonth() + 1)}`)
    cursor.setMonth(cursor.getMonth() + 1)
  }
  return months
})

// summaryGrid[name][date] = { workH: number, label: string }
const summaryGrid = computed(() => {
  const grid = {}
  for (const row of filteredRows.value) {
    if (!grid[row.name]) grid[row.name] = {}
    const cell = grid[row.name][row.date] || {
      workH: 0,
      label: '',
      applicantId: row.applicantId,
      normalApplicationId: null,
    }
    if (row.workH) {
      cell.workH = Math.round((cell.workH + row.workH) * 10) / 10
    }
    if (!cell.label) {
      if (row.paidLeave || row.paidLeaveConsec) cell.label = '有給'
      else if (row.halfDayPm || row.halfDayAm) cell.label = '半休'
    }
    if (row.applicationType === 'normal') cell.normalApplicationId = row.applicationId
    grid[row.name][row.date] = cell
  }
  return grid
})

const monthlyGrid = computed(() => {
  const grid = {}
  for (const row of filteredRows.value) {
    const month = String(row.date || '').slice(0, 7)
    if (!month) continue
    if (!grid[row.name]) grid[row.name] = {}
    const cell = grid[row.name][month] || { workH: 0, overtimeH: 0, paidLeaveCount: 0 }
    cell.workH = Math.round((cell.workH + Number(row.workH || 0)) * 10) / 10
    cell.overtimeH = Math.round((cell.overtimeH + Number(row.overtimeH || 0) + Number(row.holidayH || 0)) * 10) / 10
    cell.paidLeaveCount = Math.round((cell.paidLeaveCount + Number(row.paidLeaveCount || 0)) * 10) / 10
    grid[row.name][month] = cell
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

function monthlyRowTotal(name, key) {
  const byMonth = monthlyGrid.value[name] || {}
  const total = Object.values(byMonth).reduce((sum, cell) => sum + Number(cell[key] || 0), 0)
  return total ? Math.round(total * 10) / 10 : '—'
}

function monthlyColTotal(month, key) {
  let total = 0
  for (const name of summaryNames.value) {
    total += Number(monthlyGrid.value[name]?.[month]?.[key] || 0)
  }
  return total ? Math.round(total * 10) / 10 : 0
}

function monthlyOver42Count(name) {
  const byMonth = monthlyGrid.value[name] || {}
  return Object.values(byMonth).filter((cell) => Number(cell?.overtimeH || 0) > 42).length
}

const totalOver42Count = computed(() =>
  summaryNames.value.reduce((sum, name) => sum + monthlyOver42Count(name), 0),
)

// 日付を短縮表示（MM/DD）
function formatDateShort(dateStr) {
  if (!dateStr) return ''
  const parts = dateStr.split('-')
  return `${parts[1]}/${parts[2]}`
}

function formatMonthLabel(monthStr) {
  if (!monthStr) return ''
  const parts = monthStr.split('-')
  return `${parts[0]}/${parts[1]}`
}

function formatDateRangeLabel() {
  return `${dateFrom.value} ～ ${dateTo.value}`
}

function formatMetric(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '—'
  return num.toLocaleString('ja-JP', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

function formatUtilization(sessionHours, attendanceHours) {
  const s = Number(sessionHours || 0)
  const a = Number(attendanceHours || 0)
  if (!Number.isFinite(s) || !Number.isFinite(a) || a <= 0) return '—'
  const ratio = (s / a) * 100
  return `${ratio.toLocaleString('ja-JP', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`
}

function heatStyle(intensity) {
  const v = Math.max(0, Math.min(Number(intensity || 0), 1))
  if (v <= 0) return {}
  const alpha = 0.22 + v * 0.48
  return {
    backgroundColor: `rgba(34, 197, 94, ${alpha.toFixed(3)})`,
    fontWeight: v >= 0.85 ? 700 : 500,
  }
}

const dateBandIndexMap = computed(() => {
  const map = {}
  const uniqueDates = [...new Set(filteredProductivityRows.value.map((row) => row.date))]
  uniqueDates.forEach((date, idx) => {
    map[date] = idx % 4
  })
  return map
})

function dateBandClass(date) {
  const idx = dateBandIndexMap.value[date]
  if (idx === 0) return 'date-band-0'
  if (idx === 1) return 'date-band-1'
  if (idx === 2) return 'date-band-2'
  if (idx === 3) return 'date-band-3'
  return ''
}

function isDateStart(index) {
  if (index === 0) return true
  const current = filteredProductivityRows.value[index]
  const prev = filteredProductivityRows.value[index - 1]
  if (!current || !prev) return false
  return current.date !== prev.date
}

const NEEDS_APPROVAL = new Set(['overtime', 'holiday', 'half_day_am'])
const APPROVED_STATUSES = new Set(['approved_manager', 'approved_chief', 'approved_supervisor', 'approved_leader'])
const COUNTABLE_END_ACTIONS = new Set(['END', 'PAUSE'])

const normalizeList = (payload) => {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.results)) return payload.results
  return []
}

function scopeUsersForStats(userList) {
  const profile = authState.user?.profile || {}
  const role = profile.role || ''
  if (role !== 'leader') return userList

  const unitIds = new Set(
    [profile.unit_id, ...(Array.isArray(profile.leader_units) ? profile.leader_units : [])]
      .filter(Boolean)
      .map(Number)
  )

  if (!unitIds.size) return userList.filter((user) => Number(user.id) === Number(authState.user?.id))

  return userList.filter((user) => (
    Number(user.id) === Number(authState.user?.id) ||
    unitIds.has(Number(user.profile?.unit))
  ))
}

const loadUsers = async () => {
  try {
    const usersRes = await api.accounts.getUsers({ page_size: 1000, is_active: true })
    const rawUsers = usersRes.data?.results ?? usersRes.data ?? []
    const userList = scopeUsersForStats(rawUsers)
    allUsers.value = userList.map(u => ({
      id: u.id,
      name: `${u.last_name} ${u.first_name}`.trim() || u.username,
      team: u.profile?.team_name || '',
      group: u.profile?.unit_name || '',
      leaderUnitNames: u.profile?.leader_unit_names || [],
    }))
  } catch (e) {
    console.warn('ユーザー一覧取得失敗:', e)
  }
}

const loadProductionMetrics = async () => {
  productionSessions.value = []
  unitPriceByCode.value = {}

  const [laserRes, brakeRes, pwsRes] = await Promise.all([
    api.laserActuals.getLaserActuals({
      page_size: 1000,
      work_date__gte: dateFrom.value,
      work_date__lte: dateTo.value,
      ordering: '-work_date,-created_at',
    }),
    api.brakeLineActuals.getSessions({
      start_date: dateFrom.value,
      end_date: dateTo.value,
    }),
    api.processRealtime.getSessions({
      limit: 10000,
      plan_date_start: dateFrom.value,
      plan_date_end: dateTo.value,
    }),
  ])

  const laserRecords = normalizeList(laserRes.data)
  const brakeSessions = normalizeList(brakeRes.data)
  const pwsSessions = normalizeList(pwsRes.data)

  // レーザー: START/RESUME -> END/PAUSE を設備単位でペアリングして実作業秒を算出
  const laserByEquipment = {}
  for (const row of laserRecords) {
    const key = row?.equipment_code || '__unknown__'
    if (!laserByEquipment[key]) laserByEquipment[key] = []
    laserByEquipment[key].push(row)
  }
  const laserDurationById = new Map()
  for (const rows of Object.values(laserByEquipment)) {
    const sorted = [...rows].sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
    let pendingStart = null
    for (const row of sorted) {
      const action = String(row?.operator_action || '').toUpperCase()
      const isOpen = action === 'START' || action === 'RESUME'
      if (isOpen) {
        pendingStart = row
      } else if (pendingStart) {
        const diff = new Date(row.created_at) - new Date(pendingStart.created_at)
        laserDurationById.set(row.id, Math.max(0, Math.round(diff / 1000)))
        pendingStart = null
      }
    }
  }

  const laserItems = laserRecords.flatMap((row) => {
    const action = String(row?.operator_action || '').toUpperCase()
    if (!COUNTABLE_END_ACTIONS.has(action)) return []
    const duration = laserDurationById.get(row?.id) || 0
    const details = normalizeList(row?.details).filter(
      (detail) => String(detail?.detail_type || '').toUpperCase() === 'COMPONENT',
    )
    const buildOne = (detail) => ({
      id: row?.id,
      record_source: 'LASER',
      operator_name: row?.created_by_name || row?.updated_by_name || '—',
      plan_date: row?.work_date || null,
      work_date: row?.work_date || null,
      product_code: detail?.product_code || '',
      production_qty: Number(detail?.total_qty || 0),
      effective_work_seconds: duration,
      session_type: 'WORK',
      end_action: action,
    })
    if (!details.length) return [buildOne(null)]
    return details.map((detail) => buildOne(detail))
  })

  // ブレーキ系は専用セッションを採用
  const brakeItems = brakeSessions.map((row) => ({
    ...row,
    record_source: 'BRAKE',
  }))

  // PWSはBRAKE/LASER由来を除外して重複防止
  const pwsItems = pwsSessions.filter((row) => {
    const source = String(row?.record_source || '').toUpperCase()
    return source !== 'BRAKE' && source !== 'LASER'
  })

  const merged = [...laserItems, ...brakeItems, ...pwsItems]
  const countableSessions = merged.filter((row) => {
    if (String(row?.session_type || '') !== 'WORK') return false
    const endAction = String(row?.end_action || '').toUpperCase()
    if (!COUNTABLE_END_ACTIONS.has(endAction)) return false
    return Number(row?.production_qty || 0) !== 0
  })

  productionSessions.value = countableSessions

  const productCodes = [...new Set(
    countableSessions
      .map((row) => String(row?.product_code || '').trim())
      .filter(Boolean),
  )]
  if (!productCodes.length) return

  const codePriceMap = {}
  const chunkSize = 200
  for (let i = 0; i < productCodes.length; i += chunkSize) {
    const chunk = productCodes.slice(i, i + chunkSize)
    const productsRes = await api.products.getProductsByCodesIn(chunk)
    const products = Array.isArray(productsRes.data?.results)
      ? productsRes.data.results
      : Array.isArray(productsRes.data)
        ? productsRes.data
        : []
    for (const p of products) {
      const code = String(p?.product_code || '').trim()
      if (!code) continue
      codePriceMap[code] = Number(p?.unit_price || 0)
    }
  }
  unitPriceByCode.value = codePriceMap
}

async function load() {
  hasSearched.value = true
  loading.value = true
  rows.value = []
  try {
    if (!allUsers.value.length) await loadUsers()

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
      const midnightH = parseFloat(app.midnight_hours ?? 0)
      const overtimeTotalH = Math.round((h + midnightH) * 10) / 10
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
          applicationId: app.id,
          applicationType: app.application_type,
        }
        if (app.application_type === 'normal') {
          row.workH = 8
        } else if (app.application_type === 'overtime') {
          row.workH = Math.round((8 + overtimeTotalH) * 10) / 10
          row.overtimeH = overtimeTotalH
        } else if (app.application_type === 'half_day_am') {
          row.workH = Math.round((4 + overtimeTotalH) * 10) / 10
          row.overtimeH = overtimeTotalH
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

const EXCEL_THEME = {
  titleFill: '1F6F5F',
  titleFont: 'FFFFFF',
  metaLabelFill: 'DDEEE8',
  headerFill: 'D6E4F0',
  subHeaderFill: 'EEF5FB',
  totalFill: 'E8F5E9',
  overtimeAlertFill: 'FDE2E1',
  overtimeAlertFont: 'B42318',
  border: 'B7C4D2',
}

function excelBorder() {
  return {
    top: { style: 'thin', color: { argb: EXCEL_THEME.border } },
    left: { style: 'thin', color: { argb: EXCEL_THEME.border } },
    bottom: { style: 'thin', color: { argb: EXCEL_THEME.border } },
    right: { style: 'thin', color: { argb: EXCEL_THEME.border } },
  }
}

function styleCell(cell, {
  bold = false,
  align = 'center',
  vertical = 'middle',
  bg = null,
  color = null,
  numFmt = null,
} = {}) {
  cell.font = { bold, color: color ? { argb: color } : undefined, size: 11 }
  cell.alignment = { horizontal: align, vertical, wrapText: true }
  cell.border = excelBorder()
  if (bg) {
    cell.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: bg },
    }
  }
  if (numFmt) cell.numFmt = numFmt
}

async function saveWorkbook(workbook, filename) {
  const buffer = await workbook.xlsx.writeBuffer()
  const blob = new Blob([buffer], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

function addMetaRow(sheet, rowIndex, label, value, lastCol) {
  sheet.mergeCells(rowIndex, 2, rowIndex, lastCol)
  const labelCell = sheet.getCell(rowIndex, 1)
  const valueCell = sheet.getCell(rowIndex, 2)
  labelCell.value = label
  valueCell.value = value
  styleCell(labelCell, { bold: true, bg: EXCEL_THEME.metaLabelFill })
  styleCell(valueCell, { align: 'left' })
  for (let col = 3; col <= lastCol; col += 1) {
    styleCell(sheet.getCell(rowIndex, col), { align: 'left' })
  }
}

function setFrozenView(sheet) {
  sheet.views = [{ state: 'frozen', ySplit: 5, xSplit: 1 }]
}

function isMonthlyOvertimeColumn(colIndex, monthlyMetricLastCol) {
  if (colIndex < 2 || colIndex > monthlyMetricLastCol) return false
  return (colIndex - 2) % 3 === 0
}

function isOvertimeAlertValue(value) {
  return Number(value || 0) > 42
}

async function exportExcel() {
  const ExcelJS = (await import('exceljs')).default
  const isMonthlyTab = activeTab.value === 'monthly'
  const workbook = new ExcelJS.Workbook()
  const sheet = workbook.addWorksheet(isMonthlyTab ? '月別労働時間統計' : '労働時間統計')

  if (isMonthlyTab) {
    const monthlyMetricLastCol = 1 + (monthlyColumns.value.length * 3)
    const lastCol = monthlyMetricLastCol + 4
    sheet.mergeCells(1, 1, 1, lastCol)
    const titleCell = sheet.getCell(1, 1)
    titleCell.value = '労働時間統計（月別）'
    styleCell(titleCell, { bold: true, align: 'left', bg: EXCEL_THEME.titleFill, color: EXCEL_THEME.titleFont })

    addMetaRow(sheet, 2, '期間', formatDateRangeLabel(), lastCol)
    addMetaRow(sheet, 3, '抽出条件', `班:${filterTeam.value || '全班'} / グループ:${filterGroup.value || '全グループ'} / 氏名:${filterName.value || '全員'} / 有給:${filterPaidLeave.value === 'any' ? '有給あり' : filterPaidLeave.value === 'none' ? '有給なし' : '全て'}`, lastCol)
    addMetaRow(sheet, 4, '集計', `労働時間合計 ${totals.value.workH}H / 残業合計 ${totals.value.overtimeH || 0}H / 有給合計 ${totals.value.paidLeaveCount || 0}回`, lastCol)

    sheet.mergeCells(5, 1, 6, 1)
    sheet.getCell(5, 1).value = '氏名'
    styleCell(sheet.getCell(5, 1), { bold: true, bg: EXCEL_THEME.headerFill })
    styleCell(sheet.getCell(6, 1), { bold: true, bg: EXCEL_THEME.headerFill })

    let col = 2
    for (const month of monthlyColumns.value) {
      sheet.mergeCells(5, col, 5, col + 2)
      sheet.getCell(5, col).value = formatMonthLabel(month)
      styleCell(sheet.getCell(5, col), { bold: true, bg: EXCEL_THEME.headerFill })
      styleCell(sheet.getCell(5, col + 1), { bold: true, bg: EXCEL_THEME.headerFill })
      styleCell(sheet.getCell(5, col + 2), { bold: true, bg: EXCEL_THEME.headerFill })
      ;['残業(H)', '労働(H)', '有給(回)'].forEach((label, idx) => {
        const cell = sheet.getCell(6, col + idx)
        cell.value = label
        styleCell(cell, { bold: true, bg: EXCEL_THEME.subHeaderFill })
      })
      col += 3
    }

    sheet.mergeCells(5, col, 5, col + 3)
    sheet.getCell(5, col).value = '合計'
    styleCell(sheet.getCell(5, col), { bold: true, bg: EXCEL_THEME.totalFill })
    styleCell(sheet.getCell(5, col + 1), { bold: true, bg: EXCEL_THEME.totalFill })
    styleCell(sheet.getCell(5, col + 2), { bold: true, bg: EXCEL_THEME.totalFill })
    styleCell(sheet.getCell(5, col + 3), { bold: true, bg: EXCEL_THEME.totalFill })
    ;['残業(H)', '労働(H)', '有給(回)', '42H超え回数'].forEach((label, idx) => {
      const cell = sheet.getCell(6, col + idx)
      cell.value = label
      styleCell(cell, { bold: true, bg: EXCEL_THEME.totalFill })
    })

    let rowIndex = 7
    for (const name of summaryNames.value) {
      const row = [name]
      for (const month of monthlyColumns.value) {
        const cell = monthlyGrid.value[name]?.[month] || {}
        row.push(cell.overtimeH || '', cell.workH || '', cell.paidLeaveCount || '')
      }
      row.push(
        monthlyRowTotal(name, 'overtimeH') || '',
        monthlyRowTotal(name, 'workH') || '',
        monthlyRowTotal(name, 'paidLeaveCount') || '',
        monthlyOver42Count(name) || '',
      )
      sheet.addRow(row)
      styleCell(sheet.getCell(rowIndex, 1), { bold: true, align: 'left' })
      for (let c = 2; c <= lastCol; c += 1) {
        const value = sheet.getCell(rowIndex, c).value
        const isAlert = isMonthlyOvertimeColumn(c, monthlyMetricLastCol) && isOvertimeAlertValue(value)
        styleCell(sheet.getCell(rowIndex, c), {
          align: c % 3 === 1 ? 'center' : 'right',
          bg: isAlert ? EXCEL_THEME.overtimeAlertFill : (c > monthlyMetricLastCol ? 'F7FBF7' : null),
          color: isAlert ? EXCEL_THEME.overtimeAlertFont : null,
          numFmt: c === lastCol ? '0' : '0.0',
        })
      }
      rowIndex += 1
    }

    sheet.addRow([
      '合計',
      ...monthlyColumns.value.flatMap((month) => [
        monthlyColTotal(month, 'overtimeH') || '',
        monthlyColTotal(month, 'workH') || '',
        monthlyColTotal(month, 'paidLeaveCount') || '',
      ]),
      totals.value.overtimeH || '',
      totals.value.workH || '',
      totals.value.paidLeaveCount || '',
      totalOver42Count.value || '',
    ])
    for (let c = 1; c <= lastCol; c += 1) {
      styleCell(sheet.getCell(rowIndex, c), {
        bold: true,
        align: c === 1 ? 'left' : (c % 3 === 1 ? 'center' : 'right'),
        bg: EXCEL_THEME.totalFill,
        numFmt: c === 1 ? null : (c === lastCol ? '0' : '0.0'),
      })
    }

    sheet.columns = [{ width: 20 }, ...Array.from({ length: lastCol - 2 }, () => ({ width: 12 })), { width: 14 }]
  } else {
    const headers = ['氏名', '班', 'グループ', '日付', '種別', '開始時間', '終了時間', '労働時間(H)', '残業(H)', '休日出勤(H)', '所定外(H)', '午前半休', '午後半休', '前日有給', '連続有給', '有給数']
    const lastCol = headers.length
    sheet.mergeCells(1, 1, 1, lastCol)
    const titleCell = sheet.getCell(1, 1)
    titleCell.value = '労働時間統計（詳細）'
    styleCell(titleCell, { bold: true, align: 'left', bg: EXCEL_THEME.titleFill, color: EXCEL_THEME.titleFont })

    addMetaRow(sheet, 2, '期間', formatDateRangeLabel(), lastCol)
    addMetaRow(sheet, 3, '抽出条件', `班:${filterTeam.value || '全班'} / グループ:${filterGroup.value || '全グループ'} / 氏名:${filterName.value || '全員'} / 有給:${filterPaidLeave.value === 'any' ? '有給あり' : filterPaidLeave.value === 'none' ? '有給なし' : '全て'}`, lastCol)
    addMetaRow(sheet, 4, '集計', `件数 ${filteredRows.value.length}件 / 労働時間合計 ${totals.value.workH}H / 残業合計 ${totals.value.overtimeH || 0}H`, lastCol)

    sheet.addRow(headers)
    headers.forEach((header, idx) => {
      styleCell(sheet.getCell(5, idx + 1), { bold: true, bg: EXCEL_THEME.headerFill })
      sheet.getCell(5, idx + 1).value = header
    })

    let rowIndex = 6
    for (const r of filteredRows.value) {
      sheet.addRow([
        r.name,
        r.team,
        r.group,
        r.date,
        r.typeLabel,
        r.startTime || '',
        r.endTime || '',
        r.workH || '',
        r.overtimeH || '',
        r.holidayH || '',
        Math.round((r.overtimeH + r.holidayH) * 10) / 10 || '',
        r.halfDayAm ? '○' : '',
        r.halfDayPm ? '○' : '',
        r.paidLeave ? '○' : '',
        r.paidLeaveConsec ? '○' : '',
        r.paidLeaveCount || '',
      ])
      for (let c = 1; c <= lastCol; c += 1) {
        styleCell(sheet.getCell(rowIndex, c), {
          align: c >= 8 && c <= 11 ? 'right' : c >= 12 ? 'center' : (c === 1 || c === 5 ? 'left' : 'center'),
          numFmt: c >= 8 && c <= 11 ? '0.0' : (c === 16 ? '0.0' : null),
        })
      }
      rowIndex += 1
    }

    sheet.addRow([
      '合計', '', '', '', '', '', '',
      totals.value.workH, totals.value.overtimeH || '', totals.value.holidayH || '',
      (totals.value.overtimeH + totals.value.holidayH) || '',
      totals.value.halfDayAm || '', totals.value.halfDayPm || '',
      totals.value.paidLeave || '', totals.value.paidLeaveConsec || '',
      totals.value.paidLeaveCount || '',
    ])
    for (let c = 1; c <= lastCol; c += 1) {
      styleCell(sheet.getCell(rowIndex, c), {
        bold: true,
        align: c >= 8 && c <= 11 ? 'right' : c >= 12 ? 'center' : (c === 1 ? 'left' : 'center'),
        bg: EXCEL_THEME.totalFill,
        numFmt: c >= 8 && c <= 11 ? '0.0' : (c === 16 ? '0.0' : null),
      })
    }

    sheet.columns = [
      { width: 18 }, { width: 10 }, { width: 12 }, { width: 12 },
      { width: 12 }, { width: 10 }, { width: 10 }, { width: 12 },
      { width: 10 }, { width: 12 }, { width: 10 }, { width: 10 },
      { width: 10 }, { width: 10 }, { width: 10 }, { width: 10 },
    ]
  }

  setFrozenView(sheet)
  const filename = isMonthlyTab
    ? `労働時間統計_月別_${dateFrom.value}_${dateTo.value}.xlsx`
    : `労働時間統計_${dateFrom.value}_${dateTo.value}.xlsx`
  await saveWorkbook(workbook, filename)
}

onMounted(loadUsers)

</script>

<style scoped>
.stats-page {
  padding: 16px;
  max-width: 1880px;
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
  flex-wrap: nowrap;
  overflow-x: auto;
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
  font-size: 13px;
  flex: 0 0 auto;
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
.btn-danger { background: #dc2626; color: white; }
.btn-danger:hover { background: #b91c1c; }
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
  position: relative;
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
.stats-table th.name-header {
  position: sticky;
  left: 0;
  z-index: 4;
  background: #f8fafc;
}
.stats-table td.name-cell {
  position: sticky;
  left: 0;
  z-index: 2;
  background: #fff;
}
.stats-table tbody tr:hover td.name-cell {
  background: #f9fafb;
}
.stats-table tfoot .name-cell,
.stats-table tfoot .total-label {
  position: sticky;
  left: 0;
  z-index: 3;
  background: #f1f5f9;
}
.team-cell { color: #6b7280; white-space: nowrap; }
.date-cell { white-space: nowrap; color: #374151; }
.type-cell { white-space: nowrap; color: #374151; }
.num-cell { text-align: right; white-space: nowrap; }
.num-cell.work { font-weight: 600; color: #1f2a44; }
.num-cell.highlight { color: #dc2626; font-weight: 700; }
.num-cell.leave { text-align: center; color: #2563eb; }
.num-cell.total-col { font-weight: 700; color: #1f2a44; background: #f1f5f9; }
.stats-table tbody tr:hover { background: #f9fafb; }
.productivity-table {
  width: max-content;
  min-width: 100%;
  table-layout: auto;
}
.productivity-table th,
.productivity-table td {
  min-width: 96px;
}
.productivity-table .section-title {
  text-align: center;
  font-weight: 700;
  color: #1f2a44;
}
.productivity-table .section-divider {
  border-left: 2px solid #6b7280;
}
.productivity-table th.name-header,
.productivity-table td.name-cell {
  min-width: 200px;
}
.productivity-table th:nth-child(2),
.productivity-table th:nth-child(3),
.productivity-table th:nth-child(4),
.productivity-table td:nth-child(2),
.productivity-table td:nth-child(3),
.productivity-table td:nth-child(4) {
  min-width: 72px;
}
.productivity-table tbody tr.date-band-0 td { background-color: #eef6ff; }
.productivity-table tbody tr.date-band-1 td { background-color: #eefcf0; }
.productivity-table tbody tr.date-band-2 td { background-color: #fff5e8; }
.productivity-table tbody tr.date-band-3 td { background-color: #f5f0ff; }
.productivity-table tbody tr.date-start td { border-top: 2px solid #8fa6b3; }
.total-row { background: #f1f5f9; font-weight: 700; }
.total-row td { border-top: 2px solid #94a3b8; }
.total-label { font-weight: 700; color: #1f2a44; padding-left: 12px; }
/* 集計テーブル */
.summary-table .name-header { text-align: left; min-width: 120px; }
.summary-table .date-header { min-width: 52px; }
.summary-table .total-header { min-width: 60px; background: #e8f5e9; }
.monthly-table .date-header { min-width: 210px; }
.monthly-table .metric-header { min-width: 70px; }
.cell-empty {
  cursor: pointer;
  color: #d1d5db;
}
.cell-empty:hover {
  background: #f0fdf4;
  color: #40916c;
}
.cell-record { cursor: pointer; }
.cell-record:hover { background: #fff7ed; color: #c2410c; }
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
.modal-message { margin: 0 0 20px; font-size: 14px; color: #374151; }
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
