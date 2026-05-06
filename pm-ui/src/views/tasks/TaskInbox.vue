<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">タスク受信箱</h1>
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
            <option value="DONE">完了</option>
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
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import api from "@/api/client"

const router = useRouter()
const loading = ref(false)
const allRows = ref([])
const filters = ref({
  status: "PENDING",
  module_code: "",
  task_category: "",
  task_type: "",
})

const purchaseTaskTypeMap = {
  CREATE_PROPOSAL: "発注提案書作成",
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

const statusMap = {
  PENDING: "未対応",
  DONE: "完了",
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

const normalizePurchaseTask = (row) => {
  const targetSecondary = [row.supplier_code, row.supplier_name].filter(Boolean).join(" - ")
  const actionLabel =
    row.task_type === "CREATE_ORDER_PDF" || row.task_type === "SEND_TO_SUPPLIER" ? "注文書へ" : "提案書へ"
  return {
    row_key: `purchase-${row.id}`,
    module_code: "PURCHASE",
    module_label: "購買",
    task_category: "PURCHASE_ORDER",
    task_category_label: "発注提案",
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

    const [purchaseResponse, qualityResponse] = await Promise.all([
      api.purchaseOrderProposals.listTasks(params),
      api.qualityEquipmentInspections.listTasks(params),
    ])

    const purchaseRows = Array.isArray(purchaseResponse.data)
      ? purchaseResponse.data.map(normalizePurchaseTask)
      : []
    const qualityRows = Array.isArray(qualityResponse.data)
      ? qualityResponse.data.map(normalizeQualityTask)
      : []
    allRows.value = [...purchaseRows, ...qualityRows]
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

