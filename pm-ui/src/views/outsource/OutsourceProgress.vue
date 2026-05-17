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
      <label class="filter-label">塗装日:</label>
      <input type="date" v-model="paintingFrom" @change="fetchOrders" class="filter-date" />
      <span class="filter-sep">〜</span>
      <input type="date" v-model="paintingTo" @change="fetchOrders" class="filter-date" />
    </div>

    <table class="data-table" v-if="orders.length">
      <thead>
        <tr>
          <th>案件番号</th>
          <th>品目名称</th>
          <th>数量</th>
          <th>塗装日</th>
          <th>ステータス</th>
          <th>分割進捗</th>
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
              <div class="progress-bar" :style="{ width: progressPct(o) + '%' }"></div>
              <span class="progress-text">{{ progressPct(o) }}%</span>
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
          <thead><tr><th>#</th><th>加工日</th><th>数量</th><th>材料支給</th><th>加工完了</th><th>出荷済</th></tr></thead>
          <tbody>
            <tr v-for="s in editingOrder.splits" :key="s.id">
              <td>{{ s.sequence }}</td>
              <td>{{ s.process_date }}</td>
              <td class="text-right">{{ s.qty }}</td>
              <td class="text-center"><input type="checkbox" v-model="s.material_supplied" @change="updateSplit(s)" /></td>
              <td class="text-center"><input type="checkbox" v-model="s.process_completed" @change="updateSplit(s)" /></td>
              <td class="text-center"><input type="checkbox" v-model="s.shipped" @change="updateSplit(s)" /></td>
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
const paintingFrom = ref('')
const paintingTo = ref('')
const editingOrder = ref(null)

const STATUS_MAP = { IMPORTED: '取込済', SENT_TO_SUB: '展開送付済', SPLIT_REGISTERED: '分割登録済', IN_PROGRESS: '加工中', COMPLETED: '完了' }
function statusLabel(s) { return STATUS_MAP[s] || s }

function progressPct(order) {
  if (!order.splits || !order.splits.length) return 0
  const completed = order.splits.filter(s => s.process_completed).length
  return Math.round((completed / order.splits.length) * 100)
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
    // 全分割完了ならステータス更新
    if (editingOrder.value.splits.every(s => s.shipped)) {
      editingOrder.value.status = 'COMPLETED'
    } else if (editingOrder.value.splits.some(s => s.material_supplied || s.process_completed)) {
      editingOrder.value.status = 'IN_PROGRESS'
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
.progress-bar { height: 100%; background: #66bb6a; border-radius: 8px; transition: width 0.3s; }
.progress-text { position: absolute; top: 0; left: 0; width: 100%; text-align: center; font-size: 10px; line-height: 16px; }

.btn-sm { padding: 2px 8px; background: #e3f2fd; border: 1px solid #90caf9; border-radius: 4px; cursor: pointer; font-size: 11px; }

.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-content { background: #fff; padding: 20px; border-radius: 8px; max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto; }
.modal-content h3 { font-size: 15px; margin-bottom: 12px; }
.modal-actions { margin-top: 12px; text-align: right; }
.btn-primary { padding: 6px 16px; background: #1976d2; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
</style>
