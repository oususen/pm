<template>
  <div class="master-menu">
    <div class="page-header">
      <h2 class="page-title">工程一体チェックシート</h2>
      <DataSourceDialog title="工程一体チェックシート" :sources="dsSources" />
    </div>

    <div class="master-grid">
      <RouterLink
        v-if="canViewIntegratedTemplate"
        to="/quality/product-checksheet/integrated/templates"
        class="master-tile"
      >
        <div class="icon-box">📝</div>
        <div class="label">チェックシート作成</div>
      </RouterLink>
      <RouterLink
        v-if="canViewIntegratedOperation"
        to="/quality/product-checksheet/integrated/operation"
        class="master-tile"
      >
        <div class="icon-box">🛠</div>
        <div class="label">チェック実施</div>
      </RouterLink>
      <RouterLink
        v-if="canViewIntegratedReview"
        to="/quality/product-checksheet/integrated/review"
        class="master-tile"
      >
        <div class="icon-box">✅</div>
        <div class="label">チェック結果確認</div>
      </RouterLink>
      <RouterLink
        v-if="canViewIntegratedDashboard"
        to="/quality/product-checksheet/integrated/weekly-monthly"
        class="master-tile"
      >
        <div class="icon-box">📅</div>
        <div class="label">週・月確認</div>
      </RouterLink>
      <RouterLink
        v-if="canViewIntegratedDashboard"
        to="/quality/product-checksheet/integrated/trend-analysis"
        class="master-tile"
      >
        <div class="icon-box">📊</div>
        <div class="label">傾向確認・分析</div>
      </RouterLink>
      <RouterLink
        v-if="canViewIntegratedDashboard"
        to="/quality/product-checksheet/integrated/problem-tools"
        class="master-tile"
      >
        <div class="icon-box">🔧</div>
        <div class="label">品質問題時ツール</div>
      </RouterLink>
    </div>

    <p class="helper-text">
      工程一体チェックシートの各機能に遷移します。
    </p>
  </div>
</template>

<script setup>
import { computed } from "vue"
import { RouterLink } from "vue-router"
import DataSourceDialog from "@/components/DataSourceDialog.vue"
import { authState } from "@/auth"
import { hasPermission } from "@/router"

const canAccessQuality = (resource, level = "view", aliases = [], fallbackToQuality = true) => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  const candidates = [resource, ...aliases]
  const hasSpecific = permissions.some((item) => candidates.includes(item.resource))
  if (hasSpecific) {
    return candidates.some((candidate) => hasPermission(user, candidate, level))
  }
  return fallbackToQuality ? hasPermission(user, "quality", level) : false
}

const canViewIntegratedTemplate = computed(() =>
  canAccessQuality("quality.integrated_checksheet_template", "view", [
    "quality",
  ])
)
const canViewIntegratedOperation = computed(() =>
  canAccessQuality("quality.integrated_checksheet_operation", "view", [
    "quality.integrated_checksheet_template",
    "quality",
  ])
)
const canViewIntegratedReview = computed(() =>
  canAccessQuality("quality.integrated_checksheet_review", "view", [], false)
)
const canViewIntegratedDashboard = computed(() =>
  canAccessQuality("quality.integrated_checksheet_operation", "view", [
    "quality.integrated_checksheet_review",
    "quality.integrated_checksheet_template",
    "quality",
  ])
)

const dsSources = [
  { section: "テンプレート管理" },
  { op: "読み書き", table: "quality_integrated_checksheet_template", desc: "工程一体チェックシートのテンプレート本体" },
  { op: "読み書き", table: "quality_integrated_cs_process_block", desc: "テンプレート内の工程ブロック定義" },
  { op: "読み書き", table: "quality_integrated_cs_item", desc: "工程ごとのチェック項目" },
  { op: "読み書き", table: "quality_integrated_cs_item_attachment", desc: "チェック項目ごとの付表画像・補足情報" },
  { op: "読み書き", table: "quality_integrated_cs_sketch_field", desc: "台紙画像上の配置フィールド定義" },
  { op: "承認フロー", table: "quality_integrated_cs_task / quality_integrated_cs_workflow_log", desc: "確認依頼・承認タスクと履歴" },
  { section: "チェック実施・確認" },
  { op: "バッチ管理", table: "quality_integrated_checksheet_batch", desc: "製品・ライン・計画日単位の実施バッチ" },
  { op: "台目管理", table: "quality_integrated_checksheet_unit", desc: "台目ごとの進捗・刻印番号" },
  { op: "チェック保存", table: "quality_integrated_cs_check", desc: "台目×チェック項目の入力結果" },
  { op: "台紙保存", table: "quality_integrated_cs_sketch_response", desc: "手書き・台紙フィールド回答・保留情報" },
  { op: "マスタ参照", table: "m_product / m_line / m_process", desc: "製品・ライン・工程の選択肢と表示名" },
]
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}
</style>
