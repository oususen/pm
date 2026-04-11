<template>
  <div class="master-menu">
    <h2 class="page-title">仕入れ管理メニュー</h2>

    <div class="master-grid">
      <RouterLink
        v-for="tile in visibleTiles"
        :key="tile.to"
        :to="tile.to"
        class="master-tile"
        :class="{ 'is-disabled': tile.disabled }"
        :aria-disabled="tile.disabled ? 'true' : 'false'"
        :tabindex="tile.disabled ? -1 : 0"
        @click="(event) => onTileClick(event, tile)"
      >
        <div class="icon-box">{{ tile.icon }}</div>
        <div class="label">{{ tile.label }}</div>
      </RouterLink>
    </div>

    <p class="helper-text">
      仕入れ管理メニューから各機能に遷移します。
    </p>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { authState } from "@/auth";
import { hasPermission } from "@/router";

const PERMISSION_MODE = "hide"; // "disable" or "hide"

const findPermission = (user, resource) => {
  if (!user) return null;
  const permissions = Array.isArray(user.effective_permissions)
    ? user.effective_permissions
    : [];
  return permissions.find((item) => item.resource === resource) || null;
};

const hasMenuPermission = (resource, level) => {
  const user = authState.user;
  if (!user) return false;
  if (user.is_superuser) return true;

  const entry = findPermission(user, resource);
  if (entry) {
    return level === "edit"
      ? Boolean(entry.can_edit)
      : Boolean(entry.can_view || entry.can_edit);
  }

  return hasPermission(user, "purchase", level);
};

const tiles = computed(() => [
  {
    to: "/purchase/plan-input",
    label: "仕入れ計画",
    icon: "📦",
    required: "edit",
    resource: "purchase.plan_input",
  },
  {
    to: "/purchase/inventory",
    label: "在庫/残量",
    icon: "📊",
    required: "view",
    resource: "purchase.inventory",
  },
  {
    to: "/purchase/progress-only",
    label: "仕入れ進度のみ",
    icon: "📈",
    required: "view",
    resource: "purchase.progress",
  },
  {
    to: "/purchase/actual-input",
    label: "仕入れ実績入力",
    icon: "🧾",
    required: "edit",
    resource: "purchase.actual_input",
  },
  {
    to: "/purchase/actual-inquiry",
    label: "納入実績照会",
    icon: "📋",
    required: "view",
    resource: "purchase.actual_inquiry",
  },
  {
    to: "/purchase/actual-edit",
    label: "納入実績編集",
    icon: "✏️",
    required: "edit",
    resource: "purchase.actual_input",
  },
  {
    to: "/purchase/supplier-calendar",
    label: "仕入れ先カレンダ",
    icon: "🗓️",
    required: "edit",
    resource: "purchase.supplier_calendar",
  },
  {
    to: "/purchase/order-proposals",
    label: "発注業務",
    icon: "📝",
    required: "view",
    resource: "purchase.order_proposals",
  },
].map((tile) => ({
  ...tile,
  disabled: !hasMenuPermission(tile.resource, tile.required),
})));

const visibleTiles = computed(() => {
  if (PERMISSION_MODE === "hide") {
    return tiles.value.filter((tile) => !tile.disabled);
  }
  return tiles.value;
});

const onTileClick = (event, tile) => {
  if (tile.disabled) {
    event.preventDefault();
  }
};
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
.master-tile .icon-box {
  font-size: 22px;
}
.master-tile .label {
  font-weight: 700;
}
.master-tile.is-disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}
.helper-text {
  margin-top: 10px;
  color: #64748b;
}
</style>
