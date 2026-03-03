<template>
  <div class="page-container inspection-master" v-if="canView">
    <div class="page-header">
      <h2 class="page-title">点検項目作成</h2>
      <div class="page-actions">
        <button class="btn-secondary" @click="printCurrentTemplate" :disabled="detailLoading">
          印刷
        </button>
        <button class="btn-secondary" @click="loadTemplateList" :disabled="loadingList || detailLoading">
          更新
        </button>
        <button class="btn-primary" @click="startNewTemplate" :disabled="saving || actionLoading">
          新規作成
        </button>
      </div>
    </div>

    <div class="master-layout">
      <section class="panel list-panel">
        <h3 class="panel-title">テンプレート一覧</h3>
        <div class="table-wrap">
          <table class="data-table compact">
            <thead>
              <tr>
                <th>ID</th>
                <th>設備</th>
                <th>版</th>
                <th>状態</th>
                <th>更新者</th>
                <th>更新日時</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in templates"
                :key="row.id"
                :class="{ selected: Number(selectedTemplateId) === Number(row.id) }"
                @click="selectTemplate(row.id)"
              >
                <td>{{ row.id }}</td>
                <td>{{ row.sheet_code }} {{ row.sheet_name }}</td>
                <td>{{ row.version }}</td>
                <td>
                  <span class="status-chip" :class="statusClass(row.status)">
                    {{ statusLabel(row.status) }}
                  </span>
                </td>
                <td>{{ row.created_by_name || "-" }}</td>
                <td>{{ formatDateTime(row.updated_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="!templates.length && !loadingList" class="no-data">データがありません</div>
      </section>

      <section class="panel edit-panel">
        <h3 class="panel-title">編集</h3>

        <div class="status-row">
          <span class="status-chip" :class="statusClass(form.status)">
            {{ statusLabel(form.status) }}
          </span>
          <span class="status-meta">作成者: {{ form.created_by_name || "-" }}</span>
          <span class="status-meta">確認担当: {{ form.reviewer_user_name || "-" }}</span>
          <span class="status-meta">承認担当: {{ form.approver_user_name || "-" }}</span>
        </div>

        <div class="form-grid">
          <label>
            設備コード
            <input v-model.trim="form.sheet_code" :disabled="!canEditFields" />
          </label>
          <label>
            設備名
            <input v-model.trim="form.sheet_name" :disabled="!canEditFields" />
          </label>
          <label class="wide">
            帳票タイトル
            <input v-model.trim="form.title" :disabled="!canEditFields" />
          </label>
          <label>
            元シート名
            <input v-model.trim="form.source_sheet_name" :disabled="!canEditFields" />
          </label>
          <label>
            改訂日
            <input type="date" v-model="form.revision_date" :disabled="!canEditFields" />
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

        <div v-if="form.rejection_comment" class="rejection-box">
          差戻しコメント: {{ form.rejection_comment }}
        </div>

        <div class="workflow-actions">
          <button class="btn-primary" @click="saveTemplate" :disabled="!canEditFields || saving">
            {{ form.id ? "下書き更新" : "下書き保存" }}
          </button>
          <button class="btn-secondary" @click="loadSm009Defaults" :disabled="!canEditFields">
            SM-009初期項目を読込
          </button>
          <button class="btn-approve" @click="submitForReview" :disabled="!canSubmitForReview || actionLoading">
            確認依頼
          </button>
          <button class="btn-review" @click="completeReview" :disabled="!canReview || actionLoading">
            確認完了
          </button>
          <button class="btn-approve" @click="approveTemplate" :disabled="!canApprove || actionLoading">
            承認
          </button>
          <button class="btn-danger" @click="rejectTemplate" :disabled="!canReject || actionLoading">
            差戻し
          </button>
        </div>

        <div class="item-section">
          <div class="section-header">
            <h4>日次点検項目</h4>
            <button class="btn-secondary btn-sm" @click="addItem('DAILY')" :disabled="!canEditFields">
              行追加
            </button>
          </div>
          <div class="table-wrap">
            <table class="data-table compact">
              <thead>
                <tr>
                  <th>No</th>
                  <th>点検項目</th>
                  <th>規格</th>
                  <th>確認頻度</th>
                  <th>方法</th>
                  <th>記録種別</th>
                  <th>単位</th>
                  <th>判定基準</th>
                  <th>必須</th>
                  <th>有効</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in dailyItems" :key="item.local_key">
                  <td>
                    <input type="number" min="1" v-model.number="item.inspection_no" :disabled="!canEditFields" />
                  </td>
                  <td><textarea v-model="item.item_name" rows="2" :disabled="!canEditFields" /></td>
                  <td><textarea v-model="item.standard" rows="2" :disabled="!canEditFields" /></td>
                  <td><input v-model="item.frequency" :disabled="!canEditFields" /></td>
                  <td><textarea v-model="item.method" rows="2" :disabled="!canEditFields" /></td>
                  <td>
                    <select v-model="item.record_type" :disabled="!canEditFields">
                      <option value="CHECK">チェック</option>
                      <option value="NUMERIC">数値</option>
                      <option value="TEXT">文字</option>
                    </select>
                  </td>
                  <td><input v-model="item.unit" :disabled="!canEditFields" /></td>
                  <td><textarea v-model="item.criteria" rows="2" :disabled="!canEditFields" /></td>
                  <td class="center"><input type="checkbox" v-model="item.is_required" :disabled="!canEditFields" /></td>
                  <td class="center"><input type="checkbox" v-model="item.is_active" :disabled="!canEditFields" /></td>
                  <td>
                    <button class="btn-danger btn-sm" @click="removeItem(item)" :disabled="!canEditFields">削除</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="item-section">
          <div class="section-header">
            <h4>定期実測項目（3ヶ月）</h4>
            <button class="btn-secondary btn-sm" @click="addItem('QUARTERLY')" :disabled="!canEditFields">
              行追加
            </button>
          </div>
          <div class="table-wrap">
            <table class="data-table compact">
              <thead>
                <tr>
                  <th>項目</th>
                  <th>規格（設定）</th>
                  <th>参考値/単位</th>
                  <th>判定基準</th>
                  <th>記録種別</th>
                  <th>有効</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in quarterlyItems" :key="item.local_key">
                  <td><textarea v-model="item.item_name" rows="2" :disabled="!canEditFields" /></td>
                  <td><textarea v-model="item.standard" rows="2" :disabled="!canEditFields" /></td>
                  <td><textarea v-model="item.method" rows="2" :disabled="!canEditFields" /></td>
                  <td><textarea v-model="item.criteria" rows="2" :disabled="!canEditFields" /></td>
                  <td>
                    <select v-model="item.record_type" :disabled="!canEditFields">
                      <option value="CHECK">チェック</option>
                      <option value="NUMERIC">数値</option>
                      <option value="TEXT">文字</option>
                    </select>
                  </td>
                  <td class="center"><input type="checkbox" v-model="item.is_active" :disabled="!canEditFields" /></td>
                  <td>
                    <button class="btn-danger btn-sm" @click="removeItem(item)" :disabled="!canEditFields">削除</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
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
                  <td>{{ actionLabel(log.action) }}</td>
                  <td>{{ transitionLabel(log.from_status, log.to_status) }}</td>
                  <td>{{ log.actor_name || "-" }}</td>
                  <td>{{ log.comment || "-" }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="!form.workflow_logs.length" class="no-data">履歴はありません</div>
        </div>
      </section>
    </div>
  </div>

  <div class="page-container" v-else>
    <h2 class="page-title">点検項目作成</h2>
    <p class="no-data">品質の閲覧権限がありません。</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue"
import api from "@/api/client"
import { authState } from "@/auth"
import { hasPermission } from "@/router"

const STATUS_LABELS = {
  DRAFT: "下書き",
  REVIEW_PENDING: "確認待ち",
  APPROVAL_PENDING: "承認待ち",
  APPROVED: "承認済み",
  REJECTED: "差戻し",
}

const ACTION_LABELS = {
  CREATED: "作成",
  UPDATED: "更新",
  SUBMITTED: "確認依頼",
  REVIEWED: "確認完了",
  APPROVED: "承認",
  REJECTED: "差戻し",
}

const SM009_DAILY_ITEMS = [
  { inspection_no: 1, item_name: "電極のガタ（上下）", standard: "ガタ無きこと", frequency: "始業時", method: "シャンクを掴んで\n揺する", record_type: "CHECK", unit: "", criteria: "" },
  { inspection_no: 2, item_name: "加圧部の面直", standard: "プロジェクションの\n圧痕がはっきり\n見えること", frequency: "始業時", method: "ワーク上にナットを\n空打ちして圧痕を見る", record_type: "CHECK", unit: "", criteria: "" },
  { inspection_no: 3, item_name: "ガイドピンのガタ", standard: "下部電極との隙間が\n0.5mm以下のこと\n（ピアノ線棒が通らないこと）", frequency: "始業時", method: "ピアノ線棒（φ0.5)を\n隙間に通す", record_type: "CHECK", unit: "", criteria: "" },
  { inspection_no: 4, item_name: "ガイドピンの割れ", standard: "無きこと", frequency: "始業時", method: "目視で確認する", record_type: "CHECK", unit: "", criteria: "" },
  { inspection_no: 5, item_name: "水・エアの漏れ", standard: "無きこと", frequency: "始業時", method: "目視・手感・聴感で\n確認する", record_type: "CHECK", unit: "", criteria: "" },
  { inspection_no: 6, item_name: "上部ストローク\nセンサーの作動", standard: "ワーク・ナット空打ちにて\nNGランプ点灯すること", frequency: "始業時", method: "イジワルテストで\n確認する", record_type: "CHECK", unit: "", criteria: "" },
  { inspection_no: 7, item_name: "条件No.の設定確認", standard: "No.『13』であること", frequency: "始業時", method: "タイマーを確認する", record_type: "CHECK", unit: "", criteria: "" },
  { inspection_no: 8, item_name: "溶着強度の確認", standard: "70N・m以上\n（記録は数値記入）", frequency: "始業時", method: "テストピースを\nトルクレンチにて\n破壊する", record_type: "NUMERIC", unit: "N・m", criteria: "70以上" },
  { inspection_no: 9, item_name: "上部押さえ交換", standard: "新品または再研磨品に交換", frequency: "始業時", method: "専用工具", record_type: "CHECK", unit: "", criteria: "" },
  { inspection_no: 10, item_name: "ドレン水抜き", standard: "水が溜まっていないこと", frequency: "始業時", method: "ドレンコック開放", record_type: "CHECK", unit: "", criteria: "" },
  { inspection_no: 11, item_name: "上部ストロックセンサー調整", standard: "上部ランプ消灯すること", frequency: "電極交換後", method: "「上部ストロークセンサー\n調整要領書」に基づく", record_type: "CHECK", unit: "", criteria: "" },
  { inspection_no: 12, item_name: "オンス銅板の確認", standard: "２/３以上残りある事", frequency: "始業時", method: "目視", record_type: "CHECK", unit: "", criteria: "" },
  { inspection_no: 13, item_name: "加圧確認", standard: "加圧が0.22±0.01MPaであること", frequency: "始業時", method: "加圧計の針が2個の緑色矢印の中にあるのを目視で確認", record_type: "CHECK", unit: "", criteria: "" },
  { inspection_no: 14, item_name: "ベーク板の削れ", standard: "表面の削れ、欠けが無いこと", frequency: "始業時", method: "目視", record_type: "CHECK", unit: "", criteria: "" },
]

const SM009_QUARTERLY_ITEMS = [
  { item_name: "プログラムNo.", standard: "13", method: "参考値: ――", criteria: "設定と同じこと", record_type: "TEXT", unit: "" },
  { item_name: "加圧", standard: "0.22MPa", method: "参考値: 2.7kN", criteria: "参考値±0.3kN以内", record_type: "NUMERIC", unit: "kN" },
  { item_name: "電流", standard: "10800A", method: "参考値: 10800A", criteria: "参考値±500A以内", record_type: "NUMERIC", unit: "A" },
  { item_name: "通電時間", standard: "5サイクル", method: "参考値: ――", criteria: "設定と同じこと", record_type: "NUMERIC", unit: "サイクル" },
]

const templates = ref([])
const loadingList = ref(false)
const detailLoading = ref(false)
const saving = ref(false)
const actionLoading = ref(false)
const selectedTemplateId = ref(null)

const createEmptyForm = () => ({
  id: null,
  sheet_code: "SM-009",
  sheet_name: "M6ナット専用機",
  title: "設備始業点検表（SM-009：M6ナット専用機）",
  source_sheet_name: "SM-009",
  revision_date: "",
  effective_from: "",
  version: 1,
  status: "DRAFT",
  is_active: true,
  created_by: null,
  created_by_name: "",
  reviewer_user: null,
  reviewer_user_name: "",
  approver_user: null,
  approver_user_name: "",
  rejection_comment: "",
  items: [],
  workflow_logs: [],
})

const form = ref(createEmptyForm())

const canView = computed(() => {
  return hasPermission(authState.user, "quality", "view") || hasPermission(authState.user, "quality", "edit")
})

const canEdit = computed(() => hasPermission(authState.user, "quality", "edit"))
const currentUserId = computed(() => Number(authState.user?.id || 0))

const canEditFields = computed(() => {
  if (!canEdit.value) return false
  if (!form.value.id) return true
  return ["DRAFT", "REJECTED"].includes(form.value.status)
})

const canSubmitForReview = computed(() => {
  return Boolean(form.value.id) && canEditFields.value
})

const canReview = computed(() => {
  if (!canEdit.value || form.value.status !== "REVIEW_PENDING") return false
  const reviewerUserId = Number(form.value.reviewer_user || 0)
  return reviewerUserId === 0 || reviewerUserId === currentUserId.value
})

const canApprove = computed(() => {
  if (!canEdit.value || form.value.status !== "APPROVAL_PENDING") return false
  const approverUserId = Number(form.value.approver_user || 0)
  return approverUserId === 0 || approverUserId === currentUserId.value
})

const canReject = computed(() => canReview.value || canApprove.value)

const statusLabel = (status) => STATUS_LABELS[status] || status
const actionLabel = (action) => ACTION_LABELS[action] || action

const statusClass = (status) => {
  if (status === "APPROVED") return "ok"
  if (status === "REJECTED") return "danger"
  if (status === "APPROVAL_PENDING") return "approve"
  if (status === "REVIEW_PENDING") return "review"
  return "draft"
}

const transitionLabel = (fromStatus, toStatus) => {
  const from = statusLabel(fromStatus || "")
  const to = statusLabel(toStatus || "")
  if (!from && !to) return "-"
  if (!from) return `→ ${to}`
  if (!to) return from
  return `${from} → ${to}`
}

const escapeHtml = (value) => {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;")
}

const toPrintCell = (value) => {
  return escapeHtml(String(value ?? "")).replace(/\n/g, "<br>")
}

const printCurrentTemplate = () => {
  if (!form.value.items.length) {
    alert("印刷対象の点検項目がありません。")
    return
  }

  const statusText = statusLabel(form.value.status)
  const revisionDate = form.value.revision_date || "-"
  const effectiveFrom = form.value.effective_from || "-"
  const printedAt = new Date().toLocaleString("ja-JP")

  const dailyRowsHtml = dailyItems.value
    .map(
      (item) => `
      <tr>
        <td>${escapeHtml(item.inspection_no || "")}</td>
        <td>${toPrintCell(item.item_name)}</td>
        <td>${toPrintCell(item.standard)}</td>
        <td>${toPrintCell(item.frequency)}</td>
        <td>${toPrintCell(item.method)}</td>
        <td>${escapeHtml(item.record_type || "")}</td>
        <td>${escapeHtml(item.unit || "")}</td>
        <td>${toPrintCell(item.criteria)}</td>
      </tr>
    `
    )
    .join("")

  const quarterlyRowsHtml = quarterlyItems.value
    .map(
      (item) => `
      <tr>
        <td>${toPrintCell(item.item_name)}</td>
        <td>${toPrintCell(item.standard)}</td>
        <td>${toPrintCell(item.method)}</td>
        <td>${toPrintCell(item.criteria)}</td>
        <td>${escapeHtml(item.record_type || "")}</td>
        <td>${escapeHtml(item.unit || "")}</td>
      </tr>
    `
    )
    .join("")

  const html = `
  <!doctype html>
  <html>
    <head>
      <meta charset="utf-8" />
      <title>設備点検表 印刷</title>
      <style>
        @page { size: A4 landscape; margin: 8mm; }
        body { font-family: "Yu Gothic", "Meiryo", sans-serif; color: #111827; font-size: 11px; }
        h1 { margin: 0 0 8px; font-size: 18px; }
        .meta { display: grid; grid-template-columns: repeat(4, minmax(140px, 1fr)); gap: 6px 12px; margin-bottom: 8px; }
        .meta-item { border-bottom: 1px dashed #cbd5e1; padding-bottom: 2px; }
        .meta-label { color: #475569; margin-right: 6px; }
        h2 { margin: 12px 0 4px; font-size: 13px; }
        table { width: 100%; border-collapse: collapse; table-layout: fixed; }
        th, td { border: 1px solid #cbd5e1; padding: 4px 6px; vertical-align: top; word-break: break-word; }
        th { background: #eef2ff; font-weight: 700; }
        .narrow { width: 45px; text-align: center; }
        .mid { width: 70px; }
        .footer { margin-top: 8px; font-size: 10px; color: #64748b; text-align: right; }
      </style>
    </head>
    <body>
      <h1>${escapeHtml(form.value.title || "設備点検表")}</h1>
      <div class="meta">
        <div class="meta-item"><span class="meta-label">設備コード:</span>${escapeHtml(form.value.sheet_code || "-")}</div>
        <div class="meta-item"><span class="meta-label">設備名:</span>${escapeHtml(form.value.sheet_name || "-")}</div>
        <div class="meta-item"><span class="meta-label">版:</span>${escapeHtml(form.value.version || "-")}</div>
        <div class="meta-item"><span class="meta-label">状態:</span>${escapeHtml(statusText)}</div>
        <div class="meta-item"><span class="meta-label">改訂日:</span>${escapeHtml(revisionDate)}</div>
        <div class="meta-item"><span class="meta-label">運用開始日:</span>${escapeHtml(effectiveFrom)}</div>
        <div class="meta-item"><span class="meta-label">作成者:</span>${escapeHtml(form.value.created_by_name || "-")}</div>
        <div class="meta-item"><span class="meta-label">印刷日時:</span>${escapeHtml(printedAt)}</div>
      </div>

      <h2>日次点検項目</h2>
      <table>
        <thead>
          <tr>
            <th class="narrow">No</th>
            <th>点検項目</th>
            <th>規格</th>
            <th class="mid">確認頻度</th>
            <th>方法</th>
            <th class="mid">記録種別</th>
            <th class="mid">単位</th>
            <th>判定基準</th>
          </tr>
        </thead>
        <tbody>
          ${dailyRowsHtml || '<tr><td colspan="8">データなし</td></tr>'}
        </tbody>
      </table>

      <h2>定期実測項目（3ヶ月）</h2>
      <table>
        <thead>
          <tr>
            <th>項目</th>
            <th>規格（設定）</th>
            <th>参考値/単位</th>
            <th>判定基準</th>
            <th class="mid">記録種別</th>
            <th class="mid">単位</th>
          </tr>
        </thead>
        <tbody>
          ${quarterlyRowsHtml || '<tr><td colspan="6">データなし</td></tr>'}
        </tbody>
      </table>
      <div class="footer">PM 設備点検表</div>
    </body>
  </html>
  `

  const printWindow = window.open("", "_blank")
  if (!printWindow) {
    alert("ポップアップがブロックされました。許可して再実行してください。")
    return
  }

  printWindow.document.open()
  printWindow.document.write(html)
  printWindow.document.close()
  printWindow.focus()
  setTimeout(() => {
    printWindow.print()
  }, 200)
}

const formatDateTime = (value) => {
  if (!value) return "-"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString("ja-JP")
}

const createLocalKey = () => `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`

const buildSm009Defaults = () => {
  const daily = SM009_DAILY_ITEMS.map((item, index) => ({
    local_key: createLocalKey(),
    section_type: "DAILY",
    display_order: index + 1,
    inspection_no: item.inspection_no,
    item_name: item.item_name,
    standard: item.standard,
    frequency: item.frequency,
    method: item.method,
    record_type: item.record_type,
    unit: item.unit,
    criteria: item.criteria,
    is_required: true,
    is_active: true,
  }))

  const quarterly = SM009_QUARTERLY_ITEMS.map((item, index) => ({
    local_key: createLocalKey(),
    section_type: "QUARTERLY",
    display_order: index + 1,
    inspection_no: null,
    item_name: item.item_name,
    standard: item.standard,
    frequency: "3ヶ月/1回",
    method: item.method,
    record_type: item.record_type,
    unit: item.unit,
    criteria: item.criteria,
    is_required: true,
    is_active: true,
  }))
  return [...daily, ...quarterly]
}

const dailyItems = computed(() =>
  [...form.value.items]
    .filter((item) => item.section_type === "DAILY")
    .sort((a, b) => Number(a.display_order || 0) - Number(b.display_order || 0))
)

const quarterlyItems = computed(() =>
  [...form.value.items]
    .filter((item) => item.section_type === "QUARTERLY")
    .sort((a, b) => Number(a.display_order || 0) - Number(b.display_order || 0))
)

const resequenceSection = (sectionType) => {
  const targetItems = form.value.items
    .filter((item) => item.section_type === sectionType)
    .sort((a, b) => Number(a.display_order || 0) - Number(b.display_order || 0))
  targetItems.forEach((item, index) => {
    item.display_order = index + 1
  })
}

const addItem = (sectionType) => {
  const nextOrder =
    Math.max(
      0,
      ...form.value.items
        .filter((item) => item.section_type === sectionType)
        .map((item) => Number(item.display_order || 0))
    ) + 1

  form.value.items.push({
    local_key: createLocalKey(),
    section_type: sectionType,
    display_order: nextOrder,
    inspection_no: sectionType === "DAILY" ? nextOrder : null,
    item_name: "",
    standard: "",
    frequency: sectionType === "DAILY" ? "始業時" : "3ヶ月/1回",
    method: "",
    record_type: "CHECK",
    unit: "",
    criteria: "",
    is_required: true,
    is_active: true,
  })
}

const removeItem = (targetItem) => {
  form.value.items = form.value.items.filter((item) => item.local_key !== targetItem.local_key)
  resequenceSection(targetItem.section_type)
}

const loadSm009Defaults = () => {
  if (form.value.items.length > 0) {
    const ok = window.confirm("現在の項目をSM-009初期項目で上書きします。よろしいですか？")
    if (!ok) return
  }
  form.value.items = buildSm009Defaults()
}

const toFormModel = (raw) => {
  return {
    id: raw.id,
    sheet_code: raw.sheet_code || "",
    sheet_name: raw.sheet_name || "",
    title: raw.title || "",
    source_sheet_name: raw.source_sheet_name || "",
    revision_date: raw.revision_date || "",
    effective_from: raw.effective_from || "",
    version: Number(raw.version || 1),
    status: raw.status || "DRAFT",
    is_active: Boolean(raw.is_active),
    created_by: raw.created_by || null,
    created_by_name: raw.created_by_name || "",
    reviewer_user: raw.reviewer_user || null,
    reviewer_user_name: raw.reviewer_user_name || "",
    approver_user: raw.approver_user || null,
    approver_user_name: raw.approver_user_name || "",
    rejection_comment: raw.rejection_comment || "",
    workflow_logs: Array.isArray(raw.workflow_logs) ? raw.workflow_logs : [],
    items: Array.isArray(raw.items)
      ? raw.items.map((item) => ({
          local_key: createLocalKey(),
          id: item.id || null,
          section_type: item.section_type || "DAILY",
          display_order: Number(item.display_order || 1),
          inspection_no: item.inspection_no ?? null,
          item_name: item.item_name || "",
          standard: item.standard || "",
          frequency: item.frequency || "",
          method: item.method || "",
          record_type: item.record_type || "CHECK",
          unit: item.unit || "",
          criteria: item.criteria || "",
          is_required: Boolean(item.is_required),
          is_active: Boolean(item.is_active),
        }))
      : [],
  }
}

const buildPayload = () => {
  const normalizedItems = form.value.items
    .filter((item) => String(item.item_name || "").trim())
    .map((item) => ({
      section_type: item.section_type,
      display_order: Number(item.display_order || 1),
      inspection_no: item.section_type === "DAILY" ? Number(item.inspection_no || 0) || null : null,
      item_name: String(item.item_name || "").trim(),
      standard: String(item.standard || "").trim(),
      frequency: String(item.frequency || "").trim(),
      method: String(item.method || "").trim(),
      record_type: item.record_type || "CHECK",
      unit: String(item.unit || "").trim(),
      criteria: String(item.criteria || "").trim(),
      is_required: Boolean(item.is_required),
      is_active: Boolean(item.is_active),
    }))

  return {
    sheet_code: String(form.value.sheet_code || "").trim(),
    sheet_name: String(form.value.sheet_name || "").trim(),
    title: String(form.value.title || "").trim(),
    source_sheet_name: String(form.value.source_sheet_name || "").trim(),
    revision_date: form.value.revision_date || null,
    effective_from: form.value.effective_from || null,
    version: Number(form.value.version || 1),
    is_active: Boolean(form.value.is_active),
    items: normalizedItems,
  }
}

const loadTemplateList = async () => {
  if (!canView.value) return
  loadingList.value = true
  try {
    const response = await api.qualityEquipmentInspections.list()
    templates.value = response.data?.results || response.data || []
  } catch (error) {
    console.error("設備点検テンプレート一覧取得に失敗:", error)
    alert("テンプレート一覧の取得に失敗しました。")
  } finally {
    loadingList.value = false
  }
}

const loadTemplateDetail = async (id) => {
  if (!id) return
  detailLoading.value = true
  try {
    const response = await api.qualityEquipmentInspections.get(id)
    form.value = toFormModel(response.data)
    selectedTemplateId.value = id
  } catch (error) {
    console.error("設備点検テンプレート詳細取得に失敗:", error)
    alert("テンプレート詳細の取得に失敗しました。")
  } finally {
    detailLoading.value = false
  }
}

const selectTemplate = async (id) => {
  await loadTemplateDetail(id)
}

const startNewTemplate = () => {
  selectedTemplateId.value = null
  form.value = createEmptyForm()
  form.value.items = buildSm009Defaults()
}

const saveTemplate = async () => {
  if (!canEditFields.value) return
  if (!form.value.sheet_code || !form.value.sheet_name || !form.value.title) {
    alert("設備コード・設備名・帳票タイトルは必須です。")
    return
  }
  if (!form.value.items.length) {
    alert("点検項目を1件以上入力してください。")
    return
  }

  saving.value = true
  try {
    const payload = buildPayload()
    let response
    if (form.value.id) {
      response = await api.qualityEquipmentInspections.update(form.value.id, payload)
    } else {
      response = await api.qualityEquipmentInspections.create(payload)
    }
    const savedId = response.data?.id
    await loadTemplateList()
    if (savedId) {
      await loadTemplateDetail(savedId)
    }
    alert("保存しました。")
  } catch (error) {
    console.error("設備点検テンプレート保存に失敗:", error)
    alert("保存に失敗しました。")
  } finally {
    saving.value = false
  }
}

const submitForReview = async () => {
  if (!form.value.id || !canSubmitForReview.value) return
  const ok = window.confirm("確認依頼に進めます。よろしいですか？")
  if (!ok) return

  actionLoading.value = true
  try {
    await api.qualityEquipmentInspections.submitForReview(form.value.id)
    await loadTemplateList()
    await loadTemplateDetail(form.value.id)
    alert("確認依頼を登録しました。")
  } catch (error) {
    console.error("確認依頼に失敗:", error)
    alert("確認依頼に失敗しました。")
  } finally {
    actionLoading.value = false
  }
}

const completeReview = async () => {
  if (!form.value.id || !canReview.value) return
  const ok = window.confirm("確認完了にします。よろしいですか？")
  if (!ok) return

  actionLoading.value = true
  try {
    await api.qualityEquipmentInspections.review(form.value.id)
    await loadTemplateList()
    await loadTemplateDetail(form.value.id)
    alert("確認完了を登録しました。")
  } catch (error) {
    console.error("確認完了に失敗:", error)
    alert("確認完了に失敗しました。")
  } finally {
    actionLoading.value = false
  }
}

const approveTemplate = async () => {
  if (!form.value.id || !canApprove.value) return
  const ok = window.confirm("承認します。よろしいですか？")
  if (!ok) return

  actionLoading.value = true
  try {
    await api.qualityEquipmentInspections.approve(form.value.id)
    await loadTemplateList()
    await loadTemplateDetail(form.value.id)
    alert("承認しました。")
  } catch (error) {
    console.error("承認に失敗:", error)
    alert("承認に失敗しました。")
  } finally {
    actionLoading.value = false
  }
}

const rejectTemplate = async () => {
  if (!form.value.id || !canReject.value) return
  const comment = window.prompt("差戻しコメントを入力してください。", form.value.rejection_comment || "")
  if (comment === null) return

  actionLoading.value = true
  try {
    await api.qualityEquipmentInspections.reject(form.value.id, comment)
    await loadTemplateList()
    await loadTemplateDetail(form.value.id)
    alert("差戻ししました。")
  } catch (error) {
    console.error("差戻しに失敗:", error)
    alert("差戻しに失敗しました。")
  } finally {
    actionLoading.value = false
  }
}

onMounted(async () => {
  if (!canView.value) return
  await loadTemplateList()
  if (templates.value.length) {
    await loadTemplateDetail(templates.value[0].id)
  } else {
    startNewTemplate()
  }
})
</script>

<style scoped>
.inspection-master {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.master-layout {
  display: grid;
  grid-template-columns: 34% 1fr;
  gap: 12px;
  min-height: 0;
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
  font-size: 15px;
  font-weight: 700;
}
.table-wrap {
  overflow: auto;
  border: 1px solid #dde2ea;
  border-radius: 4px;
}
.data-table.compact th,
.data-table.compact td {
  padding: 4px 6px;
  font-size: 12px;
  vertical-align: top;
}
.data-table.compact tbody tr {
  cursor: pointer;
}
.data-table.compact tbody tr.selected {
  background: #e7f0ff;
}
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
.status-chip.draft {
  background: #eef2ff;
  border-color: #c7d2fe;
  color: #3730a3;
}
.status-chip.review {
  background: #fff4e5;
  border-color: #f5d19b;
  color: #9a5c00;
}
.status-chip.approve {
  background: #eaf7ff;
  border-color: #8ecdf3;
  color: #0c4a6e;
}
.status-chip.ok {
  background: #e9f7ef;
  border-color: #9fd9b4;
  color: #166534;
}
.status-chip.danger {
  background: #fdecec;
  border-color: #f7b1b1;
  color: #991b1b;
}
.status-meta {
  font-size: 12px;
  color: #334155;
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(140px, 1fr));
  gap: 8px;
}
.form-grid .wide {
  grid-column: span 2;
}
.form-grid label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}
.check-line {
  flex-direction: row !important;
  align-items: center;
  margin-top: 18px;
}
.workflow-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.item-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.item-section h4 {
  margin: 0;
  font-size: 14px;
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.center {
  text-align: center;
}
input,
select,
textarea {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 4px 6px;
  background: #fff;
  font-size: 12px;
}
textarea {
  resize: vertical;
}
.rejection-box {
  border: 1px solid #f5b7b1;
  background: #fff5f5;
  color: #7f1d1d;
  font-size: 12px;
  padding: 8px;
  border-radius: 4px;
}
.btn-primary,
.btn-secondary,
.btn-review,
.btn-approve,
.btn-danger {
  border: 1px solid transparent;
  border-radius: 4px;
  padding: 5px 10px;
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
.btn-review {
  background: #f59e0b;
  color: #111827;
}
.btn-approve {
  background: #16a34a;
  color: #fff;
}
.btn-danger {
  background: #dc2626;
  color: #fff;
}
.btn-sm {
  padding: 3px 8px;
}
button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
@media (max-width: 1100px) {
  .master-layout {
    grid-template-columns: 1fr;
  }
  .form-grid {
    grid-template-columns: repeat(2, minmax(140px, 1fr));
  }
}
@media (max-width: 700px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
  .form-grid .wide {
    grid-column: span 1;
  }
}
</style>
