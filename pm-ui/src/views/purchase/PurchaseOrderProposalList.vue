<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">発注提案書一覧</h1>
      <div class="page-actions">
        <button class="btn-primary" @click="fetchList">更新</button>
        <button class="btn-success" @click="openCreateDialog">新規作成</button>
      </div>
    </div>

    <div class="page-content">
      <div class="filter-bar">
        <div class="filter-field">
          <label>仕入先</label>
          <select v-model="filters.supplier">
            <option value="">すべて</option>
            <option v-for="supplier in suppliers" :key="supplier.id" :value="supplier.id">
              {{ supplier.supplier_code }} - {{ supplier.supplier_name }}
            </option>
          </select>
        </div>
        <div class="filter-field">
          <label>ステータス</label>
          <select v-model="filters.status">
            <option value="">すべて</option>
            <option v-for="item in statusOptions" :key="item.value" :value="item.value">
              {{ item.label }}
            </option>
          </select>
        </div>
        <div class="filter-field">
          <label>発注日From</label>
          <input v-model="filters.order_date_from" type="date" />
        </div>
        <div class="filter-field">
          <label>発注日To</label>
          <input v-model="filters.order_date_to" type="date" />
        </div>
        <div class="filter-field checkbox">
          <label>
            <input v-model="filters.only_my_tasks" type="checkbox" />
            自分のタスクのみ
          </label>
        </div>
        <div class="filter-actions">
          <button class="btn-primary" @click="fetchList">検索</button>
          <button class="btn-secondary" @click="resetFilters">リセット</button>
        </div>
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th>注文書番号</th>
            <th>仕入先</th>
            <th>発注日</th>
            <th>希望納入日</th>
            <th>ステータス</th>
            <th>明細数</th>
            <th>未完了タスク</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td>{{ row.proposal_no }}</td>
            <td>{{ row.supplier_code }} - {{ row.supplier_name }}</td>
            <td>{{ row.order_date }}</td>
            <td>{{ row.desired_delivery_date }}</td>
            <td>{{ statusLabel(row.status) }}</td>
            <td>{{ row.line_count }}</td>
            <td>{{ pendingTaskLabels(row.pending_tasks) }}</td>
            <td>
              <button class="btn-sm" @click="goDetail(row.id)">詳細</button>
              <button
                v-if="canDelete(row)"
                class="btn-sm btn-danger"
                @click="deleteProposal(row)"
              >
                削除
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="rows.length === 0" class="no-data">データがありません</div>
    </div>

    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>発注提案書作成</h2>
        <form @submit.prevent="createProposal">
          <div class="form-group">
            <label>仕入先 *</label>
            <select v-model="createForm.supplier" required>
              <option value="">選択してください</option>
              <option v-for="supplier in suppliers" :key="supplier.id" :value="supplier.id">
                {{ supplier.supplier_code }} - {{ supplier.supplier_name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>発注日 *</label>
            <input v-model="createForm.order_date" type="date" required />
          </div>
          <div class="form-group">
            <label>希望納入日</label>
            <input v-model="createForm.desired_delivery_date" type="date" />
          </div>
          <div class="form-group">
            <label>備考</label>
            <textarea v-model="createForm.note" rows="3" />
          </div>
          <div class="form-actions">
            <button class="btn-primary" type="submit">作成</button>
            <button class="btn-secondary" type="button" @click="closeDialog">キャンセル</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatISODate } from '@/utils/dateUtil'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'

const router = useRouter()

const rows = ref([])
const suppliers = ref([])
const showDialog = ref(false)

const filters = ref({
  supplier: '',
  status: '',
  order_date_from: '',
  order_date_to: '',
  only_my_tasks: true,
})

const createForm = ref({
  supplier: '',
  order_date: '',
  desired_delivery_date: '',
  note: '',
})

const statusOptions = [
  { value: 'DRAFT', label: '作成中' },
  { value: 'SUBMITTED', label: '業務員サイン済' },
  { value: 'APPROVED_L2', label: '班長承認済' },
  { value: 'APPROVED_L3', label: '係長承認済' },
  { value: 'APPROVED', label: '最終承認済' },
  { value: 'SENT', label: '送信済' },
  { value: 'REJECTED', label: '差戻' },
  { value: 'CANCELED', label: 'キャンセル' },
]

const statusLabel = (status) => {
  const found = statusOptions.find((item) => item.value === status)
  return found ? found.label : status
}

const taskTypeMap = {
  CREATE_PROPOSAL: '提案書作成',
  CREATE_ORDER_PDF: '注文書作成',
  APPROVE_L2: '班長承認',
  APPROVE_L3: '係長承認',
  APPROVE_L4: '部長承認',
  SEND_TO_SUPPLIER: '購入先送信',
}

const pendingTaskLabels = (taskTypes = []) => {
  if (!Array.isArray(taskTypes) || taskTypes.length === 0) return ''
  return taskTypes.map((taskType) => taskTypeMap[taskType] || taskType).join(', ')
}

const fetchSuppliers = async () => {
  const response = await api.suppliers.getSuppliers()
  suppliers.value = response.data.results || response.data || []
}

const fetchList = async () => {
  const params = {}
  if (filters.value.supplier) params.supplier = filters.value.supplier
  if (filters.value.status) params.status = filters.value.status
  if (filters.value.order_date_from) params.order_date_from = filters.value.order_date_from
  if (filters.value.order_date_to) params.order_date_to = filters.value.order_date_to
  params.only_my_tasks = filters.value.only_my_tasks
  const response = await api.purchaseOrderProposals.list(params)
  rows.value = response.data || []
}

const resetFilters = async () => {
  filters.value = {
    supplier: '',
    status: '',
    order_date_from: '',
    order_date_to: '',
    only_my_tasks: true,
  }
  await fetchList()
}

const goDetail = (id) => {
  router.push(`/purchase/order-proposals/${id}`)
}

const canDelete = (row) => {
  const currentUserId = authState.user?.id
  if (!currentUserId) return false
  return row.status === 'DRAFT' && Number(row.created_by) === Number(currentUserId)
}

const deleteProposal = async (row) => {
  if (!canDelete(row)) return
  if (!confirm(`提案書 ${row.proposal_no} を削除しますか？`)) return
  await api.purchaseOrderProposals.delete(row.id)
  await fetchList()
  alert('削除しました')
}

const openCreateDialog = () => {
  const today = new Date()
  const ymd = formatISODate(today)
  createForm.value = {
    supplier: '',
    order_date: ymd,
    desired_delivery_date: '',
    note: '',
  }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const createProposal = async () => {
  const payload = {
    supplier: createForm.value.supplier,
    order_date: createForm.value.order_date,
    note: createForm.value.note,
    lines: [],
  }
  if (createForm.value.desired_delivery_date) {
    payload.desired_delivery_date = createForm.value.desired_delivery_date
  }
  const response = await api.purchaseOrderProposals.create(payload)
  showDialog.value = false
  router.push(`/purchase/order-proposals/${response.data.id}`)
}

onMounted(async () => {
  await Promise.all([fetchSuppliers(), fetchList()])
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
  min-width: 180px;
}
.filter-field.checkbox {
  justify-content: flex-end;
}
.filter-actions {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}
.modal-content {
  background: white;
  padding: 24px;
  border-radius: 8px;
  min-width: 460px;
  max-width: 620px;
}
.form-group {
  margin-bottom: 12px;
}
.form-group label {
  display: block;
  margin-bottom: 4px;
}
.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>




