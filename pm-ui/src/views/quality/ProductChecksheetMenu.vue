<template>
  <div class="master-menu">
    <h2 class="page-title">品質チェックシート</h2>

    <h3 class="section-title">A案: 台紙方式（現行）</h3>
    <div class="master-grid">
      <RouterLink v-if="canViewTemplate" to="/quality/product-checksheet/templates" class="master-tile">
        <div class="icon-box">📝</div>
        <div class="label">チェックシート作成</div>
      </RouterLink>
      <RouterLink v-if="canViewOperation" to="/quality/product-checksheet/operation" class="master-tile">
        <div class="icon-box">🛠</div>
        <div class="label">チェック実施</div>
      </RouterLink>
      <RouterLink v-if="canViewReview" to="/quality/product-checksheet/quality" class="master-tile">
        <div class="icon-box">✅</div>
        <div class="label">品質確認</div>
      </RouterLink>
    </div>

    <h3 class="section-title">B案: 工程一体方式（新規）</h3>
    <div class="master-grid">
      <RouterLink
        v-if="canViewIntegratedTemplate"
        to="/quality/product-checksheet/integrated/templates"
        class="master-tile"
      >
        <div class="icon-box">B-T</div>
        <div class="label">テンプレート管理</div>
      </RouterLink>
      <RouterLink
        v-if="canViewIntegratedOperation"
        to="/quality/product-checksheet/integrated/operation"
        class="master-tile"
      >
        <div class="icon-box">B-O</div>
        <div class="label">チェック実施</div>
      </RouterLink>
    </div>

    <p class="helper-text">
      A案（台紙方式）とB案（工程一体方式）の機能に遷移します。
    </p>
  </div>
</template>

<script setup>
import { computed } from "vue"
import { RouterLink } from "vue-router"
import { authState } from "@/auth"
import { hasPermission } from "@/router"

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

const canViewTemplate = computed(() => canAccessQuality("quality.product_checksheet_template", "view"))
const canViewOperation = computed(() =>
  canAccessQuality("quality.product_checksheet_input", "view", [
    "quality.product_checksheet_operation",
    "quality.product_checksheet_template",
    "quality",
  ])
)
const canViewReview = computed(() =>
  canAccessQuality("quality.product_checksheet_review", "view", ["quality.product_checksheet_template"])
)
const canViewIntegratedTemplate = computed(() =>
  canAccessQuality("quality.product_checksheet_template", "view", [
    "quality.integrated_checksheet_template",
    "quality",
  ])
)
const canViewIntegratedOperation = computed(() =>
  canAccessQuality("quality.product_checksheet_input", "view", [
    "quality.integrated_checksheet_operation",
    "quality.integrated_checksheet_template",
    "quality",
  ])
)
</script>
