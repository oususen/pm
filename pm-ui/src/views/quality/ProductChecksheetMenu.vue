<template>
  <div class="master-menu">
    <h2 class="page-title">工程一体チェックシート</h2>

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
</script>
