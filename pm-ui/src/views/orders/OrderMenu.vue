<template>
  <div class="master-menu">
    <h2 class="page-title">受注管理メニュー</h2>

    <div class="master-grid">
      <RouterLink
        v-for="tile in visibleTiles"
        :key="tile.key"
        :to="tile.to || '#'"
        class="master-tile"
        :class="{ 'is-disabled': tile.disabled }"
        :aria-disabled="tile.disabled ? 'true' : 'false'"
        :tabindex="tile.disabled ? -1 : 0"
        @click="(event) => onTileClick(event, tile)"
      >
        <div class="icon-box">{{ tile.icon }}</div>
        <div class="label" v-html="tile.label"></div>
        <template v-if="tile.key === 'line_expand'">
          <button
            class="action-btn"
            :disabled="running"
            @click.prevent="runExpand"
          >
            {{ running ? '展開中...' : '展開実行' }}
          </button>
          <div v-if="message" class="status-text">{{ message }}</div>
          <ul v-if="warnings.length" class="warn-list">
            <li v-for="(w, idx) in warnings" :key="idx">{{ w }}</li>
          </ul>
        </template>
      </RouterLink>
    </div>

    <p class="helper-text">
      展開実行でOPEN受注をライン別需要に再生成します。
    </p>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { RouterLink } from "vue-router";
import { authState } from "@/auth";
import { hasPermission } from "@/router";
import api from "@/api/client";

const PERMISSION_MODE = "hide";

const running = ref(false);
const message = ref("");
const warnings = ref([]);

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

  // サブリソース未設定の場合は親（orders）の権限にフォールバック
  return hasPermission(user, "orders", level);
};

const tiles = computed(() => [
  {
    key: "list",
    to: "/orders",
    label: "受注一覧",
    icon: "📑",
    required: "view",
    resource: "orders.list",
  },
  {
    key: "csv_import",
    to: "/csv-upload",
    label: "受注取込",
    icon: "📤",
    required: "edit",
    resource: "orders.csv_import",
  },
  {
    key: "first_article_setting",
    to: "/orders/first-article-setting",
    label: "お久しぶり製品<br>通知設定",
    icon: "🔔",
    required: "edit",
    resource: "orders",
  },
  {
    key: "missing_routing_items",
    to: "/orders/missing-routing-items",
    label: "ルーティング未設定の注文品",
    icon: "⚠️",
    required: "view",
    resource: "orders.list",
  },
  {
    key: "kubota_analysis",
    to: "/orders/kubota-naiji-analysis",
    label: "クボタ内示分析",
    icon: "📊",
    required: "view",
    resource: "orders.kubota_analysis",
  },
  {
    key: "naiji_analysis",
    to: "/orders/naiji-analysis",
    label: "内示分析",
    icon: "📈",
    required: "view",
    resource: "orders.naiji_analysis",
  },
  {
    key: "line_expand",
    to: null,
    label: "ライン展開",
    icon: "🛠️",
    required: "edit",
    resource: "orders.line_expand",
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
  if (tile.disabled || !tile.to) {
    event.preventDefault();
  }
};

const runExpand = async () => {
  if (running.value) return;
  running.value = true;
  message.value = "";
  warnings.value = [];

  try {
    const res = await api.lineDemands.expand(true);
    const data = res.data || {};
    message.value = `展開完了: created=${data.created ?? 0}, cleared=${data.cleared ?? 0}`;
    warnings.value = data.warnings || [];
  } catch (e) {
    const detail = e?.response?.data?.error || e.message || "unknown error";
    message.value = `展開エラー: ${detail}`;
  } finally {
    running.value = false;
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
.action-btn {
  width: 100%;
  padding: 8px 0;
  background: #284b8f;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.status-text {
  margin-top: 6px;
  font-size: 12px;
  color: #1a3a7a;
}
.warn-list {
  margin: 6px 0 0;
  padding-left: 16px;
  color: #a05a00;
  font-size: 12px;
}
.helper-text {
  margin-top: 10px;
  color: #64748b;
}
</style>
