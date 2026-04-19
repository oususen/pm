<template>
  <div class="trip-execution-page">
    <div class="toolbar">
      <label class="field">
        <span>出発日</span>
        <input v-model="departureDate" type="date" />
      </label>
      <label class="field">
        <span>業務区分</span>
        <select v-model="businessType">
          <option value="">すべて</option>
          <option v-for="item in businessTypes" :key="item" :value="item">{{ businessTypeLabel(item) }}</option>
        </select>
      </label>
      <button class="btn" :disabled="loading" @click="loadTrips">表示</button>
    </div>

    <div class="summary">
      <button class="chip chip-button" :class="{ active: !statusFilter }" @click="setStatusFilter('')">総便数: {{ summary.total }}</button>
      <button class="chip chip-button" :class="{ active: statusFilter === 'PLANNED' }" @click="setStatusFilter('PLANNED')">未着手: {{ summary.planned }}</button>
      <button class="chip chip-button" :class="{ active: statusFilter === 'LOADING' }" @click="setStatusFilter('LOADING')">積込完了: {{ summary.loading }}</button>
      <button class="chip chip-button" :class="{ active: statusFilter === 'DEPARTED' }" @click="setStatusFilter('DEPARTED')">出発済: {{ summary.departed }}</button>
      <button class="chip chip-button" :class="{ active: statusFilter === 'CLOSED' }" @click="setStatusFilter('CLOSED')">実績入力完了: {{ summary.closed }}</button>
    </div>

    <div v-if="loading" class="loading">読み込み中...</div>
    <div v-else-if="!visibleTrips.length" class="empty">対象便がありません。</div>

    <div v-else class="trip-list">
      <section v-for="trip in visibleTrips" :key="trip.id" class="trip-card">
        <header class="trip-head">
          <div class="title-block">
            <h3>{{ trip.trip_code || trip.trip_ref }}</h3>
            <p>
              <span>出発時刻: {{ trip.departure_time_plan || '-' }}</span>
              <span class="dot">|</span>
              <span>納入場: {{ trip.ship_to_code || '-' }}</span>
            </p>
          </div>
          <div class="status-block">
            <span class="status" :class="`status-${String(trip.status || '').toLowerCase()}`">
              {{ statusLabel(trip.status) }}
            </span>
            <small v-if="trip.departure_time_actual">実出発: {{ trip.departure_time_actual }}</small>
          </div>
        </header>

        <div class="detail-list">
          <div class="detail-head">
            <span>品番 / 品名</span>
            <span>計画</span>
            <span>実績入力</span>
          </div>
          <div v-for="row in trip.details" :key="row.allocation_id" class="detail-row">
            <div class="detail-main">
              <p class="product-code">{{ row.product_code }}</p>
              <p class="product-name">{{ row.product_name }}</p>
            </div>
            <div class="detail-qty">{{ row.qty }}</div>
            <div class="actual-input-wrap">
              <input
                :value="actualQtyValue(trip.id, row.allocation_id, row.qty)"
                type="number"
                step="1"
                min="0"
                :disabled="!canRegisterActual(trip)"
                @input="setActualQty(trip.id, row.allocation_id, $event.target.value)"
              />
            </div>
          </div>
          <div v-if="!trip.details.length" class="no-detail">明細なし</div>
        </div>

        <div class="actual-row">
          <label class="field inline-field">
            <span>実績日</span>
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
            実績登録
          </button>
        </div>

        <div class="actions">
          <button
            class="btn complete"
            :disabled="updatingTripId === trip.id || !canMarkLoading(trip)"
            @click="updateTripStatus(trip, 'mark_loading')"
          >
            積込完了
          </button>
          <button
            class="btn depart"
            :disabled="updatingTripId === trip.id || !canMarkDeparted(trip)"
            @click="updateTripStatus(trip, 'mark_departed')"
          >
            出発
          </button>
          <button
            class="btn reopen"
            :disabled="updatingTripId === trip.id || !canReopen(trip)"
            @click="updateTripStatus(trip, 'reopen')"
          >
            差戻し
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'

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
const actualQtyMap = ref({})
const actualDateMap = ref({})
const statusFilter = ref('')
const loading = ref(false)
const updatingTripId = ref(null)
const summary = ref({ total: 0, planned: 0, loading: 0, departed: 0, closed: 0 })

const visibleTrips = computed(() => {
  if (!statusFilter.value) return trips.value
  return (trips.value || []).filter((trip) => trip.status === statusFilter.value)
})

const statusLabel = (status) => {
  if (status === 'PLANNED') return '未着手'
  if (status === 'LOADING') return '積込完了'
  if (status === 'DEPARTED') return '出発済'
  if (status === 'CLOSED') return '完了'
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

const canMarkLoading = (trip) => trip?.status === 'PLANNED'
const canMarkDeparted = (trip) => ['PLANNED', 'LOADING'].includes(trip?.status)
const canReopen = (trip) => ['LOADING', 'DEPARTED', 'CLOSED'].includes(trip?.status)
const canRegisterActual = (trip) => trip?.status === 'DEPARTED'

const parseQty = (value) => {
  const num = Number(String(value ?? '').replace(/,/g, ''))
  if (!Number.isFinite(num) || num <= 0) return 0
  return Math.floor(num)
}

const initActualInputState = (tripList) => {
  const nextQtyMap = {}
  const nextDateMap = {}
  ;(tripList || []).forEach((trip) => {
    nextDateMap[trip.id] = actualDateMap.value[trip.id] || trip.departure_date
    const byAlloc = {}
    ;(trip.details || []).forEach((row) => {
      byAlloc[row.allocation_id] = actualQtyMap.value[trip.id]?.[row.allocation_id] ?? String(parseQty(row.qty))
    })
    nextQtyMap[trip.id] = byAlloc
  })
  actualQtyMap.value = nextQtyMap
  actualDateMap.value = nextDateMap
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

const loadTrips = async () => {
  loading.value = true
  try {
    const res = await api.shippingTrips.execution({
      departure_date: departureDate.value,
      business_type: businessType.value || undefined,
    })
    const data = res.data || {}
    businessTypes.value = Array.isArray(data.business_types) ? data.business_types : []
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

const registerActual = async (trip) => {
  const shipmentDate = actualDateValue(trip.id, trip.departure_date)
  if (!shipmentDate) {
    alert('実績日を入力してください。')
    return
  }
  const actuals = (trip.details || []).map((row) => ({
    allocation_id: row.allocation_id,
    quantity: parseQty(actualQtyValue(trip.id, row.allocation_id, row.qty)),
  }))
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
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 760px;
  margin: 0 auto;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: flex-end;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}
.field input,
.field select {
  min-width: 160px;
  height: 32px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 8px;
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
  padding: 4px 10px;
  font-size: 12px;
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
  gap: 10px;
}
.trip-card {
  background: #fff;
  border: 1px solid #dbe2ee;
  border-radius: 10px;
  padding: 10px;
}
.trip-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: flex-start;
  margin-bottom: 8px;
}
.title-block h3 {
  margin: 0;
  font-size: 20px;
}
.title-block p {
  margin: 2px 0 0;
  font-size: 12px;
  color: #475569;
}
.dot {
  margin: 0 6px;
}
.status-block {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}
.status {
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 12px;
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
  border-radius: 8px;
  overflow: hidden;
}
.detail-head,
.detail-row {
  display: grid;
  grid-template-columns: 1fr 72px 110px;
  gap: 8px;
  align-items: center;
  padding: 8px 10px;
}
.detail-head {
  background: #f8fafc;
  font-size: 12px;
  font-weight: 700;
}
.detail-row {
  border-top: 1px solid #e2e8f0;
}
.detail-main {
  min-width: 0;
}
.product-code,
.product-name {
  margin: 0;
  line-height: 1.25;
}
.product-code {
  font-size: 17px;
  font-weight: 700;
}
.product-name {
  margin-top: 2px;
  font-size: 13px;
  color: #475569;
}
.detail-qty {
  text-align: right;
  font-size: 22px;
  font-weight: 700;
}
.actual-input-wrap input {
  width: 100%;
  height: 36px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 8px;
  font-size: 18px;
  text-align: right;
}
.no-detail {
  text-align: center;
  color: #64748b;
  padding: 10px;
}
.actual-row {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: flex-end;
}
.inline-field {
  min-width: 180px;
}
.actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.btn {
  min-height: 42px;
  border: 1px solid #cbd5e1;
  background: #fff;
  border-radius: 6px;
  padding: 0 14px;
  cursor: pointer;
  font-size: 16px;
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
  padding: 20px 0;
}
@media (max-width: 640px) {
  .trip-execution-page {
    padding: 10px;
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
    flex-direction: column;
    gap: 6px;
  }
  .status-block {
    width: 100%;
    align-items: flex-start;
  }
  .actions {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
  }
  .detail-head,
  .detail-row {
    grid-template-columns: 1fr 58px 88px;
    gap: 6px;
    padding: 7px 8px;
  }
  .product-code {
    font-size: 15px;
  }
  .product-name {
    font-size: 12px;
  }
  .detail-qty {
    font-size: 18px;
  }
  .actual-input-wrap input {
    height: 34px;
    font-size: 16px;
    padding: 0 6px;
  }
  .actual-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
  .inline-field {
    min-width: 0;
  }
  .btn {
    min-height: 44px;
    font-size: 15px;
    padding: 0 8px;
  }
  .summary {
    gap: 4px;
  }
  .chip {
    font-size: 11px;
    padding: 3px 8px;
  }
}
</style>
