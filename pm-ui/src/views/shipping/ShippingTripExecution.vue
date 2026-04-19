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
      <div class="chip">総便数: {{ summary.total }}</div>
      <div class="chip">未着手: {{ summary.planned }}</div>
      <div class="chip">積込完了: {{ summary.loading }}</div>
      <div class="chip">出発済: {{ summary.departed }}</div>
    </div>

    <div v-if="loading" class="loading">読み込み中...</div>
    <div v-else-if="!trips.length" class="empty">対象便がありません。</div>

    <div v-else class="trip-list">
      <section v-for="trip in trips" :key="trip.id" class="trip-card">
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
            <span>数量</span>
          </div>
          <div v-for="row in trip.details" :key="row.allocation_id" class="detail-row">
            <div class="detail-main">
              <p class="product-code">{{ row.product_code }}</p>
              <p class="product-name">{{ row.product_name }}</p>
            </div>
            <div class="detail-qty">{{ row.qty }}</div>
          </div>
          <div v-if="!trip.details.length" class="no-detail">明細なし</div>
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
import { onMounted, ref } from 'vue'
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
const loading = ref(false)
const updatingTripId = ref(null)
const summary = ref({ total: 0, planned: 0, loading: 0, departed: 0, closed: 0 })

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

const canMarkLoading = (trip) => ['PLANNED', 'LOADING'].includes(trip?.status)
const canMarkDeparted = (trip) => ['PLANNED', 'LOADING'].includes(trip?.status)
const canReopen = (trip) => ['LOADING', 'DEPARTED'].includes(trip?.status)

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
  } catch (error) {
    const msg = error?.response?.data?.detail || '便データの取得に失敗しました。'
    alert(msg)
  } finally {
    loading.value = false
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
  grid-template-columns: 1fr 72px;
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
.no-detail {
  text-align: center;
  color: #64748b;
  padding: 10px;
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
