<template>
  <div class="master-menu">
    <h2 class="page-title">{{ t('productionUnusedMenu.title') }}</h2>

    <div class="master-grid">
      <RouterLink
        v-for="tile in visibleTiles"
        :key="tile.to"
        :to="tile.to"
        class="master-tile"
        :class="{ accent: tile.accent, 'is-disabled': tile.disabled }"
        :aria-disabled="tile.disabled ? 'true' : 'false'"
        :tabindex="tile.disabled ? -1 : 0"
        @click="(event) => onTileClick(event, tile)"
      >
        <div class="icon-box" :aria-label="tile.iconLabel || null">{{ tile.icon }}</div>
      <div class="label">{{ tile.label }}</div>
      </RouterLink>
    </div>

    <p class="helper-text">
      {{ t('productionUnusedMenu.helper') }}
    </p>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { authState } from "@/auth";
import { hasPermission } from "@/router";
import { t } from "@/i18n";

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

  return hasPermission(user, "production", level);
};

const tiles = computed(() => {
  const list = [
    {
      to: "/production/progress",
      label: t("productionMenu.tiles.progress"),
      icon: "📊",
      iconLabel: "進捗",
      required: "view",
      resource: "production.progress",
    },
    {
      to: "/production/line-demands",
      label: t("productionMenu.tiles.lineDemands"),
      icon: "📈",
      iconLabel: "需要",
      required: "view",
      resource: "production.line_demands",
    },
    {
      to: "/production/stock-allocations",
      label: t("productionMenu.tiles.stockAllocations"),
      icon: "🎯",
      iconLabel: "引当",
      required: "edit",
      resource: "production.stock_allocations",
    },
    {
      to: "/production/orders",
      label: t("productionMenu.tiles.orders"),
      icon: "🛠️",
      iconLabel: "指示",
      required: "edit",
      resource: "production.orders",
    },
    {
      to: "/production/sequence-board",
      label: t("productionMenu.tiles.sequenceBoard"),
      icon: "🎛",
      required: "view",
      accent: true,
      resource: "production.sequence_board",
    },
    {
      to: "/production/mobile-input",
      label: t("productionMenu.tiles.mobileInput"),
      icon: "📱",
      required: "edit",
      resource: "production.mobile_input",
    },
    {
      to: "/production/tablet-process-input",
      label: "工程作業入力（タブレット）",
      icon: "💻",
      required: "edit",
      resource: "production.process_input",
    },
    {
      to: "/production/simultaneous-process-input",
      label: t("productionMenu.tiles.simultaneousInput"),
      icon: "🔄",
      required: "edit",
      resource: "production.process_input",
    },
  ];

  return list.map((tile) => ({
    ...tile,
    disabled: !hasMenuPermission(tile.resource, tile.required),
  }));
});

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
.master-tile.accent {
  border: 1px solid #4f46e5;
  box-shadow: 0 6px 16px rgba(79, 70, 229, 0.18);
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

