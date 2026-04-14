<template>
  <div class="master-menu">
    <h2 class="page-title">設備点検表</h2>

    <div class="master-grid">
      <RouterLink v-if="canViewMaster" to="/quality/equipment-inspection/master" class="master-tile">
        <div class="icon-box">📝</div>
        <div class="label">点検項目作成</div>
      </RouterLink>
      <RouterLink v-if="canViewOperation" to="/quality/equipment-inspection/operation" class="master-tile">
        <div class="icon-box">🛠</div>
        <div class="label">点検実施</div>
      </RouterLink>
      <RouterLink v-if="canViewMonthly" to="/quality/equipment-inspection/monthly-review" class="master-tile">
        <div class="icon-box">📅</div>
        <div class="label">月間確認</div>
      </RouterLink>
    </div>

    <p class="helper-text">
      点検項目作成・日次実施・週次/月次確認を同じ設備点検表メニューで運用します。
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

const canViewMaster = computed(() => canAccessQuality("quality.equipment_inspection_master", "view"))
const canViewOperation = computed(() =>
  canAccessQuality("quality.equipment_inspection_operation", "view", ["quality.equipment_inspection"])
)
const canViewMonthly = computed(() =>
  canAccessQuality("quality.equipment_inspection_monthly_review", "view", ["quality.equipment_inspection"])
)
</script>
