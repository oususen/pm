<template>
  <div class="page-container" v-if="proposal">
    <div class="page-header">
      <h1 class="page-title">発注提案書詳細: {{ proposal.proposal_no }}</h1>
      <div class="page-actions">
        <button class="btn-secondary" @click="goBack">一覧へ戻る</button>
        <button class="btn-primary" @click="fetchDetail">更新</button>
      </div>
    </div>

    <div class="page-content">
      <div class="summary-grid">
        <div><strong>仕入先:</strong> {{ proposal.supplier_code }} - {{ proposal.supplier_name }}</div>
        <div><strong>ステータス:</strong> {{ statusLabel(proposal.status) }}</div>
        <div><strong>発注日:</strong> {{ proposal.order_date }}</div>
        <div><strong>希望納入日:</strong> {{ proposal.desired_delivery_date }}</div>
      </div>

      <div class="section">
        <h3>ヘッダ編集</h3>
        <div class="edit-grid">
          <div class="form-group">
            <label>仕入先</label>
            <select v-model="form.supplier" :disabled="!canEdit">
              <option v-for="supplier in suppliers" :key="supplier.id" :value="supplier.id">
                {{ supplier.supplier_code }} - {{ supplier.supplier_name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>発注日</label>
            <input v-model="form.order_date" type="date" :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>希望納入日</label>
            <input v-model="form.desired_delivery_date" type="date" :disabled="!canEdit" />
          </div>
          <div class="form-group full">
            <label>備考</label>
            <textarea v-model="form.note" rows="2" :disabled="!canEdit" />
          </div>
        </div>
      </div>

      <div class="section">
        <h3>明細</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>品番</th>
              <th>購買ライン</th>
              <th>不足日</th>
              <th>不足数</th>
              <th>発注数</th>
              <th>備考</th>
              <th v-if="canEdit">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(line, index) in form.lines" :key="line.localKey">
              <td>
                <select v-model="line.product" :disabled="!canEdit">
                  <option :value="null">選択</option>
                  <option v-for="product in products" :key="product.id" :value="product.id">
                    {{ product.product_code }} - {{ product.product_name }}
                  </option>
                </select>
              </td>
              <td>
                <select v-model="line.line" :disabled="!canEdit">
                  <option :value="null">選択</option>
                  <option v-for="purchaseLine in purchaseLines" :key="purchaseLine.id" :value="purchaseLine.id">
                    {{ purchaseLine.line_code }} - {{ purchaseLine.line_name }}
                  </option>
                </select>
              </td>
              <td><input v-model="line.shortage_date" type="date" :disabled="!canEdit" /></td>
              <td><input v-model.number="line.shortage_qty" type="number" :disabled="!canEdit" /></td>
              <td><input v-model.number="line.order_qty" type="number" min="0" :disabled="!canEdit" /></td>
              <td><input v-model="line.note" :disabled="!canEdit" /></td>
              <td v-if="canEdit">
                <button class="btn-sm btn-danger" @click="removeLine(index)">削除</button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="canEdit" class="line-actions">
          <button class="btn-secondary" @click="addLine">行追加</button>
          <button class="btn-secondary" @click="runAutoFill">在庫から自動提案</button>
        </div>
      </div>

      <div class="section action-row">
        <button class="btn-primary" :disabled="!canEdit" @click="saveProposal">保存</button>
        <button class="btn-success" v-if="proposal.status === 'DRAFT'" @click="submitProposal">業務員サイン</button>
        <button class="btn-success" v-if="canApprove" @click="approveProposal">承認</button>
        <button class="btn-danger" v-if="canReject" @click="rejectProposal">差戻</button>
        <button class="btn-success" v-if="proposal.status === 'APPROVED'" @click="sendProposal">送信済にする</button>
      </div>

      <div class="section">
        <h3>承認履歴</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>レベル</th>
              <th>操作</th>
              <th>承認者</th>
              <th>日時</th>
              <th>コメント</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in proposal.approvals" :key="row.id">
              <td>{{ row.approval_level }}</td>
              <td>{{ row.action }}</td>
              <td>{{ row.approved_by_name || row.approved_by_username }}</td>
              <td>{{ row.approved_at }}</td>
              <td>{{ row.comment }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="section">
        <h3>タスク</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>種別</th>
              <th>担当者</th>
              <th>状態</th>
              <th>期限</th>
              <th>完了日時</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in proposal.tasks" :key="row.id">
              <td>{{ row.task_type }}</td>
              <td>{{ row.assigned_to_name || row.assigned_to_username }}</td>
              <td>{{ row.status }}</td>
              <td>{{ row.due_date }}</td>
              <td>{{ row.done_at }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'

const route = useRoute()
const router = useRouter()
const proposalId = Number(route.params.id)

const proposal = ref(null)
const suppliers = ref([])
const products = ref([])
const purchaseLines = ref([])

const form = ref({
  supplier: null,
  order_date: '',
  desired_delivery_date: '',
  note: '',
  lines: [],
})

const statusMap = {
  DRAFT: '作成中',
  SUBMITTED: '業務員サイン済',
  APPROVED_L2: '班長承認済',
  APPROVED_L3: '係長承認済',
  APPROVED: '最終承認済',
  SENT: '送信済',
  REJECTED: '差戻',
  CANCELED: 'キャンセル',
}

const statusLabel = (status) => statusMap[status] || status

const canEdit = computed(() => proposal.value && proposal.value.status === 'DRAFT')
const canApprove = computed(() =>
  proposal.value && ['SUBMITTED', 'APPROVED_L2', 'APPROVED_L3'].includes(proposal.value.status)
)
const canReject = computed(() =>
  proposal.value && !['SENT', 'CANCELED', 'DRAFT'].includes(proposal.value.status)
)

const goBack = () => {
  router.push('/purchase/order-proposals')
}

const buildLineRow = (line = {}) => ({
  localKey: `${line.id || 'n'}-${Math.random().toString(36).slice(2, 9)}`,
  product: line.product ?? null,
  line: line.line ?? null,
  shortage_date: line.shortage_date || '',
  shortage_qty: line.shortage_qty ?? null,
  order_qty: line.order_qty ?? 0,
  note: line.note || '',
})

const setFormFromProposal = (data) => {
  form.value = {
    supplier: data.supplier,
    order_date: data.order_date,
    desired_delivery_date: data.desired_delivery_date,
    note: data.note || '',
    lines: (data.lines || []).map((line) => buildLineRow(line)),
  }
}

const fetchMasterData = async () => {
  const [supplierRes, productRes, lineRes] = await Promise.all([
    api.suppliers.getSuppliers(),
    api.products.getProducts({ page_size: 10000 }),
    api.lines.getLines(),
  ])
  suppliers.value = supplierRes.data.results || supplierRes.data || []
  products.value = productRes.data.results || productRes.data || []
  const lines = lineRes.data.results || lineRes.data || []
  purchaseLines.value = lines.filter((row) => row.line_type === 'PURCHASE')
}

const fetchDetail = async () => {
  const response = await api.purchaseOrderProposals.get(proposalId)
  proposal.value = response.data
  setFormFromProposal(response.data)
}

const addLine = () => {
  form.value.lines.push(buildLineRow())
}

const removeLine = (index) => {
  form.value.lines.splice(index, 1)
}

const serializeLines = () =>
  form.value.lines
    .filter((line) => line.product && line.line)
    .map((line) => ({
      product: line.product,
      line: line.line,
      shortage_date: line.shortage_date || null,
      shortage_qty: line.shortage_qty ?? null,
      order_qty: line.order_qty ?? 0,
      note: line.note || '',
    }))

const saveProposal = async () => {
  if (!canEdit.value) return
  await api.purchaseOrderProposals.update(proposalId, {
    supplier: form.value.supplier,
    order_date: form.value.order_date,
    desired_delivery_date: form.value.desired_delivery_date,
    note: form.value.note,
    lines: serializeLines(),
  })
  await fetchDetail()
  alert('保存しました')
}

const runAutoFill = async () => {
  await api.purchaseOrderProposals.autoFill(proposalId, { clear_existing: true, horizon_days: 90 })
  await fetchDetail()
  alert('自動提案を反映しました')
}

const submitProposal = async () => {
  await saveProposal()
  await api.purchaseOrderProposals.submit(proposalId, {})
  await fetchDetail()
  alert('提出しました')
}

const approveProposal = async () => {
  const comment = window.prompt('承認コメント（任意）', '') || ''
  await api.purchaseOrderProposals.approve(proposalId, { comment })
  await fetchDetail()
  alert('承認しました')
}

const rejectProposal = async () => {
  const comment = window.prompt('差戻理由（必須）', '')
  if (!comment || !comment.trim()) {
    alert('差戻理由を入力してください')
    return
  }
  await api.purchaseOrderProposals.reject(proposalId, { comment })
  await fetchDetail()
  alert('差戻しました')
}

const sendProposal = async () => {
  if (!confirm('送信済みにしますか？')) return
  await api.purchaseOrderProposals.send(proposalId, {})
  await fetchDetail()
  alert('送信済みにしました')
}

onMounted(async () => {
  await Promise.all([fetchMasterData(), fetchDetail()])
})
</script>

<style scoped>
.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}
.section {
  margin-bottom: 16px;
}
.edit-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 8px;
}
.form-group.full {
  grid-column: 1 / -1;
}
.line-actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}
.action-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
