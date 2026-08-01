<template>
  <div class="master-menu">
    <h2 class="page-title">{{ t('productionMenu.title') }}</h2>

    <div class="menu-sections">
      <section
        v-for="(section, index) in groupedTiles"
        :key="section.key"
        class="menu-section"
        :class="{ 'has-divider': index > 0 }"
      >
        <h3 class="section-title">{{ section.label }}</h3>
        <div class="master-grid">
          <RouterLink
            v-for="tile in section.items"
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
      </section>
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
const SECTION_ORDER = ["input", "plan", "records", "inventory", "other"];
const SECTION_LABELS = {
  input: "実績入力",
  records: "実績照会・分析",
  plan: "計画・設定",
  inventory: "在庫・進度",
  other: "その他",
};

const findPermission = (user, resource) => {
  if (!user) return null;
  const permissions = Array.isArray(user.effective_permissions)
    ? user.effective_permissions
    : [];
  return permissions.find((item) => item.resource === resource) || null;
};

const hasMenuPermission = (resource, level, fallbackToParent = true) => {
  const user = authState.user;
  if (!user) return false;
  if (user.is_superuser) return true;

  const entry = findPermission(user, resource);
  if (entry) {
    return level === "edit"
      ? Boolean(entry.can_edit)
      : Boolean(entry.can_view || entry.can_edit);
  }

  if (!fallbackToParent) return false;
  return hasPermission(user, "production", level);
};

const tiles = computed(() => {
  const list = [
    {
      to: "/production/camera-actual-input",
      label: "実績入力（カメラ）",
      icon: "📷",
      category: "input",
      required: "edit",
      resource: "production.process_input",
    },
    {
      to: "/production/mobile-process-input",
      label: t("productionMenu.tiles.processInput"),
      icon: "📱",
      category: "input",
      required: "edit",
      resource: "production.process_input",
    },
    {
      to: "/production/desktop-process-input",
      label: "工程作業入力（デスクトップ）",
      icon: "🖥️",
      category: "input",
      required: "edit",
      resource: "production.process_input",
    },
    // 未使用: 工程作業入力（タブレット） /production/tablet-process-input
    {
      to: "/production/dual-process-input",
      label: "１人２工程入力",
      icon: "👤",
      category: "input",
      required: "edit",
      resource: "production.process_input",
    },
    // 未使用: 同時加工入力 /production/simultaneous-process-input
    {
      to: "/production/two-person-one-equipment-input",
      label: "2人１設備",
      icon: "👥",
      category: "input",
      required: "edit",
      resource: "production.process_input",
    },
    {
      to: "/production/laser-process-input",
      label: "レーザー実績入力",
      icon: "✳",
      category: "input",
      required: "edit",
      resource: "production.process_input",
    },
    {
      to: "/production/brake-line-input",
      label: "ブレーキ実績入力",
      icon: "⤓",
      category: "input",
      required: "edit",
      resource: "production.process_input",
    },
    {
      to: "/production/spot-line-input",
      label: "スポット実績入力",
      icon: "⚡",
      category: "input",
      required: "edit",
      resource: "production.process_input",
    },
    {
      to: "/production/product-photo-upload",
      label: t("productionMenu.tiles.productPhotoUpload"),
      icon: "🖼️",
      category: "other",
      required: "edit",
      resource: "production.process_input",
    },
    {
      to: "/production/record-inquiry",
      label: t("productionMenu.tiles.productionRecordInquiry"),
      icon: "📑",
      category: "records",
      required: "view",
      resource: "production.record_inquiry",
    },
    {
      to: "/production/record-edit",
      label: t("productionMenu.tiles.productionRecordEdit"),
      icon: "✏️",
      category: "records",
      required: "edit",
      resource: "production.record_edit",
    },
    {
      to: "/production/scrap-record",
      label: t("productionMenu.tiles.scrapRecord"),
      icon: "🛠️",
      category: "records",
      required: "edit",
      resource: "production.scrap_record",
    },
    {
      to: "/production/plan-input",
      label: t("productionMenu.tiles.planInput"),
      icon: "📝",
      iconLabel: "計画",
      category: "plan",
      required: "edit",
      resource: "production.plan_input",
    },
    {
      to: "/production/single-process-plan",
      label: "単独計画",
      icon: "🔧",
      iconLabel: "単独",
      category: "plan",
      required: "edit",
      resource: "production.plan_input",
    },
    {
      to: "/production/plan-change-history",
      label: t("productionMenu.tiles.planChangeHistory"),
      icon: "🧾",
      iconLabel: "履歴",
      category: "plan",
      required: "view",
      resource: "production.plan_input",
    },
    {
      to: "/production/gantt-display-product-map",
      label: "ガントチャート設定",
      icon: "🗺️",
      category: "plan",
      required: "edit",
      resource: "production.plan_input",
    },
    {
      to: "/production/default-start-time",
      label: "ライン開始時刻設定",
      icon: "⏲",
      iconLabel: "時刻",
      category: "plan",
      required: "edit",
      resource: "production.plan_input",
    },
    {
      to: "/production/inventory",
      label: t("productionMenu.tiles.inventory"),
      icon: "📦",
      iconLabel: "在庫",
      category: "inventory",
      required: "view",
      resource: "production.inventory",
    },
    {
      to: "/production/component-inventory",
      label: t("productionMenu.tiles.componentInventory"),
      icon: "🧩",
      iconLabel: "部品",
      category: "inventory",
      required: "view",
      resource: "production.inventory",
    },
    {
      to: "/production/scrap-history",
      label: t("productionMenu.tiles.scrapHistory"),
      icon: "📜",
      category: "records",
      required: "view",
      resource: "production.scrap_history",
    },
    {
      to: "/production/plan-deviation-report",
      label: "計画乖離レポート",
      icon: "📊",
      iconLabel: "乖離",
      category: "records",
      required: "view",
      resource: "production.record_inquiry",
    },
    {
      to: "/production/load-calc-menu",
      label: "負荷計算",
      icon: "📉",
      iconLabel: "負荷",
      category: "plan",
      required: "view",
      resource: "production",
    },
    {
      to: "/production/progress-only",
      label: t("productionMenu.tiles.progressOnly"),
      icon: "📈",
      iconLabel: "進度",
      category: "inventory",
      required: "view",
      resource: "production.progress",
    },
    {
      to: "/production/line-calendars",
      label: t("productionMenu.tiles.lineCalendars"),
      icon: "⏱",
      iconLabel: "勤",
      category: "plan",
      required: "edit",
      resource: "production.line_calendars",
    },
    {
      to: "/production/safety-stock-list",
      label: t("productionMenu.tiles.safetyStockList"),
      icon: "🛡️",
      iconLabel: "安全",
      category: "inventory",
      required: "view",
      resource: "production.inventory",
    },
    {
      to: "/production/progress-pdf-compare",
      label: "進度PDF突合",
      icon: "🔍",
      iconLabel: "突合",
      category: "inventory",
      required: "view",
      resource: "production",
    },
    {
      to: "/production/morning-meetings",
      label: "朝礼",
      icon: "☀️",
      category: "other",
      required: "view",
      accent: true,
      resource: "production.morning_meeting",
    },
    {
      to: "/production/line-monitor",
      label: t("productionMenu.tiles.lineMonitor"),
      icon: "📺",
      category: "other",
      required: "view",
      accent: true,
      resource: "production.line_monitor",
    },
    {
      to: "/production/unused",
      label: t("productionMenu.tiles.unused"),
      icon: "🗄️",
      iconLabel: "未使用",
      category: "other",
      required: "view",
      resource: "production",
    },
    {
      to: "/production/product-info-editor",
      label: "製品情報編集",
      icon: "📸",
      category: "other",
      required: "edit",
      resource: "production.process_input",
    },
    {
      to: "/production/process-knowledge-viewer",
      label: "工程別コツ・注意事項",
      icon: "💡",
      category: "other",
      required: "view",
      resource: "production.process_knowledge",
      fallbackToParent: false,
    },
    {
      to: "/masters/mobile-device",
      label: "携帯端末管理",
      icon: "📱",
      category: "other",
      required: "view",
      resource: "masters.mobile_device",
    },
  ];

  return list.map((tile) => ({
    ...tile,
    disabled: !hasMenuPermission(tile.resource, tile.required, tile.fallbackToParent !== false),
  }));
});

const visibleTiles = computed(() => {
  if (PERMISSION_MODE === "hide") {
    return tiles.value.filter((tile) => !tile.disabled);
  }
  return tiles.value;
});

const groupedTiles = computed(() => {
  const buckets = SECTION_ORDER.map((key) => ({
    key,
    label: SECTION_LABELS[key],
    items: [],
  }));
  const indexMap = Object.fromEntries(SECTION_ORDER.map((key, index) => [key, index]));
  for (const tile of visibleTiles.value) {
    const key = tile.category && indexMap[tile.category] !== undefined ? tile.category : "other";
    buckets[indexMap[key]].items.push(tile);
  }
  return buckets.filter((section) => section.items.length);
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
.menu-sections {
  display: grid;
  gap: 14px;
}
.menu-section.has-divider {
  border-top: 1px solid #dbe2ea;
  padding-top: 14px;
}
.section-title {
  margin: 0 0 8px;
  font-size: 14px;
  color: #334155;
}
.master-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}
.master-tile {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px;
  min-height: 72px;
  text-decoration: none;
  color: inherit;
  background: #fff;
  display: grid;
  gap: 6px;
  align-content: center;
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

@media (max-width: 1400px) {
  .master-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 1100px) {
  .master-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 800px) {
  .master-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 520px) {
  .master-grid {
    grid-template-columns: 1fr;
  }
}
</style>
