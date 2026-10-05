<template>
  <div class="master-menu">
    <h2 class="page-title">受注管理メニュー <DataSourceDialog title="受注管理メニュー" :sources="dsSources" /></h2>

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
            <template v-if="tile.key === 'order_expand'">
              <div class="action-stack">
                <button
                  class="action-btn"
                  :disabled="expansionBusy"
                  @click.prevent="runExpand"
                >
                  {{ orderRunning ? '展開中...' : '展開実行' }}
                </button>
              </div>
              <div v-if="orderMessage" class="status-text">{{ orderMessage }}</div>
              <ul v-if="orderWarnings.length" class="warn-list">
                <li v-for="(w, idx) in orderWarnings" :key="idx">{{ w }}</li>
              </ul>
            </template>
            <template v-if="tile.key === 'line_expand'">
              <div class="action-stack">
                <button
                  class="action-btn"
                  :disabled="expansionBusy"
                  @click.prevent="runFullExpand"
                >
                  {{ maintenanceRunning && maintenanceMode === 'full' ? '展開中...' : '全期間展開実行' }}
                </button>
                <div class="sub-action-row">
                  <button
                    class="sub-action-btn"
                    :disabled="expansionBusy"
                    @click.prevent="openMaintenanceDialog('revert')"
                  >
                    {{ maintenanceRunning && maintenanceMode === 'revert' ? '戻し中...' : '展開戻し' }}
                  </button>
                  <button
                    class="sub-action-btn secondary"
                    :disabled="expansionBusy"
                    @click.prevent="openMaintenanceDialog('expand')"
                  >
                    {{ maintenanceRunning && maintenanceMode === 'expand' ? '再展開中...' : '再展開' }}
                  </button>
                </div>
              </div>
              <div v-if="message" class="status-text">{{ message }}</div>
              <ul v-if="warnings.length" class="warn-list">
                <li v-for="(w, idx) in warnings" :key="idx">{{ w }}</li>
              </ul>
            </template>
          </RouterLink>
        </div>
      </section>
    </div>

    <p class="helper-text">
      受注展開は自動展開と同じ処理です。全期間展開実行はライン需要を全件削除し、すべてのOPEN確定・内示受注から再構築します。
    </p>

    <div v-if="showMaintenanceDialog" class="dialog-backdrop" @click.self="closeMaintenanceDialog">
      <div class="dialog-card">
        <div class="dialog-head">
          <h3>{{ maintenanceTitle }}</h3>
          <button type="button" class="plain-btn" @click="closeMaintenanceDialog">×</button>
        </div>
        <div class="dialog-body">
          <div class="form-row">
            <label>完成品コード</label>
            <input v-model.trim="maintenanceForm.productCode" type="text" placeholder="例: V053143615" />
          </div>
          <div class="form-row">
            <label>{{ maintenanceMode === 'revert' ? '戻し開始日' : '再展開開始日' }}</label>
            <input v-model="maintenanceForm.startDate" type="date" :disabled="maintenanceRunning" />
          </div>
          <div class="form-row">
            <label>{{ maintenanceMode === 'revert' ? '戻し終了日' : '再展開終了日' }}</label>
            <input v-model="maintenanceForm.endDate" type="date" />
          </div>
          <p class="dialog-note">{{ maintenanceNote }}</p>
          <p v-if="maintenanceMode === 'revert'" class="dialog-warning">
            LT（リードタイム）を変更する場合は、変更前のLTのまま展開戻し → LT変更 → 同じ対象の再展開の順で操作してください。
            先にLTを変更すると展開済み需要と一致せず、差し戻しできない場合があります。指定期間は受注の納期範囲です。
          </p>
          <p v-if="maintenanceError" class="dialog-error">{{ maintenanceError }}</p>
        </div>
        <div class="dialog-actions">
          <button type="button" @click="closeMaintenanceDialog" :disabled="maintenanceRunning">キャンセル</button>
          <button
            type="button"
            :class="maintenanceMode === 'revert' ? 'sub-action-btn' : 'sub-action-btn secondary'"
            @click="submitMaintenance"
            :disabled="maintenanceRunning"
          >
            {{ maintenanceRunning ? "実行中..." : maintenanceSubmitLabel }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { RouterLink } from "vue-router";
import { authState } from "@/auth";
import { hasPermission } from "@/router";
import api from "@/api/client";
import DataSourceDialog from "@/components/DataSourceDialog.vue";

const dsSources = [
  { op: "読み書き", table: "t_order", desc: "受注ヘッダ" },
  { op: "読み書き", table: "t_order_line", desc: "受注明細" },
  { op: "読み書き", table: "t_stg_order_raw", desc: "CSV生データ" },
  { op: "読み書き", table: "t_stg_order_daily", desc: "日次受注ステージング" },
  { op: "読み取り", table: "m_customer", desc: "得意先マスタ" },
  { op: "読み取り", table: "m_product", desc: "製品マスタ" },
  { op: "読み書き", table: "t_line_demand", desc: "ライン別需要（展開先）" },
  { op: "読み書き", table: "t_first_article_notice_log", desc: "お久しぶり製品通知履歴" },
  { op: "読み取り", table: "system_settings", desc: "お久しぶり通知設定" },
];

const PERMISSION_MODE = "hide";
const SECTION_ORDER = ["order_ops", "analysis", "settings", "other"];
const SECTION_LABELS = {
  order_ops: "受注業務",
  analysis: "分析・監査",
  settings: "設定",
  other: "その他",
};

const message = ref("");
const warnings = ref([]);
const orderRunning = ref(false);
const orderMessage = ref("");
const orderWarnings = ref([]);
const showMaintenanceDialog = ref(false);
const maintenanceMode = ref("revert");
const maintenanceRunning = ref(false);
const expansionBusy = computed(() => orderRunning.value || maintenanceRunning.value);
const maintenanceError = ref("");
const maintenanceForm = ref({
  productCode: "",
  startDate: "",
  endDate: "",
});
const maintenanceTitle = computed(() => (maintenanceMode.value === "revert" ? "受注展開の戻し" : "受注展開の再展開"));
const maintenanceSubmitLabel = computed(() => (maintenanceMode.value === "revert" ? "展開戻し実行" : "再展開実行"));
const maintenanceNote = computed(() => (
  maintenanceMode.value === "revert"
    ? "対象期間のOPEN確定受注のうち、展開済み分だけを差し戻します。"
    : "対象期間のOPEN確定受注のうち、未展開分だけを再展開します。"
));

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
    category: "order_ops",
    required: "view",
    resource: "orders.list",
  },
  {
    key: "csv_import",
    to: "/csv-upload",
    label: "受注取込",
    icon: "📤",
    category: "order_ops",
    required: "edit",
    resource: "orders.csv_import",
  },
  {
    key: "manual_entry",
    to: "/orders/manual-entry",
    label: "手動注文入力",
    icon: "✏️",
    category: "order_ops",
    required: "edit",
    resource: "orders.manual_entry",
  },
  {
    key: "first_article_setting",
    to: "/orders/first-article-setting",
    label: "お久しぶり製品<br>通知設定",
    icon: "🔔",
    category: "settings",
    required: "edit",
    resource: "orders.first_article",
  },
  {
    key: "kubota_import_setting",
    to: "/settings/kubota-import",
    label: "クボタ堺確定<br>通知設定",
    icon: "📧",
    category: "settings",
    required: "edit",
    resource: "settings.kubota_import",
  },
  {
    key: "missing_routing_items",
    to: "/orders/missing-routing-items",
    label: "ルーティング未設定の注文品",
    icon: "⚠️",
    category: "analysis",
    required: "view",
    resource: "orders.list",
  },
  {
    key: "open_order_audit",
    to: "/orders/open-order-audit",
    label: "旧OPEN受注洗い出し",
    icon: "🧾",
    category: "analysis",
    required: "view",
    resource: "orders.list",
  },
  {
    key: "kubota_analysis",
    to: "/orders/kubota-naiji-analysis",
    label: "クボタ内示分析",
    icon: "📊",
    category: "analysis",
    required: "view",
    resource: "orders.kubota_analysis",
  },
  {
    key: "naiji_analysis",
    to: "/orders/naiji-analysis",
    label: "内示分析",
    icon: "📈",
    category: "analysis",
    required: "view",
    resource: "orders.naiji_analysis",
  },
  {
    key: "order_expand",
    to: null,
    label: "受注展開",
    icon: "📥",
    category: "order_ops",
    required: "edit",
    resource: "orders.line_expand",
  },
  {
    key: "line_expand",
    to: null,
    label: "展開メンテ",
    icon: "🛠️",
    category: "order_ops",
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
  if (tile.disabled || !tile.to) {
    event.preventDefault();
  }
};

const runExpand = async () => {
  if (expansionBusy.value) return;
  const activeRunning = orderRunning;
  const activeMessage = orderMessage;
  const activeWarnings = orderWarnings;
  activeRunning.value = true;
  activeMessage.value = "";
  activeWarnings.value = [];

  try {
    const res = await api.lineDemands.expand(false);
    const data = res.data || {};
    activeMessage.value = `展開完了: 作成=${data.created ?? 0}, 更新=${data.updated ?? 0}, クリア=${data.cleared ?? 0}`;
    activeWarnings.value = data.warnings || [];
  } catch (e) {
    const detail = e?.response?.data?.errors?.join('\n') || e?.response?.data?.error || e.message || "unknown error";
    activeMessage.value = `展開エラー: ${detail}`;
    activeWarnings.value = e?.response?.data?.warnings || [];
  } finally {
    activeRunning.value = false;
  }
};

const runFullExpand = async () => {
  if (expansionBusy.value) return;
  maintenanceMode.value = "full";
  maintenanceRunning.value = true;
  message.value = "";
  warnings.value = [];

  try {
    const res = await api.lineDemands.expand(true);
    const data = res.data || {};
    message.value = `全期間展開完了: 作成=${data.created ?? 0}, クリア=${data.cleared ?? 0}, 確定展開=${data.processed_order_lines ?? 0}`;
    warnings.value = data.warnings || [];
  } catch (e) {
    const detail = e?.response?.data?.errors?.join('\n') || e?.response?.data?.error || e.message || "unknown error";
    message.value = `全期間展開エラー: ${detail}`;
    warnings.value = e?.response?.data?.warnings || [];
  } finally {
    maintenanceRunning.value = false;
  }
};

const openMaintenanceDialog = (mode) => {
  if (expansionBusy.value) return;
  maintenanceMode.value = mode;
  maintenanceError.value = "";
  maintenanceForm.value = {
    productCode: "",
    startDate: "",
    endDate: "",
  };
  showMaintenanceDialog.value = true;
};

const closeMaintenanceDialog = () => {
  if (maintenanceRunning.value) return;
  showMaintenanceDialog.value = false;
};

const submitMaintenance = async () => {
  if (expansionBusy.value) return;
  maintenanceError.value = "";
  if (!maintenanceForm.value.productCode) {
    maintenanceError.value = "完成品コードを入力してください。";
    return;
  }
  if (!maintenanceForm.value.startDate || !maintenanceForm.value.endDate) {
    maintenanceError.value = "期間を入力してください。";
    return;
  }
  if (maintenanceForm.value.startDate > maintenanceForm.value.endDate) {
    maintenanceError.value = "期間の大小が逆です。";
    return;
  }

  maintenanceRunning.value = true;
  message.value = "";
  warnings.value = [];
  try {
    const payload = {
      product_code: maintenanceForm.value.productCode,
      due_date_from: maintenanceForm.value.startDate,
      due_date_to: maintenanceForm.value.endDate,
    };
    const res = maintenanceMode.value === "revert"
      ? await api.orders.revertOrderExpansion(payload)
      : await api.orders.expandSelectedOrderExpansion(payload);
    const data = res.data || {};
    if (maintenanceMode.value === "revert") {
      message.value = `展開戻し完了: 対象=${data.target_order_lines ?? 0}, 差し戻し=${data.reverted_order_lines ?? 0}`;
    } else {
      message.value = `再展開完了: 対象=${data.target_order_lines ?? 0}, 再展開=${data.expanded_order_lines ?? 0}`;
    }
    warnings.value = data.warnings || [];
    showMaintenanceDialog.value = false;
  } catch (e) {
    maintenanceError.value = e?.response?.data?.detail || e?.response?.data?.errors?.[0] || e?.response?.data?.due_date_from?.[0] || "保守操作に失敗しました。";
    warnings.value = e?.response?.data?.warnings || [];
  } finally {
    maintenanceRunning.value = false;
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
.action-stack {
  display: grid;
  gap: 6px;
}
.sub-action-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}
.sub-action-btn {
  width: 100%;
  padding: 8px 0;
  background: #b45309;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  white-space: nowrap;
}
.sub-action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.sub-action-btn.secondary {
  background: #0f766e;
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
.dialog-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1200;
}
.dialog-card {
  width: min(460px, calc(100vw - 32px));
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.22);
  overflow: hidden;
}
.dialog-head, .dialog-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #e5e7eb;
}
.dialog-actions {
  border-bottom: none;
  border-top: 1px solid #e5e7eb;
  justify-content: flex-end;
  gap: 8px;
}
.dialog-head h3 {
  margin: 0;
  font-size: 16px;
}
.plain-btn {
  background: transparent;
  border: none;
  font-size: 18px;
  cursor: pointer;
}
.dialog-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.form-row label {
  font-size: 12px;
  color: #475569;
  font-weight: 700;
}
.form-row input {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 14px;
}
.dialog-note {
  margin: 0;
  font-size: 12px;
  color: #475569;
}
.dialog-error {
  margin: 0;
  font-size: 12px;
  color: #b91c1c;
}
.dialog-warning {
  margin: 0;
  padding: 8px;
  font-size: 12px;
  color: #9a3412;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: 6px;
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
