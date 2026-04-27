<template>
  <div class="master-menu">
    <h2 class="page-title">品質チェックシート</h2>

    <div class="master-grid">
      <RouterLink v-if="canViewTemplate" to="/quality/product-checksheet/templates" class="master-tile">
        <div class="icon-box">📝</div>
        <div class="label">品質チェックシート作成</div>
      </RouterLink>
      <RouterLink v-if="canViewOperation" to="/quality/product-checksheet/quality" class="master-tile">
        <div class="icon-box">🛠</div>
        <div class="label">品質チェックシート実施</div>
      </RouterLink>
    </div>

    <p class="helper-text">
      チェックシート台紙の作成・承認と、製造時の品質チェックシート実施を行います。
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
  canAccessQuality("quality.product_checksheet_review", "view", ["quality.product_checksheet_template"])
)
</script>
