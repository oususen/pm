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
      <span v-if="lockDate" class="lock-badge">{{ lockDate }} まで締め済</span>
      <span v-if="duePlanLockDate" class="lock-badge plan-lock">{{ duePlanLockDate }} まで計画ロック</span>
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
        <thead ref="theadRef">
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
                <button
                  class="copy-btn"
                  :disabled="loading || saving || importing"
                  @click.stop="applyDemandToPlan(col.group)"
                >→</button>
              </div>
            </th>
          </tr>
          <tr class="head2">
            <template v-for="(col, colIdx) in matrixColumns" :key="`sub-${col.colKey}`">
              <th :class="{ 'product-start': colIdx > 0 }">注番</th>
              <th>受注</th>
              <th>計画</th>
              <th class="product-end">注残</th>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in displayRows"
            :key="row.rowKey"
            :class="{ 'carry-tr': row.isCarry, 'day-row': !row.isCarry, 'locked-row': !row.isCarry && isDateLocked(row.dateKey) }"
          >
            <td class="sticky-left date-col date-separator" :class="row.dayClass">{{ row.label }}</td>
            <template v-if="row.isCarry">
              <template v-for="(col, colIdx) in matrixColumns" :key="`${row.rowKey}-${col.colKey}`">
                <td :class="{ 'product-start': colIdx > 0 }"></td>
                <td></td>
                <td></td>
                <td class="readonly-cell product-end carry-value">{{ formatNumber(row.cells[col.colKey]) }}</td>
              </template>
            </template>
            <template v-else>
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
                      v-if="editableLineAt(row, col, slotIdx - 1)"
                      :ref="(el) => { if (el) inputRefs[`${row.dateKey}-${col.colKey}-${slotIdx - 1}`] = el }"
                      :data-row="row.dateKey"
                      :data-col="col.colKey"
                      :data-slot="slotIdx - 1"
                      :value="displayInputValue(editableLineAt(row, col, slotIdx - 1).deliveryByDate[row.dateKey])"
                      :disabled="isDateLocked(row.dateKey)"
                      :class="{ 'locked-cell': isDateLocked(row.dateKey) }"
                      type="text"
                      inputmode="decimal"
                      @input="onDeliveryInput(editableLineAt(row, col, slotIdx - 1), row.dateKey, $event.target.value)"
                      @blur="onDeliveryBlur(editableLineAt(row, col, slotIdx - 1), row.dateKey)"
                      @keydown.enter.prevent="focusNextRow($event, row.dateKey, col.colKey, slotIdx - 1)"
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
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import api from '@/api/client'

const inputRefs = reactive({})
const theadRef = ref(null)

const setStickyTopValues = () => {
  if (!theadRef.value) return
  const rows = theadRef.value.querySelectorAll('tr')
  let cumTop = 0
  rows.forEach((tr) => {
    const cells = tr.querySelectorAll('th')
    cells.forEach((th) => {
      if (!th.hasAttribute('rowspan')) {
        th.style.top = `${cumTop}px`
      }
    })
    cumTop += tr.offsetHeight
  })
  const rowspanCells = theadRef.value.querySelectorAll('th[rowspan]')
  rowspanCells.forEach((th) => { th.style.top = '0px' })
}

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
const keyword2 = ref('6E')
const startDate = ref(formatLocalDate(new Date()))
const horizonDays = ref(30)
const groups = ref([])
const lockDate = ref(null)
const duePlanLockDate = ref(null)
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

const lineSortCompare = (a, b) => {
  const aFc = a.orderType === 'FORECAST' ? 1 : 0
  const bFc = b.orderType === 'FORECAST' ? 1 : 0
  if (aFc !== bFc) return aFc - bFc
  return String(a.sourceOrderNo || '').localeCompare(String(b.sourceOrderNo || ''))
}

const lineHasAnyValueInHorizon = (line) => {
  return dateColumns.value.some((dateCol) => {
    const demand = parseNumber(line.demandByDate[dateCol.key])
    const delivery = parseNumber(line.deliveryByDate[dateCol.key])
    return demand > 0 || delivery > 0
  })
}

const displayRows = computed(() => {
  // 繰越行
  const hasCarry = matrixColumns.value.some((col) => parseNumber(col.group.carryRemaining) !== 0)
  const carryRow = {
    rowKey: '_carry',
    dateKey: '_carry',
    label: '繰越',
    dayClass: 'carry-row',
    isCarry: true,
    maxSlots: 1,
    cells: {},
  }
  if (hasCarry) {
    matrixColumns.value.forEach((col) => {
      carryRow.cells[col.colKey] = parseNumber(col.group.carryRemaining)
    })
  }

  const dateRows = dateColumns.value.map((dateCol) => {
    const cells = {}
    let maxSlots = 0
    matrixColumns.value.forEach((col) => {
      const visibleLines = col.group.lines
        .filter((line) => {
          const demand = parseNumber(line.demandByDate[dateCol.key])
          const delivery = parseNumber(line.deliveryByDate[dateCol.key])
          return demand > 0 || delivery > 0
        })
        .sort(lineSortCompare)
      cells[col.colKey] = visibleLines
      if (visibleLines.length > maxSlots) maxSlots = visibleLines.length
    })
    return {
      rowKey: dateCol.key,
      dateKey: dateCol.key,
      label: dateCol.label,
      dayClass: dateCol.dayClass,
      isCarry: false,
      maxSlots: maxSlots || 1,
      cells,
    }
  })

  return hasCarry ? [carryRow, ...dateRows] : dateRows
})

const isDateLocked = (dateKey) => {
  if (lockDate.value && dateKey <= lockDate.value) return true
  if (duePlanLockDate.value && dateKey <= duePlanLockDate.value) return true
  return false
}

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

const recalcGroupRemaining = (group) => {
  // 品番+納入場所の全注番を合算して累積注残を計算
  // carry_remaining: 表示期間より前の繰越注残
  const dates = dateColumns.value.map((c) => c.key).sort()
  let running = parseNumber(group.carryRemaining)
  const remainingAtDate = {}
  for (const d of dates) {
    let dayDemand = 0
    let dayDelivery = 0
    for (const line of group.lines) {
      dayDemand += parseNumber(line.demandByDate[d])
      dayDelivery += parseNumber(line.deliveryByDate[d])
    }
    running += dayDelivery - dayDemand
    remainingAtDate[d] = running
  }
  // まず全ラインの注残をクリア
  for (const line of group.lines) {
    for (const d of dates) {
      line.remainingByDate[d] = 0
    }
  }
  // 各日付で、その日にデータがあるラインのうち最後のものに注残をセット
  for (const d of dates) {
    const activeLines = group.lines.filter((line) => {
      return parseNumber(line.demandByDate[d]) > 0 || parseNumber(line.deliveryByDate[d]) > 0
    })
    if (activeLines.length > 0) {
      activeLines[activeLines.length - 1].remainingByDate[d] = remainingAtDate[d]
    }
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
  Object.entries(li.demand_by_date || {}).forEach(([d, q]) => {
    if (Object.prototype.hasOwnProperty.call(demandByDate, d)) demandByDate[d] = parseNumber(q)
  })
  Object.entries(li.delivery_by_date || {}).forEach(([d, q]) => {
    if (Object.prototype.hasOwnProperty.call(deliveryByDate, d)) deliveryByDate[d] = parseNumber(q)
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

const buildGroupFromGridItem = (item) => {
  const group = {
    groupKey: item.group_key,
    productCode: item.product_code,
    shipToCode: item.ship_to_code || '-',
    carryRemaining: parseNumber(item.carry_remaining),
    lines: (item.lines || []).map(buildLine),
  }
  recalcGroupRemaining(group)
  return group
}

const slotLineAt = (row, colKey, slotIdx) => {
  const arr = row.cells[colKey]
  return arr && arr[slotIdx] ? arr[slotIdx] : null
}

const getPrimaryEditableLine = (group) => {
  if (!group?.lines?.length) return null
  const candidates = group.lines.filter(lineHasAnyValueInHorizon).sort(lineSortCompare)
  if (candidates.length > 0) return candidates[0]
  return [...group.lines].sort(lineSortCompare)[0] || null
}

const editableLineAt = (row, col, slotIdx) => {
  const line = slotLineAt(row, col.colKey, slotIdx)
  if (line) return line
  if (slotIdx !== 0) return null
  return getPrimaryEditableLine(col.group)
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
  // 最終日の注残合計（各注番の最終注残）
  const lastDate = dateColumns.value.length ? dateColumns.value[dateColumns.value.length - 1].key : null
  if (!lastDate) return 0
  let total = 0
  for (const line of group.lines) {
    // 最後に注残がある日のremaining
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

const applyDemandToPlan = (group) => {
  if (!group) return
  let changed = false
  for (const line of group.lines) {
    for (const col of dateColumns.value) {
      if (isDateLocked(col.key)) continue
      const demandQty = parseNumber(line.demandByDate[col.key])
      const currentQty = parseNumber(line.deliveryByDate[col.key])
      if (currentQty !== demandQty) {
        line.deliveryByDate[col.key] = demandQty
        changed = true
      }
    }
    if (changed) line._dirty = true
  }
  if (changed) recalcGroupRemaining(group)
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
    lockDate.value = res.data?.lock_date || null
    duePlanLockDate.value = res.data?.due_plan_lock_date || null
    const items = res.data?.rows || []
    groups.value = items.map(buildGroupFromGridItem)
    nextTick(setStickyTopValues)
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

const findGroupForLine = (line) => {
  return groups.value.find((g) => g.lines.includes(line))
}

const onDeliveryInput = (line, dateKey, rawValue) => {
  const normalized = rawValue.replace(/[^\d.-]/g, '')
  line.deliveryByDate[dateKey] = normalized === '' ? 0 : parseNumber(normalized)
  line._dirty = true
  const group = findGroupForLine(line)
  if (group) recalcGroupRemaining(group)
}

const onDeliveryBlur = (line, dateKey) => {
  const qty = parseNumber(line.deliveryByDate[dateKey])
  if (qty < 0) line.deliveryByDate[dateKey] = 0
}

const focusNextRow = (event, currentDateKey, colKey, slotIdx) => {
  const dates = dateColumns.value.map((c) => c.key)
  const currentIdx = dates.indexOf(currentDateKey)
  if (currentIdx < 0) return
  // 次の日付行で同じ列・同じスロットのinputを探す
  for (let i = currentIdx + 1; i < dates.length; i++) {
    const key = `${dates[i]}-${colKey}-${slotIdx}`
    const el = inputRefs[key]
    if (el) {
      el.focus()
      el.select()
      return
    }
  }
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

onMounted(async () => {
  await loadGrid()
  await nextTick()
  setStickyTopValues()
})
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
.lock-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  background: #fef3c7;
  border: 1px solid #f59e0b;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  color: #92400e;
  white-space: nowrap;
}
.import-btn {
  background: #dbe8ff;
  border-color: #8daed6;
}
.lock-badge.plan-lock {
  background: #dbeafe;
  border-color: #3b82f6;
  color: #1e3a8a;
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
  border-collapse: separate;
  border-spacing: 0;
  table-layout: fixed;
}
.grid th,
.grid td {
  border-right: 1px solid #d7dfe8;
  border-bottom: 1px solid #d7dfe8;
  padding: 3px 6px;
  white-space: nowrap;
  font-size: 12px;
  height: 28px;
  box-sizing: border-box;
  vertical-align: top;
}
.grid thead tr:first-child th {
  border-top: 1px solid #d7dfe8;
}
.grid th:first-child,
.grid td:first-child {
  border-left: 1px solid #d7dfe8;
}
.grid th {
  position: sticky;
  z-index: 2;
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
.copy-btn {
  height: 22px;
  min-width: 22px;
  padding: 0 6px;
  border: 1px solid #9fb2d1;
  border-radius: 3px;
  background: #f8fbff;
  color: #1f3b69;
  font-weight: 700;
  line-height: 1;
  cursor: pointer;
}
.copy-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
  border-bottom: 1px solid #d7dfe8;
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
.carry-tr td {
  background: #f0f4ff;
  border-bottom: 2px solid #9ab1d6;
  font-weight: 700;
}
.carry-tr .sticky-left {
  background: #f0f4ff;
}
.carry-value {
  text-align: right;
  padding: 3px 6px !important;
  color: #1e40af;
}
.day-row td {
  border-bottom: 2px solid #94a3b8;
}
.locked-row td {
  background: #f3f4f6 !important;
}
.locked-row .sticky-left {
  background: #f3f4f6 !important;
}
.locked-cell {
  background: #e5e7eb !important;
  color: #9ca3af !important;
  cursor: not-allowed;
}
</style>
