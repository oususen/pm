<template>
  <div class="page-container">
    <h2 class="page-title">納入・出荷管理</h2>

    <div class="toolbar">
      <div class="tab-btns">
        <button :class="{ active: tab === 'delivery' }" @click="tab = 'delivery'">外作先納入（検収）</button>
        <button :class="{ active: tab === 'shipment' }" @click="tab = 'shipment'">顧客出荷</button>
      </div>
      <button class="btn-month" @click="shiftMonth(-1)">◀ 前月</button>
      <label class="filter-label">塗装日:</label>
      <input type="date" v-model="paintingFrom" @change="fetchData" class="filter-date" />
      <span class="filter-sep">〜</span>
      <input type="date" v-model="paintingTo" @change="fetchData" class="filter-date" />
      <button class="btn-month" @click="shiftMonth(1)">次月 ▶</button>
    </div>

    <!-- 案件別リスト -->
    <div v-for="order in orderList" :key="order.id" class="order-group">
      <div class="order-header clickable" @click="toggleOrder(order.id)">
        <span class="toggle-icon">{{ expandedOrders.has(order.id) ? '▼' : '▶' }}</span>
        <span class="order-case">{{ order.case_no }}</span>
        <span class="order-status" :class="'st-' + order.status">{{ STATUS_MAP[order.status] || order.status }}</span>
        <span class="order-info">{{ order.product_number || '' }} {{ order.item_name }}</span>
        <span class="order-info">塗装日: {{ order.painting_date }}</span>
        <span class="order-qty">{{ order.order_qty }}個</span>
        <span v-if="tab === 'delivery'" class="order-progress" :class="deliveryProgressClass(order)">
          受入: {{ orderDeliveredQty(order) }} / {{ order.order_qty }}
        </span>
        <span v-else class="order-progress" :class="shipmentProgressClass(order)">
          出荷: {{ orderShippedQty(order) }} / {{ order.order_qty }}
        </span>
      </div>

      <div v-if="expandedOrders.has(order.id)" class="order-body">
        <table class="data-table">
          <thead>
            <tr v-if="tab === 'delivery'">
              <th>#</th><th>加工日</th><th>数量</th><th>受入済</th><th>残</th><th>納入日</th><th>数量</th><th>検収者</th><th>操作</th>
            </tr>
            <tr v-else>
              <th>#</th><th>加工日</th><th>数量</th><th>出荷済</th><th>残</th><th>出荷日</th><th>数量</th><th>担当者</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="split in order.splits" :key="split.id">
              <tr>
                <td class="text-center">{{ split.sequence }}</td>
                <td>{{ split.process_date }}</td>
                <td class="text-right">{{ split.qty }}</td>
                <td class="text-right" v-if="tab === 'delivery'">{{ splitDeliveredQty(split) }}</td>
                <td class="text-right" v-else>{{ splitShippedQty(split) }}</td>
                <td class="text-right" :class="{ 'text-danger': splitRemaining(split) > 0 }">
                  {{ splitRemaining(split) }}
                </td>
                <!-- インライン入力 -->
                <td><input type="date" v-model="split._date" class="inline-date" /></td>
                <td><input type="number" v-model.number="split._qty" class="inline-qty" :placeholder="splitRemaining(split)" /></td>
                <td>
                  <input v-if="tab === 'delivery'" type="text" v-model="split._person" placeholder="検収者" class="inline-name" />
                  <input v-else type="text" v-model="split._person" placeholder="担当者" class="inline-name" />
                  <button class="btn-reg" @click="submitInline(order, split)" :disabled="!split._qty || !split._person">登録</button>
                </td>
              </tr>
              <!-- 登録済み明細 -->
              <tr v-for="rec in splitRecords(split)" :key="rec.id" class="record-row">
                <td colspan="5"></td>
                <td>{{ rec.date }}</td>
                <td class="text-right">{{ rec.qty }}</td>
                <td>{{ rec.person }}</td>
                <td><button class="btn-del" @click="deleteRecord(rec)">削除</button></td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="!orderList.length && !loading" class="empty-state">対象案件がありません</div>
    <div v-if="loading" class="loading">読み込み中...</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'

const STATUS_MAP = {
  IMPORTED: '取込済',
  SENT_TO_SUB: '展開送付済',
  SPLIT_REGISTERED: '分割登録済',
  IN_PROGRESS: '加工中',
  COMPLETED: '完了',
}

const tab = ref('delivery')
const loading = ref(false)
function monthRange(d) {
  const y = d.getFullYear(), m = d.getMonth()
  const from = `${y}-${String(m + 1).padStart(2, '0')}-01`
  const to = `${y}-${String(m + 1).padStart(2, '0')}-${String(new Date(y, m + 1, 0).getDate()).padStart(2, '0')}`
  return { from, to }
}
const { from: initFrom, to: initTo } = monthRange(new Date())
const paintingFrom = ref(initFrom)
const paintingTo = ref(initTo)

function shiftMonth(delta) {
  const d = new Date(paintingFrom.value + 'T00:00:00')
  d.setMonth(d.getMonth() + delta)
  const { from, to } = monthRange(d)
  paintingFrom.value = from
  paintingTo.value = to
  fetchData()
}
const expandedOrders = ref(new Set())

const orders = ref([])
const deliveries = ref([])
const shipments = ref([])

const today = new Date().toISOString().slice(0, 10)
const currentUserName = computed(() => {
  const u = authState.user
  if (!u) return ''
  return `${u.last_name || ''} ${u.first_name || ''}`.trim() || u.username || ''
})

function toggleOrder(id) {
  if (expandedOrders.value.has(id)) {
    expandedOrders.value.delete(id)
  } else {
    expandedOrders.value.add(id)
  }
  expandedOrders.value = new Set(expandedOrders.value)
}

const orderList = computed(() => {
  return orders.value.map(o => ({
    ...o,
    splits: (o.splits || []).map(s => {
      const delivered = (deliveryMap.value[s.id] || []).reduce((sum, d) => sum + d.qty, 0)
      const shipped = (shipmentMap.value[s.id] || []).reduce((sum, d) => sum + d.qty, 0)
      const remain = tab.value === 'delivery' ? s.qty - delivered : s.qty - shipped
      return {
        ...s,
        _date: s._date || today,
        _qty: s._qty ?? (remain > 0 ? remain : null),
        _person: s._person || currentUserName.value,
      }
    })
  }))
})

const deliveryMap = computed(() => {
  const map = {}
  for (const d of deliveries.value) {
    if (!map[d.split]) map[d.split] = []
    map[d.split].push(d)
  }
  return map
})

const shipmentMap = computed(() => {
  const map = {}
  for (const s of shipments.value) {
    if (!map[s.split]) map[s.split] = []
    map[s.split].push(s)
  }
  return map
})

function splitDeliveredQty(split) {
  return (deliveryMap.value[split.id] || []).reduce((sum, d) => sum + d.qty, 0)
}

function splitShippedQty(split) {
  return (shipmentMap.value[split.id] || []).reduce((sum, s) => sum + s.qty, 0)
}

function splitRemaining(split) {
  if (tab.value === 'delivery') return split.qty - splitDeliveredQty(split)
  return split.qty - splitShippedQty(split)
}

function orderDeliveredQty(order) {
  return (order.splits || []).reduce((sum, s) => sum + splitDeliveredQty(s), 0)
}

function orderShippedQty(order) {
  return (order.splits || []).reduce((sum, s) => sum + splitShippedQty(s), 0)
}

function deliveryProgressClass(order) {
  const done = orderDeliveredQty(order)
  if (done >= order.order_qty) return 'progress-done'
  if (done > 0) return 'progress-partial'
  return 'progress-none'
}

function shipmentProgressClass(order) {
  const done = orderShippedQty(order)
  if (done >= order.order_qty) return 'progress-done'
  if (done > 0) return 'progress-partial'
  return 'progress-none'
}

function splitRecords(split) {
  if (tab.value === 'delivery') {
    return (deliveryMap.value[split.id] || []).map(d => ({
      id: d.id, type: 'delivery', date: d.delivery_date, qty: d.qty, person: d.inspector,
    }))
  }
  return (shipmentMap.value[split.id] || []).map(s => ({
    id: s.id, type: 'shipment', date: s.shipment_date, qty: s.qty, person: s.person,
  }))
}

async function fetchData() {
  loading.value = true
  try {
    const params = {}
    if (paintingFrom.value) params.painting_date_from = paintingFrom.value
    if (paintingTo.value) params.painting_date_to = paintingTo.value

    const orderParams = { ...params, status__in: 'SPLIT_REGISTERED,IN_PROGRESS,COMPLETED' }
    const [orderRes, delRes, shipRes] = await Promise.all([
      api.outsource.getOrders(orderParams),
      api.outsource.getDeliveries(params),
      api.outsource.getShipments(params),
    ])

    const list = orderRes.data.results || orderRes.data
    const details = await Promise.all(list.map(o => api.outsource.getOrder(o.id)))
    orders.value = details.map(r => r.data)
    deliveries.value = delRes.data.results || delRes.data
    shipments.value = shipRes.data.results || shipRes.data
  } finally { loading.value = false }
}

async function submitInline(order, split) {
  try {
    if (tab.value === 'delivery') {
      await api.outsource.createDelivery({
        split: split.id,
        delivery_date: split._date,
        qty: split._qty,
        inspector: split._person,
      })
    } else {
      await api.outsource.createShipment({
        split: split.id,
        shipment_date: split._date,
        qty: split._qty,
        person: split._person,
      })
    }
    split._qty = null
    split._person = ''
    await fetchData()
  } catch (err) { alert(err.response?.data?.detail || '登録に失敗しました') }
}

async function deleteRecord(rec) {
  if (!confirm('削除しますか？')) return
  if (rec.type === 'delivery') await api.outsource.deleteDelivery(rec.id)
  else await api.outsource.deleteShipment(rec.id)
  await fetchData()
}

watch(tab, () => {})
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
.btn-month { padding: 3px 8px; font-size: 11px; border: 1px solid #ccc; border-radius: 4px; background: #fff; cursor: pointer; }
.btn-month:hover { background: #e3f2fd; }

.order-group { margin-bottom: 8px; }
.order-header {
  display: flex; align-items: center; gap: 10px;
  padding: 6px 12px; background: #f5f5f5; border-radius: 4px; font-size: 12px;
}
.clickable { cursor: pointer; user-select: none; }
.toggle-icon { font-size: 10px; width: 12px; }
.order-case { font-family: monospace; font-size: 11px; font-weight: 600; }
.order-status { padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 600; }
.st-IMPORTED { background: #e3f2fd; color: #1565c0; }
.st-SENT_TO_SUB { background: #f3e5f5; color: #7b1fa2; }
.st-SPLIT_REGISTERED { background: #e8f5e9; color: #2e7d32; }
.st-IN_PROGRESS { background: #fff3e0; color: #e65100; }
.st-COMPLETED { background: #e0e0e0; color: #616161; }
.order-info { color: #555; }
.order-qty { font-weight: 600; }
.order-progress { margin-left: auto; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.progress-done { background: #e8f5e9; color: #2e7d32; }
.progress-partial { background: #fff3e0; color: #e65100; }
.progress-none { background: #f5f5f5; color: #999; }

.order-body { padding: 0 0 8px 0; }

.data-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.data-table th, .data-table td { border: 1px solid #ddd; padding: 3px 6px; white-space: nowrap; }
.data-table th { background: #f5f5f5; }
.text-right { text-align: right; }
.text-center { text-align: center; }
.text-danger { color: #c62828; font-weight: 600; }

.inline-date { width: 120px; padding: 2px 4px; font-size: 11px; border: 1px solid #ccc; border-radius: 3px; }
.inline-qty { width: 55px; padding: 2px 4px; font-size: 11px; border: 1px solid #ccc; border-radius: 3px; text-align: right; }
.inline-name { width: 70px; padding: 2px 4px; font-size: 11px; border: 1px solid #ccc; border-radius: 3px; }
.btn-reg { padding: 2px 8px; background: #1976d2; color: #fff; border: none; border-radius: 3px; cursor: pointer; font-size: 11px; margin-left: 4px; }
.btn-reg:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-del { padding: 1px 6px; background: #fff; border: 1px solid #e57373; border-radius: 3px; color: #c62828; cursor: pointer; font-size: 10px; }

.record-row { background: #fafafa; }
.record-row td { font-size: 11px; color: #666; }

.empty-state, .loading { text-align: center; padding: 32px; color: #999; font-size: 14px; }
</style>
