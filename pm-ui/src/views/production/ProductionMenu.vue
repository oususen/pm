<template>
  <div class="master-menu">
    <h2 class="page-title">{{ t('productionMenu.title') }}</h2>

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
      {{ t('productionMenu.helper') }}
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
      to: "/production/mobile-process-input",
      label: t("productionMenu.tiles.processInput"),
      icon: "📱",
      required: "edit",
      resource: "production.process_input",
    },
    {
      to: "/production/laser-process-input",
      label: "レーザー実績入力",
      icon: "🧱",
      required: "edit",
      resource: "production.process_input",
    },
    {
      to: "/production/brake-line-input",
      label: "ブレーキライン実績入力",
      icon: "🔧",
      required: "edit",
      resource: "production.process_input",
    },
    {
      to: "/production/spot-line-input",
      label: "スポット実績入力",
      icon: "⚡",
      required: "edit",
      resource: "production.process_input",
    },
    {
      to: "/production/record-inquiry",
      label: t("productionMenu.tiles.productionRecordInquiry"),
      icon: "📑",
      required: "view",
      resource: "production.record_inquiry",
    },
    {
      to: "/production/record-edit",
      label: t("productionMenu.tiles.productionRecordEdit"),
      icon: "✏️",
      required: "edit",
      resource: "production.record_edit",
    },
    {
      to: "/production/scrap-record",
      label: t("productionMenu.tiles.scrapRecord"),
      icon: "🛠️",
      required: "edit",
      resource: "production.scrap_record",
    },
    {
      to: "/production/plan-input",
      label: t("productionMenu.tiles.planInput"),
      icon: "📝",
      iconLabel: "計画",
      required: "edit",
      resource: "production.plan_input",
    },
    {
      to: "/production/plan-change-history",
      label: t("productionMenu.tiles.planChangeHistory"),
      icon: "🧾",
      iconLabel: "履歴",
      required: "view",
      resource: "production.plan_input",
    },
    {
      to: "/production/default-start-time",
      label: t("productionMenu.tiles.defaultStart"),
      icon: "⏲",
      iconLabel: "時刻",
      required: "edit",
      resource: "production.plan_input",
    },
    {
      to: "/production/inventory",
      label: t("productionMenu.tiles.inventory"),
      icon: "📦",
      iconLabel: "在庫",
      required: "view",
      resource: "production.inventory",
    },
    {
      to: "/production/component-inventory",
      label: t("productionMenu.tiles.componentInventory"),
      icon: "🧩",
      iconLabel: "部品",
      required: "view",
      resource: "production.component_inventory",
    },
    {
      to: "/production/scrap-history",
      label: t("productionMenu.tiles.scrapHistory"),
      icon: "📜",
      required: "view",
      resource: "production.scrap_history",
    },
    {
      to: "/production/progress-only",
      label: t("productionMenu.tiles.progressOnly"),
      icon: "📈",
      iconLabel: "進度",
      required: "view",
      resource: "production.progress",
    },
    {
      to: "/production/line-calendars",
      label: t("productionMenu.tiles.lineCalendars"),
      icon: "⏱",
      iconLabel: "勤",
      required: "edit",
      resource: "production.line_calendars",
    },
    {
      to: "/production/safety-stock-list",
      label: t("productionMenu.tiles.safetyStockList"),
      icon: "🛡️",
      iconLabel: "安全",
      required: "view",
      resource: "production.inventory",
    },
    {
      to: "/production/line-monitor",
      label: t("productionMenu.tiles.lineMonitor"),
      icon: "📺",
      required: "view",
      accent: true,
      resource: "production.line_monitor",
    },
    {
      to: "/production/unused",
      label: t("productionMenu.tiles.unused"),
      icon: "🗄️",
      iconLabel: "未使用",
      required: "view",
      resource: "production",
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
