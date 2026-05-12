<template>
  <div class="stats-page">
    <h1 class="page-title">加工費集計</h1>

    <div class="filters">
      <div class="filter-item">
        <label>期間</label>
        <input v-model="dateFrom" type="date" class="filter-input" />
        <span>〜</span>
        <input v-model="dateTo" type="date" class="filter-input" />
      </div>
      <button class="btn btn-primary" @click="load">表示</button>
    </div>

    <div class="sub-filters">
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
    </div>

    <div class="tab-bar">
      <button class="tab-btn" :class="{ active: activeTab === 'daily' }" @click="activeTab = 'daily'">日別</button>
      <button class="tab-btn" :class="{ active: activeTab === 'period' }" @click="activeTab = 'period'">期間集計</button>
      <span class="tab-actions">
        <button class="btn btn-excel" @click="exportExcel">Excel出力</button>
      </span>
    </div>

    <div v-if="loading" class="loading">読み込み中...</div>
    <div v-else class="table-wrap">
      <table class="stats-table productivity-table">
        <thead>
          <tr>
            <th class="name-header" rowspan="2">氏名</th>
            <th rowspan="2">班</th>
            <th rowspan="2">グループ</th>
            <th rowspan="2">日付</th>
            <th rowspan="2">加工数合計</th>
            <th rowspan="2">加工費合計</th>
            <th class="section-title" colspan="5">セッションから</th>
            <th class="section-title section-divider" colspan="5">勤務時間から</th>
            <th class="section-title section-divider" colspan="1">稼働率</th>
          </tr>
          <tr>
            <th>加工時間(H)</th>
            <th>出来高</th>
            <th>出来高順</th>
            <th>加工費/H</th>
            <th>加工費/H順</th>
            <th class="section-divider">出勤時間(H)</th>
            <th>出来高</th>
            <th>出来高順</th>
            <th>加工費/H</th>
            <th>加工費/H順</th>
            <th class="section-divider">(加工時間/出勤時間)</th>
          </tr>
        </thead>
        <tbody>
          <template v-if="activeTab === 'daily'">
            <tr v-for="(row, index) in filteredDailyRows" :key="`d-${row.name}-${row.date}`" :class="[dateBandClass(row.date), { 'date-start': isDateStart(index, filteredDailyRows) }]">
              <td class="name-cell">{{ row.name }}</td>
              <td class="team-cell">{{ row.team || '—' }}</td>
              <td class="team-cell">{{ row.group || '—' }}</td>
              <td class="date-cell">{{ row.date }}</td>
              <td class="num-cell">{{ formatMetric(row.qtyTotal) }}</td>
              <td class="num-cell">{{ formatMetric(row.amountTotal) }}</td>
              <td class="num-cell">{{ formatMetric(row.sessionHours) }}</td>
              <td class="num-cell heat-qty" :style="heatStyle(row.sessionQtyIntensity)">{{ row.sessionThroughput != null ? formatMetric(row.sessionThroughput) : '—' }}</td>
              <td class="num-cell">{{ row.sessionQtyRank || '—' }}</td>
              <td class="num-cell heat-rate" :style="heatStyle(row.rateIntensity)">{{ row.sessionRate != null ? formatMetric(row.sessionRate) : '—' }}</td>
              <td class="num-cell">{{ row.rateRank || '—' }}</td>
              <td class="num-cell section-divider">{{ row.attendanceHours > 0 ? formatMetric(row.attendanceHours) : '—' }}</td>
              <td class="num-cell heat-qty" :style="heatStyle(row.attendanceQtyIntensity)">{{ row.attendanceThroughput != null ? formatMetric(row.attendanceThroughput) : '—' }}</td>
              <td class="num-cell">{{ row.attendanceQtyRank || '—' }}</td>
              <td class="num-cell heat-rate" :style="heatStyle(row.attendanceRateIntensity)">{{ row.attendanceRate != null ? formatMetric(row.attendanceRate) : '—' }}</td>
              <td class="num-cell">{{ row.attendanceRateRank || '—' }}</td>
              <td class="num-cell section-divider">{{ formatUtilization(row.sessionHours, row.attendanceHours) }}</td>
            </tr>
          </template>
          <template v-else>
            <tr class="period-total-row">
              <td class="name-cell">期間合計</td>
              <td class="team-cell">—</td>
              <td class="team-cell">—</td>
              <td class="date-cell">合計</td>
              <td class="num-cell">{{ formatMetric(periodTotal.qtyTotal) }}</td>
              <td class="num-cell">{{ formatMetric(periodTotal.amountTotal) }}</td>
              <td class="num-cell">{{ formatMetric(periodTotal.sessionHours) }}</td>
              <td class="num-cell">{{ periodTotal.sessionThroughput != null ? formatMetric(periodTotal.sessionThroughput) : '—' }}</td>
              <td class="num-cell">—</td>
              <td class="num-cell">{{ periodTotal.sessionRate != null ? formatMetric(periodTotal.sessionRate) : '—' }}</td>
              <td class="num-cell">—</td>
              <td class="num-cell section-divider">{{ periodTotal.attendanceHours > 0 ? formatMetric(periodTotal.attendanceHours) : '—' }}</td>
              <td class="num-cell">{{ periodTotal.attendanceThroughput != null ? formatMetric(periodTotal.attendanceThroughput) : '—' }}</td>
              <td class="num-cell">—</td>
              <td class="num-cell">{{ periodTotal.attendanceRate != null ? formatMetric(periodTotal.attendanceRate) : '—' }}</td>
              <td class="num-cell">—</td>
              <td class="num-cell section-divider">{{ formatUtilization(periodTotal.sessionHours, periodTotal.attendanceHours) }}</td>
            </tr>
            <tr v-for="(row, index) in filteredPeriodRows" :key="`p-${row.name}`" :class="{ 'date-start': index === 0 }">
              <td class="name-cell">{{ row.name }}</td>
              <td class="team-cell">{{ row.team || '—' }}</td>
              <td class="team-cell">{{ row.group || '—' }}</td>
              <td class="date-cell">合計</td>
              <td class="num-cell">{{ formatMetric(row.qtyTotal) }}</td>
              <td class="num-cell">{{ formatMetric(row.amountTotal) }}</td>
              <td class="num-cell">{{ formatMetric(row.sessionHours) }}</td>
              <td class="num-cell heat-qty" :style="heatStyle(row.sessionQtyIntensity)">{{ row.sessionThroughput != null ? formatMetric(row.sessionThroughput) : '—' }}</td>
              <td class="num-cell">{{ row.sessionQtyRank || '—' }}</td>
              <td class="num-cell heat-rate" :style="heatStyle(row.rateIntensity)">{{ row.sessionRate != null ? formatMetric(row.sessionRate) : '—' }}</td>
              <td class="num-cell">{{ row.rateRank || '—' }}</td>
              <td class="num-cell section-divider">{{ row.attendanceHours > 0 ? formatMetric(row.attendanceHours) : '—' }}</td>
              <td class="num-cell heat-qty" :style="heatStyle(row.attendanceQtyIntensity)">{{ row.attendanceThroughput != null ? formatMetric(row.attendanceThroughput) : '—' }}</td>
              <td class="num-cell">{{ row.attendanceQtyRank || '—' }}</td>
              <td class="num-cell heat-rate" :style="heatStyle(row.attendanceRateIntensity)">{{ row.attendanceRate != null ? formatMetric(row.attendanceRate) : '—' }}</td>
              <td class="num-cell">{{ row.attendanceRateRank || '—' }}</td>
              <td class="num-cell section-divider">{{ formatUtilization(row.sessionHours, row.attendanceHours) }}</td>
            </tr>
          </template>
          <tr v-if="activeTab === 'daily' && !filteredDailyRows.length">
            <td colspan="17" class="empty">データがありません</td>
          </tr>
          <tr v-if="activeTab === 'period' && !filteredPeriodRows.length">
            <td colspan="17" class="empty">データがありません</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import * as XLSX from 'xlsx'
import api from '@/api/client'

const today = new Date()
const pad = (n) => String(n).padStart(2, '0')
const y = today.getFullYear()
const m = today.getMonth() + 1
const lastDay = new Date(y, m, 0).getDate()

const dateFrom = ref(`${y}-${pad(m)}-01`)
const dateTo = ref(`${y}-${pad(m)}-${pad(lastDay)}`)
const loading = ref(false)
const activeTab = ref('daily')

const rows = ref([])
const allUsers = ref([])
const productionSessions = ref([])
const unitPriceByCode = ref({})

const filterTeam = ref('')
const filterGroup = ref('')
const filterName = ref('')

const NEEDS_APPROVAL = new Set(['overtime', 'holiday', 'half_day_am'])
const APPROVED_STATUSES = new Set(['approved_manager', 'approved_chief', 'approved_supervisor', 'approved_leader'])
const COUNTABLE_END_ACTIONS = new Set(['END', 'PAUSE'])

const normalizeList = (payload) => Array.isArray(payload) ? payload : (Array.isArray(payload?.results) ? payload.results : [])
const normalizePersonName = (value) => String(value || '').replace(/\s+/g, '').toLowerCase()

const teamOptions = computed(() => [...new Set(rows.value.map(r => r.team).filter(Boolean))].sort())
const groupOptions = computed(() => [...new Set(rows.value.map(r => r.group).filter(Boolean))].sort())
const nameOptions = computed(() => [...new Set(rows.value.map(r => r.name).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'ja')))

const userMetaByName = computed(() => {
  const map = new Map()
  for (const user of allUsers.value) {
    const key = normalizePersonName(user.name)
    if (!key) continue
    map.set(key, { team: user.team || '', group: user.group || '' })
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

const dailyRows = computed(() => {
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
    if (!aggregate.has(key)) aggregate.set(key, { name: nameRaw, nameKey, date, qtyTotal: 0, amountTotal: 0, sessionSeconds: 0 })
    const target = aggregate.get(key)
    target.qtyTotal += qty
    target.amountTotal += amount
    target.sessionSeconds += seconds
  }

  const out = [...aggregate.values()].map((item) => {
    const sessionHours = item.sessionSeconds / 3600
    const attendanceHours = Number(attendanceHoursByPersonDate.value.get(`${item.nameKey}|${item.date}`) || 0)
    const meta = userMetaByName.value.get(item.nameKey) || {}
    return {
      name: item.name,
      team: meta.team || '',
      group: meta.group || '',
      date: item.date,
      qtyTotal: Math.round(item.qtyTotal * 1000) / 1000,
      amountTotal: Math.round(item.amountTotal * 100) / 100,
      sessionHours: Math.round(sessionHours * 1000) / 1000,
      attendanceHours: Math.round(attendanceHours * 1000) / 1000,
      sessionRate: sessionHours > 0 ? Math.round(item.amountTotal / sessionHours) : null,
      attendanceRate: attendanceHours > 0 ? Math.round(item.amountTotal / attendanceHours) : null,
      sessionThroughput: sessionHours > 0 ? Math.round(item.qtyTotal / sessionHours) : null,
      attendanceThroughput: attendanceHours > 0 ? Math.round(item.qtyTotal / attendanceHours) : null,
    }
  })

  out.sort((a, b) => a.date === b.date ? a.name.localeCompare(b.name, 'ja') : (a.date < b.date ? -1 : 1))
  return applyDateRanking(out)
})

const filteredDailyRows = computed(() => {
  const filtered = dailyRows.value
    .filter((row) =>
      (!filterTeam.value || row.team === filterTeam.value) &&
      (!filterGroup.value || row.group === filterGroup.value) &&
      (!filterName.value || row.name === filterName.value),
    )
    .map((row) => ({ ...row }))
  return applyDateRanking(filtered)
})

const periodRows = computed(() => {
  const aggregate = new Map()
  for (const row of filteredDailyRows.value) {
    const key = normalizePersonName(row.name)
    if (!aggregate.has(key)) {
      aggregate.set(key, {
        name: row.name,
        team: row.team,
        group: row.group,
        qtyTotal: 0,
        amountTotal: 0,
        sessionHours: 0,
        attendanceHours: 0,
      })
    }
    const target = aggregate.get(key)
    target.qtyTotal += Number(row.qtyTotal || 0)
    target.amountTotal += Number(row.amountTotal || 0)
    target.sessionHours += Number(row.sessionHours || 0)
    target.attendanceHours += Number(row.attendanceHours || 0)
  }
  const out = [...aggregate.values()].map((item) => ({
    ...item,
    sessionRate: item.sessionHours > 0 ? Math.round(item.amountTotal / item.sessionHours) : null,
    attendanceRate: item.attendanceHours > 0 ? Math.round(item.amountTotal / item.attendanceHours) : null,
    sessionThroughput: item.sessionHours > 0 ? Math.round(item.qtyTotal / item.sessionHours) : null,
    attendanceThroughput: item.attendanceHours > 0 ? Math.round(item.qtyTotal / item.attendanceHours) : null,
  }))
  out.sort((a, b) => b.qtyTotal - a.qtyTotal)
  return applyDateRanking(out)
})

const filteredPeriodRows = computed(() => periodRows.value)

const periodTotal = computed(() => {
  const qtyTotal = filteredPeriodRows.value.reduce((s, r) => s + Number(r.qtyTotal || 0), 0)
  const amountTotal = filteredPeriodRows.value.reduce((s, r) => s + Number(r.amountTotal || 0), 0)
  const sessionHours = filteredPeriodRows.value.reduce((s, r) => s + Number(r.sessionHours || 0), 0)
  const attendanceHours = filteredPeriodRows.value.reduce((s, r) => s + Number(r.attendanceHours || 0), 0)
  return {
    qtyTotal,
    amountTotal,
    sessionHours,
    attendanceHours,
    sessionRate: sessionHours > 0 ? Math.round(amountTotal / sessionHours) : null,
    attendanceRate: attendanceHours > 0 ? Math.round(amountTotal / attendanceHours) : null,
    sessionThroughput: sessionHours > 0 ? Math.round(qtyTotal / sessionHours) : null,
    attendanceThroughput: attendanceHours > 0 ? Math.round(qtyTotal / attendanceHours) : null,
  }
})

function applyDateRanking(inputRows) {
  const rowsOut = inputRows.map(r => ({ ...r }))
  const byDate = new Map()
  for (const row of rowsOut) {
    const key = row.date || '__period__'
    if (!byDate.has(key)) byDate.set(key, [])
    byDate.get(key).push(row)
  }
  for (const dateRows of byDate.values()) {
    const sessionQtySorted = [...dateRows]
      .filter((row) => row.sessionThroughput != null)
      .sort((a, b) => Number(b.sessionThroughput || 0) - Number(a.sessionThroughput || 0))
    let prevSessionQty = null
    let sessionQtyRank = 0
    sessionQtySorted.forEach((row, idx) => {
      if (prevSessionQty === null || row.sessionThroughput !== prevSessionQty) sessionQtyRank = idx + 1
      row.sessionQtyRank = sessionQtyRank
      prevSessionQty = row.sessionThroughput
    })

    const attendanceQtySorted = [...dateRows]
      .filter((row) => row.attendanceThroughput != null)
      .sort((a, b) => Number(b.attendanceThroughput || 0) - Number(a.attendanceThroughput || 0))
    let prevAttendanceQty = null
    let attendanceQtyRank = 0
    attendanceQtySorted.forEach((row, idx) => {
      if (prevAttendanceQty === null || row.attendanceThroughput !== prevAttendanceQty) attendanceQtyRank = idx + 1
      row.attendanceQtyRank = attendanceQtyRank
      prevAttendanceQty = row.attendanceThroughput
    })

    const rateSorted = [...dateRows].filter(row => row.sessionRate != null).sort((a, b) => b.sessionRate - a.sessionRate)
    let prevRate = null
    let rateRank = 0
    rateSorted.forEach((row, idx) => {
      if (prevRate === null || row.sessionRate !== prevRate) rateRank = idx + 1
      row.rateRank = rateRank
      prevRate = row.sessionRate
    })

    const attendanceRateSorted = [...dateRows].filter(row => row.attendanceRate != null).sort((a, b) => b.attendanceRate - a.attendanceRate)
    let prevAttendanceRate = null
    let attendanceRateRank = 0
    attendanceRateSorted.forEach((row, idx) => {
      if (prevAttendanceRate === null || row.attendanceRate !== prevAttendanceRate) attendanceRateRank = idx + 1
      row.attendanceRateRank = attendanceRateRank
      prevAttendanceRate = row.attendanceRate
    })

    const maxSessionQty = Math.max(...dateRows.map((r) => Number(r.sessionThroughput || 0)), 0)
    const maxAttendanceQty = Math.max(...dateRows.map((r) => Number(r.attendanceThroughput || 0)), 0)
    const maxRate = Math.max(...dateRows.map((r) => Number(r.sessionRate || 0)), 0)
    const maxAttendanceRate = Math.max(...dateRows.map((r) => Number(r.attendanceRate || 0)), 0)
    dateRows.forEach((row) => {
      row.sessionQtyIntensity = maxSessionQty > 0 && row.sessionThroughput != null ? Number(row.sessionThroughput || 0) / maxSessionQty : 0
      row.attendanceQtyIntensity = maxAttendanceQty > 0 && row.attendanceThroughput != null ? Number(row.attendanceThroughput || 0) / maxAttendanceQty : 0
      row.rateIntensity = maxRate > 0 && row.sessionRate != null ? Number(row.sessionRate || 0) / maxRate : 0
      row.attendanceRateIntensity = maxAttendanceRate > 0 && row.attendanceRate != null ? Number(row.attendanceRate || 0) / maxAttendanceRate : 0
    })
  }
  return rowsOut
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
  return `${((s / a) * 100).toLocaleString('ja-JP', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`
}

function heatStyle(intensity) {
  const v = Math.max(0, Math.min(Number(intensity || 0), 1))
  if (v <= 0) return {}
  const alpha = 0.22 + v * 0.48
  return { backgroundColor: `rgba(34, 197, 94, ${alpha.toFixed(3)})`, fontWeight: v >= 0.85 ? 700 : 500 }
}

const dateBandIndexMap = computed(() => {
  const map = {}
  const uniqueDates = [...new Set(filteredDailyRows.value.map((row) => row.date))]
  uniqueDates.forEach((date, idx) => { map[date] = idx % 4 })
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

function isDateStart(index, rowsRef) {
  if (index === 0) return true
  const cur = rowsRef[index]
  const prev = rowsRef[index - 1]
  return !!(cur && prev && cur.date !== prev.date)
}

async function loadProductionMetrics() {
  productionSessions.value = []
  unitPriceByCode.value = {}

  const [laserRes, brakeRes, pwsRes] = await Promise.all([
    api.laserActuals.getLaserActuals({ page_size: 1000, work_date__gte: dateFrom.value, work_date__lte: dateTo.value, ordering: '-work_date,-created_at' }),
    api.brakeLineActuals.getSessions({ start_date: dateFrom.value, end_date: dateTo.value }),
    api.processRealtime.getSessions({ limit: 10000, plan_date_start: dateFrom.value, plan_date_end: dateTo.value }),
  ])

  const laserRecords = normalizeList(laserRes.data)
  const brakeSessions = normalizeList(brakeRes.data)
  const pwsSessions = normalizeList(pwsRes.data)

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
      if (action === 'START' || action === 'RESUME') pendingStart = row
      else if (pendingStart) {
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
    const details = normalizeList(row?.details).filter((d) => String(d?.detail_type || '').toUpperCase() === 'COMPONENT')
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
    return details.length ? details.map(buildOne) : [buildOne(null)]
  })

  const brakeItems = brakeSessions.map((row) => ({ ...row, record_source: 'BRAKE' }))
  const pwsItems = pwsSessions.filter((row) => {
    const source = String(row?.record_source || '').toUpperCase()
    return source !== 'BRAKE' && source !== 'LASER'
  })

  const countableSessions = [...laserItems, ...brakeItems, ...pwsItems].filter((row) => {
    if (String(row?.session_type || '') !== 'WORK') return false
    if (!COUNTABLE_END_ACTIONS.has(String(row?.end_action || '').toUpperCase())) return false
    return Number(row?.production_qty || 0) !== 0
  })
  productionSessions.value = countableSessions

  const productCodes = [...new Set(countableSessions.map((row) => String(row?.product_code || '').trim()).filter(Boolean))]
  const codePriceMap = {}
  for (let i = 0; i < productCodes.length; i += 200) {
    const chunk = productCodes.slice(i, i + 200)
    const productsRes = await api.products.getProductsByCodesIn(chunk)
    const products = Array.isArray(productsRes.data?.results) ? productsRes.data.results : (Array.isArray(productsRes.data) ? productsRes.data : [])
    for (const p of products) {
      const code = String(p?.product_code || '').trim()
      if (code) codePriceMap[code] = Number(p?.unit_price || 0)
    }
  }
  unitPriceByCode.value = codePriceMap
}

async function load() {
  loading.value = true
  rows.value = []
  try {
    const usersRes = await api.accounts.getUsers({ page_size: 1000, is_active: true })
    const userList = usersRes.data?.results ?? usersRes.data ?? []
    allUsers.value = userList.map((u) => ({
      name: `${u.last_name} ${u.first_name}`.trim() || u.username,
      team: u.profile?.team_name || '',
      group: u.profile?.unit_name || '',
    }))

    const res = await api.overtime.getApplications({ work_date__gte: dateFrom.value, work_date__lte: dateTo.value, page_size: 1000 })
    const apps = res.data?.results ?? res.data ?? []
    const result = []

    for (const app of apps) {
      if (NEEDS_APPROVAL.has(app.application_type) && !APPROVED_STATUSES.has(app.status)) continue
      const name = app.applicant_name || String(app.applicant)
      const date = app.work_date
      if (!name || !date) continue
      const h = parseFloat(app.hours ?? 0)
      const midnightH = parseFloat(app.midnight_hours ?? 0)
      const overtimeTotalH = Math.round((h + midnightH) * 10) / 10
      let workH = 0
      if (app.application_type === 'normal') workH = 8
      else if (app.application_type === 'overtime') workH = Math.round((8 + overtimeTotalH) * 10) / 10
      else if (app.application_type === 'half_day_am') workH = Math.round((4 + overtimeTotalH) * 10) / 10
      else if (app.application_type === 'holiday') workH = h > 0 ? h : (app.work_pattern_hours != null ? parseFloat(app.work_pattern_hours) : 8)
      else if (app.application_type === 'half_day_pm') workH = 4

      result.push({
        name,
        team: app.team_name || '',
        group: app.group_name || '',
        date,
        workH,
      })
    }

    rows.value = result
    await loadProductionMetrics()
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function exportExcel() {
  const headerTop = [
    '氏名', '班', 'グループ', '日付', '加工数合計', '加工費合計',
    'セッションから', '', '', '', '',
    '勤務時間から', '', '', '', '',
    '稼働率',
  ]
  const headerBottom = [
    '', '', '', '', '', '',
    '加工時間(H)', '出来高', '出来高順', '加工費/H', '加工費/H順',
    '出勤時間(H)', '出来高', '出来高順', '加工費/H', '加工費/H順',
    '(加工時間/出勤時間)',
  ]

  const toRow = (r, dateLabel = r.date || '合計') => ([
    r.name || '',
    r.team || '',
    r.group || '',
    dateLabel,
    Number(r.qtyTotal || 0),
    Number(r.amountTotal || 0),
    Number(r.sessionHours || 0),
    r.sessionThroughput ?? '',
    r.sessionQtyRank ?? '',
    r.sessionRate ?? '',
    r.rateRank ?? '',
    Number(r.attendanceHours || 0),
    r.attendanceThroughput ?? '',
    r.attendanceQtyRank ?? '',
    r.attendanceRate ?? '',
    r.attendanceRateRank ?? '',
    formatUtilization(r.sessionHours, r.attendanceHours),
  ])

  const data = []
  if (activeTab.value === 'daily') {
    for (const row of filteredDailyRows.value) data.push(toRow(row))
  } else {
    data.push(toRow({
      name: '期間合計',
      team: '',
      group: '',
      qtyTotal: periodTotal.value.qtyTotal,
      amountTotal: periodTotal.value.amountTotal,
      sessionHours: periodTotal.value.sessionHours,
      sessionThroughput: periodTotal.value.sessionThroughput,
      sessionQtyRank: '',
      sessionRate: periodTotal.value.sessionRate,
      rateRank: '',
      attendanceHours: periodTotal.value.attendanceHours,
      attendanceThroughput: periodTotal.value.attendanceThroughput,
      attendanceQtyRank: '',
      attendanceRate: periodTotal.value.attendanceRate,
      attendanceRateRank: '',
    }, '合計'))
    for (const row of filteredPeriodRows.value) data.push(toRow(row, '合計'))
  }

  const ws = XLSX.utils.aoa_to_sheet([headerTop, headerBottom, ...data])
  ws['!merges'] = [
    { s: { r: 0, c: 0 }, e: { r: 1, c: 0 } },
    { s: { r: 0, c: 1 }, e: { r: 1, c: 1 } },
    { s: { r: 0, c: 2 }, e: { r: 1, c: 2 } },
    { s: { r: 0, c: 3 }, e: { r: 1, c: 3 } },
    { s: { r: 0, c: 4 }, e: { r: 1, c: 4 } },
    { s: { r: 0, c: 5 }, e: { r: 1, c: 5 } },
    { s: { r: 0, c: 6 }, e: { r: 0, c: 10 } },
    { s: { r: 0, c: 11 }, e: { r: 0, c: 15 } },
    { s: { r: 0, c: 16 }, e: { r: 0, c: 16 } },
  ]
  ws['!cols'] = [22, 10, 12, 12, 12, 12, 12, 14, 14, 14, 16, 12, 12, 14, 14, 16, 18].map((w) => ({ wch: w }))
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, activeTab.value === 'daily' ? '日別' : '期間集計')
  const filename = `加工費集計_${activeTab.value === 'daily' ? '日別' : '期間集計'}_${dateFrom.value}_${dateTo.value}.xlsx`
  XLSX.writeFile(wb, filename)
}

onMounted(load)
</script>

<style scoped>
.stats-page { padding: 16px; max-width: 1880px; margin: 0 auto; }
.page-title { font-size: 20px; font-weight: 700; color: #1f2a44; margin-bottom: 20px; }
.filters { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
.filter-item { display: flex; align-items: center; gap: 8px; font-size: 14px; color: #374151; }
.sub-filters { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.filter-select, .filter-input { border: 1px solid #d1d5db; border-radius: 6px; padding: 6px 10px; font-size: 13px; }
.btn { padding: 7px 18px; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; border: none; }
.btn-primary { background: #40916c; color: white; }
.table-wrap { overflow-x: auto; }
.loading, .empty { padding: 40px; text-align: center; color: #6b7280; }
.tab-bar { display: flex; margin-bottom: 12px; border-bottom: 2px solid #e5e7eb; }
.tab-btn { padding: 8px 24px; font-size: 14px; font-weight: 600; border: none; background: none; color: #6b7280; border-bottom: 2px solid transparent; margin-bottom: -2px; }
.tab-btn.active { color: #40916c; border-bottom-color: #40916c; }
.tab-actions { margin-left: auto; display: flex; align-items: center; }
.btn-excel { background: #16a34a; color: #fff; padding: 5px 14px; border-radius: 6px; font-size: 13px; font-weight: 600; }
.btn-excel:hover { background: #15803d; }
.stats-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.stats-table th { background: #f8fafc; border: 1px solid #e5e7eb; padding: 8px 10px; text-align: center; font-weight: 600; color: #374151; white-space: nowrap; }
.stats-table td { border: 1px solid #e5e7eb; padding: 7px 10px; }
.name-cell { font-weight: 600; white-space: nowrap; }
.team-cell, .date-cell { white-space: nowrap; color: #374151; }
.num-cell { text-align: right; white-space: nowrap; }
.productivity-table { width: max-content; min-width: 100%; }
.productivity-table .section-title { text-align: center; font-weight: 700; color: #1f2a44; }
.productivity-table .section-divider { border-left: 2px solid #6b7280; }
.productivity-table th.name-header, .productivity-table td.name-cell { min-width: 200px; }
.productivity-table th, .productivity-table td { min-width: 96px; }
.productivity-table tbody tr.date-band-0 td { background-color: #eef6ff; }
.productivity-table tbody tr.date-band-1 td { background-color: #eefcf0; }
.productivity-table tbody tr.date-band-2 td { background-color: #fff5e8; }
.productivity-table tbody tr.date-band-3 td { background-color: #f5f0ff; }
.productivity-table tbody tr.date-start td { border-top: 2px solid #8fa6b3; }
.period-total-row td { background: #f1f5f9; font-weight: 700; }
</style>
