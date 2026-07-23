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
      <DataSourceDialog title="" :sources="dsSources" />
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
            <span class="detail-head-main">{{ t('shippingTripExecution.product') }}</span>
            <span class="detail-head-plan">{{ t('shippingTripExecution.plan') }}</span>
            <span class="detail-head-actual">{{ isActualInputMode ? t('shippingTripExecution.actual') : t('shippingTripExecution.actualInput') }}</span>
          </div>
          <div v-for="(row, rowIdx) in trip.details" :key="row.allocation_id" class="detail-row" :class="{ 'detail-row-alt': rowIdx % 2 === 1 }">
            <div class="detail-main">
              <div class="detail-main-left">
                <span class="product-code">{{ row.product_code }}</span>
                <span class="product-name">{{ row.product_name }}</span>
                <span class="detail-shipto">{{ row.ship_to_code || '-' }}</span>
              </div>
            </div>
            <div class="detail-qty">{{ row.qty }}</div>
            <div class="actual-input-wrap">
              <input
                v-if="isExecutionMode || isActualInputMode"
                :value="actualQtyValue(trip.id, row.allocation_id, row.qty)"
                type="number"
                step="1"
                min="0"
                :disabled="true"
                readonly
              />
              <div v-else class="actual-readonly">
                {{ actualQtyValue(trip.id, row.allocation_id, row.qty) }}
              </div>
            </div>
            <div v-if="isExecutionMode || isActualInputMode" class="split-wrap">
              <div class="split-head">
                <span>{{ t('shippingTripExecution.productionDate') }}</span>
                <span>{{ t('shippingTripExecution.quantity') }}</span>
                <span>{{ t('shippingTripExecution.orderNo') }}</span>
                <span></span>
              </div>
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
                  @input="setSplitQty(trip.id, row.allocation_id, splitIdx, $event.target.value, row)"
                />
                <div class="split-order-no" :title="split.source_order_no || ''">
                  {{ split.source_order_no || '-' }}
                </div>
                <button
                  type="button"
                  class="btn split-btn"
                  :disabled="!canEditProductionDate(trip)"
                  @click="removeSplitRow(trip.id, row.allocation_id, splitIdx, row)"
                >
                  ×
                </button>
              </div>
              <div class="split-actions">
                <button
                  type="button"
                  class="btn split-add"
                  :disabled="!canEditProductionDate(trip)"
                  @click="addSplitRow(trip.id, row.allocation_id, row)"
                >
                  {{ t('shippingTripExecution.addProductionDate') }}
                </button>
                <button
                  type="button"
                  class="btn split-save"
                  :disabled="updatingTripId === trip.id || !canEditProductionDate(trip) || isAllocationSplitSaved(row.allocation_id)"
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
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '便 読み書き', table: 't_shipping_trip', desc: '便ヘッダ（ステータス・出発時刻）' },
  { op: '便割付 読み取り', table: 't_shipping_trip_allocation', desc: '便ごとの製品割付明細' },
  { op: '出荷実績 読み取り', table: 't_shipment_actual', desc: '出荷実績数量' },
]

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
const editedAllocationIds = ref(new Set())
const savedAllocationIds = ref(new Set())
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
const isAllocationSplitSaved = (allocationId) =>
  savedAllocationIds.value.has(allocationId) && !editedAllocationIds.value.has(allocationId)

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

const canMarkDeparted = (trip) => canStatusEdit.value && trip?.status === 'LOADING'
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

const sumSplitQuantities = (rows, fallbackQty = 0) => {
  if (!Array.isArray(rows) || !rows.length) return parseQty(fallbackQty)
  return rows.reduce((sum, item) => sum + parseQty(item?.quantity), 0)
}

const actualMatchesPlan = (trip) =>
  (trip?.details || []).every((row) => parseQty(actualQtyValue(trip.id, row.allocation_id, row.qty)) === parseQty(row.qty))

const canMarkLoading = (trip) => canStatusEdit.value && trip?.status === 'PLANNED'

const syncActualQtyWithSplits = (tripId, allocationId, rows, fallbackQty = 0) => {
  const nextTrip = { ...(actualQtyMap.value[tripId] || {}) }
  nextTrip[allocationId] = String(sumSplitQuantities(rows, fallbackQty))
  actualQtyMap.value = { ...actualQtyMap.value, [tripId]: nextTrip }
}

const initActualInputState = (tripList) => {
  const nextQtyMap = {}
  const nextDateMap = {}
  const nextSplitMap = {}
  const initialSaved = new Set()
  ;(tripList || []).forEach((trip) => {
    nextDateMap[trip.id] = actualDateMap.value[trip.id] || trip.departure_date
    const byAlloc = {}
    const byAllocSplit = {}
    ;(trip.details || []).forEach((row) => {
      const existing = productionSplitMap.value[trip.id]?.[row.allocation_id]
      if (Array.isArray(existing) && existing.length) {
        byAllocSplit[row.allocation_id] = existing
      } else if (Array.isArray(row.production_splits) && row.production_splits.length) {
        byAllocSplit[row.allocation_id] = row.production_splits.map((item) => ({
          production_date: item.production_date || '',
          quantity: String(parseQty(item.quantity || 0)),
          source_order_no: item.source_order_no || row.source_order_no || '',
        }))
        initialSaved.add(row.allocation_id)
      } else {
        byAllocSplit[row.allocation_id] = [{
          production_date: prevBusinessDay.value,
          quantity: String(parseQty(row.qty)),
          source_order_no: row.source_order_no || '',
        }]
      }
      byAlloc[row.allocation_id] = String(sumSplitQuantities(byAllocSplit[row.allocation_id], row.qty))
    })
    nextQtyMap[trip.id] = byAlloc
    nextSplitMap[trip.id] = byAllocSplit
  })
  actualQtyMap.value = nextQtyMap
  actualDateMap.value = nextDateMap
  productionSplitMap.value = nextSplitMap
  savedAllocationIds.value = initialSaved
  editedAllocationIds.value = new Set()
}

const actualQtyValue = (tripId, allocationId, fallbackQty) =>
  actualQtyMap.value[tripId]?.[allocationId] ?? String(parseQty(fallbackQty))

const actualDateValue = (tripId, fallbackDate) =>
  actualDateMap.value[tripId] || fallbackDate

const setActualDate = (tripId, value) => {
  actualDateMap.value = { ...actualDateMap.value, [tripId]: value }
}

const splitRows = (tripId, allocationId, row) => {
  const rows = productionSplitMap.value[tripId]?.[allocationId]
  if (Array.isArray(rows) && rows.length) return rows
  return [{ production_date: '', quantity: String(parseQty(row?.qty || 0)), source_order_no: row?.source_order_no || '' }]
}

const markAllocationEdited = (allocationId) => {
  editedAllocationIds.value = new Set([...editedAllocationIds.value, allocationId])
  savedAllocationIds.value = new Set([...savedAllocationIds.value].filter((id) => id !== allocationId))
}

const setSplitDate = (tripId, allocationId, splitIdx, value) => {
  const next = [...(productionSplitMap.value[tripId]?.[allocationId] || [])]
  if (!next[splitIdx]) return
  next[splitIdx] = { ...next[splitIdx], production_date: value || '' }
  productionSplitMap.value = {
    ...productionSplitMap.value,
    [tripId]: { ...(productionSplitMap.value[tripId] || {}), [allocationId]: next },
  }
  markAllocationEdited(allocationId)
}

const setSplitQty = (tripId, allocationId, splitIdx, value, row) => {
  const next = [...(productionSplitMap.value[tripId]?.[allocationId] || [])]
  if (!next[splitIdx]) return
  next[splitIdx] = { ...next[splitIdx], quantity: String(value ?? '') }
  productionSplitMap.value = {
    ...productionSplitMap.value,
    [tripId]: { ...(productionSplitMap.value[tripId] || {}), [allocationId]: next },
  }
  syncActualQtyWithSplits(tripId, allocationId, next, row?.qty)
  markAllocationEdited(allocationId)
}

const addSplitRow = (tripId, allocationId, row) => {
  const next = [...(productionSplitMap.value[tripId]?.[allocationId] || [])]
  next.push({ production_date: prevBusinessDay.value, quantity: '', source_order_no: row?.source_order_no || '' })
  productionSplitMap.value = {
    ...productionSplitMap.value,
    [tripId]: { ...(productionSplitMap.value[tripId] || {}), [allocationId]: next },
  }
  syncActualQtyWithSplits(tripId, allocationId, next, row?.qty)
  markAllocationEdited(allocationId)
}

const removeSplitRow = (tripId, allocationId, splitIdx, row) => {
  const next = [...(productionSplitMap.value[tripId]?.[allocationId] || [])]
  next.splice(splitIdx, 1)
  if (!next.length) {
    next.push({
      production_date: '',
      quantity: String(parseQty(row?.qty || 0)),
      source_order_no: row?.source_order_no || '',
    })
  }
  productionSplitMap.value = {
    ...productionSplitMap.value,
    [tripId]: { ...(productionSplitMap.value[tripId] || {}), [allocationId]: next },
  }
  syncActualQtyWithSplits(tripId, allocationId, next, row?.qty)
  markAllocationEdited(allocationId)
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
    const msg = error?.response?.data?.detail || t('shippingTripExecution.error.loadTrips')
    alert(msg)
  } finally {
    loading.value = false
  }
}

const applyRouteQuery = () => {
  const query = route.query || {}
  if (typeof query.departure_date === 'string' && query.departure_date) {
    departureDate.value = query.departure_date
  }
  if (typeof query.business_type === 'string') {
    businessType.value = query.business_type
  }
  if (typeof query.trip_code === 'string') {
    tripFilter.value = query.trip_code
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
        source_order_no: String(item.source_order_no || row.source_order_no || ''),
      }))
      .filter((item) => item.production_date && item.quantity > 0),
  }))

const saveProductionDates = async (trip) => {
  if (!canEditProductionDate(trip)) {
    alert(t('shippingTripExecution.error.editProductionDatesDenied'))
    return
  }
  updatingTripId.value = trip.id
  try {
    const res = await api.shippingTrips.updateExecutionStatus({
      trip_id: trip.id,
      trip_ids: trip.trip_ids || [trip.id],
      action: 'save_production_dates',
      actuals: buildActualPayload(trip),
    })
    const d = res.data || {}
    const allocIds = (trip.details || []).map((r) => r.allocation_id)
    savedAllocationIds.value = new Set([...savedAllocationIds.value, ...allocIds])
    editedAllocationIds.value = new Set([...editedAllocationIds.value].filter((id) => !allocIds.includes(id)))
    alert(t('shippingTripExecution.success.saveProductionDates', { updated: d.updated || 0 }))
  } catch (error) {
    const msg = error?.response?.data?.detail || t('shippingTripExecution.error.saveProductionDates')
    alert(msg)
  } finally {
    updatingTripId.value = null
  }
}

const registerActual = async (trip) => {
  if (!canRegisterActual(trip)) {
    alert(t('shippingTripExecution.error.registerActualDenied'))
    return
  }
  const shipmentDate = actualDateValue(trip.id, trip.departure_date)
  if (!shipmentDate) {
    alert(t('shippingTripExecution.error.actualDateRequired'))
    return
  }
  const actuals = buildActualPayload(trip)
  updatingTripId.value = trip.id
  try {
    const res = await api.shippingTrips.updateExecutionStatus({
      trip_id: trip.id,
      trip_ids: trip.trip_ids || [trip.id],
      action: 'register_actual',
      shipment_date: shipmentDate,
      actuals,
    })
    const d = res.data || {}
    alert(t('shippingTripExecution.success.registerActual', {
      created: d.created || 0,
      updated: d.updated || 0,
      deleted: d.deleted || 0,
    }))
    await loadTrips()
  } catch (error) {
    const msg = error?.response?.data?.detail || t('shippingTripExecution.error.registerActual')
    alert(msg)
  } finally {
    updatingTripId.value = null
  }
}

const updateTripStatus = async (trip, action) => {
  if (!canStatusEdit.value) {
    alert(t('shippingTripExecution.error.updateStatusDenied'))
    return
  }
  if (action === 'mark_loading') {
    const allocIds = (trip.details || []).map((r) => r.allocation_id)
    const hasEdited = allocIds.some((id) => editedAllocationIds.value.has(id))
    const hasSaved = allocIds.some((id) => savedAllocationIds.value.has(id))
    if (hasEdited) {
      alert(t('shippingTripExecution.error.unsavedProductionDates'))
      return
    }
    if (!hasSaved) {
      if (!confirm(t('shippingTripExecution.confirm.defaultProductionDates'))) {
        return
      }
    }
    if (!actualMatchesPlan(trip)) {
      alert(t('shippingTripExecution.error.planActualMismatch'))
      return
    }
  }
  updatingTripId.value = trip.id
  try {
    const res = await api.shippingTrips.updateExecutionStatus({
      trip_id: trip.id,
      trip_ids: trip.trip_ids || [trip.id],
      action,
      actuals: ['mark_loading', 'mark_departed'].includes(action) ? buildActualPayload(trip) : undefined,
    })
    const updated = res.data?.trip
    if (updated) {
      const idx = trips.value.findIndex((t) => t.id === updated.id)
      if (idx >= 0) trips.value[idx] = updated
    }
    await loadTrips()
  } catch (error) {
    const msg = error?.response?.data?.detail || t('shippingTripExecution.error.updateStatus')
    alert(msg)
  } finally {
    updatingTripId.value = null
  }
}

onMounted(async () => {
  applyRouteQuery()
  await loadTrips()
})
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
.detail-head-main {
  text-align: left;
}
.detail-head-plan,
.detail-head-actual {
  width: 100%;
  box-sizing: border-box;
  text-align: right;
}
.detail-head-plan {
  padding-right: 6px;
}
.detail-head-actual {
  padding-right: 7px;
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
.split-head,
.split-row {
  display: grid;
  grid-template-columns: 1fr 100px 120px 36px;
  gap: 3px;
}
.split-head {
  font-size: 14px;
  font-weight: 700;
  color: #334155;
  padding: 2px 0 0;
}
.split-head span:nth-child(2),
.split-head span:nth-child(3) {
  text-align: center;
}
.split-row input {
  height: 38px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 0 6px;
  font-size: 18px;
}
.split-order-no {
  height: 38px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 0 6px;
  font-size: 18px;
  line-height: 38px;
  color: #334155;
  background: #f8fafc;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.btn.split-btn {
  min-height: 36px;
  font-size: 18px;
  padding: 0;
  width: 36px;
  color: #fff;
  background: #ef4444;
  border-color: #dc2626;
}
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
}
.detail-main-left {
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  display: flex;
  align-items: baseline;
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
.detail-shipto {
  margin-left: 10px;
  flex-shrink: 0;
  font-size: 17px;
  color: #1e3a8a;
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
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    align-items: flex-end;
  }
  .field {
    min-width: 0;
    font-size: 13px;
  }
  .field input,
  .field select {
    min-width: 0;
    height: 36px;
    font-size: 14px;
    padding-left: 0;
    padding-right: 0;
  }
  .field input[type="date"] {
    width: 107px;
  }
  .field select {
    width: 80px;
  }
  .toolbar .btn {
    min-height: 0;
    height: 36px;
    padding-top: 0;
    padding-bottom: 0;
    font-size: 14px;
  }
  .detail-list {
    overflow-x: auto;
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
    font-size: 15px;
  }
  .product-name {
    font-size: 12px;
  }
  .detail-shipto {
    font-size: 12px;
  }
  .detail-qty {
    font-size: 18px;
  }
  .actual-input-wrap input {
    height: 32px;
    font-size: 16px;
    padding: 0 4px;
  }
  .actual-readonly {
    min-height: 32px;
    font-size: 18px;
    padding: 2px 4px;
  }
  .split-head {
    font-size: 11px;
  }
  .split-row input {
    height: 32px;
    font-size: 14px;
  }
  .split-order-no {
    height: 32px;
    font-size: 14px;
    line-height: 32px;
  }
  .split-btn,
  .split-add,
  .split-save {
    min-height: 32px;
    font-size: 14px;
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
    min-height: 36px;
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
  .split-head,
  .split-row {
    grid-template-columns: 1fr 70px 105px 28px;
  }
  .split-row input[type="date"] {
    width: 110px;
    padding-left: 0;
    padding-right: 0;
  }
}
</style>
