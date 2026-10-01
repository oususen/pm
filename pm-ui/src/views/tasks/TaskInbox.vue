<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">タスク受信箱 <DataSourceDialog title="タスク受信箱" :sources="dsSources" /></h1>
      <div class="page-actions">
        <button class="btn-primary" @click="fetchTasks" :disabled="loading">
          {{ loading ? "更新中..." : "更新" }}
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
            <option value="IN_PROGRESS">対応中</option>
            <option value="DONE">完了</option>
            <option value="REJECTED">却下</option>
            <option value="SKIPPED">スキップ</option>
          </select>
        </div>
        <div class="filter-field">
          <label>業務</label>
          <select v-model="filters.module_code">
            <option value="">すべて</option>
            <option v-for="option in moduleOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>
        <div class="filter-field">
          <label>類別</label>
          <select v-model="filters.task_category">
            <option value="">すべて</option>
            <option v-for="option in categoryOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>
        <div class="filter-field">
          <label>タスク種別</label>
          <select v-model="filters.task_type">
            <option value="">すべて</option>
            <option v-for="option in taskTypeOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
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
            <th>類別</th>
            <th>タスク種別</th>
            <th>状態</th>
            <th>対象</th>
            <th>補足</th>
            <th>期限</th>
            <th>作成日時</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in filteredRows" :key="row.row_key">
            <td>{{ row.module_label }}</td>
            <td>{{ row.task_category_label }}</td>
            <td>{{ row.task_type_label }}</td>
            <td>{{ statusLabel(row.status) }}</td>
            <td>{{ row.target_primary || "-" }}</td>
            <td>{{ row.target_secondary || "-" }}</td>
            <td>{{ row.due_date || "-" }}</td>
            <td>{{ formatDateTime(row.created_at) }}</td>
            <td>
              <button class="btn-sm" @click="openTask(row)">{{ row.action_label }}</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="!filteredRows.length && !loading" class="no-data">タスクはありません</div>
    </div>
    <UserRequestTaskDialog :task="selectedRequestTask" @close="selectedRequestTask = null" @changed="fetchTasks" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import api from "@/api/client"
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'
import UserRequestTaskDialog from '@/components/UserRequestTaskDialog.vue'

const dsSources = [
  { op: '読み取り', table: 't_task', desc: '各業務のタスク一覧取得（購買・品質・チェックシート）' },
  { op: '読み取り', table: 'accounts_approvaltask / accounts_approvalrequest', desc: '共通承認タスク一覧取得（材料発注など）' },
  { op: '読み取り・更新・削除', table: 'notifications_user_request_task', desc: 'システム管理者リクエストの一覧取得・状況変更・削除（システム管理者のみ）' },
]

const router = useRouter()
const loading = ref(false)
const allRows = ref([])
const selectedRequestTask = ref(null)
const filters = ref({
  status: "PENDING",
  module_code: "",
  task_category: "",
  task_type: "",
})

const purchaseTaskTypeMap = {
  CREATE_PROPOSAL: "外作・購入品注文書作成",
  CREATE_ORDER_PDF: "注文書作成",
  APPROVE_L2: "班長承認",
  APPROVE_L3: "係長承認",
  APPROVE_L4: "事業部長承認",
  SEND_TO_SUPPLIER: "購入先送信",
}

const qualityTaskTypeMap = {
  SUPERVISOR_REVIEW: "班長確認",
  CHIEF_REVIEW: "係長承認",
  MANAGER_APPROVE: "部長承認",
  CREATOR_FIX: "差戻し修正",
}

const approvalTaskTypeMap = {
  CREATOR_CREATE: "作成",
  REVIEWER1_REVIEW: "確認①",
  REVIEWER2_REVIEW: "確認②",
  APPROVER_APPROVE: "承認",
  CREATOR_FIX: "差戻し修正",
}

const statusMap = {
  PENDING: "未対応",
  IN_PROGRESS: "対応中",
  DONE: "完了",
  REJECTED: "却下",
  SKIPPED: "スキップ",
}

const statusLabel = (value) => statusMap[value] || value

const buildOptionList = (rows, keyName, labelName) => {
  const seen = new Set()
  const options = []
  rows.forEach((row) => {
    const value = String(row?.[keyName] || "").trim()
    if (!value || seen.has(value)) return
    seen.add(value)
    options.push({
      value,
      label: row?.[labelName] || value,
    })
  })
  return options
}

const moduleOptions = computed(() => buildOptionList(allRows.value, "module_code", "module_label"))
const categoryOptions = computed(() => buildOptionList(allRows.value, "task_category", "task_category_label"))
const taskTypeOptions = computed(() => buildOptionList(allRows.value, "task_type", "task_type_label"))

const filteredRows = computed(() => {
  return allRows.value.filter((row) => {
    if (filters.value.status && row.status !== filters.value.status) return false
    if (filters.value.module_code && row.module_code !== filters.value.module_code) return false
    if (filters.value.task_category && row.task_category !== filters.value.task_category) return false
    if (filters.value.task_type && row.task_type !== filters.value.task_type) return false
    return true
  })
})

const normalizeUserRequestTask = (row) => ({
  row_key: `user-request-${row.id}`,
  module_code: "USER_REQUEST",
  module_label: "リクエスト",
  task_category: "USER_REQUEST",
  task_category_label: "システム管理者リクエスト",
  task_type: row.request_type,
  task_type_label: row.request_type_label || row.request_type,
  status: row.status,
  due_date: "",
  created_at: row.created_at || "",
  target_primary: row.subject,
  target_secondary: `依頼者 ${row.requester_name || "-"}`,
  action_label: "内容を見る",
  navigate() {
    selectedRequestTask.value = row
  },
})

const normalizePurchaseTask = (row) => {
  const targetSecondary = [row.supplier_code, row.supplier_name].filter(Boolean).join(" - ")
  const actionLabel = "外作・購入品注文書へ"
  return {
    row_key: `purchase-${row.id}`,
    module_code: "PURCHASE",
    module_label: "購買",
    task_category: "PURCHASE_ORDER",
    task_category_label: "外作・購入品注文書",
    task_type: row.task_type,
    task_type_label: purchaseTaskTypeMap[row.task_type] || row.task_type,
    status: row.status,
    due_date: row.due_date || "",
    created_at: row.created_at || "",
    target_primary: row.proposal_no || `提案ID:${row.proposal}`,
    target_secondary: targetSecondary,
    action_label: actionLabel,
    navigate() {
      router.push(`/purchase/order-proposals/${row.proposal}`)
    },
  }
}

const normalizeQualityTask = (row) => {
  const title = row.template_title || "設備点検表"
  const version = row.template_version ? `版${row.template_version}` : ""
  return {
    row_key: `quality-${row.id}`,
    module_code: row.module_code || "QUALITY",
    module_label: row.module_label || "品質",
    task_category: row.task_category || "EQUIPMENT_INSPECTION",
    task_category_label: row.task_category_label || "設備点検表",
    task_type: row.task_type,
    task_type_label: qualityTaskTypeMap[row.task_type] || row.task_type,
    status: row.status,
    due_date: row.due_date || "",
    created_at: row.created_at || "",
    target_primary: [row.sheet_code, row.sheet_name].filter(Boolean).join(" "),
    target_secondary: [title, version].filter(Boolean).join(" / "),
    action_label: "点検表へ",
    navigate() {
      router.push({
        path: "/quality/equipment-inspection/master",
        query: { id: String(row.template || "") },
      })
    },
  }
}

const normalizeIntegratedCsTask = (row) => ({
  row_key: `ics-${row.id}`,
  module_code: "QUALITY",
  module_label: "品質",
  task_category: "INTEGRATED_CHECKSHEET",
  task_category_label: "工程一体CS",
  task_type: row.task_type,
  task_type_label: qualityTaskTypeMap[row.task_type] || row.task_type_display || row.task_type,
  status: row.status,
  due_date: row.due_date || "",
  created_at: row.created_at || "",
  target_primary: row.product_code || "",
  target_secondary: row.template_name || "",
  action_label: "製品チェックシートへ",
  navigate() {
    router.push({
      path: "/quality/product-checksheet/integrated/templates",
      query: { id: String(row.template_id || "") },
    })
  },
})

const normalizeList = (payload) => {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.results)) return payload.results
  return []
}

const normalizeApprovalTask = (request, task) => {
  const context = request.context || {}
  const period = [context.lock_start_date, context.lock_end_date].filter(Boolean).join(" ～ ")
  const category = request.route_config_item_key === "laser_material_order"
    ? "LASER_MATERIAL_ORDER"
    : request.route_config_item_key || "APPROVAL_REQUEST"
  const supplierLabel = context.supplier === "SATO" ? "佐藤商事" : context.supplier === "MEISEI" ? "名成鋼機" : ""
  const categoryLabel = request.route_config_item_key === "laser_material_order"
    ? `レーザ材料発注${supplierLabel ? `（${supplierLabel}）` : ""}`
    : request.route_config_name || "承認申請"
  return {
    row_key: `approval-${request.id}-${task.id}`,
    module_code: "APPROVAL",
    module_label: "承認",
    task_category: category,
    task_category_label: categoryLabel,
    task_type: task.task_type,
    task_type_label: approvalTaskTypeMap[task.task_type] || task.task_type,
    status: task.status,
    due_date: task.due_date || "",
    created_at: task.created_at || request.created_at || "",
    target_primary: request.route_config_item_key === "laser_material_order" && supplierLabel ? `${request.route_config_name || "承認申請"}（${supplierLabel}）` : request.route_config_name || "承認申請",
    target_secondary: period ? `注文書期間 ${period}` : `申請者 ${request.creator_name || "-"}`,
    action_label: request.route_config_item_key === "laser_material_order"
      ? "材料発注へ"
      : request.route_config_item_key === "consumable_dispatch_order" ? "注文書へ" : "承認へ",
    ...(request.route_config_item_key === "consumable_dispatch_order" && context.order_number
      ? { target_secondary: `${context.supplier_name || ""} ${context.order_number}（申請者 ${request.creator_name || "-"}）` }
      : {}),
    navigate() {
      if (request.route_config_item_key === "consumable_dispatch_order") {
        router.push({ path: "/consumables/dispatch-orders", query: { id: context.dispatch_order_id || "" } })
        return
      }
      if (request.route_config_item_key === "laser_material_order") {
        router.push({
          path: "/production/plan-input",
          query: {
            tab: "laser",
            start_date: context.start_date || "",
          },
        })
      }
    },
  }
}

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
    if (filters.value.status) {
      params.status = filters.value.status
    }
    const approvalParams = { assigned_to_me: true }
    if (filters.value.status) {
      approvalParams.task_status = filters.value.status
    }

    // システム管理者リクエストは、システム管理者にだけ表示する（他のユーザーは取得しない）
    const isSystemAdmin = Boolean(authState.user?.profile?.is_system_admin)
    const [purchaseResponse, qualityResponse, icsResponse, approvalResponse, requestResponse] = await Promise.all([
      api.purchaseOrderProposals.listTasks(params),
      api.qualityEquipmentInspections.listTasks(params),
      api.integratedChecksheets.listTasks(params),
      api.accounts.getApprovalRequests(approvalParams),
      isSystemAdmin ? api.userRequests.listTasks(params) : Promise.resolve({ data: [] }),
    ])

    const purchaseRows = normalizeList(purchaseResponse.data).map(normalizePurchaseTask)
    const qualityRows = normalizeList(qualityResponse.data).map(normalizeQualityTask)
    const icsRows = normalizeList(icsResponse.data).map(normalizeIntegratedCsTask)
    const currentUserId = Number(authState.user?.id || 0)
    const approvalRows = normalizeList(approvalResponse.data).flatMap((request) =>
      normalizeList(request.tasks)
        .filter((task) => Number(task.assigned_to) === currentUserId)
        .map((task) => normalizeApprovalTask(request, task)),
    )
    const requestRows = normalizeList(requestResponse.data).map(normalizeUserRequestTask)
    allRows.value = [...purchaseRows, ...qualityRows, ...icsRows, ...approvalRows, ...requestRows]
  } catch (error) {
    console.error("タスク一覧取得に失敗:", error)
    allRows.value = []
  } finally {
    loading.value = false
  }
}

const resetFilters = async () => {
  filters.value = {
    status: "PENDING",
    module_code: "",
    task_category: "",
    task_type: "",
  }
  await fetchTasks()
}

const openTask = (row) => {
  if (!row || typeof row.navigate !== "function") return
  row.navigate()
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
  min-width: 180px;
}

.filter-actions {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}
</style>
