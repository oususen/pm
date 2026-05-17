<template>
  <div class="page-container">
    <h2 class="page-title">納入・出荷管理</h2>

    <div class="toolbar">
      <div class="tab-btns">
        <button :class="{ active: tab === 'delivery' }" @click="tab = 'delivery'">外作先納入</button>
        <button :class="{ active: tab === 'shipment' }" @click="tab = 'shipment'">顧客出荷</button>
      </div>
      <label class="filter-label">塗装日:</label>
      <input type="date" v-model="paintingFrom" @change="fetchData" class="filter-date" />
      <span class="filter-sep">〜</span>
      <input type="date" v-model="paintingTo" @change="fetchData" class="filter-date" />
    </div>

    <!-- 外作先納入タブ -->
    <div v-if="tab === 'delivery'">
      <div class="form-section">
        <h3 class="section-title">受入登録</h3>
        <div class="form-row">
          <select v-model="deliveryForm.split" class="form-input">
            <option value="">分割を選択</option>
            <option v-for="s in availableSplits" :key="s.id" :value="s.id">
              {{ s.case_no }} #{{ s.sequence }} ({{ s.process_date }} / {{ s.qty }}個)
            </option>
          </select>
          <input type="date" v-model="deliveryForm.delivery_date" class="form-input form-date" />
          <input type="number" v-model.number="deliveryForm.qty" placeholder="数量" class="form-input form-qty" />
          <input type="text" v-model="deliveryForm.inspector" placeholder="検収者" class="form-input form-name" />
          <button class="btn-primary" @click="submitDelivery" :disabled="!canSubmitDelivery">登録</button>
        </div>
      </div>

      <table class="data-table" v-if="deliveries.length">
        <thead><tr><th>納入日</th><th>案件番号</th><th>品目</th><th>#</th><th>数量</th><th>検収者</th><th>備考</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="d in deliveries" :key="d.id">
            <td>{{ d.delivery_date }}</td>
            <td class="case-no">{{ d.case_no }}</td>
            <td>{{ d.item_name }}</td>
            <td class="text-center">{{ d.sequence }}</td>
            <td class="text-right">{{ d.qty }}</td>
            <td>{{ d.inspector }}</td>
            <td>{{ d.notes || '-' }}</td>
            <td><button class="btn-del" @click="deleteDelivery(d.id)">削除</button></td>
          </tr>
        </tbody>
      </table>
      <div v-else-if="!loading" class="empty-state">納入記録がありません</div>
    </div>

    <!-- 顧客出荷タブ -->
    <div v-if="tab === 'shipment'">
      <div class="form-section">
        <h3 class="section-title">出荷登録</h3>
        <div class="form-row">
          <select v-model="shipmentForm.split" class="form-input">
            <option value="">分割を選択</option>
            <option v-for="s in availableSplits" :key="s.id" :value="s.id">
              {{ s.case_no }} #{{ s.sequence }} ({{ s.process_date }} / {{ s.qty }}個)
            </option>
          </select>
          <input type="date" v-model="shipmentForm.shipment_date" class="form-input form-date" />
          <input type="number" v-model.number="shipmentForm.qty" placeholder="数量" class="form-input form-qty" />
          <input type="text" v-model="shipmentForm.person" placeholder="担当者" class="form-input form-name" />
          <button class="btn-primary" @click="submitShipment" :disabled="!canSubmitShipment">登録</button>
        </div>
      </div>

      <table class="data-table" v-if="shipments.length">
        <thead><tr><th>出荷日</th><th>案件番号</th><th>品目</th><th>#</th><th>数量</th><th>担当者</th><th>備考</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="s in shipments" :key="s.id">
            <td>{{ s.shipment_date }}</td>
            <td class="case-no">{{ s.case_no }}</td>
            <td>{{ s.item_name }}</td>
            <td class="text-center">{{ s.sequence }}</td>
            <td class="text-right">{{ s.qty }}</td>
            <td>{{ s.person }}</td>
            <td>{{ s.notes || '-' }}</td>
            <td><button class="btn-del" @click="deleteShipment(s.id)">削除</button></td>
          </tr>
        </tbody>
      </table>
      <div v-else-if="!loading" class="empty-state">出荷記録がありません</div>
    </div>

    <div v-if="loading" class="loading">読み込み中...</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '@/api/client'

const tab = ref('delivery')
const loading = ref(false)
const paintingFrom = ref('')
const paintingTo = ref('')

const deliveries = ref([])
const shipments = ref([])
const splits = ref([])

const today = new Date().toISOString().slice(0, 10)

const deliveryForm = ref({ split: '', delivery_date: today, qty: null, inspector: '' })
const shipmentForm = ref({ split: '', shipment_date: today, qty: null, person: '' })

const canSubmitDelivery = computed(() => deliveryForm.value.split && deliveryForm.value.delivery_date && deliveryForm.value.qty > 0 && deliveryForm.value.inspector)
const canSubmitShipment = computed(() => shipmentForm.value.split && shipmentForm.value.shipment_date && shipmentForm.value.qty > 0 && shipmentForm.value.person)

const availableSplits = computed(() => {
  return splits.value.map(s => ({
    id: s.id,
    case_no: s.case_no || s.order_case_no,
    sequence: s.sequence,
    process_date: s.process_date,
    qty: s.qty,
  }))
})

async function fetchData() {
  loading.value = true
  try {
    const params = {}
    if (paintingFrom.value) params.painting_date_from = paintingFrom.value
    if (paintingTo.value) params.painting_date_to = paintingTo.value

    const [delRes, shipRes, splitRes] = await Promise.all([
      api.outsource.getDeliveries(params),
      api.outsource.getShipments(params),
      fetchSplits(),
    ])
    deliveries.value = delRes.data.results || delRes.data
    shipments.value = shipRes.data.results || shipRes.data
  } finally { loading.value = false }
}

async function fetchSplits() {
  const params = { ordering: 'order__painting_date' }
  if (paintingFrom.value) params.painting_date_from = paintingFrom.value
  if (paintingTo.value) params.painting_date_to = paintingTo.value
  const res = await api.outsource.getSplits(params)
  const list = res.data.results || res.data
  // getSplitsはorder情報を含まないので、ordersから補完
  const orderRes = await api.outsource.getOrders({
    ...(paintingFrom.value ? { painting_date_from: paintingFrom.value } : {}),
    ...(paintingTo.value ? { painting_date_to: paintingTo.value } : {}),
  })
  const orders = orderRes.data.results || orderRes.data
  const orderMap = {}
  for (const o of orders) orderMap[o.id] = o
  splits.value = list.map(s => ({ ...s, case_no: orderMap[s.order]?.case_no || '', order_case_no: orderMap[s.order]?.case_no || '' }))
}

async function submitDelivery() {
  try {
    await api.outsource.createDelivery(deliveryForm.value)
    deliveryForm.value = { split: '', delivery_date: today, qty: null, inspector: '' }
    fetchData()
  } catch (err) { alert(err.response?.data?.detail || '登録に失敗しました') }
}

async function submitShipment() {
  try {
    await api.outsource.createShipment(shipmentForm.value)
    shipmentForm.value = { split: '', shipment_date: today, qty: null, person: '' }
    fetchData()
  } catch (err) { alert(err.response?.data?.detail || '登録に失敗しました') }
}

async function deleteDelivery(id) {
  if (!confirm('削除しますか？')) return
  await api.outsource.deleteDelivery(id)
  fetchData()
}

async function deleteShipment(id) {
  if (!confirm('削除しますか？')) return
  await api.outsource.deleteShipment(id)
  fetchData()
}

watch(tab, () => fetchData())
onMounted(fetchData)
</script>

<style scoped>
.page-container { padding: 16px; }
.page-title { font-size: 18px; margin-bottom: 12px; }

.toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
.tab-btns { display: flex; gap: 0; }
.tab-btns button { padding: 5px 14px; font-size: 13px; border: 1px solid #ccc; background: #f5f5f5; cursor: pointer; }
.tab-btns button:first-child { border-radius: 4px 0 0 4px; }
.tab-btns button:last-child { border-radius: 0 4px 4px 0; }
.tab-btns button.active { background: #1976d2; color: #fff; border-color: #1976d2; }
.filter-label { font-size: 12px; color: #555; margin-left: 12px; }
.filter-date { padding: 3px 6px; font-size: 12px; border: 1px solid #ccc; border-radius: 4px; width: 130px; }
.filter-sep { font-size: 12px; color: #888; }

.form-section { background: #f9f9f9; padding: 10px 12px; border-radius: 6px; margin-bottom: 12px; }
.section-title { font-size: 13px; margin-bottom: 8px; }
.form-row { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.form-input { padding: 4px 8px; font-size: 12px; border: 1px solid #ccc; border-radius: 4px; }
.form-input:first-child { min-width: 280px; }
.form-date { width: 130px; }
.form-qty { width: 70px; }
.form-name { width: 100px; }
.btn-primary { padding: 5px 14px; background: #1976d2; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.data-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.data-table th, .data-table td { border: 1px solid #ddd; padding: 3px 8px; white-space: nowrap; }
.data-table th { background: #f5f5f5; }
.text-right { text-align: right; }
.text-center { text-align: center; }
.case-no { font-family: monospace; font-size: 11px; }

.btn-del { padding: 2px 8px; background: #fff; border: 1px solid #e57373; border-radius: 4px; color: #c62828; cursor: pointer; font-size: 11px; }

.empty-state, .loading { text-align: center; padding: 32px; color: #999; font-size: 14px; }
</style>
