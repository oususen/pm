<template>
  <div class="page-container">
    <h2 class="page-title">FB外作進捗管理</h2>

    <div class="filter-row">
      <select v-model="filterStatus" @change="fetchOrders" class="filter-select">
        <option value="">全ステータス</option>
        <option value="SPLIT_REGISTERED">分割計画登録済</option>
        <option value="IN_PROGRESS">加工中</option>
        <option value="COMPLETED">完了</option>
      </select>
      <button class="btn-month" @click="shiftMonth(-1)">◀ 前月</button>
      <label class="filter-label">塗装日:</label>
      <input type="date" v-model="paintingFrom" @change="fetchOrders" class="filter-date" />
      <span class="filter-sep">〜</span>
      <input type="date" v-model="paintingTo" @change="fetchOrders" class="filter-date" />
      <button class="btn-month" @click="shiftMonth(1)">次月 ▶</button>
    </div>

    <table class="data-table" v-if="orders.length">
      <thead>
        <tr>
          <th>案件番号</th>
          <th>品目名称</th>
          <th>数量</th>
          <th>塗装日</th>
          <th>ステータス</th>
          <th>支給進捗</th>
          <th>加工進捗</th>
          <th>出荷進捗</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="o in orders" :key="o.id">
          <td class="case-no">{{ o.case_no }}</td>
          <td>{{ o.item_name }}</td>
          <td class="text-right">{{ o.order_qty }}</td>
          <td>{{ o.painting_date }}</td>
          <td><span class="status-badge" :class="'st-' + o.status">{{ statusLabel(o.status) }}</span></td>
          <td>
            <div class="progress-bar-container" v-if="o.splits && o.splits.length">
              <div class="progress-bar bar-supply" :style="{ width: supplyPct(o) + '%' }"></div>
              <span class="progress-text">{{ supplyPct(o) }}%</span>
            </div>
            <span v-else>-</span>
          </td>
          <td>
            <div class="progress-bar-container" v-if="o.splits && o.splits.length">
              <div class="progress-bar bar-process" :style="{ width: processPct(o) + '%' }"></div>
              <span class="progress-text">{{ processPct(o) }}%</span>
            </div>
            <span v-else>-</span>
          </td>
          <td>
            <div class="progress-bar-container" v-if="o.splits && o.splits.length">
              <div class="progress-bar bar-ship" :style="{ width: shipPct(o) + '%' }"></div>
              <span class="progress-text">{{ shipPct(o) }}%</span>
            </div>
            <span v-else>-</span>
          </td>
          <td>
            <button v-if="o.status !== 'COMPLETED'" class="btn-sm" @click="openSplits(o)">更新</button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- 分割詳細モーダル -->
    <div v-if="editingOrder" class="modal-overlay" @click.self="editingOrder = null">
      <div class="modal-content">
        <h3>{{ editingOrder.case_no }} - 進捗更新</h3>
        <table class="data-table">
          <thead><tr>
            <th>#</th><th>加工日</th><th>数量</th>
            <th>材料支給</th><th>加工完了(受入)</th><th>出荷済</th>
          </tr></thead>
          <tbody>
            <tr v-for="s in editingOrder.splits" :key="s.id">
              <td>{{ s.sequence }}</td>
              <td>{{ s.process_date }}</td>
              <td class="text-right">{{ s.qty }}</td>
              <td class="text-center">
                <input type="checkbox"
                  :checked="s.material_supplied || s.auto_material_supplied"
                  :disabled="s.auto_material_supplied"
                  @change="onToggle(s, 'material_supplied', $event)" />
                <span v-if="s.auto_material_supplied" class="auto-tag">自動</span>
              </td>
              <td class="text-center">
                <input type="checkbox"
                  :checked="s.process_completed || s.auto_process_completed"
                  :disabled="s.auto_process_completed"
                  @change="onToggle(s, 'process_completed', $event)" />
                <span v-if="s.auto_process_completed" class="auto-tag">{{ s.delivered_qty }}/{{ s.qty }}</span>
                <span v-else-if="s.delivered_qty > 0" class="partial-tag">{{ s.delivered_qty }}/{{ s.qty }}</span>
              </td>
              <td class="text-center">
                <input type="checkbox"
                  :checked="s.shipped || s.auto_shipped"
                  :disabled="s.auto_shipped"
                  @change="onToggle(s, 'shipped', $event)" />
                <span v-if="s.auto_shipped" class="auto-tag">{{ s.shipped_qty }}/{{ s.qty }}</span>
                <span v-else-if="s.shipped_qty > 0" class="partial-tag">{{ s.shipped_qty }}/{{ s.qty }}</span>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="modal-actions">
          <button class="btn-primary" @click="editingOrder = null">閉じる</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api/client'

const orders = ref([])
const filterStatus = ref('')
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
  fetchOrders()
}
const editingOrder = ref(null)

const STATUS_MAP = { IMPORTED: '取込済', SENT_TO_SUB: '展開送付済', SPLIT_REGISTERED: '分割登録済', IN_PROGRESS: '加工中', COMPLETED: '完了' }
function statusLabel(s) { return STATUS_MAP[s] || s }

function supplyPct(order) {
  if (!order.splits || !order.splits.length) return 0
  const done = order.splits.filter(s => s.material_supplied || s.auto_material_supplied).length
  return Math.round((done / order.splits.length) * 100)
}

function processPct(order) {
  if (!order.splits || !order.splits.length) return 0
  const done = order.splits.filter(s => s.process_completed || s.auto_process_completed).length
  return Math.round((done / order.splits.length) * 100)
}

function shipPct(order) {
  if (!order.splits || !order.splits.length) return 0
  const done = order.splits.filter(s => s.shipped || s.auto_shipped).length
  return Math.round((done / order.splits.length) * 100)
}

async function fetchOrders() {
  try {
    const params = {}
    if (filterStatus.value) params.status = filterStatus.value
    else params.status__in = 'SPLIT_REGISTERED,IN_PROGRESS,COMPLETED'
    if (paintingFrom.value) params.painting_date_from = paintingFrom.value
    if (paintingTo.value) params.painting_date_to = paintingTo.value
    const res = await api.outsource.getOrders(params)
    const list = res.data.results || res.data
    // 各案件の詳細（splits含む）を取得
    orders.value = await Promise.all(list.map(async (o) => {
      const detail = await api.outsource.getOrder(o.id)
      return detail.data
    }))
  } catch (err) {
    console.error(err)
  }
}

function openSplits(order) {
  editingOrder.value = order
}

function onToggle(split, field, event) {
  split[field] = event.target.checked
  updateSplit(split)
}

async function updateSplit(split) {
  try {
    await api.outsource.updateSplit(split.id, {
      order: split.order || editingOrder.value.id,
      sequence: split.sequence,
      process_date: split.process_date,
      qty: split.qty,
      material_supplied: split.material_supplied,
      process_completed: split.process_completed,
      shipped: split.shipped,
    })
    await fetchOrders()
    if (editingOrder.value) {
      const updated = orders.value.find(o => o.id === editingOrder.value.id)
      if (updated) editingOrder.value = updated
    }
  } catch (err) {
    console.error(err)
  }
}

onMounted(fetchOrders)
</script>

<style scoped>
.page-container { padding: 16px; }
.page-title { font-size: 18px; margin-bottom: 12px; }
.filter-row { display: flex; gap: 8px; margin-bottom: 12px; }
.filter-select { padding: 4px 8px; font-size: 13px; border: 1px solid #ccc; border-radius: 4px; }
.filter-label { font-size: 12px; color: #555; }
.filter-date { padding: 3px 6px; font-size: 12px; border: 1px solid #ccc; border-radius: 4px; width: 130px; }
.filter-sep { font-size: 12px; color: #888; }
.btn-month { padding: 3px 8px; font-size: 11px; border: 1px solid #ccc; border-radius: 4px; background: #fff; cursor: pointer; }
.btn-month:hover { background: #e3f2fd; }

.data-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.data-table th, .data-table td { border: 1px solid #ddd; padding: 4px 8px; }
.data-table th { background: #f5f5f5; }
.text-right { text-align: right; }
.text-center { text-align: center; }
.case-no { font-family: monospace; font-size: 11px; }

.status-badge { padding: 2px 8px; border-radius: 10px; font-size: 11px; }
.st-SPLIT_REGISTERED { background: #e8f5e9; color: #2e7d32; }
.st-IN_PROGRESS { background: #fce4ec; color: #c62828; }
.st-COMPLETED { background: #f5f5f5; color: #616161; }

.progress-bar-container { position: relative; width: 80px; height: 16px; background: #eee; border-radius: 8px; display: inline-block; }
.progress-bar { height: 100%; border-radius: 8px; transition: width 0.3s; }
.bar-supply { background: #42a5f5; }
.bar-process { background: #66bb6a; }
.bar-ship { background: #ffa726; }
.progress-text { position: absolute; top: 0; left: 0; width: 100%; text-align: center; font-size: 10px; line-height: 16px; }

.auto-tag { font-size: 9px; color: #2e7d32; background: #e8f5e9; padding: 0 4px; border-radius: 3px; margin-left: 2px; }
.partial-tag { font-size: 9px; color: #e65100; background: #fff3e0; padding: 0 4px; border-radius: 3px; margin-left: 2px; }
.btn-sm { padding: 2px 8px; background: #e3f2fd; border: 1px solid #90caf9; border-radius: 4px; cursor: pointer; font-size: 11px; }

.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-content { background: #fff; padding: 20px; border-radius: 8px; max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto; }
.modal-content h3 { font-size: 15px; margin-bottom: 12px; }
.modal-actions { margin-top: 12px; text-align: right; }
.btn-primary { padding: 6px 16px; background: #1976d2; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
</style>
