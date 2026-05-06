<template>
  <div class="trip-execution-page">
    <div class="toolbar">
      <label class="field">
        <span>{{ t('shippingTripExecution.departureDate') }}</span>
        <input v-model="departureDate" type="date" />
      </label>
      <label class="field">
        <span>{{ t('shippingTripExecution.businessType') }}</span>
        <select v-model="businessType">
          <option value="">{{ t('shippingTripExecution.all') }}</option>
          <option v-for="item in businessTypes" :key="item" :value="item">{{ businessTypeLabel(item) }}</option>
        </select>
      </label>
      <label class="field">
        <span>{{ t('shippingTripExecution.trip') }}</span>
        <select v-model="tripFilter">
          <option value="">{{ t('shippingTripExecution.all') }}</option>
          <option v-for="item in tripOptions" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <button class="btn" :disabled="loading" @click="loadTrips">{{ t('shippingTripExecution.show') }}</button>
    </div>

    <div class="summary">
      <button class="chip chip-button" :class="{ active: !statusFilter }" @click="setStatusFilter('')">{{ t('shippingTripExecution.totalTrips') }}: {{ summary.total }}</button>
      <button class="chip chip-button" :class="{ active: statusFilter === 'PLANNED' }" @click="setStatusFilter('PLANNED')">{{ t('shippingTripExecution.statusPlanned') }}: {{ summary.planned }}</button>
      <button class="chip chip-button" :class="{ active: statusFilter === 'LOADING' }" @click="setStatusFilter('LOADING')">{{ t('shippingTripExecution.statusLoading') }}: {{ summary.loading }}</button>
      <button class="chip chip-button" :class="{ active: statusFilter === 'DEPARTED' }" @click="setStatusFilter('DEPARTED')">{{ t('shippingTripExecution.statusDeparted') }}: {{ summary.departed }}</button>
      <button class="chip chip-button" :class="{ active: statusFilter === 'CLOSED' }" @click="setStatusFilter('CLOSED')">{{ t('shippingTripExecution.statusClosedInput') }}: {{ summary.closed }}</button>
    </div>

    <div v-if="loading" class="loading">{{ t('shippingTripExecution.loading') }}</div>
    <div v-else-if="!visibleTrips.length" class="empty">{{ t('shippingTripExecution.noTrips') }}</div>

    <div v-else class="trip-list">
      <section v-for="(trip, tripIdx) in visibleTrips" :key="trip.id" class="trip-card" :class="`trip-color-${tripIdx % 6}`">
        <header class="trip-head">
          <h3>{{ t('shippingTripExecution.trip') }}{{ trip.trip_code || trip.trip_ref }}</h3>
          <span class="trip-meta">{{ t('shippingTripExecution.departureTime') }}: {{ trip.departure_time_plan || '-' }} | {{ t('shippingTripExecution.deliveryPlace') }}: {{ trip.ship_to_code || '-' }}</span>
          <span class="status" :class="`status-${String(trip.status || '').toLowerCase()}`">
            {{ statusLabel(trip.status) }}
          </span>
          <small v-if="trip.departure_time_actual" class="actual-time">{{ t('shippingTripExecution.actualDeparture') }}: {{ trip.departure_time_actual }}</small>
        </header>

        <div class="detail-list">
          <div class="detail-head">
            <span>{{ t('shippingTripExecution.product') }}</span>
            <span>{{ t('shippingTripExecution.plan') }}</span>
            <span>{{ isActualInputMode ? t('shippingTripExecution.actual') : t('shippingTripExecution.actualInput') }}</span>
          </div>
          <div v-for="(row, rowIdx) in trip.details" :key="row.allocation_id" class="detail-row" :class="{ 'detail-row-alt': rowIdx % 2 === 1 }">
            <div class="detail-main">
              <span class="product-code">{{ row.product_code }}</span>
              <span class="product-name">{{ row.product_name }}</span>
            </div>
            <div class="detail-qty">{{ row.qty }}</div>
            <div class="actual-input-wrap">
              <input
                v-if="isExecutionMode || isActualInputMode"
                :value="actualQtyValue(trip.id, row.allocation_id, row.qty)"
                type="number"
                step="1"
                min="0"
                :disabled="!canRegisterActual(trip)"
                @input="setActualQty(trip.id, row.allocation_id, $event.target.value)"
              />
              <div v-else class="actual-readonly">
                {{ actualQtyValue(trip.id, row.allocation_id, row.qty) }}
              </div>
            </div>
            <div v-if="isExecutionMode || isActualInputMode" class="split-wrap">
              <div
                v-for="(split, splitIdx) in splitRows(trip.id, row.allocation_id, row)"
                :key="`${row.allocation_id}-${splitIdx}`"
                class="split-row"
              >
                <input
                  type="date"
                  :value="split.production_date"
                  :disabled="!canEditProductionDate(trip)"
                  @input="setSplitDate(trip.id, row.allocation_id, splitIdx, $event.target.value)"
                />
                <input
                  type="number"
                  min="0"
                  step="1"
                  :value="split.quantity"
                  :disabled="!canEditProductionDate(trip)"
                  @input="setSplitQty(trip.id, row.allocation_id, splitIdx, $event.target.value)"
                />
                <button
                  type="button"
                  class="btn split-btn"
                  :disabled="!canEditProductionDate(trip)"
                  @click="removeSplitRow(trip.id, row.allocation_id, splitIdx, row)"
                >
                  {{ t('shippingTripExecution.delete') }}
                </button>
              </div>
              <div class="split-actions">
                <button
                  type="button"
                  class="btn split-add"
                  :disabled="!canEditProductionDate(trip)"
                  @click="addSplitRow(trip.id, row.allocation_id)"
                >
                  {{ t('shippingTripExecution.addProductionDate') }}
                </button>
                <button
                  type="button"
                  class="btn split-save"
                  :disabled="updatingTripId === trip.id || !canEditProductionDate(trip)"
                  @click="saveProductionDates(trip)"
                >
                  {{ t('shippingTripExecution.saveProductionDates') }}
                </button>
              </div>
            </div>
          </div>
          <div v-if="!trip.details.length" class="no-detail">{{ t('shippingTripExecution.noDetails') }}</div>
        </div>

        <div v-if="isActualInputMode" class="actual-row">
          <label class="field inline-field">
            <span>{{ t('shippingTripExecution.actualDate') }}</span>
            <input
              :value="actualDateValue(trip.id, trip.departure_date)"
              type="date"
              :disabled="!canRegisterActual(trip)"
              @input="setActualDate(trip.id, $event.target.value)"
            />
          </label>
          <button
            class="btn actual"
            :disabled="updatingTripId === trip.id || !trip.details.length || !canRegisterActual(trip)"
            @click="registerActual(trip)"
          >
            {{ t('shippingTripExecution.registerActual') }}
          </button>
        </div>

        <div class="actions">
          <button
            class="btn complete"
            :disabled="updatingTripId === trip.id || !canMarkLoading(trip)"
            @click="updateTripStatus(trip, 'mark_loading')"
          >
            {{ t('shippingTripExecution.markLoading') }}
          </button>
          <button
            class="btn depart"
            :disabled="updatingTripId === trip.id || !canMarkDeparted(trip)"
            @click="updateTripStatus(trip, 'mark_departed')"
          >
            {{ t('shippingTripExecution.markDeparted') }}
          </button>
          <button
            class="btn reopen"
            :disabled="updatingTripId === trip.id || !canReopen(trip)"
            @click="updateTripStatus(trip, 'reopen')"
          >
            {{ t('shippingTripExecution.reopen') }}
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'
import { t } from '@/i18n'

const formatDate = (d) => {
  const yyyy = String(d.getFullYear())
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

const departureDate = ref(formatDate(new Date()))
const businessType = ref('')
const businessTypes = ref([])
const trips = ref([])
const prevBusinessDay = ref('')
const actualQtyMap = ref({})
const actualDateMap = ref({})
const productionSplitMap = ref({})
const tripFilter = ref('')
const statusFilter = ref('')
const loading = ref(false)
const updatingTripId = ref(null)
const summary = ref({ total: 0, planned: 0, loading: 0, departed: 0, closed: 0 })
const route = useRoute()
const isActualInputMode = computed(() => Boolean(route.meta?.actualInputEnabled))
const isExecutionMode = computed(() => !isActualInputMode.value)
const canTripEdit = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  const routeResource = route.meta?.resource
  if (routeResource && permissions.some((item) => item.resource === routeResource)) {
    return hasPermission(user, routeResource, 'edit')
  }
  return hasPermission(user, 'shipping', 'edit')
})
const canActualEdit = computed(() => canTripEdit.value && (isExecutionMode.value || isActualInputMode.value))
const canStatusEdit = computed(() => canTripEdit.value && !isActualInputMode.value)
const canEditProductionDate = (trip) => isExecutionMode.value && canRegisterActual(trip)

const visibleTrips = computed(() => {
  let list = trips.value || []
  if (tripFilter.value) {
    list = list.filter((trip) => String(trip.trip_code || trip.trip_ref || '') === tripFilter.value)
  }
  if (!statusFilter.value) return list
  return list.filter((trip) => trip.status === statusFilter.value)
})

const tripOptions = computed(() => {
  const set = new Set()
  ;(trips.value || []).forEach((trip) => {
    const code = String(trip.trip_code || trip.trip_ref || '').trim()
    if (code) set.add(code)
  })
  return Array.from(set)
})

const statusLabel = (status) => {
  if (status === 'PLANNED') return t('shippingTripExecution.statusPlanned')
  if (status === 'LOADING') return t('shippingTripExecution.statusLoading')
  if (status === 'DEPARTED') return t('shippingTripExecution.statusDeparted')
  if (status === 'CLOSED') return t('shippingTripExecution.statusClosedInput')
  return status || '-'
}

const businessTypeLabel = (value) => {
  const map = {
    KUBOTA_SAKAI: 'クボタ堺',
    KUBOTA_HIRAKATA: 'クボタ枚方',
    TIERA_HQ: 'ティエラ本社',
    TIERA_HOKUSHIN: 'ティエラ北進',
    TIERA_FUJISHOJI: 'ティエラ富士商事',
    TIERA_WATANABE: 'ティエラ渡辺',
  }
  return map[value] || value
}

const canMarkLoading = (trip) => canStatusEdit.value && trip?.status === 'PLANNED'
const canMarkDeparted = (trip) => canStatusEdit.value && ['PLANNED', 'LOADING'].includes(trip?.status)
const canReopen = (trip) => canStatusEdit.value && ['LOADING', 'DEPARTED', 'CLOSED'].includes(trip?.status)
const canRegisterActual = (trip) => {
  if (!canActualEdit.value) return false
  if (isActualInputMode.value) return trip?.status === 'DEPARTED'
  return trip?.status !== 'CLOSED'
}

const parseQty = (value) => {
  const num = Number(String(value ?? '').replace(/,/g, ''))
  if (!Number.isFinite(num) || num <= 0) return 0
  return Math.floor(num)
}

const initActualInputState = (tripList) => {
  const nextQtyMap = {}
  const nextDateMap = {}
  const nextSplitMap = {}
  ;(tripList || []).forEach((trip) => {
    nextDateMap[trip.id] = actualDateMap.value[trip.id] || trip.departure_date
    const byAlloc = {}
    const byAllocSplit = {}
    ;(trip.details || []).forEach((row) => {
      byAlloc[row.allocation_id] = actualQtyMap.value[trip.id]?.[row.allocation_id] ?? String(parseQty(row.qty))
      const existing = productionSplitMap.value[trip.id]?.[row.allocation_id]
      if (Array.isArray(existing) && existing.length) {
        byAllocSplit[row.allocation_id] = existing
      } else if (Array.isArray(row.production_splits) && row.production_splits.length) {
        byAllocSplit[row.allocation_id] = row.production_splits.map((item) => ({
          production_date: item.production_date || '',
          quantity: String(parseQty(item.quantity || 0)),
        }))
      } else {
        byAllocSplit[row.allocation_id] = [{ production_date: prevBusinessDay.value, quantity: String(parseQty(row.qty)) }]
      }
    })
    nextQtyMap[trip.id] = byAlloc
    nextSplitMap[trip.id] = byAllocSplit
  })
  actualQtyMap.value = nextQtyMap
  actualDateMap.value = nextDateMap
  productionSplitMap.value = nextSplitMap
}

const actualQtyValue = (tripId, allocationId, fallbackQty) =>
  actualQtyMap.value[tripId]?.[allocationId] ?? String(parseQty(fallbackQty))

const setActualQty = (tripId, allocationId, value) => {
  const nextTrip = { ...(actualQtyMap.value[tripId] || {}) }
  nextTrip[allocationId] = String(value ?? '')
  actualQtyMap.value = { ...actualQtyMap.value, [tripId]: nextTrip }
}

const actualDateValue = (tripId, fallbackDate) =>
  actualDateMap.value[tripId] || fallbackDate

const setActualDate = (tripId, value) => {
  actualDateMap.value = { ...actualDateMap.value, [tripId]: value }
}

const splitRows = (tripId, allocationId, row) => {
  const rows = productionSplitMap.value[tripId]?.[allocationId]
  if (Array.isArray(rows) && rows.length) return rows
  return [{ production_date: '', quantity: String(parseQty(row?.qty || 0)) }]
}

const setSplitDate = (tripId, allocationId, splitIdx, value) => {
  const next = [...(productionSplitMap.value[tripId]?.[allocationId] || [])]
  if (!next[splitIdx]) return
  next[splitIdx] = { ...next[splitIdx], production_date: value || '' }
  productionSplitMap.value = {
    ...productionSplitMap.value,
    [tripId]: { ...(productionSplitMap.value[tripId] || {}), [allocationId]: next },
  }
}

const setSplitQty = (tripId, allocationId, splitIdx, value) => {
  const next = [...(productionSplitMap.value[tripId]?.[allocationId] || [])]
  if (!next[splitIdx]) return
  next[splitIdx] = { ...next[splitIdx], quantity: String(value ?? '') }
  productionSplitMap.value = {
    ...productionSplitMap.value,
    [tripId]: { ...(productionSplitMap.value[tripId] || {}), [allocationId]: next },
  }
}

const addSplitRow = (tripId, allocationId) => {
  const next = [...(productionSplitMap.value[tripId]?.[allocationId] || [])]
  next.push({ production_date: prevBusinessDay.value, quantity: '' })
  productionSplitMap.value = {
    ...productionSplitMap.value,
    [tripId]: { ...(productionSplitMap.value[tripId] || {}), [allocationId]: next },
  }
}

const removeSplitRow = (tripId, allocationId, splitIdx, row) => {
  const next = [...(productionSplitMap.value[tripId]?.[allocationId] || [])]
  next.splice(splitIdx, 1)
  if (!next.length) {
    next.push({ production_date: '', quantity: String(parseQty(row?.qty || 0)) })
  }
  productionSplitMap.value = {
    ...productionSplitMap.value,
    [tripId]: { ...(productionSplitMap.value[tripId] || {}), [allocationId]: next },
  }
}

const loadTrips = async () => {
  loading.value = true
  try {
    const res = await api.shippingTrips.execution({
      departure_date: departureDate.value,
      business_type: businessType.value || undefined,
    })
    const data = res.data || {}
    businessTypes.value = Array.isArray(data.business_types) ? data.business_types : []
    prevBusinessDay.value = data.prev_business_day || ''
    summary.value = data.summary || { total: 0, planned: 0, loading: 0, departed: 0, closed: 0 }
    trips.value = Array.isArray(data.trips) ? data.trips : []
    initActualInputState(trips.value)
  } catch (error) {
    const msg = error?.response?.data?.detail || '便データの取得に失敗しました。'
    alert(msg)
  } finally {
    loading.value = false
  }
}

const setStatusFilter = (status) => {
  statusFilter.value = status
}

const buildActualPayload = (trip) =>
  (trip.details || []).map((row) => ({
    allocation_id: row.allocation_id,
    quantity: parseQty(actualQtyValue(trip.id, row.allocation_id, row.qty)),
    production_splits: (splitRows(trip.id, row.allocation_id, row) || [])
      .map((item) => ({
        production_date: item.production_date || '',
        quantity: parseQty(item.quantity),
      }))
      .filter((item) => item.production_date && item.quantity > 0),
  }))

const saveProductionDates = async (trip) => {
  if (!canEditProductionDate(trip)) {
    alert('生産日内訳の編集権限がありません。')
    return
  }
  updatingTripId.value = trip.id
  try {
    const res = await api.shippingTrips.updateExecutionStatus({
      trip_id: trip.id,
      action: 'save_production_dates',
      actuals: buildActualPayload(trip),
    })
    const d = res.data || {}
    alert(`生産日保存: ${d.updated || 0}件`)
    await loadTrips()
  } catch (error) {
    const msg = error?.response?.data?.detail || '生産日内訳の保存に失敗しました。'
    alert(msg)
  } finally {
    updatingTripId.value = null
  }
}

const registerActual = async (trip) => {
  if (!canRegisterActual(trip)) {
    alert('実績登録の編集権限がありません。')
    return
  }
  const shipmentDate = actualDateValue(trip.id, trip.departure_date)
  if (!shipmentDate) {
    alert('実績日を入力してください。')
    return
  }
  const actuals = buildActualPayload(trip)
  updatingTripId.value = trip.id
  try {
    const res = await api.shippingTrips.updateExecutionStatus({
      trip_id: trip.id,
      action: 'register_actual',
      shipment_date: shipmentDate,
      actuals,
    })
    const d = res.data || {}
    alert(`実績登録: 新規${d.created || 0}件 / 更新${d.updated || 0}件 / 削除${d.deleted || 0}件`)
    await loadTrips()
  } catch (error) {
    const msg = error?.response?.data?.detail || '実績登録に失敗しました。'
    alert(msg)
  } finally {
    updatingTripId.value = null
  }
}

const updateTripStatus = async (trip, action) => {
  if (!canStatusEdit.value) {
    alert('ステータス更新の編集権限がありません。')
    return
  }
  updatingTripId.value = trip.id
  try {
    const res = await api.shippingTrips.updateExecutionStatus({
      trip_id: trip.id,
      action,
    })
    const updated = res.data?.trip
    if (updated) {
      const idx = trips.value.findIndex((t) => t.id === updated.id)
      if (idx >= 0) trips.value[idx] = updated
    }
    await loadTrips()
  } catch (error) {
    const msg = error?.response?.data?.detail || 'ステータス更新に失敗しました。'
    alert(msg)
  } finally {
    updatingTripId.value = null
  }
}

onMounted(loadTrips)
</script>

<style scoped>
.trip-execution-page {
  padding: 4px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 900px;
  margin: 0 auto;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: flex-end;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 18px;
}
.field input,
.field select {
  min-width: 160px;
  height: 42px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 8px;
  font-size: 18px;
}
.summary {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.chip {
  background: #eef2ff;
  border: 1px solid #c7d2fe;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 18px;
}
.chip-button {
  cursor: pointer;
}
.chip-button.active {
  background: #dbeafe;
  border-color: #60a5fa;
}
.trip-list {
  display: grid;
  gap: 6px;
}
.trip-card {
  background: #fff;
  border: 1px solid #dbe2ee;
  border-radius: 8px;
  padding: 4px 6px;
  border-left: 5px solid #94a3b8;
}
.trip-color-0 { border-left-color: #3b82f6; background: #eff6ff; }
.trip-color-1 { border-left-color: #f59e0b; background: #fffbeb; }
.trip-color-2 { border-left-color: #10b981; background: #ecfdf5; }
.trip-color-3 { border-left-color: #8b5cf6; background: #f5f3ff; }
.trip-color-4 { border-left-color: #ef4444; background: #fef2f2; }
.trip-color-5 { border-left-color: #06b6d4; background: #ecfeff; }
.trip-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 2px;
  flex-wrap: wrap;
}
.trip-head h3 {
  margin: 0;
  font-size: 30px;
}
.trip-meta {
  font-size: 18px;
  color: #475569;
}
.actual-time {
  font-size: 16px;
  color: #475569;
  margin-left: auto;
}
.status {
  border-radius: 999px;
  padding: 3px 12px;
  font-size: 18px;
  border: 1px solid;
}
.status-planned {
  background: #f8fafc;
  border-color: #cbd5e1;
}
.status-loading {
  background: #fef9c3;
  border-color: #facc15;
}
.status-departed {
  background: #dcfce7;
  border-color: #22c55e;
}
.status-closed {
  background: #e2e8f0;
  border-color: #64748b;
}
.detail-list {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
}
.detail-head,
.detail-row {
  display: grid;
  grid-template-columns: 1fr 80px 120px;
  gap: 4px;
  align-items: center;
  padding: 3px 6px;
}
.detail-head {
  background: #f8fafc;
  font-size: 16px;
  font-weight: 700;
  padding: 2px 6px;
}
.detail-row {
  border-top: 2px solid #cbd5e1;
  background: #bfdbfe;
}
.detail-row-alt {
  background: #bbf7d0;
}
.split-wrap {
  grid-column: 1 / -1;
  margin-top: 1px;
  display: grid;
  gap: 2px;
}
.split-row {
  display: grid;
  grid-template-columns: 1fr 100px 80px;
  gap: 3px;
}
.split-row input {
  height: 38px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 0 6px;
  font-size: 18px;
}
.split-btn,
.split-add,
.split-save {
  min-height: 38px;
  font-size: 18px;
  padding: 0 8px;
}
.split-actions {
  display: flex;
  gap: 6px;
}
.detail-main {
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.product-code {
  font-size: 21px;
  font-weight: 700;
}
.product-name {
  margin-left: 6px;
  font-size: 18px;
  color: #475569;
}
.detail-qty {
  text-align: right;
  font-size: 27px;
  font-weight: 700;
}
.actual-input-wrap input {
  width: 100%;
  height: 40px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 0 6px;
  font-size: 24px;
  text-align: right;
}
.actual-readonly {
  width: 100%;
  min-height: 40px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 4px 6px;
  font-size: 27px;
  line-height: 1;
  text-align: right;
  color: #475569;
  background: #f8fafc;
}
.no-detail {
  text-align: center;
  color: #64748b;
  padding: 6px;
}
.actual-row {
  margin-top: 2px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: flex-end;
}
.inline-field {
  min-width: 160px;
}
.actions {
  margin-top: 2px;
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.btn {
  min-height: 42px;
  border: 1px solid #cbd5e1;
  background: #fff;
  border-radius: 4px;
  padding: 0 10px;
  cursor: pointer;
  font-size: 21px;
}
.btn.complete {
  background: #fffbeb;
  border-color: #f59e0b;
}
.btn.depart {
  background: #ecfdf5;
  border-color: #22c55e;
}
.btn.reopen {
  background: #fff1f2;
  border-color: #f43f5e;
}
.btn.actual {
  background: #eff6ff;
  border-color: #60a5fa;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.loading,
.empty {
  text-align: center;
  color: #64748b;
  padding: 12px 0;
}
@media (max-width: 640px) {
  .trip-execution-page {
    padding: 6px;
    max-width: 100%;
  }
  .toolbar {
    display: grid;
    grid-template-columns: 1fr;
  }
  .field input,
  .field select,
  .btn {
    width: 100%;
  }
  .trip-head {
    flex-wrap: wrap;
    gap: 4px;
  }
  .actual-time {
    margin-left: 0;
    width: 100%;
  }
  .actions {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
  }
  .detail-head,
  .detail-row {
    grid-template-columns: 1fr 70px 100px;
    gap: 4px;
    padding: 4px 6px;
  }
  .product-code {
    font-size: 19px;
  }
  .product-name {
    font-size: 16px;
  }
  .detail-qty {
    font-size: 24px;
  }
  .actual-input-wrap input {
    height: 38px;
    font-size: 21px;
    padding: 0 4px;
  }
  .actual-readonly {
    min-height: 38px;
    font-size: 24px;
    padding: 4px 4px;
  }
  .actual-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
  }
  .inline-field {
    min-width: 0;
  }
  .btn {
    min-height: 48px;
    font-size: 19px;
    padding: 0 8px;
  }
  .summary {
    gap: 4px;
  }
  .chip {
    font-size: 16px;
    padding: 3px 8px;
  }
  .split-row {
    grid-template-columns: 1fr 80px 52px;
  }
}
</style>

