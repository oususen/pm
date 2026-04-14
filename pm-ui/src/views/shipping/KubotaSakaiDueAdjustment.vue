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
        <label>検索</label>
        <input v-model.trim="keyword" type="text" placeholder="品番/品名" @keydown.enter="loadGrid" />
      </div>
      <button class="btn save-btn" :disabled="loading || saving" @click="saveAdjustments">保存</button>
      <button class="btn" :disabled="loading" @click="loadGrid">表示のみ</button>
    </div>

    <div class="table-wrap">
      <div class="table-split">
        <div class="main-grid-wrap">
          <table class="grid">
            <colgroup>
              <col style="width: 120px" />
              <col style="width: 220px" />
              <template v-for="col in dateColumns" :key="`col-${col.key}`">
                <col style="width: 82px" />
                <col style="width: 82px" />
                <col style="width: 82px" />
              </template>
            </colgroup>
            <thead>
              <tr class="head1">
                <th rowspan="2" class="sticky code-col">品番</th>
                <th rowspan="2" class="sticky name-col">品名</th>
                <th v-for="col in dateColumns" :key="col.key" colspan="3" :class="col.dayClass">{{ col.label }}</th>
              </tr>
              <tr class="head2">
                <template v-for="col in dateColumns" :key="`${col.key}-sub`">
                  <th :class="col.dayClass">受注</th>
                  <th :class="col.dayClass">納入</th>
                  <th :class="col.dayClass">残量</th>
                </template>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in rows" :key="row.orderKey">
                <td class="sticky code-col">{{ row.productCode }}</td>
                <td class="sticky name-col">{{ row.productName }}</td>
                <template v-for="col in dateColumns" :key="`${row.orderKey}-${col.key}`">
                  <td class="readonly-cell" :class="col.dayClass">{{ formatNumber(row.demandByDate[col.key]) }}</td>
                  <td :class="col.dayClass">
                    <input
                      :value="displayInputValue(row.deliveryByDate[col.key])"
                      type="text"
                      inputmode="decimal"
                      @input="onDeliveryInput(row, col.key, $event.target.value)"
                      @blur="onDeliveryBlur(row, col.key)"
                    />
                  </td>
                  <td class="readonly-cell" :class="col.dayClass">{{ formatNumber(row.remainingByDate[col.key]) }}</td>
                </template>
              </tr>
              <tr v-if="!rows.length">
                <td :colspan="dateColumns.length * 3 + 2" class="empty">データがありません</td>
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
              <tr v-for="row in rows" :key="`total-${row.orderKey}`">
                <td :class="{ error: remainingQty(row) !== 0 }">{{ formatNumber(remainingQty(row)) }}</td>
              </tr>
              <tr v-if="!rows.length">
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

const formatLocalDate = (date) => {
  const yyyy = String(date.getFullYear())
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const dd = String(date.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const startDate = ref(formatLocalDate(new Date()))
const horizonDays = ref(30)
const rows = ref([])
const calendarDayMap = ref({})
const kubotaSakaiCalendarId = ref(null)

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

const isHolidayDate = (dateKey, weekDay) => {
  const day = calendarDayMap.value[dateKey]
  if (day && typeof day.is_working_day === 'boolean') return !day.is_working_day
  return weekDay === 0 || weekDay === 6
}

const resolveKubotaSakaiCalendarId = async () => {
  if (kubotaSakaiCalendarId.value) return kubotaSakaiCalendarId.value

  const normalize = (value) => String(value || '').trim().toLowerCase()
  const pick = (rows = []) => {
    const exactCode = rows.find((row) => {
      const code = normalize(row.calendar_code)
      return code === 'kubota_sakai' || code === 'kobota_sakai' || code === 'kubota-muke' || code === 'kubota_muke'
    })
    if (exactCode) return exactCode

    const nameHit = rows.find((row) => {
      const code = normalize(row.calendar_code)
      const name = normalize(row.calendar_name)
      return (name.includes('クボタ') && name.includes('堺')) || (name.includes('kubota') && name.includes('堺')) || (code.includes('kubota') && code.includes('sakai')) || (code.includes('kobota') && code.includes('sakai'))
    })
    if (nameHit) return nameHit

    const kubotaHit = rows.find((row) => {
      const code = normalize(row.calendar_code)
      return code.includes('kubota') || code.includes('kobota')
    })
    return kubotaHit || null
  }

  // kobota_sakai（typo）にも対応するため、kubotaとkobota両方で検索
  for (const keyword of ['kubota', 'kobota', 'クボタ']) {
    try {
      const res = await api.calendars.getCalendars({ search: keyword, page_size: 500 })
      const rows = res.data?.results || res.data || []
      const found = pick(rows)
      if (found?.id) {
        kubotaSakaiCalendarId.value = found.id
        return found.id
      }
    } catch (error) {
      // 次のキーワードで再試行
    }
  }

  try {
    const fallbackRes = await api.calendars.getCalendars({ page_size: 5000 })
    const rows = fallbackRes.data?.results || fallbackRes.data || []
    const found = pick(rows)
    kubotaSakaiCalendarId.value = found?.id || null
    return kubotaSakaiCalendarId.value
  } catch (error) {
    kubotaSakaiCalendarId.value = null
    return null
  }
}

const loadKubotaSakaiCalendarDays = async () => {
  try {
    const calendarId = await resolveKubotaSakaiCalendarId()
    if (!calendarId) {
      calendarDayMap.value = {}
      return
    }
    const daysRes = await api.calendars.getCalendarDays(calendarId, { page_size: 5000 })
    const days = daysRes.data?.results || daysRes.data || []
    const map = {}
    days.forEach((day) => {
      if (day?.target_date) map[day.target_date] = day
    })
    calendarDayMap.value = map
  } catch (error) {
    calendarDayMap.value = {}
  }
}

const remainingQty = (row) => {
  const orderTotal = Object.values(row.demandByDate).reduce((sum, value) => sum + parseNumber(value), 0)
  const deliveryTotal = Object.values(row.deliveryByDate).reduce((sum, value) => sum + parseNumber(value), 0)
  return Number((orderTotal - deliveryTotal).toFixed(3))
}

const hasAnyVisibleQty = (row) => {
  return dateColumns.value.some((col) => {
    const demand = Math.abs(parseNumber(row.demandByDate[col.key]))
    const delivery = Math.abs(parseNumber(row.deliveryByDate[col.key]))
    const remaining = Math.abs(parseNumber(row.remainingByDate[col.key]))
    return demand > 0.000001 || delivery > 0.000001 || remaining > 0.000001
  })
}

const recalculateRemainingByDate = (row, dateKey) => {
  const demand = parseNumber(row.demandByDate[dateKey])
  const delivery = parseNumber(row.deliveryByDate[dateKey])
  row.remainingByDate[dateKey] = Number((demand - delivery).toFixed(3))
}

const loadGrid = async () => {
  loading.value = true
  try {
    const endDateKey = dateColumns.value[dateColumns.value.length - 1]?.key
    const [res] = await Promise.all([
      api.orders.listOrderLines({
        customer_code: '000196',
        due_date__gte: startDate.value,
        due_date__lte: endDateKey,
        page_size: 10000,
      }),
      loadKubotaSakaiCalendarDays(),
    ])

    const allLines = Array.isArray(res.data?.results) ? res.data.results : (Array.isArray(res.data) ? res.data : [])
    const sakaiLines = allLines.filter((line) => String(line.order_type || '') !== 'FORECAST')
    const forecastLines = allLines.filter((line) => String(line.order_type || '') === 'FORECAST')

    const firmByProductDate = {}
    sakaiLines.forEach((line) => {
      const productCode = String(line.product_code || '')
      const dueDate = String(line.due_date || '')
      const key = `${productCode}__${dueDate}`
      firmByProductDate[key] = (firmByProductDate[key] || 0) + parseNumber(line.quantity)
    })

    const grouped = {}
    const ensureGroup = (productCode, productName) => {
      if (!grouped[productCode]) {
        const demandByDate = {}
        const deliveryByDate = {}
        const remainingByDate = {}
        dateColumns.value.forEach((col) => {
          demandByDate[col.key] = 0
          deliveryByDate[col.key] = 0
          remainingByDate[col.key] = 0
        })
        grouped[productCode] = {
          orderKey: productCode,
          orderLineIds: [],
          baseDueDate: startDate.value,
          productCode,
          productName,
          demandByDate,
          deliveryByDate,
          remainingByDate,
        }
      }
    }

    sakaiLines.forEach((line) => {
      const productCode = String(line.product_code || '')
      const productName = String(line.product_name || '')
      ensureGroup(productCode, productName)
      if (line.id) grouped[productCode].orderLineIds.push(line.id)
      const dueDate = String(line.due_date || '')
      const qty = parseNumber(line.quantity)
      if (Object.prototype.hasOwnProperty.call(grouped[productCode].demandByDate, dueDate)) {
        grouped[productCode].demandByDate[dueDate] += qty
        grouped[productCode].deliveryByDate[dueDate] += qty
      }
    })

    forecastLines.forEach((line) => {
      const productCode = String(line.product_code || '')
      const productName = String(line.product_name || '')
      const dueDate = String(line.due_date || '')
      const firmKey = `${productCode}__${dueDate}`
      if (firmByProductDate[firmKey] && firmByProductDate[firmKey] > 0) return
      ensureGroup(productCode, productName)
      const qty = parseNumber(line.quantity)
      if (Object.prototype.hasOwnProperty.call(grouped[productCode].demandByDate, dueDate)) {
        grouped[productCode].demandByDate[dueDate] += qty
        grouped[productCode].deliveryByDate[dueDate] += qty
      }
    })

    rows.value = Object.values(grouped)
      .filter((item) => {
        if (!keyword.value) return true
        return item.productCode.includes(keyword.value) || item.productName.includes(keyword.value)
      })
      .map((row) => {
        dateColumns.value.forEach((col) => {
          recalculateRemainingByDate(row, col.key)
        })
        row.orderLineIds = Array.from(new Set(row.orderLineIds))
        return row
      })
      .filter((row) => hasAnyVisibleQty(row))
      .sort((a, b) => a.productCode.localeCompare(b.productCode))
  } catch (error) {
    const message = error?.response?.data?.detail || 'データ取得に失敗しました。'
    alert(message)
  } finally {
    loading.value = false
  }
}

const onDeliveryInput = (row, dateKey, rawValue) => {
  const normalized = rawValue.replace(/[^\d.-]/g, '')
  row.deliveryByDate[dateKey] = normalized === '' ? 0 : parseNumber(normalized)
  recalculateRemainingByDate(row, dateKey)
}

const onDeliveryBlur = (row, dateKey) => {
  const qty = parseNumber(row.deliveryByDate[dateKey])
  if (qty <= 0) row.deliveryByDate[dateKey] = 0
  recalculateRemainingByDate(row, dateKey)
}

const saveAdjustments = async () => {
  saving.value = true
  try {
    const payloadRows = rows.value.map((row) => {
      const adjustments = dateColumns.value
        .map((col) => {
          const qty = parseNumber(row.deliveryByDate[col.key])
          if (qty <= 0) return null
          return {
            adjusted_due_date: col.key,
            adjusted_qty: qty,
            remaining_qty: parseNumber(row.remainingByDate[col.key]),
            customer_approved: true,
            note: '',
          }
        })
        .filter(Boolean)

      return {
        order_key: row.orderKey,
        order_line_ids: row.orderLineIds,
        adjustments,
      }
    })

    await api.kubotaSakaiDueAdjustments.bulkSave(payloadRows)
    await loadGrid()
    alert('保存しました。')
  } catch (error) {
    const detail = error?.response?.data?.detail || '保存に失敗しました。'
    const errors = error?.response?.data?.errors
    if (Array.isArray(errors) && errors.length > 0) {
      const lines = errors.map((item) => {
        const key = item.order_key ? `行:${item.order_key}` : '行'
        return `${key} ${item.detail || '入力エラー'}`
      })
      alert([detail, ...lines].join('\n'))
    } else {
      alert(detail)
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
  min-width: 120px;
  padding: 6px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
}
.search-field input {
  min-width: 220px;
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
  min-width: 180px;
}
.readonly-cell {
  text-align: right;
  color: #4b5563;
}
.grid input {
  width: 74px;
  text-align: right;
  padding: 3px 4px;
  border: 1px solid #d1d5db;
  border-radius: 3px;
}
.total-grid {
  width: 88px;
  min-width: 88px;
}
.total-grid th,
.total-grid td {
  text-align: right;
}
.error {
  color: #b91c1c;
  font-weight: 700;
}
.empty {
  text-align: center;
  color: #6b7280;
  padding: 16px 0;
}
</style>
