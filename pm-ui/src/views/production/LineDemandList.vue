<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">ライン需要一覧</h2>
      <div class="page-actions">
        <input
          type="text"
          v-model="lineFilter"
          placeholder="ラインコード/名称で絞り込み"
          @keyup.enter="load"
        />
        <input
          type="text"
          v-model="processFilter"
          placeholder="工程コード/名称で絞り込み"
          @keyup.enter="load"
        />
        <input
          type="text"
          v-model="productFilter"
          placeholder="品番/品名で絞り込み"
          @keyup.enter="load"
        />
        <button @click="load" :disabled="loading || !hasFilter">更新</button>
      </div>
    </div>

    <div class="page-content">
      <div v-if="loading">読込中...</div>
      <div v-else-if="error" class="no-data">エラー: {{ error }}</div>
      <div v-else-if="!hasFilter" class="no-data">ライン、工程、または品番を入力してください</div>
      <div v-else>
        <table class="data-table" v-if="items.length">
          <thead>
            <tr>
              <th>日付</th>
              <th>ライン</th>
              <th>工程</th>
              <th>品番</th>
              <th>確定</th>
              <th>内示</th>
              <th>計画</th>
              <th>実績</th>
              <th>計画進度</th>
              <th>実績進度</th>
              <th>受注番号</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td>{{ item.plan_date }}</td>
              <td>{{ item.line_name || item.line }}</td>
              <td>{{ item.process_name || '' }}</td>
              <td>{{ item.product_code }}</td>
              <td class="num">{{ formatQty(item.firm_qty) }}</td>
              <td class="num">{{ formatQty(item.forecast_qty) }}</td>
              <td class="num">{{ formatQty(item.plan_qty) }}</td>
              <td class="num">{{ formatQty(item.actual_qty) }}</td>
              <td class="num">{{ formatProgress(item.plan_progress) }}</td>
              <td class="num">{{ formatProgress(item.actual_progress) }}</td>
              <td>{{ item.order_numbers }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="no-data">データがありません</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import api from "@/api/client";

const lineFilter = ref("");
const processFilter = ref("");
const productFilter = ref("");
const items = ref([]);
const loading = ref(false);
const error = ref("");

const hasFilter = computed(() =>
  !!(lineFilter.value.trim() || processFilter.value.trim() || productFilter.value.trim())
);

const formatQty = (v) => {
  if (v === null || v === undefined) return "";
  return Number(v).toLocaleString();
};

const formatProgress = (v) => {
  if (v === null || v === undefined) return "";
  return `${(Number(v) * 100).toFixed(1)}%`;
};

const load = async () => {
  if (!hasFilter.value) return;
  loading.value = true;
  error.value = "";
  try {
    const params = {};
    if (lineFilter.value.trim()) params.line_search = lineFilter.value.trim();
    if (processFilter.value.trim()) params.process_search = processFilter.value.trim();
    if (productFilter.value.trim()) params.product_search = productFilter.value.trim();
    const res = await api.lineDemands.list(params);
    const payload = res.data || [];
    items.value = Array.isArray(payload) ? payload : payload.results || [];
  } catch (e) {
    error.value = e?.message || "読み込みに失敗しました";
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.page-container {
  padding: 12px 10px 18px;
  background: #efefdc;
  min-height: 100%;
}
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}
.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
}
.page-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.page-actions input[type="text"] {
  padding: 4px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 13px;
  width: 180px;
}
.page-actions button {
  padding: 4px 14px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  background: #e2e8f0;
  cursor: pointer;
  font-size: 13px;
}
.page-actions button:disabled {
  opacity: 0.5;
  cursor: default;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.data-table th,
.data-table td {
  border: 1px solid #cbd5e1;
  padding: 4px 8px;
  white-space: nowrap;
}
.data-table th {
  background: #e2e8f0;
  font-weight: 600;
  position: sticky;
  top: 0;
}
.num {
  text-align: right;
}
.no-data {
  padding: 20px;
  color: #64748b;
  text-align: center;
}
</style>
