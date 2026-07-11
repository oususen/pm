<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">出荷実績追跡 <DataSourceDialog title="出荷実績追跡" :sources="dsSources" /></h2>
        <p class="subtitle">注番・納入地・製品・出発日・到着日を便明細単位で追跡します。</p>
      </div>
      <div class="page-actions">
        <input v-model.trim="filters.productCode" type="text" placeholder="品番" />
        <input v-model.trim="filters.shipToCode" type="text" placeholder="納入先" />
        <input v-model.trim="filters.sourceOrderNo" type="text" placeholder="注番" />
        <input v-model.trim="filters.tripKeyword" type="text" placeholder="便名" />
        <input v-model="filters.departureDateFrom" type="date" title="出発日From" />
        <input v-model="filters.departureDateTo" type="date" title="出発日To" />
        <input v-model="filters.arrivalDateFrom" type="date" title="到着日From" />
        <input v-model="filters.arrivalDateTo" type="date" title="到着日To" />
        <button @click="load" :disabled="loading">検索</button>
        <button class="btn-secondary" @click="resetFilters" :disabled="loading">クリア</button>
      </div>
    </div>

    <div class="page-body">
      <div class="summary-card">
        <div class="summary-item">件数: {{ rows.length }}</div>
        <div class="summary-item">数量合計: {{ totalQty }}</div>
      </div>

      <div class="list-card">
        <div v-if="loading" class="status-text">読込中...</div>
        <div v-else-if="error" class="status-text error">エラー: {{ error }}</div>
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>到着日</th>
                <th>出発日</th>
                <th>便</th>
                <th>業務区分</th>
                <th>品番</th>
                <th>品名</th>
                <th>納入先</th>
                <th>得意先</th>
                <th class="num">数量</th>
                <th>注番</th>
                <th>生産日内訳</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in rows" :key="item.id">
                <td>{{ item.shipment_date || "-" }}</td>
                <td>{{ displayDepartureDate(item) }}</td>
                <td>{{ item.trip_code || "-" }}</td>
                <td>{{ item.business_type || "-" }}</td>
                <td>{{ item.product_code || "-" }}</td>
                <td>{{ item.product_name || "-" }}</td>
                <td>{{ item.ship_to_code || "-" }}</td>
                <td>{{ displayCustomer(item) }}</td>
                <td class="num">{{ formatQty(item.quantity) }}</td>
                <td>{{ joinOrderNos(item.source_order_nos) }}</td>
                <td class="split-cell">
                  <div v-for="split in item.production_splits || []" :key="split.id || `${item.id}-${split.line_no}`" class="split-row">
                    <span>{{ split.production_date }}</span>
                    <span class="num">{{ formatQty(split.quantity) }}</span>
                    <span>{{ split.source_order_no || "-" }}</span>
                  </div>
                  <span v-if="!(item.production_splits || []).length">-</span>
                </td>
              </tr>
              <tr v-if="!rows.length">
                <td colspan="11" class="no-data">データがありません</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import api from "@/api/client";
import DataSourceDialog from "@/components/DataSourceDialog.vue";

const dsSources = [
  { op: "読み取り", table: "t_shipment_actual", desc: "出荷実績" },
  { op: "読み取り", table: "t_shipment_actual_split", desc: "出荷実績内訳（生産日・注番）" },
  { op: "読み取り", table: "t_shipping_trip_allocation", desc: "出荷便割付" },
  { op: "読み取り", table: "t_shipping_trip", desc: "出荷便" },
];

const loading = ref(false);
const error = ref("");
const rows = ref([]);

const today = new Date();
const defaultFrom = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 7);

const filters = reactive({
  productCode: "",
  shipToCode: "",
  sourceOrderNo: "",
  tripKeyword: "",
  departureDateFrom: "",
  departureDateTo: "",
  arrivalDateFrom: "",
  arrivalDateTo: "",
});

const totalQty = computed(() => {
  const total = rows.value.reduce((sum, item) => sum + Number(item.quantity || 0), 0);
  if (!total) return "0";
  return total.toLocaleString();
});

function formatDate(date) {
  if (typeof date === "string") return date;
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function formatQty(value) {
  const num = Number(value || 0);
  if (!num) return "";
  return num.toLocaleString();
}

function displayCustomer(item) {
  if (item.customer_name) {
    return `${item.customer_code || ""} ${item.customer_name}`.trim();
  }
  return item.customer_code || "-";
}

function joinOrderNos(values) {
  const rows = Array.isArray(values) ? values.filter(Boolean) : [];
  return rows.length ? rows.join(", ") : "-";
}

function displayDepartureDate(item) {
  const departureDate = String(item?.departure_date || "").trim();
  if (!departureDate) return "-";
  if (item?.departure_time_actual) return departureDate;
  return `予定 ${departureDate}`;
}

function resetFilters() {
  filters.productCode = "";
  filters.shipToCode = "";
  filters.sourceOrderNo = "";
  filters.tripKeyword = "";
  filters.departureDateFrom = "";
  filters.departureDateTo = "";
  filters.arrivalDateFrom = "";
  filters.arrivalDateTo = "";
  load();
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const params = {
      product_code: filters.productCode,
      ship_to_code: filters.shipToCode,
      source_order_no: filters.sourceOrderNo,
      trip_keyword: filters.tripKeyword,
      departure_date__gte: filters.departureDateFrom,
      departure_date__lte: filters.departureDateTo,
      shipment_date__gte: filters.arrivalDateFrom,
      shipment_date__lte: filters.arrivalDateTo,
      page_size: 10000,
      ordering: "-shipment_date",
    };
    const res = await api.shippingTrace.getShippingTrace(params);
    rows.value = Array.isArray(res.data) ? res.data : res.data.results || [];
  } catch (e) {
    console.error("出荷実績追跡取得エラー:", e);
    error.value = e?.message || "読み込みに失敗しました";
  } finally {
    loading.value = false;
  }
}

onMounted(load);
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
  gap: 12px;
}
.summary-card,
.list-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
  background: #fff;
}
.summary-card {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}
.summary-item {
  font-size: 13px;
  font-weight: 600;
}
.table-wrap {
  overflow: auto;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  min-width: 1400px;
}
.data-table th,
.data-table td {
  border: 1px solid #e5e7eb;
  padding: 6px 8px;
  vertical-align: top;
}
.data-table th {
  background: #f9fafb;
  font-weight: 600;
  white-space: nowrap;
}
.num {
  text-align: right;
}
.split-cell {
  min-width: 260px;
}
.split-row {
  display: grid;
  grid-template-columns: 90px 70px 1fr;
  gap: 8px;
  border-bottom: 1px solid #f1f5f9;
  padding: 2px 0;
}
.split-row:last-child {
  border-bottom: none;
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
</style>
