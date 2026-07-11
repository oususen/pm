<template>
  <div class="master-menu">
    <h2 class="page-title">出荷管理メニュー</h2>

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
            :class="{ 'is-disabled': tile.disabled }"
            :aria-disabled="tile.disabled ? 'true' : 'false'"
            :tabindex="tile.disabled ? -1 : 0"
            @click="(event) => onTileClick(event, tile)"
          >
            <div class="icon-box">{{ tile.icon }}</div>
            <div class="label">{{ tile.label }}</div>
          </RouterLink>
        </div>
      </section>
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
const SECTION_ORDER = ["shipping_ops", "documents", "trip", "settings", "other"];
const SECTION_LABELS = {
  shipping_ops: "出荷業務",
  documents: "帳票",
  trip: "便計画・進捗",
  settings: "設定",
  other: "その他",
};

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
    category: "shipping_ops",
    required: "view",
    resource: "shipping.instruction",
  },
  {
    to: "/shipping/actual",
    label: "出荷実績",
    icon: "📦",
    category: "shipping_ops",
    required: "view",
    resource: "shipping.actual",
  },
  {
    to: "/shipping/actual-trace",
    label: "出荷実績追跡",
    icon: "🔎",
    category: "shipping_ops",
    required: "view",
    resource: "shipping.actual",
  },
  {
    to: "/shipping/progress",
    label: "出荷進度照会",
    icon: "📊",
    category: "shipping_ops",
    required: "view",
    resource: "shipping.progress",
  },
  {
    to: "/shipping/order-document",
    label: "出荷指示書",
    icon: "📄",
    category: "documents",
    required: "view",
    resource: "shipping.order_document",
  },
  {
    to: "/shipping/hirakata-pickup",
    label: "枚方集荷依頼書",
    icon: "📦",
    category: "documents",
    required: "view",
    resource: "shipping.hirakata_pickup",
  },
  {
    to: "/shipping/fujishoji-document",
    label: "富士商事出荷指示書",
    icon: "🏗️",
    category: "documents",
    required: "view",
    resource: "shipping.fujishoji_document",
  },
  {
    to: "/shipping/kubota-sakai-due-adjustment",
    label: "クボタ堺納期調整",
    icon: "🗓️",
    category: "trip",
    required: "view",
    resource: "shipping.kubota_sakai_due_adjustment",
  },
  {
    to: "/shipping/kubota-sakai-trip-planning",
    label: "クボタ堺便計画",
    icon: "🚛",
    category: "trip",
    required: "view",
    resource: "shipping.kubota_sakai_trip_planning",
  },
  {
    to: "/shipping/trip-execution",
    label: "便確認（出荷担当）",
    icon: "📱",
    category: "trip",
    required: "view",
    resource: "shipping.trip_execution",
  },
  {
    to: "/shipping/trip-progress",
    label: "便確認（業務員）",
    icon: "📈",
    category: "trip",
    required: "view",
    resource: "shipping.trip_progress",
  },
  {
    to: "/shipping/trip-progress-summary",
    label: "便進捗確認（一覧）",
    icon: "📋",
    category: "trip",
    required: "view",
    resource: "shipping.trip_progress_summary",
  },
  {
    to: "/shipping/ship-to-lead-time",
    label: "納入地別出荷加算日数",
    icon: "⚙️",
    category: "settings",
    required: "view",
    resource: "shipping.ship_to_lead_time",
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
