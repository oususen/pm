<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">タスク受信箱</h1>
      <div class="page-actions">
        <button class="btn-primary" @click="fetchTasks" :disabled="loading">
          {{ loading ? '更新中...' : '更新' }}
        </button>
      </div>
    </div>

    <div class="page-content">
      <div class="filter-bar">
        <div class="filter-field">
          <label>状態</label>
          <select v-model="filters.status">
            <option value="">すべて</option>
            <option value="PENDING">未対応</option>
            <option value="DONE">完了</option>
            <option value="SKIPPED">スキップ</option>
          </select>
        </div>
        <div class="filter-field">
          <label>タスク種別</label>
          <select v-model="filters.task_type">
            <option value="">すべて</option>
            <option value="CREATE_PROPOSAL">発注提案書作成</option>
            <option value="CREATE_ORDER_PDF">注文書作成</option>
            <option value="APPROVE_L2">班長承認</option>
            <option value="APPROVE_L3">係長承認</option>
            <option value="APPROVE_L4">事業部長承認</option>
            <option value="SEND_TO_SUPPLIER">購入先送信</option>
          </select>
        </div>
        <div class="filter-actions">
          <button class="btn-primary" @click="fetchTasks">検索</button>
          <button class="btn-secondary" @click="resetFilters">リセット</button>
        </div>
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th>業務</th>
            <th>タスク種別</th>
            <th>状態</th>
            <th>注文書番号</th>
            <th>仕入先</th>
            <th>期限</th>
            <th>作成日時</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="`purchase-${row.id}`">
            <td>購買</td>
            <td>{{ taskTypeLabel(row.task_type) }}</td>
            <td>{{ statusLabel(row.status) }}</td>
            <td>{{ row.proposal_no }}</td>
            <td>{{ row.supplier_code }} - {{ row.supplier_name }}</td>
            <td>{{ row.due_date || '-' }}</td>
            <td>{{ formatDateTime(row.created_at) }}</td>
            <td>
              <button class="btn-sm" @click="openPurchaseProposal(row.proposal)">{{ actionLabel(row) }}</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="!rows.length && !loading" class="no-data">タスクはありません</div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import api from "@/api/client"

const router = useRouter()
const loading = ref(false)
const rows = ref([])
const filters = ref({
  status: "PENDING",
  task_type: "",
})

const taskTypeMap = {
  CREATE_PROPOSAL: "発注提案書作成",
  CREATE_ORDER_PDF: "注文書作成",
  APPROVE_L2: "班長承認",
  APPROVE_L3: "係長承認",
  APPROVE_L4: "事業部長承認",
  SEND_TO_SUPPLIER: "購入先送信",
}

const statusMap = {
  PENDING: "未対応",
  DONE: "完了",
  SKIPPED: "スキップ",
}

const taskTypeLabel = (value) => taskTypeMap[value] || value
const statusLabel = (value) => statusMap[value] || value
const purchaseTaskTypes = new Set([
  'CREATE_PROPOSAL',
  'CREATE_ORDER_PDF',
  'APPROVE_L2',
  'APPROVE_L3',
  'APPROVE_L4',
  'SEND_TO_SUPPLIER',
])
const actionLabel = (row) => (purchaseTaskTypes.has(String(row?.task_type || '')) ? '注文書へ' : '提案書へ')

const formatDateTime = (value) => {
  if (!value) return "-"
  const dt = new Date(value)
  if (Number.isNaN(dt.getTime())) return value
  return dt.toLocaleString("ja-JP")
}

const fetchTasks = async () => {
  loading.value = true
  try {
    const params = { assigned_to_me: true }
    if (filters.value.status) params.status = filters.value.status
    if (filters.value.task_type) params.task_type = filters.value.task_type
    const response = await api.purchaseOrderProposals.listTasks(params)
    rows.value = response.data || []
  } finally {
    loading.value = false
  }
}

const resetFilters = async () => {
  filters.value = {
    status: "PENDING",
    task_type: "",
  }
  await fetchTasks()
}

const openPurchaseProposal = (proposalId) => {
  router.push(`/purchase/order-proposals/${proposalId}`)
}

onMounted(async () => {
  await fetchTasks()
})
</script>

<style scoped>
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}

.filter-field {
  display: flex;
  flex-direction: column;
  min-width: 200px;
}

.filter-actions {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}
</style>
