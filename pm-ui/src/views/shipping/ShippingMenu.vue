<template>
  <div class="master-menu">
    <h2 class="page-title">出荷管理メニュー</h2>

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
      出荷管理メニューから各機能に遷移します。
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

  return hasPermission(user, "shipping", level);
};

const tiles = computed(() => [
  {
    to: "/shipping/instruction",
    label: "出荷指示",
    icon: "🚚",
    required: "view",
    resource: "shipping.instruction",
  },
  {
    to: "/shipping/actual",
    label: "出荷実績",
    icon: "📦",
    required: "view",
    resource: "shipping.actual",
  },
  {
    to: "/shipping/progress",
    label: "出荷進度照会",
    icon: "📊",
    required: "view",
    resource: "shipping.progress",
  },
  {
    to: "/shipping/order-document",
    label: "出荷指示書",
    icon: "📄",
    required: "view",
    resource: "shipping.order_document",
  },
  {
    to: "/shipping/hirakata-pickup",
    label: "枚方集荷依頼書",
    icon: "📦",
    required: "view",
    resource: "shipping.hirakata_pickup",
  },
  {
    to: "/shipping/fujishoji-document",
    label: "富士商事出荷指示書",
    icon: "🏗️",
    required: "view",
    resource: "shipping.fujishoji_document",
  },
  {
    to: "/shipping/kubota-sakai-due-adjustment",
    label: "クボタ堺納期調整",
    icon: "🗓️",
    required: "view",
    resource: "shipping.kubota_sakai_due_adjustment",
  },
  {
    to: "/shipping/kubota-sakai-due-adjustment-2",
    label: "クボタ堺納期調整２",
    icon: "🗓️",
    required: "view",
    resource: "shipping.kubota_sakai_due_adjustment",
  },
  {
    to: "/shipping/kubota-sakai-trip-planning",
    label: "クボタ堺便計画",
    icon: "🚛",
    required: "view",
    resource: "shipping.kubota_sakai_trip_planning",
  },
  {
    to: "/shipping/kubota-sakai-trip-planning-2",
    label: "クボタ堺便計画２",
    icon: "🚛",
    required: "view",
    resource: "shipping.kubota_sakai_trip_planning",
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
