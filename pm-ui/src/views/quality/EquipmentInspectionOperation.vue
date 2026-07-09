<template>
  <div class="page-container inspection-operation" v-if="canView">
    <div class="page-header">
      <h2 class="page-title">{{ isTestMode ? '設備点検 テスト実施' : '点検実施' }}</h2>
      <div class="page-actions">
        <button
          v-if="isTestMode"
          class="btn-secondary"
          @click="backToTemplate"
        >
          テンプレートに戻る
        </button>
        <button
          v-if="showBackToProcessInput && !isTestMode"
          class="btn-secondary"
          @click="backToProcessInput"
        >
          工程作業入力へ戻る
        </button>
        <button v-if="!isTestMode" class="btn-secondary" @click="loadTemplates" :disabled="loadingOptions || loadingRecord">
          テンプレート更新
        </button>
        <button v-if="!isTestMode" class="btn-secondary" @click="reloadRecord" :disabled="loadingRecord || !selectedSheetCode || !selectedDate">
          再読込
        </button>
      </div>
    </div>

    <p v-if="isTestMode" class="test-note">テスト実施の入力内容はDB保存されません。画面を閉じると破棄されます。</p>

    <section v-if="!isTestMode" class="panel filter-panel">
      <label>
        ライン
        <select
          v-model="selectedLineId"
          :disabled="loadingOptions || loadingRecord || isLineLockedFromRoute"
        >
          <option value="">すべて</option>
          <option v-for="line in lineOptions" :key="line.id" :value="String(line.id)">
            {{ formatLineOptionLabel(line) }}
          </option>
        </select>
      </label>
      <label>
        工程
        <select v-model="selectedProcessId" :disabled="loadingOptions || loadingRecord || isFilterLockedForWorker">
          <option value="">すべて</option>
          <option v-for="process in filteredProcessOptions" :key="process.id" :value="String(process.id)">
            {{ formatProcessOptionLabel(process) }}
          </option>
        </select>
      </label>
      <label>
        設備
        <select v-model="selectedSheetCode" :disabled="loadingOptions || loadingRecord || isFilterLockedForWorker">
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
      <div class="favorite-controls">
        <select v-model="selectedFavoriteId" @change="applyFavorite">
          <option value="">お気に入り選択</option>
          <option v-for="fav in favorites" :key="fav.id" :value="String(fav.id)">
            {{ fav.name }}
          </option>
        </select>
        <input type="text" v-model.trim="favoriteName" placeholder="お気に入り名" class="favorite-name-input" />
        <button class="btn-favorite" title="お気に入り登録" @click="saveFavorite" :disabled="loadingRecord">★</button>
      </div>
      <div class="header-status">
        <div>状態: <strong>{{ statusLabel(form.status) }}</strong></div>
        <div>実施者: <strong>{{ form.operator_name || "-" }}</strong></div>
        <div>総合判定: <strong>{{ form.overall_result || "-" }}</strong></div>
      </div>
    </section>

    <section class="panel" v-if="selectedSheetCode || isTestMode">
      <div class="record-summary">
        <div>
          <div class="summary-month">{{ inspectionYearMonthLabel }}</div>
          <div v-if="displaySummaryTitle" class="summary-title">{{ displaySummaryTitle }}</div>
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
              <th v-if="isQuarterlySection">確認方法</th>
              <th v-if="isQuarterlySection">判定基準</th>
              <th>方法</th>
              <th>確認頻度</th>
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
              :class="{ 'row-ng': result.judgement === 'NG', 'row-optional': !result.is_required }"
            >
              <td class="col-no">{{ result.inspection_no || "-" }}</td>
              <td>
                <div class="item-name">{{ result.item_name }}</div>
                <div class="item-meta">
                  {{ recordTypeLabel(result.record_type) }}
                  <span v-if="result.unit"> / {{ result.unit }}</span>
                </div>
              </td>
              <td>{{ result.standard || "-" }}</td>
              <td v-if="isQuarterlySection">{{ result.confirmation_method || "-" }}</td>
              <td v-if="isQuarterlySection">{{ result.criteria || "-" }}</td>
              <td>{{ result.method || "-" }}</td>
              <td>{{ result.frequency || "-" }}</td>
              <td class="col-value">
                <template v-if="isNumericRecordType(result.record_type)">
                  <input
                    type="number"
                    step="0.001"
                    v-model="result.numeric_value"
                    :class="{ 'input-invalid': isNumericOutOfSpec(result) }"
                    :disabled="!canEditRecord"
                    @input="handleNumericInput(result)"
                  />
                  <div v-if="result.record_type === 'PHOTO_NUMERIC'" class="photo-input-wrap">
                    <input type="file" accept="image/*" capture="environment" :disabled="!canEditRecord" @change="uploadResultPhoto($event, result)" />
                    <div v-if="result.photo_url" class="photo-action-row">
                      <button type="button" class="btn-secondary btn-sm" @click="toggleResultPhotoPreview(result)">
                        {{ result.photo_preview_visible ? "プレビュー閉じる" : "プレビュー" }}
                      </button>
                      <button type="button" class="btn-secondary btn-sm" :disabled="!canEditRecord" @click="removeResultPhoto(result)">写真削除</button>
                    </div>
                    <div v-if="result.photo_url && result.photo_preview_visible" class="photo-preview-wrap">
                      <img :src="result.photo_url" alt="計測写真" class="result-photo-preview" />
                    </div>
                  </div>
                </template>
                <template v-else-if="isPhotoOnlyRecordType(result.record_type)">
                  <div class="photo-input-wrap">
                    <input type="file" accept="image/*" capture="environment" :disabled="!canEditRecord" @change="uploadResultPhoto($event, result)" />
                    <div v-if="result.photo_url" class="photo-action-row">
                      <button type="button" class="btn-secondary btn-sm" @click="toggleResultPhotoPreview(result)">
                        {{ result.photo_preview_visible ? "プレビュー閉じる" : "プレビュー" }}
                      </button>
                      <button type="button" class="btn-secondary btn-sm" :disabled="!canEditRecord" @click="removeResultPhoto(result)">写真削除</button>
                    </div>
                    <div v-if="result.photo_url && result.photo_preview_visible" class="photo-preview-wrap">
                      <img :src="result.photo_url" alt="計測写真" class="result-photo-preview" />
                    </div>
                  </div>
                </template>
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
                    :disabled="!canEditRecord || !canSelectJudgement(result)"
                    :title="judgementButtonTitle(result)"
                    @click="setJudgement(result, 'NG')"
                  >
                    NG
                  </button>
                </div>
              </td>
              <td>
                <textarea v-model="result.comment" rows="2" :disabled="!canEditComment" />
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

      <div v-if="!isTestMode" class="record-actions">
        <button
          v-if="!isCompleted"
          class="btn-primary"
          @click="saveRecord('DRAFT')"
          :disabled="!canEditRecord || saving"
        >
          下書き保存
        </button>
        <button
          v-if="!isCompleted"
          class="btn-approve"
          @click="saveRecord('COMPLETED')"
          :disabled="!canEditRecord || saving"
        >
          点検完了
        </button>
        <button
          v-else
          class="btn-primary"
          @click="saveRecord('COMPLETED')"
          :disabled="!canEditComment || saving"
        >
          コメント保存
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
import { formatISODate } from '@/utils/dateUtil'
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
const lineOptions = ref([])
const processOptions = ref([])
const currentTemplate = ref(null)
const isLocked = ref(false)

const isTestMode = computed(() => Boolean(route.query?.test_template_id))
const testTemplateId = computed(() => Number(route.query?.test_template_id || 0))

const selectedSheetCode = ref(String(route.query.sheet_code || ""))
const selectedDate = ref(String(route.query.date || formatISODate(new Date())))
const sectionType = ref(String(route.query.section_type || "DAILY").toUpperCase())
// 工程/ラインからの絞り込み用（実績入力画面から渡される）
const selectedProcessId = ref(route.query.process_id ? String(route.query.process_id) : "")

const FAVORITE_SCREEN_KEY = 'quality.equipment_inspection_operation'
const favorites = ref([])
const selectedFavoriteId = ref('')
const favoriteName = ref('')
const isLeaderOrAbove = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const role = user.profile?.role || ''
  return ['leader', 'supervisor', 'chief', 'manager'].includes(role)
})
const resolveInitialLineId = () => {
  if (route.query.line_id) return String(route.query.line_id)
  if (isLeaderOrAbove.value) return ""
  const unitLines = authState.user?.profile?.unit_lines
  if (!Array.isArray(unitLines) || !unitLines.length) return ""
  const defaultMapping = unitLines.find((item) => item?.is_default)
  const target = defaultMapping || unitLines[0]
  return target?.line_id ? String(target.line_id) : ""
}
const selectedLineId = ref(resolveInitialLineId())

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

const canAccessQuality = (resource, level = "view", aliases = []) => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  const candidates = [resource, ...aliases]
  const hasSpecific = permissions.some((item) => candidates.includes(item.resource))
  if (hasSpecific) {
    return candidates.some((candidate) => hasPermission(user, candidate, level))
  }
  return hasPermission(user, "quality", level)
}
const canView = computed(() =>
  canAccessQuality("quality.equipment_inspection_operation", "view", ["quality.equipment_inspection"])
)
const canEdit = computed(() =>
  canAccessQuality("quality.equipment_inspection_operation", "edit", ["quality.equipment_inspection"])
)
const isCompleted = computed(() => String(form.value.status || "").toUpperCase() === "COMPLETED")
const canEditRecord = computed(() => isTestMode.value || (canEdit.value && !isLocked.value && !isCompleted.value))
const canEditComment = computed(() => isTestMode.value || (canEdit.value && !isLocked.value))
const isQuarterlySection = computed(() => String(sectionType.value || "").toUpperCase() === "QUARTERLY")
const processInputReturnPathMap = {
  mobile_process_input: "/production/mobile-process-input",
  desktop_process_input: "/production/desktop-process-input",
  tablet_process_input: "/production/tablet-process-input",
  simultaneous_process_input: "/production/simultaneous-process-input",
  dual_process_input: "/production/dual-process-input",
  two_person_one_equipment_input: "/production/two-person-one-equipment-input",
  laser_process_input: "/production/laser-process-input",
  brake_line_input: "/production/brake-line-input",
  spot_line_input: "/production/spot-line-input",
  mobile_line_input: "/production/mobile-input",
}
const showBackToProcessInput = computed(() => {
  const source = String(route.query?.source || "").trim()
  if (processInputReturnPathMap[source]) return true
  return Boolean(String(selectedLineId.value || "").trim() || String(selectedProcessId.value || "").trim())
})
const isFilterLockedForWorker = computed(() => !isLeaderOrAbove.value)
const isLineLockedFromRoute = computed(() =>
  Boolean(String(route.query?.line_id || "").trim()) || isFilterLockedForWorker.value
)
const filteredProcessOptions = computed(() => {
  if (!selectedLineId.value) return processOptions.value
  const lineMatched = processOptions.value.filter((process) => {
    const processLineId = process?.line ?? process?.line_id ?? ""
    return String(processLineId) === String(selectedLineId.value)
  })
  if (!selectedProcessId.value) return lineMatched
  const hasSelected = lineMatched.some((process) => String(process.id) === String(selectedProcessId.value))
  if (hasSelected) return lineMatched
  const selectedProcess = processOptions.value.find((process) => String(process.id) === String(selectedProcessId.value))
  return selectedProcess ? [...lineMatched, selectedProcess] : lineMatched
})
const inspectionYearMonthLabel = computed(() => {
  const raw = String(selectedDate.value || "").trim()
  if (!raw) return "-"
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return "-"
  const year = date.getFullYear()
  const month = date.getMonth() + 1
  return `${year}年 ${month}月`
})
const displaySummaryTitle = computed(() => {
  const title = String(form.value.template_title || currentTemplate.value?.title || "").trim()
  if (!title) return ""
  const normalized = title.replace(/\s+/g, "")
  if (normalized === "年月度" || normalized === "年月") return ""
  return title
})

const statusLabel = (value) => {
  if (value === "COMPLETED") return "完了"
  return "下書き"
}

const recordTypeLabel = (value) => {
  if (value === "NUMERIC") return "数値"
  if (value === "PHOTO_NUMERIC") return "写真＋数値"
  if (value === "PHOTO") return "写真のみ"
  if (value === "TEXT") return "文字"
  return "チェック"
}
const isNumericRecordType = (value) => ["NUMERIC", "PHOTO_NUMERIC"].includes(String(value || "").toUpperCase())
const isPhotoOnlyRecordType = (value) => String(value || "").toUpperCase() === "PHOTO"

const formatLineOptionLabel = (line) => {
  const code = String(line?.line_code || "").trim()
  const name = String(line?.line_name || "").trim()
  if (code && name) return `${code} - ${name}`
  if (name) return name
  if (code) return code
  return `ID:${line?.id ?? ""}`
}

const formatProcessOptionLabel = (process) => {
  const code = String(process?.process_code || "").trim()
  const name = String(process?.process_name || "").trim()
  if (code && name) return `${code} - ${name}`
  if (name) return name
  if (code) return code
  return `ID:${process?.id ?? ""}`
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

  const rangeDelimMatch = text.match(/(\d+(?:\.\d+)?)\s*[～~\-]\s*(\d+(?:\.\d+)?)/)
  if (rangeDelimMatch) {
    let low = toNumericValue(rangeDelimMatch[1])
    let high = toNumericValue(rangeDelimMatch[2])
    if (low !== null && high !== null) {
      if (low > high) [low, high] = [high, low]
      return { type: "range", min: low, max: high }
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
  if (!result || !isNumericRecordType(result.record_type)) return null
  for (const candidate of [result.criteria, result.standard]) {
    const rule = parseNumericRuleText(candidate)
    if (rule) return rule
  }
  return null
}

const numericValueWithinRule = (result) => {
  if (!result || !isNumericRecordType(result.record_type)) return null
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

const canSelectJudgement = (result) => {
  if (!result) return true
  return result.is_frequency_applicable !== false
}

const canSelectOk = (result) => {
  if (!canSelectJudgement(result)) return false
  if (!result) return true
  if (isPhotoOnlyRecordType(result.record_type)) return Boolean(String(result.photo_url || "").trim())
  if (!isNumericRecordType(result.record_type)) return true
  if (toNumericValue(result.numeric_value) === null) return false
  if (result.record_type === "PHOTO_NUMERIC" && !String(result.photo_url || "").trim()) return false
  return numericValueWithinRule(result) !== false
}

const judgementButtonTitle = (result) => {
  if (!canSelectJudgement(result)) {
    return "この項目はラインカレンダ上の対象日ではないため判定できません。"
  }
  return ""
}

const okButtonTitle = (result) => {
  const baseTitle = judgementButtonTitle(result)
  if (baseTitle) return baseTitle
  if (!result) return ""
  if (isPhotoOnlyRecordType(result.record_type) && !String(result.photo_url || "").trim()) {
    return "写真をアップロードしてください。"
  }
  if (!isNumericRecordType(result.record_type)) return ""
  if (toNumericValue(result.numeric_value) === null) {
    return "測定値を入力してください。"
  }
  if (result.record_type === "PHOTO_NUMERIC" && !String(result.photo_url || "").trim()) {
    return "写真をアップロードしてください。"
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
        is_frequency_applicable: result.is_frequency_applicable !== false,
        numeric_value: result.numeric_value ?? "",
        photo_url: result.photo_url || "",
        photo_preview_visible: false,
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
    numeric_value: isNumericRecordType(result.record_type) && result.numeric_value !== "" ? result.numeric_value : null,
    photo_url: ["PHOTO_NUMERIC", "PHOTO"].includes(String(result.record_type || "").toUpperCase()) ? String(result.photo_url || "") : "",
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
      process_id: selectedProcessId.value || undefined,
      line_id: selectedLineId.value || undefined,
      source: route.query?.source ? String(route.query.source) : undefined,
    },
  })
}

const backToTemplate = () => {
  const templateId = testTemplateId.value
  router.push({
    path: '/quality/equipment-inspection/master',
    query: templateId ? { id: String(templateId) } : {},
  })
}

const loadTestRecord = async () => {
  if (!testTemplateId.value) return
  loadingRecord.value = true
  try {
    const response = await api.qualityEquipmentInspections.prepareTest(
      testTemplateId.value,
      { section_type: sectionType.value },
    )
    form.value = normalizeRecord(response.data?.record || createEmptyForm())
  } catch (error) {
    console.error("テストデータ準備に失敗:", error)
    form.value = createEmptyForm()
    alert("テストデータの取得に失敗しました。")
  } finally {
    loadingRecord.value = false
  }
}

const backToProcessInput = () => {
  const source = String(route.query?.source || "").trim()
  const path = processInputReturnPathMap[source] || "/production/mobile-process-input"
  const lineId = selectedLineId.value || ""
  const processId = selectedProcessId.value || ""
  const returnPanel = route.query?.return_panel ? String(route.query.return_panel) : ""
  const returnOperatorName = route.query?.return_operator_name ? String(route.query.return_operator_name) : ""
  const returnOperatorUserId = route.query?.return_operator_user_id ? String(route.query.return_operator_user_id) : ""
  router.push({
    path,
    query: {
      ...(lineId ? { line_id: String(lineId) } : {}),
      ...(processId ? { process_id: String(processId) } : {}),
      ...(returnPanel ? { return_panel: returnPanel } : {}),
      ...(returnOperatorName ? { return_operator_name: returnOperatorName } : {}),
      ...(returnOperatorUserId ? { return_operator_user_id: returnOperatorUserId } : {}),
    },
  })
}

const loadFilterOptions = async () => {
  try {
    const [linesRes, processesRes] = await Promise.all([
      api.lines.getProductionLines(),
      api.processes.getProcesses(),
    ])
    lineOptions.value = Array.isArray(linesRes.data) ? linesRes.data : linesRes.data?.results || []
    processOptions.value = Array.isArray(processesRes.data) ? processesRes.data : processesRes.data?.results || []
  } catch (error) {
    console.warn("ライン/工程候補の取得に失敗:", error)
    lineOptions.value = []
    processOptions.value = []
  }

  if (selectedLineId.value) {
    const exists = lineOptions.value.some((line) => String(line.id) === String(selectedLineId.value))
    if (!exists) {
      try {
        const res = await api.lines.getLine(selectedLineId.value)
        if (res?.data?.id !== undefined && res?.data?.id !== null) {
          lineOptions.value = [...lineOptions.value, res.data]
        }
      } catch (error) {
        console.warn("ライン候補の補完取得に失敗:", error)
        lineOptions.value = [
          ...lineOptions.value,
          { id: selectedLineId.value, line_code: `ID:${selectedLineId.value}`, line_name: "（候補未取得）" },
        ]
      }
    }
  }

  if (selectedProcessId.value) {
    const exists = processOptions.value.some((process) => String(process.id) === String(selectedProcessId.value))
    if (!exists) {
      try {
        const res = await api.processes.getProcess(selectedProcessId.value)
        if (res?.data?.id !== undefined && res?.data?.id !== null) {
          processOptions.value = [...processOptions.value, res.data]
        }
      } catch (error) {
        console.warn("工程候補の補完取得に失敗:", error)
        processOptions.value = [
          ...processOptions.value,
          { id: selectedProcessId.value, process_code: `ID:${selectedProcessId.value}`, process_name: "（候補未取得）", line: selectedLineId.value || null },
        ]
      }
    }
  }
}

const mergeFilterOptionsFromTemplates = (rows = []) => {
  const lineMap = new Map(lineOptions.value.map((line) => [String(line.id), line]))
  const processMap = new Map(processOptions.value.map((process) => [String(process.id), process]))

  rows.forEach((row) => {
    const rowLines = Array.isArray(row?.line_options) ? row.line_options : []
    rowLines.forEach((line) => {
      const key = String(line?.id || "")
      if (!key || lineMap.has(key)) return
      lineMap.set(key, {
        id: line.id,
        line_code: line.line_code || `ID:${line.id}`,
        line_name: line.line_name || "",
      })
    })

    const rowProcesses = Array.isArray(row?.process_options) ? row.process_options : []
    rowProcesses.forEach((process) => {
      const key = String(process?.id || "")
      if (!key || processMap.has(key)) return
      processMap.set(key, {
        id: process.id,
        process_code: process.process_code || `ID:${process.id}`,
        process_name: process.process_name || "",
        line: process.line_id ?? null,
      })
    })
  })

  lineOptions.value = Array.from(lineMap.values())
  processOptions.value = Array.from(processMap.values())
}

const hydrateFiltersFromEquipment = async () => {
  const sheetCode = String(selectedSheetCode.value || "").trim()
  if (!sheetCode) return
  try {
    const res = await api.equipments.list({ equipment_code: sheetCode })
    const rows = Array.isArray(res.data) ? res.data : res.data?.results || []
    const equipment = rows.find((row) => String(row?.equipment_code || "").trim() === sheetCode) || rows[0]
    if (!equipment) return

    const lineId = equipment.line ?? equipment.line_id ?? ""
    if (lineId) {
      const nextLine = {
        id: lineId,
        line_code: equipment.line_code || "",
        line_name: equipment.line_name || "",
      }
      const index = lineOptions.value.findIndex((line) => String(line.id) === String(lineId))
      if (index >= 0) {
        const current = lineOptions.value[index] || {}
        lineOptions.value[index] = {
          ...current,
          line_code: nextLine.line_code || current.line_code || "",
          line_name: nextLine.line_name || current.line_name || "",
        }
      } else {
        lineOptions.value = [...lineOptions.value, nextLine]
      }
      if (!selectedLineId.value) selectedLineId.value = String(lineId)
    }

    const processId = equipment.process ?? equipment.process_id ?? ""
    if (processId) {
      const nextProcess = {
        id: processId,
        process_code: equipment.process_code || "",
        process_name: equipment.process_name || "",
        line: lineId || null,
      }
      const index = processOptions.value.findIndex((process) => String(process.id) === String(processId))
      if (index >= 0) {
        const current = processOptions.value[index] || {}
        processOptions.value[index] = {
          ...current,
          process_code: nextProcess.process_code || current.process_code || "",
          process_name: nextProcess.process_name || current.process_name || "",
          line: nextProcess.line || current.line || current.line_id || null,
        }
      } else {
        processOptions.value = [...processOptions.value, nextProcess]
      }
      if (!selectedProcessId.value) selectedProcessId.value = String(processId)
    }
  } catch (error) {
    console.warn("設備からのライン/工程補完に失敗:", error)
  }
}

const applyEquipmentContext = (context = {}) => {
  if (!context || typeof context !== "object") return

  const lineId = context.line_id ? String(context.line_id) : ""
  if (lineId) {
    const index = lineOptions.value.findIndex((line) => String(line.id) === lineId)
    const next = {
      id: context.line_id,
      line_code: context.line_code || "",
      line_name: context.line_name || "",
    }
    if (index >= 0) {
      const current = lineOptions.value[index] || {}
      lineOptions.value[index] = {
        ...current,
        line_code: next.line_code || current.line_code || "",
        line_name: next.line_name || current.line_name || "",
      }
    } else {
      lineOptions.value = [...lineOptions.value, next]
    }
    selectedLineId.value = lineId
  }

  const processId = context.process_id ? String(context.process_id) : ""
  if (processId) {
    const index = processOptions.value.findIndex((process) => String(process.id) === processId)
    const next = {
      id: context.process_id,
      process_code: context.process_code || "",
      process_name: context.process_name || "",
      line: context.line_id ?? null,
    }
    if (index >= 0) {
      const current = processOptions.value[index] || {}
      processOptions.value[index] = {
        ...current,
        process_code: next.process_code || current.process_code || "",
        process_name: next.process_name || current.process_name || "",
        line: next.line || current.line || current.line_id || null,
      }
    } else {
      processOptions.value = [...processOptions.value, next]
    }
    selectedProcessId.value = processId
  }
}

const loadTemplates = async () => {
  loadingOptions.value = true
  try {
    const fetchOptions = async (params) => {
      const response = await api.qualityEquipmentInspections.list({ for_operation: true, ...params })
      return response.data?.results || response.data || []
    }

    let rows = []
    if (selectedProcessId.value) {
      // 工程に紐付く設備を優先
      rows = await fetchOptions({ process_id: selectedProcessId.value })
      // 該当なければラインにフォールバック
      if (!rows.length && selectedLineId.value) {
        rows = await fetchOptions({ line_id: selectedLineId.value })
      }
    } else if (selectedLineId.value) {
      rows = await fetchOptions({ line_id: selectedLineId.value })
    } else {
      rows = await fetchOptions({})
    }

    mergeFilterOptionsFromTemplates(rows)
    await hydrateFiltersFromEquipment()

    templateOptions.value = [...rows].sort((a, b) => {
      return String(a.sheet_code || "").localeCompare(String(b.sheet_code || ""), "ja")
    })
    if (!selectedSheetCode.value && templateOptions.value.length && (selectedLineId.value || selectedProcessId.value)) {
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
    applyEquipmentContext(response.data?.equipment_context || {})
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

const loadFavorites = async () => {
  try {
    const res = await api.accounts.getFavorites({ screen_key: FAVORITE_SCREEN_KEY, page_size: 200 })
    favorites.value = Array.isArray(res.data) ? res.data : res.data?.results || []
  } catch (e) {
    console.error('お気に入り取得エラー:', e)
  }
}

const toFavoritePayload = () => ({
  lineId: String(selectedLineId.value || ''),
  processId: String(selectedProcessId.value || ''),
  sheetCode: String(selectedSheetCode.value || ''),
})

const applyFavorite = async () => {
  const id = Number(selectedFavoriteId.value || 0)
  if (!id) return
  const target = favorites.value.find((item) => Number(item.id) === id)
  if (!target) return
  favoriteName.value = target.name || ''
  const payload = target.payload || {}
  selectedLineId.value = String(payload.lineId || '')
  await loadTemplates()
  selectedProcessId.value = String(payload.processId || '')
  selectedSheetCode.value = String(payload.sheetCode || '')
}

const saveFavorite = async () => {
  const name = String(favoriteName.value || '').trim()
  if (!name) {
    alert('お気に入り名を入力してください。')
    return
  }
  try {
    const id = Number(selectedFavoriteId.value || 0)
    const data = { screen_key: FAVORITE_SCREEN_KEY, name, payload: toFavoritePayload() }
    if (id) {
      await api.accounts.updateFavorite(id, data)
    } else {
      await api.accounts.createFavorite(data)
    }
    await loadFavorites()
    const found = favorites.value.find((item) => item.name === name)
    selectedFavoriteId.value = found ? String(found.id) : ''
    alert('お気に入りを保存しました。')
  } catch (e) {
    alert(`お気に入り保存エラー: ${e?.response?.data?.detail || e?.message || '保存に失敗しました。'}`)
  }
}

const setJudgement = (result, value) => {
  if (!canEditRecord.value || !result) return
  if (!canSelectJudgement(result)) return
  const nextValue = String(value || "").trim().toUpperCase()
  if (nextValue === "OK" && !canSelectOk(result)) return
  if (String(result.judgement || "").trim().toUpperCase() === nextValue) {
    result.judgement = ""
    return
  }
  result.judgement = nextValue
}

const handleNumericInput = (result) => {
  if (!result || !isNumericRecordType(result.record_type)) return
  if (result.judgement === "OK" && !canSelectOk(result)) {
    result.judgement = ""
  }
}


const uploadResultPhoto = async (event, result) => {
  const file = event?.target?.files?.[0]
  if (!file || !result) return
  try {
    const formData = new FormData()
    formData.append("file", file)
    const response = await api.qualityEquipmentInspections.uploadAttachmentImage(formData)
    result.photo_url = String(response.data?.image_url || "")
    result.photo_preview_visible = false
  } catch (error) {
    console.error("計測写真アップロードに失敗:", error)
    alert("写真アップロードに失敗しました。")
  } finally {
    if (event?.target) event.target.value = ""
  }
}

const removeResultPhoto = (result) => {
  if (!result) return
  result.photo_url = ""
  result.photo_preview_visible = false
}

const toggleResultPhotoPreview = (result) => {
  if (!result || !String(result.photo_url || "").trim()) return
  result.photo_preview_visible = !Boolean(result.photo_preview_visible)
}
const saveRecord = async (targetStatus) => {
  if (!canEditComment.value) return
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
  if (!canView.value || isTestMode.value) return
  syncQuery()
  if (selectedSheetCode.value && selectedDate.value) {
    await loadPreparedRecord()
  }
})

watch([selectedLineId, selectedProcessId], async () => {
  if (!canView.value || isTestMode.value) return
  syncQuery()
  await loadTemplates()
})

watch(selectedLineId, (lineId) => {
  if (!lineId) return
  if (!selectedProcessId.value) return
  const exists = filteredProcessOptions.value.some((process) => String(process.id) === String(selectedProcessId.value))
  if (!exists) {
    selectedProcessId.value = ""
  }
})

onMounted(async () => {
  if (!canView.value) return
  if (isTestMode.value) {
    await loadTestRecord()
    return
  }
  await loadFilterOptions()
  loadFavorites()
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
.test-note {
  margin: 0;
  padding: 8px 12px;
  background: #fef3c7;
  border: 1px solid #f59e0b;
  border-radius: 6px;
  color: #92400e;
  font-size: 13px;
  font-weight: 700;
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
.favorite-controls {
  display: flex;
  gap: 6px;
  align-items: end;
}
.favorite-controls select {
  flex: 1;
  min-width: 100px;
}
.favorite-name-input {
  width: 100px !important;
}
.btn-favorite {
  padding: 5px 10px;
  background: #facc15;
  color: #78350f;
  border: 1px solid #eab308;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 700;
  min-width: 34px;
  white-space: nowrap;
}
.btn-favorite:hover {
  background: #eab308;
}
.btn-favorite:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
.summary-month {
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.1;
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
.photo-input-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.photo-action-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.photo-preview-wrap {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 6px;
  background: #f8fafc;
}
.result-photo-preview {
  display: block;
  width: min(360px, 100%);
  max-height: 260px;
  object-fit: contain;
  border-radius: 4px;
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
.row-optional {
  opacity: 0.6;
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
