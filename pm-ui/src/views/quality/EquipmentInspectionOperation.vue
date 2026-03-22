<template>
  <div class="page-container inspection-operation" v-if="canView">
    <div class="page-header">
      <h2 class="page-title">点検実施</h2>
      <div class="page-actions">
        <button class="btn-secondary" @click="loadTemplates" :disabled="loadingOptions || loadingRecord">
          テンプレート更新
        </button>
        <button class="btn-secondary" @click="reloadRecord" :disabled="loadingRecord || !selectedSheetCode || !selectedDate">
          再読込
        </button>
      </div>
    </div>

    <section class="panel filter-panel">
      <label>
        設備
        <select v-model="selectedSheetCode" :disabled="loadingOptions || loadingRecord">
          <option value="">選択してください</option>
          <option v-for="option in templateOptions" :key="option.sheet_code" :value="option.sheet_code">
            {{ option.sheet_code }} - {{ option.sheet_name }} (v{{ option.version }})
          </option>
        </select>
      </label>
      <label>
        点検日
        <input type="date" v-model="selectedDate" :disabled="loadingRecord" />
      </label>
      <label>
        区分
        <select v-model="sectionType" :disabled="loadingRecord">
          <option value="DAILY">日次点検</option>
          <option value="QUARTERLY">定期実測</option>
        </select>
      </label>
      <div class="header-status">
        <div>状態: <strong>{{ statusLabel(form.status) }}</strong></div>
        <div>実施者: <strong>{{ form.operator_name || "-" }}</strong></div>
        <div>総合判定: <strong>{{ form.overall_result || "-" }}</strong></div>
      </div>
    </section>

    <section class="panel" v-if="selectedSheetCode">
      <div class="record-summary">
        <div>
          <div class="summary-title">{{ form.template_title || currentTemplate?.title || "-" }}</div>
          <div class="summary-meta">
            設備: {{ form.sheet_code || selectedSheetCode }} {{ form.sheet_name || currentTemplate?.sheet_name || "" }}
          </div>
          <div class="summary-meta">
            使用テンプレート: v{{ form.template_version || currentTemplate?.version || "-" }}
          </div>
        </div>
        <div class="summary-side">
          <div>必須未入力: {{ form.missing_required_count ?? 0 }}</div>
          <div>NG件数: {{ form.ng_count ?? 0 }}</div>
          <div v-if="form.completed_at">完了日時: {{ formatDateTime(form.completed_at) }}</div>
        </div>
      </div>

      <div v-if="isLocked" class="locked-box">
        この月は月間班長確認済みのため、点検結果は更新できません。
      </div>

      <div class="memo-area">
        <label>
          備考
          <textarea v-model="form.memo" rows="2" :disabled="!canEditRecord" />
        </label>
      </div>

      <div class="table-wrap">
        <table class="data-table compact">
          <thead>
            <tr>
              <th class="col-no">No</th>
              <th>点検項目</th>
              <th>規格</th>
              <th>方法</th>
              <th class="col-value">記録</th>
              <th class="col-judge">判定</th>
              <th>コメント</th>
              <th class="col-ref">付表</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="result in form.results"
              :key="result.local_key"
              :class="{ 'row-ng': result.judgement === 'NG' }"
            >
              <td class="col-no">{{ result.inspection_no || "-" }}</td>
              <td>
                <div class="item-name">{{ result.item_name }}</div>
                <div class="item-meta">
                  {{ result.frequency || "-" }} / {{ recordTypeLabel(result.record_type) }}
                  <span v-if="result.unit"> / {{ result.unit }}</span>
                </div>
              </td>
              <td>{{ result.standard || "-" }}</td>
              <td>{{ result.method || "-" }}</td>
              <td class="col-value">
                <input
                  v-if="result.record_type === 'NUMERIC'"
                  type="number"
                  step="0.001"
                  v-model="result.numeric_value"
                  :class="{ 'input-invalid': isNumericOutOfSpec(result) }"
                  :disabled="!canEditRecord"
                  @input="handleNumericInput(result)"
                />
                <textarea
                  v-else-if="result.record_type === 'TEXT'"
                  v-model="result.text_value"
                  rows="2"
                  :disabled="!canEditRecord"
                />
                <div v-else class="check-caption">チェック項目</div>
              </td>
              <td class="col-judge">
                <div class="judge-buttons">
                  <button
                    type="button"
                    class="judge-button"
                    :class="{ active: result.judgement === 'OK', ok: result.judgement === 'OK' }"
                    :disabled="!canEditRecord || !canSelectOk(result)"
                    :title="okButtonTitle(result)"
                    @click="setJudgement(result, 'OK')"
                  >
                    OK
                  </button>
                  <button
                    type="button"
                    class="judge-button"
                    :class="{ active: result.judgement === 'NG', ng: result.judgement === 'NG' }"
                    :disabled="!canEditRecord"
                    @click="setJudgement(result, 'NG')"
                  >
                    NG
                  </button>
                </div>
              </td>
              <td>
                <textarea v-model="result.comment" rows="2" :disabled="!canEditRecord" />
              </td>
              <td class="col-ref">
                <button
                  class="btn-secondary btn-sm"
                  @click="openAttachmentViewer(result)"
                  :disabled="!result.reference_attachments?.length"
                >
                  参照{{ result.reference_attachments?.length ? `(${result.reference_attachments.length})` : "" }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="!form.results.length && !loadingRecord" class="no-data">
        対象項目がありません。
      </div>

      <div class="record-actions">
        <button class="btn-primary" @click="saveRecord('DRAFT')" :disabled="!canEditRecord || saving">
          下書き保存
        </button>
        <button class="btn-approve" @click="saveRecord('COMPLETED')" :disabled="!canEditRecord || saving">
          点検完了
        </button>
      </div>
    </section>

    <div v-if="attachmentViewer.visible" class="modal-backdrop" @click.self="closeAttachmentViewer">
      <div class="modal-panel">
        <div class="modal-header">
          <div>
            <h3 class="panel-title">付表参照</h3>
            <div class="summary-meta">{{ attachmentViewer.itemName }}</div>
          </div>
          <button class="btn-secondary btn-sm" @click="closeAttachmentViewer">閉じる</button>
        </div>

        <div v-if="attachmentViewer.attachments.length" class="attachment-list">
          <div v-for="attachment in attachmentViewer.attachments" :key="attachment.local_key" class="attachment-card">
            <div class="attachment-card-title">{{ attachment.title || "付表" }}</div>
            <div v-if="attachment.image_url" class="attachment-image-wrap">
              <img :src="attachment.image_url" :alt="attachment.title || attachmentViewer.itemName" />
            </div>
            <div class="attachment-text"><strong>補足説明:</strong> {{ attachment.description || "-" }}</div>
            <div class="attachment-text"><strong>確認ポイント:</strong> {{ attachment.check_point || "-" }}</div>
            <div class="attachment-text"><strong>OK例:</strong> {{ attachment.ok_example || "-" }}</div>
            <div class="attachment-text"><strong>NG例:</strong> {{ attachment.ng_example || "-" }}</div>
          </div>
        </div>
        <div v-else class="no-data">付表はありません。</div>
      </div>
    </div>
  </div>

  <div class="page-container" v-else>
    <h2 class="page-title">点検実施</h2>
    <p class="no-data">品質の閲覧権限がありません。</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import api from "@/api/client"
import { authState } from "@/auth"
import { hasPermission } from "@/router"

const route = useRoute()
const router = useRouter()

const loadingOptions = ref(false)
const loadingRecord = ref(false)
const saving = ref(false)
const templateOptions = ref([])
const currentTemplate = ref(null)
const isLocked = ref(false)

const selectedSheetCode = ref(String(route.query.sheet_code || ""))
const selectedDate = ref(String(route.query.date || new Date().toISOString().slice(0, 10)))
const sectionType = ref(String(route.query.section_type || "DAILY").toUpperCase())
// 工程/ラインからの絞り込み用（実績入力画面から渡される）
const filterProcessId = ref(route.query.process_id ? String(route.query.process_id) : null)
const filterLineId = ref(route.query.line_id ? String(route.query.line_id) : null)

const createAttachment = (raw = {}) => ({
  local_key: raw.local_key || `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
  title: raw.title || "",
  description: raw.description || "",
  check_point: raw.check_point || "",
  ok_example: raw.ok_example || "",
  ng_example: raw.ng_example || "",
  image_url: raw.image_url || "",
})

const createEmptyForm = () => ({
  id: null,
  template: null,
  sheet_code: "",
  sheet_name: "",
  template_title: "",
  template_version: 1,
  operation_date: "",
  section_type: "DAILY",
  operator_name: "",
  status: "DRAFT",
  overall_result: "",
  memo: "",
  completed_at: "",
  result_count: 0,
  ng_count: 0,
  missing_required_count: 0,
  results: [],
})

const form = ref(createEmptyForm())
const attachmentViewer = ref({
  visible: false,
  itemName: "",
  attachments: [],
})

const canView = computed(() => {
  return hasPermission(authState.user, "quality", "view") || hasPermission(authState.user, "quality", "edit")
})
const canEdit = computed(() => hasPermission(authState.user, "quality", "edit"))
const canEditRecord = computed(() => canEdit.value && !isLocked.value)

const statusLabel = (value) => {
  if (value === "COMPLETED") return "完了"
  return "下書き"
}

const recordTypeLabel = (value) => {
  if (value === "NUMERIC") return "数値"
  if (value === "TEXT") return "文字"
  return "チェック"
}

const formatDateTime = (value) => {
  if (!value) return "-"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString("ja-JP")
}

const normalizeNumericText = (value) => {
  const raw = String(value ?? "").trim()
  if (!raw) return ""
  return raw.replace(/[０-９．，－＋]/g, (char) => {
    const map = {
      "０": "0",
      "１": "1",
      "２": "2",
      "３": "3",
      "４": "4",
      "５": "5",
      "６": "6",
      "７": "7",
      "８": "8",
      "９": "9",
      "．": ".",
      "，": ",",
      "－": "-",
      "＋": "+",
    }
    return map[char] || char
  })
}

const toNumericValue = (value) => {
  if (value === "" || value === null || value === undefined) return null
  const normalized = normalizeNumericText(value).replace(/,/g, "")
  if (!normalized) return null
  const parsed = Number(normalized)
  return Number.isFinite(parsed) ? parsed : null
}

const normalizeRuleText = (value) => {
  const normalized = normalizeNumericText(value)
  return normalized.replace(/\s+/g, "")
}

const parseNumericRuleText = (value) => {
  const text = normalizeRuleText(value)
  if (!text) return null

  const rangeMatch = text.match(/([-+]?\d+(?:\.\d+)?)±([-+]?\d+(?:\.\d+)?)/)
  if (rangeMatch) {
    const center = toNumericValue(rangeMatch[1])
    const tolerance = toNumericValue(rangeMatch[2])
    if (center !== null && tolerance !== null) {
      return {
        type: "range",
        min: center - Math.abs(tolerance),
        max: center + Math.abs(tolerance),
      }
    }
  }

  const minMatch = text.match(/([-+]?\d+(?:\.\d+)?)以上/)
  if (minMatch) {
    const minimum = toNumericValue(minMatch[1])
    if (minimum !== null) {
      return { type: "min", value: minimum }
    }
  }

  const maxMatch = text.match(/([-+]?\d+(?:\.\d+)?)以下/)
  if (maxMatch) {
    const maximum = toNumericValue(maxMatch[1])
    if (maximum !== null) {
      return { type: "max", value: maximum }
    }
  }

  return null
}

const parseNumericRule = (result) => {
  if (!result || result.record_type !== "NUMERIC") return null
  for (const candidate of [result.criteria, result.standard]) {
    const rule = parseNumericRuleText(candidate)
    if (rule) return rule
  }
  return null
}

const numericValueWithinRule = (result) => {
  if (!result || result.record_type !== "NUMERIC") return null
  const numericValue = toNumericValue(result.numeric_value)
  if (numericValue === null) return null
  const rule = parseNumericRule(result)
  if (!rule) return null
  if (rule.type === "min") return numericValue >= rule.value
  if (rule.type === "max") return numericValue <= rule.value
  if (rule.type === "range") return numericValue >= rule.min && numericValue <= rule.max
  return null
}

const isNumericOutOfSpec = (result) => numericValueWithinRule(result) === false

const canSelectOk = (result) => {
  if (!result || result.record_type !== "NUMERIC") return true
  if (toNumericValue(result.numeric_value) === null) return false
  return numericValueWithinRule(result) !== false
}

const okButtonTitle = (result) => {
  if (!result || result.record_type !== "NUMERIC") return ""
  if (toNumericValue(result.numeric_value) === null) {
    return "測定値を入力してください。"
  }
  if (numericValueWithinRule(result) === false) {
    return "測定値が規格を満たしていないためOKにできません。"
  }
  return ""
}

const normalizeRecord = (raw) => ({
  id: raw.id || null,
  template: raw.template || null,
  sheet_code: raw.sheet_code || "",
  sheet_name: raw.sheet_name || "",
  template_title: raw.template_title || "",
  template_version: Number(raw.template_version || 1),
  operation_date: raw.operation_date || selectedDate.value,
  section_type: raw.section_type || sectionType.value,
  operator_name: raw.operator_name || "",
  status: raw.status || "DRAFT",
  overall_result: raw.overall_result || "",
  memo: raw.memo || "",
  completed_at: raw.completed_at || "",
  result_count: Number(raw.result_count || 0),
  ng_count: Number(raw.ng_count || 0),
  missing_required_count: Number(raw.missing_required_count || 0),
  results: Array.isArray(raw.results)
    ? raw.results.map((result) => ({
        local_key: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        id: result.id || null,
        item: result.item || null,
        display_order: Number(result.display_order || 1),
        inspection_no: result.inspection_no ?? null,
        item_name: result.item_name || "",
        standard: result.standard || "",
        frequency: result.frequency || "",
        method: result.method || "",
        record_type: result.record_type || "CHECK",
        unit: result.unit || "",
        criteria: result.criteria || "",
        is_required: Boolean(result.is_required),
        numeric_value: result.numeric_value ?? "",
        text_value: result.text_value || "",
        judgement: result.judgement || "",
        comment: result.comment || "",
        reference_attachments: Array.isArray(result.reference_attachments)
          ? result.reference_attachments.map((attachment) => createAttachment(attachment))
          : [],
      }))
    : [],
})

const buildPayload = (targetStatus) => ({
  template: form.value.template || currentTemplate.value?.id || null,
  sheet_code: String(form.value.sheet_code || selectedSheetCode.value || "").trim(),
  sheet_name: String(form.value.sheet_name || currentTemplate.value?.sheet_name || "").trim(),
  template_title: String(form.value.template_title || currentTemplate.value?.title || "").trim(),
  template_version: Number(form.value.template_version || currentTemplate.value?.version || 1),
  operation_date: selectedDate.value,
  section_type: sectionType.value,
  status: targetStatus,
  memo: String(form.value.memo || ""),
  results: form.value.results.map((result) => ({
    item: result.item || null,
    display_order: Number(result.display_order || 1),
    inspection_no: result.inspection_no ?? null,
    item_name: String(result.item_name || ""),
    standard: String(result.standard || ""),
    frequency: String(result.frequency || ""),
    method: String(result.method || ""),
    record_type: result.record_type || "CHECK",
    unit: String(result.unit || ""),
    criteria: String(result.criteria || ""),
    is_required: Boolean(result.is_required),
    numeric_value: result.record_type === "NUMERIC" && result.numeric_value !== "" ? result.numeric_value : null,
    text_value: result.record_type === "TEXT" ? String(result.text_value || "") : "",
    judgement: String(result.judgement || "").trim().toUpperCase(),
    comment: String(result.comment || ""),
  })),
})

const syncQuery = () => {
  router.replace({
    query: {
      ...route.query,
      sheet_code: selectedSheetCode.value || undefined,
      date: selectedDate.value || undefined,
      section_type: sectionType.value || undefined,
    },
  })
}

const loadTemplates = async () => {
  loadingOptions.value = true
  try {
    const fetchOptions = async (params) => {
      const response = await api.qualityEquipmentInspections.list({ for_operation: true, ...params })
      return response.data?.results || response.data || []
    }

    let rows = []
    if (filterProcessId.value) {
      // 工程に紐付く設備を優先
      rows = await fetchOptions({ process_id: filterProcessId.value })
      // 該当なければラインにフォールバック
      if (!rows.length && filterLineId.value) {
        rows = await fetchOptions({ line_id: filterLineId.value })
      }
    } else if (filterLineId.value) {
      rows = await fetchOptions({ line_id: filterLineId.value })
    } else {
      rows = await fetchOptions({})
    }

    templateOptions.value = [...rows].sort((a, b) => {
      return String(a.sheet_code || "").localeCompare(String(b.sheet_code || ""), "ja")
    })
    if (!selectedSheetCode.value && templateOptions.value.length) {
      selectedSheetCode.value = templateOptions.value[0].sheet_code
    }
  } catch (error) {
    console.error("承認済みテンプレート取得に失敗:", error)
    alert("承認済みテンプレートの取得に失敗しました。")
  } finally {
    loadingOptions.value = false
  }
}

const loadPreparedRecord = async () => {
  if (!selectedSheetCode.value || !selectedDate.value) return
  loadingRecord.value = true
  try {
    const response = await api.qualityEquipmentInspections.prepareRecord({
      sheet_code: selectedSheetCode.value,
      operation_date: selectedDate.value,
      section_type: sectionType.value,
    })
    currentTemplate.value = response.data?.current_template || null
    isLocked.value = Boolean(response.data?.is_locked)
    form.value = normalizeRecord(response.data?.record || createEmptyForm())
  } catch (error) {
    console.error("点検実施データ準備に失敗:", error)
    currentTemplate.value = null
    form.value = createEmptyForm()
    alert("点検実施データの取得に失敗しました。")
  } finally {
    loadingRecord.value = false
  }
}

const reloadRecord = async () => {
  await loadPreparedRecord()
}

const setJudgement = (result, value) => {
  if (!canEditRecord.value || !result) return
  if (String(value || "").trim().toUpperCase() === "OK" && !canSelectOk(result)) return
  result.judgement = String(value || "").trim().toUpperCase()
}

const handleNumericInput = (result) => {
  if (!result || result.record_type !== "NUMERIC") return
  if (result.judgement === "OK" && !canSelectOk(result)) {
    result.judgement = ""
  }
}

const saveRecord = async (targetStatus) => {
  if (!canEditRecord.value) return
  if (!selectedSheetCode.value || !selectedDate.value) {
    alert("設備と点検日を選択してください。")
    return
  }

  saving.value = true
  try {
    const payload = buildPayload(targetStatus)
    if (form.value.id) {
      await api.qualityEquipmentInspections.updateRecord(form.value.id, payload)
    } else {
      await api.qualityEquipmentInspections.createRecord(payload)
    }
    await loadPreparedRecord()
    alert(targetStatus === "COMPLETED" ? "点検完了を登録しました。" : "下書きを保存しました。")
  } catch (error) {
    console.error("点検実施保存に失敗:", error)
    const detail = error.response?.data?.results
    if (Array.isArray(detail) && detail.length) {
      alert(detail.join("\n"))
      return
    }
    alert(error.response?.data?.detail || "保存に失敗しました。")
  } finally {
    saving.value = false
  }
}

const openAttachmentViewer = (result) => {
  attachmentViewer.value = {
    visible: true,
    itemName: result.item_name || "",
    attachments: Array.isArray(result.reference_attachments) ? result.reference_attachments : [],
  }
}

const closeAttachmentViewer = () => {
  attachmentViewer.value = {
    visible: false,
    itemName: "",
    attachments: [],
  }
}

watch([selectedSheetCode, selectedDate, sectionType], async () => {
  if (!canView.value) return
  syncQuery()
  if (selectedSheetCode.value && selectedDate.value) {
    await loadPreparedRecord()
  }
})

onMounted(async () => {
  if (!canView.value) return
  await loadTemplates()
  if (selectedSheetCode.value && selectedDate.value) {
    await loadPreparedRecord()
  }
})
</script>

<style scoped>
.inspection-operation {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.panel {
  background: #fff;
  border: 1px solid #d5d8dc;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.filter-panel {
  display: grid;
  grid-template-columns: repeat(4, minmax(160px, 1fr));
  gap: 10px;
  align-items: end;
}
.filter-panel label,
.memo-area label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: #334155;
}
.header-status {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: #0f172a;
}
.record-summary {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.summary-title {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}
.summary-meta {
  margin-top: 4px;
  color: #475569;
  font-size: 13px;
}
.summary-side {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: #334155;
  font-size: 13px;
}
.locked-box {
  padding: 10px 12px;
  border: 1px solid #f5d19b;
  background: #fff8e8;
  color: #9a5c00;
  border-radius: 6px;
}
.memo-area textarea {
  min-height: 60px;
}
.table-wrap {
  overflow: auto;
  border: 1px solid #dde2ea;
  border-radius: 6px;
}
.data-table.compact {
  width: 100%;
  border-collapse: collapse;
}
.data-table.compact th,
.data-table.compact td {
  border: 1px solid #dde2ea;
  padding: 6px 8px;
  vertical-align: top;
  font-size: 13px;
  color: #0f172a;
}
.data-table.compact thead th {
  background: #f8fafc;
}
.col-no {
  width: 56px;
  text-align: center;
}
.col-value {
  width: 170px;
}
.col-judge {
  width: 126px;
}
.col-ref {
  width: 96px;
  text-align: center;
}
.item-name {
  font-weight: 700;
}
.item-meta {
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
}
.check-caption {
  color: #475569;
  font-size: 12px;
}
.judge-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}
.judge-button {
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 6px 0;
  font-size: 12px;
  font-weight: 700;
  background: #fff;
  color: #334155;
  cursor: pointer;
  transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}
.judge-button.ok.active {
  background: #16a34a;
  border-color: #15803d;
  color: #fff;
}
.judge-button.ng.active {
  background: #dc2626;
  border-color: #b91c1c;
  color: #fff;
}
.input-invalid {
  border-color: #dc2626;
  background: #fff5f5;
}
.row-ng {
  background: #fff5f5;
}
.record-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
input,
select,
textarea {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 5px 6px;
  font-size: 13px;
  background: #fff;
}
input:disabled,
select:disabled,
textarea:disabled {
  background: #f8fafc;
  color: #475569;
}
textarea {
  resize: vertical;
}
.btn-primary,
.btn-secondary,
.btn-approve {
  border: 1px solid transparent;
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 12px;
  cursor: pointer;
}
.btn-primary {
  background: #2563eb;
  color: #fff;
}
.btn-secondary {
  background: #f1f5f9;
  color: #334155;
  border-color: #cbd5e1;
}
.btn-approve {
  background: #16a34a;
  color: #fff;
}
.btn-sm {
  padding: 4px 8px;
}
button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.44);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 30;
}
.modal-panel {
  width: min(980px, 100%);
  max-height: calc(100vh - 40px);
  overflow: auto;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #d7dde7;
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.22);
  padding: 16px;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}
.attachment-list {
  display: grid;
  gap: 12px;
}
.attachment-card {
  border: 1px solid #d7dde7;
  border-radius: 6px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.attachment-card-title {
  font-weight: 700;
}
.attachment-image-wrap img {
  max-width: 100%;
  max-height: 320px;
  object-fit: contain;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
}
.attachment-text {
  color: #334155;
  line-height: 1.5;
}
@media (max-width: 1100px) {
  .filter-panel {
    grid-template-columns: repeat(2, minmax(160px, 1fr));
  }
}
@media (max-width: 720px) {
  .inspection-operation {
    padding: 10px;
  }
  .filter-panel {
    grid-template-columns: 1fr;
  }
  .record-summary,
  .record-actions {
    flex-direction: column;
  }
  .modal-backdrop {
    padding: 10px;
  }
}
</style>
