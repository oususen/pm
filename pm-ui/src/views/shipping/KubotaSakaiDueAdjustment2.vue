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
        <label>品番 OR検索</label>
        <div class="search-inputs">
          <input v-model.trim="keyword" type="text" placeholder="キーワード1" @keydown.enter="loadGrid" />
          <input v-model.trim="keyword2" type="text" placeholder="キーワード2" @keydown.enter="loadGrid" />
        </div>
      </div>
      <button class="btn import-btn" :disabled="importing || loading" @click="importOrders">{{ importing ? '取込中...' : '取込' }}</button>
      <button class="btn save-btn" :disabled="saving || loading" @click="saveDeliveries">{{ saving ? '保存中...' : '保存' }}</button>
      <button class="btn" :disabled="loading" @click="loadGrid">表示</button>
    </div>

    <div class="table-wrap">
      <table class="grid">
        <colgroup>
          <col style="width: 60px" />
          <template v-for="col in matrixColumns" :key="`col-${col.colKey}`">
            <col style="width: 70px" />
            <col style="width: 40px" />
            <col style="width: 45px" />
            <col style="width: 40px" />
          </template>
        </colgroup>
        <thead>
          <tr class="head1">
            <th rowspan="2" class="sticky-left date-separator">日付</th>
            <th
              v-for="(col, colIdx) in matrixColumns"
              :key="col.colKey"
              colspan="4"
              :class="{ 'product-start': colIdx > 0 }"
            >
              <div class="head-group">
                <span class="head-code">{{ col.productCode }}</span>
                <span class="head-ship">{{ col.shipToCode }}</span>
              </div>
            </th>
          </tr>
          <tr class="head2">
            <template v-for="(col, colIdx) in matrixColumns" :key="`sub-${col.colKey}`">
              <th :class="{ 'product-start': colIdx > 0 }">注番</th>
              <th>受注</th>
              <th>納入</th>
              <th class="product-end">残量</th>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in displayRows" :key="row.rowKey">
            <td class="sticky-left date-col date-separator" :class="row.dayClass">{{ row.label }}</td>
            <template v-for="(col, colIdx) in matrixColumns" :key="`${row.rowKey}-${col.colKey}`">
              <td class="orderno-subcol" :class="{ 'product-start': colIdx > 0 }">
                <div
                  v-for="slotIdx in row.maxSlots"
                  :key="`${row.rowKey}-${col.colKey}-label-${slotIdx}`"
                  class="sub-cell"
                  :class="{ forecast: slotLineAt(row, col.colKey, slotIdx - 1)?.orderType === 'FORECAST' }"
                >{{ slotLabel(row, col.colKey, slotIdx - 1) }}</div>
              </td>
              <td class="readonly-cell demand" :class="row.dayClass">
                <div
                  v-for="slotIdx in row.maxSlots"
                  :key="`${row.rowKey}-${col.colKey}-demand-${slotIdx}`"
                  class="sub-cell"
                >{{ slotDemand(row, col.colKey, slotIdx - 1) }}</div>
              </td>
              <td :class="row.dayClass">
                <div
                  v-for="slotIdx in row.maxSlots"
                  :key="`${row.rowKey}-${col.colKey}-delivery-${slotIdx}`"
                  class="sub-cell"
                >
                  <input
                    v-if="slotLineAt(row, col.colKey, slotIdx - 1)"
                    :value="displayInputValue(slotLineAt(row, col.colKey, slotIdx - 1).deliveryByDate[row.dateKey])"
                    type="text"
                    inputmode="decimal"
                    @input="onDeliveryInput(slotLineAt(row, col.colKey, slotIdx - 1), row.dateKey, $event.target.value)"
                    @blur="onDeliveryBlur(slotLineAt(row, col.colKey, slotIdx - 1), row.dateKey)"
                  />
                </div>
              </td>
              <td class="readonly-cell product-end" :class="row.dayClass">
                <div
                  v-for="slotIdx in row.maxSlots"
                  :key="`${row.rowKey}-${col.colKey}-remaining-${slotIdx}`"
                  class="sub-cell"
                >{{ slotRemaining(row, col.colKey, slotIdx - 1) }}</div>
              </td>
            </template>
          </tr>
          <tr v-if="!displayRows.length">
            <td :colspan="matrixColumns.length * 4 + 1" class="empty">データがありません</td>
          </tr>
        </tbody>
        <tfoot>
          <tr class="total-row">
            <th class="sticky-left total-label date-separator">総残</th>
            <template v-for="(col, colIdx) in matrixColumns" :key="`total-${col.colKey}`">
              <td class="total-blank" :class="{ 'product-start': colIdx > 0 }"></td>
              <td class="total-blank"></td>
              <td class="total-blank"></td>
              <td class="total-value product-end" :class="{ error: groupTotalRemaining(col.group) !== 0 }">
                {{ formatNumber(groupTotalRemaining(col.group)) }}
              </td>
            </template>
          </tr>
        </tfoot>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'

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
  if (Math.abs(num) < 0.000001) return ''
  return Number.isInteger(num) ? String(num) : num.toFixed(3).replace(/\.?0+$/, '')
}

const displayInputValue = (value) => {
  const num = parseNumber(value)
  if (Math.abs(num) < 0.000001) return ''
  return Number.isInteger(num) ? String(num) : num.toFixed(3).replace(/\.?0+$/, '')
}

const loading = ref(false)
const saving = ref(false)
const importing = ref(false)
const keyword = ref('V0')
const keyword2 = ref('')
const startDate = ref(formatLocalDate(new Date()))
const horizonDays = ref(30)
const groups = ref([])
const calendarDayMap = ref({})
const kubotaSakaiCalendarId = ref(null)

const dateColumns = computed(() => {
  const base = new Date(`${startDate.value}T00:00:00`)
  return Array.from({ length: horizonDays.value }).map((_, idx) => {
    const d = new Date(base)
    d.setDate(base.getDate() + idx)
    const mm = d.getMonth() + 1
    const dd = d.getDate()
    const w = ['日', '月', '火', '水', '木', '金', '土'][d.getDay()]
    const key = formatLocalDate(d)
    return { key, label: `${mm}/${dd}${w}`, dayClass: isHolidayDate(key, d.getDay()) ? 'holiday' : '' }
  })
})

const filteredGroups = computed(() => {
  const kw1 = keyword.value.trim().toLowerCase()
  const kw2 = keyword2.value.trim().toLowerCase()
  if (!kw1 && !kw2) return groups.value
  return groups.value.filter((group) => {
    const searchTarget = `${group.productCode}`.toLowerCase()
    const match1 = kw1 && searchTarget.includes(kw1)
    const match2 = kw2 && searchTarget.includes(kw2)
    return match1 || match2
  })
})

const matrixColumns = computed(() => {
  return [...filteredGroups.value]
    .sort((a, b) => {
      const codeCmp = String(a.productCode).localeCompare(String(b.productCode))
      if (codeCmp !== 0) return codeCmp
      return String(a.shipToCode || '').localeCompare(String(b.shipToCode || ''))
    })
    .map((group) => ({
      colKey: group.groupKey,
      productCode: group.productCode,
      shipToCode: group.shipToCode || '-',
      group,
    }))
})

const displayRows = computed(() => {
  return dateColumns.value.map((dateCol) => {
    const cells = {}
    let maxSlots = 0
    matrixColumns.value.forEach((col) => {
      const active = col.group.lines.filter((line) => {
        const demand = parseNumber(line.demandByDate[dateCol.key])
        const delivery = parseNumber(line.deliveryByDate[dateCol.key])
        return demand > 0 || delivery > 0
      })
      active.sort((a, b) => {
        const aFc = a.orderType === 'FORECAST' ? 1 : 0
        const bFc = b.orderType === 'FORECAST' ? 1 : 0
        if (aFc !== bFc) return aFc - bFc
        return String(a.sourceOrderNo || '').localeCompare(String(b.sourceOrderNo || ''))
      })
      cells[col.colKey] = active
      if (active.length > maxSlots) maxSlots = active.length
    })
    return {
      rowKey: dateCol.key,
      dateKey: dateCol.key,
      label: dateCol.label,
      dayClass: dateCol.dayClass,
      maxSlots: maxSlots || 1,
      cells,
    }
  })
})

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
    if (!calendarId) { calendarDayMap.value = {}; return }
    const daysRes = await api.calendars.getCalendarDays(calendarId, { page_size: 5000 })
    const days = daysRes.data?.results || daysRes.data || []
    const map = {}
    days.forEach((day) => { if (day?.target_date) map[day.target_date] = day })
    calendarDayMap.value = map
  } catch (error) {
    calendarDayMap.value = {}
  }
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
  // APIから返されたデータをマッピング
  Object.entries(li.demand_by_date || {}).forEach(([d, q]) => {
    if (Object.prototype.hasOwnProperty.call(demandByDate, d)) demandByDate[d] = parseNumber(q)
  })
  Object.entries(li.delivery_by_date || {}).forEach(([d, q]) => {
    if (Object.prototype.hasOwnProperty.call(deliveryByDate, d)) deliveryByDate[d] = parseNumber(q)
  })
  Object.entries(li.remaining_by_date || {}).forEach(([d, q]) => {
    if (Object.prototype.hasOwnProperty.call(remainingByDate, d)) remainingByDate[d] = parseNumber(q)
  })
  return {
    lineKey: li.line_key,
    sourceOrderNo: li.source_order_no,
    orderType: li.order_type,
    demandByDate,
    deliveryByDate,
    remainingByDate,
    _dirty: false,
  }
}

const buildGroupFromGridItem = (item) => ({
  groupKey: item.group_key,
  productCode: item.product_code,
  shipToCode: item.ship_to_code || '-',
  lines: (item.lines || []).map(buildLine),
})

const slotLineAt = (row, colKey, slotIdx) => {
  const arr = row.cells[colKey]
  return arr && arr[slotIdx] ? arr[slotIdx] : null
}

const slotLabel = (row, colKey, slotIdx) => {
  const line = slotLineAt(row, colKey, slotIdx)
  if (!line) return ''
  return line.sourceOrderNo || (line.orderType === 'FORECAST' ? '内示' : '-')
}

const slotDemand = (row, colKey, slotIdx) => {
  const line = slotLineAt(row, colKey, slotIdx)
  return line ? formatNumber(line.demandByDate[row.dateKey]) : ''
}

const slotRemaining = (row, colKey, slotIdx) => {
  const line = slotLineAt(row, colKey, slotIdx)
  return line ? formatNumber(line.remainingByDate[row.dateKey]) : ''
}

const groupTotalRemaining = (group) => {
  // 最終日の残量合計（各注番の最終残量）
  const lastDate = dateColumns.value.length ? dateColumns.value[dateColumns.value.length - 1].key : null
  if (!lastDate) return 0
  let total = 0
  for (const line of group.lines) {
    // 最後に残量がある日のremaining
    let lastRemaining = 0
    for (const col of dateColumns.value) {
      const r = parseNumber(line.remainingByDate[col.key])
      if (r !== 0 || parseNumber(line.demandByDate[col.key]) > 0 || parseNumber(line.deliveryByDate[col.key]) > 0) {
        lastRemaining = r
      }
    }
    total += lastRemaining
  }
  return Number(total.toFixed(3))
}

const loadGrid = async () => {
  loading.value = true
  try {
    const [res] = await Promise.all([
      api.kubotaSakaiDueAdjustments.grid({
        start_date: startDate.value,
        horizon_days: horizonDays.value,
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

const importOrders = async () => {
  if (importing.value || loading.value) return
  importing.value = true
  try {
    const res = await api.kubotaSakaiDueAdjustments.importOrders({
      start_date: startDate.value,
      horizon_days: horizonDays.value,
    })
    const d = res.data
    alert(`取込完了: 新規${d.created}件, 更新${d.updated}件, 内示→確定削除${d.deleted_forecast}件`)
    await loadGrid()
  } catch (error) {
    const message = error?.response?.data?.detail || '取込に失敗しました。'
    alert(message)
  } finally {
    importing.value = false
  }
}

const onDeliveryInput = (line, dateKey, rawValue) => {
  const normalized = rawValue.replace(/[^\d.-]/g, '')
  line.deliveryByDate[dateKey] = normalized === '' ? 0 : parseNumber(normalized)
  line._dirty = true
}

const onDeliveryBlur = (line, dateKey) => {
  const qty = parseNumber(line.deliveryByDate[dateKey])
  if (qty < 0) line.deliveryByDate[dateKey] = 0
}

const saveDeliveries = async () => {
  if (saving.value || loading.value) return

  // 変更された行を収集
  const payloadRows = []
  for (const group of groups.value) {
    for (const line of group.lines) {
      if (!line._dirty) continue
      const deliveryByDate = {}
      for (const col of dateColumns.value) {
        const qty = parseNumber(line.deliveryByDate[col.key])
        deliveryByDate[col.key] = qty
      }
      payloadRows.push({
        line_key: line.lineKey,
        delivery_by_date: deliveryByDate,
      })
    }
  }

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
    alert(data?.detail || '保存に失敗しました。')
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
.import-btn {
  background: #dbe8ff;
  border-color: #8daed6;
}
.table-wrap {
  flex: 1;
  overflow: auto;
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 4px;
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
.grid thead .head1 th {
  background: #cfd8ec;
}
.grid thead .head2 th {
  background: #e7edf7;
}
.grid th.product-start,
.grid td.product-start {
  border-left: 2px solid #7b8aa7;
}
.grid th.product-end,
.grid td.product-end {
  border-right: 2px solid #7b8aa7;
}
.head-group {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.head-code {
  font-weight: 700;
}
.head-ship {
  color: #374151;
  font-weight: 500;
}
.grid th.holiday,
.grid td.holiday {
  background: #ffe3e3;
}
.sticky-left {
  position: sticky;
  left: 0;
  z-index: 4;
  background: #fff;
}
.head1 .sticky-left,
.head2 .sticky-left {
  z-index: 6;
}
.date-col {
  text-align: right;
  padding: 3px 8px !important;
}
.date-separator {
  border-right: 3px solid #5f6f8f !important;
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
.readonly-cell {
  color: #4b5563;
}
.readonly-cell.demand .sub-cell {
  background: #f4f7fb;
}
.readonly-cell.demand .sub-cell.forecast {
  background: #eef4fb;
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
.total-row th,
.total-row td {
  position: sticky;
  bottom: 0;
  z-index: 5;
  background: #dbe6f7;
  border-top: 2px solid #9ab1d6;
}
.total-row .total-label {
  text-align: center;
  font-weight: 700;
}
.total-row .total-value {
  text-align: right;
  font-weight: 700;
}
.total-row .total-blank {
  background: #e5edf9;
}
.total-row .error {
  color: #b91c1c;
}
.empty {
  text-align: center;
  color: #6b7280;
  padding: 16px 0;
}
</style>
