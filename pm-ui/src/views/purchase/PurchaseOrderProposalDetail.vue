<template>
  <div class="page-container" v-if="proposal">
    <div class="page-header">
      <h1 class="page-title">外作・購入品注文書詳細: {{ proposal.proposal_no }}</h1>
      <div class="page-actions">
        <button class="btn-secondary" @click="goBack">一覧へ戻る</button>
        <button class="btn-primary" @click="fetchDetail">更新</button>
      </div>
    </div>

    <div class="page-content">
      <div class="summary-grid">
        <div><strong>仕入先:</strong> {{ proposal.supplier_code }} - {{ proposal.supplier_name }}</div>
        <div><strong>送信先メール:</strong> {{ proposal.supplier_order_email || '-' }}</div>
        <div><strong>ステータス:</strong> {{ statusLabel(proposal.status) }}</div>
        <div><strong>発注日:</strong> {{ proposal.order_date }}</div>
        <div><strong>希望納入日:</strong> {{ proposal.desired_delivery_date }}</div>
        <div><strong>次回納入日:</strong> {{ proposal.next_delivery_date || '-' }}</div>
      </div>

      <div class="section header-edit-row">
        <label>仕入先</label>
        <select v-model="form.supplier" :disabled="!canEdit">
          <option v-for="supplier in suppliers" :key="supplier.id" :value="supplier.id">
            {{ supplier.supplier_code }} - {{ supplier.supplier_name }}
          </option>
        </select>
        <label>発注日</label>
        <input v-model="form.order_date" type="date" :disabled="!canEdit" />
        <label>希望納入日</label>
        <input v-model="form.desired_delivery_date" type="date" :disabled="!canEdit" />
        <label>次回納入日</label>
        <input v-model="form.next_delivery_date" type="date" :disabled="!canEdit" />
        <label>備考</label>
        <input v-model="form.note" :disabled="!canEdit" />
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
              <th>次回納入日</th>
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
              <td><input v-model="line.next_delivery_date" type="date" :disabled="!canEdit" /></td>
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
          <button class="btn-secondary" :disabled="!canRunAutoFill" @click="runAutoFill('PROGRESS')">進度から提案</button>
          <button class="btn-secondary" :disabled="!canRunAutoFill" @click="runAutoFill('PLANNED_PROGRESS')">計画進度から提案</button>
          <button class="btn-secondary" :disabled="!canRunAutoFill" @click="runAutoFill('PLANNED_STOCK')">計画在庫から提案</button>
          <span v-if="!canRunAutoFill" class="auto-fill-hint">※次回納入日を入力してください</span>
        </div>
      </div>

      <div class="section action-row">
        <button class="btn-primary" :disabled="!canEdit" @click="saveProposal">保存</button>
        <button class="btn-success" v-if="['DRAFT', 'REJECTED'].includes(proposal.status)" @click="submitProposal">業務員サイン</button>
        <button class="btn-danger" v-if="proposal.status === 'DRAFT'" @click="deleteProposal">削除</button>
        <button class="btn-success" v-if="canApprove" @click="approveProposal">{{ approveButtonLabel }}</button>
        <button class="btn-danger" v-if="canReject" @click="rejectProposal">差戻</button>
        <button class="btn-danger" v-if="canCancel" @click="cancelProposal">キャンセル</button>
        <button class="btn-secondary" v-if="canGenerateOrderPdf" @click="downloadOrderPdf">{{ orderPdfButtonLabel }}</button>
        <button class="btn-secondary" v-if="canGenerateDeliveryNotePdf" @click="downloadDeliveryNotePdf">{{ deliveryNotePdfButtonLabel }}</button>
        <button
          class="btn-success"
          v-if="canShowSendButton"
          @click="openSendDialog"
        >
          購入先へ送信
        </button>
        <span v-if="proposal.status === 'APPROVED' && hasPendingCreateOrderPdfTask" class="pending-send-hint">
          注文書作成後に送信できます
        </span>
        <button
          class="btn-danger"
          v-if="isSuperuser && proposal.status !== 'DRAFT'"
          @click="adminReset"
          style="margin-left: auto;"
        >
          管理者リセット
        </button>
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
              <td>{{ approvalActionLabel(row.action) }}</td>
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
              <td>{{ taskTypeLabel(row.task_type) }}</td>
              <td>{{ row.assigned_to_name || row.assigned_to_username }}</td>
              <td>{{ taskStatusLabel(row.status) }}</td>
              <td>{{ row.due_date }}</td>
              <td>{{ row.done_at }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showSendDialog" class="modal-overlay" @click.self="closeSendDialog">
      <div class="modal-content send-dialog">
        <h3>購入先へ送信</h3>
        <div class="form-group">
          <label>宛先メールアドレス</label>
          <input v-model="sendForm.to_email" type="email" />
        </div>
        <div class="form-group">
          <label>CC（社内担当者）</label>
          <div class="cc-options readonly">
            <span v-for="option in sendCcOptions" :key="option.email" class="cc-option readonly">
              {{ option.label }}
            </span>
            <span v-if="!sendCcOptions.length" class="cc-empty">CCは注文書メール設定で未設定です</span>
          </div>
        </div>
        <div class="form-group">
          <label>件名</label>
          <input v-model="sendForm.subject" type="text" />
        </div>
        <div class="form-group">
          <label>本文</label>
          <textarea v-model="sendForm.body" rows="10" />
        </div>
        <div class="dialog-actions">
          <button class="btn-primary" :disabled="processing" @click="sendProposal">
            {{ processing ? '送信中...' : '送信' }}
          </button>
          <button class="btn-secondary" :disabled="processing" @click="closeSendDialog">キャンセル</button>
        </div>
      </div>
    </div>

    <div v-if="processing" class="processing-overlay">
      <div class="processing-box">
        <div class="spinner"></div>
        <span>{{ processingLabel }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatISODate } from '@/utils/dateUtil'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'

const route = useRoute()
const router = useRouter()
const proposalId = Number(route.params.id)

const proposal = ref(null)
const processing = ref(false)
const processingLabel = ref('')
const approvalRouteConfig = ref(null)
const suppliers = ref([])
const allProducts = ref([])
const supplierProductIds = ref(null)
const allPurchaseLines = ref([])
const purchaseLines = computed(() => {
  if (!proposal.value?.supplier) return allPurchaseLines.value
  const supplier = suppliers.value.find(s => s.id === proposal.value.supplier)
  if (!supplier) return allPurchaseLines.value
  const matched = allPurchaseLines.value.filter(l => l.line_code === supplier.supplier_code)
  return matched.length ? matched : allPurchaseLines.value
})
const showSendDialog = ref(false)
const sendCcOptions = ref([])
const sendEmailConfig = ref(null)
const sendForm = ref({
  to_email: '',
  subject: '',
  body: '',
})

const form = ref({
  supplier: null,
  order_date: '',
  desired_delivery_date: '',
  next_delivery_date: '',
  note: '',
  lines: [],
})

const products = computed(() => {
  if (!supplierProductIds.value) return allProducts.value
  return allProducts.value.filter(p => supplierProductIds.value.has(p.id))
})

const canRunAutoFill = computed(() => canEdit.value && Boolean(form.value.next_delivery_date))

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

const approvalActionMap = {
  APPROVED: '承認',
  REJECTED: '差戻',
}

const approvalActionLabel = (action) => approvalActionMap[action] || action

const taskTypeMap = {
  CREATE_PROPOSAL: '提案書作成',
  CREATE_ORDER_PDF: '注文書作成',
  APPROVE_L2: '班長承認',
  APPROVE_L3: '係長承認',
  APPROVE_L4: '部長承認',
  SEND_TO_SUPPLIER: '購入先送信',
}

const taskTypeLabel = (taskType) => taskTypeMap[taskType] || taskType

const taskStatusMap = {
  PENDING: '未対応',
  DONE: '完了',
  SKIPPED: 'スキップ',
}

const taskStatusLabel = (taskStatus) => taskStatusMap[taskStatus] || taskStatus

const canEdit = computed(() => proposal.value && ['DRAFT', 'REJECTED'].includes(proposal.value.status))
const currentUserId = computed(() => Number(authState.user?.id || 0))
const isSuperuser = computed(() => !!authState.user?.is_superuser)
const approvalTaskTypeByStatus = {
  SUBMITTED: 'APPROVE_L2',
  APPROVED_L2: 'APPROVE_L3',
  APPROVED_L3: 'APPROVE_L4',
}
const myPendingApprovalTask = computed(() => {
  if (!proposal.value) return false
  const expectedTaskType = approvalTaskTypeByStatus[proposal.value.status]
  if (!expectedTaskType) return false
  if (!currentUserId.value) return false
  return (proposal.value.tasks || []).find(
    (row) =>
      row.status === 'PENDING' &&
      row.task_type === expectedTaskType &&
      Number(row.assigned_to) === currentUserId.value
  )
})
const hasMyPendingApprovalTask = computed(() => Boolean(myPendingApprovalTask.value))
const level4ProxyApproverSet = computed(() => {
  const ids = Array.isArray(approvalRouteConfig.value?.approver_proxy_users)
    ? approvalRouteConfig.value.approver_proxy_users
    : []
  return new Set(ids.map((id) => Number(id)).filter((id) => Number.isFinite(id)))
})
const isProxyFinalApproval = computed(() =>
  Boolean(
    proposal.value &&
      proposal.value.status === 'APPROVED_L3' &&
      myPendingApprovalTask.value &&
      myPendingApprovalTask.value.task_type === 'APPROVE_L4' &&
      level4ProxyApproverSet.value.has(currentUserId.value)
  )
)
const approveButtonLabel = computed(() => (isProxyFinalApproval.value ? '部長代理承認' : '承認'))
const canApprove = computed(() => Boolean(proposal.value && hasMyPendingApprovalTask.value))
const canReject = computed(() => Boolean(proposal.value && hasMyPendingApprovalTask.value))
const level4AuthorizedSet = computed(() => {
  const ids = [
    ...(Array.isArray(approvalRouteConfig.value?.approver_allowed_users) ? approvalRouteConfig.value.approver_allowed_users : []),
    ...(Array.isArray(approvalRouteConfig.value?.approver_proxy_users) ? approvalRouteConfig.value.approver_proxy_users : []),
  ]
  return new Set(ids.map((id) => Number(id)).filter((id) => Number.isFinite(id)))
})
const currentUserRole = computed(() => String(authState.user?.profile?.role || '').trim())
const canCancelByApproverRole = computed(() =>
  Boolean(
    approvalRouteConfig.value &&
      !level4AuthorizedSet.value.size &&
      currentUserRole.value &&
      currentUserRole.value === String(approvalRouteConfig.value.approver_role || '').trim()
  )
)
const canCancel = computed(() =>
  Boolean(
    proposal.value &&
      proposal.value.status === 'APPROVED' &&
      currentUserId.value &&
      (level4AuthorizedSet.value.has(currentUserId.value) || canCancelByApproverRole.value)
  )
)
const canGenerateOrderPdf = computed(() =>
  proposal.value && !['CANCELED'].includes(proposal.value.status)
)
const canGenerateDeliveryNotePdf = computed(() =>
  proposal.value && !['CANCELED'].includes(proposal.value.status)
)
const deliveryNotePdfButtonLabel = computed(() =>
  proposal.value && ['APPROVED', 'SENT'].includes(proposal.value.status)
    ? '納品書作成' : '納品書プレビュー'
)
const orderPdfButtonLabel = computed(() =>
  proposal.value && ['APPROVED', 'SENT'].includes(proposal.value.status)
    ? '注文書作成' : '注文書プレビュー'
)
const hasPendingCreateOrderPdfTask = computed(() =>
  Boolean(
    proposal.value &&
      (proposal.value.tasks || []).some(
        (row) => row.task_type === 'CREATE_ORDER_PDF' && row.status === 'PENDING'
      )
  )
)
const hasPendingSendToSupplierTask = computed(() =>
  Boolean(
    proposal.value &&
      (proposal.value.tasks || []).some(
        (row) => row.task_type === 'SEND_TO_SUPPLIER' && row.status === 'PENDING'
      )
  )
)
const canShowSendButton = computed(() =>
  Boolean(proposal.value && proposal.value.status === 'APPROVED' && hasPendingSendToSupplierTask.value)
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
  next_delivery_date: line.next_delivery_date || '',
  order_qty: line.order_qty ?? 0,
  note: line.note || '',
})

const setFormFromProposal = (data) => {
  form.value = {
    supplier: data.supplier,
    order_date: data.order_date,
    desired_delivery_date: data.desired_delivery_date,
    next_delivery_date: data.next_delivery_date || '',
    note: data.note || '',
    lines: (data.lines || []).map((line) => buildLineRow(line)),
  }
}

const fetchMasterData = async () => {
  const [supplierRes, productRes, lineRes] = await Promise.all([
    api.suppliers.getSuppliers(),
    api.products.getProducts({ page_size: 10000 }),
    api.lines.getLines({ page_size: 500 }),
  ])
  suppliers.value = supplierRes.data.results || supplierRes.data || []
  allProducts.value = productRes.data.results || productRes.data || []
  const lines = lineRes.data.results || lineRes.data || []
  allPurchaseLines.value = lines.filter((row) => row.line_type === 'PURCHASE')
}

const fetchSupplierProducts = async (supplierId) => {
  if (!supplierId) {
    supplierProductIds.value = null
    return
  }
  const supplier = suppliers.value.find(s => s.id === supplierId)
  if (!supplier) {
    supplierProductIds.value = null
    return
  }
  const supplierLine = allPurchaseLines.value.find(l => l.line_code === supplier.supplier_code)
  if (!supplierLine) {
    supplierProductIds.value = new Set()
    return
  }
  const res = await api.routings.getRoutingSteps({ line: supplierLine.id })
  const steps = res.data?.results || res.data || []
  const ids = new Set(steps.map(s => s.output_product).filter(Boolean))
  supplierProductIds.value = ids
}

const fetchApprovalRouteConfig = async () => {
  const response = await api.accounts.getApprovalRoutes({ item_key: 'purchase_order_proposal' })
  const rows = response.data?.results || response.data || []
  approvalRouteConfig.value = rows.find((row) => row.item_key === 'purchase_order_proposal') || null
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
      next_delivery_date: line.next_delivery_date || null,
      order_qty: line.order_qty ?? 0,
      note: line.note || '',
    }))

const withProcessing = async (label, fn) => {
  if (processing.value) return
  processing.value = true
  processingLabel.value = label
  try {
    await fn()
  } catch (e) {
    const responseData = e?.response?.data
    if (responseData instanceof Blob) {
      const msg = await parsePdfErrorMessage(e)
      alert(msg)
    } else {
      const detail = responseData?.detail
      if (detail) alert(detail)
      else throw e
    }
  } finally {
    processing.value = false
    processingLabel.value = ''
  }
}

const saveProposal = () => withProcessing('保存中...', async () => {
  if (!canEdit.value) return
  await api.purchaseOrderProposals.update(proposalId, {
    supplier: form.value.supplier,
    order_date: form.value.order_date,
    desired_delivery_date: form.value.desired_delivery_date,
    next_delivery_date: form.value.next_delivery_date || null,
    note: form.value.note,
    lines: serializeLines(),
  })
  await fetchDetail()
  alert('保存しました')
})

const autoFillSourceLabel = (source) => {
  if (source === 'PROGRESS') return '進度'
  if (source === 'PLANNED_PROGRESS') return '計画進度'
  return '計画在庫'
}

const runAutoFill = (source) => withProcessing('提案中...', async () => {
  if (!form.value.next_delivery_date) {
    alert('次回納入日を入力してください')
    return
  }
  await api.purchaseOrderProposals.autoFill(proposalId, {
    clear_existing: true,
    next_delivery_date: form.value.next_delivery_date,
    source,
  })
  await fetchDetail()
  alert(`${autoFillSourceLabel(source)}から提案を反映しました（〜${form.value.next_delivery_date}）`)
})

const submitProposal = () => withProcessing('提出中...', async () => {
  if (!canEdit.value) return
  await api.purchaseOrderProposals.update(proposalId, {
    supplier: form.value.supplier,
    order_date: form.value.order_date,
    desired_delivery_date: form.value.desired_delivery_date,
    next_delivery_date: form.value.next_delivery_date || null,
    note: form.value.note,
    lines: serializeLines(),
  })
  await api.purchaseOrderProposals.submit(proposalId, {})
  await fetchDetail()
  alert('提出しました')
})

const deleteProposal = async () => {
  if (!proposal.value || proposal.value.status !== 'DRAFT') {
    alert('DRAFTのみ削除できます')
    return
  }
  if (!window.confirm('この注文書を削除します。よろしいですか？')) return
  await withProcessing('削除中...', async () => {
    await api.purchaseOrderProposals.delete(proposalId)
    alert('削除しました')
    router.push('/purchase/order-proposals')
  })
}

const approveProposal = async () => {
  if (!canApprove.value) {
    alert('この承認は担当者のみ実行できます')
    return
  }
  const comment = window.prompt('承認コメント（任意）', '') || ''
  await withProcessing('承認中...', async () => {
    await api.purchaseOrderProposals.approve(proposalId, { comment })
    await fetchDetail()
    alert('承認しました')
  })
}

const rejectProposal = async () => {
  if (!canReject.value) {
    alert('この差戻は担当者のみ実行できます')
    return
  }
  const comment = window.prompt('差戻理由（必須）', '')
  if (!comment || !comment.trim()) {
    alert('差戻理由を入力してください')
    return
  }
  await withProcessing('差戻中...', async () => {
    await api.purchaseOrderProposals.reject(proposalId, { comment })
    await fetchDetail()
    alert('差戻しました')
  })
}

const cancelProposal = async () => {
  if (!canCancel.value) {
    alert('キャンセル権限がありません（事業部長または代理承認者のみ）')
    return
  }
  if (!window.confirm('この注文書をキャンセルします。よろしいですか？')) return
  const comment = window.prompt('キャンセル理由（任意）', '') || ''
  await withProcessing('キャンセル中...', async () => {
    await api.purchaseOrderProposals.cancel(proposalId, { comment })
    await fetchDetail()
    alert('キャンセルしました')
  })
}

const adminReset = async () => {
  if (!window.confirm('承認履歴・タスクを全て削除し、ステータスを「作成中」に戻します。よろしいですか？')) return
  await withProcessing('リセット中...', async () => {
    await api.purchaseOrderProposals.adminReset(proposalId)
    await fetchDetail()
    alert('リセットしました')
  })
}

const resolvePdfFilename = (contentDisposition, fallback) => {
  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match && utf8Match[1]) {
    try {
      return decodeURIComponent(utf8Match[1])
    } catch (_) {
      return fallback
    }
  }
  const plainMatch = contentDisposition.match(/filename="?([^"]+)"?/i)
  if (plainMatch && plainMatch[1]) {
    return plainMatch[1]
  }
  return fallback
}

const sanitizeFilePart = (value, fallback = '-') => {
  const raw = String(value ?? '').trim()
  const sanitized = raw.replace(/[\\/:*?"<>|]/g, '_').replace(/\s+/g, '')
  return sanitized || fallback
}

const extractDailySerialNo = (proposalNo, fallbackId) => {
  const matched = String(proposalNo || '').match(/-(\d+)$/)
  if (matched && matched[1]) {
    const parsed = Number(matched[1])
    if (Number.isFinite(parsed) && parsed > 0) return String(parsed)
  }
  return String(fallbackId || proposalId || 1)
}

const buildFallbackOrderPdfFilename = () => {
  if (!proposal.value) return `注文書_${proposalId}.pdf`

  const orderDateRaw = String(proposal.value.order_date || '').replace(/-/g, '')
  const orderDate = /^\d{8}$/.test(orderDateRaw)
    ? orderDateRaw
    : formatISODate(new Date()).replace(/-/g, '')

  const supplierCode = sanitizeFilePart(proposal.value.supplier_code, 'UNKNOWN')
  const totalAmount = Array.isArray(proposal.value.lines)
    ? proposal.value.lines.reduce((sum, row) => {
        const qty = Number(row?.order_qty ?? 0)
        return sum + (Number.isFinite(qty) && qty > 0 ? Math.trunc(qty) : 0)
      }, 0)
    : 0
  const dailySerialNo = extractDailySerialNo(proposal.value.proposal_no, proposal.value.id)
  return `${orderDate}_${supplierCode}_${totalAmount}_注文書_${dailySerialNo}.pdf`
}

const parsePdfErrorMessage = async (error) => {
  try {
    const response = error?.response
    if (!response) return '注文書PDFの作成に失敗しました'
    const payload = response.data
    if (payload instanceof Blob) {
      const text = await payload.text()
      try {
        const json = JSON.parse(text)
        if (json?.detail) return String(json.detail)
      } catch (_) {
        if (text) return text
      }
      return '注文書PDFの作成に失敗しました'
    }
    if (payload?.detail) return String(payload.detail)
    return '注文書PDFの作成に失敗しました'
  } catch (_) {
    return '注文書PDFの作成に失敗しました'
  }
}

const downloadOrderPdf = () => withProcessing('PDF作成中...', async () => {
  {
    const response = await api.purchaseOrderProposals.downloadPdf(proposalId)
    const blob = new Blob([response.data], { type: 'application/pdf' })
    const contentDisposition = response.headers?.['content-disposition'] || ''
    const fallbackName = buildFallbackOrderPdfFilename()
    const filename = resolvePdfFilename(contentDisposition, fallbackName)
    const url = window.URL.createObjectURL(blob)

    const opened = window.open(url, '_blank')
    if (!opened) {
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      alert('PDFをダウンロードしました（ポップアップを許可すると画面表示できます）')
    }

    window.setTimeout(() => {
      window.URL.revokeObjectURL(url)
    }, 60000)

    await fetchDetail()
  }
})

const downloadDeliveryNotePdf = () => withProcessing('納品書作成中...', async () => {
  const response = await api.purchaseOrderProposals.downloadDeliveryNotePdf(proposalId)
  const blob = new Blob([response.data], { type: 'application/pdf' })
  const contentDisposition = response.headers?.['content-disposition'] || ''
  let filename = '外作納品書.pdf'
  if (contentDisposition) {
    const utf8Match = contentDisposition.match(/filename\*=UTF-8''(.+)/i)
    if (utf8Match) filename = decodeURIComponent(utf8Match[1])
  }
  const url = window.URL.createObjectURL(blob)
  const opened = window.open(url, '_blank')
  if (!opened) {
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    alert('PDFをダウンロードしました（ポップアップを許可すると画面表示できます）')
  }
  window.setTimeout(() => { window.URL.revokeObjectURL(url) }, 60000)
})

const buildDefaultSendSubject = () => {
  if (!proposal.value) return ''
  return `【発注書】${proposal.value.proposal_no} ${proposal.value.supplier_name}`
}

const addCcOption = (options, seen, name, email, userId, roleLabel) => {
  const normalizedEmail = String(email || '').trim()
  if (!normalizedEmail) return
  const key = userId ? `user-${userId}` : normalizedEmail
  if (seen.has(key)) return
  seen.add(key)
  const displayName = String(name || '').trim() || normalizedEmail
  options.push({
    email: normalizedEmail,
    label: roleLabel ? `${roleLabel}: ${displayName} <${normalizedEmail}>` : `${displayName} <${normalizedEmail}>`,
  })
}

const userDisplayName = (user) => {
  const lastName = String(user?.last_name || '').trim()
  const firstName = String(user?.first_name || '').trim()
  return [lastName, firstName].filter(Boolean).join(' ') || user?.profile?.name || user?.username || user?.email || ''
}

const buildDefaultCcOptions = () => {
  const options = []
  const seen = new Set()
  ;(sendEmailConfig.value?.cc_user_details || []).forEach((user) => {
    const email = String(user.email || '').trim()
    if (email) {
      addCcOption(options, seen, user.name || user.username, email, user.id, '設定CC')
      return
    }
    const displayName = user.name || user.username || `ID:${user.id}`
    options.push({
      email: `missing-${user.id}`,
      label: `設定CC: ${displayName} <メール未設定>`,
      missingEmail: true,
    })
  })
  return options
}

const defaultSendBodyTemplate = `{supplier_name} 御中

お世話になっております。
発注書を送付いたします。

注文書番号: {proposal_no}
発注日: {order_date}
希望納入日: {desired_delivery_date}

添付のPDFをご確認のうえ、手配をお願いいたします。

------------------------------
ダイソウ工業株式会社
{created_by_name}

ご不明な点がございましたら下記までご連絡ください。
Email:{created_by_email}`

const appendSendOnlyNotice = (body, ccOptions = []) => {
  const text = String(body || '')
  if (text.includes('送信専用') && (text.includes('返信') || text.includes('ご返信'))) return text
  const ccEmails = ccOptions.filter(o => o.email && !o.missingEmail).map(o => o.email)
  const replyTo = ccEmails.length ? `CC宛先（${ccEmails.join(', ')}）` : 'CC宛先'
  const notice = `※このメールは送信専用です。ご返信は${replyTo}へお願いします。`
  return text ? `${text.trimEnd()}\n\n${notice}` : notice
}

const renderSendBodyTemplate = (template) => {
  if (!proposal.value) return ''
  const values = {
    supplier_name: proposal.value.supplier_name || '',
    proposal_no: proposal.value.proposal_no || '',
    order_date: proposal.value.order_date || '',
    desired_delivery_date: proposal.value.desired_delivery_date || '',
    created_by_name: proposal.value.created_by_name || proposal.value.created_by_username || '',
    created_by_email: proposal.value.created_by_email || '',
  }
  const body = template || defaultSendBodyTemplate
  return appendSendOnlyNotice(
    body.replace(/\{(\w+)\}/g, (match, key) => (key in values ? String(values[key] || '') : match)),
    sendCcOptions.value,
  )
}

const buildDefaultSendBody = () => renderSendBodyTemplate(sendEmailConfig.value?.body || defaultSendBodyTemplate)

const openSendDialog = async () => {
  const toEmail = proposal.value?.supplier_order_email || ''
  if (!toEmail) {
    alert('仕入先マスタに送信メールアドレスが設定されていません')
    return
  }
  try {
    const { data } = await api.purchaseOrderProposals.getEmailConfig(proposal.value.supplier)
    sendEmailConfig.value = data || null
  } catch (err) {
    sendEmailConfig.value = null
  }
  const ccOptions = buildDefaultCcOptions()
  sendCcOptions.value = ccOptions
  sendForm.value = {
    to_email: toEmail,
      subject: buildDefaultSendSubject(),
    body: buildDefaultSendBody(),
  }
  showSendDialog.value = true
}

const closeSendDialog = () => {
  showSendDialog.value = false
}

const sendProposal = async () => {
  const toEmail = String(sendForm.value.to_email || '').trim()
  if (!toEmail) {
    alert('宛先メールアドレスを入力してください')
    return
  }
  const subject = String(sendForm.value.subject || '').trim()
  if (!subject) {
    alert('件名を入力してください')
    return
  }
  const body = String(sendForm.value.body || '').trim()
  if (!body) {
    alert('本文を入力してください')
    return
  }
  await withProcessing('送信中...', async () => {
    const response = await api.purchaseOrderProposals.send(proposalId, {
      to_email: toEmail,
      subject,
      body: sendForm.value.body,
    })
    closeSendDialog()
    await fetchDetail()
    const result = response.data?.send_result || ''
    const savedPath = response.data?.saved_pdf_path || ''
    const lines = ['購入先へ送信しました']
    if (result) lines.push(result)
    if (savedPath) lines.push(`保存先: ${savedPath}`)
    alert(lines.join('\n'))
  })
}

watch(() => form.value.supplier, (newVal) => {
  fetchSupplierProducts(newVal)
})

onMounted(async () => {
  await Promise.all([fetchMasterData(), fetchDetail(), fetchApprovalRouteConfig()])
  if (proposal.value?.supplier) {
    await fetchSupplierProducts(proposal.value.supplier)
  }
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
.header-edit-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.header-edit-row label {
  font-weight: 600;
  font-size: 13px;
  white-space: nowrap;
}
.header-edit-row select,
.header-edit-row input {
  padding: 2px 4px;
  font-size: 13px;
}
.header-edit-row input[type="date"] {
  width: 130px;
}
.header-edit-row input:not([type="date"]) {
  flex: 1;
  min-width: 80px;
}
.page-content {
  overflow-x: visible;
}
.data-table thead th {
  position: sticky;
  top: -1px;
  background: #f1f5f9;
  z-index: 10;
  box-shadow: 0 1px 0 #cbd5e1;
}
.form-group.full {
  grid-column: 1 / -1;
}
.line-actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.auto-fill-hint {
  font-size: 12px;
  color: #92400e;
}
.action-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.pending-send-hint {
  font-size: 12px;
  color: #92400e;
}
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}
.modal-content {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  width: min(980px, 96vw);
  max-height: 88vh;
  overflow: auto;
}
.send-dialog h3 {
  margin: 0 0 14px;
  font-size: 24px;
}
.send-dialog .form-group {
  margin-bottom: 12px;
}
.send-dialog .form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 16px;
}
.send-dialog .form-group input,
.send-dialog .form-group textarea {
  width: 100%;
  box-sizing: border-box;
  font-size: 18px;
  line-height: 1.45;
  padding: 8px 10px;
}
.send-dialog .form-group textarea {
  min-height: 320px;
  resize: vertical;
}
.cc-options {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
  padding: 8px;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
}
.cc-option {
  display: inline-flex !important;
  align-items: center;
  gap: 4px;
  margin: 0 !important;
  font-size: 14px !important;
}
.cc-option input {
  width: auto !important;
}
.cc-empty {
  color: #64748b;
  font-size: 14px;
}
.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.processing-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}
.processing-box {
  background: #fff;
  border-radius: 8px;
  padding: 24px 36px;
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 16px;
  font-weight: 500;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}
.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #e2e8f0;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>




