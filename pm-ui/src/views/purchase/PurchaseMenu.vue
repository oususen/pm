<template>
  <div class="master-menu">
    <h2 class="page-title">仕入れ管理メニュー</h2>

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
const SECTION_ORDER = ["records", "plan", "inventory", "other"];
const SECTION_LABELS = {
  records: "実績・発注",
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
    category: "plan",
    required: "edit",
    resource: "purchase.plan_input",
  },
  {
    to: "/purchase/inventory",
    label: "在庫/残量",
    icon: "📊",
    category: "inventory",
    required: "view",
    resource: "purchase.inventory",
  },
  {
    to: "/purchase/progress-only",
    label: "仕入れ進度のみ",
    icon: "📈",
    category: "inventory",
    required: "view",
    resource: "purchase.progress",
  },
  {
    to: "/purchase/receiving",
    label: "仕入れ検収",
    icon: "📥",
    category: "records",
    required: "edit",
    resource: "purchase.receiving",
  },
  {
    to: "/purchase/actual-input",
    label: "仕入れ実績入力",
    icon: "🧾",
    category: "records",
    required: "edit",
    resource: "purchase.actual_input",
  },
  {
    to: "/purchase/actual-inquiry",
    label: "納入実績照会",
    icon: "📋",
    category: "records",
    required: "view",
    resource: "purchase.actual_inquiry",
  },
  {
    to: "/purchase/actual-edit",
    label: "納入実績編集",
    icon: "✏️",
    category: "records",
    required: "edit",
    resource: "purchase.actual_input",
  },
  {
    to: "/purchase/supplier-calendar",
    label: "仕入れ先カレンダ",
    icon: "🗓️",
    category: "plan",
    required: "edit",
    resource: "purchase.supplier_calendar",
  },
  {
    to: "/settings/supplier-order-pattern",
    label: "納入パターン設定",
    icon: "🔄",
    category: "plan",
    required: "view",
    resource: "settings.supplier_order_schedule",
  },
  {
    to: "/settings/supplier-order-schedule",
    label: "仕入れ先スケジュール設定",
    icon: "📅",
    category: "plan",
    required: "view",
    resource: "settings.supplier_order_schedule",
  },
  {
    to: "/settings/purchase-order-approval",
    label: "発注承認者設定",
    icon: "✅",
    category: "plan",
    required: "view",
    resource: "settings.purchase_order_approval",
  },
  {
    to: "/purchase/order-proposals",
    label: "発注業務",
    icon: "📝",
    category: "records",
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

