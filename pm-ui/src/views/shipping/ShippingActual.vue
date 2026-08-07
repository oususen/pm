<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">出荷実績照会 <DataSourceDialog title="出荷実績照会" :sources="dsSources" /></h2>
        <p class="subtitle">出荷実績の検索・閲覧ができます。</p>
      </div>
      <div class="page-actions">
        <input v-model="filters.productCode" type="text" placeholder="品番で検索" />
        <input v-model="filters.customerCode" type="text" placeholder="得意先で検索" />
        <input v-model="filters.shipToCode" type="text" placeholder="納入先で検索" />
        <input v-model="filters.startDate" type="date" />
        <input v-model="filters.endDate" type="date" />
        <select v-model="selectedFavoriteId" @change="applyFavorite">
          <option value="">お気に入り選択</option>
          <option v-for="fav in favorites" :key="fav.id" :value="String(fav.id)">
            {{ fav.name }}
          </option>
        </select>
        <input v-model.trim="favoriteName" type="text" placeholder="お気に入り名" />
        <button class="btn-secondary" title="お気に入り登録" @click="saveFavorite" :disabled="loading">★</button>
        <button @click="load" :disabled="loading">検索</button>
        <button class="btn-secondary" @click="exportExcel" :disabled="loading || exporting">
          {{ exporting ? '出力中...' : 'Excel出力' }}
        </button>
        <button class="btn-secondary" @click="resetFilters" :disabled="loading">クリア</button>
      </div>
    </div>

    <div class="page-body">
      <div class="list-card">
        <div v-if="loading" class="status-text">読込中...</div>
        <div v-else-if="error" class="status-text error">エラー: {{ error }}</div>
        <div v-else>
          <table class="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>出荷日</th>
                <th>品番</th>
                <th>品名</th>
                <th>得意先</th>
                <th>納入先</th>
                <th class="num">数量</th>
                <th>便番号</th>
                <th>出荷者</th>
                <th>出発時刻</th>
                <th>到着日</th>
                <th>注番</th>
                <th>備考</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in shipmentActuals" :key="item.id">
                <td class="num">{{ item.id }}</td>
                <td>{{ item.shipment_date }}</td>
                <td>{{ item.product_code }}</td>
                <td>{{ item.product_name || '-' }}</td>
                <td>{{ displayCustomer(item) }}</td>
                <td>{{ item.ship_to_code || '-' }}</td>
                <td class="num">{{ formatQty(item.quantity) }}</td>
                <td>{{ item.trip_code || '-' }}</td>
                <td>{{ item.departed_by_name || '-' }}</td>
                <td>{{ item.departure_time_actual || '-' }}</td>
                <td>{{ formatDateOnly(item.departure_date) }}</td>
                <td>{{ formatSourceOrderNos(item.source_order_nos) }}</td>
                <td>{{ displayRemark(item.remark) }}</td>
                <td class="actions">
                  <button class="btn-sm btn-secondary" @click="loadHistory(item)">履歴</button>
                </td>
              </tr>
              <tr v-if="!shipmentActuals.length">
                <td colspan="14" class="no-data">データがありません</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="historyTarget" class="history-card">
        <div class="history-header">
          <h3 class="card-title">修正履歴 (ID: {{ historyTarget.id }})</h3>
          <button class="btn-secondary btn-sm" @click="clearHistory">閉じる</button>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>記録日時</th>
              <th>操作</th>
              <th>出荷日</th>
              <th>品番</th>
              <th>得意先</th>
              <th>納入先</th>
              <th class="num">数量</th>
              <th>備考</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="h in historyRecords" :key="h.id">
              <td>{{ formatDateTime(h.created_at) }}</td>
              <td>{{ actionLabel(h.action) }}</td>
              <td>{{ h.shipment_date }}</td>
              <td>{{ h.product_code }}</td>
              <td>{{ h.customer_code || '-' }}</td>
              <td>{{ h.ship_to_code || '-' }}</td>
              <td class="num">{{ formatQty(h.quantity) }}</td>
              <td>{{ displayRemark(h.remark) }}</td>
            </tr>
            <tr v-if="!historyRecords.length">
              <td colspan="8" class="no-data">履歴がありません</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import api from "@/api/client";
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: 't_shipment_actual', desc: '出荷実績データ' },
]

const loading = ref(false);
const exporting = ref(false);
const error = ref("");
const shipmentActuals = ref([]);
const historyRecords = ref([]);
const historyTarget = ref(null);
const favorites = ref([]);
const selectedFavoriteId = ref("");
const favoriteName = ref("");
const FAVORITE_SCREEN_KEY = "shipping.actual";

const today = new Date();
const defaultStart = new Date(today.getFullYear(), today.getMonth(), 1);

const filters = reactive({
  productCode: "",
  customerCode: "",
  shipToCode: "",
  startDate: formatDate(today),
  endDate: formatDate(today),
});

function formatDate(date) {
  if (typeof date === "string") return date;
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function formatDateTime(value) {
  if (!value) return "-";
  const d = new Date(value);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${y}-${m}-${day} ${hh}:${mm}`;
}

function formatQty(value) {
  const num = Number(value || 0);
  if (!num) return "";
  return num.toLocaleString();
}

function formatDateOnly(value) {
  if (!value) return "-";
  const text = String(value).trim();
  if (!text) return "-";
  if (text.includes("T")) return text.split("T")[0];
  if (text.includes(" ")) return text.split(" ")[0];
  return text;
}

function displayCustomer(item) {
  if (item.customer_name) {
    return `${item.customer_code || ""} ${item.customer_name}`.trim();
  }
  return item.customer_code || "-";
}

function displayRemark(value) {
  const v = String(value || "").trim();
  if (!v) return "-";
  if (v.startsWith("[TRIP_ACTUAL]")) return "-";
  return v;
}

function formatSourceOrderNos(values) {
  if (!Array.isArray(values) || !values.length) return "-";
  return values.join(", ");
}

function resetFilters() {
  filters.productCode = "";
  filters.customerCode = "";
  filters.shipToCode = "";
  filters.startDate = formatDate(defaultStart);
  filters.endDate = formatDate(today);
  load();
}

function buildParams() {
  return {
    shipment_date__gte: filters.startDate,
    shipment_date__lte: filters.endDate,
    product_code: filters.productCode,
    customer_code: filters.customerCode,
    ship_to_code: filters.shipToCode,
    page_size: 10000,
  };
}

function toFavoritePayload() {
  return {
    productCode: filters.productCode,
    customerCode: filters.customerCode,
    shipToCode: filters.shipToCode,
  };
}

function applyFavoritePayload(payload) {
  filters.productCode = String(payload?.productCode || "");
  filters.customerCode = String(payload?.customerCode || "");
  filters.shipToCode = String(payload?.shipToCode || "");
}

async function loadFavorites() {
  try {
    const res = await api.accounts.getFavorites({ screen_key: FAVORITE_SCREEN_KEY, page_size: 200 });
    favorites.value = Array.isArray(res.data) ? res.data : res.data?.results || [];
  } catch (e) {
    console.error("お気に入り取得失敗:", e);
  }
}

function applyFavorite() {
  const id = Number(selectedFavoriteId.value || 0);
  if (!id) return;
  const target = favorites.value.find((item) => Number(item.id) === id);
  if (!target) return;
  favoriteName.value = target.name || "";
  applyFavoritePayload(target.payload || {});
}

async function saveFavorite() {
  const name = String(favoriteName.value || "").trim();
  if (!name) {
    window.alert("お気に入り名を入力してください。");
    return;
  }

  const payload = {
    screen_key: FAVORITE_SCREEN_KEY,
    name,
    payload: toFavoritePayload(),
  };

  try {
    const id = Number(selectedFavoriteId.value || 0);
    if (id) {
      await api.accounts.updateFavorite(id, payload);
    } else {
      await api.accounts.createFavorite(payload);
    }
    await loadFavorites();
    const found = favorites.value.find((item) => item.name === name);
    selectedFavoriteId.value = found ? String(found.id) : "";
    window.alert("お気に入りを保存しました。");
  } catch (e) {
    const detail = e?.response?.data?.detail || e?.message || "保存に失敗しました。";
    window.alert(`お気に入り保存エラー: ${detail}`);
  }
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const res = await api.shipmentActuals.getShipmentActuals(buildParams());
    shipmentActuals.value = Array.isArray(res.data) ? res.data : res.data.results || [];
  } catch (e) {
    console.error("出荷実績取得エラー:", e);
    error.value = e?.message || "読み込みに失敗しました";
  } finally {
    loading.value = false;
  }
}

async function exportExcel() {
  exporting.value = true;
  try {
    const res = await api.shipmentActuals.exportShipmentActualsExcel(buildParams());
    const blob = new Blob([res.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `出荷実績_${filters.startDate || 'from'}_${filters.endDate || 'to'}.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    console.error("出荷実績Excel出力エラー:", e);
    alert("Excel出力に失敗しました: " + (e.response?.data?.detail || e.message));
  } finally {
    exporting.value = false;
  }
}

async function loadHistory(item) {
  loading.value = true;
  error.value = "";
  historyTarget.value = item;
  try {
    const res = await api.shipmentActuals.getShipmentActualHistory(item.id);
    historyRecords.value = Array.isArray(res.data) ? res.data : res.data.results || [];
  } catch (e) {
    console.error("履歴取得エラー:", e);
    error.value = e?.message || "履歴取得に失敗しました";
  } finally {
    loading.value = false;
  }
}

function clearHistory() {
  historyTarget.value = null;
  historyRecords.value = [];
}

function actionLabel(action) {
  if (action === "CREATE") return "作成";
  if (action === "UPDATE") return "更新";
  if (action === "UPDATE_BEFORE") return "更新前";
  if (action === "UPDATE_AFTER") return "更新後";
  if (action === "DELETE") return "削除";
  return action;
}

onMounted(() => {
  load();
  loadFavorites();
});
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}
.page-title {
  margin: 0 0 4px 0;
  font-size: 20px;
  font-weight: 700;
}
.subtitle {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}
.page-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.page-actions input,
.page-actions button {
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 13px;
}
.btn-secondary {
  background: #f3f4f6;
}
.page-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.list-card,
.history-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
  background: #fff;
}
.card-title {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 700;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.data-table th,
.data-table td {
  border: 1px solid #e5e7eb;
  padding: 6px 8px;
}
.data-table th {
  background: #f9fafb;
  font-weight: 600;
}
.num {
  text-align: right;
}
.actions {
  display: flex;
  gap: 6px;
}
.btn-sm {
  padding: 2px 6px;
  font-size: 11px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: #fff;
}
.btn-danger {
  background: #fee2e2;
  border-color: #fecaca;
}
.status-text {
  padding: 12px;
  color: #6b7280;
}
.status-text.error {
  color: #dc2626;
}
.no-data {
  text-align: center;
  color: #6b7280;
}
.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
</style>
