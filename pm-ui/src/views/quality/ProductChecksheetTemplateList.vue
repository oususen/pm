<template>
  <div class="page-container checksheet-master" v-if="canView">
    <div class="page-header">
      <h2 class="page-title">品質チェックシート作成</h2>
      <div class="page-actions">
        <button class="btn-secondary" @click="loadTemplateList" :disabled="loadingList || detailLoading">
          更新
        </button>
        <button class="btn-secondary" @click="toggleTemplateList" :disabled="saving || actionLoading">
          {{ isListHidden ? '一覧表示' : '一覧隠す' }}
        </button>
        <button class="btn-primary" @click="startNewTemplate" :disabled="saving || actionLoading">
          新規作成
        </button>
      </div>
    </div>

    <div class="master-layout" :class="{ 'create-mode': isListHidden }">
      <section v-if="!isListHidden" class="panel list-panel">
        <h3 class="panel-title">テンプレート一覧</h3>
        <div class="list-filter-bar">
          <input v-model="listFilter.keyword" class="list-filter-input" placeholder="品番・品名・テンプレ名" />
          <select v-model="listFilter.status" class="list-filter-select">
            <option value="">状態：すべて</option>
            <option value="DRAFT">下書き</option>
            <option value="SUPERVISOR_PENDING">班長確認待ち</option>
            <option value="CHIEF_PENDING">係長承認待ち</option>
            <option value="MANAGER_PENDING">部長承認待ち</option>
            <option value="APPROVED">承認済み</option>
            <option value="REJECTED">差戻し</option>
          </select>
        </div>
        <div class="table-wrap">
          <table class="data-table compact">
            <thead>
              <tr>
                <th>ID</th>
                <th>製品</th>
                <th>テンプレート名</th>
                <th>版</th>
                <th>状態</th>
                <th>更新日時</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in filteredTemplates"
                :key="row.id"
                :class="{ selected: Number(selectedTemplateId) === Number(row.id) }"
                @click="selectTemplate(row.id)"
              >
                <td>{{ row.id }}</td>
                <td>{{ row.product_code || '-' }}</td>
                <td>{{ row.document_title || row.name || '-' }}</td>
                <td>{{ row.version }}</td>
                <td>
                  <span class="status-chip" :class="statusClass(row.status)">
                    {{ statusLabel(row.status) }}
                  </span>
                </td>
                <td>{{ formatDateTime(row.updated_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="!filteredTemplates.length && !loadingList" class="no-data">データがありません</div>
      </section>

      <section class="panel edit-panel">
        <h3 class="panel-title">編集</h3>

        <div class="status-row">
          <span class="status-chip" :class="statusClass(form.status)">
            {{ statusLabel(form.status) }}
          </span>
          <span class="status-meta">
            作成者: {{ form.created_by_name || '-' }}
            <span v-if="form.created_at" class="status-date">（{{ formatDate(form.created_at) }}）</span>
          </span>
          <span class="status-meta">
            班長担当: {{ form.reviewer_user_name || '-' }}
            <span v-if="form.reviewed_at" class="status-date">（{{ formatDate(form.reviewed_at) }}）</span>
          </span>
          <span class="status-meta">
            係長担当: {{ form.chief_user_name || '-' }}
            <span v-if="form.chief_reviewed_at" class="status-date">（{{ formatDate(form.chief_reviewed_at) }}）</span>
          </span>
          <span class="status-meta">
            部長担当: {{ form.approver_user_name || '-' }}
            <span v-if="form.approved_at" class="status-date">（{{ formatDate(form.approved_at) }}）</span>
          </span>
        </div>

        <div class="form-grid">
          <label>
            テンプレート名
            <input v-model.trim="form.name" :disabled="!canEditFields" />
          </label>
          <label>
            ライン <span class="required-mark">*</span>
            <select v-model="form.line" :disabled="!canEditFields" required>
              <option value="">選択してください</option>
              <option v-for="l in lineOptions" :key="l.id" :value="l.id">{{ l.line_code }} - {{ l.line_name }}</option>
            </select>
          </label>
          <label>
            工程 <span class="required-mark">*</span>
            <select v-model="form.process" :disabled="!canEditFields" required>
              <option value="">選択してください</option>
              <option v-for="p in processOptions" :key="p.id" :value="p.id">{{ p.process_code }} - {{ p.process_name }}</option>
            </select>
          </label>
          <label>
            製品 <span class="required-mark">*</span>
            <div class="autocomplete">
              <input
                v-model="productSearch"
                type="text"
                placeholder="品番・品名で検索"
                autocomplete="off"
                :disabled="!canEditFields"
                @input="onProductSearchInput"
                @focus="showProductSuggestions = true"
                @blur="hideProductSuggestions"
                @keydown.enter.prevent="selectFirstProduct"
              />
              <div v-if="showProductSuggestions && canEditFields" class="suggestions">
                <button
                  v-for="product in productSuggestions"
                  :key="product.id"
                  type="button"
                  class="suggestion"
                  @mousedown.prevent="selectProduct(product)"
                >
                  <span>{{ product.product_code }}</span>
                  <small>{{ product.product_name }}</small>
                </button>
                <p v-if="productSearching" class="suggestion-note">検索中...</p>
                <p v-else-if="productSearch.trim() && !productSuggestions.length" class="suggestion-note">該当なし</p>
                <p v-else-if="!productSearch.trim()" class="suggestion-note">品番または品名を入力してください。</p>
              </div>
            </div>
          </label>
          <label class="wide">
            帳票タイトル
            <input v-model.trim="form.document_title" :disabled="!canEditFields" />
          </label>
          <label>
            元シート名
            <input v-model.trim="form.sheet_name" :disabled="!canEditFields" />
          </label>
          <label>
            改訂日
            <input type="date" v-model="form.revision_date" :disabled="!canEditFields" />
          </label>
          <label class="wide">
            改訂内容
            <textarea v-model="form.revision_notes" :disabled="!canEditFields" rows="2" />
          </label>
          <label>
            運用開始日
            <input type="date" v-model="form.effective_from" :disabled="!canEditFields" />
          </label>
          <label>
            版
            <input type="number" min="1" v-model.number="form.version" :disabled="!canEditFields" />
          </label>
          <label class="check-line">
            <input type="checkbox" v-model="form.is_active" :disabled="!canEditFields" />
            有効
          </label>
        </div>

        <h4 class="sub-section-title">台紙</h4>
        <div class="form-grid">
          <label>
            台紙PDF
            <input type="file" accept="application/pdf" :disabled="!canEditFields" @change="onFileChange($event, 'source_pdf')" />
          </label>
          <label>
            台紙画像
            <input type="file" accept="image/*" :disabled="!canEditFields" @change="onFileChange($event, 'source_image')" />
          </label>
          <label class="wide">
            編集メモ
            <textarea v-model="form.editor_notes" :disabled="!canEditFields" rows="2" />
          </label>
        </div>

        <div v-if="form.rejection_comment" class="rejection-box">
          差戻しコメント: {{ form.rejection_comment }}
        </div>

        <div class="workflow-actions">
          <button class="btn-primary" @click="saveTemplate" :disabled="!canEditFields || saving">
            {{ form.id ? '下書き更新' : '下書き保存' }}
          </button>
          <button class="btn-secondary" @click="downloadPreviewPdf" :disabled="!form.id || pdfLoading">
            {{ pdfLoading ? 'PDF生成中...' : 'PDF出力' }}
          </button>
          <button class="btn-approve" @click="submitForReview" :disabled="!canSubmitForReview || actionLoading">
            確認依頼
          </button>
          <button class="btn-review" @click="completeReview" :disabled="!canReview || actionLoading">
            {{ reviewActionLabel }}
          </button>
          <button class="btn-approve" @click="approveTemplate" :disabled="!canApprove || actionLoading">
            部長承認
          </button>
          <button class="btn-danger" @click="rejectTemplate" :disabled="!canReject || actionLoading">
            差戻し
          </button>
          <button class="btn-revise" @click="reviseTemplate" :disabled="!canRevise || actionLoading">
            改訂
          </button>
        </div>

        <div class="item-section">
          <div class="section-header">
            <h4>フィールド配置</h4>
            <RouterLink
              v-if="form.id"
              class="btn-secondary btn-sm"
              :to="`/quality/product-checksheet/templates/${form.id}/edit`"
            >
              配置エディタを開く
            </RouterLink>
          </div>
          <div v-if="form.fields_data && form.fields_data.length" class="table-wrap">
            <table class="data-table compact">
              <thead>
                <tr>
                  <th>No</th>
                  <th>キー</th>
                  <th>ラベル</th>
                  <th>種別</th>
                  <th>必須</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(field, idx) in form.fields_data" :key="field.id || idx">
                  <td>{{ field.sort_order || idx + 1 }}</td>
                  <td>{{ field.key }}</td>
                  <td>{{ field.label }}</td>
                  <td>{{ field.field_type }}</td>
                  <td>{{ field.required ? 'Yes' : '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="no-data">フィールドはまだ配置されていません。保存後に配置エディタでフィールドを追加してください。</div>
        </div>

        <div class="item-section">
          <h4>ワークフロー履歴</h4>
          <div class="table-wrap">
            <table class="data-table compact">
              <thead>
                <tr>
                  <th>日時</th>
                  <th>操作</th>
                  <th>遷移</th>
                  <th>実施者</th>
                  <th>コメント</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="log in form.workflow_logs" :key="log.id">
                  <td>{{ formatDateTime(log.created_at) }}</td>
                  <td>{{ actionLabelText(log.action) }}</td>
                  <td>{{ transitionLabel(log.from_status, log.to_status) }}</td>
                  <td>{{ log.actor_name || '-' }}</td>
                  <td>{{ log.comment || '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="!form.workflow_logs.length" class="no-data">履歴はありません</div>
        </div>
      </section>
    </div>

    <!-- 確認依頼コメントモーダル -->
    <div v-if="submitDialogVisible" class="modal-backdrop" @click.self="cancelSubmit">
      <div class="modal-panel reject-modal">
        <div class="modal-header">
          <h3 class="panel-title">確認依頼</h3>
        </div>
        <div class="reject-modal-body">
          <label class="reject-label">コメント（任意）</label>
          <textarea
            v-model="submitComment"
            class="reject-textarea"
            rows="5"
            placeholder="確認依頼時のコメントがあれば入力してください。"
            autofocus
          />
        </div>
        <div class="reject-modal-footer">
          <button class="btn-secondary" @click="cancelSubmit">キャンセル</button>
          <button class="btn-approve" @click="confirmSubmitForReview">確認依頼</button>
        </div>
      </div>
    </div>

    <!-- 差戻しコメントモーダル -->
    <div v-if="rejectDialogVisible" class="modal-backdrop" @click.self="cancelReject">
      <div class="modal-panel reject-modal">
        <div class="modal-header">
          <h3 class="panel-title">差戻し</h3>
        </div>
        <div class="reject-modal-body">
          <label class="reject-label">差戻しコメント</label>
          <textarea
            v-model="rejectComment"
            class="reject-textarea"
            rows="8"
            placeholder="差戻しの理由や修正指示を入力してください。"
            autofocus
          />
        </div>
        <div class="reject-modal-footer">
          <button class="btn-secondary" @click="cancelReject">キャンセル</button>
          <button class="btn-danger" @click="confirmReject">差戻し実行</button>
        </div>
      </div>
    </div>
  </div>

  <div class="page-container" v-else>
    <h2 class="page-title">品質チェックシート作成</h2>
    <p class="no-data">品質の閲覧権限がありません。</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const STATUS_LABELS = {
  DRAFT: '下書き',
  SUPERVISOR_PENDING: '班長確認待ち',
  CHIEF_PENDING: '係長承認待ち',
  MANAGER_PENDING: '部長承認待ち',
  APPROVED: '承認済み',
  REJECTED: '差戻し',
}

const ACTION_LABELS = {
  CREATED: '作成',
  UPDATED: '更新',
  SUBMITTED: '確認依頼',
  SUPERVISOR_REVIEWED: '班長確認完了',
  CHIEF_REVIEWED: '係長承認',
  APPROVED: '部長承認',
  REJECTED: '差戻し',
}

const route = useRoute()
const router = useRouter()

const templates = ref([])
const loadingList = ref(false)
const detailLoading = ref(false)
const saving = ref(false)
const actionLoading = ref(false)
const selectedTemplateId = ref(null)
const isListHidden = ref(false)
const lineOptions = ref([])
const allProcesses = ref([])
const processOptions = computed(() => {
  if (!form.value.line) return allProcesses.value
  return allProcesses.value.filter((p) => String(p.line) === String(form.value.line))
})
const pdfLoading = ref(false)
const rejectDialogVisible = ref(false)
const rejectComment = ref('')
const submitDialogVisible = ref(false)
const submitComment = ref('')
const listFilter = ref({ keyword: '', status: '' })

const productSearch = ref('')
const productSuggestions = ref([])
const productSearching = ref(false)
const showProductSuggestions = ref(false)
const selectedProductLabel = ref('')
let productSearchTimer = null
let productSearchSerial = 0

const createEmptyForm = () => ({
  id: null,
  name: '',
  line: '',
  process: '',
  product: '',
  document_title: '',
  sheet_name: '',
  revision_date: '',
  revision_notes: '',
  effective_from: '',
  editor_notes: '',
  version: 1,
  status: 'DRAFT',
  is_active: true,
  source_pdf: null,
  source_image: null,
  created_by_name: '',
  created_at: '',
  reviewer_user: null,
  reviewer_user_name: '',
  chief_user: null,
  chief_user_name: '',
  approver_user: null,
  approver_user_name: '',
  rejection_comment: '',
  reviewed_at: '',
  chief_reviewed_at: '',
  approved_at: '',
  fields_data: [],
  workflow_logs: [],
})

const form = ref(createEmptyForm())

const canAccessQuality = (resource, level = 'view') => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  if (permissions.some((item) => item.resource === resource)) return hasPermission(user, resource, level)
  return hasPermission(user, 'quality', level)
}

const canView = computed(() => canAccessQuality('quality.product_checksheet_template', 'view'))
const canEdit = computed(() => canAccessQuality('quality.product_checksheet_template', 'edit'))
const currentUserId = computed(() => Number(authState.user?.id || 0))
const normalizeStatus = (status) => String(status || '').trim().toUpperCase()
const normalizedFormStatus = computed(() => normalizeStatus(form.value.status) || 'DRAFT')

const canEditFields = computed(() => {
  if (!canEdit.value) return false
  if (!form.value.id) return true
  return ['DRAFT', 'REJECTED'].includes(normalizedFormStatus.value)
})

const canSubmitForReview = computed(() => {
  return Boolean(form.value.id) && canEditFields.value
})

const canReview = computed(() => {
  if (!canEdit.value) return false
  if (normalizedFormStatus.value === 'SUPERVISOR_PENDING') {
    const reviewerUserId = Number(form.value.reviewer_user || 0)
    return reviewerUserId === 0 || reviewerUserId === currentUserId.value
  }
  if (normalizedFormStatus.value === 'CHIEF_PENDING') {
    const chiefUserId = Number(form.value.chief_user || 0)
    return chiefUserId === 0 || chiefUserId === currentUserId.value
  }
  return false
})

const canApprove = computed(() => {
  if (!canEdit.value) return false
  if (normalizedFormStatus.value !== 'MANAGER_PENDING') return false
  const approverUserId = Number(form.value.approver_user || 0)
  return approverUserId === 0 || approverUserId === currentUserId.value
})

const canReject = computed(() => canReview.value || canApprove.value)
const canRevise = computed(() => canEdit.value && normalizedFormStatus.value === 'APPROVED')

const reviewActionLabel = computed(() => {
  if (normalizedFormStatus.value === 'CHIEF_PENDING') return '係長承認'
  return '班長確認完了'
})

const filteredTemplates = computed(() => {
  const kw = listFilter.value.keyword.trim().toLowerCase()
  const st = listFilter.value.status
  return templates.value.filter((row) => {
    if (st && row.status !== st) return false
    if (kw) {
      const haystack = `${row.product_code || ''} ${row.product_name || ''} ${row.name || ''} ${row.document_title || ''}`.toLowerCase()
      if (!haystack.includes(kw)) return false
    }
    return true
  })
})

const statusLabel = (status) => {
  const normalized = normalizeStatus(status)
  return STATUS_LABELS[normalized] || status
}
const actionLabelText = (action) => ACTION_LABELS[action] || action

const statusClass = (status) => {
  const normalized = normalizeStatus(status)
  if (normalized === 'APPROVED') return 'ok'
  if (normalized === 'REJECTED') return 'danger'
  if (normalized === 'MANAGER_PENDING') return 'approve'
  if (normalized === 'SUPERVISOR_PENDING') return 'review'
  if (normalized === 'CHIEF_PENDING') return 'approve'
  return 'draft'
}

const transitionLabel = (fromStatus, toStatus) => {
  const from = statusLabel(fromStatus || '')
  const to = statusLabel(toStatus || '')
  if (!from && !to) return '-'
  if (!from) return `→ ${to}`
  if (!to) return from
  return `${from} → ${to}`
}

const formatDateTime = (value) => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('ja-JP')
}

const formatDate = (value) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('ja-JP')
}

const onFileChange = (event, key) => {
  form.value[key] = event.target.files?.[0] || null
}

const toFormModel = (raw) => {
  const productId = raw.product || ''
  const productLabel = raw.product_code
    ? `${raw.product_code} - ${raw.product_name || ''}`
    : ''
  productSearch.value = productLabel
  selectedProductLabel.value = productLabel

  return {
    id: raw.id,
    name: raw.name || '',
    line: raw.line || '',
    process: raw.process || '',
    product: productId,
    document_title: raw.document_title || '',
    sheet_name: raw.sheet_name || '',
    revision_date: raw.revision_date || '',
    revision_notes: raw.revision_notes || '',
    effective_from: raw.effective_from || '',
    editor_notes: raw.editor_notes || '',
    version: Number(raw.version || 1),
    status: normalizeStatus(raw.status) || 'DRAFT',
    is_active: Boolean(raw.is_active),
    source_pdf: null,
    source_image: null,
    created_by_name: raw.created_by_name || '',
    created_at: raw.created_at || '',
    reviewer_user: raw.reviewer_user || null,
    reviewer_user_name: raw.reviewer_user_name || '',
    chief_user: raw.chief_user || null,
    chief_user_name: raw.chief_user_name || '',
    approver_user: raw.approver_user || null,
    approver_user_name: raw.approver_user_name || '',
    rejection_comment: raw.rejection_comment || '',
    submitted_fields_snapshot: raw.submitted_fields_snapshot || null,
    reviewed_at: raw.reviewed_at || '',
    chief_reviewed_at: raw.chief_reviewed_at || '',
    approved_at: raw.approved_at || '',
    fields_data: Array.isArray(raw.fields_data) ? raw.fields_data : [],
    workflow_logs: Array.isArray(raw.workflow_logs) ? raw.workflow_logs : [],
  }
}

const buildFormData = () => {
  const data = new FormData()
  const fields = ['name', 'line', 'process', 'product', 'document_title', 'sheet_name',
    'revision_date', 'revision_notes', 'effective_from', 'editor_notes', 'version', 'is_active']
  for (const key of fields) {
    const val = form.value[key]
    if (val !== null && val !== '' && val !== undefined) {
      data.append(key, val)
    }
  }
  if (form.value.source_pdf instanceof File) {
    data.append('source_pdf', form.value.source_pdf)
  }
  if (form.value.source_image instanceof File) {
    data.append('source_image', form.value.source_image)
  }
  return data
}

const searchProducts = async () => {
  const keyword = productSearch.value.trim()
  const serial = ++productSearchSerial
  if (!keyword) {
    productSuggestions.value = []
    return
  }
  productSearching.value = true
  try {
    const res = await api.products.getProducts({ is_active: true, is_line_final_product: true, search: keyword, page_size: 20 })
    if (serial !== productSearchSerial) return
    productSuggestions.value = res.data?.results || res.data || []
  } catch (error) {
    console.error(error)
    if (serial === productSearchSerial) productSuggestions.value = []
  } finally {
    if (serial === productSearchSerial) productSearching.value = false
  }
}

const onProductSearchInput = () => {
  showProductSuggestions.value = true
  if (productSearch.value !== selectedProductLabel.value) {
    form.value.product = ''
    selectedProductLabel.value = ''
  }
  if (productSearchTimer) clearTimeout(productSearchTimer)
  productSearchTimer = setTimeout(searchProducts, 250)
}

const selectProduct = (product) => {
  form.value.product = product.id
  selectedProductLabel.value = `${product.product_code} - ${product.product_name}`
  if (!form.value.sheet_name) form.value.sheet_name = product.product_code || ''
  const selectedProcess = allProcesses.value.find((p) => String(p.id) === String(form.value.process))
  const processName = selectedProcess?.process_name || ''
  form.value.document_title = `${product.product_code || ''}${processName ? ' ' + processName : ''} チェックシート`.trim()
  productSearch.value = selectedProductLabel.value
  productSuggestions.value = [product]
  showProductSuggestions.value = false
}

const selectFirstProduct = () => {
  if (productSuggestions.value.length) selectProduct(productSuggestions.value[0])
}

const hideProductSuggestions = () => {
  setTimeout(() => { showProductSuggestions.value = false }, 150)
}

const loadMasters = async () => {
  try {
    const [lineRes, processRes] = await Promise.all([
      api.lines.getLines({ line_type: 'PROD', page_size: 1000 }),
      api.processes.getProcesses({ is_active: true, page_size: 1000 }),
    ])
    lineOptions.value = lineRes.data?.results || lineRes.data || []
    allProcesses.value = processRes.data?.results || processRes.data || []
  } catch (error) {
    console.error('マスタ取得に失敗:', error)
  }
}

const loadTemplateList = async () => {
  if (!canView.value) return
  loadingList.value = true
  try {
    const res = await api.productChecksheets.listTemplates({ page_size: 500 })
    templates.value = res.data?.results || res.data || []
  } catch (error) {
    console.error('テンプレート一覧取得に失敗:', error)
    alert('テンプレート一覧の取得に失敗しました。')
  } finally {
    loadingList.value = false
  }
}

const loadTemplateDetail = async (id) => {
  if (!id) return
  detailLoading.value = true
  try {
    const res = await api.productChecksheets.getTemplate(id)
    form.value = toFormModel(res.data)
    selectedTemplateId.value = id
  } catch (error) {
    console.error('テンプレート詳細取得に失敗:', error)
    alert('テンプレート詳細の取得に失敗しました。')
  } finally {
    detailLoading.value = false
  }
}

const selectTemplate = async (id) => {
  await router.replace({ path: route.path, query: { ...route.query, id: String(id) } })
  await loadTemplateDetail(id)
}

const startNewTemplate = async () => {
  if (route.query.id) {
    await router.replace({ path: route.path, query: {} })
  }
  isListHidden.value = true
  selectedTemplateId.value = null
  form.value = createEmptyForm()
  productSearch.value = ''
  selectedProductLabel.value = ''
}

const toggleTemplateList = () => {
  isListHidden.value = !isListHidden.value
}

const validateForm = () => {
  if (!form.value.line) {
    alert('ラインは必須です。')
    return false
  }
  if (!form.value.process) {
    alert('工程は必須です。')
    return false
  }
  if (!form.value.product) {
    alert('製品を候補から選択してください。')
    return false
  }
  return true
}

const saveTemplateInternal = async () => {
  const data = buildFormData()
  let response
  if (form.value.id) {
    response = await api.productChecksheets.updateTemplate(form.value.id, data)
  } else {
    response = await api.productChecksheets.createTemplate(data)
  }
  const savedId = response.data?.id
  await loadTemplateList()
  if (savedId) await loadTemplateDetail(savedId)
  return savedId
}

const saveTemplate = async () => {
  if (!canEditFields.value) return
  if (!validateForm()) return
  saving.value = true
  try {
    await saveTemplateInternal()
    alert('保存しました。')
  } catch (error) {
    console.error('保存に失敗:', error)
    alert(`保存に失敗しました: ${error.response?.data?.detail || error.message}`)
  } finally {
    saving.value = false
  }
}

const submitForReview = () => {
  if (!form.value.id || !canSubmitForReview.value) return
  if (!validateForm()) return
  submitComment.value = ''
  submitDialogVisible.value = true
}

const cancelSubmit = () => {
  submitDialogVisible.value = false
  submitComment.value = ''
}

const confirmSubmitForReview = async () => {
  if (!form.value.id) return
  submitDialogVisible.value = false
  actionLoading.value = true
  try {
    const savedId = await saveTemplateInternal()
    const targetId = savedId || form.value.id
    await api.productChecksheets.submitForReview(targetId, submitComment.value)
    await loadTemplateList()
    await loadTemplateDetail(targetId)
    submitComment.value = ''
    alert('確認依頼を登録しました。')
  } catch (error) {
    console.error('確認依頼に失敗:', error)
    alert('確認依頼に失敗しました。')
  } finally {
    actionLoading.value = false
  }
}

const completeReview = async () => {
  if (!form.value.id || !canReview.value) return
  const label = reviewActionLabel.value
  const ok = window.confirm(`${label}にします。よろしいですか？`)
  if (!ok) return
  actionLoading.value = true
  try {
    await api.productChecksheets.review(form.value.id)
    await loadTemplateList()
    await loadTemplateDetail(form.value.id)
    alert(`${label}を登録しました。`)
  } catch (error) {
    console.error('確認完了に失敗:', error)
    alert('確認完了に失敗しました。')
  } finally {
    actionLoading.value = false
  }
}

const approveTemplate = async () => {
  if (!form.value.id || !canApprove.value) return
  const ok = window.confirm('部長承認します。よろしいですか？')
  if (!ok) return
  actionLoading.value = true
  try {
    await api.productChecksheets.approve(form.value.id)
    await loadTemplateList()
    await loadTemplateDetail(form.value.id)
    alert('部長承認しました。')
  } catch (error) {
    console.error('承認に失敗:', error)
    alert('承認に失敗しました。')
  } finally {
    actionLoading.value = false
  }
}

const rejectTemplate = () => {
  if (!form.value.id || !canReject.value) return
  rejectComment.value = form.value.rejection_comment || ''
  rejectDialogVisible.value = true
}

const cancelReject = () => {
  rejectDialogVisible.value = false
  rejectComment.value = ''
}

const confirmReject = async () => {
  if (!form.value.id) return
  rejectDialogVisible.value = false
  actionLoading.value = true
  try {
    await api.productChecksheets.reject(form.value.id, rejectComment.value)
    await loadTemplateList()
    await loadTemplateDetail(form.value.id)
    rejectComment.value = ''
    alert('差戻ししました。')
  } catch (error) {
    console.error('差戻しに失敗:', error)
    alert('差戻しに失敗しました。')
  } finally {
    actionLoading.value = false
  }
}

const reviseTemplate = async () => {
  if (!form.value.id || !canRevise.value) return
  const ok = window.confirm(
    `v${form.value.version} を基に改訂版（v${form.value.version + 1}）を作成します。よろしいですか？`
  )
  if (!ok) return
  actionLoading.value = true
  try {
    const response = await api.productChecksheets.revise(form.value.id)
    const newId = response.data?.id
    await loadTemplateList()
    if (newId) await loadTemplateDetail(newId)
    alert(`改訂版（v${response.data?.version}）を作成しました。`)
  } catch (error) {
    console.error('改訂に失敗:', error)
    alert(error.response?.data?.detail || '改訂に失敗しました。')
  } finally {
    actionLoading.value = false
  }
}

const downloadPreviewPdf = async () => {
  if (!form.value.id) return
  pdfLoading.value = true
  try {
    const res = await api.productChecksheets.previewPdf(form.value.id)
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `checksheet_template_${form.value.id}.pdf`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('PDF出力に失敗:', error)
    alert('PDF出力に失敗しました。台紙画像が設定されているか確認してください。')
  } finally {
    pdfLoading.value = false
  }
}

watch(
  () => route.query.id,
  async (nextId) => {
    const numericId = Number(nextId || 0)
    if (!numericId || numericId === Number(selectedTemplateId.value || 0)) return
    const exists = templates.value.some((item) => Number(item.id) === numericId)
    if (!exists) return
    await loadTemplateDetail(numericId)
  }
)

watch(() => form.value.line, () => {
  form.value.process = ''
  form.value.product = ''
  productSearch.value = ''
  selectedProductLabel.value = ''
  productSuggestions.value = []
})

onMounted(async () => {
  if (!canView.value) return
  await loadMasters()
  await loadTemplateList()

  const routeTemplateId = Number(route.query.id || 0)
  if (routeTemplateId && templates.value.some((item) => Number(item.id) === routeTemplateId)) {
    await loadTemplateDetail(routeTemplateId)
  } else if (templates.value.length) {
    await loadTemplateDetail(templates.value[0].id)
  } else {
    await startNewTemplate()
  }
})
</script>

<style scoped>
.checksheet-master {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  color: #111827;
  font-family: 'Meiryo', 'Yu Gothic UI', 'Yu Gothic', sans-serif;
  font-size: 14px;
  font-weight: 400;
  letter-spacing: 0.02em;
}
.master-layout {
  display: grid;
  grid-template-columns: 34% 1fr;
  gap: 12px;
  min-height: 0;
}
.master-layout.create-mode {
  grid-template-columns: 1fr;
}
.panel {
  background: #fff;
  border: 1px solid #d5d8dc;
  border-radius: 6px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.panel-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}
.list-filter-bar {
  display: flex;
  gap: 8px;
  padding: 6px 0 8px;
  flex-wrap: wrap;
}
.list-filter-input {
  flex: 1 1 120px;
  min-width: 100px;
  padding: 4px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 13px;
}
.list-filter-select {
  flex: 0 0 auto;
  padding: 4px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 13px;
}
.required-mark {
  color: #dc2626;
  font-size: 12px;
  margin-left: 2px;
}
.table-wrap {
  overflow: auto;
  border: 1px solid #dde2ea;
  border-radius: 4px;
}
.data-table.compact th,
.data-table.compact td {
  padding: 4px 6px;
  font-size: 14px;
  line-height: 1.45;
  vertical-align: top;
  color: #0f172a;
  letter-spacing: 0.02em;
}
.data-table.compact th { font-weight: 700; }
.data-table.compact td { font-weight: 400; }
.data-table.compact tbody tr { cursor: pointer; }
.data-table.compact tbody tr.selected { background: #e7f0ff; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 6px 8px; border-bottom: 1px solid #edf1f5; text-align: left; }
.data-table th { background: #f7f9fb; font-size: 13px; }
.status-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.status-chip {
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid transparent;
}
.status-chip.draft { background: #eef2ff; border-color: #c7d2fe; color: #3730a3; }
.status-chip.review { background: #fff4e5; border-color: #f5d19b; color: #9a5c00; }
.status-chip.approve { background: #eaf7ff; border-color: #8ecdf3; color: #0c4a6e; }
.status-chip.ok { background: #e9f7ef; border-color: #9fd9b4; color: #166534; }
.status-chip.danger { background: #fdecec; border-color: #f7b1b1; color: #991b1b; }
.status-meta { font-size: 14px; font-weight: 500; color: #334155; }
.status-date { font-size: 12px; font-weight: 400; color: #64748b; }
.form-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(140px, 1fr));
  gap: 8px;
}
.form-grid .wide { grid-column: span 2; }
.form-grid label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: #334155;
  font-weight: 500;
}
.form-grid input, .form-grid select, .form-grid textarea {
  padding: 5px 7px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 13px;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
}
.form-grid input:disabled, .form-grid select:disabled, .form-grid textarea:disabled {
  background: #f8fafc;
  color: #64748b;
}
.check-line {
  flex-direction: row !important;
  align-items: center;
  gap: 6px !important;
}
.sub-section-title {
  margin: 4px 0 0;
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  padding-top: 8px;
  border-top: 1px solid #edf1f5;
}
.autocomplete { position: relative; }
.suggestions {
  position: absolute;
  z-index: 20;
  left: 0; right: 0;
  top: calc(100% + 4px);
  max-height: 280px;
  overflow: auto;
  border: 1px solid #cfd6df;
  border-radius: 6px;
  background: #fff;
  box-shadow: 0 8px 20px rgba(15,23,42,0.14);
}
.suggestion {
  width: 100%;
  border: 0;
  border-bottom: 1px solid #edf1f5;
  background: #fff;
  padding: 8px 10px;
  display: grid;
  gap: 2px;
  text-align: left;
  cursor: pointer;
}
.suggestion:hover { background: #eff6ff; }
.suggestion span { font-weight: 700; color: #111827; }
.suggestion small { color: #4b5563; }
.suggestion-note { margin: 0; padding: 10px; color: #6b7280; }
.rejection-box {
  background: #fef2f2;
  border: 1px solid #fca5a5;
  border-radius: 6px;
  padding: 10px 14px;
  color: #991b1b;
  font-size: 13px;
}
.workflow-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 0;
  border-top: 1px solid #edf1f5;
  border-bottom: 1px solid #edf1f5;
}
.item-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.item-section h4 { margin: 0; font-size: 15px; font-weight: 700; color: #0f172a; }
.section-header { display: flex; justify-content: space-between; align-items: center; }
.no-data { color: #6b7280; padding: 8px 0; font-size: 13px; }
.page-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.page-title { margin: 0; font-size: 20px; font-weight: 700; color: #0f172a; }
.page-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.btn-primary, .btn-secondary, .btn-sm, .btn-approve, .btn-review, .btn-danger, .btn-revise {
  border-radius: 6px;
  padding: 7px 14px;
  cursor: pointer;
  border: 1px solid transparent;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
}
.btn-sm { padding: 4px 10px; font-size: 12px; }
.btn-primary { background: #2563eb; color: #fff; border-color: #2563eb; }
.btn-primary:disabled { background: #93c5fd; border-color: #93c5fd; cursor: not-allowed; }
.btn-secondary { background: #fff; color: #2563eb; border-color: #2563eb; }
.btn-approve { background: #059669; color: #fff; border-color: #059669; }
.btn-approve:disabled { background: #6ee7b7; border-color: #6ee7b7; cursor: not-allowed; }
.btn-review { background: #d97706; color: #fff; border-color: #d97706; }
.btn-review:disabled { background: #fcd34d; border-color: #fcd34d; cursor: not-allowed; }
.btn-danger { background: #dc2626; color: #fff; border-color: #dc2626; }
.btn-danger:disabled { background: #fca5a5; border-color: #fca5a5; cursor: not-allowed; }
.btn-revise { background: #7c3aed; color: #fff; border-color: #7c3aed; }
.btn-revise:disabled { background: #c4b5fd; border-color: #c4b5fd; cursor: not-allowed; }
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15,23,42,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.modal-panel {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 20px 60px rgba(15,23,42,0.25);
  max-width: 520px;
  width: 100%;
}
.reject-modal { padding: 0; }
.modal-header { padding: 16px 20px 8px; }
.reject-modal-body { padding: 0 20px 16px; }
.reject-label { display: block; margin-bottom: 6px; font-weight: 600; font-size: 14px; color: #334155; }
.reject-textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 14px;
  resize: vertical;
}
.reject-modal-footer { padding: 10px 20px 16px; display: flex; justify-content: flex-end; gap: 8px; }
@media (max-width: 960px) {
  .master-layout { grid-template-columns: 1fr; }
  .form-grid { grid-template-columns: 1fr 1fr; }
}
</style>
