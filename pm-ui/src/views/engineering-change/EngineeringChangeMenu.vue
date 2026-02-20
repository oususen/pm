<template>
  <div class="master-menu">
    <h2 class="page-title">設変新規管理メニュー</h2>

    <p v-if="!canView" class="helper-text">この画面を閲覧する権限がありません。</p>

    <div v-else class="master-grid">
      <RouterLink to="/engineering-change/new" class="master-tile" :class="{ disabled: !canEdit }">
        <div class="icon-box">🆕</div>
        <div class="label">新規タイル</div>
      </RouterLink>
      <RouterLink to="/engineering-change/change" class="master-tile">
        <div class="icon-box">🔁</div>
        <div class="label">設変タイル</div>
      </RouterLink>
    </div>

    <p class="helper-text">打ち切り製品の設変部品に対する過剰仕入れ・過剰生産を管理します。</p>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { authState } from "@/auth";
import { hasPermission } from "@/router";
import { RouterLink } from "vue-router";

const canAccessEngineeringChange = (level = "view") => {
  const user = authState.user;
  if (!user) return false;
  return hasPermission(user, "engineering_change", level);
};

const canView = computed(() => canAccessEngineeringChange("view"));
const canEdit = computed(() => canAccessEngineeringChange("edit"));
</script>

<style scoped>
.master-menu {
  padding: 16px;
}
.master-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}
.master-tile {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px;
  text-decoration: none;
  color: inherit;
  background: #fff;
  display: grid;
  gap: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
}
.master-tile.disabled {
  pointer-events: none;
  opacity: 0.45;
}
.master-tile .icon-box {
  font-size: 22px;
}
.master-tile .label {
  font-weight: 700;
}
.helper-text {
  margin-top: 10px;
  color: #64748b;
}
</style>
