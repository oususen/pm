<template>
  <div class="due-adjustment-page">
    <div class="toolbar">
      <div class="field">
        <label>開始日</label>
        <input v-model="startDate" type="date" />
      </div>
      <div class="field">
        <label>期間</label>
        <select v-model.number="horizonDays">
          <option :value="7">7日</option>
          <option :value="14">14日</option>
          <option :value="30">30日</option>
          <option :value="60">60日</option>
        </select>
      </div>
      <div class="field search-field">
        <label>品番/品名 OR検索</label>
        <div class="search-inputs">
          <input v-model.trim="keyword" type="text" placeholder="キーワード1" @keydown.enter="loadGrid" />
          <input v-model.trim="keyword2" type="text" placeholder="キーワード2" @keydown.enter="loadGrid" />
        </div>
      </div>
      <button class="btn save-btn" :disabled="saving || loading" @click="saveAdjustments">{{ saving ? '保存中...' : '保存' }}</button>
      <button class="btn" :disabled="loading" @click="loadGrid">表示</button>
    </div>

    <div class="table-wrap">
      <div class="table-split">
        <div class="main-grid-wrap">
          <table class="grid">
            <colgroup>
              <col style="width: 60px" />
              <col style="width: 120px" />
              <col style="width: 60px" />
              <template v-for="col in dateColumns" :key="`col-${col.key}`">
                <col style="width: 70px" />
                <col style="width: 30px" />
                <col style="width: 50px" />
                <col style="width: 30px" />
              </template>
            </colgroup>
            <thead>
              <tr class="head1">
                <th rowspan="2" class="sticky code-col">品番</th>
                <th rowspan="2" class="sticky name-col">品名</th>
                <th rowspan="2" class="shipto-col">納入場所</th>
                <th v-for="col in dateColumns" :key="col.key" colspan="4" :class="col.dayClass">{{ col.label }}</th>
              </tr>
              <tr class="head2">
                <template v-for="col in dateColumns" :key="`${col.key}-sub`">
                  <th :class="col.dayClass">注番</th>
                  <th :class="col.dayClass">受注</th>
                  <th :class="col.dayClass">納入</th>
                  <th :class="col.dayClass">残量</th>
                </template>
              </tr>
            </thead>
            <tbody>
              <tr v-for="group in displayGroups" :key="group.groupKey">
                <td class="sticky code-col">{{ group.productCode }}</td>
                <td class="sticky name-col">{{ group.productName }}</td>
                <td class="shipto-col">{{ group.shipToCode || '-' }}</td>
                <template v-for="col in dateColumns" :key="`${group.groupKey}-${col.key}`">
                  <td class="orderno-subcol">
                    <div
                      v-for="slotIdx in group.maxSlots"
                      :key="`${col.key}-lbl-${slotIdx}`"
                      class="sub-cell"
                      :class="{ forecast: slotLineAt(group, col.key, slotIdx - 1) && slotLineAt(group, col.key, slotIdx - 1).orderType === 'FORECAST' }"
                    >{{ slotLabel(group, col.key, slotIdx - 1) }}</div>
                  </td>
                  <td class="readonly-cell demand" :class="col.dayClass">
                    <div
                      v-for="slotIdx in group.maxSlots"
                      :key="`${col.key}-d-${slotIdx}`"
                      class="sub-cell"
                    >{{ slotDemand(group, col.key, slotIdx - 1) }}</div>
                  </td>
                  <td :class="col.dayClass">
                    <div
                      v-for="slotIdx in group.maxSlots"
                      :key="`${col.key}-i-${slotIdx}`"
                      class="sub-cell"
                    >
                      <input
                        v-if="slotLineAt(group, col.key, slotIdx - 1)"
                        :value="displayInputValue(slotLineAt(group, col.key, slotIdx - 1).deliveryByDate[col.key])"
                        type="text"
                        inputmode="decimal"
                        @input="onDeliveryInput(slotLineAt(group, col.key, slotIdx - 1), col.key, $event.target.value)"
                        @blur="onDeliveryBlur(slotLineAt(group, col.key, slotIdx - 1), col.key)"
                      />
                    </div>
                  </td>
                  <td class="readonly-cell" :class="col.dayClass">
                    <div
                      v-for="slotIdx in group.maxSlots"
                      :key="`${col.key}-r-${slotIdx}`"
                      class="sub-cell"
                    >{{ slotRemaining(group, col.key, slotIdx - 1) }}</div>
                  </td>
                </template>
              </tr>
              <tr v-if="!displayGroups.length">
                <td :colspan="dateColumns.length * 4 + 3" class="empty">データがありません</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="total-grid-wrap">
          <table class="grid total-grid">
            <thead>
              <tr class="head1">
                <th>総残</th>
              </tr>
              <tr class="head2">
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="group in displayGroups" :key="`total-${group.groupKey}`">
                <td class="stacked-total">
                  <div
                    v-for="slotIdx in group.maxSlots"
                    :key="`total-${group.groupKey}-${slotIdx}`"
                    class="sub-cell"
                    :class="{ error: slotIdx === 1 && groupTotalDiff(group) !== 0 }"
                  >{{ slotIdx === 1 ? formatNumber(groupTotalDiff(group)) : '' }}</div>
                </td>
              </tr>
              <tr v-if="!displayGroups.length">
                <td class="empty"></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'

// --- Utility Functions ---
const formatLocalDate = (date) => {
  const yyyy = String(date.getFullYear())
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const dd = String(date.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

const parseNumber = (value) => {
  if (value === null || value === undefined || value === '') return 0
  const num = Number(String(value).replace(/,/g, ''))
  return Number.isFinite(num) ? num : 0
}

const formatNumber = (value) => {
  const num = parseNumber(value)
  if (Math.abs(num) < 0.000001) return '0'
  return Number.isInteger(num) ? String(num) : num.toFixed(3).replace(/\.?0+$/, '')
}

const displayInputValue = (value) => {
  const num = parseNumber(value)
  if (Math.abs(num) < 0.000001) return ''
  return Number.isInteger(num) ? String(num) : num.toFixed(3).replace(/\.?0+$/, '')
}

// --- State ---
const loading = ref(false)
const saving = ref(false)
const keyword = ref('V0') 
const keyword2 = ref('6E')
const startDate = ref(formatLocalDate(new Date()))
const horizonDays = ref(30)
const groups = ref([])
const calendarDayMap = ref({})
const kubotaSakaiCalendarId = ref(null)

// --- Computed ---
const dateColumns = computed(() => {
  const base = new Date(`${startDate.value}T00:00:00`)
  return Array.from({ length: horizonDays.value }).map((_, idx) => {
    const d = new Date(base)
    d.setDate(base.getDate() + idx)
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    const dd = String(d.getDate()).padStart(2, '0')
    const w = ['日', '月', '火', '水', '木', '金', '土'][d.getDay()]
    const key = formatLocalDate(d)
    return { key, label: `${mm}/${dd}(${w})`, dayClass: isHolidayDate(key, d.getDay()) ? 'holiday' : '' }
  })
})

const displayGroups = computed(() => {
  const dateKeys = dateColumns.value.map((c) => c.key)
  const kw1 = keyword.value.trim().toLowerCase()
  const kw2 = keyword2.value.trim().toLowerCase()

  // 1. Keyword Filtering (OR logic)
  let filtered = groups.value
  if (kw1 || kw2) {
    filtered = groups.value.filter(group => {
      const searchTarget = `${group.productCode} ${group.productName}`.toLowerCase()
      const match1 = kw1 && searchTarget.includes(kw1)
      const match2 = kw2 && searchTarget.includes(kw2)
      return match1 || match2
    })
  }

  // 2. Map to display structure with slots
  return filtered.map((group) => {
    const slotsByDate = {}
    let maxSlots = 0
    dateKeys.forEach((d) => {
      const active = group.lines.filter((line) => {
        const src = parseNumber(line.demandByDate[d])
        const del = parseNumber(line.deliveryByDate[d])
        return src > 0 || del > 0
      })
      active.sort((a, b) => {
        const aFc = a.orderType === 'FORECAST' ? 1 : 0
        const bFc = b.orderType === 'FORECAST' ? 1 : 0
        if (aFc !== bFc) return aFc - bFc
        return String(a.sourceOrderNo || '').localeCompare(String(b.sourceOrderNo || ''))
      })
      slotsByDate[d] = active
      if (active.length > maxSlots) maxSlots = active.length
    })
    if (maxSlots === 0) maxSlots = 1
    return { ...group, slotsByDate, maxSlots }
  })
})

// --- Methods ---
const isHolidayDate = (dateKey, weekDay) => {
  const day = calendarDayMap.value[dateKey]
  if (day && typeof day.is_working_day === 'boolean') return !day.is_working_day
  return weekDay === 0 || weekDay === 6
}

const resolveKubotaSakaiCalendarId = async () => {
  if (kubotaSakaiCalendarId.value) return kubotaSakaiCalendarId.value
  const normalize = (value) => String(value || '').trim().toLowerCase()
  const pick = (list = []) => {
    const exact = list.find((row) => {
      const code = normalize(row.calendar_code)
      return code === 'kubota_sakai' || code === 'kobota_sakai' || code === 'kubota-muke' || code === 'kubota_muke'
    })
    if (exact) return exact
    const nameHit = list.find((row) => {
      const code = normalize(row.calendar_code)
      const name = normalize(row.calendar_name)
      return (name.includes('クボタ') && name.includes('堺')) || (code.includes('kubota') && code.includes('sakai'))
    })
    if (nameHit) return nameHit
    return list.find((row) => normalize(row.calendar_code).includes('kubota') || normalize(row.calendar_code).includes('kobota')) || null
  }
  for (const kw of ['kubota', 'kobota', 'クボタ']) {
    try {
      const res = await api.calendars.getCalendars({ search: kw, page_size: 500 })
      const list = res.data?.results || res.data || []
      const found = pick(list)
      if (found?.id) {
        kubotaSakaiCalendarId.value = found.id
        return found.id
      }
    } catch (error) { /* ignore */ }
  }
  return null
}

const loadKubotaSakaiCalendarDays = async () => {
  try {
    const calendarId = await resolveKubotaSakaiCalendarId()
    if (!calendarId) { calendarDayMap.value = {}; return; }
    const daysRes = await api.calendars.getCalendarDays(calendarId, { page_size: 5000 })
    const days = daysRes.data?.results || daysRes.data || []
    const map = {}
    days.forEach((day) => { if (day?.target_date) map[day.target_date] = day })
    calendarDayMap.value = map
  } catch (error) { calendarDayMap.value = {} }
}

const buildLine = (li) => {
  const demandByDate = {}
  const deliveryByDate = {}
  const remainingByDate = {}
  dateColumns.value.forEach((col) => {
    demandByDate[col.key] = 0
    deliveryByDate[col.key] = 0
    remainingByDate[col.key] = 0
  })
  const sourceQtyByDate = li.source_qty_by_date || {}
  const sourceDates = []
  Object.entries(sourceQtyByDate).forEach(([d, q]) => {
    const qty = parseNumber(q)
    if (qty > 0) sourceDates.push(d)
    if (Object.prototype.hasOwnProperty.call(demandByDate, d)) demandByDate[d] = qty
  })
  const hasAdjustments = Array.isArray(li.adjustments) && li.adjustments.length > 0
  if (hasAdjustments) {
    li.adjustments.forEach((adj) => {
      const key = adj.adjusted_due_date
      if (Object.prototype.hasOwnProperty.call(deliveryByDate, key)) {
        deliveryByDate[key] = parseNumber(adj.adjusted_qty)
        remainingByDate[key] = parseNumber(adj.remaining_qty)
      }
    })
  } else {
    Object.entries(sourceQtyByDate).forEach(([d, q]) => {
      if (Object.prototype.hasOwnProperty.call(deliveryByDate, d)) deliveryByDate[d] = parseNumber(q)
    })
  }
  return {
    lineKey: li.line_key,
    orderLineIds: li.order_line_ids || [],
    sourceOrderNo: li.source_order_no,
    orderType: li.order_type,
    sourceDates: sourceDates.sort(),
    sourceQty: parseNumber(li.source_qty_total),
    demandByDate,
    deliveryByDate,
    remainingByDate,
    _untouched: !hasAdjustments,
  }
}

const buildGroupFromGridItem = (item) => ({
  groupKey: item.group_key,
  productCode: item.product_code,
  productName: item.product_name,
  shipToCode: item.ship_to_code,
  shipToName: item.ship_to_name,
  lines: (item.lines || []).map(buildLine),
})

const slotLineAt = (group, dateKey, slotIdx) => {
  const arr = group.slotsByDate[dateKey]
  return arr && arr[slotIdx] ? arr[slotIdx] : null
}
const slotLabel = (group, dateKey, slotIdx) => {
  const line = slotLineAt(group, dateKey, slotIdx)
  if (!line) return ''
  return line.sourceOrderNo || (line.orderType === 'FORECAST' ? '内示' : '-')
}
const slotDemand = (group, dateKey, slotIdx) => {
  const line = slotLineAt(group, dateKey, slotIdx)
  return line ? formatNumber(line.demandByDate[dateKey]) : ''
}
const slotRemaining = (group, dateKey, slotIdx) => {
  const line = slotLineAt(group, dateKey, slotIdx)
  return line ? formatNumber(line.remainingByDate[dateKey]) : ''
}
const groupTotalDiff = (group) => {
  const totalDemand = group.lines.reduce((sum, line) => sum + parseNumber(line.sourceQty), 0)
  const totalDelivery = group.lines.reduce((sum, line) => {
    return sum + Object.values(line.deliveryByDate).reduce((s, v) => s + parseNumber(v), 0)
  }, 0)
  return Number((totalDemand - totalDelivery).toFixed(3))
}

const loadGrid = async () => {
  loading.value = true
  try {
    const [res] = await Promise.all([
      api.kubotaSakaiDueAdjustments.grid({
        start_date: startDate.value,
        horizon_days: horizonDays.value,
        // keywordはフロントでフィルタリングするためここでは送らない（または広く取得）
      }),
      loadKubotaSakaiCalendarDays(),
    ])
    const items = res.data?.rows || []
    groups.value = items.map(buildGroupFromGridItem)
  } catch (error) {
    const message = error?.response?.data?.detail || 'データ取得に失敗しました。'
    alert(message)
  } finally {
    loading.value = false
  }
}

const onDeliveryInput = (line, dateKey, rawValue) => {
  const normalized = rawValue.replace(/[^\d.-]/g, '')
  line.deliveryByDate[dateKey] = normalized === '' ? 0 : parseNumber(normalized)
  line._untouched = false
}

const onDeliveryBlur = (line, dateKey) => {
  const qty = parseNumber(line.deliveryByDate[dateKey])
  if (qty <= 0) line.deliveryByDate[dateKey] = 0
}

const buildSavePayload = () => {
  const payloadRows = []
  let hasError = false
  outer: for (const group of groups.value) {
    for (const line of group.lines) {
      if (line._untouched) continue

      const adjustments = []
      let needApproval = false
      const minSourceDate = line.sourceDates.length ? line.sourceDates[0] : null
      for (const col of dateColumns.value) {
        const qty = parseNumber(line.deliveryByDate[col.key])
        if (qty <= 0) continue
        if (minSourceDate && col.key > minSourceDate) needApproval = true
        adjustments.push({
          adjusted_due_date: col.key,
          adjusted_qty: qty,
          customer_approved: false,
          note: '',
        })
      }

      const total = adjustments.reduce((s, a) => s + a.adjusted_qty, 0)
      if (Math.abs(total - line.sourceQty) > 0.001) {
        alert(`数量合計不一致: ${group.productCode} / ${group.shipToCode || '-'} / ${line.sourceOrderNo || '内示'} / 元=${line.sourceQty} 納入計=${total}`)
        hasError = true
        break outer
      }

      if (needApproval) {
        const ok = confirm(`[${group.productCode}] ${line.sourceOrderNo || '内示'} に後ろ倒し納入があります。顧客の口頭承認は済んでいますか？`)
        if (!ok) {
          hasError = true
          break outer
        }
        adjustments.forEach((a) => { a.customer_approved = true })
      }

      payloadRows.push({
        group_key: line.lineKey,
        order_line_ids: line.orderLineIds,
        adjustments,
      })
    }
  }
  return { payloadRows, hasError }
}

const saveAdjustments = async () => {
  if (saving.value || loading.value) return
  const { payloadRows, hasError } = buildSavePayload()
  if (hasError) return
  if (payloadRows.length === 0) {
    alert('変更された行がありません。')
    return
  }
  saving.value = true
  try {
    await api.kubotaSakaiDueAdjustments.bulkSave(payloadRows)
    alert('保存しました。')
    await loadGrid()
  } catch (error) {
    const data = error?.response?.data
    if (data?.errors?.length) {
      const msg = data.errors.slice(0, 5).map((e) => `- ${e.detail}`).join('\n')
      alert(`保存失敗:\n${msg}`)
    } else {
      alert(data?.detail || '保存に失敗しました。')
    }
  } finally {
    saving.value = false
  }
}

onMounted(loadGrid)
</script>

<style scoped>
.due-adjustment-page {
  padding: 8px;
  background: #eef2f6;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.toolbar {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: #e1e8f4;
  border: 1px solid #c5cfde;
  border-radius: 4px;
  padding: 8px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.field label {
  font-size: 12px;
  color: #374151;
}
.field input,
.field select {
  min-width: 60px;
  padding: 6px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
}
.search-inputs {
  display: flex;
  gap: 4px;
}
.search-field input {
  min-width: 40px;
  width: 60px;
}
.btn {
  padding: 6px 12px;
  border: 1px solid #b5c1d2;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}
.save-btn {
  background: #dff3e6;
  border-color: #8fc8a1;
}
.table-wrap {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 4px;
}
.table-split {
  display: flex;
  align-items: flex-start;
  width: 100%;
}
.main-grid-wrap {
  flex: 1;
  min-width: 0;
  overflow-x: auto;
  overflow-y: visible;
  border-right: 1px solid #cbd5e1;
}
.total-grid-wrap {
  flex: 0 0 88px;
  width: 88px;
}
.grid {
  width: max-content;
  min-width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
.grid th,
.grid td {
  border: 1px solid #d7dfe8;
  padding: 3px 6px;
  white-space: nowrap;
  font-size: 12px;
  height: 28px;
  box-sizing: border-box;
  vertical-align: top;
}
.grid tbody td {
  padding: 0;
}
.sub-cell {
  height: 26px;
  line-height: 26px;
  padding: 0 6px;
  border-bottom: 1px dashed #e5e7eb;
  box-sizing: border-box;
  text-align: right;
  font-size: 12px;
}
.sub-cell:last-child {
  border-bottom: none;
}
.sub-cell.forecast {
  background: #fafcff;
  color: #64748b;
}
.orderno-subcol .sub-cell {
  text-align: center;
  font-size: 11px;
  color: #374151;
  background: #f1f5f9;
}
.sub-cell input {
  width: 100%;
  height: 22px;
  text-align: right;
  border: 1px solid #d1d5db;
  border-radius: 2px;
  padding: 0 4px;
  box-sizing: border-box;
  background: #fff;
}
.grid tbody td.sticky {
  padding: 3px 6px;
}
.grid tbody td.shipto-col {
  padding: 3px 6px;
}
.grid thead .head1 th {
  background: #cfd8ec;
}
.grid thead .head2 th {
  background: #e7edf7;
}
.grid th.holiday,
.grid td.holiday {
  background: #ffe3e3;
}
.sticky {
  position: sticky;
  left: 0;
  background: #fff;
  z-index: 2;
}
.code-col {
  left: 0;
  min-width: 120px;
}
.name-col {
  left: 120px;
  min-width: 70px;
  width: 80px;
}
.shipto-col {
  text-align: center;
  color: #374151;
}
.readonly-cell {
  color: #4b5563;
}
.readonly-cell.demand .sub-cell {
  background: #f4f7fb;
}
.readonly-cell.demand .sub-cell.forecast {
  background: #eef4fb;
}
.total-grid {
  width: 88px;
  min-width: 88px;
}
.total-grid th,
.total-grid td {
  text-align: right;
}
.total-grid tbody td {
  padding: 0;
}
.stacked-total .sub-cell {
  text-align: right;
}
.sub-cell.error {
  color: #b91c1c;
  font-weight: 700;
}
.empty {
  text-align: center;
  color: #6b7280;
  padding: 16px 0;
}
</style>