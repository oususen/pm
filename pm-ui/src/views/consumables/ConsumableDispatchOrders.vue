<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">消耗品 注文書 <DataSourceDialog title="消耗品 注文書" :sources="dsSources" /></h1>
      <button class="btn-primary" :disabled="loading" @click="fetchOrders">更新</button>
    </div>

    <div class="filter-bar">
      <label>状態:
        <select v-model="statusFilter" @change="fetchOrders">
          <option value="">すべて</option>
          <option value="unsent">未送信</option>
          <option value="sent">送信済（入庫待ち）</option>
          <option value="received">入庫済</option>
        </select>
      </label>
      <label>検索: <input v-model="search" placeholder="注文書番号/購入先" @keyup.enter="fetchOrders" /></label>
      <span class="summary">{{ orders.length }}件</span>
    </div>

    <div v-if="loading" class="loading-message">読み込み中...</div>
    <table v-else class="data-table">
      <thead>
        <tr>
          <th></th><th>注文書番号</th><th>購入先</th><th>件数</th><th>金額</th><th>作成者</th><th>作成日時</th>
          <th>承認状況</th><th>状態</th><th>送信・入庫</th><th>操作</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="o in orders" :key="o.id">
          <tr :class="{ highlight: highlightId === o.id }">
            <td><button class="btn-link" @click="toggleExpand(o.id)">{{ expanded.includes(o.id) ? '▼' : '▶' }}</button></td>
            <td class="mono">{{ o.order_number }}</td>
            <td>{{ o.supplier_name }}</td>
            <td class="num">{{ o.total_items }}</td>
            <td class="num">{{ formatPrice(o.total_amount) }}円</td>
            <td>{{ o.created_by_name }}</td>
            <td class="nowrap">{{ formatDateTime(o.created_at) }}</td>
            <td>
              <span :class="['status-chip', o.approval_status]">{{ approvalLabel(o) }}</span>
              <div v-if="o.approval_status === 'rejected' && o.reject_reason" class="reject-reason">却下理由: {{ o.reject_reason }}</div>
            </td>
            <td><span :class="['status-chip', o.status]">{{ o.status_label }}</span></td>
            <td class="small">
              <div v-if="o.sent_at">送信: {{ formatDateTime(o.sent_at) }}（{{ o.sent_email }}）</div>
              <div v-if="o.received_at">入庫: {{ formatDateTime(o.received_at) }}</div>
            </td>
            <td class="action-cell">
              <button class="btn-sm btn-secondary" @click="openPdf(o)">PDF</button>
              <button v-if="canSubmit(o)" class="btn-sm btn-primary" @click="runApproval(o, 'submit')">確認依頼</button>
              <button v-if="hasTask(o, 'REVIEWER1_REVIEW', 'REVIEWER2_REVIEW')" class="btn-sm btn-primary" @click="runApproval(o, 'confirm')">確認</button>
              <button v-if="hasTask(o, 'APPROVER_APPROVE')" class="btn-sm btn-success" @click="runApproval(o, 'approve')">承認</button>
              <button v-if="hasTask(o, 'REVIEWER1_REVIEW', 'REVIEWER2_REVIEW', 'APPROVER_APPROVE')" class="btn-sm btn-warn" @click="runApproval(o, 'reject')">却下</button>
              <button v-if="canEdit && o.status === 'unsent' && o.approval_status === 'approved'" class="btn-sm btn-success" @click="sendOrder(o)">送信</button>
              <button v-if="canReceive && o.status === 'sent'" class="btn-sm btn-success" @click="receiveOrder(o)">一括入庫</button>
              <button v-if="canEdit && o.status === 'unsent'" class="btn-sm btn-delete" @click="removeOrder(o)">削除</button>
            </td>
          </tr>
          <tr v-if="expanded.includes(o.id)" class="detail-row">
            <td></td>
            <td colspan="10">
              <div v-if="o.note" class="small">備考: {{ o.note }}</div>
              <table class="data-table inner">
                <thead><tr><th>No</th><th>発注コード</th><th>コード</th><th>品名</th><th>数量</th><th>単価</th><th>金額</th><th>納期</th><th>備考</th></tr></thead>
                <tbody>
                  <tr v-for="(it, i) in o.items" :key="it.id">
                    <td class="num">{{ i + 1 }}</td>
                    <td class="mono">{{ it.order_code }}</td>
                    <td class="mono">{{ it.code }}</td>
                    <td>{{ it.name }}</td>
                    <td class="num">{{ it.quantity }} {{ it.unit }}</td>
                    <td class="num">{{ formatPrice(it.unit_price) }}</td>
                    <td class="num">{{ formatPrice(it.total_amount) }}</td>
                    <td>{{ it.deadline }}</td>
                    <td>{{ it.note }}</td>
                  </tr>
                </tbody>
              </table>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'
import DataSourceDialog from '@/components/DataSourceDialog.vue'
import { errorMessage, formatDateTime, formatPrice, rowsOf } from './consumableUtils'

const dsSources = [
  { op: '読み書き', table: 't_consumable_dispatch_order', desc: '注文書（未送信→送信済→入庫済）' },
  { op: '読み', table: 't_consumable_dispatch_order_item', desc: '注文書明細' },
  { op: '読み書き', table: 'accounts_approvalrequest', desc: '承認申請（確認依頼・確認・承認・却下）' },
  { op: '書き', table: 't_consumable_request', desc: '送信で発注済、入庫で入庫済に更新' },
  { op: '書き', table: 't_consumable_stock_movement', desc: '一括入庫の入庫履歴' },
]

const STAGE_LABELS = { creator: '作成者', reviewer1: '確認①', reviewer2: '確認②', approver: '承認者', completed: '完了' }

const route = useRoute()
const canEdit = computed(() => hasPermission(authState.user, 'consumables.dispatch', 'edit'))
const canReceive = computed(() => hasPermission(authState.user, 'consumables.operations', 'edit'))

const orders = ref([])
const loading = ref(false)
const statusFilter = ref('')
const search = ref('')
const expanded = ref([])
const highlightId = ref(Number(route.query.id) || null)

const approvalLabel = (o) => {
  if (o.approval_status === 'reviewing') return `確認中（${STAGE_LABELS[o.approval_stage] || o.approval_stage}）`
  return o.approval_status_label || '-'
}

const hasTask = (o, ...types) => o.my_pending_task_types.some((t) => types.includes(t))

const canSubmit = (o) => {
  if (o.status !== 'unsent' || !['created', 'rejected'].includes(o.approval_status)) return false
  const user = authState.user
  return Boolean(user && (user.is_superuser || user.id === o.created_by))
}

async function fetchOrders() {
  loading.value = true
  try {
    const params = { page_size: 0, search: search.value || undefined }
    if (statusFilter.value) params.status = statusFilter.value
    orders.value = rowsOf(await api.consumables.listDispatchOrders(params))
  } finally {
    loading.value = false
  }
}

function toggleExpand(id) {
  expanded.value = expanded.value.includes(id) ? expanded.value.filter((x) => x !== id) : [...expanded.value, id]
}

async function openPdf(o) {
  // 先にウィンドウを開いておく（非同期後の window.open はポップアップブロックされるため）
  const win = window.open('', '_blank')
  try {
    const res = await api.consumables.fetchDispatchOrderPdf(o.id)
    const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
    if (win) win.location.href = url
    else window.open(url, '_blank')
  } catch (err) {
    if (win) win.close()
    alert(`PDFを開けませんでした: ${errorMessage(err)}`)
  }
}

async function runApproval(o, actionName) {
  const labels = { submit: '確認依頼', confirm: '確認', approve: '承認', reject: '却下' }
  let reason = ''
  if (actionName === 'reject') {
    reason = prompt('却下理由を入力してください')
    if (reason === null) return
  } else if (!confirm(`${o.order_number}（${o.supplier_name}）を${labels[actionName]}しますか？`)) {
    return
  }
  try {
    const id = o.approval_request
    if (actionName === 'submit') await api.accounts.submitApprovalRequest(id)
    if (actionName === 'confirm') await api.accounts.confirmApprovalRequest(id)
    if (actionName === 'approve') await api.accounts.approveApprovalRequest(id)
    if (actionName === 'reject') await api.accounts.rejectApprovalRequest(id, reason)
    fetchOrders()
  } catch (err) {
    alert(`${labels[actionName]}できませんでした: ${errorMessage(err)}`)
  }
}

async function sendOrder(o) {
  const email = prompt(`${o.supplier_name} へ注文書を送信します。送信先メールアドレス:`, o.supplier_email || '')
  if (email === null) return
  if (!email.trim()) {
    alert('送信先メールアドレスを入力してください')
    return
  }
  try {
    await api.consumables.sendDispatchOrder(o.id, email.trim())
    alert('送信しました')
    fetchOrders()
  } catch (err) {
    alert(errorMessage(err))
  }
}

async function receiveOrder(o) {
  if (!confirm(`${o.order_number}（${o.supplier_name}）の全明細 ${o.total_items}件を入庫しますか？\n在庫数が増え、依頼は入庫済になります。`)) return
  try {
    await api.consumables.receiveDispatchOrder(o.id)
    fetchOrders()
  } catch (err) {
    alert(errorMessage(err))
  }
}

async function removeOrder(o) {
  if (!confirm(`${o.order_number} を削除しますか？\n依頼は発注準備に戻り、承認申請も削除されます。`)) return
  try {
    await api.consumables.deleteDispatchOrder(o.id)
    fetchOrders()
  } catch (err) {
    alert(errorMessage(err))
  }
}

onMounted(async () => {
  await fetchOrders()
  if (highlightId.value) expanded.value = [highlightId.value]
})
</script>

<style scoped>
.page-container { padding: 12px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.page-title { font-size: 1.2em; margin: 0; }
.filter-bar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 6px; font-size: 0.85em; }
.summary { color: #555; }
.loading-message { padding: 12px; color: #666; }
.data-table { width: 100%; border-collapse: collapse; font-size: 0.85em; }
.data-table th, .data-table td { padding: 3px 6px; border: 1px solid #ddd; text-align: left; vertical-align: top; }
.data-table th { background: #f5f5f5; white-space: nowrap; }
.data-table .num { text-align: right; white-space: nowrap; }
.data-table .mono { font-family: monospace; }
.data-table .nowrap { white-space: nowrap; }
.data-table.inner { margin-top: 4px; }
.small { font-size: 0.85em; color: #555; }
.highlight { background: #fffde7; }
.detail-row { background: #fafafa; }
.reject-reason { color: #c62828; font-size: 0.85em; }
.action-cell { white-space: nowrap; }
.action-cell button { margin-right: 3px; }
.status-chip { padding: 0 6px; border-radius: 8px; background: #eee; white-space: nowrap; }
.status-chip.created { background: #eceff1; color: #455a64; }
.status-chip.reviewing { background: #fff3e0; color: #e65100; }
.status-chip.approved { background: #e8f5e9; color: #2e7d32; }
.status-chip.rejected { background: #ffebee; color: #c62828; }
.status-chip.unsent { background: #fff3e0; color: #e65100; }
.status-chip.sent { background: #e3f2fd; color: #1565c0; }
.status-chip.received { background: #eceff1; color: #455a64; }
.btn-link { border: none; background: none; cursor: pointer; color: #1565c0; }
.btn-primary { background: #1565c0; color: #fff; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85em; }
.btn-success { background: #2e7d32; color: #fff; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85em; }
.btn-secondary { background: #f5f5f5; border: 1px solid #ccc; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85em; }
.btn-warn { background: #ef6c00; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
.btn-delete { background: #e53935; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
.btn-sm { padding: 2px 8px; font-size: 0.8em; }
</style>
