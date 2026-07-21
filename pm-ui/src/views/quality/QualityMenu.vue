<template>
  <div class="master-menu">
    <h2 class="page-title">品質管理メニュー</h2>

    <div class="master-grid">
      <RouterLink v-if="canViewEquipment" to="/quality/equipment-inspection" class="master-tile">
        <div class="icon-box">🧰</div>
        <div class="label">設備点検表</div>
      </RouterLink>
      <RouterLink v-if="canViewChecksheet" to="/quality/product-checksheet" class="master-tile">
        <div class="icon-box">CS</div>
        <div class="label">品質チェックシート</div>
      </RouterLink>
      <RouterLink v-if="canViewTrainingCertification" to="/quality/training-certification" class="master-tile">
        <div class="icon-box">教認</div>
        <div class="label">教育・テスト・認定</div>
      </RouterLink>
    </div>

    <p class="helper-text">
      品質管理メニューから各機能に遷移します。
    </p>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { authState } from "@/auth";
import { hasPermission } from "@/router";

const canAccessQuality = (resource, level = "view", aliases = []) => {
  const user = authState.user;
  if (!user) return false;
  if (user.is_superuser) return true;
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : [];
  const candidates = [resource, ...aliases];
  const hasSpecific = permissions.some((item) => candidates.includes(item.resource));
  if (hasSpecific) return candidates.some((candidate) => hasPermission(user, candidate, level));
  return hasPermission(user, "quality", level);
};

const canViewEquipment = computed(() =>
  canAccessQuality("quality.equipment_inspection_master", "view", [
    "quality.equipment_inspection_operation",
    "quality.equipment_inspection_monthly_review",
  ])
);
const canViewChecksheet = computed(() =>
  canAccessQuality("quality.product_checksheet_template", "view", [
    "quality.product_checksheet_input",
    "quality.product_checksheet_review",
  ])
);
const canViewTrainingCertification = computed(() => canAccessQuality("quality"));
</script>

